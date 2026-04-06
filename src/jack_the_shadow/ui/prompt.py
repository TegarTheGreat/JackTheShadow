"""
Jack The Shadow — User Prompt & Spinner

The ``jshadow>`` input prompt powered by prompt_toolkit.
Features: command history, real-time slash-command autocomplete,
proper arrow-key handling.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator, Iterable, Optional

from prompt_toolkit import PromptSession, ANSI
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document
from prompt_toolkit.history import InMemoryHistory

from jack_the_shadow.i18n import t
from jack_the_shadow.ui.console import console

# ── Slash-command completer ───────────────────────────────────────────

# Populated at startup via ``register_slash_commands``
_slash_commands: list[tuple[str, str]] = []


def register_slash_commands(commands: list[tuple[str, str]]) -> None:
    """Register slash commands for autocompletion.

    Args:
        commands: List of ``("/cmd", "description")`` tuples.
    """
    global _slash_commands
    _slash_commands = list(commands)


class _SlashCompleter(Completer):
    """Shows matching slash commands as the user types ``/``."""

    def get_completions(
        self, document: Document, complete_event: object,
    ) -> Iterable[Completion]:
        text = document.text_before_cursor.lstrip()
        if not text.startswith("/"):
            return

        for cmd, desc_key in _slash_commands:
            if cmd.startswith(text):
                yield Completion(
                    cmd,
                    start_position=-len(text),
                    display=cmd,
                    display_meta=_try_translate(desc_key),
                )


def _try_translate(key: str) -> str:
    try:
        return t(key)
    except Exception:
        return key


# ── Prompt session (singleton) ────────────────────────────────────────

_session: Optional[PromptSession[str]] = None


def _get_session() -> PromptSession[str]:
    global _session
    if _session is None:
        _session = PromptSession(
            history=InMemoryHistory(),
            completer=_SlashCompleter(),
            complete_while_typing=True,
        )
    return _session


# ── Public API ────────────────────────────────────────────────────────

def prompt_user() -> str:
    """Show the ``jshadow>`` prompt and return user input.

    Uses prompt_toolkit for:
    - Arrow key history (up/down)
    - Real-time slash command autocomplete
    - Proper line editing (home/end/ctrl-a/ctrl-e)
    """
    session = _get_session()
    try:
        result = session.prompt(ANSI("\033[1;36mjshadow>\033[0m "))
        return result.strip()
    except (EOFError, KeyboardInterrupt):
        console.print(f"\n[dim]{t('goodbye')}[/]\n")
        raise SystemExit(0)


@contextmanager
def status_spinner(message: Optional[str] = None) -> Generator[None, None, None]:
    msg = message or t("spinner.thinking")
    with console.status(f"[info]{msg}[/]", spinner="dots"):
        yield
