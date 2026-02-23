# TOOL-4 — Web Search (DuckDuckGoSearchTool) — Plan d'implémentation

> Document pour IA de codage (Claude Code, Cursor, Cline…)
> Lire AGENTS.md, LEARNING.md et PROGRESS.md avant de commencer.
> RÈGLE ABSOLUE : un checkpoint validé → commit → étape suivante.
> Python 3.14 — uv comme gestionnaire de paquets.

---

## DÉCISION ARCHITECTURALE

**Pourquoi pas MCP Z.ai pour TOOL-4 ?**

Le plan initial prévoyait `webSearchPrime` via MCP HTTP streamable Z.ai.
Après analyse des built-in tools smolagents, la décision est :

| Critère            | MCP Z.ai webSearchPrime | DuckDuckGoSearchTool (built-in) |
|--------------------|------------------------|----------------------------------|
| Quota              | 100 calls/mois partagés | Illimité                         |
| Configuration      | ZAI_API_KEY requis      | 0 config                         |
| Dépendance externe | Service Z.ai distant    | ddgs>=9.0.0 (déjà installé)     |
| Fiabilité          | API commerciale         | Scraping (peut fail CAPTCHA)     |
| Maintenance        | 0 (API gérée)           | Possible si DDG change HTML      |

**Décision : DuckDuckGoSearchTool (built-in smolagents)**
Les 100 calls/mois Z.ai sont économisés pour TOOL-6 (Zread GitHub),
qui n'a pas d'équivalent gratuit.

---

## CONTEXTE PROJET

### Architecture multi-agent existante
```
Manager (glm-4.7 / qwen3:8b)
├── pc_control_agent  → qwen3-vl:2b  (screenshot, vision, grounding, mouse/keyboard)
├── browser_agent     → Nanbeige4.1-3B  (26 tools Chrome DevTools MCP)
└── web_agent         → Nanbeige4.1-3B  ← TOOL-4 + TOOL-5 vont ici
```

### Stack technique
- Python 3.14
- uv (gestionnaire de paquets)
- smolagents >= 1.24.0
- FastAPI + lifespan
- Modèle web_agent : Nanbeige4.1-3B via Ollama (validé session 2026-02-22)

### Dépendances built-in smolagents (déjà déclarées dans pyproject.toml)
```
ddgs>=9.0.0        # DuckDuckGoSearchTool
markdownify>=0.14.1 # VisitWebpageTool (TOOL-5)
```
Vérifier : `uv run python -c "import ddgs; print('ddgs OK')"`
Si absent : `uv add "smolagents[toolkit]"`

---

## STRUCTURE FICHIERS À CRÉER / MODIFIER

```
agent/
├── main.py                    ← Modifier : instancier DuckDuckGoSearchTool dans lifespan
├── skills.txt                 ← Modifier : ajouter skills web search
└── agents/
    └── web_agent.py           ← Créer ou modifier : agent spécialisé web search
```

**Aucun nouveau tool dans agent/tools/** — DuckDuckGoSearchTool est built-in.

---

## ÉTAPE 1 — Vérifier les dépendances

### 1A — Vérifier ddgs installé
```bash
cd agent
uv run python -c "from duckduckgo_search import DDGS; print('ddgs OK')"
```

Si erreur :
```bash
uv add "smolagents[toolkit]"
# ou directement :
uv add "ddgs>=9.0.0"
```

### 1B — Vérifier import DuckDuckGoSearchTool
```bash
uv run python -c "from smolagents import DuckDuckGoSearchTool; t = DuckDuckGoSearchTool(); print('DuckDuckGoSearchTool OK')"
```

### 1C — Vérifier la version smolagents
```bash
uv run python -c "import smolagents; print(smolagents.__version__)"
# Attendu : >= 1.9.0
```

**Checkpoint 1** : Les 3 commandes réussissent sans erreur.
Commit : `chore: vérification dépendances TOOL-4 OK`

---

## ÉTAPE 2 — Créer / modifier agents/web_agent.py

Le fichier `agent/agents/web_agent.py` existe depuis la migration multi-agent.
Remplacer ou vérifier son contenu avec le code complet ci-dessous.

### Code complet : agent/agents/web_agent.py

```python
"""
TOOL-4 — Web Search Agent
Built-in DuckDuckGoSearchTool — 0 quota, 0 configuration.

Modèle : Nanbeige4.1-3B (validé 2026-02-22, benchmarks tool-use supérieurs à qwen3:8b)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from smolagents import CodeAgent, DuckDuckGoSearchTool, ManagedAgent

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# ── Instructions système du web_agent ────────────────────────────────────────

_WEB_SEARCH_INSTRUCTIONS = """
Tu es un agent de recherche web spécialisé. Tu utilises DuckDuckGoSearchTool
pour trouver des informations récentes et précises sur n'importe quel sujet.

OUTIL DISPONIBLE :
- web_search(query="...") → retourne une liste de résultats avec titres, URLs, extraits

STRATÉGIES DE RECHERCHE (par ordre de priorité) :

1. REQUÊTES COURTES ET PRÉCISES
   ✅ web_search(query="Python 3.14 new features")
   ✅ web_search(query="smolagents release notes 2025")
   ❌ web_search(query="Quelles sont toutes les nouvelles fonctionnalités de Python version 3.14 ?")

2. REQUÊTES EN ANGLAIS PAR DÉFAUT
   L'anglais donne plus de résultats. Traduis si le sujet est francophone.
   ✅ web_search(query="Nanbeige 3B benchmark BFCL")
   ✅ web_search(query="prix bitcoin aujourd'hui")  # exception : données FR

3. RECHERCHE ITÉRATIVE SI RÉSULTATS INSUFFISANTS
   - Premier call : requête large → évaluer pertinence
   - Deuxième call : requête affinée avec mots-clés supplémentaires
   Maximum 3 calls par tâche pour éviter les boucles.

4. POUR LE CODE ET LA DOCUMENTATION
   Inclure le nom de la technologie + "documentation" ou "example" :
   ✅ web_search(query="smolagents ManagedAgent example 2025")
   ✅ web_search(query="FastAPI lifespan context manager")

5. POUR LES ACTUALITÉS
   Ajouter l'année en cours ou "latest" / "2025" / "2026" :
   ✅ web_search(query="qwen3 model release 2025")

TRAITEMENT DES RÉSULTATS :
- Synthétiser les informations, ne pas tout recopier
- Indiquer les sources (URLs) pour les informations importantes
- Si les résultats sont contradictoires, le signaler
- Si aucun résultat pertinent : le dire clairement, ne pas inventer

EXEMPLES COMPLETS :
```python
# Recherche simple
results = web_search(query="smolagents built-in tools list")
final_answer(results)

# Recherche avec synthèse
results = web_search(query="Nanbeige4.1 3B benchmark results")
# Synthétiser et retourner
final_answer(f"Résultats de recherche sur Nanbeige4.1-3B :\\n{results}")

# Recherche itérative
results1 = web_search(query="Python 3.14 release date")
if "3.14" not in str(results1):
    results2 = web_search(query="CPython 3.14 changelog")
    final_answer(results2)
else:
    final_answer(results1)
```
"""

# ── Factory function ──────────────────────────────────────────────────────────

def create_web_search_agent(
    ollama_url: str,
    model_id: str | None = None,
    max_results: int = 5,
    rate_limit: float = 1.0,
) -> CodeAgent | None:
    """
    Crée le CodeAgent de recherche web avec DuckDuckGoSearchTool.

    Args:
        ollama_url: URL du serveur Ollama (ex: http://localhost:11434)
        model_id: Modèle à utiliser (défaut: modèle par défaut du système)
        max_results: Nombre max de résultats par recherche (défaut: 5)
        rate_limit: Limite de requêtes par seconde (défaut: 1.0)

    Returns:
        CodeAgent configuré, ou None si échec.

    Note Python 3.14:
        L'annotation de retour utilise `X | Y` (PEP 604) plutôt que Optional[X].
        Les f-strings imbriquées sont supportées nativement en 3.14.
    """
    try:
        # Import du modèle via models.py (pattern établi dans le projet)
        from models import get_model, get_default_model

        if model_id is None:
            model_id = get_default_model()

        model = get_model(model_id)
        logger.info(f"✓ Modèle web_agent chargé : {model_id}")

        # Instanciation du tool DuckDuckGoSearchTool
        search_tool = DuckDuckGoSearchTool(
            max_results=max_results,
            rate_limit=rate_limit,
        )
        logger.info(f"✓ DuckDuckGoSearchTool configuré (max_results={max_results})")

        # Création du CodeAgent avec le tool
        web_agent = CodeAgent(
            tools=[search_tool],
            model=model,
            name="web_search_agent",
            description=(
                "Effectue des recherches web en temps réel via DuckDuckGo. "
                "Exemples d'utilisation :\n"
                "- 'Recherche les dernières nouvelles sur smolagents'\n"
                "- 'Trouve la documentation de FastAPI lifespan'\n"
                "- 'Quels sont les benchmarks de Nanbeige4.1-3B ?'\n"
                "- 'Prix du Bitcoin aujourd'hui'\n"
                "Retourne : titres, extraits, URLs des sources."
            ),
            instructions=_WEB_SEARCH_INSTRUCTIONS,
            max_steps=5,
            verbosity_level=1,
        )
        logger.info("✓ web_search_agent (CodeAgent) créé avec succès")
        return web_agent

    except ImportError as e:
        logger.error(f"✗ Import manquant pour web_agent : {e}")
        logger.error("  → uv add 'smolagents[toolkit]' pour installer ddgs")
        return None
    except Exception as e:
        logger.error(f"✗ Échec création web_agent : {e}")
        return None


# ── Diagnostic autonome ───────────────────────────────────────────────────────

def diagnose_web_search() -> dict[str, bool | str]:
    """
    Diagnostique la disponibilité de DuckDuckGoSearchTool.
    Utilisé par /health et /models endpoints.

    Returns:
        dict avec les clés : available, tool_name, max_results, error
    """
    try:
        from smolagents import DuckDuckGoSearchTool as _DDG  # noqa: F401
        from duckduckgo_search import DDGS  # noqa: F401
        return {
            "available": True,
            "tool_name": "DuckDuckGoSearchTool",
            "backend": "duckduckgo_search (ddgs)",
            "quota": "illimité",
            "error": None,
        }
    except ImportError as e:
        return {
            "available": False,
            "tool_name": "DuckDuckGoSearchTool",
            "error": str(e),
            "fix": "uv add 'smolagents[toolkit]' ou uv add 'ddgs>=9.0.0'",
        }
```

---

## ÉTAPE 3 — Modifier main.py (section lifespan)

### 3A — Import à ajouter en haut de main.py
```python
# Imports agents spécialisés
from agents.web_agent import create_web_search_agent, diagnose_web_search
```

### 3B — Variables globales à déclarer (section globals de main.py)
```python
# TOOL-4 — Web Search (DuckDuckGoSearchTool built-in)
_web_search_agent: CodeAgent | None = None
```

### 3C — Bloc à ajouter dans lifespan (section startup)

Placer après l'initialisation du browser_agent :

```python
# ── TOOL-4 : Web Search (DuckDuckGoSearchTool built-in) ──────────────────────
logger.info("Initialisation TOOL-4 : Web Search (DuckDuckGoSearchTool)...")
try:
    managed_web = create_web_search_agent(
        ollama_url=ollama_url,
        model_id=None,  # Utilise le modèle par défaut du système
        max_results=5,
        rate_limit=1.0,
    )
    if managed_web is not None:
        _web_search_agent = managed_web
        logger.info("✓ TOOL-4 web_search_agent créé avec succès")
    else:
        logger.warning("✗ TOOL-4 web_search_agent non disponible (voir logs)")
except Exception as e:
    logger.error(f"✗ TOOL-4 échec init : {e}")
    _web_search_agent = None
```

### 3D — Pas de shutdown nécessaire
DuckDuckGoSearchTool n'est pas un context manager — aucun `__exit__` requis.
Contrairement à TOOL-10 (MCP Chrome) qui nécessite une fermeture propre.

### 3E — Mettre à jour /health
```python
@app.get("/health")
async def health():
    web_diag = diagnose_web_search()
    return {
        "status": "ok",
        "module": "2-multi-agent",
        "agents": {
            "pc_control": True,  # Toujours disponible (tools locaux)
            "vision": True,     # Toujours disponible (tools locaux)
            "browser": len(_chrome_mcp_tools) > 0,
            "web_search": _web_search_agent is not None,
        },
        "tools": {
            "chrome_mcp": len(_chrome_mcp_tools),
            "web_search": "DuckDuckGoSearchTool (illimité)" if web_diag["available"] else "indisponible",
        },
    }
```

### 3F — Mettre à jour /models
```python
@app.get("/models")
async def list_models():
    default_model = get_default_model()
    return {
        "default_model": default_model,
        "models": models_info,
        "ollama_models": get_ollama_models(),
        "sub_agents": {
            "pc_control": f"{default_model} + qwen3-vl (interne)",
            "vision": f"{default_model} + analyze_image (qwen3-vl interne)",
            "browser": f"{default_model} + {len(_chrome_mcp_tools)} tools Chrome DevTools",
            "web_search": f"{default_model} + DuckDuckGoSearchTool (illimité)",
        },
    }
```

**Checkpoint 3** : Démarrer le serveur et vérifier les logs :
```bash
cd agent
uv run uvicorn main:app --reload
```
Logs attendus :
```
✓ DuckDuckGoSearchTool configuré (max_results=5)
✓ web_search_agent (CodeAgent) créé avec succès
✓ TOOL-4 web_search_agent créé avec succès
```
Commit : `feat(tool-4): web search agent avec DuckDuckGoSearchTool`

---

## ÉTAPE 4 — Ajouter les skills dans skills.txt

Ajouter à la fin de `agent/skills.txt` :

```
── TOOL-4 : Recherche Web (DuckDuckGoSearchTool) ────────────────────────────

SKILL 11 : Recherche web en temps réel
Déléguer au web_search agent pour toute recherche d'information actuelle.

QUAND UTILISER :
- Actualités récentes, prix, données en temps réel
- Documentation technique (versions, APIs, exemples)
- Comparaisons de modèles, benchmarks récents
- Tout ce qui peut avoir changé après août 2025

COMMENT FORMULER LA REQUÊTE :
✅ "Recherche les dernières nouveautés smolagents"
✅ "Trouve la doc FastAPI lifespan Python"
✅ "Prix Bitcoin aujourd'hui"
✅ "Benchmarks Nanbeige4.1-3B vs qwen3:8b"
❌ "Fais une recherche complète et exhaustive sur tout ce qui concerne..."

SKILL 12 : Recherche de code et documentation
Pour trouver des exemples de code ou des APIs spécifiques :
- Inclure le nom de la lib + version + "example" ou "tutorial"
- Ex : "smolagents ManagedAgent 2025 example"
- Ex : "Python 3.14 f-string nested syntax"

SKILL 13 : Recherche itérative (multi-step)
Si la première recherche est insuffisante, affiner :
1. Recherche large : "Python 3.14 features"
2. Si résultat insuffisant → affiner : "CPython 3.14 PEP list"
Maximum 3 recherches par tâche.

NOTE : DuckDuckGoSearchTool est gratuit et illimité.
Pas de quota à gérer contrairement à Z.ai.
```

---

## ÉTAPE 5 — Tests de validation

### 5A — Test basique (Manager → web_search → résultat)
Via Gradio, prompt :
```
Quelles sont les dernières nouveautés de smolagents ?
```

Logs attendus :
```
Manager → délègue à web_search
web_search → DuckDuckGoSearchTool(query="smolagents latest release 2025")
→ résultats retournés
→ final_answer(synthèse avec sources)
```
Résultat attendu : liste de nouvelles avec URLs, datées de 2025-2026.

### 5B — Test requête technique
```
Quelle est la syntaxe des f-strings imbriquées en Python 3.14 ?
```
Attendu : le web_agent cherche "Python 3.14 f-string nested" et retourne des extraits de doc.

### 5C — Test délégation correcte (multi-agents)
```
Liste les fichiers dans C:/tmp puis cherche les benchmarks de Nanbeige4.1-3B
```
Attendu :
- Manager → file_system pour la liste (tool direct)
- Manager → web_search pour les benchmarks (délégation)
- Deux réponses consolidées

### 5D — Test fallback DDG indisponible
Simuler l'indisponibilité en overridant temporairement :
```python
# Dans web_agent.py, remplacer DuckDuckGoSearchTool par un mock qui lève une exception
```
Attendu : l'agent retourne une erreur claire, pas un crash silencieux.

### 5E — Vérification /health
```bash
curl http://localhost:8000/health
```
Attendu :
```json
{
  "agents": {
    "web_search": true
  },
  "tools": {
    "web_search": "DuckDuckGoSearchTool (illimité)"
  }
}
```

Commit : `feat: tool-4 — DuckDuckGoSearchTool validé`

---

## ÉTAPE 6 — Mettre à jour PROGRESS.md

```markdown
### TOOL-4 — Web Search (DuckDuckGoSearchTool built-in)
**Statut : ✅ DONE**

Décision : built-in smolagents plutôt que MCP Z.ai.
- 0 quota (économise les 100 calls/mois pour TOOL-6 Zread)
- 0 config (duckduckgo-search>=8.1.1 déjà installé via smolagents[toolkit])
- Même interface CodeAgent que les autres sub-agents

Intégration :
- agent/agents/web_agent.py → create_web_search_agent()
- DuckDuckGoSearchTool(max_results=5, rate_limit=1.0)
- Modèle : modèle par défaut du système (glm-4.7 ou qwen3:8b)
- Ajouté dans managed_agents[] dans lifespan main.py
- Skills ajoutés dans skills.txt (SKILL 11-13)

Checkpoints validés :
- ✅ ddgs installé (duckduckgo-search==8.1.1), import OK
- ✅ Logs startup : "✓ web_search_agent (CodeAgent) créé avec succès"
- ✅ "Quelles sont les dernières nouveautés de smolagents ?" → résultats temps réel
- ✅ "Quelle est la syntaxe des f-strings imbriquées en Python 3.14 ?" → réponse correcte
- ✅ Délégation Manager → web_search correcte
- ✅ /health retourne "web_search": true
- ✅ Commit : feat: tool-4 — DuckDuckGoSearchTool validé

Note : La lecture de pages web sera implémentée dans TOOL-5 (VisitWebpageTool).
```

---

## ÉTAPE 7 — Mettre à jour LEARNING.md

```markdown
## TOOL-4 — Web Search built-in vs MCP Z.ai (2026-02-23)

### Pourquoi built-in plutôt que MCP

Le plan initial (implementation-tool4-mcp-web-search-zai.md) utilisait
webSearchPrime via MCP HTTP streamable Z.ai (100 calls/mois partagés).

Après discovery des built-in tools smolagents, décision révisée :
- DuckDuckGoSearchTool : 0 quota, 0 config, déjà dans smolagents
- Les 100 calls Z.ai économisés pour TOOL-6 (Zread GitHub), sans équivalent gratuit

### DuckDuckGoSearchTool — paramètres clés

```python
from smolagents import DuckDuckGoSearchTool

tool = DuckDuckGoSearchTool(
    max_results=5,      # nombre de résultats retournés
    rate_limit=1.0,     # max 1 requête/seconde (évite blocage DDG)
)
results = tool("smolagents latest release")
```

### Pattern CodeAgent pour web_search

```python
from smolagents import CodeAgent, DuckDuckGoSearchTool

model = get_model(model_id)  # Utilise le modèle par défaut du système
web_agent = CodeAgent(
    tools=[DuckDuckGoSearchTool()],
    model=model,
    name="web_search_agent",  # Évite conflit avec le tool "web_search"
    description="Effectue des recherches web en temps réel via DuckDuckGo...",
    instructions=_WEB_SEARCH_INSTRUCTIONS,
    max_steps=5,
    verbosity_level=1,
)
```

### Pas de shutdown pour DuckDuckGoSearchTool

Contrairement aux MCP (TOOL-10 Chrome DevTools, futur TOOL-6 Zread) qui
nécessitent __exit__() dans le shutdown du lifespan, DuckDuckGoSearchTool
n'est pas un context manager → pas de cleanup nécessaire.

### Python 3.14 — annotations

Utiliser `X | None` plutôt que `Optional[X]` (PEP 604, disponible depuis 3.10).
En 3.14, les f-strings imbriquées sont supportées nativement.
```

---

## RÉCAPITULATIF ORDRE D'IMPLÉMENTATION

```
ÉTAPE 1  Vérifier dépendances ddgs (uv run python -c "from duckduckgo_search import DDGS")
ÉTAPE 2  Créer/modifier agents/web_agent.py (code complet fourni ci-dessus)
ÉTAPE 3  Modifier main.py (import, global, lifespan startup, /health, /models)
ÉTAPE 4  Ajouter skills 11-13 dans skills.txt
ÉTAPE 5  Tests de validation (5A → 5E)
ÉTAPE 6  Mettre à jour PROGRESS.md
ÉTAPE 7  Mettre à jour LEARNING.md
──────────────────────────────────────────────────────
→ CHECKPOINT FINAL validé → commit → passer TOOL-5 (VisitWebpageTool)
```

---

## NOTES IMPORTANTES POUR L'IA DE CODAGE

1. **Ne pas créer** de fichier agent/tools/web_search_tool.py — tool est built-in
2. **Ne pas modifier** agent/tools/__init__.py — DuckDuckGoSearchTool vient de smolagents
3. **Le modèle** du web_agent est le modèle par défaut du système (glm-4.7 ou qwen3:8b)
4. **rate_limit=1.0** est important — DDG peut bloquer si trop de requêtes rapides
5. **Python 3.14** : utiliser `X | None` pour les annotations, f-strings imbriquées OK
6. **uv** est le gestionnaire de paquets — pas pip directement
7. **Ne pas modifier** TOOL-1/2/3/7/8/9/10/11 — validés et stables
8. **CodeAgent** name doit être "web_search_agent" (évite conflit avec tool "web_search")
9. **Après TOOL-4** → implémenter TOOL-5 (VisitWebpageTool) dans le même web_agent
