"""
Pytest configuration and fixtures for Worker tests.

Provides shared fixtures for testing all workers including:
- Database connections
- Test user creation/cleanup
- Journal entry creation
- Personal model setup
- Memory graph nodes/edges
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

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
    db_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not db_url:
        pytest.skip("No DATABASE_URL configured for integration tests")
    yield


@pytest.fixture
async def db_query():
    """Provide async database query function."""
    from sakhi.apps.api.core.db import q
    return q


@pytest.fixture
async def db_exec():
    """Provide async database exec function."""
    from sakhi.apps.api.core.db import exec as db_exec_fn
    return db_exec_fn


@pytest.fixture
async def test_user_id(db_query, db_exec):
    """
    Get or create a test user for worker tests.

    Returns existing demo user if available, otherwise creates one.
    """
    # Try to find existing test user
    existing = await db_query(
        "SELECT id FROM persons WHERE id = $1",
        os.getenv("DEMO_USER_ID", "565bdb63-124b-4692-a039-846fddceff90"),
        one=True
    )

    if existing:
        return str(existing["id"])

    # Find any existing user
    any_user = await db_query(
        "SELECT id FROM persons LIMIT 1",
        one=True
    )

    if any_user:
        return str(any_user["id"])

    pytest.skip("No test user available in database")


@pytest.fixture
async def test_session_id():
    """Generate a unique test session ID."""
    return str(uuid.uuid4())


@pytest.fixture
async def create_journal_entry(db_exec, db_query):
    """
    Factory fixture to create test journal entries.

    Returns a function that creates entries and tracks them for cleanup.
    """
    created_entries = []

    async def _create_entry(
        user_id: str,
        content: str,
        layer: str = "reflection",
        mood: Optional[str] = None,
        tags: Optional[List[str]] = None,
        created_at: Optional[datetime] = None,
    ) -> str:
        entry_id = str(uuid.uuid4())
        ts = created_at or datetime.now(timezone.utc)

        await db_exec("""
            INSERT INTO journal_entries (id, user_id, content, layer, mood, tags, created_at, processing_state)
            VALUES ($1, $2, $3, $4, $5, $6, $7, 'pending')
        """, entry_id, user_id, content, layer, mood, tags or [], ts)

        created_entries.append(entry_id)
        return entry_id

    yield _create_entry

    # Cleanup
    for entry_id in created_entries:
        await db_exec("DELETE FROM journal_entries WHERE id = $1", entry_id)


@pytest.fixture
async def create_episodic_memory(db_exec, db_query):
    """
    Factory fixture to create test episodic memory entries.
    """
    created_episodes = []

    async def _create_episode(
        user_id: str,
        content: str,
        state_vector: Optional[Dict] = None,
        guna_vector: Optional[Dict] = None,
        created_at: Optional[datetime] = None,
    ) -> str:
        episode_id = str(uuid.uuid4())
        ts = created_at or datetime.now(timezone.utc)

        await db_exec("""
            INSERT INTO memory_episodic (id, user_id, content, state_vector, guna_vector, created_at)
            VALUES ($1, $2, $3, $4, $5, $6)
        """, episode_id, user_id, content,
            state_vector or {"dosha": {"vata": 0.33, "pitta": 0.33, "kapha": 0.34}},
            guna_vector or {"sattva": 0.5, "rajas": 0.3, "tamas": 0.2},
            ts)

        created_episodes.append(episode_id)
        return episode_id

    yield _create_episode

    # Cleanup
    for ep_id in created_episodes:
        await db_exec("DELETE FROM memory_episodic WHERE id = $1", ep_id)


@pytest.fixture
async def create_pattern_occurrence(db_exec):
    """
    Factory fixture to create test pattern occurrences.
    """
    created_occurrences = []

    async def _create_occurrence(
        user_id: str,
        pattern_type: str,
        pattern_value: str,
        source_entry_id: str,
        confidence: float = 0.8,
        evidence_snippet: str = "",
        created_at: Optional[datetime] = None,
    ) -> str:
        occ_id = str(uuid.uuid4())
        ts = created_at or datetime.now(timezone.utc)

        await db_exec("""
            INSERT INTO pattern_occurrences (id, person_id, pattern_type, pattern_value,
                source_entry_id, confidence, evidence_snippet, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """, occ_id, user_id, pattern_type, pattern_value,
            source_entry_id, confidence, evidence_snippet, ts)

        created_occurrences.append(occ_id)
        return occ_id

    yield _create_occurrence

    # Cleanup
    for occ_id in created_occurrences:
        await db_exec("DELETE FROM pattern_occurrences WHERE id = $1", occ_id)


@pytest.fixture
async def create_memory_node(db_exec):
    """
    Factory fixture to create test memory graph nodes.
    """
    created_nodes = []

    async def _create_node(
        user_id: str,
        node_kind: str,
        label: str,
        data: Optional[Dict] = None,
        weight: float = 0.5,
    ) -> str:
        node_id = str(uuid.uuid4())

        await db_exec("""
            INSERT INTO memory_nodes (id, person_id, node_kind, label, data, weight)
            VALUES ($1, $2, $3, $4, $5, $6)
        """, node_id, user_id, node_kind, label, data or {}, weight)

        created_nodes.append(node_id)
        return node_id

    yield _create_node

    # Cleanup
    for node_id in created_nodes:
        await db_exec("DELETE FROM memory_nodes WHERE id = $1", node_id)


@pytest.fixture
async def create_memory_edge(db_exec):
    """
    Factory fixture to create test memory graph edges.
    """
    created_edges = []

    async def _create_edge(
        user_id: str,
        from_node: str,
        to_node: str,
        relation: str,
        weight: float = 0.5,
        evidence: Optional[Dict] = None,
    ) -> str:
        edge_id = str(uuid.uuid4())

        await db_exec("""
            INSERT INTO memory_edges (id, person_id, from_node, to_node, relation, weight, evidence)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
        """, edge_id, user_id, from_node, to_node, relation, weight, evidence or {})

        created_edges.append(edge_id)
        return edge_id

    yield _create_edge

    # Cleanup
    for edge_id in created_edges:
        await db_exec("DELETE FROM memory_edges WHERE id = $1", edge_id)


@pytest.fixture
async def setup_personal_model(db_exec, db_query):
    """
    Ensure personal_model exists for test user with required fields.
    """
    async def _setup(user_id: str) -> bool:
        # Check if exists
        existing = await db_query(
            "SELECT person_id FROM personal_model WHERE person_id = $1",
            user_id, one=True
        )

        if not existing:
            # Create minimal personal_model
            await db_exec("""
                INSERT INTO personal_model (person_id, operating_system, soul_state, emotion_state, rhythm_state)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (person_id) DO NOTHING
            """, user_id,
                {"type": "Adaptive-Performance", "dosha_baseline": {"vata": 0.25, "pitta": 0.5, "kapha": 0.25}},
                {"values": ["growth", "balance"]},
                {"current": "stable"},
                {"slots": {"morning": "high", "afternoon": "medium", "evening": "low"}}
            )

        return True

    return _setup


@pytest.fixture
async def cleanup_test_data(db_exec):
    """
    Fixture that provides cleanup function for test data.
    """
    cleanup_queries = []

    def _add_cleanup(table: str, column: str, value: str):
        cleanup_queries.append((table, column, value))

    yield _add_cleanup

    # Execute cleanup
    for table, column, value in cleanup_queries:
        await db_exec(f"DELETE FROM {table} WHERE {column} = $1", value)


# Helper functions for tests
def days_ago(n: int) -> datetime:
    """Return datetime n days ago."""
    return datetime.now(timezone.utc) - timedelta(days=n)


def hours_ago(n: int) -> datetime:
    """Return datetime n hours ago."""
    return datetime.now(timezone.utc) - timedelta(hours=n)
