"""
Jack The Shadow — Interactive Terminal Selector

Arrow-key navigated menus using raw terminal mode.
No external dependencies — uses stdlib ``tty`` and ``termios``.
"""

from __future__ import annotations

import sys
import tty
import termios
from typing import Optional

from jack_the_shadow.ui.console import console


def interactive_select(
    options: list[str],
    *,
    title: str = "",
    selected: int = 0,
    descriptions: Optional[list[str]] = None,
) -> Optional[int]:
    """Show an interactive selector.  Navigate with ↑↓, Enter to select, ESC to cancel.

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

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    cursor = min(selected, len(options) - 1)

    hint = "[dim]  ↑↓ navigate  ⏎ select  ESC cancel[/]"
    console.print()
    if title:
        console.print(f"  [info]{title}[/]")
    console.print(hint)

    # Print initial blank lines that we'll overwrite
    for _ in options:
        sys.stdout.write("\n")
    sys.stdout.flush()

    lines_to_clear = len(options)

    def render() -> None:
        # Move up to start of options
        sys.stdout.write(f"\033[{lines_to_clear}A")
        for i, opt in enumerate(options):
            sys.stdout.write("\033[2K")  # clear line
            if i == cursor:
                label = f"\033[1;36m  ❯ {opt}\033[0m"
            else:
                label = f"    {opt}"
            if descriptions and i < len(descriptions):
                desc = descriptions[i]
                label += f"  \033[2m{desc}\033[0m"
            sys.stdout.write(label + "\n")
        sys.stdout.flush()

    try:
        tty.setcbreak(fd)
        render()

        while True:
            ch = sys.stdin.read(1)

            if ch == "\x1b":  # ESC sequence
                # Read with a tiny buffer — if another char follows, it's an arrow
                import select as _sel

                if _sel.select([sys.stdin], [], [], 0.05)[0]:
                    ch2 = sys.stdin.read(1)
                    if ch2 == "[":
                        ch3 = sys.stdin.read(1)
                        if ch3 == "A":  # Up
                            cursor = (cursor - 1) % len(options)
                        elif ch3 == "B":  # Down
                            cursor = (cursor + 1) % len(options)
                        # Ignore other sequences
                    # else: unknown sequence, ignore
                else:
                    # Plain ESC — cancel
                    _cleanup(lines_to_clear)
                    return None
            elif ch in ("\r", "\n"):  # Enter
                _cleanup(lines_to_clear)
                return cursor
            elif ch == "\x03":  # Ctrl+C
                _cleanup(lines_to_clear)
                return None
            elif ch == "q":
                _cleanup(lines_to_clear)
                return None

            render()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def _cleanup(lines: int) -> None:
    """Erase the selector area from the terminal."""
    sys.stdout.write(f"\033[{lines}A")
    for _ in range(lines):
        sys.stdout.write("\033[2K\n")
    sys.stdout.write(f"\033[{lines}A")
    sys.stdout.flush()
