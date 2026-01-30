"""
Pytest configuration for Friction Framework tests.
"""

from __future__ import annotations

import os
import pytest


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment variables."""
    os.environ.setdefault("SAKHI_ENVIRONMENT", "test")
    # Ensure we have a database URL
    db_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not db_url:
        pytest.skip("No DATABASE_URL configured for integration tests")
    yield


@pytest.fixture
def db_query():
    """Provide async database query function."""
    from sakhi.apps.api.core.db import q
    return q


@pytest.fixture
def db_exec():
    """Provide async database exec function."""
    from sakhi.apps.api.core.db import exec as db_exec_fn
    return db_exec_fn


@pytest.fixture
def demo_user_id():
    """Provide demo user ID."""
    return os.getenv("DEMO_USER_ID", "565bdb63-124b-4692-a039-846fddceff90")
