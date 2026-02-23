"""
Tools package for smolagents CodeAgent.

All tools are local - 100% local, 0 donnée sortante.
"""

from .clipboard import ClipboardTool
from .file_system import FileSystemTool
from .grounding import QwenGroundingTool
from .mouse_keyboard import MouseKeyboardTool
from .os_exec import OsExecTool
from .screenshot import ScreenshotTool
from .vision import VisionTool

TOOLS = [
    FileSystemTool(),
    OsExecTool(),
    ClipboardTool(),
    ScreenshotTool(),
    MouseKeyboardTool(),
    VisionTool(),
    QwenGroundingTool(),
]
