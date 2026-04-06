"""
Jack The Shadow — Message Display

Functions for rendering AI responses, user input, errors, and info.
Includes a terminal-safe text sanitizer for complex Unicode sequences.
"""

import re
import sys

from rich.markdown import Markdown
from rich.panel import Panel

from jack_the_shadow.ui.console import console

# ── Emoji / Unicode sanitizer ─────────────────────────────────────────

# Variation selectors (VS15 text, VS16 emoji presentation)
_VARIATION_SELECTORS = re.compile(r"[\ufe00-\ufe0f]")
# Combining enclosing keycap
_KEYCAP = re.compile(r"\u20e3")
# Skin tone modifiers
_SKIN_TONES = re.compile(r"[\U0001F3FB-\U0001F3FF]")
# Zero-width joiner (used in compound emoji like 👨‍💻)
_ZWJ = re.compile(r"\u200d")


def sanitize_for_terminal(text: str) -> str:
    """Strip invisible Unicode modifiers that break terminal rendering.

    Removes variation selectors, keycap combiners, skin tone modifiers,
    and zero-width joiners that cause garbled output like ``ï¸â£``.
    """
    text = _VARIATION_SELECTORS.sub("", text)
    text = _KEYCAP.sub("", text)
    text = _SKIN_TONES.sub("", text)
    text = _ZWJ.sub("", text)
    return text


def display_user_message(text: str) -> None:
    console.print(f"\n[user]┃ You:[/] {text}")


def display_ai_message(text: str) -> None:
    text = sanitize_for_terminal(text)
    console.print()
    console.print(Panel(
        Markdown(text),
        title="[jack]🗡  Jack[/]",
        border_style="green",
        padding=(1, 2),
    ))


class StreamingDisplay:
    """Collects streamed tokens and renders a final formatted panel.

    Tokens are printed inline for real-time feedback.  When ``finish()``
    is called, the inline text is left as-is (no duplicate panel).
    """

    def __init__(self) -> None:
        self._parts: list[str] = []
        self._started = False
        self._aborted = False

    def on_token(self, token: str) -> None:
        """Called by the engine for each SSE text chunk."""
        if self._aborted:
            return
        if not self._started:
            console.print()
            console.print("[jack]🗡  Jack:[/]", end=" ")
            self._started = True

        # Sanitize and write through Rich's console for proper encoding
        clean = sanitize_for_terminal(token)
        console.out(clean, end="", highlight=False)
        self._parts.append(clean)

    def finish(self) -> str:
        """End the stream. Returns the full accumulated text."""
        full = "".join(self._parts)
        if self._started and full.strip():
            console.out("\n")
        return full

    def abort(self) -> None:
        """Cancel the stream display (e.g. on error)."""
        self._aborted = True
        if self._started:
            console.out("\n")


def display_error(text: str) -> None:
    console.print(f"\n[warning]✖ Error:[/] {text}")


def display_info(text: str) -> None:
    console.print(f"[info]✓ {text}[/]")
