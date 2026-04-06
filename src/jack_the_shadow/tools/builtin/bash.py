"""
Jack The Shadow — Bash Execute Tool

Run shell commands with risk-level gating.
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING, Any

from jack_the_shadow.config import COMMAND_TIMEOUT
from jack_the_shadow.i18n import t
from jack_the_shadow.tools.base import BaseTool
from jack_the_shadow.tools.helpers import result, truncate
from jack_the_shadow.utils.logger import get_logger

if TYPE_CHECKING:
    from jack_the_shadow.tools.executor import ToolExecutor

logger = get_logger("tools.bash")


class BashExecuteTool(BaseTool):
    name = "bash_execute"
    description = (
        "Execute a shell command on the operator's machine and return "
        "stdout/stderr.  Always classify risk_level honestly."
    )
    risk_aware = True

    @classmethod
    def parameters_schema(cls) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute.",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds (default: 120).",
                },
            },
            "required": ["command"],
        }


def handle_bash_execute(
    executor: "ToolExecutor",
    command: str,
    risk_level: str = "Medium",
    timeout: int = COMMAND_TIMEOUT,
) -> dict[str, str]:
    if not executor.request_approval("bash_execute", command, risk_level):
        return result("error", message=t("tool.denied"))

    try:
        proc = subprocess.run(
            command, shell=True,
            capture_output=True, text=True,
            timeout=min(timeout, 300),
        )
        parts: list[str] = []
        if proc.stdout:
            parts.append(f"[stdout]\n{truncate(proc.stdout)}")
        if proc.stderr:
            parts.append(f"[stderr]\n{truncate(proc.stderr)}")
        parts.append(f"[exit_code] {proc.returncode}")
        output = "\n".join(parts)
        logger.info("bash OK — exit=%d", proc.returncode)
        return result("success", output=output)
    except subprocess.TimeoutExpired:
        return result("error", message=t("tool.timeout", timeout=timeout))
    except OSError as exc:
        return result("error", message=f"OS error: {exc}")
