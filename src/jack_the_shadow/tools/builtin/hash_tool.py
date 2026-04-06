"""
Jack The Shadow — Hash Analysis Tool

Analyse, identify, and generate cryptographic hashes.
"""

from __future__ import annotations

import hashlib
import re
from typing import TYPE_CHECKING, Any, ClassVar, Optional

from jack_the_shadow.tools.base import BaseTool
from jack_the_shadow.tools.helpers import result, truncate
from jack_the_shadow.utils.logger import get_logger

if TYPE_CHECKING:
    from jack_the_shadow.tools.executor import ToolExecutor

logger = get_logger("tools.hash")

# ── hash‑identification patterns ──────────────────────────────────────
HASH_PATTERNS: list[tuple[str, list[str]]] = [
    (r"^[a-f0-9]{32}$", ["MD5", "NTLM"]),
    (r"^[a-f0-9]{40}$", ["SHA-1"]),
    (r"^[a-f0-9]{64}$", ["SHA-256"]),
    (r"^[a-f0-9]{128}$", ["SHA-512"]),
    (r"^\$2[aby]?\$\d+\$.{53}$", ["bcrypt"]),
    (r"^\$1\$[./A-Za-z0-9]{8}\$[./A-Za-z0-9]{22}$", ["MD5crypt (Unix)"]),
    (r"^\$5\$[./A-Za-z0-9]{16}\$[./A-Za-z0-9]{43}$", ["SHA-256crypt (Unix)"]),
    (r"^\$6\$[./A-Za-z0-9]{16}\$[./A-Za-z0-9]{86}$", ["SHA-512crypt (Unix)"]),
    (r"^[a-f0-9]{16}$", ["MySQL (old)", "Half MD5"]),
    (r"^[a-f0-9]{56}$", ["SHA-224"]),
    (r"^[a-f0-9]{96}$", ["SHA-384"]),
    (r"^\$apr1\$", ["Apache MD5"]),
    (r"^\{SHA\}", ["LDAP SHA"]),
    (r"^\{SSHA\}", ["LDAP SSHA"]),
    (r"^[A-Fa-f0-9]{32}:[A-Fa-f0-9]+$", ["MD5 (salted)"]),
    (r"^[a-f0-9]{40}:[a-f0-9]+$", ["SHA-1 (salted)"]),
    (r"^pbkdf2", ["PBKDF2"]),
    (r"^scrypt:", ["scrypt"]),
    (r"^\$argon2", ["Argon2"]),
]

HASHCAT_MODES: dict[str, str] = {
    "MD5": "0",
    "SHA-1": "100",
    "SHA-256": "1400",
    "SHA-512": "1700",
    "NTLM": "1000",
    "bcrypt": "3200",
    "MD5crypt (Unix)": "500",
    "SHA-256crypt (Unix)": "7400",
    "SHA-512crypt (Unix)": "1800",
    "MySQL (old)": "200",
    "WPA/WPA2": "22000",
}

JOHN_FORMATS: dict[str, str] = {
    "MD5": "raw-md5",
    "SHA-1": "raw-sha1",
    "SHA-256": "raw-sha256",
    "SHA-512": "raw-sha512",
    "NTLM": "nt",
    "bcrypt": "bcrypt",
    "MD5crypt (Unix)": "md5crypt",
    "SHA-256crypt (Unix)": "sha256crypt",
    "SHA-512crypt (Unix)": "sha512crypt",
}


# ── tool class ────────────────────────────────────────────────────────
class HashAnalyzeTool(BaseTool):
    name: ClassVar[str] = "hash_analyze"
    description: ClassVar[str] = (
        "Analyze, identify, and generate hashes. Supports hash type "
        "identification, hash generation (MD5, SHA1, SHA256, SHA512, NTLM, "
        "bcrypt), and known-hash lookup."
    )
    risk_aware: ClassVar[bool] = False

    @classmethod
    def parameters_schema(cls) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["identify", "generate", "crack_lookup"],
                    "description": (
                        "identify: detect hash type from a hash string. "
                        "generate: create hash(es) from plaintext. "
                        "crack_lookup: look up a hash in online databases."
                    ),
                },
                "input_data": {
                    "type": "string",
                    "description": (
                        "Hash string to identify/lookup, or plaintext to hash."
                    ),
                },
                "algorithm": {
                    "type": "string",
                    "enum": [
                        "md5", "sha1", "sha256", "sha512",
                        "ntlm", "bcrypt", "all",
                    ],
                    "description": (
                        "Hash algorithm for 'generate' action (default: all)."
                    ),
                },
            },
            "required": ["action", "input_data"],
        }


# ── internal helpers ──────────────────────────────────────────────────

def _classify_charset(text: str) -> str:
    if re.fullmatch(r"[a-f0-9]+", text):
        return "hex (lowercase)"
    if re.fullmatch(r"[A-Fa-f0-9]+", text):
        return "hex (mixed case)"
    if re.fullmatch(r"[A-Za-z0-9]+", text):
        return "alphanumeric"
    if re.fullmatch(r"[A-Za-z0-9+/=]+", text):
        return "base64-like"
    return "mixed / special characters"


def _identify(hash_str: str) -> str:
    hash_str = hash_str.strip()
    matches: list[str] = []
    for pattern, types in HASH_PATTERNS:
        if re.match(pattern, hash_str, re.IGNORECASE):
            matches.extend(types)

    lines: list[str] = [
        f"Hash:      {hash_str}",
        f"Length:    {len(hash_str)} characters",
        f"Charset:  {_classify_charset(hash_str)}",
        "",
    ]

    if matches:
        lines.append("Possible hash types:")
        for i, m in enumerate(matches, 1):
            confidence = "High" if i == 1 else "Medium" if i <= 3 else "Low"
            lines.append(f"  {i}. {m:<25s} (confidence: {confidence})")
    else:
        lines.append("No known hash type matched this pattern.")

    return "\n".join(lines)


def _generate(plaintext: str, algorithm: str) -> str:
    algo = algorithm or "all"
    hashes: dict[str, str] = {}

    if algo in ("md5", "all"):
        hashes["MD5"] = hashlib.md5(plaintext.encode()).hexdigest()
    if algo in ("sha1", "all"):
        hashes["SHA-1"] = hashlib.sha1(plaintext.encode()).hexdigest()
    if algo in ("sha256", "all"):
        hashes["SHA-256"] = hashlib.sha256(plaintext.encode()).hexdigest()
    if algo in ("sha512", "all"):
        hashes["SHA-512"] = hashlib.sha512(plaintext.encode()).hexdigest()
    if algo in ("ntlm", "all"):
        hashes["NTLM"] = hashlib.new(
            "md4", plaintext.encode("utf-16le"),
        ).hexdigest()
    if algo in ("bcrypt", "all"):
        try:
            import bcrypt as bcrypt_lib

            hashes["bcrypt"] = bcrypt_lib.hashpw(
                plaintext.encode(), bcrypt_lib.gensalt(),
            ).decode()
        except ImportError:
            hashes["bcrypt"] = "(bcrypt library not installed — pip install bcrypt)"

    if not hashes:
        return f"Unknown algorithm: {algo}"

    label_width = max(len(k) for k in hashes) + 2
    lines = [f"Hashes for: {plaintext!r}", ""]
    for label, digest in hashes.items():
        lines.append(f"  {label + ':':<{label_width}s} {digest}")
    return "\n".join(lines)


def _crack_lookup(hash_str: str) -> str:
    import requests as _requests

    hash_str = hash_str.strip()

    # First, identify the hash type
    identified: list[str] = []
    for pattern, types in HASH_PATTERNS:
        if re.match(pattern, hash_str, re.IGNORECASE):
            identified.extend(types)

    primary_type = identified[0] if identified else "Unknown"

    # Try free online lookup via hashify.net
    lookup_result: Optional[str] = None
    hash_type_param = "md5" if primary_type == "MD5" else "sha1" if primary_type == "SHA-1" else None
    if hash_type_param:
        try:
            resp = _requests.get(
                f"https://api.hashify.net/hash/{hash_type_param}/hex",
                params={"value": hash_str},
                timeout=10,
            )
            if resp.ok:
                data = resp.json()
                if data.get("Ede"):
                    lookup_result = data["Ede"]
        except Exception:  # noqa: BLE001
            pass

    lines: list[str] = [
        f"Hash:            {hash_str}",
        f"Identified as:   {', '.join(identified) if identified else 'Unknown'}",
        "",
    ]

    if lookup_result:
        lines.append(f"Online lookup:   FOUND — plaintext: {lookup_result}")
    else:
        lines.append("Online lookup:   Not found in free databases.")

    lines.append("")
    lines.append("Offline cracking suggestions:")

    # Hashcat
    if primary_type in HASHCAT_MODES:
        mode = HASHCAT_MODES[primary_type]
        lines.append(f"  hashcat -m {mode} {hash_str} wordlist.txt")
    else:
        lines.append(f"  hashcat -m <mode> {hash_str} wordlist.txt")

    # John the Ripper
    fmt = JOHN_FORMATS.get(primary_type)
    if fmt:
        lines.append(f"  john --format={fmt} hash.txt")
    else:
        lines.append("  john hash.txt")

    lines.append("")
    lines.append("Recommended wordlists: rockyou.txt, SecLists/Passwords/")
    return "\n".join(lines)


# ── handler ───────────────────────────────────────────────────────────

def handle_hash_analyze(
    executor: "ToolExecutor",
    action: str,
    input_data: str,
    algorithm: Optional[str] = None,
) -> dict[str, str]:
    """Execute hash analysis."""
    logger.info("hash_analyze action=%s", action)

    if action == "identify":
        output = _identify(input_data)
        return result("success", output=truncate(output))

    if action == "generate":
        output = _generate(input_data, algorithm or "all")
        return result("success", output=truncate(output))

    if action == "crack_lookup":
        try:
            output = _crack_lookup(input_data)
            return result("success", output=truncate(output))
        except Exception as exc:  # noqa: BLE001
            logger.error("crack_lookup failed: %s", exc)
            return result("error", message=f"Lookup failed: {exc}")

    return result("error", message=f"Unknown action: {action}")
