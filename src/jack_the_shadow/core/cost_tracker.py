"""
Jack The Shadow — Cost & Token Tracker

Tracks API calls, estimated tokens, and model usage per session.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class APICallRecord:
    """Single API call record."""
    timestamp: float
    model: str
    input_tokens: int
    output_tokens: int
    duration_ms: float
    success: bool


class CostTracker:
    """Tracks API usage statistics for the session."""

    def __init__(self) -> None:
        self._calls: list[APICallRecord] = []
        self._session_start: float = time.time()

    def record_call(
        self,
        model: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        duration_ms: float = 0.0,
        success: bool = True,
    ) -> None:
        self._calls.append(APICallRecord(
            timestamp=time.time(),
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            duration_ms=duration_ms,
            success=success,
        ))

    def estimate_tokens(self, text: str) -> int:
        """Rough token estimate (~4 chars per token for English)."""
        return max(1, len(text) // 4)

    @property
    def total_calls(self) -> int:
        return len(self._calls)

    @property
    def successful_calls(self) -> int:
        return sum(1 for c in self._calls if c.success)

    @property
    def failed_calls(self) -> int:
        return sum(1 for c in self._calls if not c.success)

    @property
    def total_input_tokens(self) -> int:
        return sum(c.input_tokens for c in self._calls)

    @property
    def total_output_tokens(self) -> int:
        return sum(c.output_tokens for c in self._calls)

    @property
    def total_tokens(self) -> int:
        return self.total_input_tokens + self.total_output_tokens

    @property
    def avg_latency_ms(self) -> float:
        if not self._calls:
            return 0.0
        return sum(c.duration_ms for c in self._calls) / len(self._calls)

    @property
    def session_duration_s(self) -> float:
        return time.time() - self._session_start

    def get_model_breakdown(self) -> dict[str, dict[str, Any]]:
        """Get usage breakdown by model."""
        breakdown: dict[str, dict[str, Any]] = {}
        for call in self._calls:
            if call.model not in breakdown:
                breakdown[call.model] = {"calls": 0, "input_tokens": 0, "output_tokens": 0}
            breakdown[call.model]["calls"] += 1
            breakdown[call.model]["input_tokens"] += call.input_tokens
            breakdown[call.model]["output_tokens"] += call.output_tokens
        return breakdown

    def format_summary(self) -> str:
        """Format a human-readable usage summary."""
        mins = self.session_duration_s / 60
        lines = [
            f"Session Duration : {mins:.1f} min",
            f"API Calls        : {self.total_calls} ({self.successful_calls} ok, {self.failed_calls} failed)",
            f"Total Tokens     : ~{self.total_tokens:,} (in: ~{self.total_input_tokens:,}, out: ~{self.total_output_tokens:,})",
            f"Avg Latency      : {self.avg_latency_ms:.0f}ms",
        ]
        breakdown = self.get_model_breakdown()
        if breakdown:
            lines.append("\nBy Model:")
            for model, stats in breakdown.items():
                short = model.split("/")[-1] if "/" in model else model
                lines.append(f"  {short}: {stats['calls']} calls, ~{stats['input_tokens']+stats['output_tokens']:,} tokens")
        return "\n".join(lines)
