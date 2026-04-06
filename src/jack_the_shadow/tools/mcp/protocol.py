"""
Jack The Shadow — MCP JSON-RPC 2.0 Protocol Helpers

Low-level helpers for JSON-RPC 2.0 message formatting.
"""

from __future__ import annotations

import threading
from typing import Any

_REQUEST_ID = 0
_ID_LOCK = threading.Lock()


def next_id() -> int:
    global _REQUEST_ID
    with _ID_LOCK:
        _REQUEST_ID += 1
        return _REQUEST_ID


def jsonrpc_request(method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    msg: dict[str, Any] = {
        "jsonrpc": "2.0",
        "id": next_id(),
        "method": method,
    }
    if params is not None:
        msg["params"] = params
    return msg
