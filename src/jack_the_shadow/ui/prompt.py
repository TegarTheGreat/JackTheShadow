"""
Jack The Shadow — User Prompt & Spinner

The ``jack>`` input prompt and status spinner context manager.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator, Optional

from jack_the_shadow.i18n import t
from jack_the_shadow.ui.console import console


def prompt_user() -> str:
    """Show the ``jshadow>`` prompt and return user input."""
    try:
        return console.input("[bold cyan]jshadow>[/] ").strip()
    except (EOFError, KeyboardInterrupt):
        console.print(f"\n[dim]{t('goodbye')}[/]\n")
        raise SystemExit(0)


@contextmanager
def status_spinner(message: Optional[str] = None) -> Generator[None, None, None]:
    msg = message or t("spinner.thinking")
    with console.status(f"[info]{msg}[/]", spinner="dots"):
        yield
