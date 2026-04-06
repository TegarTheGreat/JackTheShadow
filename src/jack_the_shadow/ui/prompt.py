"""
Jack The Shadow — User Prompt & Spinner

The ``jshadow>`` input prompt (with readline support) and status spinner.
"""

from __future__ import annotations

import readline  # noqa: F401 — importing enables arrow keys + history in input()
from contextlib import contextmanager
from typing import Generator, Optional

from jack_the_shadow.i18n import t
from jack_the_shadow.ui.console import console


def prompt_user() -> str:
    """Show the ``jshadow>`` prompt and return user input.

    Uses raw input() instead of console.input() so that readline
    handles arrow keys, history (up/down), and line editing properly.
    """
    try:
        return input("\033[1;36mjshadow>\033[0m ").strip()
    except (EOFError, KeyboardInterrupt):
        console.print(f"\n[dim]{t('goodbye')}[/]\n")
        raise SystemExit(0)


@contextmanager
def status_spinner(message: Optional[str] = None) -> Generator[None, None, None]:
    msg = message or t("spinner.thinking")
    with console.status(f"[info]{msg}[/]", spinner="dots"):
        yield
