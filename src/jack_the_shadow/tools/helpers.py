"""
Jack The Shadow — Tool Helpers

Shared utility functions for tool implementations.
"""

from __future__ import annotations

from jack_the_shadow.config import MAX_OUTPUT_CHARS


def truncate(text: str, limit: int = MAX_OUTPUT_CHARS) -> str:
    """Truncate text to *limit* chars with a trailing note."""
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n\n... [truncated — {len(text)} total chars]"


def result(status: str, output: str = "", message: str = "") -> dict[str, str]:
    """Build a standardised tool result dict."""
    return {"status": status, "output": output, "message": message}
