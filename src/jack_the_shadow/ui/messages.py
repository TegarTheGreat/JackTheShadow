"""
Jack The Shadow — Message Display

Functions for rendering AI responses, user input, errors, and info.
"""

from rich.markdown import Markdown
from rich.panel import Panel
from rich.live import Live
from rich.text import Text

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


def display_ai_stream(token_iter) -> str:
    """Display AI response tokens as they stream in.

    Returns the full accumulated text, or None if the iterator
    returned a dict (tool_call) instead of yielding strings.
    """
    collected: list[str] = []
    console.print()

    with Live(
        Panel(Text("▌", style="green"), title="[jack]🗡  Jack[/]", border_style="green", padding=(1, 2)),
        console=console,
        refresh_per_second=12,
        transient=True,
    ) as live:
        for token in token_iter:
            if isinstance(token, dict):
                return token  # type: ignore[return-value]
            collected.append(token)
            text_so_far = "".join(collected)
            live.update(Panel(
                Markdown(text_so_far + " ▌"),
                title="[jack]🗡  Jack[/]",
                border_style="green",
                padding=(1, 2),
            ))

    full_text = "".join(collected)
    if full_text.strip():
        console.print(Panel(
            Markdown(full_text),
            title="[jack]🗡  Jack[/]",
            border_style="green",
            padding=(1, 2),
        ))
    return full_text


def display_error(text: str) -> None:
    console.print(f"\n[warning]✖ Error:[/] {text}")


def display_info(text: str) -> None:
    console.print(f"[info]✓ {text}[/]")
