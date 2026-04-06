"""
Jack The Shadow — Persistent Memory Tools

Read and write persistent notes (recon findings, credentials, target intel).
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from jack_the_shadow.session.paths import JSHADOW_DIR
from jack_the_shadow.tools.base import BaseTool
from jack_the_shadow.tools.helpers import result, truncate
from jack_the_shadow.utils.logger import get_logger

if TYPE_CHECKING:
    from jack_the_shadow.tools.executor import ToolExecutor

logger = get_logger("tools.memory")

MEMORY_DIR: Path = JSHADOW_DIR / "memory"
NOTES_FILE: Path = MEMORY_DIR / "notes.md"


class MemoryReadTool(BaseTool):
    name = "memory_read"
    description = (
        "Read persistent memory notes (recon findings, credentials, "
        "target intel). Returns contents of the session memory file."
    )
    risk_aware = False

    @classmethod
    def parameters_schema(cls) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Optional keyword filter for memory notes.",
                },
            },
            "required": [],
        }


class MemoryWriteTool(BaseTool):
    name = "memory_write"
    description = (
        "Save important findings to persistent memory (survives across "
        "sessions). Use for discovered IPs, credentials, vulnerabilities, "
        "recon intel."
    )
    risk_aware = False

    @classmethod
    def parameters_schema(cls) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "The content to save to memory.",
                },
                "category": {
                    "type": "string",
                    "enum": [
                        "recon",
                        "credentials",
                        "vulnerability",
                        "exploit",
                        "note",
                    ],
                    "description": "Category for the memory entry (default: note).",
                },
            },
            "required": ["content"],
        }


def handle_memory_read(
    executor: "ToolExecutor",
    query: str | None = None,
) -> dict[str, str]:
    if not NOTES_FILE.exists():
        return result("success", output="No memory notes found.")

    try:
        contents = NOTES_FILE.read_text(encoding="utf-8")
    except OSError as exc:
        return result("error", message=f"Failed to read memory: {exc}")

    if not contents.strip():
        return result("success", output="No memory notes found.")

    if query:
        lower_query = query.lower()
        filtered = [
            line for line in contents.splitlines()
            if lower_query in line.lower()
        ]
        if not filtered:
            return result("success", output=f"No memory notes matching '{query}'.")
        return result("success", output=truncate("\n".join(filtered)))

    return result("success", output=truncate(contents))


def handle_memory_write(
    executor: "ToolExecutor",
    content: str,
    category: str = "note",
) -> dict[str, str]:
    try:
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        entry = f"## [{category}] {timestamp}\n{content}\n\n"
        with NOTES_FILE.open("a", encoding="utf-8") as f:
            f.write(entry)
        logger.info("memory_write OK — category=%s", category)
        return result("success", output="Memory saved.")
    except OSError as exc:
        return result("error", message=f"Failed to write memory: {exc}")
