"""
Pytest fixtures for longitudinal tests.

Provides:
- Database connection fixtures
- Persona loading fixtures
- Simulation harness setup/teardown
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest
import pytest_asyncio

# Load environment
from dotenv import load_dotenv
env_path = Path(__file__).parents[3] / ".env"
load_dotenv(env_path)


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
    db_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not db_url:
        pytest.skip("No DATABASE_URL configured for longitudinal tests")
    yield


@pytest_asyncio.fixture
async def db_query():
    """Provide async database query function."""
    from sakhi.apps.api.core.db import q
    return q


@pytest_asyncio.fixture
async def db_exec():
    """Provide async database exec function."""
    from sakhi.apps.api.core.db import exec as db_exec_fn
    return db_exec_fn


@pytest.fixture
def persona_anxious_achiever():
    """Load the anxious_achiever test persona."""
    from sakhi.tests.longitudinal.persona_spec import load_persona
    return load_persona("anxious_achiever")


@pytest.fixture
def persona_stuck_creative():
    """Load the stuck_creative test persona."""
    from sakhi.tests.longitudinal.persona_spec import load_persona
    return load_persona("stuck_creative")


@pytest_asyncio.fixture
async def simulation_harness(db_query, db_exec, persona_anxious_achiever):
    """
    Provide a configured simulation harness with cleanup.

    Uses the anxious_achiever persona by default.
    """
    from sakhi.tests.longitudinal.simulation_harness import SimulationHarness

    harness = SimulationHarness(
        persona=persona_anxious_achiever,
        db_query=db_query,
        db_exec=db_exec,
        run_workers=False,  # Disable workers by default in tests
    )

    await harness.setup()

    yield harness

    # Cleanup
    await harness.cleanup()


@pytest_asyncio.fixture
async def test_user_for_simulation(db_exec):
    """
    Create a test user specifically for simulation tests.

    Returns user_id and cleans up after test.
    """
    user_id = str(uuid.uuid4())

    await db_exec(
        """
        INSERT INTO profiles (user_id, email, created_at, updated_at)
        VALUES ($1, $2, NOW(), NOW())
        ON CONFLICT (user_id) DO NOTHING
        """,
        user_id,
        f"sim_test_{user_id[:8]}@test.sakhi.dev",
    )

    await db_exec(
        """
        INSERT INTO personal_model (person_id, updated_at)
        VALUES ($1, NOW())
        ON CONFLICT (person_id) DO NOTHING
        """,
        user_id,
    )

    yield user_id

    # Cleanup
    tables = [
        "pattern_occurrences",
        "crystallized_patterns",
        "memory_edges",
        "memory_nodes",
        "memory_episodic",
        "journal_entries",
        "personal_model",
        "profiles",
    ]
    for table in tables:
        try:
            col = "user_id" if table in ["memory_episodic", "journal_entries"] else "person_id"
            if table == "profiles":
                col = "user_id"
            await db_exec(f"DELETE FROM {table} WHERE {col} = $1", user_id)
        except Exception:
            pass


@pytest.fixture
def sample_entry_content():
    """Provide sample journal entry content for testing."""
    return {
        "anxious": "Can't stop thinking about the presentation tomorrow. What if I mess up? "
                   "Haven't slept well in days. Took on another project even though I know I shouldn't have.",
        "burnout": "I'm exhausted. Snapped at my partner again this morning. "
                   "Had a headache all day. Maybe I need to slow down but there's just too much to do.",
        "recovery": "Actually said no to an extra meeting today. It was hard but I did it. "
                    "Went for a short walk at lunch. Baby steps.",
        "stagnant": "Same as yesterday. Stayed in, watched TV, ordered food. "
                    "Don't have energy for anything else. Know I should but can't.",
    }
