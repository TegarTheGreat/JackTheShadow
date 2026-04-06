#!/usr/bin/env python3
"""
Jack The Shadow — CLI Entry Point

Starts the interactive agent. No mandatory arguments — target is set in chat.
If no credentials are found, forces an interactive login first.
"""

from __future__ import annotations

import argparse
import sys

from jack_the_shadow.config import DEFAULT_LANGUAGE, DEFAULT_MODEL
from jack_the_shadow.core.engine import CloudflareAI
from jack_the_shadow.core.orchestrator import main_loop
from jack_the_shadow.core.state import AppState
from jack_the_shadow.i18n import set_language, t
from jack_the_shadow.session import ensure_session_dir, is_logged_in, load_credentials
from jack_the_shadow.tools.executor import ToolExecutor
from jack_the_shadow.tools.registry import build_default_registry
from jack_the_shadow.ui import console, display_banner, display_error, display_info
from jack_the_shadow.utils.logger import get_logger

logger = get_logger("cli")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="jshadow",
        description="Jack The Shadow — Autonomous Cybersecurity Agent",
        epilog="Examples:\n  jshadow\n  jshadow --target 192.168.1.0/24\n  jshadow -l id",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--target", "-t", default="",
        help="Target scope (IP, CIDR, domain, or URL). Can also be set in chat with /target.",
    )
    parser.add_argument(
        "--model", "-m", default=DEFAULT_MODEL,
        help=f"Cloudflare Workers AI model ID (default: {DEFAULT_MODEL}).",
    )
    parser.add_argument(
        "--lang", "-l", default=DEFAULT_LANGUAGE, choices=["en", "id"],
        help="Language: en (English, default) or id (Bahasa Indonesia).",
    )
    return parser


def _run_login_gate() -> bool:
    """If no credentials, force interactive login. Returns True if logged in."""
    if is_logged_in():
        return True

    console.print(f"\n[warning]{t('auth.gate_header')}[/]")
    console.print(f"[dim]{t('auth.gate_body')}[/]\n")

    from jack_the_shadow.ui.commands import _handle_login_command
    _handle_login_command()

    return is_logged_in()


def _create_ai_client(model: str) -> CloudflareAI | None:
    """Try to create AI client from stored/env credentials."""
    account_id, api_token = load_credentials()
    if account_id and api_token:
        return CloudflareAI(
            account_id=account_id,
            api_token=api_token,
            model=model,
        )
    return None


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    ensure_session_dir()
    set_language(args.lang)

    # Load user config preferences (saved from previous sessions)
    from jack_the_shadow.session.user_config import load_user_config, update_user_config
    user_config = load_user_config()

    # User config provides defaults, CLI args override
    model = args.model if args.model != DEFAULT_MODEL else (user_config.get("model") or DEFAULT_MODEL)
    lang = args.lang if args.lang != DEFAULT_LANGUAGE else (user_config.get("language") or DEFAULT_LANGUAGE)
    if lang != args.lang:
        set_language(lang)

    state = AppState(
        model=model,
        language=lang,
        target=args.target,
    )
    executor = ToolExecutor(state)
    registry = build_default_registry()
    tool_schemas = registry.get_all_schemas()
    tool_names = registry.list_names()

    display_banner(state)

    # ── Auth gate: if no creds, force login
    if not is_logged_in():
        logged_in = _run_login_gate()
        if not logged_in:
            console.print(f"\n[dim]{t('auth.skipped')}[/]\n")

    ai = _create_ai_client(state.model)

    # Initialize cost tracker
    from jack_the_shadow.core.cost_tracker import CostTracker
    cost_tracker = CostTracker()

    if ai is None:
        console.print(t("banner.no_creds"))
        console.print()
    else:
        display_info(t("auth.connected"))

    # Show welcome message
    console.print(f"\n{t('welcome.message')}\n")

    logger.info(
        "Starting Jack — target=%s model=%s lang=%s tools=%s",
        state.target or "(none)", state.model, state.language, tool_names,
    )

    try:
        main_loop(state, ai, executor, tool_schemas, tool_names, _create_ai_client, cost_tracker)
    except SystemExit:
        # Save user preferences for next launch
        update_user_config(model=state.model, language=state.language)
        executor.mcp.shutdown()
        logger.info("Clean shutdown")
    except Exception as exc:
        executor.mcp.shutdown()
        logger.exception("Unhandled exception")
        display_error(f"Fatal: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
