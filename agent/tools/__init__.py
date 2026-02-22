"""
Tools package for smolagents CodeAgent.

All tools are local - 100% local, 0 donnée sortante.
"""

from .file_system import FileSystemTool
from .os_exec import OsExecTool
from .clipboard import ClipboardTool
from .screenshot import ScreenshotTool
from .mouse_keyboard import MouseKeyboardTool
from .vision import VisionTool
from .grounding import QwenGroundingTool

TOOLS = [
    FileSystemTool(),
    OsExecTool(),
    ClipboardTool(),
    ScreenshotTool(),
    MouseKeyboardTool(),
    VisionTool(),
    QwenGroundingTool(),
]
