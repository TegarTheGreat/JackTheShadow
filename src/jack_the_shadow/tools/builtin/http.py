"""
Jack The Shadow — HTTP Request Tool

Make HTTP requests with risk-level gating.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import requests as http_lib

from jack_the_shadow.config import MAX_OUTPUT_CHARS
from jack_the_shadow.i18n import t
from jack_the_shadow.tools.base import BaseTool
from jack_the_shadow.tools.helpers import result, truncate
from jack_the_shadow.utils.logger import get_logger

if TYPE_CHECKING:
    from jack_the_shadow.tools.executor import ToolExecutor

logger = get_logger("tools.http")


class HttpRequestTool(BaseTool):
    name = "http_request"
    description = (
        "Make an HTTP request (GET, POST, PUT, DELETE, HEAD, OPTIONS).  "
        "Useful for API probing, service detection, and web recon.  "
        "Returns status code, headers, and body."
    )
    risk_aware = True

    @classmethod
    def parameters_schema(cls) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Full URL to request.",
                },
                "method": {
                    "type": "string",
                    "enum": ["GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS"],
                    "description": "HTTP method (default: GET).",
                },
                "headers": {
                    "type": "object",
                    "description": "Custom headers as key-value pairs.",
                },
                "body": {
                    "type": "string",
                    "description": "Request body (for POST/PUT).",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds (default: 30).",
                },
                "follow_redirects": {
                    "type": "boolean",
                    "description": "Follow redirects (default: true).",
                },
            },
            "required": ["url"],
        }


def handle_http_request(
    executor: "ToolExecutor",
    url: str,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    body: str | None = None,
    timeout: int = 30,
    follow_redirects: bool = True,
    risk_level: str = "Medium",
) -> dict[str, str]:
    detail = f"{method} {url}"
    if not executor.request_approval("http_request", detail, risk_level):
        return result("error", message=t("tool.denied"))

    try:
        resp = http_lib.request(
            method=method.upper(),
            url=url,
            headers=headers or {},
            data=body.encode("utf-8") if body else None,
            timeout=min(timeout, 60),
            allow_redirects=follow_redirects,
            verify=False,
        )

        parts: list[str] = [
            f"[status] {resp.status_code} {resp.reason}",
            f"[url] {resp.url}",
            "",
            "[headers]",
        ]
        for k, v in resp.headers.items():
            parts.append(f"  {k}: {v}")

        parts.append("")
        parts.append("[body]")
        parts.append(truncate(resp.text, MAX_OUTPUT_CHARS - 2000))

        output = "\n".join(parts)
        logger.info("http_request OK — %s %s → %d", method, url, resp.status_code)
        return result("success", output=output)

    except http_lib.exceptions.Timeout:
        return result("error", message=f"Request timed out after {timeout}s")
    except http_lib.exceptions.ConnectionError as exc:
        return result("error", message=f"Connection error: {exc}")
    except http_lib.exceptions.RequestException as exc:
        return result("error", message=f"HTTP error: {exc}")
