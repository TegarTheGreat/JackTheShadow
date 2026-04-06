"""
Jack The Shadow — Configuration Package

Splits settings, model catalog, and system prompts into
separate, focused modules.
"""

from jack_the_shadow.config.settings import *  # noqa: F401,F403
from jack_the_shadow.config.models import MODEL_CATALOG  # noqa: F401
from jack_the_shadow.config.prompts import get_system_prompt  # noqa: F401
