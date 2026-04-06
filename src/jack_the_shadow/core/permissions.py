"""
Jack The Shadow — Permission Patterns

Glob-based auto-approve rules for finer-grained control than YOLO on/off.
E.g., auto-approve `bash_execute` for "nmap *" but still prompt for "rm -rf".
"""

from __future__ import annotations

import fnmatch
import json
from pathlib import Path
from typing import Any

from jack_the_shadow.session.paths import JSHADOW_DIR
from jack_the_shadow.utils.logger import get_logger

logger = get_logger("core.permissions")

PERMISSIONS_FILE = JSHADOW_DIR / "permissions.json"


def _load_rules() -> dict[str, list[str]]:
    """Load permission rules from disk. Format: {"tool_name": ["pattern", ...]}"""
    if PERMISSIONS_FILE.exists():
        try:
            return json.loads(PERMISSIONS_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_rules(rules: dict[str, list[str]]) -> None:
    PERMISSIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    PERMISSIONS_FILE.write_text(json.dumps(rules, indent=2))


def add_permission_rule(tool_name: str, pattern: str) -> None:
    """Add an auto-approve pattern for a tool.

    Examples:
        add_permission_rule("bash_execute", "nmap *")
        add_permission_rule("bash_execute", "cat *")
        add_permission_rule("file_read", "*")
    """
    rules = _load_rules()
    if tool_name not in rules:
        rules[tool_name] = []
    if pattern not in rules[tool_name]:
        rules[tool_name].append(pattern)
        _save_rules(rules)
        logger.info("Permission rule added: %s(%s)", tool_name, pattern)


def remove_permission_rule(tool_name: str, pattern: str) -> bool:
    rules = _load_rules()
    if tool_name in rules and pattern in rules[tool_name]:
        rules[tool_name].remove(pattern)
        if not rules[tool_name]:
            del rules[tool_name]
        _save_rules(rules)
        return True
    return False


def clear_permission_rules() -> None:
    rules: dict[str, list[str]] = {}
    _save_rules(rules)


def list_permission_rules() -> dict[str, list[str]]:
    return _load_rules()


def check_auto_approve(tool_name: str, detail: str) -> bool:
    """Check if a tool call matches an auto-approve pattern.

    Args:
        tool_name: The tool being called (e.g., "bash_execute").
        detail: The detail string (e.g., the command for bash_execute).

    Returns:
        True if auto-approved by a pattern, False otherwise.
    """
    rules = _load_rules()
    patterns = rules.get(tool_name, [])
    for pattern in patterns:
        if pattern == "*" or fnmatch.fnmatch(detail, pattern):
            logger.info("Auto-approved by rule: %s(%s)", tool_name, pattern)
            return True
    return False
