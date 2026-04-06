"""
Jack The Shadow — Slash Command System

Interactive command menu and all local command handlers.
"""

from __future__ import annotations

from typing import Any, Optional

from rich.panel import Panel
from rich.table import Table

from jack_the_shadow.config import MAX_CONTEXT_MESSAGES, MODEL_CATALOG
from jack_the_shadow.i18n import set_language, t
from jack_the_shadow.ui.console import console
from jack_the_shadow.ui.messages import display_error, display_info
from jack_the_shadow.utils.logger import get_logger

logger = get_logger("ui.commands")

# Registry: (command, description_key)
SLASH_COMMANDS: list[tuple[str, str]] = [
    ("/yolo",    "cmd.yolo.desc"),
    ("/clear",   "cmd.clear.desc"),
    ("/compact", "cmd.compact.desc"),
    ("/context", "cmd.context.desc"),
    ("/tools",   "cmd.tools.desc"),
    ("/model",   "cmd.model.desc"),
    ("/models",  "cmd.models.desc"),
    ("/lang",    "cmd.lang.desc"),
    ("/target",  "cmd.target.desc"),
    ("/login",   "cmd.login.desc"),
    ("/logout",  "cmd.logout.desc"),
    ("/mcp",     "cmd.mcp.desc"),
    ("/help",    "cmd.help.desc"),
    ("/exit",    "cmd.exit.desc"),
]


def _display_command_menu() -> Optional[str]:
    """Show a numbered menu of slash commands and let user pick one."""
    console.print()
    table = Table(
        title="[info]Commands[/]",
        show_header=False,
        border_style="blue",
        padding=(0, 2),
    )
    table.add_column("No", style="bold white", width=4)
    table.add_column("Command", style="menu.cmd", width=12)
    table.add_column("Description", style="menu.desc")

    for i, (cmd, desc_key) in enumerate(SLASH_COMMANDS, 1):
        table.add_row(str(i), cmd, t(desc_key))

    console.print(table)
    console.print()

    try:
        choice = console.input(
            "[bold white]  Pick a number (or type command): [/]"
        ).strip()
    except (EOFError, KeyboardInterrupt):
        return None

    if not choice:
        return None

    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(SLASH_COMMANDS):
            selected = SLASH_COMMANDS[idx][0]
            if selected in ("/model", "/lang", "/target", "/login"):
                try:
                    arg = console.input(
                        f"[dim]  {selected} [/][bold white]→ value: [/]"
                    ).strip()
                except (EOFError, KeyboardInterrupt):
                    return None
                return f"{selected} {arg}" if arg else selected
            return selected
        return None

    if choice.startswith("/"):
        return choice
    return None


def _show_models_list(state: Any) -> None:
    table = Table(title="[info]Available Models[/]", border_style="blue")
    table.add_column("No", style="bold", width=4)
    table.add_column("Model", style="cyan")
    table.add_column("ID", style="dim")
    table.add_column("", width=3)

    for i, (name, model_id) in enumerate(MODEL_CATALOG.items(), 1):
        active = "◉" if model_id == state.model else ""
        table.add_row(str(i), name, model_id, f"[green]{active}[/]")

    console.print(table)


def _show_tools_list(tool_names: list[str]) -> None:
    table = Table(title="[info]Available Tools[/]", border_style="blue")
    table.add_column("No", style="bold", width=4)
    table.add_column("Tool", style="cyan")

    for i, name in enumerate(tool_names, 1):
        table.add_row(str(i), name)

    console.print(table)


def _show_context_info(state: Any) -> None:
    count = len(state.context_messages)
    console.print(Panel(
        f"[bold]{t('context.messages')}:[/] {count} / {MAX_CONTEXT_MESSAGES}\n"
        f"[bold]{t('banner.target')}:[/] {state.target}\n"
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
        try:
            overwrite = console.input(
                f"\n[bold white]  {t('login.overwrite_prompt')}[/]"
            ).strip().lower()
        except (EOFError, KeyboardInterrupt):
            return
        if overwrite not in ("y", "yes"):
            return

    console.print(f"\n[info]  {t('login.instruction')}[/]\n")
    try:
        account_id = console.input(
            "[bold white]  Cloudflare Account ID: [/]"
        ).strip()
        api_token = console.input(
            "[bold white]  Cloudflare API Token:  [/]"
        ).strip()
    except (EOFError, KeyboardInterrupt):
        console.print(f"\n[dim]  {t('hitl.cancelled')}[/]")
        return

    if not account_id or not api_token:
        display_error(t("login.empty_fields"))
        return

    save_credentials(account_id, api_token)
    display_info(t("login.success"))
    console.print(f"  [dim]{t('login.restart_hint')}[/]")


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


def handle_local_command(
    command: str,
    state: Any,
    tool_names: Optional[list[str]] = None,
    executor: Optional[Any] = None,
) -> bool:
    """Process a slash command.  Returns True if handled."""
    from jack_the_shadow.ui.panels import display_yolo_toggle

    parts = command.strip().split(maxsplit=1)
    cmd = parts[0].lower()
    arg = parts[1].strip() if len(parts) > 1 else ""

    if cmd == "/":
        selected = _display_command_menu()
        if selected:
            return handle_local_command(selected, state, tool_names, executor)
        return True

    if cmd in ("/exit", "/quit"):
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
        if not arg:
            _show_models_list(state)
            try:
                choice = console.input("[bold white]  Pick number or model ID: [/]").strip()
            except (EOFError, KeyboardInterrupt):
                return True
            arg = choice

        if arg.isdigit():
            idx = int(arg) - 1
            ids = list(MODEL_CATALOG.values())
            if 0 <= idx < len(ids):
                state.model = ids[idx]
                display_info(t("model.switched", model=state.model))
                return True

        all_ids = list(MODEL_CATALOG.values())
        if arg in all_ids or arg.startswith("@cf/"):
            state.model = arg
            display_info(t("model.switched", model=state.model))
            return True

        for name, mid in MODEL_CATALOG.items():
            if arg.lower() in name.lower():
                state.model = mid
                display_info(t("model.switched", model=state.model))
                return True

        display_error(t("model.invalid"))
        return True

    if cmd == "/lang":
        if arg in ("en", "id"):
            state.language = arg
            set_language(arg)
            display_info(t("lang.switched"))
        else:
            display_error(t("lang.invalid"))
        return True

    if cmd == "/target":
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

    if cmd == "/help":
        _display_command_menu()
        return True

    console.print(f"[dim]Unknown command: {cmd}. Type / for menu.[/]")
    return True
