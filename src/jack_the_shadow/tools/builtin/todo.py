"""
Jack The Shadow — Todo / Plan Tracker Tools

Read and manage attack plan tasks and pentesting phase progress.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from jack_the_shadow.session.paths import JSHADOW_DIR
from jack_the_shadow.tools.base import BaseTool
from jack_the_shadow.tools.helpers import result
from jack_the_shadow.utils.logger import get_logger

if TYPE_CHECKING:
    from jack_the_shadow.tools.executor import ToolExecutor

logger = get_logger("tools.todo")

MEMORY_DIR: Path = JSHADOW_DIR / "memory"
TODOS_FILE: Path = MEMORY_DIR / "todos.json"


def _load_todos() -> list[dict[str, Any]]:
    if not TODOS_FILE.exists():
        return []
    try:
        data = json.loads(TODOS_FILE.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return []


def _save_todos(todos: list[dict[str, Any]]) -> None:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    TODOS_FILE.write_text(
        json.dumps(todos, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _next_id(todos: list[dict[str, Any]]) -> int:
    if not todos:
        return 1
    return max(t.get("id", 0) for t in todos) + 1


def _format_todos(todos: list[dict[str, Any]]) -> str:
    if not todos:
        return "No tasks found."
    status_icons = {"pending": "[ ]", "in_progress": "[~]", "done": "[x]"}
    lines: list[str] = []
    for t in todos:
        icon = status_icons.get(t.get("status", "pending"), "[ ]")
        phase = f" ({t['phase']})" if t.get("phase") else ""
        lines.append(f"{icon} #{t['id']} — {t.get('task', '???')}{phase}")
    return "\n".join(lines)


class TodoReadTool(BaseTool):
    name = "todo_read"
    description = (
        "Read the current attack plan and task checklist. "
        "Shows pentesting phase progress."
    )
    risk_aware = False

    @classmethod
    def parameters_schema(cls) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "status_filter": {
                    "type": "string",
                    "enum": ["pending", "in_progress", "done", "all"],
                    "description": (
                        "Filter tasks by status (default: all)."
                    ),
                },
            },
            "required": [],
        }


class TodoWriteTool(BaseTool):
    name = "todo_write"
    description = (
        "Create or update attack plan tasks. Use for tracking pentesting "
        "phases: Recon, Enumeration, Exploitation, Post-Exploitation, "
        "Reporting."
    )
    risk_aware = False

    @classmethod
    def parameters_schema(cls) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["add", "update", "remove", "clear"],
                    "description": "The action to perform on the todo list.",
                },
                "task": {
                    "type": "string",
                    "description": "Task description (for add action).",
                },
                "task_id": {
                    "type": "integer",
                    "description": "Task ID (for update/remove actions).",
                },
                "status": {
                    "type": "string",
                    "enum": ["pending", "in_progress", "done"],
                    "description": "New status (for update action).",
                },
                "phase": {
                    "type": "string",
                    "enum": [
                        "recon",
                        "enumeration",
                        "exploitation",
                        "post-exploitation",
                        "reporting",
                    ],
                    "description": "Pentesting phase for the task.",
                },
            },
            "required": ["action"],
        }


def handle_todo_read(
    executor: "ToolExecutor",
    status_filter: str = "all",
) -> dict[str, str]:
    try:
        todos = _load_todos()
    except OSError as exc:
        return result("error", message=f"Failed to load todos: {exc}")

    if status_filter and status_filter != "all":
        todos = [t for t in todos if t.get("status") == status_filter]

    return result("success", output=_format_todos(todos))


def handle_todo_write(
    executor: "ToolExecutor",
    action: str,
    task: str | None = None,
    task_id: int | None = None,
    status: str | None = None,
    phase: str | None = None,
) -> dict[str, str]:
    valid_actions = {"add", "update", "remove", "clear"}

    # Auto-correct: AI sometimes puts a description in `action` instead of enum
    if action not in valid_actions:
        if not task:
            task = action
        action = "add"
        logger.info("todo_write: auto-corrected action to 'add', task=%s", task)

    try:
        todos = _load_todos()
    except OSError as exc:
        return result("error", message=f"Failed to load todos: {exc}")

    if action == "add":
        if not task:
            return result("error", message="Task description is required for add.")
        new_todo: dict[str, Any] = {
            "id": _next_id(todos),
            "task": task,
            "status": "pending",
            "phase": phase or "",
            "created": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        }
        todos.append(new_todo)
        logger.info("todo add — id=%d task=%s", new_todo["id"], task)

    elif action == "update":
        if task_id is None:
            return result("error", message="task_id is required for update.")
        found = False
        for t in todos:
            if t.get("id") == task_id:
                if status:
                    t["status"] = status
                if phase:
                    t["phase"] = phase
                if task:
                    t["task"] = task
                found = True
                break
        if not found:
            return result("error", message=f"Task #{task_id} not found.")
        logger.info("todo update — id=%d", task_id)

    elif action == "remove":
        if task_id is None:
            return result("error", message="task_id is required for remove.")
        before = len(todos)
        todos = [t for t in todos if t.get("id") != task_id]
        if len(todos) == before:
            return result("error", message=f"Task #{task_id} not found.")
        logger.info("todo remove — id=%d", task_id)

    elif action == "clear":
        todos = []
        logger.info("todo clear — all tasks removed")

    else:
        return result("error", message=f"Unknown action: {action}")

    try:
        _save_todos(todos)
    except OSError as exc:
        return result("error", message=f"Failed to save todos: {exc}")

    return result("success", output=_format_todos(todos))
