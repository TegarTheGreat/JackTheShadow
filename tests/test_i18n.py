"""
Tests for i18n engine.
"""

from jack_the_shadow.i18n import get_language, set_language, t


def test_default_language_is_english():
    set_language("en")
    assert get_language() == "en"


def test_switch_to_indonesian():
    set_language("id")
    assert get_language() == "id"
    assert t("goodbye") == "👋 Jack menghilang ke dalam bayangan..."
    set_language("en")


def test_english_strings():
    set_language("en")
    assert t("goodbye") == "👋 Jack fades into the shadows..."


def test_fallback_to_key():
    set_language("en")
    assert t("nonexistent.key") == "nonexistent.key"


def test_format_kwargs():
    set_language("en")
    assert "192.168.1.1" in t("target.switched", target="192.168.1.1")
