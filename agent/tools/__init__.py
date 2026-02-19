"""
Tools package for smolagents CodeAgent.

Local tools are imported here and added to the TOOLS list.
MCP tools are loaded dynamically in main.py.
"""

from .file_system import FileSystemTool
from .os_exec import OsExecTool
from .clipboard import ClipboardTool
from .screenshot import ScreenshotTool

TOOLS = [FileSystemTool(), OsExecTool(), ClipboardTool(), ScreenshotTool()]
