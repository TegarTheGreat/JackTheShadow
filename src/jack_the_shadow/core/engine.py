"""
Jack The Shadow — Cloudflare Workers AI Engine

Uses the OpenAI-compatible ``/ai/v1/chat/completions`` endpoint for
proper tool-calling, streaming (SSE), and standard response format.
Includes retry logic with exponential backoff.
"""

from __future__ import annotations

import json
import time
from typing import Any, Callable, Optional

import requests

from jack_the_shadow.config import (
    API_ENDPOINT,
    MAX_RETRIES,
    MAX_TOKENS,
    RETRY_BACKOFF_BASE,
    STREAM_RESPONSES,
    TEMPERATURE,
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
    """Client for the Cloudflare Workers AI chat-completion endpoint.

    Uses the OpenAI-compatible ``/ai/v1/chat/completions`` endpoint by default.
    """

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

    # ── Public API ────────────────────────────────────────────────────

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: Optional[list[dict[str, Any]]] = None,
        cost_tracker: Optional[Any] = None,
    ) -> dict[str, Any]:
        """Send a chat-completion request and return the parsed response."""
        clean = self._sanitise_messages(messages)
        payload = self._build_payload(clean, tools)
        start = time.time()
        raw = self._make_request(payload)
        duration_ms = (time.time() - start) * 1000
        result = self._parse_response(raw)

        if cost_tracker is not None:
            self._track_cost(cost_tracker, raw, messages, result, duration_ms)
        return result

    def chat_stream(
        self,
        messages: list[dict[str, Any]],
        tools: Optional[list[dict[str, Any]]] = None,
        cost_tracker: Optional[Any] = None,
        on_token: Optional[Callable[[str], None]] = None,
    ) -> dict[str, Any]:
        """Streaming chat that always returns a complete assistant message dict.

        Unlike a generator, this is a regular function so ``return`` works
        correctly for both text-only and tool-call responses.

        Args:
            on_token: Optional callback invoked with each text chunk as it
                      arrives from the SSE stream.  Used by the UI to display
                      tokens in real-time.
        """
        clean = self._sanitise_messages(messages)
        payload = self._build_payload(clean, tools, stream=True)
        endpoint = self._build_endpoint()
        start = time.time()

        try:
            resp = self._session.post(
                endpoint, json=payload, timeout=120, stream=True,
            )
            if resp.status_code != 200:
                resp.close()
                logger.warning("Stream HTTP %d, falling back to non-stream", resp.status_code)
                return self.chat(messages, tools, cost_tracker)

            content_parts: list[str] = []
            tool_call_chunks: dict[int, dict[str, Any]] = {}
            finish_reason: Optional[str] = None

            for line in resp.iter_lines(decode_unicode=True):
                if not line or not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str.strip() == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                except json.JSONDecodeError:
                    continue

                choices = chunk.get("choices", [{}])
                if not choices:
                    continue
                delta = choices[0].get("delta", {})
                fr = choices[0].get("finish_reason")
                if fr:
                    finish_reason = fr

                # Text content
                text = delta.get("content")
                if text:
                    content_parts.append(text)
                    if on_token is not None:
                        on_token(text)

                # Accumulate tool_call deltas
                tc_deltas = delta.get("tool_calls")
                if tc_deltas:
                    for tcd in tc_deltas:
                        idx = tcd.get("index", 0)
                        if idx not in tool_call_chunks:
                            tool_call_chunks[idx] = {
                                "id": tcd.get("id", f"call_{idx}"),
                                "type": "function",
                                "function": {"name": "", "arguments": ""},
                            }
                        fn = tcd.get("function", {})
                        if fn.get("name"):
                            tool_call_chunks[idx]["function"]["name"] += fn["name"]
                        if fn.get("arguments"):
                            tool_call_chunks[idx]["function"]["arguments"] += fn["arguments"]

            resp.close()
            duration_ms = (time.time() - start) * 1000

            # Build the assistant message
            msg: dict[str, Any] = {
                "role": "assistant",
                "content": "".join(content_parts) or "",
            }

            if tool_call_chunks:
                msg["tool_calls"] = [
                    tool_call_chunks[i]
                    for i in sorted(tool_call_chunks.keys())
                ]

            if cost_tracker is not None:
                self._track_cost_estimated(cost_tracker, messages, msg, duration_ms)

            # If no content and no tool_calls, something went wrong
            if not msg["content"] and "tool_calls" not in msg:
                logger.warning("Empty stream response, finish_reason=%s", finish_reason)
                msg["content"] = ""

            return msg

        except requests.exceptions.RequestException as exc:
            logger.warning("Stream error (%s), falling back to non-stream", exc)
            return self.chat(messages, tools, cost_tracker)

    # ── Internal helpers ──────────────────────────────────────────────

    def _build_endpoint(self) -> str:
        return API_ENDPOINT.format(account_id=self.account_id)

    def _build_payload(
        self,
        messages: list[dict[str, Any]],
        tools: Optional[list[dict[str, Any]]] = None,
        stream: bool = False,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_tokens": MAX_TOKENS,
            "temperature": TEMPERATURE,
        }
        if tools:
            payload["tools"] = tools
        if stream:
            payload["stream"] = True
        return payload

    @staticmethod
    def _sanitise_messages(
        messages: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Ensure every message has a valid ``content`` string.

        The Cloudflare API rejects ``content: null``; assistant messages
        with tool_calls often arrive with null content.
        """
        clean: list[dict[str, Any]] = []
        for m in messages:
            msg = dict(m)
            if msg.get("content") is None:
                msg["content"] = ""
            clean.append(msg)
        return clean

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
                resp = self._session.post(endpoint, json=payload, timeout=120)

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
                        f"HTTP {resp.status_code}", status_code=resp.status_code,
                    )
                    time.sleep(wait)
                    continue

                if resp.status_code == 400:
                    # Log the full error for debugging, then raise
                    body = resp.text[:1000]
                    logger.error("API 400 Bad Request: %s", body)
                    raise CloudflareAIError(
                        f"Bad request (400): {body}",
                        status_code=400,
                    )

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
        """Extract the assistant message from the API response.

        Handles three response shapes:
        1. OpenAI v1 direct: ``{choices: [{message: ...}], usage: ...}``
        2. Cloudflare-wrapped OpenAI: ``{result: {choices: [...]}, success: true}``
        3. Legacy Cloudflare: ``{result: {response: "..."}, success: true}``
        """
        # ── Check for Cloudflare-level errors ─────────────────────────
        if "success" in raw and not raw["success"]:
            errors = raw.get("errors", [])
            msg = (
                "; ".join(e.get("message", str(e)) for e in errors)
                if errors
                else "Unknown API error"
            )
            raise CloudflareAIError(f"API error: {msg}")

        # ── Unwrap: find the actual result object ─────────────────────
        # v1 endpoint returns choices at root; legacy wraps in result{}
        if "choices" in raw:
            result = raw
        elif "result" in raw:
            result = raw["result"]
        else:
            result = raw

        assistant_msg: dict[str, Any] = {"role": "assistant", "content": ""}

        # ── OpenAI format (choices[].message) ─────────────────────────
        choices = result.get("choices")
        if choices and isinstance(choices, list) and len(choices) > 0:
            msg = choices[0].get("message", {})
            content = msg.get("content") or ""
            tool_calls = msg.get("tool_calls")
            if isinstance(tool_calls, list) and len(tool_calls) == 0:
                tool_calls = None
        else:
            # ── Legacy format (result.response) ───────────────────────
            content = result.get("response") or ""
            tool_calls = result.get("tool_calls")

        assistant_msg["content"] = content

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

        if not assistant_msg["content"] and "tool_calls" not in assistant_msg:
            logger.warning("Empty AI response: %s", json.dumps(result)[:500])
            assistant_msg["content"] = "(Jack tidak memberikan respons.)"

        return assistant_msg

    def _track_cost(
        self,
        cost_tracker: Any,
        raw: dict[str, Any],
        messages: list[dict[str, Any]],
        result: dict[str, Any],
        duration_ms: float,
    ) -> None:
        try:
            # v1 puts usage at root; legacy inside result
            usage = raw.get("usage") or raw.get("result", {}).get("usage", {})
            in_tokens = usage.get("prompt_tokens") or sum(
                len(str(m.get("content", ""))) // 4 for m in messages
            )
            out_tokens = usage.get("completion_tokens") or len(
                result.get("content", "")
            ) // 4
            cost_tracker.record_call(
                model=self.model,
                input_tokens=in_tokens,
                output_tokens=out_tokens,
                duration_ms=duration_ms,
                success=True,
            )
        except Exception:
            pass

    def _track_cost_estimated(
        self,
        cost_tracker: Any,
        messages: list[dict[str, Any]],
        result: dict[str, Any],
        duration_ms: float,
    ) -> None:
        try:
            in_tokens = sum(
                len(str(m.get("content", ""))) // 4 for m in messages
            )
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
