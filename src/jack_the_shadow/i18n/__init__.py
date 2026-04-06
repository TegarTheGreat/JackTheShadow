"""
Jack The Shadow — Internationalisation Package

Re-exports the public API: ``t()``, ``set_language()``, ``get_language()``.
"""

from jack_the_shadow.i18n.engine import get_language, set_language, t  # noqa: F401

__all__ = ["t", "set_language", "get_language"]
