"""
web_agent — Agent spécialisé recherche et lecture web via MCP Z.ai.

Outils : webSearchPrime, webReader, zread (chargés dynamiquement si ZAI_API_KEY)
Modèle : qwen3:8b (local, 0 quota pour le LLM)
Rôle : Recherche web temps réel, lecture d'articles, exploration de repos GitHub
"""

import logging
from smolagents import CodeAgent

logger = logging.getLogger(__name__)

_WEB_INSTRUCTIONS = """
Tu es un agent spécialisé dans la recherche et la lecture de contenu web.

OUTILS DISPONIBLES (si configurés) :
- webSearchPrime(search_query="...", search_recency_filter="oneWeek") → recherche web temps réel
- webReader(url="...") → lire le contenu complet d'une page web
- search_doc / get_repo_structure / read_file → explorer des repos GitHub publics

BONNES PRATIQUES :
- Garder les requêtes de recherche courtes et précises (max 70 caractères)
- Utiliser search_recency_filter="oneWeek" pour les actualités récentes
- Utiliser search_domain_filter="huggingface.co" pour cibler un site précis
- Résumer les résultats de manière concise et structurée
- Si aucun tool Z.ai n'est disponible (pas de ZAI_API_KEY), le signaler clairement

QUOTA : 100 calls/mois partagés entre recherche, lecture et GitHub. Utiliser avec parcimonie.
"""


def create_web_agent(
    ollama_url: str,
    web_search_tools: list,
    model_id: str | None = None,
) -> CodeAgent | None:
    """
    Crée le sous-agent web avec les tools MCP Z.ai déjà chargés.
    Retourne None si aucun tool web n'est disponible.

    Args:
        ollama_url: URL du serveur Ollama (non utilisé, conservé pour compatibilité)
        web_search_tools: Liste des tools MCP Z.ai (peut être vide)
        model_id: Modèle à utiliser (défaut: modèle par défaut via get_default_model())

    Returns:
        CodeAgent ou None si pas de tools disponibles
    """
    from models import get_model, get_default_model

    if not web_search_tools:
        logger.warning("web_agent: aucun tool web MCP disponible (ZAI_API_KEY manquant?)")
        return None

    if model_id is None:
        model_id = get_default_model()

    model = get_model(model_id)

    agent = CodeAgent(
        tools=web_search_tools,
        model=model,
        max_steps=8,
        verbosity_level=1,
        additional_authorized_imports=["json", "re"],
        executor_kwargs={"timeout_seconds": 120},
        instructions=_WEB_INSTRUCTIONS,
        name="web_search",
        description=(
            "Agent spécialisé dans la recherche web et la lecture de contenu en ligne. "
            "Peut effectuer des recherches web en temps réel, lire des articles et pages web, "
            "et explorer des repositories GitHub publics. "
            "Utilise-le pour : trouver des informations récentes, lire la documentation, "
            "explorer du code source sur GitHub."
        ),
    )

    return agent
