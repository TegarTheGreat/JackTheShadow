"""
Jack The Shadow — Cloudflare Workers AI Engine

Handles all communication with the Cloudflare Workers AI REST API,
including retry logic with exponential backoff.
"""

from __future__ import annotations

import json
import time
from typing import Any, Optional

import requests

from jack_the_shadow.config import (
    API_ENDPOINT,
    MAX_RETRIES,
    RETRY_BACKOFF_BASE,
)
from jack_the_shadow.utils.logger import get_logger

logger = get_logger("core.engine")

_RETRYABLE_STATUSES = {500, 502, 503, 504, 429}


class CloudflareAIError(Exception):
    """Raised when the Cloudflare API returns an unrecoverable error."""

    def __init__(self, message: str, status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class CloudflareAI:
    """Client for the Cloudflare Workers AI chat-completion endpoint."""

    def __init__(
        self,
        account_id: str,
        api_token: str,
        model: str = "",
    ) -> None:
        if not account_id or not api_token:
            raise CloudflareAIError(
                "Cloudflare credentials are required. "
                "Use the /login command or set CLOUDFLARE_ACCOUNT_ID "
                "and CLOUDFLARE_API_TOKEN environment variables."
            )
        self.account_id = account_id
        self.api_token = api_token
        self.model = model
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        })
        logger.info("CloudflareAI initialised — model=%s", self.model)

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: Optional[list[dict[str, Any]]] = None,
        cost_tracker: Optional[Any] = None,
    ) -> dict[str, Any]:
        """Send a chat-completion request and return the parsed response."""
        payload = self._build_payload(messages, tools)
        start = time.time()
        raw = self._make_request(payload)
        duration_ms = (time.time() - start) * 1000
        result = self._parse_response(raw)

        if cost_tracker is not None:
            try:
                in_tokens = sum(len(m.get("content", "")) // 4 for m in messages)
                out_tokens = len(result.get("content", "")) // 4
                cost_tracker.record_call(
                    model=self.model,
                    input_tokens=in_tokens,
                    output_tokens=out_tokens,
                    duration_ms=duration_ms,
                    success=True,
                )
            except Exception:
                pass
        return result

    def _build_endpoint(self) -> str:
        return API_ENDPOINT.format(
            account_id=self.account_id,
            model=self.model,
        )

    def _build_payload(
        self,
        messages: list[dict[str, Any]],
        tools: Optional[list[dict[str, Any]]] = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"messages": messages}
        if tools:
            payload["tools"] = tools
        return payload

    def _make_request(self, payload: dict[str, Any]) -> dict[str, Any]:
        """POST to Cloudflare with retry on transient failures."""
        endpoint = self._build_endpoint()
        last_error: Optional[Exception] = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.debug(
                    "API request attempt %d/%d → %s",
                    attempt, MAX_RETRIES, endpoint,
                )
                resp = self._session.post(endpoint, json=payload, timeout=60)

                if resp.status_code in (401, 403):
                    raise CloudflareAIError(
                        f"Authentication failed (HTTP {resp.status_code}). "
                        "Use /login to update your credentials.",
                        status_code=resp.status_code,
                    )

                if resp.status_code in _RETRYABLE_STATUSES:
                    wait = RETRY_BACKOFF_BASE ** attempt
                    logger.warning(
                        "HTTP %d — retrying in %.1fs (attempt %d/%d)",
                        resp.status_code, wait, attempt, MAX_RETRIES,
                    )
                    last_error = CloudflareAIError(
                        f"HTTP {resp.status_code}", status_code=resp.status_code
                    )
                    time.sleep(wait)
                    continue

                resp.raise_for_status()
                data = resp.json()
                logger.debug("API response received (%d bytes)", len(resp.text))
                return data

            except requests.exceptions.Timeout:
                wait = RETRY_BACKOFF_BASE ** attempt
                logger.warning(
                    "Request timeout — retrying in %.1fs (attempt %d/%d)",
                    wait, attempt, MAX_RETRIES,
                )
                last_error = CloudflareAIError("Request timed out")
                time.sleep(wait)

            except requests.exceptions.ConnectionError as exc:
                wait = RETRY_BACKOFF_BASE ** attempt
                logger.warning(
                    "Connection error — retrying in %.1fs (attempt %d/%d): %s",
                    wait, attempt, MAX_RETRIES, exc,
                )
                last_error = CloudflareAIError(f"Connection error: {exc}")
                time.sleep(wait)

            except CloudflareAIError:
                raise

            except requests.exceptions.RequestException as exc:
                raise CloudflareAIError(f"HTTP error: {exc}") from exc

        raise CloudflareAIError(
            f"All {MAX_RETRIES} retry attempts exhausted. Last error: {last_error}"
        )

    def _parse_response(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Extract the assistant message from Cloudflare's response envelope."""
        if not raw.get("success", False):
            errors = raw.get("errors", [])
            msg = (
                "; ".join(e.get("message", str(e)) for e in errors)
                if errors
                else "Unknown API error"
            )
            raise CloudflareAIError(f"API error: {msg}")

        result = raw.get("result", {})
        assistant_msg: dict[str, Any] = {"role": "assistant"}

        content = result.get("response", "")
        if content:
            assistant_msg["content"] = content

        tool_calls = result.get("tool_calls")
        if tool_calls:
            normalised: list[dict[str, Any]] = []
            for i, tc in enumerate(tool_calls):
                entry: dict[str, Any] = {
                    "id": tc.get("id", f"call_{i}"),
                    "type": "function",
                    "function": {
                        "name": tc.get("name", tc.get("function", {}).get("name", "")),
                        "arguments": tc.get(
                            "arguments",
                            tc.get("function", {}).get("arguments", "{}"),
                        ),
                    },
                }
                if isinstance(entry["function"]["arguments"], dict):
                    entry["function"]["arguments"] = json.dumps(
                        entry["function"]["arguments"]
                    )
                normalised.append(entry)
            assistant_msg["tool_calls"] = normalised

        if "content" not in assistant_msg and "tool_calls" not in assistant_msg:
            assistant_msg["content"] = "(Jack tidak memberikan respons.)"

        return assistant_msg
