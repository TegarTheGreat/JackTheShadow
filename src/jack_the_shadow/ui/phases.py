"""
Jack The Shadow — Phase Indicator

Shows the current AI activity phase in the terminal:
thinking → streaming → tool_input → tool_use → done.
Inspired by claude-code's SpinnerMode enum.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from jack_the_shadow.ui.console import console


class Phase(Enum):
    """Current activity phase."""
    THINKING = "thinking"
    STREAMING = "streaming"
    TOOL_INPUT = "tool_input"
    TOOL_USE = "tool_use"
    DONE = "done"
    ERROR = "error"

    @property
    def icon(self) -> str:
        return {
            Phase.THINKING: "🤔",
            Phase.STREAMING: "✍️",
            Phase.TOOL_INPUT: "📥",
            Phase.TOOL_USE: "⚙️",
            Phase.DONE: "✅",
            Phase.ERROR: "❌",
        }.get(self, "")

    @property
    def label(self) -> str:
        return {
            Phase.THINKING: "Thinking...",
            Phase.STREAMING: "Responding...",
            Phase.TOOL_INPUT: "Processing tool input...",
            Phase.TOOL_USE: "Executing tool...",
            Phase.DONE: "Done",
            Phase.ERROR: "Error",
        }.get(self, "")


class PhaseIndicator:
    """Tracks and displays the current phase."""

    def __init__(self) -> None:
        self._phase: Phase = Phase.THINKING
        self._detail: str = ""
        self._visible: bool = False

    @property
    def phase(self) -> Phase:
        return self._phase

    def set(self, phase: Phase, detail: str = "") -> None:
        """Update the displayed phase."""
        self._phase = phase
        self._detail = detail
        if self._visible:
            self._render()

    def show(self) -> None:
        self._visible = True
        self._render()

    def hide(self) -> None:
        self._visible = False

    def _render(self) -> None:
        detail = f" — {self._detail}" if self._detail else ""
        console.print(
            f"  [dim]{self._phase.icon} {self._phase.label}{detail}[/]",
            end="\r",
        )


# Module-level singleton
_indicator: Optional[PhaseIndicator] = None


def get_phase_indicator() -> PhaseIndicator:
    global _indicator
    if _indicator is None:
        _indicator = PhaseIndicator()
    return _indicator
