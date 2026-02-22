"""
File system tool for Windows operations.
Provides read, write, create, delete, list, move, and search operations on files and directories.
"""

import logging
from pathlib import Path
from typing import Optional

from smolagents import Tool

logger = logging.getLogger(__name__)


class FileSystemTool(Tool):
    name = "file_system"
    structured_output = False
    description = """Windows file system operations tool. Performs read, write, create, delete, list, move, and search operations on files and directories.

Operations:
- read: Read the content of a text file
- write: Write or replace the content of a file (creates parent directories if needed)
- create: Create a new file (with optional content, creates parent directories if needed)
- delete: Delete a file or empty directory
- list: List the contents of a directory
- move: Move or rename a file/directory
- search: Search for files by glob pattern in a directory

Returns a string with operation result or error message prefixed with 'ERROR:'."""
    inputs = {
        "operation": {
            "type": "string",
            "description": "The operation to perform: 'read', 'write', 'create', 'delete', 'list', 'move', or 'search'",
        },
        "path": {
            "type": "string",
            "description": "The file or directory path (absolute or relative)",
        },
        "content": {
            "type": "string",
            "description": "Content to write/create (required for 'write' and 'create' operations)",
            "nullable": True,
        },
        "destination": {
            "type": "string",
            "description": "Destination path for 'move' operation",
            "nullable": True,
        },
        "pattern": {
            "type": "string",
            "description": "Glob pattern for 'search' operation (e.g., '*.txt', 'test_*.py')",
            "nullable": True,
        },
    }
    output_type = "string"

    def forward(
        self,
        operation: str,
        path: str,
        content: Optional[str] = None,
        destination: Optional[str] = None,
        pattern: Optional[str] = None,
    ) -> str:
        """
        Execute the requested file system operation.

        Args:
            operation: The operation to perform
            path: The file or directory path
            content: Content for write/create operations
            destination: Destination for move operation
            pattern: Glob pattern for search operation

        Returns:
            Operation result or error message
        """
        try:
            path_obj = Path(path)

            if operation == "read":
                return self._read_file(path_obj)
            elif operation == "write":
                if content is None:
                    return "ERROR: content parameter is required for 'write' operation"
                return self._write_file(path_obj, content)
            elif operation == "create":
                return self._create_file(path_obj, content)
            elif operation == "delete":
                return self._delete(path_obj)
            elif operation == "list":
                return self._list_directory(path_obj)
            elif operation == "move":
                if destination is None:
                    return "ERROR: destination parameter is required for 'move' operation"
                return self._move(path_obj, Path(destination))
            elif operation == "search":
                if pattern is None:
                    return "ERROR: pattern parameter is required for 'search' operation"
                return self._search(path_obj, pattern)
            else:
                return f"ERROR: Unknown operation '{operation}'. Valid operations are: read, write, create, delete, list, move, search"

        except FileNotFoundError as e:
            logger.error(f"File not found: {e}")
            return f"ERROR: File or directory not found: {path}"
        except PermissionError as e:
            logger.error(f"Permission denied: {e}")
            return f"ERROR: Permission denied: {path}"
        except IsADirectoryError as e:
            logger.error(f"Expected file, got directory: {e}")
            return f"ERROR: Expected a file, got a directory: {path}"
        except NotADirectoryError as e:
            logger.error(f"Expected directory, got file: {e}")
            return f"ERROR: Expected a directory, got a file: {path}"
        except OSError as e:
            logger.error(f"OS error: {e}")
            return f"ERROR: {e}"

    def _read_file(self, path_obj: Path) -> str:
        """Read the content of a text file."""
        if not path_obj.is_file():
            raise FileNotFoundError(f"Not a file: {path_obj}")
        content = path_obj.read_text(encoding="utf-8")
        logger.info(f"Read file: {path_obj}")
        return content

    def _write_file(self, path_obj: Path, content: str) -> str:
        """Write content to a file, replacing existing content."""
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        path_obj.write_text(content, encoding="utf-8")
        logger.info(f"Wrote file: {path_obj}")
        return f"Successfully wrote content to {path_obj}"

    def _create_file(self, path_obj: Path, content: Optional[str] = None) -> str:
        """Create a new file (fails if already exists)."""
        if path_obj.exists():
            return f"ERROR: File already exists: {path_obj}"
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        if content is not None:
            path_obj.write_text(content, encoding="utf-8")
        else:
            path_obj.touch()
        logger.info(f"Created file: {path_obj}")
        return f"Successfully created file {path_obj}"

    def _delete(self, path_obj: Path) -> str:
        """Delete a file or empty directory."""
        if not path_obj.exists():
            raise FileNotFoundError(f"Path does not exist: {path_obj}")
        if path_obj.is_file():
            path_obj.unlink()
            logger.info(f"Deleted file: {path_obj}")
            return f"Successfully deleted file {path_obj}"
        else:
            if any(path_obj.iterdir()):
                return f"ERROR: Directory is not empty: {path_obj}"
            path_obj.rmdir()
            logger.info(f"Deleted directory: {path_obj}")
            return f"Successfully deleted directory {path_obj}"

    def _list_directory(self, path_obj: Path) -> str:
        """List the contents of a directory."""
        if not path_obj.is_dir():
            raise NotADirectoryError(f"Not a directory: {path_obj}")
        items = [item.name for item in path_obj.iterdir()]
        items.sort()
        logger.info(f"Listed directory: {path_obj} ({len(items)} items)")
        if items:
            return f"Contents of {path_obj}:\n" + "\n".join(f"  - {item}" for item in items)
        else:
            return f"Directory {path_obj} is empty"

    def _move(self, path_obj: Path, destination: Path) -> str:
        """Move or rename a file/directory."""
        if not path_obj.exists():
            raise FileNotFoundError(f"Source path does not exist: {path_obj}")
        if destination.exists():
            return f"ERROR: Destination already exists: {destination}"
        path_obj.rename(destination)
        logger.info(f"Moved {path_obj} -> {destination}")
        return f"Successfully moved/renamed {path_obj} to {destination}"

    def _search(self, path_obj: Path, pattern: str) -> str:
        """Search for files by glob pattern."""
        if not path_obj.is_dir():
            raise NotADirectoryError(f"Not a directory: {path_obj}")
        matches = list(path_obj.glob(pattern))
        logger.info(f"Searched {path_obj} for '{pattern}': {len(matches)} matches")
        if matches:
            # Sort by name and show relative paths
            matches_sorted = sorted(matches, key=lambda p: p.name)
            result = [str(match) for match in matches_sorted]
            return f"Found {len(matches)} matches for '{pattern}' in {path_obj}:\n" + "\n".join(f"  - {r}" for r in result)
        else:
            return f"No matches found for pattern '{pattern}' in {path_obj}"
