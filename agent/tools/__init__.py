"""
Tools package for smolagents CodeAgent.

Most tools are local. Web tools (WebSearchTool, WebVisitTool) make outgoing
HTTP requests to DuckDuckGo and target websites (0 API key, unlimited).

Dependencies:
- ddgs>=9.0.0 for WebSearchTool (DuckDuckGo search)
- markdownify>=0.14.1 for WebVisitTool (web page reader)

Graceful degradation: If dependencies are missing, web tools are silently
disabled and the agent continues with remaining tools.
"""

import logging

from .clipboard import ClipboardTool
from .file_system import FileSystemTool
from .grounding import QwenGroundingTool
from .mouse_keyboard import MouseKeyboardTool
from .os_exec import OsExecTool
from .screenshot import ScreenshotTool
from .vision import VisionTool

logger = logging.getLogger(__name__)

# ── Web tools imports with graceful degradation ─────────────────────────────
WebSearchTool = None
WebVisitTool = None

try:
    from .web_search_tool import WebSearchTool  # noqa: F401

    logger.info("✓ WebSearchTool (DuckDuckGo) disponible")
except ImportError as e:
    logger.warning(f"✗ WebSearchTool indisponible: {e}")
    logger.warning("  → uv add 'ddgs>=9.0.0' pour activer la recherche web")
    WebSearchTool = None

try:
    from .web_visit_tool import WebVisitTool  # noqa: F401

    logger.info("✓ WebVisitTool (web reader) disponible")
except ImportError as e:
    logger.warning(f"✗ WebVisitTool indisponible: {e}")
    logger.warning("  → uv add 'markdownify>=0.14.1' pour activer la lecture web")
    WebVisitTool = None

__all__ = [
    "TOOLS",
    "ClipboardTool",
    "FileSystemTool",
    "QwenGroundingTool",
    "MouseKeyboardTool",
    "OsExecTool",
    "ScreenshotTool",
    "VisionTool",
    "WebSearchTool",
    "WebVisitTool",
]

# ── Tool list (local tools only) ─────────────────────────────────────────────
# NOTE: Les outils web (WebSearchTool, WebVisitTool) sont instanciés
# séparément dans main.py et ajoutés uniquement au manager, pas aux sous-agents.
# Les sous-agents utilisent uniquement les outils locaux.
TOOLS = [
    FileSystemTool(),
    OsExecTool(),
    ClipboardTool(),
    ScreenshotTool(),
    VisionTool(),
    QwenGroundingTool(),
    MouseKeyboardTool(),
]

logger.info(f"✓ {len(TOOLS)} outils chargés : {[t.name for t in TOOLS]}")
