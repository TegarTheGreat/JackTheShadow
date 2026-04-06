"""
Jack The Shadow — Web Fetch Tool

Fetch URL content, convert HTML → Markdown, with Cloudflare bypass.
"""

from __future__ import annotations

import re
import time
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

import requests as http_lib

from jack_the_shadow.config import WEB_FETCH_MAX_LENGTH, WEB_FETCH_TIMEOUT
from jack_the_shadow.tools.base import BaseTool
from jack_the_shadow.tools.helpers import result, truncate
from jack_the_shadow.utils.logger import get_logger

if TYPE_CHECKING:
    from jack_the_shadow.tools.executor import ToolExecutor

logger = get_logger("tools.web_fetch")

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,text/markdown,application/xhtml+xml,*/*",
    "Accept-Language": "en-US,en;q=0.9",
}


class WebFetchTool(BaseTool):
    name = "web_fetch"
    description = (
        "Fetch content from a URL, convert HTML to clean Markdown, and "
        "optionally extract specific info using a prompt.  Handles "
        "Cloudflare-protected sites via cloudscraper bypass.  "
        "Great for reading docs, scraping pages, and web recon."
    )
    risk_aware = False

    @classmethod
    def parameters_schema(cls) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to fetch content from.",
                },
                "prompt": {
                    "type": "string",
                    "description": (
                        "Optional: what to extract from the page. "
                        "If empty, returns the full markdown content."
                    ),
                },
                "max_length": {
                    "type": "integer",
                    "description": "Max chars to return (default: 50000).",
                },
                "raw": {
                    "type": "boolean",
                    "description": "Return raw HTML instead of markdown (default: false).",
                },
            },
            "required": ["url"],
        }


def handle_web_fetch(
    executor: "ToolExecutor",
    url: str,
    prompt: str = "",
    max_length: int = WEB_FETCH_MAX_LENGTH,
    raw: bool = False,
) -> dict[str, str]:
    start = time.time()
    logger.info("web_fetch: %s", url)

    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return result("error", message=f"Invalid URL scheme: {parsed.scheme}")
    except Exception:
        return result("error", message=f"Invalid URL: {url}")

    content, status_code, content_type = _fetch_url_content(url)
    if content is None:
        return result("error", message=f"Failed to fetch {url}")

    elapsed = time.time() - start

    if raw:
        output = truncate(content, max_length)
        return result("success", output=(
            f"[status] {status_code}\n"
            f"[content-type] {content_type}\n"
            f"[length] {len(content)} chars\n"
            f"[time] {elapsed:.1f}s\n\n"
            f"{output}"
        ))

    if "html" in content_type.lower():
        markdown = _html_to_markdown(content)
    else:
        markdown = content

    if len(markdown) > max_length:
        markdown = markdown[:max_length] + "\n\n[...content truncated...]"

    parts = [
        f"[url] {url}",
        f"[status] {status_code}",
        f"[length] {len(markdown)} chars",
        f"[time] {elapsed:.1f}s",
        "",
    ]

    if prompt:
        parts.append(f"[extraction prompt] {prompt}")
        parts.append("")

    parts.append(markdown)
    output = "\n".join(parts)
    logger.info("web_fetch OK — %s (%d chars, %.1fs)", url, len(markdown), elapsed)
    return result("success", output=output)


def _fetch_url_content(url: str) -> tuple[str | None, int, str]:
    """Fetch URL content with cloudscraper fallback for CF protection."""
    try:
        import cloudscraper
        scraper = cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "linux", "desktop": True},
        )
        resp = scraper.get(url, headers=_HEADERS, timeout=WEB_FETCH_TIMEOUT, verify=False)
        return resp.text, resp.status_code, resp.headers.get("content-type", "text/html")
    except Exception as exc:
        logger.debug("cloudscraper failed for %s: %s — trying requests", url, exc)

    try:
        resp = http_lib.get(
            url, headers=_HEADERS, timeout=WEB_FETCH_TIMEOUT,
            verify=False, allow_redirects=True,
        )
        return resp.text, resp.status_code, resp.headers.get("content-type", "text/html")
    except Exception as exc:
        logger.error("web_fetch failed for %s: %s", url, exc)
        return None, 0, ""


def _html_to_markdown(html: str) -> str:
    """Convert HTML to clean Markdown using bs4 + markdownify."""
    try:
        from bs4 import BeautifulSoup
        from markdownify import markdownify as md

        soup = BeautifulSoup(html, "html.parser")

        for tag in soup.find_all(
            ["script", "style", "nav", "footer", "iframe", "noscript", "svg"]
        ):
            tag.decompose()

        markdown = md(str(soup), heading_style="ATX", strip=["img"])
        markdown = re.sub(r"\n{3,}", "\n\n", markdown)
        markdown = re.sub(r" {2,}", " ", markdown)
        return markdown.strip()

    except ImportError:
        logger.warning("bs4/markdownify not installed — returning raw HTML")
        return html
