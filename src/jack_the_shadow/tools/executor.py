"""
Jack The Shadow — Tool Executor with HITL Interceptor

Dispatches tool calls to their concrete implementations and enforces
human-in-the-loop approval (unless YOLO mode is active).
"""

from __future__ import annotations

from typing import Any, Optional

from jack_the_shadow.core.state import AppState
from jack_the_shadow.i18n import t
from jack_the_shadow.tools.helpers import result
from jack_the_shadow.tools.mcp.client import MCPManager
from jack_the_shadow.ui.panels import display_yolo_auto_approve, prompt_approval
from jack_the_shadow.utils.logger import get_logger

logger = get_logger("tools.executor")


class ToolExecutor:
    """Dispatches and executes tool calls with HITL gating."""

    def __init__(self, state: AppState, mcp_manager: Optional[MCPManager] = None) -> None:
        self.state = state
        self.mcp = mcp_manager or MCPManager()

        # Import handlers lazily to avoid circular imports
        from jack_the_shadow.tools.builtin.bash import handle_bash_execute
        from jack_the_shadow.tools.builtin.cve import handle_cve_lookup
        from jack_the_shadow.tools.builtin.directory import handle_list_directory
        from jack_the_shadow.tools.builtin.files import (
            handle_file_edit,
            handle_file_read,
            handle_file_write,
        )
        from jack_the_shadow.tools.builtin.http import handle_http_request
        from jack_the_shadow.tools.builtin.search import handle_glob_find, handle_grep_search
        from jack_the_shadow.tools.builtin.web_fetch import handle_web_fetch
        from jack_the_shadow.tools.builtin.web_search import handle_web_search
        from jack_the_shadow.tools.mcp.tool import handle_mcp_call

        self._dispatch: dict[str, Any] = {
            "bash_execute": handle_bash_execute,
            "file_read": handle_file_read,
            "file_write": handle_file_write,
            "file_edit": handle_file_edit,
            "grep_search": handle_grep_search,
            "glob_find": handle_glob_find,
            "list_directory": handle_list_directory,
            "http_request": handle_http_request,
            "web_fetch": handle_web_fetch,
            "web_search": handle_web_search,
            "cve_lookup": handle_cve_lookup,
            "mcp_call": handle_mcp_call,
        }

    def execute(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, str]:
        logger.info("Executing tool: %s args=%s", tool_name, arguments)
        handler = self._dispatch.get(tool_name)
        if handler is None:
            msg = f"Unknown tool: {tool_name}"
            logger.error(msg)
            return result("error", message=msg)
        try:
            return handler(self, **arguments)
        except TypeError as exc:
            msg = f"Invalid arguments for {tool_name}: {exc}"
            logger.error(msg)
            return result("error", message=msg)

    def request_approval(self, action: str, detail: str, risk_level: str) -> bool:
        """HITL interceptor — checks YOLO mode, then prompts user."""
        if self.state.yolo_mode:
            display_yolo_auto_approve(action)
            logger.info("YOLO auto-approved: %s [%s]", action, risk_level)
            return True
        return prompt_approval(action, detail, risk_level)
