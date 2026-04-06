"""
Jack The Shadow — Message Display

Functions for rendering AI responses, user input, errors, and info.
"""

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


def display_error(text: str) -> None:
    console.print(f"\n[warning]✖ Error:[/] {text}")


def display_info(text: str) -> None:
    console.print(f"[info]✓ {text}[/]")
