"""
Jack The Shadow — Slash Command System

Interactive command menu and all local command handlers.
Commands are registered in a CommandRegistry for alias resolution,
fuzzy search, and autocomplete. All menus use ↑↓ selector.
"""

from __future__ import annotations

from typing import Any, Optional

from rich.panel import Panel
from rich.table import Table

from jack_the_shadow.config import MAX_CONTEXT_MESSAGES
from jack_the_shadow.config.models import get_model_catalog, MODEL_CATALOG
from jack_the_shadow.core.command_registry import Command, CommandRegistry
from jack_the_shadow.i18n import set_language, t
from jack_the_shadow.ui.console import console
from jack_the_shadow.ui.messages import display_error, display_info
from jack_the_shadow.ui.selector import interactive_select
from jack_the_shadow.utils.logger import get_logger

logger = get_logger("ui.commands")


# ── Global registry ───────────────────────────────────────────────────

_registry = CommandRegistry()


def _register_commands() -> None:
    """Populate the registry with all slash commands."""
    commands = [
        Command("/yolo",        t("cmd.yolo.desc"),        "session",  aliases=["/y"]),
        Command("/clear",       t("cmd.clear.desc"),       "session"),
        Command("/compact",     t("cmd.compact.desc"),     "session"),
        Command("/context",     t("cmd.context.desc"),     "session", aliases=["/ctx"]),
        Command("/tools",       t("cmd.tools.desc"),       "tools"),
        Command("/model",       t("cmd.model.desc"),       "config",  aliases=["/m"]),
        Command("/models",      t("cmd.models.desc"),      "config"),
        Command("/lang",        t("cmd.lang.desc"),        "config",  aliases=["/language"]),
        Command("/target",      t("cmd.target.desc"),      "session", aliases=["/t"]),
        Command("/login",       t("cmd.login.desc"),       "auth"),
        Command("/logout",      t("cmd.logout.desc"),      "auth"),
        Command("/mcp",         t("cmd.mcp.desc"),         "tools"),
        Command("/history",     t("cmd.history.desc"),     "session", aliases=["/hist"]),
        Command("/export",      t("cmd.export.desc"),      "session"),
        Command("/doctor",      t("cmd.doctor.desc"),      "tools",   aliases=["/doc"]),
        Command("/cost",        t("cmd.cost.desc"),        "session"),
        Command("/memory",      t("cmd.memory.desc"),      "session", aliases=["/mem"]),
        Command("/plan",        t("cmd.plan.desc"),        "session"),
        Command("/permissions", t("cmd.permissions.desc"), "config",  aliases=["/perm"]),
        Command("/phase",       t("cmd.phase.desc"),       "session", aliases=["/p"]),
        Command("/help",        t("cmd.help.desc"),        "general", aliases=["/h", "/?"]),
        Command("/exit",        t("cmd.exit.desc"),        "general", aliases=["/quit", "/q"]),
    ]
    for cmd in commands:
        _registry.register(cmd)


# Build on first import
_register_commands()


def get_slash_commands() -> list[tuple[str, str]]:
    """Return (command, description) list for prompt autocomplete.

    Includes aliases so typing '/q' also autocompletes.
    """
    result: list[tuple[str, str]] = []
    for cmd in _registry.all():
        result.append((cmd.name, cmd.description))
        for alias in cmd.aliases:
            result.append((alias, f"→ {cmd.name}"))
    return result


def _safe_input(prompt_text: str) -> str:
    """Read input with a plain prompt. Returns '' on cancel."""
    try:
        return input(prompt_text).strip()
    except (EOFError, KeyboardInterrupt):
        console.print()
        return ""


def _display_command_menu() -> Optional[str]:
    """Show an interactive ↑↓ selector for commands."""
    commands = _registry.all()
    labels = [cmd.name for cmd in commands]
    descs = [cmd.description for cmd in commands]

    idx = interactive_select(labels, title="Commands", descriptions=descs)
    if idx is None:
        return None

    selected = commands[idx].name
    if selected in ("/target",):
        console.print(f"[dim]  {selected} → enter value (ESC to cancel):[/]")
        arg = _safe_input("  > ")
        return f"{selected} {arg}" if arg else None
    return selected


def _get_live_catalog() -> dict[str, str]:
    """Get the model catalog, using live API if credentials are available."""
    try:
        from jack_the_shadow.session.auth import load_credentials
        account_id, api_token = load_credentials()
        if account_id and api_token:
            return get_model_catalog(account_id, api_token)
    except Exception:
        pass
    return MODEL_CATALOG


def _show_models_list(state: Any) -> None:
    catalog = _get_live_catalog()
    table = Table(title="[info]Available Models[/]", border_style="blue")
    table.add_column("No", style="bold", width=4)
    table.add_column("Model", style="cyan")
    table.add_column("ID", style="dim")
    table.add_column("", width=3)

    for i, (name, model_id) in enumerate(catalog.items(), 1):
        active = "◉" if model_id == state.model else ""
        table.add_row(str(i), name, model_id, f"[green]{active}[/]")

    console.print(table)
    console.print(f"[dim]  {len(catalog)} models (auto-fetched from Cloudflare)[/]")


def _select_model(state: Any) -> Optional[str]:
    """Interactive model selector. Returns model ID or None on cancel."""
    catalog = _get_live_catalog()
    names = list(catalog.keys())
    ids = list(catalog.values())

    # Pre-select the currently active model
    try:
        current_idx = ids.index(state.model)
    except ValueError:
        current_idx = 0

    descs = [mid for mid in ids]
    idx = interactive_select(names, title="Select Model", selected=current_idx, descriptions=descs)
    if idx is None:
        return None
    return ids[idx]


def _show_tools_list(tool_names: list[str]) -> None:
    table = Table(title="[info]Available Tools[/]", border_style="blue")
    table.add_column("No", style="bold", width=4)
    table.add_column("Tool", style="cyan")

    for i, name in enumerate(tool_names, 1):
        table.add_row(str(i), name)

    console.print(table)


def _show_context_info(state: Any) -> None:
    count = len(state.context_messages)
    target_str = state.target if state.target else f"[dim]{t('banner.no_target')}[/]"
    console.print(Panel(
        f"[bold]{t('context.messages')}:[/] {count} / {MAX_CONTEXT_MESSAGES}\n"
        f"[bold]{t('banner.target')}:[/] {target_str}\n"
        f"[bold]{t('banner.model')}:[/] {state.model}\n"
        f"[bold]{t('banner.yolo')}:[/] {'ON' if state.yolo_mode else 'OFF'}",
        title=f"[info]{t('context.title')}[/]",
        border_style="blue",
    ))


def _handle_mcp_command(arg: str, executor: Optional[Any]) -> None:
    """Handle /mcp subcommands: add, remove, list."""
    if executor is None or not hasattr(executor, "mcp"):
        display_error(t("mcp.usage"))
        return

    mcp = executor.mcp
    sub_parts = arg.split(maxsplit=2) if arg else []
    sub_cmd = sub_parts[0].lower() if sub_parts else "list"

    if sub_cmd == "list" or not arg:
        servers = mcp.list_servers()
        if not servers:
            console.print(f"  [dim]{t('mcp.no_servers')}[/]")
            return
        table = Table(title=f"[info]{t('mcp.title')}[/]", border_style="blue")
        table.add_column("Name", style="cyan")
        table.add_column("Status", style="bold")
        table.add_column("Tools", style="dim")
        for s in servers:
            status = "[green]●[/] Running" if s["running"] else "[red]●[/] Stopped"
            tools = ", ".join(s["tools"]) if s["tools"] else "-"
            table.add_row(s["name"], status, tools)
        console.print(table)
        return

    if sub_cmd == "add":
        if len(sub_parts) < 3:
            display_error(t("mcp.usage"))
            return
        name = sub_parts[1]
        rest = sub_parts[2].split()
        command = rest[0]
        args = rest[1:] if len(rest) > 1 else []
        success = mcp.add_server(name, command, args)
        if success:
            server = mcp.get_server(name)
            tool_count = len(server.list_tools()) if server else 0
            display_info(t("mcp.added", name=name, tools=tool_count))
        else:
            display_error(t("mcp.add_failed", name=name))
        return

    if sub_cmd in ("remove", "rm"):
        if len(sub_parts) < 2:
            display_error(t("mcp.usage"))
            return
        name = sub_parts[1]
        mcp.remove_server(name)
        display_info(t("mcp.removed", name=name))
        return

    display_error(t("mcp.usage"))


def _handle_login_command() -> None:
    """Interactive Cloudflare credential setup → ~/.jshadow/credentials.json."""
    from jack_the_shadow.session.auth import (
        get_credential_source,
        is_logged_in,
        save_credentials,
    )

    if is_logged_in():
        source = get_credential_source() or "unknown"
        console.print(
            f"\n[info]  {t('login.already_logged_in')}[/]\n"
            f"  [dim]{t('login.source', source=source)}[/]"
        )
        idx = interactive_select(
            ["Yes — overwrite credentials", "No — keep current"],
            title="Overwrite existing credentials?",
        )
        if idx != 0:
            return

    console.print(f"\n[info]  {t('login.instruction')}[/]\n")
    account_id = _safe_input("  Cloudflare Account ID: ")
    api_token = _safe_input("  Cloudflare API Token:  ")

    if not account_id or not api_token:
        display_error(t("login.empty_fields"))
        return

    save_credentials(account_id, api_token)
    display_info(t("login.success"))
    console.print(f"  [dim]{t('login.reconnect_hint')}[/]")


def _handle_logout_command() -> None:
    """Clear stored Cloudflare credentials."""
    from jack_the_shadow.session.auth import clear_credentials, is_logged_in

    if not is_logged_in():
        display_info(t("logout.not_logged_in"))
        return

    cleared = clear_credentials()
    if cleared:
        display_info(t("logout.success"))
    else:
        display_info(t("logout.not_logged_in"))


def _handle_history_command() -> None:
    """List past sessions and allow resuming one via interactive selector."""
    from jack_the_shadow.session.history import list_sessions

    sessions = list_sessions()
    if not sessions:
        console.print("[dim]  No saved sessions found.[/]")
        return

    labels = []
    for s in sessions:
        target = s["target"] or "(no target)"
        phase = s.get("phase", "")
        tools = s.get("tools", 0)
        dur = s.get("duration", 0)
        dur_str = f"{int(dur // 60)}m{int(dur % 60)}s" if dur else ""

        parts = [s["date"][:16], target, f"{s['messages']}msg"]
        if tools:
            parts.append(f"{tools}tools")
        if dur_str:
            parts.append(dur_str)
        if phase:
            parts.append(phase)
        labels.append("  │  ".join(parts))

    idx = interactive_select(labels, title="Resume a session")
    if idx is not None:
        return sessions[idx]["id"]
    return None


def _handle_export_command(state: Any) -> None:
    """Export current conversation to a markdown file."""
    from jack_the_shadow.session.history import export_session

    if not state.context_messages:
        console.print("[dim]  Nothing to export — conversation is empty.[/]")
        return

    filepath = export_session(state)
    if filepath:
        display_info(f"Session exported → {filepath}")
    else:
        display_error("Failed to export session.")


def _handle_doctor_command(executor: Optional[Any]) -> None:
    """Run doctor diagnostics to check pentest tool availability."""
    if executor is None:
        display_error("Executor not available.")
        return
    from jack_the_shadow.tools.builtin.doctor import handle_doctor_check
    res = handle_doctor_check(executor, category="all")
    if res["status"] == "success":
        console.print(f"\n{res['output']}")
    else:
        display_error(res.get("message", "Doctor check failed."))


def _handle_cost_command(cost_tracker: Any) -> None:
    """Display API usage statistics."""
    if cost_tracker is None:
        console.print("[dim]  Cost tracking not available.[/]")
        return
    summary = cost_tracker.format_summary()
    console.print(Panel(summary, title="[info]API Usage[/]", border_style="blue"))


def _handle_memory_command(arg: str) -> None:
    """View or manage persistent memory."""
    from jack_the_shadow.session.paths import JSHADOW_DIR

    memory_file = JSHADOW_DIR / "memory" / "notes.md"
    if arg.lower() == "clear":
        if memory_file.exists():
            memory_file.write_text("")
            display_info("Memory cleared.")
        else:
            console.print("[dim]  No memory to clear.[/]")
        return

    if not memory_file.exists() or not memory_file.read_text().strip():
        console.print("[dim]  No memory notes saved yet. Jack will save findings as you work.[/]")
        return

    content = memory_file.read_text()
    if arg:
        lines = [l for l in content.splitlines() if arg.lower() in l.lower()]
        if lines:
            console.print("\n".join(lines))
        else:
            console.print(f"[dim]  No memory entries matching '{arg}'.[/]")
    else:
        console.print(Panel(content[:3000], title="[info]Persistent Memory[/]", border_style="blue"))


def _handle_plan_command() -> None:
    """View current attack plan / todo list."""
    from jack_the_shadow.session.paths import JSHADOW_DIR
    import json as _json

    todo_file = JSHADOW_DIR / "memory" / "todos.json"
    if not todo_file.exists():
        console.print("[dim]  No attack plan yet. Jack will create tasks as you work.[/]")
        return

    try:
        todos = _json.loads(todo_file.read_text())
    except (ValueError, OSError):
        console.print("[dim]  No attack plan yet.[/]")
        return

    if not todos:
        console.print("[dim]  Task list is empty.[/]")
        return

    table = Table(title="[info]Attack Plan[/]", border_style="blue")
    table.add_column("ID", style="bold", width=4)
    table.add_column("Phase", style="magenta", width=18)
    table.add_column("Task", style="white")
    table.add_column("Status", width=14)

    icons = {"pending": "⏳", "in_progress": "🔄", "done": "✅"}
    for todo in todos:
        icon = icons.get(todo.get("status", "pending"), "⏳")
        table.add_row(
            str(todo.get("id", "?")),
            todo.get("phase", "-"),
            todo.get("task", "-"),
            f"{icon} {todo.get('status', 'pending')}",
        )
    console.print(table)


def _handle_permissions_command(arg: str) -> None:
    """Manage permission auto-approve rules."""
    from jack_the_shadow.core.permissions import (
        add_permission_rule,
        clear_permission_rules,
        list_permission_rules,
        remove_permission_rule,
    )

    parts = arg.split(maxsplit=2) if arg else []
    sub = parts[0].lower() if parts else ""

    if not sub:
        # Interactive sub-command selector
        idx = interactive_select(
            ["List rules", "Add rule", "Remove rule", "Clear all"],
            title="Permission Rules",
        )
        if idx is None:
            return
        sub = ["list", "add", "remove", "clear"][idx]

    if sub == "list":
        rules = list_permission_rules()
        if not rules:
            console.print("[dim]  No permission rules set. All risky tools require approval.[/]")
            console.print("[dim]  Usage: /permissions add bash_execute \"nmap *\"[/]")
            return
        table = Table(title="[info]Permission Rules[/]", border_style="blue")
        table.add_column("Tool", style="cyan")
        table.add_column("Pattern", style="white")
        for tool, patterns in rules.items():
            for p in patterns:
                table.add_row(tool, p)
        console.print(table)
        return

    if sub == "add" and len(parts) >= 3:
        tool_name = parts[1]
        pattern = parts[2].strip("\"'")
        add_permission_rule(tool_name, pattern)
        display_info(f"Rule added: {tool_name}({pattern})")
        return

    if sub in ("remove", "rm") and len(parts) >= 3:
        tool_name = parts[1]
        pattern = parts[2].strip("\"'")
        if remove_permission_rule(tool_name, pattern):
            display_info(f"Rule removed: {tool_name}({pattern})")
        else:
            display_error("Rule not found.")
        return

    if sub == "clear":
        clear_permission_rules()
        display_info("All permission rules cleared.")
        return

    console.print("[dim]  Usage: /permissions add|remove|clear|list <tool> <pattern>[/]")


def handle_local_command(
    command: str,
    state: Any,
    tool_names: Optional[list[str]] = None,
    executor: Optional[Any] = None,
    cost_tracker: Optional[Any] = None,
) -> Any:
    """Process a slash command.  Returns True if handled, or session_id for /history resume."""
    from jack_the_shadow.ui.panels import display_yolo_toggle

    parts = command.strip().split(maxsplit=1)
    raw_cmd = parts[0].lower()
    arg = parts[1].strip() if len(parts) > 1 else ""

    # Resolve aliases via registry (e.g. /q → /exit, /m → /model)
    entry = _registry.find(raw_cmd)
    cmd = entry.name if entry else raw_cmd

    if cmd == "/":
        selected = _display_command_menu()
        if selected:
            return handle_local_command(selected, state, tool_names, executor, cost_tracker)
        return True

    if cmd == "/exit":
        console.print(f"\n[dim]{t('goodbye')}[/]\n")
        logger.info("User requested /exit")
        raise SystemExit(0)

    if cmd == "/clear":
        state.clear_context()
        display_info(t("cmd.clear.desc"))
        return True

    if cmd == "/compact":
        keep = int(arg) if arg.isdigit() else 10
        dropped = state.compact_context(keep)
        display_info(f"Dropped {dropped} messages, kept last {keep}.")
        return True

    if cmd == "/yolo":
        display_yolo_toggle(state.toggle_yolo())
        return True

    if cmd == "/context":
        _show_context_info(state)
        return True

    if cmd == "/tools":
        _show_tools_list(tool_names or [])
        return True

    if cmd == "/models":
        _show_models_list(state)
        return True

    if cmd == "/model":
        if arg:
            # Direct argument: try to match
            catalog = _get_live_catalog()
            all_ids = list(catalog.values())
            if arg in all_ids or arg.startswith("@cf/"):
                state.model = arg
                display_info(t("model.switched", model=state.model))
                return True
            for name, mid in catalog.items():
                if arg.lower() in name.lower():
                    state.model = mid
                    display_info(t("model.switched", model=state.model))
                    return True
            display_error(t("model.invalid"))
        else:
            # Interactive selector
            model_id = _select_model(state)
            if model_id:
                state.model = model_id
                display_info(t("model.switched", model=state.model))
        return True

    if cmd == "/lang":
        if not arg:
            idx = interactive_select(
                ["English", "Bahasa Indonesia"],
                title="Select Language",
            )
            if idx == 0:
                arg = "en"
            elif idx == 1:
                arg = "id"
            else:
                return True  # cancelled

        if arg in ("en", "id"):
            state.language = arg
            set_language(arg)
            display_info(t("lang.switched"))
        else:
            display_error(t("lang.invalid"))
        return True

    if cmd == "/target":
        if not arg:
            console.print("[dim]  Enter target scope (IP, CIDR, domain, URL):[/]")
            arg = _safe_input("  > ")
        if arg:
            state.target = arg
            display_info(t("target.switched", target=arg))
        else:
            display_error(t("target.usage"))
        return True

    if cmd == "/login":
        _handle_login_command()
        return True

    if cmd == "/logout":
        _handle_logout_command()
        return True

    if cmd == "/mcp":
        _handle_mcp_command(arg, executor)
        return True

    if cmd == "/history":
        result = _handle_history_command()
        if result:
            return ("resume", result)
        return True

    if cmd == "/export":
        _handle_export_command(state)
        return True

    if cmd == "/help":
        selected = _display_command_menu()
        if selected:
            return handle_local_command(selected, state, tool_names, executor, cost_tracker)
        return True

    if cmd == "/doctor":
        _handle_doctor_command(executor)
        return True

    if cmd == "/cost":
        _handle_cost_command(cost_tracker)
        return True

    if cmd == "/memory":
        _handle_memory_command(arg)
        return True

    if cmd == "/plan":
        _handle_plan_command()
        return True

    if cmd == "/permissions":
        _handle_permissions_command(arg)
        return True

    if cmd == "/phase":
        _handle_phase_command(arg, state)
        return True

    # Fuzzy suggestion for unknown commands
    suggestions = _registry.fuzzy_search(raw_cmd)
    if suggestions:
        best = suggestions[0].name
        console.print(f"[dim]  Unknown command: {raw_cmd}. Did you mean [bold]{best}[/bold]? Type / for menu.[/]")
    else:
        console.print(f"[dim]  Unknown command: {raw_cmd}. Type / for menu.[/]")
    return True


def _handle_phase_command(arg: str, state: "AppState") -> None:
    """Switch the current pentest phase (affects tool selection)."""
    from jack_the_shadow.core.methodology import PHASES

    if arg and arg.lower() in PHASES:
        state.phase = arg.lower()
        console.print(f"[bold green]  Phase set: {state.phase}[/]")
        return

    labels = list(PHASES)
    descs = [
        "Reconnaissance — DNS, WHOIS, port scan, web search",
        "Enumeration — dir brute, param discovery, service enum",
        "Vulnerability — CVE search, vuln scan, tech fingerprint",
        "Exploitation — payload gen, exploit run, RCE, SQLi",
        "Post-Exploit — privesc, lateral movement, data exfil",
        "Reporting — compile findings, generate report",
    ]
    idx = interactive_select(labels, title="Pentest Phase", descriptions=descs)
    if idx is not None:
        state.phase = labels[idx]
        console.print(f"[bold green]  Phase set: {state.phase}[/]")
