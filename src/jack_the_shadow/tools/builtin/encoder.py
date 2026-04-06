"""
Jack The Shadow — Encoder/Decoder Tool

Encode or decode data using common formats for payload crafting and analysis.
"""

from __future__ import annotations

import base64
import binascii
import codecs
import hashlib
import html
import json
import urllib.parse
from typing import TYPE_CHECKING, Any, ClassVar

from jack_the_shadow.tools.base import BaseTool
from jack_the_shadow.tools.helpers import result, truncate
from jack_the_shadow.utils.logger import get_logger

if TYPE_CHECKING:
    from jack_the_shadow.tools.executor import ToolExecutor

logger = get_logger("tools.encoder")

VALID_FORMATS = (
    "base64", "url", "hex", "html", "unicode",
    "binary", "rot13", "jwt_decode", "md5", "sha1", "sha256",
)
HASH_ONLY_FORMATS = ("md5", "sha1", "sha256")
DECODE_ONLY_FORMATS = ("jwt_decode",)


# ── Schema ───────────────────────────────────────────────────────────

class EncoderDecoderTool(BaseTool):
    name: ClassVar[str] = "encode_decode"
    description: ClassVar[str] = (
        "Encode or decode data using common formats. "
        "Essential for payload crafting, data analysis, and CTF challenges."
    )
    risk_aware: ClassVar[bool] = False

    @classmethod
    def parameters_schema(cls) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "data": {
                    "type": "string",
                    "description": "Input data to encode or decode.",
                },
                "operation": {
                    "type": "string",
                    "enum": ["encode", "decode"],
                    "description": "Whether to encode or decode the data.",
                },
                "format": {
                    "type": "string",
                    "enum": list(VALID_FORMATS),
                    "description": "Format to use for encoding/decoding.",
                },
            },
            "required": ["data", "operation", "format"],
        }


# ── Handler ──────────────────────────────────────────────────────────

def handle_encode_decode(
    executor: "ToolExecutor",
    data: str,
    operation: str,
    format: str,
) -> dict[str, str]:
    """Encode or decode data in the specified format."""
    operation = operation.lower().strip()
    format = format.lower().strip()

    if format not in VALID_FORMATS:
        return result("error", message=f"Unknown format: {format}. Valid: {', '.join(VALID_FORMATS)}")

    if operation not in ("encode", "decode"):
        return result("error", message="Operation must be 'encode' or 'decode'.")

    if operation == "encode" and format in DECODE_ONLY_FORMATS:
        return result("error", message=f"Format '{format}' only supports decode.")

    if operation == "decode" and format in HASH_ONLY_FORMATS:
        return result("error", message=f"Hash format '{format}' is one-way; decode is not supported.")

    try:
        output_data = _dispatch(data, operation, format)
    except Exception as exc:
        logger.warning("encode_decode error — %s:%s — %s", operation, format, exc)
        return result("error", message=f"Failed to {operation} as {format}: {exc}")

    logger.info("encode_decode OK — %s:%s", operation, format)
    return result("success", output=truncate(f"[{operation}:{format}] {output_data}"))


def _dispatch(data: str, operation: str, fmt: str) -> str:
    """Route to the correct encode/decode implementation."""
    if fmt == "base64":
        return _base64(data, operation)
    if fmt == "url":
        return _url(data, operation)
    if fmt == "hex":
        return _hex(data, operation)
    if fmt == "html":
        return _html(data, operation)
    if fmt == "unicode":
        return _unicode(data, operation)
    if fmt == "binary":
        return _binary(data, operation)
    if fmt == "rot13":
        return _rot13(data)
    if fmt == "jwt_decode":
        return _jwt_decode(data)
    if fmt == "md5":
        return hashlib.md5(data.encode()).hexdigest()
    if fmt == "sha1":
        return hashlib.sha1(data.encode()).hexdigest()
    if fmt == "sha256":
        return hashlib.sha256(data.encode()).hexdigest()
    raise ValueError(f"Unhandled format: {fmt}")


# ── Format implementations ───────────────────────────────────────────

def _base64(data: str, operation: str) -> str:
    if operation == "encode":
        return base64.b64encode(data.encode()).decode()
    return base64.b64decode(data).decode("utf-8", errors="replace")


def _url(data: str, operation: str) -> str:
    if operation == "encode":
        return urllib.parse.quote(data, safe="")
    return urllib.parse.unquote(data)


def _hex(data: str, operation: str) -> str:
    if operation == "encode":
        return data.encode().hex()
    try:
        return bytes.fromhex(data).decode("utf-8", errors="replace")
    except ValueError as exc:
        raise ValueError(f"Invalid hex string: {exc}") from exc


def _html(data: str, operation: str) -> str:
    if operation == "encode":
        return html.escape(data)
    return html.unescape(data)


def _unicode(data: str, operation: str) -> str:
    if operation == "encode":
        return "".join(f"\\u{ord(c):04x}" for c in data)
    return data.encode().decode("unicode_escape", errors="replace")


def _binary(data: str, operation: str) -> str:
    if operation == "encode":
        return " ".join(format(b, "08b") for b in data.encode())
    # Decode: split on whitespace, convert each 8-bit chunk
    try:
        chunks = data.split()
        byte_vals = bytes(int(b, 2) for b in chunks)
        return byte_vals.decode("utf-8", errors="replace")
    except ValueError as exc:
        raise ValueError(f"Invalid binary string: {exc}") from exc


def _rot13(data: str) -> str:
    return codecs.encode(data, "rot_13")


def _jwt_decode(data: str) -> str:
    parts = data.split(".")
    if len(parts) < 2:
        raise ValueError("Invalid JWT: expected at least 2 dot-separated segments")

    decoded_parts: list[str] = []
    labels = ("Header", "Payload")
    for label, segment in zip(labels, parts[:2]):
        # Restore base64 padding
        padded = segment + "=" * (-len(segment) % 4)
        try:
            raw = base64.urlsafe_b64decode(padded)
            parsed = json.loads(raw)
            decoded_parts.append(f"[{label}]\n{json.dumps(parsed, indent=2)}")
        except (json.JSONDecodeError, binascii.Error):
            decoded_parts.append(f"[{label}]\n{raw.decode('utf-8', errors='replace')}")

    if len(parts) >= 3:
        decoded_parts.append(f"[Signature]\n{parts[2]}")

    return "\n\n".join(decoded_parts)
