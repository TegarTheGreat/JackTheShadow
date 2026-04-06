"""
Jack The Shadow — MCP Call Tool

Schema definition and handler for calling MCP server tools.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from jack_the_shadow.i18n import t
from jack_the_shadow.tools.base import BaseTool
from jack_the_shadow.tools.helpers import result, truncate
from jack_the_shadow.utils.logger import get_logger

if TYPE_CHECKING:
    from jack_the_shadow.tools.executor import ToolExecutor

logger = get_logger("tools.mcp.tool")


class MCPCallTool(BaseTool):
    name = "mcp_call"
    description = (
        "Call a tool on a connected MCP (Model Context Protocol) server.  "
        "MCP servers expose external tools, APIs, and data sources.  "
        "Use /mcp command to manage MCP server connections."
    )
    risk_aware = True

    @classmethod
    def parameters_schema(cls) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "server_name": {
                    "type": "string",
                    "description": "Name of the MCP server to call.",
                },
                "tool_name": {
                    "type": "string",
                    "description": "Name of the tool on the MCP server.",
                },
                "arguments": {
                    "type": "object",
                    "description": "Arguments to pass to the MCP tool.",
                },
            },
            "required": ["server_name", "tool_name"],
        }


def handle_mcp_call(
    executor: "ToolExecutor",
    server_name: str,
    tool_name: str,
    arguments: dict[str, Any] | None = None,
    risk_level: str = "Medium",
) -> dict[str, str]:
    detail = (
        f"MCP:{server_name}/{tool_name}"
        f"({json.dumps(arguments or {}, ensure_ascii=False)[:100]})"
    )
    if not executor.request_approval("mcp_call", detail, risk_level):
        return result("error", message=t("tool.denied"))

    res = executor.mcp.call_tool(server_name, tool_name, arguments or {})

    if "error" in res:
        return result("error", message=res["error"])

    output = res.get("output", "")
    is_error = res.get("is_error", False)
    status = "error" if is_error else "success"
    return result(status, output=truncate(output))
