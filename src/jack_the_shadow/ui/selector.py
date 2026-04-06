"""
Jack The Shadow — Interactive Terminal Selector

Arrow-key navigated menus using prompt_toolkit Application.
Fully compatible with the main prompt_toolkit PromptSession.
"""

from __future__ import annotations

from typing import Optional

from prompt_toolkit import Application
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout, Window, FormattedTextControl

from jack_the_shadow.ui.console import console


def interactive_select(
    options: list[str],
    *,
    title: str = "",
    selected: int = 0,
    descriptions: Optional[list[str]] = None,
) -> Optional[int]:
    """Show an interactive selector.

    Navigate with ↑↓ (or j/k), Enter to select, ESC to cancel.

    Args:
        options: Display labels for each option.
        title: Optional header above the list.
        selected: Initial cursor position.
        descriptions: Optional right-aligned descriptions.

    Returns:
        Index of the selected option, or ``None`` if cancelled.
    """
    if not options:
        return None

    state = {"cursor": min(selected, len(options) - 1), "result": None}

    # ── Key bindings ──────────────────────────────────────────────────
    kb = KeyBindings()

    @kb.add("up")
    @kb.add("k")
    def _move_up(event: object) -> None:
        state["cursor"] = (state["cursor"] - 1) % len(options)

    @kb.add("down")
    @kb.add("j")
    def _move_down(event: object) -> None:
        state["cursor"] = (state["cursor"] + 1) % len(options)

    @kb.add("home")
    def _go_top(event: object) -> None:
        state["cursor"] = 0

    @kb.add("end")
    def _go_bottom(event: object) -> None:
        state["cursor"] = len(options) - 1

    @kb.add("enter")
    def _select(event: object) -> None:
        state["result"] = state["cursor"]
        event.app.exit()  # type: ignore[union-attr]

    @kb.add("escape")
    @kb.add("c-c")
    def _cancel(event: object) -> None:
        state["result"] = None
        event.app.exit()  # type: ignore[union-attr]

    # ── Render function ───────────────────────────────────────────────
    def _build_fragments() -> FormattedText:
        frags: list[tuple[str, str]] = []

        if title:
            frags.append(("bold", f"  {title}\n"))
        frags.append(("fg:ansigray", "  ↑↓ navigate  ⏎ select  ESC cancel\n\n"))

        for i, opt in enumerate(options):
            if i == state["cursor"]:
                frags.append(("bold fg:ansibrightcyan", f"  ❯ {opt}"))
            else:
                frags.append(("", f"    {opt}"))

            if descriptions and i < len(descriptions):
                frags.append(("fg:ansigray", f"  {descriptions[i]}"))

            frags.append(("", "\n"))

        return FormattedText(frags)

    # ── prompt_toolkit Application ────────────────────────────────────
    control = FormattedTextControl(_build_fragments)
    layout = Layout(Window(content=control, always_hide_cursor=True))

    app: Application[None] = Application(
        layout=layout,
        key_bindings=kb,
        full_screen=False,
        mouse_support=False,
    )

    try:
        app.run()
    except (EOFError, KeyboardInterrupt):
        return None

    return state["result"]
