"""
TOOL-4 + TOOL-5 — Web Search & Web Reader (Built-in smolagents)

- TOOL-4 : DuckDuckGoSearchTool — recherche web (0 quota, 0 config)
- TOOL-5 : VisitWebpageTool — lecture de page web (0 quota, 0 config)

ARCHITECTURE : Ces outils sont passés DIRECTEMENT au manager (pas de managed_agent).
Contrairement à pc_control_agent ou vision_agent, il n'y a pas de web_agent spécialisé.
Les outils sont appelés directement par le manager via web_search() et visit_webpage().

MODÈLE : Nanbeige4.1-3B (validé 2026-02-22, BFCL-V4: 56.5)
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


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
        from ddgs import DDGS  # noqa: F401
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
