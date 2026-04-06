"""
Jack The Shadow — Interactive Terminal Selector

Arrow-key navigated menus using prompt_toolkit Application.
Supports viewport scrolling for long lists (auto-adapts to terminal height).
Fully compatible with the main prompt_toolkit PromptSession.
"""

from __future__ import annotations

import shutil
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
    skip_indices: Optional[set[int]] = None,
) -> Optional[int]:
    """Show an interactive selector with viewport scrolling.

    Navigate with ↑↓ (or j/k), Enter to select, ESC to cancel.
    Long lists auto-scroll to keep the cursor visible.

    Args:
        options: Display labels for each option.
        title: Optional header above the list.
        selected: Initial cursor position.
        descriptions: Optional right-aligned descriptions.
        skip_indices: Set of indices that are headers (not selectable).

    Returns:
        Index of the selected option, or ``None`` if cancelled.
    """
    if not options:
        return None

    skip = skip_indices or set()

    # Calculate viewport size (leave room for header + hints + padding)
    term_height = shutil.get_terminal_size().lines
    header_lines = 3 if title else 2  # title + hints + blank line
    max_visible = max(5, term_height - header_lines - 4)

    def _next_selectable(pos: int, direction: int) -> int:
        """Find next selectable index in given direction."""
        for _ in range(len(options)):
            pos = (pos + direction) % len(options)
            if pos not in skip:
                return pos
        return pos

    # Ensure initial selection is on a selectable item
    if selected in skip:
        selected = _next_selectable(selected, 1)

    state = {
        "cursor": min(selected, len(options) - 1),
        "result": None,
        "scroll_offset": 0,
    }

    # ── Key bindings ──────────────────────────────────────────────────
    kb = KeyBindings()

    def _adjust_scroll() -> None:
        """Keep cursor within visible viewport."""
        if state["cursor"] < state["scroll_offset"]:
            state["scroll_offset"] = state["cursor"]
        elif state["cursor"] >= state["scroll_offset"] + max_visible:
            state["scroll_offset"] = state["cursor"] - max_visible + 1

    @kb.add("up")
    @kb.add("k")
    def _move_up(event: object) -> None:
        state["cursor"] = _next_selectable(state["cursor"], -1)
        _adjust_scroll()

    @kb.add("down")
    @kb.add("j")
    def _move_down(event: object) -> None:
        state["cursor"] = _next_selectable(state["cursor"], 1)
        _adjust_scroll()

    @kb.add("home")
    def _go_top(event: object) -> None:
        state["cursor"] = _next_selectable(-1, 1)
        state["scroll_offset"] = 0

    @kb.add("end")
    def _go_bottom(event: object) -> None:
        state["cursor"] = _next_selectable(len(options), -1)
        _adjust_scroll()

    @kb.add("pageup")
    def _page_up(event: object) -> None:
        target = max(0, state["cursor"] - max_visible)
        state["cursor"] = target if target not in skip else _next_selectable(target, 1)
        _adjust_scroll()

    @kb.add("pagedown")
    def _page_down(event: object) -> None:
        target = min(len(options) - 1, state["cursor"] + max_visible)
        state["cursor"] = target if target not in skip else _next_selectable(target, -1)
        _adjust_scroll()

    @kb.add("enter")
    def _select(event: object) -> None:
        if state["cursor"] in skip:
            return  # Don't select headers
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

        # Scroll indicators
        total = len(options)
        showing = min(max_visible, total)
        hint_parts = ["↑↓ navigate", "⏎ select", "ESC cancel"]
        if total > max_visible:
            hint_parts.append(f"{state['cursor'] + 1}/{total}")
        frags.append(("fg:ansigray", f"  {'  '.join(hint_parts)}\n\n"))

        # Scrollable viewport
        start = state["scroll_offset"]
        end = min(start + max_visible, total)

        # Show scroll-up indicator
        if start > 0:
            frags.append(("fg:ansigray", f"  ▲ {start} more above\n"))

        for i in range(start, end):
            opt = options[i]
            is_header = i in skip
            if is_header:
                frags.append(("bold fg:ansiyellow", f"  {opt}"))
            elif i == state["cursor"]:
                frags.append(("bold fg:ansibrightcyan", f"  ❯ {opt}"))
            else:
                frags.append(("", f"    {opt}"))

            if descriptions and i < len(descriptions) and not is_header:
                frags.append(("fg:ansigray", f"  {descriptions[i]}"))

            frags.append(("", "\n"))

        # Show scroll-down indicator
        remaining = total - end
        if remaining > 0:
            frags.append(("fg:ansigray", f"  ▼ {remaining} more below\n"))

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
