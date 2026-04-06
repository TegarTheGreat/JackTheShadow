"""
Jack The Shadow — User Config Persistence

Saves/loads user preferences to ~/.jshadow/config.json.
Persists: default model, language, yolo_mode.
"""

from __future__ import annotations

import json
from typing import Any, Optional

from jack_the_shadow.session.paths import get_config_path
from jack_the_shadow.utils.logger import get_logger

logger = get_logger("session.config")

_DEFAULTS: dict[str, Any] = {
    "model": "",
    "language": "",
    "yolo_mode": False,
}


def load_user_config() -> dict[str, Any]:
    """Load user config from ~/.jshadow/config.json. Returns defaults if missing."""
    path = get_config_path()
    if not path.exists():
        return dict(_DEFAULTS)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.debug("User config loaded from %s", path)
        merged = dict(_DEFAULTS)
        merged.update(data)
        return merged
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Failed to load config: %s", exc)
        return dict(_DEFAULTS)


def save_user_config(config: dict[str, Any]) -> bool:
    """Save user config to ~/.jshadow/config.json."""
    path = get_config_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        logger.info("User config saved to %s", path)
        return True
    except OSError as exc:
        logger.error("Failed to save config: %s", exc)
        return False


def update_user_config(**kwargs: Any) -> bool:
    """Update specific config values and save."""
    config = load_user_config()
    config.update(kwargs)
    return save_user_config(config)


def get_user_pref(key: str, default: Optional[Any] = None) -> Any:
    """Get a single preference value."""
    config = load_user_config()
    return config.get(key, default)
