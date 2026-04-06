"""
Jack The Shadow — Search Tools (Grep + Glob)

Regex search (ripgrep with Python fallback) and glob file finding.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Any

from jack_the_shadow.config import GLOB_MAX_RESULTS, GREP_MAX_RESULTS
from jack_the_shadow.tools.base import BaseTool
from jack_the_shadow.tools.helpers import result, truncate
from jack_the_shadow.utils.logger import get_logger

if TYPE_CHECKING:
    from jack_the_shadow.tools.executor import ToolExecutor

logger = get_logger("tools.search")


# ── Schemas ──────────────────────────────────────────────────────────

class GrepSearchTool(BaseTool):
    name = "grep_search"
    description = (
        "Search file contents using regex patterns (like ripgrep).  "
        "Returns matching lines with file paths and line numbers."
    )
    risk_aware = False

    @classmethod
    def parameters_schema(cls) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Regex pattern to search for.",
                },
                "path": {
                    "type": "string",
                    "description": "File or directory to search (default: cwd).",
                },
                "glob": {
                    "type": "string",
                    "description": "Glob filter for filenames, e.g. '*.py'.",
                },
                "case_insensitive": {
                    "type": "boolean",
                    "description": "Case insensitive search (default: false).",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Max results to return (default: 250).",
                },
            },
            "required": ["pattern"],
        }


class GlobFindTool(BaseTool):
    name = "glob_find"
    description = (
        "Find files matching a glob pattern.  "
        "Supports *, **, ?, {a,b} patterns.  "
        "Returns matching file paths."
    )
    risk_aware = False

    @classmethod
    def parameters_schema(cls) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern, e.g. '**/*.py' or 'src/**/*.conf'.",
                },
                "path": {
                    "type": "string",
                    "description": "Directory to search (default: cwd).",
                },
            },
            "required": ["pattern"],
        }


# ── Handlers ─────────────────────────────────────────────────────────

def handle_grep_search(
    executor: "ToolExecutor",
    pattern: str,
    path: str = ".",
    glob: str | None = None,
    case_insensitive: bool = False,
    max_results: int = GREP_MAX_RESULTS,
) -> dict[str, str]:
    path = os.path.expanduser(path)

    rg = _try_ripgrep(pattern, path, glob, case_insensitive, max_results)
    if rg is not None:
        return rg

    return _python_grep(pattern, path, glob, case_insensitive, max_results)


def handle_glob_find(
    executor: "ToolExecutor",
    pattern: str,
    path: str = ".",
) -> dict[str, str]:
    path = os.path.expanduser(path)
    target = Path(path)

    if not target.is_dir():
        return result("error", message=f"Directory not found: {path}")

    try:
        files = sorted(target.rglob(pattern))[:GLOB_MAX_RESULTS + 1]
    except OSError as exc:
        return result("error", message=f"Glob error: {exc}")

    truncated = len(files) > GLOB_MAX_RESULTS
    files = files[:GLOB_MAX_RESULTS]

    if not files:
        return result("success", output="No files matched.")

    lines = [str(f) for f in files]
    if truncated:
        lines.append(f"\n... [truncated at {GLOB_MAX_RESULTS} results]")

    return result("success", output="\n".join(lines))


# ── Internal ─────────────────────────────────────────────────────────

def _try_ripgrep(
    pattern: str, path: str, glob_pat: str | None,
    case_insensitive: bool, max_results: int,
) -> dict[str, str] | None:
    cmd = ["rg", "--no-heading", "--line-number", "--color=never"]
    if case_insensitive:
        cmd.append("-i")
    if glob_pat:
        cmd.extend(["-g", glob_pat])
    cmd.extend(["--max-count", str(max_results), pattern, path])

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if proc.returncode <= 1:
            output = truncate(proc.stdout) if proc.stdout else "No matches found."
            return result("success", output=output)
        return None
    except (FileNotFoundError, OSError):
        return None


def _python_grep(
    pattern: str, path: str, glob_pat: str | None,
    case_insensitive: bool, max_results: int,
) -> dict[str, str]:
    flags = re.IGNORECASE if case_insensitive else 0
    try:
        regex = re.compile(pattern, flags)
    except re.error as exc:
        return result("error", message=f"Invalid regex: {exc}")

    matches: list[str] = []
    target = Path(path)

    if target.is_file():
        files_iter = [target]
    elif target.is_dir():
        files_iter = list(target.rglob(glob_pat)) if glob_pat else [
            f for f in target.rglob("*") if f.is_file()
        ]
    else:
        return result("error", message=f"Path not found: {path}")

    for fp in files_iter:
        if len(matches) >= max_results:
            break
        try:
            with open(fp, "r", encoding="utf-8", errors="ignore") as fh:
                for lineno, line in enumerate(fh, 1):
                    if regex.search(line):
                        matches.append(f"{fp}:{lineno}: {line.rstrip()}")
                        if len(matches) >= max_results:
                            break
        except (OSError, UnicodeDecodeError):
            continue

    if not matches:
        return result("success", output="No matches found.")

    output = "\n".join(matches)
    if len(matches) == max_results:
        output += f"\n\n... [limited to {max_results} results]"
    return result("success", output=truncate(output))
