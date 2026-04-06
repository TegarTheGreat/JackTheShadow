"""
Jack The Shadow — Orchestrator

The AI ↔ tool-call loop extracted from main.py for clean separation.
Handles multi-round tool calling, result feeding, display, and session auto-save.
Supports live AI reconnection via /login, SSE streaming, and session resume.
"""

from __future__ import annotations

import json
import select
import sys
import threading
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
from jack_the_shadow.ui.phases import Phase, get_phase_indicator
from rich.text import Text
from jack_the_shadow.utils.logger import get_logger

logger = get_logger("core.orchestrator")

AIFactory = Callable[[str], Optional[CloudflareAI]]


def process_tool_calls(
    tool_calls: list[dict[str, Any]],
    executor: ToolExecutor,
    state: AppState,
) -> None:
    """Execute each tool call and feed results back into context.

    After execution, analyzes results and injects follow-up intelligence
    hints so the AI knows what to do next without guessing.
    """
    from jack_the_shadow.core.methodology import analyze_results, format_suggestions

    indicator = get_phase_indicator()
    all_suggestions: list[str] = []

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

        args_preview = json.dumps(args, ensure_ascii=False)[:120]
        console.print(
            Text.assemble(
                ("\n⚙  ", "dim"),
                (f"{t('tool.call')}: ", "dim"),
                (name, "dim bold"),
                (f"({args_preview})", "dim"),
            )
        )

        indicator.set(Phase.TOOL_USE, name)

        try:
            tool_result = executor.execute(name, args)
        except Exception as exc:
            logger.exception("Tool %s crashed", name)
            tool_result = {"status": "error", "output": "", "message": f"{name} crashed: {exc}"}

        result_str = json.dumps(tool_result, ensure_ascii=False)

        # Format tool output — compact for success, detailed for errors
        icon = "✓" if tool_result["status"] == "success" else "✖"
        style = "green" if tool_result["status"] == "success" else "red"
        # Use `or` chain — result() always sets output="" even for errors
        preview = tool_result.get("output", "") or tool_result.get("message", "")

        # Show tool output (use Text to prevent Rich markup interpretation)
        lines = preview.strip().split("\n") if preview.strip() else []
        if len(lines) > 8:
            visible = "\n".join(lines[:6])
            visible += f"\n  ... +{len(lines) - 6} more lines"
            console.print(Text(f"  {icon} {name}:", style=style))
            console.print(Text(visible, style="dim"))
        elif len(preview) > 300:
            console.print(Text(f"  {icon} {name}: {preview[:300]}...", style=style))
        elif preview:
            console.print(Text(f"  {icon} {name}: {preview}", style=style))
        else:
            console.print(Text(f"  {icon} {name}", style=style))

        state.add_tool_result(call_id, result_str)

        # Analyze results for follow-up intelligence
        if tool_result.get("status") == "success":
            suggestions = analyze_results(name, args, tool_result)
            all_suggestions.extend(suggestions)

    # Inject intelligence hints as system guidance
    if all_suggestions:
        intel = format_suggestions(all_suggestions, state.language)
        state.add_message("system", intel)
        logger.info("Injected %d intelligence hints", len(all_suggestions))


def _filter_schemas_for_phase(
    all_schemas: list[dict[str, Any]],
    phase: str,
) -> list[dict[str, Any]]:
    """Return only tool schemas relevant to the current pentest phase.

    Reduces context token usage and helps the model focus on applicable tools.
    """
    from jack_the_shadow.core.methodology import get_phase_tools

    allowed = get_phase_tools(phase)

    # If the allowed set covers nearly everything, just return all
    if len(allowed) >= 25:
        return all_schemas

    return [
        s for s in all_schemas
        if s.get("function", {}).get("name", "") in allowed
    ]


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
    Applies phase-aware tool filtering to reduce token usage.
    """
    max_tool_rounds = 15
    indicator = get_phase_indicator()
    indicator.show()
    active_schemas = _filter_schemas_for_phase(tool_schemas, state.phase)

    for round_num in range(max_tool_rounds):
        # Warn AI when approaching round limit
        if round_num == max_tool_rounds - 2:
            state.add_message(
                "system",
                "⚠ You have 2 tool-call rounds remaining. "
                "Summarize findings and wrap up."
            )

        messages = state.get_messages_for_api()

        # ── Streaming path (first round only, text responses) ─────────
        if STREAM_RESPONSES and round_num == 0:
            indicator.set(Phase.THINKING)
            display = StreamingDisplay()
            try:
                assistant_msg = ai.chat_stream(
                    messages,
                    tools=active_schemas,
                    cost_tracker=cost_tracker,
                    on_token=display.on_token,
                )
            except CloudflareAIError as exc:
                indicator.set(Phase.ERROR, str(exc))
                indicator.hide()
                display.abort()
                display_error(str(exc))
                logger.error("AI query failed: %s", exc)
                return

            state.add_assistant_message(assistant_msg)

            tool_calls = assistant_msg.get("tool_calls")
            if tool_calls:
                indicator.set(Phase.TOOL_INPUT)
                process_tool_calls(tool_calls, executor, state)
                continue

            # Pure text response — render the streamed content
            content = display.finish()
            if not content:
                content = assistant_msg.get("content", "")
                if content:
                    display_ai_message(content)
            indicator.set(Phase.DONE)
            indicator.hide()
            return

        # ── Non-streaming path (tool rounds & fallback) ───────────────
        indicator.set(Phase.THINKING if round_num == 0 else Phase.TOOL_INPUT)
        spinner_msg = (
            t("spinner.thinking") if round_num == 0
            else t("spinner.tool_result")
        )
        with status_spinner(spinner_msg):
            try:
                assistant_msg = ai.chat(
                    messages, tools=active_schemas, cost_tracker=cost_tracker,
                )
            except CloudflareAIError as exc:
                indicator.set(Phase.ERROR, str(exc))
                indicator.hide()
                display_error(str(exc))
                logger.error("AI query failed: %s", exc)
                return

        state.add_assistant_message(assistant_msg)

        tool_calls = assistant_msg.get("tool_calls")
        if tool_calls:
            process_tool_calls(tool_calls, executor, state)
            continue

        content = assistant_msg.get("content", "")
        # After tool rounds, suppress the placeholder "no response" text —
        # tool output already served as the response.
        is_placeholder = content == t("ai.empty_response")
        if content and not (is_placeholder and round_num > 0):
            display_ai_message(content)
        indicator.set(Phase.DONE)
        indicator.hide()
        return

    indicator.hide()
    display_error(t("tool.max_rounds", limit=max_tool_rounds))
    logger.warning("Tool-call loop hit max rounds (%d)", max_tool_rounds)


def _drain_stdin_queue() -> list[str]:
    """Drain any input the user typed while AI was executing.

    Uses non-blocking select on stdin (Linux). Returns lines typed,
    or empty list if nothing was queued.
    """
    queued: list[str] = []
    try:
        while True:
            ready, _, _ = select.select([sys.stdin], [], [], 0)
            if not ready:
                break
            line = sys.stdin.readline()
            if not line:
                break
            stripped = line.strip()
            if stripped:
                queued.append(stripped)
    except (OSError, ValueError):
        pass
    return queued


def _auto_save_session(state: AppState) -> None:
    """Finalize the active SessionWriter or do a one-shot save as fallback."""
    try:
        writer = getattr(state, "_session_writer", None)
        if writer is not None:
            path = writer.finalize(state)
            if path:
                console.print(f"\n[dim]  Session saved → {path}[/]")
            return

        # Fallback: no writer (old path or crash before writer init)
        from jack_the_shadow.session.history import save_session
        if state.context_messages:
            path = save_session(state)
            if path:
                console.print(f"\n[dim]  Session saved → {path}[/]")
    except Exception as exc:
        logger.warning("Auto-save failed: %s", exc)
        console.print(f"[yellow dim]  ⚠ Session save failed: {exc}[/]")


def _resume_session(session_id: str, state: AppState) -> bool:
    """Load a previous session into current state.

    Restores ALL state: target, model, language, phase, yolo_mode, messages.
    Returns True if resume succeeded.
    """
    from rich.panel import Panel
    from rich.table import Table

    from jack_the_shadow.i18n import set_language
    from jack_the_shadow.session.history import load_session

    data = load_session(session_id)
    if data is None:
        display_error(f"Session '{session_id}' not found.")
        return False

    meta = data["metadata"]
    messages = data["messages"]

    if not messages:
        display_error("Session is empty — nothing to resume.")
        return False

    # Restore full state from metadata
    state.restore_from_metadata(meta)
    state.context_messages = messages

    # Sync language if changed
    if meta.get("language") and meta["language"] != state.language:
        set_language(meta["language"])

    # Display resume summary panel
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="dim")
    table.add_column(style="bold")
    table.add_row("Session", meta.get("session_id", session_id))
    table.add_row("Date", meta.get("date", "?"))
    table.add_row("Target", meta.get("target") or "(none)")
    table.add_row("Model", meta.get("model", "?"))
    table.add_row("Phase", meta.get("phase", "recon"))
    table.add_row("Messages", str(len(messages)))
    if meta.get("tool_count"):
        table.add_row("Tool calls", str(meta["tool_count"]))
    if meta.get("duration_seconds"):
        dur = meta["duration_seconds"]
        table.add_row("Duration", f"{int(dur // 60)}m {int(dur % 60)}s")
    if meta.get("yolo_mode"):
        table.add_row("YOLO", "[red bold]ON[/]")

    console.print(Panel(
        table,
        title="[bold green]⏪ Session Resumed[/]",
        border_style="green",
    ))

    # Show last few messages as preview
    preview_msgs = [
        m for m in messages[-6:]
        if m.get("role") in ("user", "assistant") and m.get("content")
    ]
    if preview_msgs:
        console.print("[dim]  Last messages:[/]")
        for m in preview_msgs[-3:]:
            role = "You" if m["role"] == "user" else "Jack"
            content = str(m.get("content", ""))[:100]
            if len(str(m.get("content", ""))) > 100:
                content += "..."
            icon = "┃" if m["role"] == "user" else "🗡"
            console.print(f"[dim]  {icon} {role}: {content}[/]")
        console.print()

    logger.info(
        "Resumed session %s: %d msgs, target=%s, phase=%s",
        session_id, len(messages), state.target, state.phase,
    )
    return True


def _maybe_enrich_target_input(user_input: str, state: AppState) -> str:
    """If user input looks like a bare target, auto-set it and enrich
    the message with a phase-appropriate instruction.

    The instruction varies by current phase so the AI doesn't always
    fall back to recon when the user has already advanced.
    """
    import re

    text = user_input.strip()

    # Skip if input is clearly a sentence (has spaces + common words)
    if len(text.split()) > 3:
        return user_input

    # Detect domain pattern (e.g., "example.com", "sub.example.co.id")
    domain_re = re.compile(
        r'^(?:https?://)?([a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?'
        r'(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*'
        r'\.[a-zA-Z]{2,})(?:[:/].*)?$'
    )
    # Detect IP pattern
    ip_re = re.compile(
        r'^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})(?:[:/].*)?$'
    )

    match = domain_re.match(text) or ip_re.match(text)
    if not match:
        return user_input

    target = match.group(1)

    # Auto-set the target if not already set
    if not state.target:
        state.target = target
        console.print(f"[dim]  🎯 Target auto-set: {target}[/]")
        logger.info("Auto-set target: %s", target)

    # Phase-aware instructions
    phase = state.phase
    phase_instructions = {
        "recon": (
            f"Execute full recon immediately using batch_execute — "
            f"DNS lookup, WHOIS, SSL info, port scan (21,22,80,443,3306,5432,8080,8443), "
            f"web_fetch homepage, and web_search for known vulns. "
            f"Do NOT list steps or ask — just call the tools NOW."
        ),
        "enum": (
            f"Target is already reconned. Move to ENUMERATION — "
            f"directory bruteforce, parameter discovery, tech fingerprinting, "
            f"service enumeration. Check memory_read for prior findings first. "
            f"Execute tools NOW, don't ask."
        ),
        "vuln": (
            f"Target is scoped. Focus on VULNERABILITY ANALYSIS — "
            f"search CVEs for detected tech stack, run vuln scans, "
            f"check exploit_search for known exploits. Read memory first. "
            f"Execute tools NOW."
        ),
        "exploit": (
            f"Target is scoped and vulnerabilities identified. EXPLOIT NOW — "
            f"Read memory_read for prior findings, then execute exploits: "
            f"try RCE, SQLi, file upload, auth bypass, webshell deployment. "
            f"Use payload_generate, http_request, python_repl, bash_execute. "
            f"Prioritize getting a shell. Do NOT do recon again. Execute NOW."
        ),
        "post_exploit": (
            f"You have access to the target. POST-EXPLOITATION — "
            f"privesc, lateral movement, data exfiltration, persistence. "
            f"Read memory for current access level. Deploy gsocket for backdoor. "
            f"Execute NOW."
        ),
        "report": (
            f"Generate a full penetration test report for this target. "
            f"Read memory_read and todo_read for all findings, then use "
            f"report_generate. Execute NOW."
        ),
    }

    instruction = phase_instructions.get(phase, phase_instructions["recon"])
    return f"Target: {target}\n{instruction}"


def main_loop(
    state: AppState,
    ai: CloudflareAI | None,
    executor: ToolExecutor,
    tool_schemas: list[dict[str, Any]],
    tool_names: list[str],
    ai_factory: AIFactory | None = None,
    cost_tracker: Any = None,
    resume_session_id: str | None = None,
) -> NoReturn:
    """The main interactive prompt loop.

    Args:
        ai_factory: Optional callable(model) -> CloudflareAI for reconnecting
                    after /login without restarting.
        cost_tracker: Optional CostTracker instance for API usage tracking.
        resume_session_id: Optional session ID to resume at startup.
    """
    # Initialize incremental session writer
    from jack_the_shadow.session.history import SessionWriter
    writer = SessionWriter(state)
    state._session_writer = writer
    logger.info("Session writer initialized: %s", writer.session_id)

    # Handle startup resume if requested
    if resume_session_id:
        _resume_session(resume_session_id, state)

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
                # Create a new writer for the resumed session continuation
                writer = SessionWriter(state)
                state._session_writer = writer
                continue

            # Live reconnect after /login
            if was_login and ai is None and ai_factory is not None:
                new_ai = ai_factory(state.model)
                if new_ai is not None:
                    ai = new_ai
                    display_info(t("auth.connected"))
            continue

        display_user_message(user_input)

        # Detect target-like input and auto-set target + inject recon hint
        enriched = _maybe_enrich_target_input(user_input, state)
        state.add_message("user", enriched)

        if ai is None:
            display_error(t("offline.hint"))
        else:
            try:
                query_ai(ai, state, executor, tool_schemas, cost_tracker)
            except KeyboardInterrupt:
                console.print("\n[dim]  ⚡ Interrupted — back to prompt.[/]")
                logger.info("User interrupted AI query with Ctrl+C")

            # Check if user typed anything during execution (stdin buffer)
            queued = _drain_stdin_queue()
            for q in queued:
                if q.startswith("/"):
                    handle_local_command(q, state, tool_names, executor, cost_tracker)
                    continue
                display_user_message(q)
                enriched_q = _maybe_enrich_target_input(q, state)
                state.add_message("user", enriched_q)
                if ai is not None:
                    console.print("[dim]  📨 Processing queued message...[/]")
                    try:
                        query_ai(ai, state, executor, tool_schemas, cost_tracker)
                    except KeyboardInterrupt:
                        console.print("\n[dim]  ⚡ Interrupted — back to prompt.[/]")
