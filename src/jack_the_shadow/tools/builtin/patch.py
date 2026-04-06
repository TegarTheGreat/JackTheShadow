"""
Jack The Shadow — Apply Patch Tool

Apply a unified diff patch to one or more files.
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

logger = get_logger("tools.patch")


class ApplyPatchTool(BaseTool):
    name = "apply_patch"
    description = (
        "Apply a unified diff patch to one or more files. Useful for "
        "applying exploit patches, configuration changes, or code modifications."
    )
    risk_aware = True

    @classmethod
    def parameters_schema(cls) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "patch_content": {
                    "type": "string",
                    "description": "The patch in unified diff format.",
                },
                "strip_level": {
                    "type": "integer",
                    "description": "Strip level for patch paths (default: 1, equivalent to patch -p1).",
                },
            },
            "required": ["patch_content"],
        }


def handle_apply_patch(
    executor: "ToolExecutor",
    patch_content: str,
    risk_level: str = "High",
    strip_level: int = 1,
) -> dict[str, str]:
    preview = truncate(patch_content, 2000)
    if not executor.request_approval("apply_patch", preview, risk_level):
        return result("error", message="Patch application denied.")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".patch", delete=False) as f:
        f.write(patch_content)
        tmppath = f.name

    try:
        # Dry run first
        dry = subprocess.run(
            ["patch", f"-p{strip_level}", "--dry-run", "-i", tmppath],
            capture_output=True, text=True, timeout=30,
        )
        if dry.returncode != 0:
            return result(
                "error",
                message=f"Dry-run failed:\n{dry.stderr or dry.stdout}",
            )

        # Apply for real
        proc = subprocess.run(
            ["patch", f"-p{strip_level}", "-i", tmppath],
            capture_output=True, text=True, timeout=30,
        )
        output = proc.stdout
        if proc.stderr:
            output += f"\n[stderr] {proc.stderr}"
        logger.info("patch applied — exit=%d", proc.returncode)
        return result("success", output=truncate(output))
    except FileNotFoundError:
        return result(
            "error",
            message="'patch' command not found. Install with: apt install patch",
        )
    except subprocess.TimeoutExpired:
        return result("error", message="Patch operation timed out.")
    finally:
        os.unlink(tmppath)
