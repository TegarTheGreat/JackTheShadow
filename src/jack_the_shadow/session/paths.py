"""
Jack The Shadow — Session Directory Paths

Manages the ~/.jshadow directory structure:
  ~/.jshadow/
  ├── credentials.json   # Cloudflare account_id + api_token
  ├── config.json        # User preferences (lang, default model, etc.)
  ├── sessions/          # Future: conversation history persistence
  └── logs/              # Future: centralized log storage
"""

from __future__ import annotations

from pathlib import Path

JSHADOW_DIR: Path = Path.home() / ".jshadow"
CREDENTIALS_FILE: str = "credentials.json"
CONFIG_FILE: str = "config.json"


def ensure_session_dir() -> Path:
    """Create ~/.jshadow and subdirectories if they don't exist."""
    JSHADOW_DIR.mkdir(parents=True, exist_ok=True)
    (JSHADOW_DIR / "sessions").mkdir(exist_ok=True)
    return JSHADOW_DIR


def get_session_dir() -> Path:
    return ensure_session_dir()


def get_credentials_path() -> Path:
    return JSHADOW_DIR / CREDENTIALS_FILE


def get_config_path() -> Path:
    return JSHADOW_DIR / CONFIG_FILE
