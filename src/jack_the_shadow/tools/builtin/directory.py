"""
Jack The Shadow — List Directory Tool

Tree-style directory listing.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

from jack_the_shadow.config import LIST_DIR_MAX_DEPTH
from jack_the_shadow.tools.base import BaseTool
from jack_the_shadow.tools.helpers import result, truncate
from jack_the_shadow.utils.logger import get_logger

if TYPE_CHECKING:
    from jack_the_shadow.tools.executor import ToolExecutor

logger = get_logger("tools.directory")


class ListDirectoryTool(BaseTool):
    name = "list_directory"
    description = (
        "List files and directories in a tree-like format.  "
        "Shows structure up to a given depth."
    )
    risk_aware = False

    @classmethod
    def parameters_schema(cls) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Directory to list (default: cwd).",
                },
                "max_depth": {
                    "type": "integer",
                    "description": "Max depth to traverse (default: 3).",
                },
                "show_hidden": {
                    "type": "boolean",
                    "description": "Show hidden files (default: false).",
                },
            },
            "required": [],
        }


def handle_list_directory(
    executor: "ToolExecutor",
    path: str = ".",
    max_depth: int = LIST_DIR_MAX_DEPTH,
    show_hidden: bool = False,
) -> dict[str, str]:
    path = os.path.expanduser(path)
    if not os.path.isdir(path):
        return result("error", message=f"Directory not found: {path}")

    lines: list[str] = [f"{path}/"]
    _tree(Path(path), "", 0, max_depth, show_hidden, lines)

    output = "\n".join(lines)
    return result("success", output=truncate(output))


def _tree(
    dir_path: Path,
    prefix: str,
    depth: int,
    max_depth: int,
    show_hidden: bool,
    lines: list[str],
) -> None:
    if depth >= max_depth:
        return
    try:
        entries = sorted(
            dir_path.iterdir(),
            key=lambda e: (not e.is_dir(), e.name.lower()),
        )
    except PermissionError:
        lines.append(f"{prefix}[permission denied]")
        return

    if not show_hidden:
        entries = [e for e in entries if not e.name.startswith(".")]

    for i, entry in enumerate(entries):
        is_last = i == len(entries) - 1
        connector = "└── " if is_last else "├── "
        suffix = "/" if entry.is_dir() else ""
        lines.append(f"{prefix}{connector}{entry.name}{suffix}")

        if entry.is_dir():
            extension = "    " if is_last else "│   "
            _tree(entry, prefix + extension, depth + 1, max_depth, show_hidden, lines)
