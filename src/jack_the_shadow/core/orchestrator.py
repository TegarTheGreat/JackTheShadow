"""
Jack The Shadow — Orchestrator

The AI ↔ tool-call loop extracted from main.py for clean separation.
Handles multi-round tool calling, result feeding, and display.
"""

from __future__ import annotations

import json
from typing import Any, NoReturn

from jack_the_shadow.core.engine import CloudflareAI, CloudflareAIError
from jack_the_shadow.core.state import AppState
from jack_the_shadow.i18n import t
from jack_the_shadow.tools.executor import ToolExecutor
from jack_the_shadow.ui import (
    console,
    display_ai_message,
    display_error,
    display_user_message,
    handle_local_command,
    prompt_user,
    status_spinner,
)
from jack_the_shadow.utils.logger import get_logger

logger = get_logger("core.orchestrator")


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
) -> None:
    """Run the AI query with multi-round tool calling (max 15 rounds)."""
    max_tool_rounds = 15

    for round_num in range(max_tool_rounds):
        state.truncate_context()
        messages = state.get_messages_for_api()

        spinner_msg = (
            t("spinner.thinking") if round_num == 0
            else t("spinner.tool_result")
        )
        with status_spinner(spinner_msg):
            try:
                assistant_msg = ai.chat(messages, tools=tool_schemas)
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


def main_loop(
    state: AppState,
    ai: CloudflareAI | None,
    executor: ToolExecutor,
    tool_schemas: list[dict[str, Any]],
    tool_names: list[str],
) -> NoReturn:
    """The main interactive prompt loop."""
    while True:
        user_input = prompt_user()

        if not user_input:
            continue

        if user_input.startswith("/"):
            handle_local_command(user_input, state, tool_names, executor)
            continue

        display_user_message(user_input)
        state.add_message("user", user_input)

        if ai is None:
            with status_spinner():
                ai_response = t(
                    "offline.response",
                    input=user_input,
                    target=state.target,
                )
            state.add_message("assistant", ai_response)
            display_ai_message(ai_response)
        else:
            query_ai(ai, state, executor, tool_schemas)
