"""
Jack The Shadow — Logging Utility

Consistent logging setup — file handler to jack.log,
console handler CRITICAL-only to avoid clashing with rich UI.
"""

from __future__ import annotations

import logging
import sys
from typing import Optional

from jack_the_shadow.config import LOG_FILE, LOG_LEVEL

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_initialized: bool = False


def _init_root_logger() -> None:
    global _initialized
    if _initialized:
        return

    root = logging.getLogger("jack")
    root.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.DEBUG))

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    root.addHandler(fh)

    ch = logging.StreamHandler(sys.stderr)
    ch.setLevel(logging.CRITICAL)
    ch.setFormatter(formatter)
    root.addHandler(ch)

    _initialized = True


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Return a child logger under the ``jack`` namespace."""
    _init_root_logger()
    if name:
        return logging.getLogger(f"jack.{name}")
    return logging.getLogger("jack")
