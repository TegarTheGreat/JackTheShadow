"""
Jack The Shadow — Permission System

5-layer permission cascade inspired by claude-code:
1. Tool-level (read_only tools always allowed)
2. Deny rules (fail-closed — explicit blocks)
3. Allow rules (glob patterns for auto-approve)
4. YOLO mode (global auto-approve)
5. Manual prompt (ask user)
"""

from __future__ import annotations

import fnmatch
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from jack_the_shadow.session.paths import JSHADOW_DIR
from jack_the_shadow.utils.logger import get_logger

logger = get_logger("core.permissions")

PERMISSIONS_FILE = JSHADOW_DIR / "permissions.json"


@dataclass
class PermissionDecision:
    """Result of a permission check."""
    behavior: Literal["allow", "deny", "ask"]
    reason: str  # human-readable explanation
    source: str  # "tool_level" | "deny_rule" | "allow_rule" | "yolo" | "user"


def _load_rules() -> dict[str, Any]:
    """Load permission rules from disk.

    Format: {"allow": {"tool": ["pattern"]}, "deny": {"tool": ["pattern"]}}
    Also supports legacy format: {"tool": ["pattern"]} (treated as allow).
    """
    if PERMISSIONS_FILE.exists():
        try:
            data = json.loads(PERMISSIONS_FILE.read_text())
            # Migrate legacy format
            if data and "allow" not in data and "deny" not in data:
                return {"allow": data, "deny": {}}
            return data
        except (json.JSONDecodeError, OSError):
            pass
    return {"allow": {}, "deny": {}}


def _save_rules(rules: dict[str, Any]) -> None:
    PERMISSIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    PERMISSIONS_FILE.write_text(json.dumps(rules, indent=2))


def add_permission_rule(tool_name: str, pattern: str, *, deny: bool = False) -> None:
    """Add an auto-approve (or deny) pattern for a tool.

    Examples:
        add_permission_rule("bash_execute", "nmap *")
        add_permission_rule("bash_execute", "rm -rf *", deny=True)
    """
    rules = _load_rules()
    section = "deny" if deny else "allow"
    if section not in rules:
        rules[section] = {}
    if tool_name not in rules[section]:
        rules[section][tool_name] = []
    if pattern not in rules[section][tool_name]:
        rules[section][tool_name].append(pattern)
        _save_rules(rules)
        logger.info("Permission %s rule added: %s(%s)", section, tool_name, pattern)


def remove_permission_rule(tool_name: str, pattern: str, *, deny: bool = False) -> bool:
    rules = _load_rules()
    section = "deny" if deny else "allow"
    sec = rules.get(section, {})
    if tool_name in sec and pattern in sec[tool_name]:
        sec[tool_name].remove(pattern)
        if not sec[tool_name]:
            del sec[tool_name]
        _save_rules(rules)
        return True
    return False


def clear_permission_rules() -> None:
    _save_rules({"allow": {}, "deny": {}})


def list_permission_rules() -> dict[str, list[str]]:
    """Return allow rules (for backward compatibility with /permissions list)."""
    rules = _load_rules()
    return rules.get("allow", {})


def list_deny_rules() -> dict[str, list[str]]:
    rules = _load_rules()
    return rules.get("deny", {})


def check_permission(
    tool_name: str,
    detail: str,
    *,
    yolo_mode: bool = False,
    read_only: bool = False,
) -> PermissionDecision:
    """5-layer permission cascade.

    Args:
        tool_name: The tool being called.
        detail: The detail string (command, filepath, etc.).
        yolo_mode: Whether global auto-approve is on.
        read_only: Whether the tool is read-only (always allowed).

    Returns:
        PermissionDecision with behavior and reason.
    """
    # Layer 1: Read-only tools always allowed
    if read_only:
        return PermissionDecision("allow", "Read-only tool", "tool_level")

    rules = _load_rules()

    # Layer 2: Deny rules (fail-closed)
    deny_patterns = rules.get("deny", {}).get(tool_name, [])
    for pattern in deny_patterns:
        if pattern == "*" or fnmatch.fnmatch(detail, pattern):
            logger.warning("DENIED by rule: %s(%s)", tool_name, pattern)
            return PermissionDecision(
                "deny",
                f"Blocked by deny rule: {tool_name}({pattern})",
                "deny_rule",
            )

    # Layer 3: Allow rules (explicit auto-approve)
    allow_patterns = rules.get("allow", {}).get(tool_name, [])
    for pattern in allow_patterns:
        if pattern == "*" or fnmatch.fnmatch(detail, pattern):
            logger.info("Auto-approved by rule: %s(%s)", tool_name, pattern)
            return PermissionDecision(
                "allow",
                f"Auto-approved: {tool_name}({pattern})",
                "allow_rule",
            )

    # Layer 4: YOLO mode
    if yolo_mode:
        return PermissionDecision("allow", "YOLO mode active", "yolo")

    # Layer 5: Ask user
    return PermissionDecision("ask", "Manual approval required", "user")


# Backward-compatible alias
def check_auto_approve(tool_name: str, detail: str) -> bool:
    """Check if a tool call matches an auto-approve pattern (legacy API)."""
    decision = check_permission(tool_name, detail)
    return decision.behavior == "allow"
