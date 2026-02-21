"""
browser_agent — Agent spécialisé pilotage Chrome via DevTools MCP.

Outils : 26 tools Chrome DevTools MCP (navigation, click, fill, screenshot, snapshot...)
Modèle : qwen3:8b (local, 0 quota)
Rôle : Naviguer sur le web, remplir des formulaires, extraire du contenu
"""

import os
import logging
from contextlib import contextmanager
from smolagents import CodeAgent, ToolCollection
from mcp import StdioServerParameters

logger = logging.getLogger(__name__)

_BROWSER_INSTRUCTIONS = """
Tu es un agent spécialisé dans l'automatisation de Chrome via Chrome DevTools MCP.

WORKFLOW RECOMMANDÉ :
1. navigate_page(url=...) → naviguer vers une URL
2. take_snapshot() → obtenir la structure de la page avec les uid des éléments
3. click(uid=...) ou fill(uid=..., value=...) → interagir avec les éléments
4. wait_for(text=...) → attendre le chargement si nécessaire

BONNES PRATIQUES :
- Toujours take_snapshot() avant d'interagir pour connaître les uid
- Préférer take_snapshot() à take_screenshot() (plus rapide, uid exploitables)
- Utiliser wait_for() après une navigation si la page charge lentement
- Pour les recherches web : éviter Google (CAPTCHA), préférer DuckDuckGo ou Bing
- Utiliser evaluate_script() pour extraire du contenu dynamique
- Toujours retourner un résumé clair de ce qui a été fait ou trouvé
"""


def create_browser_agent(
    ollama_url: str,
    mcp_tools: list,
    model_id: str = "qwen3:8b",
) -> CodeAgent:
    """
    Crée le sous-agent browser avec les tools Chrome DevTools MCP déjà chargés.

    Args:
        ollama_url: URL du serveur Ollama (non utilisé, conservé pour compatibilité)
        mcp_tools: Liste des tools MCP déjà initialisés (depuis lifespan)
        model_id: Modèle à utiliser (défaut: "qwen3:8b")

    Returns:
        CodeAgent pour utilisation dans le manager
    """
    from models import get_model

    if not mcp_tools:
        logger.warning("browser_agent: aucun tool MCP Chrome DevTools disponible")

    # Modèle : glm-4.7 ou qwen3:8b local (0 quota, bon pour navigation structurée)
    model = get_model(model_id)

    agent = CodeAgent(
        tools=mcp_tools,
        model=model,
        max_steps=12,
        verbosity_level=1,
        additional_authorized_imports=["json", "re", "time"],
        executor_kwargs={"timeout_seconds": 240},
        instructions=_BROWSER_INSTRUCTIONS,
        name="browser",
        description=(
            "Agent spécialisé dans l'automatisation de Chrome. "
            "Peut naviguer vers des URLs, prendre des snapshots de pages web, "
            "cliquer sur des éléments, remplir des formulaires, exécuter du JavaScript, "
            "et extraire du contenu de pages web. "
            "Utilise-le pour : visiter des sites, faire des recherches web, "
            "remplir des formulaires en ligne, extraire des données de pages web."
        ),
    )

    return agent
