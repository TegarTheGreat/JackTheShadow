"""
Shared test fixtures for Jack The Shadow.
"""

import pytest

from jack_the_shadow.core.state import AppState


@pytest.fixture
def state() -> AppState:
    """Create a minimal AppState for testing."""
    return AppState(target="127.0.0.1", model="@cf/openai/gpt-oss-120b", language="en")
