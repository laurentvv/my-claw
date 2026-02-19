"""
OS execution tool for Windows PowerShell commands.
Allows executing PowerShell commands with timeout and capturing stdout/stderr.
"""

import logging
import subprocess
from typing import Optional

from smolagents import Tool


logger = logging.getLogger(__name__)


class OsExecTool(Tool):
    name = "os_exec"
    description = """Windows PowerShell execution tool. Executes PowerShell commands with timeout support.

Executes any PowerShell command and returns stdout, stderr, and returncode.
This tool provides full access to Windows system operations.

Parameters:
- command: The PowerShell command to execute
- timeout: Timeout in seconds (default: 30)

Returns a formatted string with stdout, stderr, and returncode, or an error message prefixed with 'ERROR:'."""
    inputs = {
        "command": {
            "type": "string",
            "description": "The PowerShell command to execute",
        },
        "timeout": {
            "type": "integer",
            "description": "Timeout in seconds (default: 30)",
            "nullable": True,
        },
    }
    output_type = "string"

    def forward(self, command: str, timeout: Optional[int] = 30) -> str:
        """
        Execute a PowerShell command.

        Args:
            command: The PowerShell command to execute
            timeout: Timeout in seconds (default: 30)

        Returns:
            Formatted string with stdout, stderr, and returncode, or error message
        """
        try:
            logger.info(f"Executing PowerShell command: {command[:100]}...")

            result = subprocess.run(
                ["powershell", "-Command", command],
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=timeout,
                shell=False,
            )

            stdout = result.stdout.strip() if result.stdout else ""
            stderr = result.stderr.strip() if result.stderr else ""
            returncode = result.returncode

            logger.info(f"Command completed with returncode: {returncode}")

            # Format the output
            output_parts = []
            output_parts.append(f"Return code: {returncode}")

            if stdout:
                output_parts.append(f"Stdout:\n{stdout}")

            if stderr:
                output_parts.append(f"Stderr:\n{stderr}")

            return "\n\n".join(output_parts)

        except subprocess.TimeoutExpired:
            logger.error(f"Command timed out after {timeout} seconds")
            return f"ERROR: Command timed out after {timeout} seconds"

        except FileNotFoundError:
            logger.error("PowerShell not found")
            return "ERROR: PowerShell not found on this system"

        except Exception as e:
            logger.error(f"Unexpected error executing command: {e}")
            return f"ERROR: {str(e)}"
