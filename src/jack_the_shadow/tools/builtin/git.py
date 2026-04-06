"""
Jack The Shadow — Git Command Tool

Execute git operations with risk-level gating for write operations.
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING, Any

from jack_the_shadow.tools.base import BaseTool
from jack_the_shadow.tools.helpers import result, truncate
from jack_the_shadow.utils.logger import get_logger

if TYPE_CHECKING:
    from jack_the_shadow.tools.executor import ToolExecutor

logger = get_logger("tools.git")

READ_ONLY_SUBCOMMANDS = {"status", "diff", "log", "show", "branch", "remote"}
WRITE_SUBCOMMANDS = {"add", "commit", "checkout", "stash"}


class GitCommandTool(BaseTool):
    name = "git_command"
    description = (
        "Execute git operations (status, diff, log, commit, branch, add, "
        "stash, etc.). Useful for tracking exploit development and "
        "configuration changes."
    )
    risk_aware = True

    @classmethod
    def parameters_schema(cls) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "subcommand": {
                    "type": "string",
                    "enum": [
                        "status", "diff", "log", "add", "commit",
                        "branch", "checkout", "stash", "show", "remote",
                    ],
                    "description": "The git subcommand to execute.",
                },
                "args": {
                    "type": "string",
                    "description": "Additional arguments for the subcommand.",
                },
                "message": {
                    "type": "string",
                    "description": "Commit message (required for commit subcommand).",
                },
            },
            "required": ["subcommand"],
        }


def handle_git_command(
    executor: "ToolExecutor",
    subcommand: str,
    args: str = "",
    message: str = "",
    risk_level: str = "Medium",
) -> dict[str, str]:
    if subcommand == "commit" and not message:
        return result("error", message="A commit message is required for git commit.")

    if subcommand == "commit":
        cmd = f'git commit -m "{message}"'
        if args:
            cmd = f'git commit -m "{message}" {args}'
    else:
        cmd = f"git --no-pager {subcommand}"
        if args:
            cmd = f"git --no-pager {subcommand} {args}"

    # Write operations require HITL approval; read-only operations auto-approve.
    if subcommand in WRITE_SUBCOMMANDS:
        if not executor.request_approval("git_command", cmd, risk_level):
            return result("error", message="Git command denied by operator.")
    else:
        logger.debug("auto-approved read-only git subcommand: %s", subcommand)

    try:
        proc = subprocess.run(
            cmd, shell=True,
            capture_output=True, text=True,
            timeout=30,
        )
        parts: list[str] = []
        if proc.stdout:
            parts.append(truncate(proc.stdout))
        if proc.stderr:
            parts.append(f"[stderr]\n{truncate(proc.stderr)}")
        parts.append(f"[exit_code] {proc.returncode}")
        output = "\n".join(parts)
        logger.info("git %s OK — exit=%d", subcommand, proc.returncode)
        return result("success", output=output)
    except subprocess.TimeoutExpired:
        return result("error", message="Git command timed out after 30 seconds.")
    except OSError as exc:
        return result("error", message=f"OS error: {exc}")
