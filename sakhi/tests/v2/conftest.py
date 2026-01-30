"""
Sakhi v2 Test Fixtures

Shared fixtures for all v2 tests. Requires:
- DATABASE_URL environment variable
- DEMO_USER_ID environment variable (or uses default)

Server Setup (for integration tests):
- Simple mode: ./scripts/dev-simple.sh (no Redis, inline workers)
- Full mode:   ./scripts/dev-full.sh (Redis + async workers)

Run tests with: pytest sakhi/tests/v2/ -v
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional
import uuid

# Load .env file before any other imports
from dotenv import load_dotenv
env_path = Path(__file__).parents[3] / ".env"
load_dotenv(env_path)

import pytest
import pytest_asyncio
import asyncpg

# Test user - use DEMO_USER_ID or fallback
TEST_USER_ID = os.getenv("DEMO_USER_ID", "565bdb63-124b-4692-a039-846fddceff90")
DATABASE_URL = os.getenv("DATABASE_URL")


@pytest_asyncio.fixture(scope="function")
async def db():
    """Create database connection for test."""
    if not DATABASE_URL:
        pytest.skip("DATABASE_URL not set")
    # statement_cache_size=0 for pgbouncer compatibility
    conn = await asyncpg.connect(DATABASE_URL, statement_cache_size=0)
    try:
        yield conn
    finally:
        await conn.close()


@pytest.fixture
def test_user_id():
    """Return test user ID."""
    return TEST_USER_ID


@pytest_asyncio.fixture
async def ensure_test_user(db, test_user_id):
    """Ensure test user exists in profiles table."""
    existing = await db.fetchrow(
        "SELECT user_id FROM profiles WHERE user_id = $1", test_user_id
    )
    if not existing:
        await db.execute("""
            INSERT INTO profiles (user_id, email, created_at, updated_at)
            VALUES ($1, 'test@sakhi.dev', NOW(), NOW())
            ON CONFLICT (user_id) DO NOTHING
        """, test_user_id)
    return test_user_id


@pytest_asyncio.fixture
async def ensure_personal_model(db, test_user_id):
    """Ensure personal_model row exists for test user."""
    existing = await db.fetchrow(
        "SELECT person_id FROM personal_model WHERE person_id = $1",
        test_user_id
    )
    if not existing:
        await db.execute("""
            INSERT INTO personal_model (person_id, data, updated_at)
            VALUES ($1, '{}', NOW())
            ON CONFLICT (person_id) DO NOTHING
        """, test_user_id)
    return test_user_id


@pytest_asyncio.fixture
async def create_test_entry(db, test_user_id):
    """Factory to create test journal entries."""
    created_ids = []

    async def _create(text: str, layer: str = "conversation") -> str:
        entry_id = str(uuid.uuid4())
        await db.execute("""
            INSERT INTO journal_entries (id, person_id, content, layer, created_at)
            VALUES ($1, $2, $3, $4, NOW())
        """, entry_id, test_user_id, text, layer)
        created_ids.append(entry_id)
        return entry_id

    yield _create

    # Cleanup
    for entry_id in created_ids:
        await db.execute("DELETE FROM journal_entries WHERE id = $1", entry_id)


# Helper functions for assertions
async def get_personal_model_facet(db, person_id: str, facet: str) -> Optional[Dict]:
    """Get a specific facet from personal_model."""
    row = await db.fetchrow("""
        SELECT data, updated_at FROM personal_model
        WHERE person_id = $1 AND facet = $2
    """, person_id, facet)
    return dict(row) if row else None


async def get_memory_count(db, person_id: str, table: str = "memory_episodic") -> int:
    """Get count of memories for a user."""
    return await db.fetchval(
        f"SELECT COUNT(*) FROM {table} WHERE user_id = $1", person_id
    )


async def get_recent_memories(db, person_id: str, limit: int = 5) -> list:
    """Get recent memories for a user."""
    rows = await db.fetch("""
        SELECT id, content, created_at FROM memory_episodic
        WHERE user_id = $1
        ORDER BY created_at DESC
        LIMIT $2
    """, person_id, limit)
    return [dict(r) for r in rows]
