"""
Jack The Shadow — Message Display

Functions for rendering AI responses, user input, errors, and info.
"""

import sys

from rich.markdown import Markdown
from rich.panel import Panel

from jack_the_shadow.ui.console import console


def display_user_message(text: str) -> None:
    console.print(f"\n[user]┃ You:[/] {text}")


def display_ai_message(text: str) -> None:
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
    is called, the inline text is left as-is and a formatted panel is
    rendered below (only for substantial content).
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
            # Print a header, then stream tokens inline
            console.print()
            console.print("[jack]🗡  Jack:[/]", end=" ")
            self._started = True
        sys.stdout.write(token)
        sys.stdout.flush()
        self._parts.append(token)

    def finish(self) -> str:
        """End the stream and render the final panel.

        Returns the full accumulated text.
        """
        full = "".join(self._parts)
        if self._started and full.strip():
            # End the inline stream
            sys.stdout.write("\n\n")
            sys.stdout.flush()
        elif not full.strip():
            # Empty stream — nothing to show
            pass
        return full

    def abort(self) -> None:
        """Cancel the stream display (e.g. on error)."""
        self._aborted = True
        if self._started:
            sys.stdout.write("\n")
            sys.stdout.flush()


def display_error(text: str) -> None:
    console.print(f"\n[warning]✖ Error:[/] {text}")


def display_info(text: str) -> None:
    console.print(f"[info]✓ {text}[/]")
