"""
Sakhi Test Configuration

Root conftest.py with shared fixtures for all tests.
Provides database connections, test user setup, and common utilities.

Test Categories:
- Unit tests: No real DB, use mocked fixtures
- Integration tests: Real DB, marked with @pytest.mark.integration
- E2E tests: Full system, marked with @pytest.mark.e2e

Usage:
    pytest                           # Run all tests
    pytest -m integration            # Run integration tests only
    pytest -m "not integration"      # Run unit tests only
    pytest --tb=short -q             # Quick mode
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock
import uuid

import pytest
import pytest_asyncio

# Load environment
from dotenv import load_dotenv
env_path = Path(__file__).parents[2] / ".env"
load_dotenv(env_path)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parents[2]))

# Import test fixtures
from sakhi.tests.fixtures.constants import DEMO_USER_ID, TEST_USER_ID


# ─────────────────────────────────────────────────────────────────────────────
# Pytest Configuration
# ─────────────────────────────────────────────────────────────────────────────

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (require DB)"
    )
    config.addinivalue_line(
        "markers", "e2e: marks tests as end-to-end tests (require full system)"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow"
    )


def pytest_collection_modifyitems(config, items):
    """Skip integration tests if no DB available."""
    db_url = os.getenv("DATABASE_URL")

    if not db_url:
        skip_integration = pytest.mark.skip(reason="DATABASE_URL not set")
        for item in items:
            if "integration" in item.keywords or "e2e" in item.keywords:
                item.add_marker(skip_integration)


# ─────────────────────────────────────────────────────────────────────────────
# Event Loop
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ─────────────────────────────────────────────────────────────────────────────
# Database Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="function")
async def db():
    """
    Create database connection for integration tests.

    Usage:
        @pytest.mark.integration
        async def test_something(db):
            result = await db.fetch("SELECT 1")
    """
    import asyncpg

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        pytest.skip("DATABASE_URL not set")

    conn = await asyncpg.connect(db_url, statement_cache_size=0)
    try:
        yield conn
    finally:
        await conn.close()


@pytest_asyncio.fixture(scope="function")
async def db_pool():
    """
    Get the shared database pool.

    Usage:
        @pytest.mark.integration
        async def test_something(db_pool):
            async with db_pool.acquire() as conn:
                result = await conn.fetch("SELECT 1")
    """
    from sakhi.libs.db import get_db_pool

    pool = await get_db_pool()
    yield pool


# ─────────────────────────────────────────────────────────────────────────────
# Mock Database Fixtures (for unit tests)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_db():
    """
    Mock database connection for unit tests.

    Usage:
        async def test_something(mock_db):
            mock_db.fetch.return_value = [{"id": "123"}]
            # Test your function that uses DB
    """
    mock = AsyncMock()
    mock.fetch = AsyncMock(return_value=[])
    mock.fetchrow = AsyncMock(return_value=None)
    mock.fetchval = AsyncMock(return_value=None)
    mock.execute = AsyncMock(return_value="")
    return mock


@pytest.fixture
def mock_db_pool(mock_db):
    """
    Mock database pool for unit tests.

    Usage:
        async def test_something(mock_db_pool):
            with patch("sakhi.libs.db.get_db_pool", return_value=mock_db_pool):
                # Test your function
    """
    pool = AsyncMock()
    pool.acquire = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_db)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
    return pool


# ─────────────────────────────────────────────────────────────────────────────
# Test User Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def test_person_id() -> str:
    """Return the demo user ID for tests."""
    return DEMO_USER_ID


@pytest.fixture
def test_user_id_fresh() -> str:
    """Return a fresh test user ID (not demo user)."""
    return str(uuid.uuid4())


@pytest_asyncio.fixture
async def ensure_test_user(db):
    """
    Ensure test user exists in database.

    Usage:
        @pytest.mark.integration
        async def test_something(ensure_test_user):
            user_id = await ensure_test_user(DEMO_USER_ID)
    """
    async def _ensure(person_id: str = DEMO_USER_ID) -> str:
        # Check if user exists in personal_model
        existing = await db.fetchval(
            "SELECT person_id FROM personal_model WHERE person_id = $1",
            person_id
        )

        if not existing:
            # Create minimal personal_model
            await db.execute("""
                INSERT INTO personal_model (person_id, operating_system, updated_at)
                VALUES ($1, $2, NOW())
                ON CONFLICT (person_id) DO NOTHING
            """, person_id, {"type": "adaptive", "primary_dosha": "vata"})

        return person_id

    return _ensure


# ─────────────────────────────────────────────────────────────────────────────
# Data Factory Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def create_journal_entry(db):
    """
    Factory to create test journal entries with automatic cleanup.

    Usage:
        @pytest.mark.integration
        async def test_something(create_journal_entry):
            entry_id = await create_journal_entry(
                person_id=DEMO_USER_ID,
                content="Test entry"
            )
    """
    created_ids = []

    async def _create(
        person_id: str,
        content: str,
        title: str = "Test Entry",
        mood: str = "neutral",
        created_at: Optional[datetime] = None,
    ) -> str:
        entry_id = str(uuid.uuid4())
        ts = created_at or datetime.now(timezone.utc)

        await db.execute("""
            INSERT INTO journal_entries (id, user_id, title, content, mood, created_at)
            VALUES ($1, $2, $3, $4, $5, $6)
        """, entry_id, person_id, title, content, mood, ts)

        created_ids.append(entry_id)
        return entry_id

    yield _create

    # Cleanup
    for entry_id in created_ids:
        await db.execute("DELETE FROM journal_entries WHERE id = $1", entry_id)


@pytest_asyncio.fixture
async def create_memory(db):
    """
    Factory to create test memory records with automatic cleanup.

    Usage:
        @pytest.mark.integration
        async def test_something(create_memory):
            mem_id = await create_memory(
                person_id=DEMO_USER_ID,
                content="Test memory"
            )
    """
    created_ids = []

    async def _create(
        person_id: str,
        content: str,
        table: str = "memory_short_term",
        created_at: Optional[datetime] = None,
    ) -> str:
        mem_id = str(uuid.uuid4())
        ts = created_at or datetime.now(timezone.utc)

        if table == "memory_short_term":
            await db.execute("""
                INSERT INTO memory_short_term (id, person_id, content, created_at)
                VALUES ($1, $2, $3, $4)
            """, mem_id, person_id, content, ts)
        elif table == "memory_episodic":
            await db.execute("""
                INSERT INTO memory_episodic (id, person_id, content, content_hash, created_at)
                VALUES ($1, $2, $3, $4, $5)
            """, mem_id, person_id, content, f"hash_{mem_id[:8]}", ts)

        created_ids.append((table, mem_id))
        return mem_id

    yield _create

    # Cleanup
    for table, mem_id in created_ids:
        await db.execute(f"DELETE FROM {table} WHERE id = $1", mem_id)


# ─────────────────────────────────────────────────────────────────────────────
# HTTP Client Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def api_client():
    """
    HTTP client for testing API endpoints.

    Usage:
        @pytest.mark.integration
        async def test_endpoint(api_client):
            response = await api_client.get("/health")
            assert response.status_code == 200
    """
    from httpx import AsyncClient, ASGITransport
    from sakhi.apps.api.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


# ─────────────────────────────────────────────────────────────────────────────
# Utility Functions
# ─────────────────────────────────────────────────────────────────────────────

def days_ago(n: int) -> datetime:
    """Return datetime n days ago."""
    return datetime.now(timezone.utc) - timedelta(days=n)


def hours_ago(n: int) -> datetime:
    """Return datetime n hours ago."""
    return datetime.now(timezone.utc) - timedelta(hours=n)


def generate_uuid() -> str:
    """Generate a new UUID string."""
    return str(uuid.uuid4())


# ─────────────────────────────────────────────────────────────────────────────
# Assertion Helpers
# ─────────────────────────────────────────────────────────────────────────────

async def assert_record_exists(db, table: str, column: str, value: str) -> bool:
    """Assert a record exists in a table."""
    result = await db.fetchval(
        f"SELECT 1 FROM {table} WHERE {column} = $1", value
    )
    assert result is not None, f"Expected record in {table} where {column}={value}"
    return True


async def assert_record_count(db, table: str, person_id: str, expected: int) -> bool:
    """Assert expected number of records for a user."""
    count = await db.fetchval(
        f"SELECT COUNT(*) FROM {table} WHERE person_id = $1", person_id
    )
    assert count == expected, f"Expected {expected} records in {table}, got {count}"
    return True


async def get_latest_record(db, table: str, person_id: str) -> Optional[Dict]:
    """Get the most recent record for a user."""
    row = await db.fetchrow(
        f"SELECT * FROM {table} WHERE person_id = $1 ORDER BY created_at DESC LIMIT 1",
        person_id
    )
    return dict(row) if row else None
