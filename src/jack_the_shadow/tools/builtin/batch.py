"""
Jack The Shadow — Batch Parallel Execution Tool

Execute multiple tool calls in parallel.
"""

from __future__ import annotations

import concurrent.futures
from typing import TYPE_CHECKING, Any

from jack_the_shadow.tools.base import BaseTool
from jack_the_shadow.tools.helpers import result, truncate
from jack_the_shadow.utils.logger import get_logger

if TYPE_CHECKING:
    from jack_the_shadow.tools.executor import ToolExecutor

logger = get_logger("tools.batch")


class BatchExecuteTool(BaseTool):
    name = "batch_execute"
    description = (
        "Execute multiple tool calls in parallel. Useful for running "
        "recon tools simultaneously (e.g., nmap + whatweb + dirb at once)."
    )
    risk_aware = True

    @classmethod
    def parameters_schema(cls) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "calls": {
                    "type": "array",
                    "description": "List of tool calls to execute in parallel.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "tool_name": {
                                "type": "string",
                                "description": "Name of the tool to invoke.",
                            },
                            "arguments": {
                                "type": "object",
                                "description": "Arguments to pass to the tool.",
                            },
                        },
                        "required": ["tool_name", "arguments"],
                    },
                    "maxItems": 10,
                },
            },
            "required": ["calls"],
        }


def handle_batch_execute(
    executor: "ToolExecutor",
    calls: list[dict[str, Any]],
    risk_level: str = "High",
) -> dict[str, str]:
    summary = ", ".join(c["tool_name"] for c in calls)
    detail = "\n".join(
        f"  [{i + 1}] {c['tool_name']}({c.get('arguments', {})})"
        for i, c in enumerate(calls)
    )

    if not executor.request_approval(
        "batch_execute", f"{len(calls)} calls: {summary}\n{detail}", risk_level
    ):
        return result("error", message="Batch execution denied.")

    results: dict[int, dict[str, str]] = {}

    def run_one(idx: int, call: dict[str, Any]) -> tuple[int, dict[str, str]]:
        try:
            return idx, executor.execute(call["tool_name"], call["arguments"])
        except Exception as e:
            logger.error("batch call %d (%s) failed: %s", idx, call["tool_name"], e)
            return idx, result("error", message=str(e))

    # Temporarily enable yolo so individual tools don't re-prompt
    old_yolo = executor.state.yolo_mode
    executor.state.yolo_mode = True
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
            futures = [pool.submit(run_one, i, c) for i, c in enumerate(calls)]
            for f in concurrent.futures.as_completed(futures):
                idx, res = f.result()
                results[idx] = res
    finally:
        executor.state.yolo_mode = old_yolo

    # Format output
    parts = []
    for i in sorted(results):
        r = results[i]
        body = r.get("output", "") or r.get("message", "")
        parts.append(f"--- [{calls[i]['tool_name']}] status={r['status']} ---\n{body}")

    logger.info("batch finished — %d/%d succeeded",
                sum(1 for r in results.values() if r["status"] == "success"),
                len(calls))
    return result("success", output=truncate("\n\n".join(parts)))
