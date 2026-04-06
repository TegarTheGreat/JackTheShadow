#!/usr/bin/env python3
"""
Jack The Shadow — CLI Entry Point

CLI argument parsing, initialisation, and handoff to the orchestrator.
"""

from __future__ import annotations

import argparse
import sys

from jack_the_shadow.config import (
    CLOUDFLARE_ACCOUNT_ID,
    CLOUDFLARE_API_TOKEN,
    DEFAULT_LANGUAGE,
    DEFAULT_MODEL,
)
from jack_the_shadow.core.engine import CloudflareAI
from jack_the_shadow.core.orchestrator import main_loop
from jack_the_shadow.core.state import AppState
from jack_the_shadow.i18n import set_language, t
from jack_the_shadow.tools.executor import ToolExecutor
from jack_the_shadow.tools.registry import build_default_registry
from jack_the_shadow.ui import console, display_banner, display_error
from jack_the_shadow.utils.logger import get_logger

logger = get_logger("cli")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="jack",
        description="Jack The Shadow — Autonomous Penetration-Testing Agent",
        epilog="Example: jack --target 192.168.1.0/24",
    )
    parser.add_argument(
        "--target", "-t", required=True,
        help="Target scope (IP, CIDR, domain, or URL). Required.",
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


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    set_language(args.lang)

    state = AppState(
        target=args.target,
        model=args.model,
        language=args.lang,
    )
    executor = ToolExecutor(state)
    registry = build_default_registry()
    tool_schemas = registry.get_all_schemas()
    tool_names = registry.list_names()

    logger.info(
        "Starting Jack — target=%s model=%s lang=%s tools=%s",
        state.target, state.model, state.language, tool_names,
    )

    ai: CloudflareAI | None = None
    if CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN:
        ai = CloudflareAI(
            account_id=CLOUDFLARE_ACCOUNT_ID,
            api_token=CLOUDFLARE_API_TOKEN,
            model=state.model,
        )
    else:
        logger.warning("No Cloudflare credentials — offline mode")

    display_banner(state)

    if ai is None:
        console.print(t("banner.no_creds"))
        console.print()

    try:
        main_loop(state, ai, executor, tool_schemas, tool_names)
    except SystemExit:
        executor.mcp.shutdown()
        logger.info("Clean shutdown")
    except Exception as exc:
        executor.mcp.shutdown()
        logger.exception("Unhandled exception")
        display_error(f"Fatal: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
