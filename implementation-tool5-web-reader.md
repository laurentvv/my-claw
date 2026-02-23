# TOOL-5 — Web Reader (VisitWebpageTool) — Plan d'implémentation

> Document pour IA de codage (Claude Code, Cursor, Cline…)
> Lire AGENTS.md, LEARNING.md, PROGRESS.md et le plan TOOL-4 avant de commencer.
> RÈGLE ABSOLUE : TOOL-4 doit être validé (✅ DONE) avant de commencer TOOL-5.
> Python 3.14 — uv comme gestionnaire de paquets.

---

## DÉCISION ARCHITECTURALE

**Pourquoi VisitWebpageTool plutôt que MCP Z.ai webReader ?**

| Critère            | MCP Z.ai webReader      | VisitWebpageTool (built-in)     |
|--------------------|------------------------|----------------------------------|
| Quota              | 100 calls/mois partagés | Illimité                         |
| Configuration      | ZAI_API_KEY requis      | 0 config                         |
| Dépendance         | Service Z.ai            | markdownify>=0.14.1 (déjà là)   |
| Output             | Texte propre (service)  | Markdown converti depuis HTML    |
| Max output         | Géré côté Z.ai          | max_output_length configurable   |

**Décision : VisitWebpageTool (built-in smolagents)**

**Important :** TOOL-5 s'intègre dans le même `web_agent` que TOOL-4.
Le web_agent gère à la fois DuckDuckGoSearchTool ET VisitWebpageTool.

---

## CONTEXTE PROJET

### Architecture après TOOL-4 (état attendu au démarrage de TOOL-5)
```
Manager (glm-4.7 / qwen3:8b)
├── pc_control_agent  → qwen3-vl:2b
├── browser_agent     → Nanbeige4.1-3B + 26 tools Chrome DevTools
└── web_agent         → Nanbeige4.1-3B
    ├── ✅ DuckDuckGoSearchTool  (TOOL-4)
    └── 🔧 VisitWebpageTool     (TOOL-5 — ce qu'on ajoute)
```

### Cas d'usage de VisitWebpageTool
- Lire le contenu complet d'une page GitHub (README, fichiers)
- Extraire la documentation d'une URL spécifique
- Vérifier le contenu d'un article ou d'un résultat de recherche
- Scraper une page pour en extraire les informations clés

### Différence avec browser_agent (Chrome DevTools)
- **browser_agent** : contrôle Chrome interactif, remplir formulaires, cliquer, naviguer
- **web_agent/VisitWebpageTool** : lecture seule du contenu texte d'une URL statique
  → Choisir web_agent pour extraction de texte (plus rapide, pas de Chrome)
  → Choisir browser_agent pour interaction avec la page (connexion, clic, etc.)

---

## STRUCTURE FICHIERS À CRÉER / MODIFIER

```
agent/
├── main.py           ← Pas de modification (web_agent déjà initialisé en TOOL-4)
├── skills.txt        ← Modifier : ajouter skills VisitWebpageTool
└── agents/
    └── web_agent.py  ← Modifier : ajouter VisitWebpageTool + mettre à jour instructions
```

**Aucun nouveau fichier de tool** — VisitWebpageTool est built-in smolagents.

---

## ÉTAPE 1 — Vérifier les dépendances

### 1A — Vérifier markdownify installé
```bash
cd agent
uv run python -c "import markdownify; print('markdownify OK')"
```
Si absent :
```bash
uv add "markdownify>=0.14.1"
# ou via toolkit :
uv add "smolagents[toolkit]"
```

### 1B — Vérifier import VisitWebpageTool
```bash
uv run python -c "from smolagents import VisitWebpageTool; t = VisitWebpageTool(); print('VisitWebpageTool OK')"
```

### 1C — Test rapide de lecture d'URL
```bash
uv run python -c "
from smolagents import VisitWebpageTool
tool = VisitWebpageTool(max_output_length=2000)
result = tool('https://huggingface.co/docs/smolagents/en/reference/default_tools')
print(result[:500])
"
```
Attendu : extrait du contenu de la page en markdown.

**Checkpoint 1** : Les 3 commandes réussissent.
Commit : `chore: vérification dépendances TOOL-5 OK`

---

## ÉTAPE 2 — Modifier agents/web_agent.py

TOOL-5 ne crée pas un nouveau agent — il enrichit le web_agent existant (TOOL-4).
Modifier `agent/agents/web_agent.py` pour :
1. Importer VisitWebpageTool
2. Mettre à jour les instructions système
3. Ajouter VisitWebpageTool dans la liste des tools du CodeAgent
4. Mettre à jour les descriptions ManagedAgent

### Code complet mis à jour : agent/agents/web_agent.py

```python
"""
TOOL-4 + TOOL-5 — Web Search & Web Reader Agent
- TOOL-4 : DuckDuckGoSearchTool — recherche web (0 quota, 0 config)
- TOOL-5 : VisitWebpageTool — lecture de page web (0 quota, 0 config)

Modèle : Nanbeige4.1-3B (validé 2026-02-22, BFCL-V4: 56.5)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from smolagents import CodeAgent, DuckDuckGoSearchTool, ManagedAgent, VisitWebpageTool

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# ── Constantes de configuration ───────────────────────────────────────────────

# Limite de sortie VisitWebpageTool
# 40000 chars = défaut smolagents (~10000 tokens)
# Réduire si le contexte du modèle est saturé (Nanbeige4.1-3B : 8192 tokens)
_VISIT_MAX_OUTPUT_LENGTH = 8000  # Adapté pour contexte 8192 tokens Nanbeige

# DuckDuckGo : nombre de résultats
_DDG_MAX_RESULTS = 5

# DuckDuckGo : rate limit (1 req/sec évite les blocages)
_DDG_RATE_LIMIT = 1.0

# ── Instructions système du web_agent (TOOL-4 + TOOL-5) ─────────────────────

_WEB_AGENT_INSTRUCTIONS = """
Tu es un agent web spécialisé dans la recherche et la lecture de pages web.

OUTILS DISPONIBLES :

1. web_search(query="...") [DuckDuckGoSearchTool]
   → Recherche web via DuckDuckGo
   → Retourne : titres, URLs, extraits de texte
   → Illimité, pas de quota

2. visit_webpage(url="https://...") [VisitWebpageTool]
   → Lit le contenu complet d'une URL
   → Retourne : contenu de la page en markdown
   → Limite : 8000 caractères de sortie
   → Ne fonctionne pas pour : pages derrière login, PDF, images

STRATÉGIE PAR CAS D'USAGE :

── CAS 1 : Trouver des informations générales ──────────────────────────────
1. web_search(query="sujet précis") pour trouver les meilleures URLs
2. visit_webpage(url="url_la_plus_pertinente") pour lire le détail
3. final_answer(synthèse)

Exemple :
```python
results = web_search(query="smolagents ManagedAgent tutorial 2025")
# Extraire la première URL pertinente des résultats
url = "https://huggingface.co/docs/smolagents/..."  # depuis les résultats
content = visit_webpage(url=url)
final_answer(f"Voici ce que j'ai trouvé :\\n{content}")
```

── CAS 2 : Lire une URL directe (connue) ────────────────────────────────────
Utiliser directement visit_webpage sans passer par web_search.

Exemple :
```python
content = visit_webpage(url="https://github.com/huggingface/smolagents/blob/main/README.md")
final_answer(content)
```

── CAS 3 : Recherche avec plusieurs sources ──────────────────────────────────
```python
results = web_search(query="Nanbeige 3B BFCL benchmark")
# Identifier 2-3 URLs pertinentes
content1 = visit_webpage(url="url_1")
content2 = visit_webpage(url="url_2")
final_answer(f"Source 1:\\n{content1}\\n\\nSource 2:\\n{content2}")
```

RÈGLES IMPORTANTES :
- Requêtes web_search : courtes (3-6 mots), en anglais si possible
- URLs visit_webpage : complètes avec https://
- Ne pas boucler indéfiniment — max 3 web_search + 3 visit_webpage par tâche
- Si visit_webpage échoue (timeout, 403, etc.) → essayer une autre URL
- Synthétiser le contenu, ne pas retourner des blocs bruts de 8000 chars

EXEMPLES DE PROMPTS ET RÉPONSES ATTENDUES :

Prompt : "Quelles sont les nouveautés Python 3.14 ?"
```python
results = web_search(query="Python 3.14 new features changelog")
url = "https://docs.python.org/3.14/whatsnew/3.14.html"  # depuis résultats
content = visit_webpage(url=url)
final_answer(content[:3000])  # limiter pour ne pas surcharger
```

Prompt : "Lis le README de smolagents sur GitHub"
```python
content = visit_webpage(url="https://raw.githubusercontent.com/huggingface/smolagents/main/README.md")
final_answer(content)
```

Prompt : "Cherche et lis la doc de FastAPI lifespan"
```python
results = web_search(query="FastAPI lifespan context manager documentation")
content = visit_webpage(url="https://fastapi.tiangolo.com/advanced/events/")
final_answer(content)
```
"""

# ── Factory function ──────────────────────────────────────────────────────────

def create_web_search_managed_agent(
    ollama_url: str,
    model_id: str = "hf.co/tantk/Nanbeige4.1-3B-GGUF:Q4_K_M",
    max_results: int = _DDG_MAX_RESULTS,
    rate_limit: float = _DDG_RATE_LIMIT,
    visit_max_output_length: int = _VISIT_MAX_OUTPUT_LENGTH,
) -> ManagedAgent | None:
    """
    Crée le ManagedAgent web avec DuckDuckGoSearchTool + VisitWebpageTool.

    TOOL-4 : DuckDuckGoSearchTool  (recherche web)
    TOOL-5 : VisitWebpageTool      (lecture page web)

    Args:
        ollama_url: URL du serveur Ollama
        model_id: Modèle Ollama (Nanbeige4.1-3B validé)
        max_results: Résultats max DuckDuckGo (défaut: 5)
        rate_limit: Rate limit DuckDuckGo req/sec (défaut: 1.0)
        visit_max_output_length: Limite sortie VisitWebpageTool (défaut: 8000)

    Returns:
        ManagedAgent configuré, ou None si échec.

    Note Python 3.14:
        - `X | None` préféré à `Optional[X]` (PEP 604)
        - f-strings imbriquées supportées nativement
        - `from __future__ import annotations` pour eval lazy des annotations
    """
    try:
        from smolagents import LiteLLMModel

        model = LiteLLMModel(
            model_id=f"ollama_chat/{model_id}",
            api_base=ollama_url,
            num_ctx=8192,
        )
        logger.info(f"✓ Modèle web_agent chargé : {model_id}")

        # ── TOOL-4 : DuckDuckGoSearchTool ────────────────────────────────────
        search_tool = DuckDuckGoSearchTool(
            max_results=max_results,
            rate_limit=rate_limit,
        )
        logger.info(
            f"✓ TOOL-4 DuckDuckGoSearchTool configuré "
            f"(max_results={max_results}, rate_limit={rate_limit})"
        )

        # ── TOOL-5 : VisitWebpageTool ─────────────────────────────────────────
        visit_tool = VisitWebpageTool(
            max_output_length=visit_max_output_length,
        )
        logger.info(
            f"✓ TOOL-5 VisitWebpageTool configuré "
            f"(max_output_length={visit_max_output_length})"
        )

        # ── CodeAgent avec les 2 tools ────────────────────────────────────────
        web_agent = CodeAgent(
            tools=[search_tool, visit_tool],  # TOOL-4 + TOOL-5
            model=model,
            name="web_search",
            description=(
                "Agent web : recherche et lecture de pages web. "
                "Outils : DuckDuckGoSearchTool (recherche) + VisitWebpageTool (lecture URL). "
                "Illimité, pas de quota."
            ),
            system_prompt=_WEB_AGENT_INSTRUCTIONS,
            max_steps=8,        # Plus élevé pour les tâches search+visit (2 étapes min)
            verbosity_level=1,
        )
        logger.info("✓ web_agent créé avec DuckDuckGoSearchTool + VisitWebpageTool")

        # ── ManagedAgent ──────────────────────────────────────────────────────
        managed_agent = ManagedAgent(
            agent=web_agent,
            name="web_search",
            description=(
                "Agent web pour recherche et lecture de pages. Capacités :\n"
                "- Recherche web via DuckDuckGo (TOOL-4)\n"
                "- Lecture du contenu d'une URL (TOOL-5)\n"
                "- Combinaison : rechercher puis lire la page la plus pertinente\n\n"
                "Exemples d'utilisation :\n"
                "- 'Quelles sont les nouveautés smolagents ?'\n"
                "- 'Lis le README de https://github.com/...'\n"
                "- 'Cherche et lis la doc FastAPI lifespan'\n"
                "- 'Prix Bitcoin aujourd'hui'\n"
                "- 'Benchmarks Nanbeige4.1-3B 2025'\n\n"
                "Ne pas utiliser pour : interactions avec des pages web (clic, formulaires) "
                "→ utiliser browser_agent dans ce cas."
            ),
            additional_prompting=(
                "Formule des requêtes web_search courtes (3-6 mots). "
                "Pour visit_webpage, fournis des URLs complètes avec https://. "
                "Synthétise les résultats au lieu de retourner du texte brut."
            ),
        )

        logger.info("✓ ManagedAgent web_search créé (TOOL-4 + TOOL-5)")
        return managed_agent

    except ImportError as e:
        logger.error(f"✗ Import manquant pour web_agent : {e}")
        if "markdownify" in str(e):
            logger.error("  → uv add 'markdownify>=0.14.1' pour VisitWebpageTool")
        elif "ddgs" in str(e) or "duckduckgo" in str(e):
            logger.error("  → uv add 'ddgs>=9.0.0' pour DuckDuckGoSearchTool")
        else:
            logger.error("  → uv add 'smolagents[toolkit]' pour tous les built-in tools")
        return None
    except Exception as e:
        logger.error(f"✗ Échec création web_agent : {e}")
        return None


# ── Diagnostic autonome ───────────────────────────────────────────────────────

def diagnose_web_tools() -> dict[str, bool | str | None]:
    """
    Diagnostique la disponibilité des outils web built-in.
    Utilisé par /health et /models.

    Returns:
        dict avec l'état de chaque tool.
    """
    result: dict[str, bool | str | None] = {}

    # TOOL-4 : DuckDuckGoSearchTool
    try:
        from duckduckgo_search import DDGS  # noqa: F401
        result["tool4_ddg"] = True
        result["tool4_ddg_name"] = "DuckDuckGoSearchTool"
        result["tool4_ddg_error"] = None
    except ImportError as e:
        result["tool4_ddg"] = False
        result["tool4_ddg_error"] = str(e)

    # TOOL-5 : VisitWebpageTool
    try:
        import markdownify  # noqa: F401
        result["tool5_visit"] = True
        result["tool5_visit_name"] = "VisitWebpageTool"
        result["tool5_visit_error"] = None
    except ImportError as e:
        result["tool5_visit"] = False
        result["tool5_visit_error"] = str(e)

    result["web_agent_ready"] = result.get("tool4_ddg", False) and result.get("tool5_visit", False)
    result["quota"] = "illimité (DuckDuckGo + markdownify, 0 API key)"

    return result


# ── Compatibilité TOOL-4 seul (alias pour rétrocompatibilité) ─────────────────

# Alias utilisé si main.py appelle encore l'ancienne signature TOOL-4 seule
# À supprimer après validation TOOL-5
diagnose_web_search = diagnose_web_tools
```

---

## ÉTAPE 3 — Pas de modification de main.py

TOOL-5 réutilise exactement la même factory `create_web_search_managed_agent()`.
La signature de la fonction n'a pas changé (nouveaux params ont des valeurs par défaut).

Vérifier simplement que l'appel dans main.py n'a pas de paramètres hardcodés qui
empêcheraient VisitWebpageTool de s'initialiser :

```python
# Dans main.py — lifespan startup — aucun changement nécessaire
managed_web = create_web_search_managed_agent(
    ollama_url=ollama_url,
    # Les paramètres TOOL-5 ont des valeurs par défaut :
    # visit_max_output_length=8000  ← défaut configuré dans web_agent.py
)
```

**Mettre à jour la description dans /models :**
```python
"web_search": "Nanbeige4.1-3B + DuckDuckGoSearchTool + VisitWebpageTool (illimité)",
```

**Mettre à jour /health pour inclure VisitWebpageTool :**
```python
@app.get("/health")
async def health():
    web_diag = diagnose_web_tools()  # ← signature mise à jour
    return {
        "status": "ok",
        "agents": {
            "web_search": _web_search_agent is not None,
        },
        "tools": {
            "web_search_ddg": web_diag.get("tool4_ddg", False),
            "web_visit": web_diag.get("tool5_visit", False),
            "web_agent_ready": web_diag.get("web_agent_ready", False),
        },
    }
```

**Checkpoint 3** : Redémarrer le serveur, vérifier logs :
```
✓ TOOL-4 DuckDuckGoSearchTool configuré (max_results=5, rate_limit=1.0)
✓ TOOL-5 VisitWebpageTool configuré (max_output_length=8000)
✓ web_agent créé avec DuckDuckGoSearchTool + VisitWebpageTool
✓ ManagedAgent web_search créé (TOOL-4 + TOOL-5)
```
Commit : `feat(tool-5): VisitWebpageTool ajouté au web_agent`

---

## ÉTAPE 4 — Mettre à jour skills.txt

Ajouter après les skills TOOL-4 dans `agent/skills.txt` :

```
── TOOL-5 : Lecture de Page Web (VisitWebpageTool) ──────────────────────────

SKILL 14 : Lire le contenu d'une URL
Utiliser visit_webpage pour extraire le texte d'une page web connue.
Passer l'URL complète au web_search agent.

QUAND UTILISER :
- Lire le README d'un repo GitHub
- Extraire le contenu d'une documentation officielle
- Vérifier le contenu d'un article trouvé via web_search
- Lire une page de résultat de recherche en détail

COMMENT FORMULER :
✅ "Lis le README de https://github.com/huggingface/smolagents"
✅ "Lis la doc officielle de smolagents sur huggingface.co"
✅ "Cherche les benchmarks Nanbeige puis lis la page la plus pertinente"
❌ "Télécharge le PDF de..." (VisitWebpageTool ne gère pas les PDF)
❌ "Clique sur le bouton..." (utiliser browser_agent pour les interactions)

SKILL 15 : Workflow Search + Read (Pattern recommandé)
Combiner TOOL-4 et TOOL-5 pour un workflow complet :
1. web_search(query="...") → trouver les meilleures URLs
2. visit_webpage(url="...") → lire le contenu de l'URL la plus pertinente
3. Synthétiser et retourner

Exemple de prompt utilisateur : "Quelles sont les nouveautés de smolagents v1.24 ?"
→ Le web_agent fait : search("smolagents 1.24 changelog") puis visit(url du changelog)

SKILL 16 : Lecture de raw GitHub
Pour lire des fichiers GitHub directement (code, markdown) :
✅ URL raw : https://raw.githubusercontent.com/user/repo/main/file.py
✅ "Lis le fichier web_agent.py dans le repo my-claw sur GitHub"

NOTE : VisitWebpageTool ne lit pas les pages derrière authentification.
Pour GitHub privé ou pages protégées → utiliser browser_agent.
```

---

## ÉTAPE 5 — Tests de validation

### 5A — Test VisitWebpageTool seul (URL directe)
Via Gradio :
```
Lis le contenu de https://huggingface.co/docs/smolagents/en/reference/default_tools
```
Attendu : extrait de la doc smolagents en markdown, avec liste des tools disponibles.

### 5B — Test workflow complet Search + Visit
```
Cherche les dernières nouveautés de smolagents puis lis la page la plus pertinente
```
Attendu en logs :
```
web_agent → web_search(query="smolagents latest release 2025")
web_agent → visit_webpage(url="https://github.com/huggingface/smolagents/releases")
→ final_answer(contenu du changelog)
```

### 5C — Test lecture fichier GitHub raw
```
Lis le README de smolagents sur GitHub
```
Attendu :
```
web_agent → visit_webpage(url="https://raw.githubusercontent.com/huggingface/smolagents/main/README.md")
→ contenu du README retourné
```

### 5D — Test gestion d'erreur (URL invalide)
```
Lis le contenu de https://cette-url-nexiste-pas-12345.xyz
```
Attendu : le web_agent retourne une erreur claire, pas un crash.
Log attendu : erreur mentionnée dans le final_answer, pas d'exception non gérée.

### 5E — Test délégation correcte (ne pas utiliser pour les clics)
```
Va sur GitHub et connecte-toi à mon compte
```
Attendu : le Manager délègue à browser_agent (pas au web_agent),
car VisitWebpageTool ne gère pas les authentifications.

### 5F — Vérification /health
```bash
curl http://localhost:8000/health
```
Attendu :
```json
{
  "tools": {
    "web_search_ddg": true,
    "web_visit": true,
    "web_agent_ready": true
  }
}
```

Commit : `feat: tool-5 — VisitWebpageTool validé`

---

## ÉTAPE 6 — Mettre à jour PROGRESS.md

```markdown
### TOOL-5 — Web Reader (VisitWebpageTool built-in)
**Statut : ✅ DONE**

Décision : built-in smolagents plutôt que MCP Z.ai webReader.
- 0 quota (économise les calls Z.ai pour TOOL-6 Zread)
- 0 config (markdownify>=0.14.1 déjà déclaré via smolagents[toolkit])
- Intégré dans le même web_agent que TOOL-4

Intégration :
- agent/agents/web_agent.py → tools=[DuckDuckGoSearchTool, VisitWebpageTool]
- VisitWebpageTool(max_output_length=8000) — adapté pour contexte 8192 Nanbeige
- Même ManagedAgent "web_search" — pas de nouvel agent créé
- Workflow combiné : search() puis visit() dans le même CodeAgent

Checkpoints validés :
- ✅ markdownify installé, import OK
- ✅ Logs startup : "✓ TOOL-5 VisitWebpageTool configuré"
- ✅ "Lis https://..." → contenu de la page en markdown
- ✅ Workflow Search + Visit dans le même agent
- ✅ Gestion d'erreur URL invalide (pas de crash)
- ✅ /health retourne "web_visit": true
- ✅ Commit : feat: tool-5 — VisitWebpageTool validé

Prochaine étape : TOOL-6 (Zread GitHub via MCP Z.ai — les 100 calls économisés)
```

---

## ÉTAPE 7 — Mettre à jour LEARNING.md

```markdown
## TOOL-5 — VisitWebpageTool (2026-02-23)

### Intégration dans le même agent que TOOL-4

Pattern recommandé : un seul CodeAgent avec plusieurs tools built-in.
Ne pas créer un agent séparé pour chaque outil — cela surcharge le Manager.

```python
web_agent = CodeAgent(
    tools=[
        DuckDuckGoSearchTool(max_results=5),  # TOOL-4
        VisitWebpageTool(max_output_length=8000),  # TOOL-5
    ],
    model=model_nanbeige,
    name="web_search",
    max_steps=8,  # Plus élevé car search + visit = 2 steps min
)
```

### max_output_length : calibrer selon le contexte du modèle

VisitWebpageTool.max_output_length (défaut smolagents : 40000 chars).
Nanbeige4.1-3B a un contexte de 8192 tokens ≈ 32000 chars.
Mais le contexte est partagé avec l'historique + les instructions.
Valeur safe pour Nanbeige : **8000 chars** (≈ 2000 tokens de contenu).

Si saturation du contexte : réduire à 4000.
Si résultats trop tronqués : augmenter à 12000 (avec modèle à plus grand contexte).

### Différence web_agent vs browser_agent

| Cas d'usage                    | Agent recommandé  |
|--------------------------------|-------------------|
| Lire le texte d'une URL        | web_agent (TOOL-5)|
| Chercher des infos sur le web  | web_agent (TOOL-4)|
| Cliquer sur un bouton          | browser_agent     |
| Remplir un formulaire          | browser_agent     |
| Se connecter à un compte       | browser_agent     |
| Scraper une SPA (JavaScript)   | browser_agent     |

### URLs raw GitHub pour lire des fichiers

VisitWebpageTool peut lire directement les fichiers GitHub via raw.githubusercontent.com :
```python
visit_webpage(url="https://raw.githubusercontent.com/user/repo/branch/file.py")
```
Utile pour lire le code sans passer par l'API GitHub (TOOL-6 Zread pour repos privés).

### max_steps=8 pour les workflows combinés

Un workflow search + visit = minimum 2 steps :
- Step 1 : web_search()
- Step 2 : visit_webpage()
- Step 3 : final_answer()

Mettre max_steps=5 (TOOL-4 seul) → max_steps=8 (TOOL-4 + TOOL-5).
```

---

## RÉCAPITULATIF ORDRE D'IMPLÉMENTATION

```
PRÉ-REQUIS : TOOL-4 validé (✅ DONE dans PROGRESS.md)
──────────────────────────────────────────────────────
ÉTAPE 1  Vérifier markdownify installé
ÉTAPE 2  Modifier agents/web_agent.py (code complet fourni ci-dessus)
         → Ajouter VisitWebpageTool dans tools[]
         → Mettre à jour instructions système
         → Mettre à jour descriptions ManagedAgent
         → max_steps=8 (au lieu de 5)
ÉTAPE 3  Mettre à jour /health et /models dans main.py (descriptions)
         → Pas de nouveau bloc lifespan nécessaire
ÉTAPE 4  Ajouter skills 14-16 dans skills.txt
ÉTAPE 5  Tests de validation (5A → 5F)
ÉTAPE 6  Mettre à jour PROGRESS.md
ÉTAPE 7  Mettre à jour LEARNING.md
──────────────────────────────────────────────────────
→ CHECKPOINT FINAL validé → commit → passer TOOL-6 (MCP Zread Z.ai)
```

---

## NOTES IMPORTANTES POUR L'IA DE CODAGE

1. **Ne pas créer** de deuxième ManagedAgent pour VisitWebpageTool — même agent que TOOL-4
2. **Ne pas modifier** main.py dans lifespan — create_web_search_managed_agent() n'a pas changé de signature
3. **max_output_length=8000** est calibré pour Nanbeige4.1-3B (contexte 8192 tokens)
4. **max_steps doit passer à 8** (était 5 pour TOOL-4 seul) — search+visit = 2-3 steps
5. **diagnose_web_search() devient diagnose_web_tools()** — alias rétrocompatible fourni
6. **Ne pas utiliser VisitWebpageTool pour les PDF** — il retourne le binaire ou échoue
7. **Python 3.14** : `X | None`, f-strings imbriquées, `from __future__ import annotations`
8. **uv** est le gestionnaire de paquets — pas pip
9. **Ne pas modifier** TOOL-1/2/3/7/8/9/10 — validés et stables
10. **TOOL-6** (Zread GitHub MCP Z.ai) utilise les 100 calls Z.ai économisés — plan séparé à venir
