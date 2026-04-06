"""
Jack The Shadow — Web Search Tool

Search the web using DuckDuckGo (ddgs).
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from jack_the_shadow.config import WEB_SEARCH_MAX_RESULTS
from jack_the_shadow.tools.base import BaseTool
from jack_the_shadow.tools.helpers import result
from jack_the_shadow.utils.logger import get_logger

if TYPE_CHECKING:
    from jack_the_shadow.tools.executor import ToolExecutor

logger = get_logger("tools.web_search")


class WebSearchTool(BaseTool):
    name = "web_search"
    description = (
        "Search the web using DuckDuckGo and return results with titles, "
        "URLs, and snippets.  Use for finding current info, docs, CVEs, "
        "exploits, writeups, and anything beyond training data."
    )
    risk_aware = False

    @classmethod
    def parameters_schema(cls) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query string.",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Max results to return (default: 8).",
                },
                "region": {
                    "type": "string",
                    "description": "Region code, e.g. 'us-en', 'id-id' (default: 'wt-wt' global).",
                },
                "time_range": {
                    "type": "string",
                    "enum": ["d", "w", "m", "y"],
                    "description": "Time filter: d=day, w=week, m=month, y=year.",
                },
            },
            "required": ["query"],
        }


def handle_web_search(
    executor: "ToolExecutor",
    query: str,
    max_results: int = WEB_SEARCH_MAX_RESULTS,
    region: str = "wt-wt",
    time_range: str | None = None,
) -> dict[str, str]:
    start = time.time()
    logger.info("web_search: %s (max=%d)", query, max_results)

    try:
        from ddgs import DDGS
    except ImportError:
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            return result("error", message="ddgs not installed. Run: pip install ddgs")

    try:
        with DDGS() as ddgs:
            kwargs: dict[str, Any] = {"max_results": min(max_results, 20)}
            if time_range:
                kwargs["timelimit"] = time_range
            results = list(ddgs.text(query, **kwargs))

    except Exception as exc:
        logger.error("web_search error: %s", exc)
        return result("error", message=f"Search failed: {exc}")

    elapsed = time.time() - start

    if not results:
        return result("success", output=f"No results found for: {query}")

    parts = [
        f'Web search results for: "{query}"',
        f"({len(results)} results in {elapsed:.1f}s)",
        "",
    ]

    for i, r in enumerate(results, 1):
        title = r.get("title", "Untitled")
        href = r.get("href", r.get("link", ""))
        body = r.get("body", r.get("snippet", ""))
        parts.append(f"[{i}] {title}")
        parts.append(f"    URL: {href}")
        if body:
            parts.append(f"    {body[:300]}")
        parts.append("")

    parts.append("REMINDER: Include relevant source URLs in your response.")
    output = "\n".join(parts)
    logger.info("web_search OK — %d results for '%s'", len(results), query)
    return result("success", output=output)
