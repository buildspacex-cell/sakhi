"""Kala test configuration — no database fixtures needed for pure computation tests."""

import pytest


@pytest.fixture
def sample_baseline():
    """Sample baseline state for testing."""
    return {"energy": 0.7, "focus": 0.6, "stress": 0.3, "motivation": 0.8}
