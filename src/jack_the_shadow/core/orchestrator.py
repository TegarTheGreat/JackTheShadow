"""
Jack The Shadow — Orchestrator

The AI ↔ tool-call loop extracted from main.py for clean separation.
Handles multi-round tool calling, result feeding, display, and session auto-save.
Supports live AI reconnection via /login and SSE streaming.
"""

from __future__ import annotations

import json
from typing import Any, Callable, NoReturn, Optional

from jack_the_shadow.config import STREAM_RESPONSES
from jack_the_shadow.core.engine import CloudflareAI, CloudflareAIError
from jack_the_shadow.core.state import AppState
from jack_the_shadow.i18n import t
from jack_the_shadow.tools.executor import ToolExecutor
from jack_the_shadow.ui import (
    console,
    display_ai_message,
    display_error,
    display_info,
    display_user_message,
    handle_local_command,
    prompt_user,
    status_spinner,
    StreamingDisplay,
)
from jack_the_shadow.utils.logger import get_logger

logger = get_logger("core.orchestrator")

AIFactory = Callable[[str], Optional[CloudflareAI]]


def process_tool_calls(
    tool_calls: list[dict[str, Any]],
    executor: ToolExecutor,
    state: AppState,
) -> None:
    """Execute each tool call and feed results back into context."""
    for tc in tool_calls:
        call_id = tc.get("id", "unknown")
        func = tc.get("function", {})
        name = func.get("name", "")
        raw_args = func.get("arguments", "{}")

        try:
            args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
        except json.JSONDecodeError:
            args = {}
            logger.warning("Bad args for %s: %s", name, raw_args)

        console.print(
            f"\n[dim]⚙  {t('tool.call')}: "
            f"[bold]{name}[/bold]({json.dumps(args, ensure_ascii=False)[:120]})[/]"
        )

        result = executor.execute(name, args)
        result_str = json.dumps(result, ensure_ascii=False)

        icon = "✓" if result["status"] == "success" else "✖"
        style = "green" if result["status"] == "success" else "red"
        preview = result.get("output", result.get("message", ""))
        if len(preview) > 200:
            preview = preview[:200] + "..."
        console.print(f"[{style}]  {icon} {name}: {preview}[/]")

        state.add_tool_result(call_id, result_str)


def query_ai(
    ai: CloudflareAI,
    state: AppState,
    executor: ToolExecutor,
    tool_schemas: list[dict[str, Any]],
    cost_tracker: Any = None,
) -> None:
    """Run the AI query with multi-round tool calling (max 15 rounds).

    Uses SSE streaming for text-only responses when STREAM_RESPONSES is on.
    Always uses non-streaming for tool-call rounds (more reliable).
    """
    max_tool_rounds = 15

    for round_num in range(max_tool_rounds):
        state.truncate_context()
        messages = state.get_messages_for_api()

        # ── Streaming path (first round only, text responses) ─────────
        if STREAM_RESPONSES and round_num == 0:
            display = StreamingDisplay()
            try:
                assistant_msg = ai.chat_stream(
                    messages,
                    tools=tool_schemas,
                    cost_tracker=cost_tracker,
                    on_token=display.on_token,
                )
            except CloudflareAIError as exc:
                display.abort()
                display_error(str(exc))
                logger.error("AI query failed: %s", exc)
                return

            state.add_assistant_message(assistant_msg)

            tool_calls = assistant_msg.get("tool_calls")
            if tool_calls:
                # Don't show text panel for tool-call responses
                process_tool_calls(tool_calls, executor, state)
                continue

            # Pure text response — render the streamed content
            content = display.finish()
            if not content:
                content = assistant_msg.get("content", "")
                if content:
                    display_ai_message(content)
            return

        # ── Non-streaming path (tool rounds & fallback) ───────────────
        spinner_msg = (
            t("spinner.thinking") if round_num == 0
            else t("spinner.tool_result")
        )
        with status_spinner(spinner_msg):
            try:
                assistant_msg = ai.chat(
                    messages, tools=tool_schemas, cost_tracker=cost_tracker,
                )
            except CloudflareAIError as exc:
                display_error(str(exc))
                logger.error("AI query failed: %s", exc)
                return

        state.add_assistant_message(assistant_msg)

        tool_calls = assistant_msg.get("tool_calls")
        if tool_calls:
            process_tool_calls(tool_calls, executor, state)
            continue

        content = assistant_msg.get("content", "")
        if content:
            display_ai_message(content)
        return

    display_error(t("tool.max_rounds", limit=max_tool_rounds))
    logger.warning("Tool-call loop hit max rounds (%d)", max_tool_rounds)


def _auto_save_session(state: AppState) -> None:
    """Auto-save the session on exit."""
    try:
        from jack_the_shadow.session.history import save_session
        if state.context_messages:
            path = save_session(state)
            if path:
                console.print(f"[dim]  Session saved → {path}[/]")
    except Exception as exc:
        logger.warning("Auto-save failed: %s", exc)


def _resume_session(session_id: str, state: AppState) -> None:
    """Load a previous session into current state."""
    from jack_the_shadow.session.history import load_session

    data = load_session(session_id)
    if data is None:
        display_error(f"Session '{session_id}' not found.")
        return

    meta = data["metadata"]
    messages = data["messages"]

    if meta.get("target"):
        state.target = meta["target"]
    state.context_messages = messages
    display_info(
        f"Resumed session: {meta.get('date', '?')} — "
        f"{len(messages)} messages, target: {meta.get('target', '(none)')}"
    )


def main_loop(
    state: AppState,
    ai: CloudflareAI | None,
    executor: ToolExecutor,
    tool_schemas: list[dict[str, Any]],
    tool_names: list[str],
    ai_factory: AIFactory | None = None,
    cost_tracker: Any = None,
) -> NoReturn:
    """The main interactive prompt loop.

    Args:
        ai_factory: Optional callable(model) -> CloudflareAI for reconnecting
                    after /login without restarting.
        cost_tracker: Optional CostTracker instance for API usage tracking.
    """
    while True:
        try:
            user_input = prompt_user()
        except SystemExit:
            _auto_save_session(state)
            raise

        if not user_input:
            continue

        if user_input.startswith("/"):
            was_login = user_input.strip().lower().startswith("/login")
            cmd_result = handle_local_command(user_input, state, tool_names, executor, cost_tracker)

            # Handle /history resume
            if isinstance(cmd_result, tuple) and cmd_result[0] == "resume":
                _resume_session(cmd_result[1], state)
                continue

            # Live reconnect after /login
            if was_login and ai is None and ai_factory is not None:
                new_ai = ai_factory(state.model)
                if new_ai is not None:
                    ai = new_ai
                    display_info(t("auth.connected"))
            continue

        display_user_message(user_input)
        state.add_message("user", user_input)

        if ai is None:
            display_error(t("offline.hint"))
        else:
            try:
                query_ai(ai, state, executor, tool_schemas, cost_tracker)
            except KeyboardInterrupt:
                console.print("\n[dim]  ⚡ Interrupted — back to prompt.[/]")
                logger.info("User interrupted AI query with Ctrl+C")
