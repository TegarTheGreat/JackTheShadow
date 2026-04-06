"""
Jack The Shadow — i18n Engine

Global language state and the ``t()`` string accessor.
Loads string tables from per-language modules.
"""

from __future__ import annotations

from typing import Any

from jack_the_shadow.i18n import en as _en_mod
from jack_the_shadow.i18n import id as _id_mod

_TABLES: dict[str, dict[str, str]] = {
    "en": _en_mod.STRINGS,
    "id": _id_mod.STRINGS,
}

_current_lang: str = "en"


def set_language(lang: str) -> None:
    """Set the active language globally."""
    global _current_lang
    _current_lang = lang if lang in _TABLES else "en"


def get_language() -> str:
    return _current_lang


def t(key: str, **kwargs: Any) -> str:
    """Get a translated string.  Falls back to English, then the key itself."""
    table = _TABLES.get(_current_lang, _TABLES["en"])
    text = table.get(key)
    if text is None:
        text = _TABLES["en"].get(key, key)
    if kwargs:
        text = text.format(**kwargs)
    return text
