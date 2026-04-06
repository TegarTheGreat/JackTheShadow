"""
Jack The Shadow — Bash Execute Tool

Run shell commands with risk-level gating.
Supports both blocking (default) and background/daemon mode.
"""

from __future__ import annotations

import os
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
        "stdout/stderr.  Set background=true for daemon/long-running processes "
        "(e.g., gsocket deploy, reverse shells, servers).  "
        "Always classify risk_level honestly."
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
                    "description": "Timeout in seconds (default: 120, max: 600).",
                },
                "background": {
                    "type": "boolean",
                    "description": (
                        "Run command in background (detached). Use for daemon "
                        "processes, reverse shells, gsocket deploy, servers, "
                        "or anything that should persist. Returns PID immediately."
                    ),
                },
            },
            "required": ["command"],
        }


def handle_bash_execute(
    executor: "ToolExecutor",
    command: str,
    risk_level: str = "Medium",
    timeout: int = COMMAND_TIMEOUT,
    background: bool = False,
) -> dict[str, str]:
    if not executor.request_approval("bash_execute", command, risk_level):
        return result("error", message=t("tool.denied"))

    if background:
        return _run_background(command)
    return _run_blocking(command, timeout)


def _run_blocking(command: str, timeout: int) -> dict[str, str]:
    """Run command and wait for completion (default mode)."""
    try:
        proc = subprocess.run(
            command, shell=True,
            capture_output=True, text=True,
            timeout=min(timeout, 600),
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


def _run_background(command: str) -> dict[str, str]:
    """Launch command as a detached background process.

    Used for daemon processes like gsocket deploy, reverse shells,
    servers, or any long-running task that should persist independently.
    Returns PID and any immediate output (first 2 seconds).
    """
    try:
        proc = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            text=True,
            start_new_session=True,  # Detach from parent process group
        )

        # Wait briefly to capture early output (deploy scripts print secrets)
        try:
            stdout, stderr = proc.communicate(timeout=3)
        except subprocess.TimeoutExpired:
            # Process is still running (expected for daemons)
            stdout = ""
            stderr = ""
            try:
                # Read any available output without blocking
                if proc.stdout:
                    import select
                    if select.select([proc.stdout], [], [], 0)[0]:
                        stdout = proc.stdout.read(4096) or ""
                if proc.stderr:
                    if select.select([proc.stderr], [], [], 0)[0]:
                        stderr = proc.stderr.read(4096) or ""
            except Exception:
                pass

        parts: list[str] = [f"[background] PID={proc.pid}"]
        if proc.poll() is not None:
            parts.append(f"[exit_code] {proc.returncode}")
        else:
            parts.append("[status] running (detached)")

        if stdout:
            parts.append(f"[stdout]\n{truncate(stdout)}")
        if stderr:
            parts.append(f"[stderr]\n{truncate(stderr)}")

        output = "\n".join(parts)
        logger.info("bash background — PID=%d cmd=%s", proc.pid, command[:80])
        return result("success", output=output)

    except OSError as exc:
        return result("error", message=f"OS error launching background process: {exc}")
