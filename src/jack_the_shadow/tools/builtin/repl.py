"""
Jack The Shadow — Python REPL Tool

Execute Python code in an isolated subprocess.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from typing import TYPE_CHECKING, Any

from jack_the_shadow.tools.base import BaseTool
from jack_the_shadow.tools.helpers import result, truncate
from jack_the_shadow.utils.logger import get_logger

if TYPE_CHECKING:
    from jack_the_shadow.tools.executor import ToolExecutor

logger = get_logger("tools.repl")


class ReplTool(BaseTool):
    name = "python_repl"
    description = (
        "Execute Python code in an interactive session. Useful for quick "
        "exploit prototyping, data processing, encoding/decoding, and "
        "pwntools usage."
    )
    risk_aware = True

    @classmethod
    def parameters_schema(cls) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code to execute.",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds (default: 30).",
                },
            },
            "required": ["code"],
        }


def handle_python_repl(
    executor: "ToolExecutor",
    code: str,
    risk_level: str = "Medium",
    timeout: int = 30,
) -> dict[str, str]:
    preview = truncate(code, 2000)
    if not executor.request_approval("python_repl", preview, risk_level):
        return result("error", message="REPL execution denied.")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        tmppath = f.name

    try:
        proc = subprocess.run(
            ["python3", tmppath],
            capture_output=True, text=True,
            timeout=min(timeout, 120),
        )
        parts: list[str] = []
        if proc.stdout:
            parts.append(proc.stdout)
        if proc.stderr:
            parts.append(f"[stderr]\n{proc.stderr}")
        parts.append(f"[exit_code] {proc.returncode}")
        logger.info("python_repl OK — exit=%d", proc.returncode)
        return result("success", output=truncate("\n".join(parts)))
    except subprocess.TimeoutExpired:
        return result("error", message=f"Python execution timed out after {timeout}s.")
    except OSError as exc:
        return result("error", message=f"OS error: {exc}")
    finally:
        os.unlink(tmppath)
