"""
Jack The Shadow — Tool Helpers

Shared utility functions for tool implementations.
"""

from __future__ import annotations

from jack_the_shadow.config import MAX_OUTPUT_CHARS


def truncate(text: str, limit: int = MAX_OUTPUT_CHARS) -> str:
    """Truncate text to *limit* chars with a trailing summary."""
    if len(text) <= limit:
        return text
    lost = len(text) - limit
    pct = round(100 * lost / len(text))
    return (
        text[:limit]
        + f"\n\n⚠ TRUNCATED — showing {limit:,}/{len(text):,} chars ({pct}% cut). "
        f"Use file_write to save full output if needed."
    )


def result(status: str, output: str = "", message: str = "") -> dict[str, str]:
    """Build a standardised tool result dict."""
    return {"status": status, "output": output, "message": message}
