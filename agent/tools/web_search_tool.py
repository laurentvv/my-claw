"""
web_search_tool — DuckDuckGoSearchTool pour la recherche web.

Outil : web_search (DuckDuckGoSearchTool)
Dépendances : ddgs>=9.0.0
Quota : Illimité (0 API key, 0 configuration)

NOTE: Wrapper avec configuration par défaut pour contrôle des paramètres.
"""

from smolagents import DuckDuckGoSearchTool

__all__ = ["WebSearchTool"]


class WebSearchTool(DuckDuckGoSearchTool):
    """
    DuckDuckGo web search avec configuration par défaut.
    
    Paramètres par défaut optimisés pour my-claw :
    - max_results=5 : équilibre entre pertinence et concision
    - rate_limit=1.0 : 1 requête/seconde pour éviter blocages DuckDuckGo
    """

    def __init__(self, max_results: int = 5, rate_limit: float = 1.0):
        super().__init__(max_results=max_results, rate_limit=rate_limit)
