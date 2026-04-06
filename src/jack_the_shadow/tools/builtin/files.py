"""
Jack The Shadow — File Tools (Read, Write, Edit)

File operations with HITL gating for write/edit.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from jack_the_shadow.i18n import t
from jack_the_shadow.tools.base import BaseTool
from jack_the_shadow.tools.helpers import result, truncate
from jack_the_shadow.utils.logger import get_logger

if TYPE_CHECKING:
    from jack_the_shadow.tools.executor import ToolExecutor

logger = get_logger("tools.files")


# ── Schemas ──────────────────────────────────────────────────────────

class FileReadTool(BaseTool):
    name = "file_read"
    description = (
        "Read the contents of a file.  Supports text files.  "
        "Returns an error message if the file doesn't exist."
    )
    risk_aware = False

    @classmethod
    def parameters_schema(cls) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "filepath": {
                    "type": "string",
                    "description": "Absolute or relative path to the file.",
                },
                "line_start": {
                    "type": "integer",
                    "description": "Start line (1-indexed, optional).",
                },
                "line_end": {
                    "type": "integer",
                    "description": "End line (1-indexed, optional).",
                },
            },
            "required": ["filepath"],
        }


class FileWriteTool(BaseTool):
    name = "file_write"
    description = (
        "Create or overwrite a file with the given content.  "
        "Creates parent directories automatically.  Needs risk_level."
    )
    risk_aware = True

    @classmethod
    def parameters_schema(cls) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "filepath": {
                    "type": "string",
                    "description": "Absolute or relative path for the file.",
                },
                "content": {
                    "type": "string",
                    "description": "Full text content to write.",
                },
            },
            "required": ["filepath", "content"],
        }


class FileEditTool(BaseTool):
    name = "file_edit"
    description = (
        "Make a surgical text replacement in an existing file.  "
        "Finds old_text and replaces it with new_text.  "
        "Use for precise edits without rewriting the whole file."
    )
    risk_aware = True

    @classmethod
    def parameters_schema(cls) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "filepath": {
                    "type": "string",
                    "description": "Path to the file to edit.",
                },
                "old_text": {
                    "type": "string",
                    "description": "Exact text to find in the file.",
                },
                "new_text": {
                    "type": "string",
                    "description": "Replacement text.",
                },
            },
            "required": ["filepath", "old_text", "new_text"],
        }


# ── Handlers ─────────────────────────────────────────────────────────

def handle_file_read(
    executor: "ToolExecutor",
    filepath: str,
    line_start: int | None = None,
    line_end: int | None = None,
) -> dict[str, str]:
    filepath = os.path.expanduser(filepath)
    if not os.path.isfile(filepath):
        return result("error", message=f"File not found: {filepath}")

    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as fh:
            if line_start or line_end:
                lines = fh.readlines()
                start = max((line_start or 1) - 1, 0)
                end = line_end or len(lines)
                selected = lines[start:end]
                content = ""
                for i, line in enumerate(selected, start + 1):
                    content += f"{i:>4}│ {line}"
            else:
                content = fh.read()
        content = truncate(content)
        logger.info("file_read OK — %s (%d chars)", filepath, len(content))
        return result("success", output=content)
    except OSError as exc:
        return result("error", message=f"Cannot read {filepath}: {exc}")


def handle_file_write(
    executor: "ToolExecutor",
    filepath: str,
    content: str,
    risk_level: str = "Medium",
) -> dict[str, str]:
    filepath = os.path.expanduser(filepath)
    detail = f"{filepath}  ({len(content)} chars)"
    if not executor.request_approval("file_write", detail, risk_level):
        return result("error", message=t("tool.denied"))

    try:
        parent = os.path.dirname(filepath)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as fh:
            fh.write(content)
        logger.info("file_write OK — %s (%d chars)", filepath, len(content))
        return result("success", output=f"Written {len(content)} chars → {filepath}")
    except OSError as exc:
        return result("error", message=f"Cannot write {filepath}: {exc}")


def handle_file_edit(
    executor: "ToolExecutor",
    filepath: str,
    old_text: str,
    new_text: str,
    risk_level: str = "Low",
) -> dict[str, str]:
    filepath = os.path.expanduser(filepath)
    if not os.path.isfile(filepath):
        return result("error", message=f"File not found: {filepath}")

    try:
        with open(filepath, "r", encoding="utf-8") as fh:
            original = fh.read()
    except OSError as exc:
        return result("error", message=f"Cannot read {filepath}: {exc}")

    count = original.count(old_text)
    if count == 0:
        return result("error", message=f"old_text not found in {filepath}")
    if count > 1:
        return result(
            "error",
            message=f"old_text found {count} times — must be unique. Add more context.",
        )

    preview = f"{filepath}: replace '{old_text[:60]}...' → '{new_text[:60]}...'"
    if not executor.request_approval("file_edit", preview, risk_level):
        return result("error", message=t("tool.denied"))

    updated = original.replace(old_text, new_text, 1)
    try:
        with open(filepath, "w", encoding="utf-8") as fh:
            fh.write(updated)
        logger.info("file_edit OK — %s", filepath)
        return result("success", output=f"Edited {filepath} — replaced 1 occurrence")
    except OSError as exc:
        return result("error", message=f"Cannot write {filepath}: {exc}")
