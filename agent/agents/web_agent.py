"""
TOOL-4 — Web Search Agent
Built-in DuckDuckGoSearchTool — 0 quota, 0 configuration.

Modèle : Nanbeige4.1-3B (validé 2026-02-22, benchmarks tool-use supérieurs à qwen3:8b)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from smolagents import CodeAgent, DuckDuckGoSearchTool

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
    model_id: str | None = None,
    max_results: int = 5,
    rate_limit: float = 1.0,
) -> CodeAgent | None:
    """
    Crée le CodeAgent de recherche web avec DuckDuckGoSearchTool.

    Args:
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
