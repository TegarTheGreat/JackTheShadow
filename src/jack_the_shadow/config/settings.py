"""
Jack The Shadow — Environment Variables & Constants

Loads .env and exposes all runtime configuration values.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

# ── Cloudflare Workers AI ────────────────────────────────────────────
CLOUDFLARE_ACCOUNT_ID: str = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
CLOUDFLARE_API_TOKEN: str = os.getenv("CLOUDFLARE_API_TOKEN", "")
DEFAULT_MODEL: str = os.getenv("JACK_DEFAULT_MODEL", "@cf/openai/gpt-oss-120b")
DEFAULT_LANGUAGE: str = os.getenv("JACK_LANG", "en")

# ── Runtime Limits ───────────────────────────────────────────────────
MAX_CONTEXT_MESSAGES: int = 50
MAX_OUTPUT_CHARS: int = 10_000
MAX_RETRIES: int = 3
COMMAND_TIMEOUT: int = 120
RETRY_BACKOFF_BASE: float = 2.0
GREP_MAX_RESULTS: int = 250
GLOB_MAX_RESULTS: int = 100
LIST_DIR_MAX_DEPTH: int = 3
WEB_FETCH_MAX_LENGTH: int = 50_000
WEB_FETCH_TIMEOUT: int = 30
WEB_SEARCH_MAX_RESULTS: int = 8

# ── Logging ──────────────────────────────────────────────────────────
LOG_FILE: str = "jack.log"
LOG_LEVEL: str = os.getenv("JACK_LOG_LEVEL", "DEBUG")

# ── API Endpoint Template ────────────────────────────────────────────
API_ENDPOINT: str = (
    "https://api.cloudflare.com/client/v4/accounts"
    "/{account_id}/ai/run/{model}"
)
