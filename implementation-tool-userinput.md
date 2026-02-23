# TOOL-UserInput — UserInputTool (Human-in-the-Loop) — Plan d'implémentation

> Document pour IA de codage (Claude Code, Cursor, Cline…)
> Lire AGENTS.md, LEARNING.md et PROGRESS.md avant de commencer.
> RÈGLE ABSOLUE : un checkpoint validé → commit → étape suivante.
> Python 3.14 — uv comme gestionnaire de paquets.

---

## RÔLE ET VALEUR AJOUTÉE

### Qu'est-ce que UserInputTool ?

`UserInputTool` est un built-in smolagents qui permet à l'agent de **mettre en pause
son exécution** pour poser une question à l'utilisateur, attendre sa réponse,
puis reprendre avec cette information.

C'est le mécanisme officiel smolagents pour Human-in-the-Loop.

### Cas d'usage critiques pour my-claw

```
1. CONFIRMATION AVANT ACTION DESTRUCTRICE
   Agent : "Je vais supprimer 47 fichiers dans C:/tmp. Confirmer ? (oui/non)"
   User  : "oui"
   Agent : → supprime les fichiers

2. LEVÉE D'AMBIGUÏTÉ
   Agent : "Tu veux le dossier 'projet-v1' ou 'projet-v2' ?"
   User  : "projet-v2"
   Agent : → continue avec le bon dossier

3. PARAMÈTRE MANQUANT
   Agent : "Quel nom donner au fichier de sortie ?"
   User  : "rapport_final.docx"
   Agent : → crée le fichier avec ce nom

4. VALIDATION D'UN PLAN
   Agent : "Voici mon plan en 3 étapes : [détail]. Je continue ?"
   User  : "oui mais skip l'étape 2"
   Agent : → adapte et exécute

5. SECRET / CREDENTIAL
   Agent : "Quel est ton mot de passe FTP ? (ne sera pas stocké)"
   User  : "••••••••"
   Agent : → utilise en mémoire sans logger
```

### Différence avec le chat Gradio normal

| Gradio normal | UserInputTool |
|---------------|---------------|
| L'utilisateur tape → l'agent répond | L'agent demande → attend → reprend |
| Multi-tours classiques | Interruption en cours d'exécution |
| Pas de contexte d'exécution | L'exécution est suspendue et reprend |

---

## CONTEXTE PROJET

### Architecture cible après ce TOOL

```
Manager (glm-4.7 / qwen3:8b)
├── UserInputTool     ← AJOUTÉ DIRECTEMENT AU MANAGER (pas un sous-agent)
├── pc_control_agent  → qwen3-vl:2b
├── browser_agent     → Nanbeige4.1-3B + Chrome DevTools
└── web_agent         → Nanbeige4.1-3B + DDG + VisitWebpage
```

**Important :** UserInputTool va dans le Manager directement, pas dans un sous-agent.
Le Manager doit pouvoir interroger l'utilisateur lui-même avant de déléguer.

### Compatibilité Gradio

UserInputTool utilise `input()` Python par défaut (stdin).
Avec Gradio, il faut utiliser le mode interactif de smolagents.

**Vérifier** que `main.py` utilise bien le streaming/callback Gradio compatible
avec les interruptions d'agent. Détail en Étape 3.

---

## STRUCTURE FICHIERS À CRÉER / MODIFIER

```
agent/
├── main.py           ← Modifier : ajouter UserInputTool au Manager + config Gradio
├── skills.txt        ← Modifier : ajouter skills Human-in-the-Loop
└── agents/
    └── manager_agent.py  ← Modifier : ajouter UserInputTool dans tools[]
```

**Aucun nouveau fichier de tool** — UserInputTool est built-in smolagents.

---

## ÉTAPE 1 — Vérifier la compatibilité

### 1A — Vérifier l'import UserInputTool
```bash
cd agent
uv run python -c "from smolagents import UserInputTool; t = UserInputTool(); print('UserInputTool OK')"
```

### 1B — Vérifier la version smolagents (>= 1.9.0 requis)
```bash
uv run python -c "import smolagents; print(smolagents.__version__)"
```

### 1C — Test fonctionnel basique (hors Gradio)
```bash
uv run python -c "
from smolagents import UserInputTool
tool = UserInputTool()
# Simulation : ce test va demander une saisie stdin
# Taper 'test_response' puis Entrée
result = tool('Quel est ton prénom ?')
print(f'Réponse reçue : {result}')
"
```
Attendu : affiche `Quel est ton prénom ?`, attend saisie, retourne la valeur.

**Checkpoint 1** : Import OK, test basique fonctionne.
Commit : `chore: vérification UserInputTool OK`

---

## ÉTAPE 2 — Comprendre le comportement en contexte Gradio

### Le problème stdin vs Gradio

Par défaut, `UserInputTool` appelle `input()` Python — bloquant sur stdin.
En contexte Gradio (serveur web), stdin n'est pas disponible de façon interactive.

**Smolagents propose 2 solutions :**

#### Solution A — GradioUI intégré (recommandée si tu utilises smolagents GradioUI)
```python
from smolagents import GradioUI, CodeAgent, UserInputTool

agent = CodeAgent(tools=[UserInputTool()], model=model)
GradioUI(agent).launch()  # gère l'interruption automatiquement
```
GradioUI de smolagents intègre nativement UserInputTool avec une zone de saisie
qui apparaît dans l'interface quand l'agent pose une question.

#### Solution B — Custom Gradio avec callback (si tu as ton propre main.py Gradio)
Surclasser UserInputTool pour rediriger `input()` vers un mécanisme async Gradio :

```python
# agent/tools/gradio_user_input_tool.py
from __future__ import annotations

import asyncio
import threading
from smolagents import UserInputTool

class GradioUserInputTool(UserInputTool):
    """
    UserInputTool adapté pour Gradio.
    Utilise un Event threading pour suspendre l'agent et attendre
    la saisie utilisateur via le chat Gradio.

    Python 3.14 : utilise queue.Queue plutôt que des globals mutables.
    """
    name = "user_input"
    description = (
        "Pose une question à l'utilisateur et attend sa réponse avant de continuer. "
        "Utiliser pour : confirmer une action, lever une ambiguïté, demander un paramètre manquant."
    )

    def __init__(self) -> None:
        super().__init__()
        # Queue thread-safe pour passer la réponse du thread Gradio → thread agent
        self._response_queue: "asyncio.Queue[str] | None" = None
        self._pending_question: str | None = None

    def forward(self, question: str) -> str:
        """
        Appelé par l'agent quand il a besoin d'une saisie utilisateur.
        Suspend l'exécution jusqu'à réception de la réponse.
        """
        import queue as stdlib_queue

        # Utiliser une queue stdlib (thread-safe, pas async)
        response_queue: stdlib_queue.Queue[str] = stdlib_queue.Queue()
        self._pending_question = question
        self._response_queue = response_queue  # type: ignore[assignment]

        # Signaler au thread Gradio qu'une question est en attente
        # (le thread Gradio lit _pending_question et envoie la question au chat)
        print(f"\n[UserInputTool] Question posée : {question}")
        print("[UserInputTool] En attente de réponse via Gradio...")

        # Attendre la réponse (bloquant — l'agent est suspendu)
        response = response_queue.get(timeout=300)  # timeout 5 minutes
        self._pending_question = None
        self._response_queue = None
        return response

    def provide_response(self, response: str) -> None:
        """
        Appelé par le handler Gradio quand l'utilisateur répond.
        Débloque forward() en injectant la réponse dans la queue.
        """
        if self._response_queue is not None:
            self._response_queue.put(response)  # type: ignore[union-attr]
        else:
            print("[UserInputTool] Warning : réponse reçue mais aucune question en attente")

    @property
    def has_pending_question(self) -> bool:
        """True si l'agent attend une réponse de l'utilisateur."""
        return self._pending_question is not None
```

**Quelle solution choisir pour my-claw ?**

Si `main.py` utilise `GradioUI` de smolagents directement → **Solution A** (0 code custom).
Si `main.py` construit son propre `gr.Blocks()` → **Solution B** (GradioUserInputTool).

Vérifier dans `main.py` :
```bash
grep -n "GradioUI\|gr.Blocks\|gradio" agent/main.py | head -20
```

**Checkpoint 2A** : Identifier quelle solution s'applique (A ou B).

---

## ÉTAPE 3 — Modifier manager_agent.py

### 3A — Si Solution A (GradioUI smolagents)

Dans `agent/agents/manager_agent.py`, ajouter UserInputTool dans la liste des tools du Manager :

```python
from smolagents import UserInputTool

# Dans create_manager_agent() :
manager_tools = [
    UserInputTool(),    # ← AJOUTER (Human-in-the-Loop)
    # ... autres tools directs du manager (si applicable)
]

manager_agent = CodeAgent(
    tools=manager_tools,
    managed_agents=[pc_control_agent, browser_agent, web_agent],
    model=model,
    name="manager",
    ...
)
```

### 3B — Si Solution B (gr.Blocks custom)

**Créer le fichier custom** `agent/tools/gradio_user_input_tool.py` avec le code
de l'Étape 2 (GradioUserInputTool).

Puis dans `manager_agent.py` :
```python
from tools.gradio_user_input_tool import GradioUserInputTool

# Instance globale partagée entre le manager et le handler Gradio
_user_input_tool = GradioUserInputTool()

def create_manager_agent(...) -> CodeAgent:
    manager_agent = CodeAgent(
        tools=[_user_input_tool],
        managed_agents=[...],
        ...
    )
    return manager_agent

def get_user_input_tool() -> GradioUserInputTool:
    """Exposer l'instance pour le handler Gradio dans main.py."""
    return _user_input_tool
```

### 3C — Instructions système du Manager

Ajouter dans les instructions système du Manager la directive d'utilisation de UserInputTool :

```python
_MANAGER_SYSTEM_PROMPT = """
...  (instructions existantes)

── HUMAN-IN-THE-LOOP : user_input ──────────────────────────────────────────

QUAND utiliser user_input(question="...") :
1. Avant toute action IRRÉVERSIBLE : suppression, écrasement, envoi réseau
2. Quand la tâche est AMBIGUË : plusieurs interprétations possibles
3. Quand un PARAMÈTRE MANQUE : nom de fichier, chemin, valeur spécifique
4. Pour VALIDER UN PLAN LONG : plus de 3 étapes, avant de commencer

COMMENT formuler la question :
✅ Question courte et précise avec les options possibles
✅ "Je vais supprimer 47 fichiers dans C:/tmp. Confirmer ? (oui/non)"
✅ "Dossier source : 'projet-v1' ou 'projet-v2' ?"
❌ Question vague sans options
❌ Demander à l'utilisateur ce que tu peux déduire toi-même

QUAND NE PAS utiliser user_input :
- Si la tâche est claire et non destructrice → exécuter directement
- Ne pas demander une confirmation pour chaque micro-action
- Maximum 2 user_input par tâche (éviter de harceler l'utilisateur)

EXEMPLE :
```python
# Avant suppression
confirmation = user_input(question="Je vais supprimer C:/tmp/old_logs/ (127 fichiers). Confirmer ? (oui/non)")
if "oui" in confirmation.lower():
    # ... suppression
else:
    final_answer("Suppression annulée par l'utilisateur.")
```
"""
```

**Checkpoint 3** : Redémarrer le serveur, vérifier que le Manager démarre avec UserInputTool :
```bash
cd agent
uv run uvicorn main:app --reload
# Logs attendus :
# ✓ Manager créé avec UserInputTool
```

---

## ÉTAPE 4 — Modifier main.py (handler Gradio)

### 4A — Si Solution A (GradioUI smolagents) — minimal

Rien à modifier dans le handler Gradio — GradioUI gère tout nativement.
Vérifier simplement que l'agent principal est passé à GradioUI :

```python
# Dans main.py — section Gradio
from smolagents import GradioUI

# Lancer l'interface avec le manager
GradioUI(manager_agent).launch(server_port=7860)
```

### 4B — Si Solution B (gr.Blocks custom) — handler à modifier

Dans `main.py`, modifier le handler du chat Gradio pour détecter si l'agent attend
une réponse et la router correctement :

```python
from agents.manager_agent import get_user_input_tool

# Récupérer l'instance partagée du tool
_input_tool = get_user_input_tool()

async def chat_handler(message: str, history: list) -> str:
    """
    Handler du chat Gradio.
    Gère 2 cas :
    1. Agent en attente de saisie → injecter la réponse via provide_response()
    2. Nouvelle requête → lancer l'agent normalement
    """
    # CAS 1 : l'agent attend une réponse utilisateur
    if _input_tool.has_pending_question:
        _input_tool.provide_response(message)
        return f"✓ Réponse transmise à l'agent : '{message}'"

    # CAS 2 : nouvelle requête normale
    try:
        result = await asyncio.to_thread(
            manager_agent.run,
            message,
        )
        return result
    except Exception as e:
        return f"Erreur : {e}"
```

**Note Python 3.14** : `asyncio.to_thread()` est la méthode recommandée pour
exécuter du code synchrone (l'agent smolagents) dans un contexte async (FastAPI/Gradio).
Disponible depuis Python 3.9, parfaitement supporté en 3.14.

**Checkpoint 4** : Tester via Gradio — voir Étape 5.

---

## ÉTAPE 5 — Tests de validation

### 5A — Test confirmation action destructrice
Via Gradio :
```
Supprime tous les fichiers .tmp dans C:/Windows/Temp
```
Attendu en logs :
```
Manager → user_input(question="Je vais supprimer N fichiers .tmp dans C:/Windows/Temp. Confirmer ? (oui/non)")
[Chat Gradio affiche la question]
```
Répondre "non" → attendu : "Suppression annulée par l'utilisateur."
Répondre "oui" → attendu : suppression effectuée + confirmation.

### 5B — Test levée d'ambiguïté
```
Ouvre le projet
```
Attendu :
```
Manager → user_input(question="Quel projet ? Projets disponibles : projet-v1, projet-v2, my-claw")
```

### 5C — Test paramètre manquant
```
Crée un nouveau fichier Python
```
Attendu :
```
Manager → user_input(question="Quel nom pour le fichier Python ? (ex: main.py, utils.py)")
```

### 5D — Test tâche claire sans interruption
```
Quelle heure est-il ?
```
Attendu : réponse directe SANS appel user_input (pas de perturbation inutile).

### 5E — Test timeout (5 minutes sans réponse)
Lancer une tâche qui déclenche user_input, ne pas répondre pendant 5+ minutes.
Attendu : le tool lève une TimeoutError propre, l'agent retourne une erreur claire.

### 5F — Vérification /health
```bash
curl http://localhost:8000/health
```
Attendu :
```json
{
  "tools": {
    "user_input": true
  }
}
```

Commit : `feat: UserInputTool — human-in-the-loop validé`

---

## ÉTAPE 6 — Ajouter les skills dans skills.txt

```
── UserInputTool : Human-in-the-Loop ────────────────────────────────────────

SKILL 17 : Confirmation avant action irréversible
Le Manager doit TOUJOURS demander confirmation avant :
- Suppression de fichiers ou dossiers
- Écrasement d'un fichier existant (sauf si l'utilisateur l'a explicitement demandé)
- Envoi de requêtes réseau modifiant des données distantes
- Fermeture ou arrêt d'un processus en cours

Formulation recommandée :
"Je vais [action] sur [cible] ([quantité/impact]). Confirmer ? (oui/non)"

SKILL 18 : Levée d'ambiguïté
Quand une requête a plusieurs interprétations possibles, demander avant d'agir :
"Tu veux dire [option A] ou [option B] ?"

Ne pas assumer. Ne pas choisir arbitrairement.

SKILL 19 : Paramètre manquant
Si un paramètre est indispensable et absent de la requête :
"Pour [action], j'ai besoin de [paramètre]. Quelle valeur ?"

Exemples :
- Nom de fichier de sortie
- Chemin de destination
- Valeur de configuration spécifique

RÈGLE GLOBALE UserInputTool :
Maximum 2 questions par tâche. Si plus de 2 paramètres manquent,
les grouper dans une seule question multi-parties plutôt que de
demander l'un après l'autre.

✅ "J'ai besoin de 2 informations : (1) nom du fichier ? (2) dossier de destination ?"
❌ Question 1 : "Nom du fichier ?" → Question 2 : "Dossier ?" → Question 3 : "Format ?"
```

---

## ÉTAPE 7 — Mettre à jour PROGRESS.md et LEARNING.md

### PROGRESS.md

```markdown
### UserInputTool — Human-in-the-Loop
**Statut : ✅ DONE**

Intégration :
- Ajouté dans tools[] du Manager directement (pas un sous-agent)
- Solution A (GradioUI) ou B (gr.Blocks custom) selon l'architecture Gradio
- Instructions système du Manager mises à jour avec règles HITL

Cas d'usage validés :
- ✅ Confirmation avant suppression
- ✅ Levée d'ambiguïté
- ✅ Paramètre manquant
- ✅ Tâche claire → 0 interruption (ne pas harceler)
- ✅ Timeout 5min propre

Commit : feat: UserInputTool — human-in-the-loop validé
```

### LEARNING.md

```markdown
## UserInputTool — Human-in-the-Loop (2026-02-23)

### Placement : Manager, pas sous-agent

UserInputTool va dans le Manager (CodeAgent principal), pas dans un ManagedAgent.
Raison : c'est le Manager qui décide d'agir ou non. Les sous-agents n'ont pas
à interroger l'utilisateur — ils reçoivent des tâches précises du Manager.

### Solution A vs Solution B

- GradioUI smolagents (Solution A) : intégration native, 0 code custom.
  Utiliser si l'interface Gradio est créée via GradioUI(agent).launch().

- gr.Blocks custom (Solution B) : nécessite GradioUserInputTool + handler modifié.
  Le handler vérifie _input_tool.has_pending_question avant de lancer l'agent.

### asyncio.to_thread() en Python 3.14

smolagents CodeAgent.run() est synchrone. Dans un contexte async (FastAPI, Gradio),
utiliser asyncio.to_thread() pour ne pas bloquer la boucle d'événements :

```python
result = await asyncio.to_thread(manager_agent.run, message)
```

Disponible depuis Python 3.9. En 3.14, c'est la bonne pratique.
Ne pas utiliser loop.run_in_executor(None, ...) — deprecated style.

### Règle des 2 questions max

Un agent qui pose trop de questions est perçu comme incompétent.
Regrouper les questions manquantes en une seule si possible.
```

---

## RÉCAPITULATIF ORDRE D'IMPLÉMENTATION

```
ÉTAPE 1  Vérifier import UserInputTool
ÉTAPE 2  Identifier Solution A (GradioUI) ou B (gr.Blocks)
ÉTAPE 3  Modifier manager_agent.py (ajouter UserInputTool + instructions HITL)
         → Si Solution B : créer agent/tools/gradio_user_input_tool.py
ÉTAPE 4  Modifier main.py handler Gradio
         → Solution A : vérifier GradioUI(agent).launch()
         → Solution B : ajouter logique has_pending_question
ÉTAPE 5  Tests de validation (5A → 5F)
ÉTAPE 6  Ajouter skills 17-19 dans skills.txt
ÉTAPE 7  Mettre à jour PROGRESS.md et LEARNING.md
──────────────────────────────────────────────────────────────────
→ CHECKPOINT FINAL validé → commit → passer PythonInterpreterTool
```

---

## NOTES IMPORTANTES POUR L'IA DE CODAGE

1. **UserInputTool va dans le Manager** — pas dans pc_control, browser, ou web_agent
2. **Solution A si GradioUI** — vérifier avant de créer du code custom inutile
3. **Solution B** : l'instance `_user_input_tool` doit être **partagée** entre
   `manager_agent.py` (qui la passe au CodeAgent) et `main.py` (qui appelle provide_response)
4. **timeout=300** dans `stdlib_queue.Queue.get()` — évite un blocage infini
5. **asyncio.to_thread()** pour appeler agent.run() depuis un contexte async
6. **Python 3.14** : `X | None`, annotations lazy via `from __future__ import annotations`
7. **Ne pas ajouter** UserInputTool aux sous-agents (pc_control, browser, web) — Manager seul
8. **Maximum 2 user_input par tâche** — le noter dans les instructions système du Manager
9. **Ne pas modifier** TOOL-1/2/3/4/5/7/8/9/10 — validés et stables
10. **has_pending_question** : propriété booléenne à vérifier dans le handler Gradio
    avant chaque message entrant (Solution B uniquement)
