"""
Jack The Shadow — Credential Management

Stores and retrieves Cloudflare Workers AI credentials from
~/.jshadow/credentials.json. Falls back to environment variables
for backward compatibility.
"""

from __future__ import annotations

import json
import os
from typing import Optional

from jack_the_shadow.session.paths import ensure_session_dir, get_credentials_path


def save_credentials(account_id: str, api_token: str) -> None:
    """Persist Cloudflare credentials to ~/.jshadow/credentials.json."""
    ensure_session_dir()
    path = get_credentials_path()
    data = {
        "cloudflare_account_id": account_id,
        "cloudflare_api_token": api_token,
    }
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    path.chmod(0o600)  # owner-only read/write


def load_credentials() -> tuple[str, str]:
    """Load credentials from file, fallback to env vars.

    Returns:
        (account_id, api_token) — empty strings if not found.
    """
    path = get_credentials_path()
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            account_id = data.get("cloudflare_account_id", "")
            api_token = data.get("cloudflare_api_token", "")
            if account_id and api_token:
                return account_id, api_token
        except (json.JSONDecodeError, OSError):
            pass

    account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
    api_token = os.getenv("CLOUDFLARE_API_TOKEN", "")
    return account_id, api_token


def clear_credentials() -> bool:
    """Remove stored credentials. Returns True if file existed."""
    path = get_credentials_path()
    if path.is_file():
        path.unlink()
        return True
    return False


def is_logged_in() -> bool:
    """Check if valid credentials exist."""
    account_id, api_token = load_credentials()
    return bool(account_id and api_token)


def get_credential_source() -> Optional[str]:
    """Return where credentials were loaded from, or None."""
    path = get_credentials_path()
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("cloudflare_account_id") and data.get("cloudflare_api_token"):
                return str(path)
        except (json.JSONDecodeError, OSError):
            pass
    if os.getenv("CLOUDFLARE_ACCOUNT_ID") and os.getenv("CLOUDFLARE_API_TOKEN"):
        return "environment variables"
    return None
