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
        from jack_the_shadow.tools.builtin.ask import handle_ask_user
        from jack_the_shadow.tools.builtin.bash import handle_bash_execute
        from jack_the_shadow.tools.builtin.batch import handle_batch_execute
        from jack_the_shadow.tools.builtin.cve import handle_cve_lookup
        from jack_the_shadow.tools.builtin.directory import handle_list_directory
        from jack_the_shadow.tools.builtin.doctor import handle_doctor_check
        from jack_the_shadow.tools.builtin.exploit_search import handle_exploit_search
        from jack_the_shadow.tools.builtin.files import (
            handle_file_edit,
            handle_file_read,
            handle_file_write,
        )
        from jack_the_shadow.tools.builtin.git import handle_git_command
        from jack_the_shadow.tools.builtin.http import handle_http_request
        from jack_the_shadow.tools.builtin.memory import handle_memory_read, handle_memory_write
        from jack_the_shadow.tools.builtin.network import handle_network_recon
        from jack_the_shadow.tools.builtin.patch import handle_apply_patch
        from jack_the_shadow.tools.builtin.repl import handle_python_repl
        from jack_the_shadow.tools.builtin.report import handle_report_generate
        from jack_the_shadow.tools.builtin.search import handle_glob_find, handle_grep_search
        from jack_the_shadow.tools.builtin.todo import handle_todo_read, handle_todo_write
        from jack_the_shadow.tools.builtin.web_fetch import handle_web_fetch
        from jack_the_shadow.tools.builtin.web_search import handle_web_search
        from jack_the_shadow.tools.builtin.wordlist import handle_wordlist_manage
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
            "memory_read": handle_memory_read,
            "memory_write": handle_memory_write,
            "network_recon": handle_network_recon,
            "todo_read": handle_todo_read,
            "todo_write": handle_todo_write,
            "git_command": handle_git_command,
            "doctor_check": handle_doctor_check,
            "batch_execute": handle_batch_execute,
            "apply_patch": handle_apply_patch,
            "python_repl": handle_python_repl,
            "report_generate": handle_report_generate,
            "ask_user": handle_ask_user,
            "mcp_call": handle_mcp_call,
            "exploit_search": handle_exploit_search,
            "wordlist_manage": handle_wordlist_manage,
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
        """HITL interceptor — checks permission patterns, YOLO mode, then prompts user."""
        from jack_the_shadow.core.permissions import check_auto_approve

        if check_auto_approve(action, detail):
            logger.info("Auto-approved by permission rule: %s", action)
            return True
        if self.state.yolo_mode:
            display_yolo_auto_approve(action)
            logger.info("YOLO auto-approved: %s [%s]", action, risk_level)
            return True
        return prompt_approval(action, detail, risk_level)
