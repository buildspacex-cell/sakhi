"""
Test helper functions for database operations and setup.

These helpers are used in integration tests to set up
and tear down test data in the database.
"""

import os
from typing import Optional
from datetime import datetime

from .constants import DEMO_USER_ID, DEMO_USER_NAME, DEMO_USER_EMAIL
from .factories import create_test_personal_model


# ─────────────────────────────────────────────────────────────────────────────
# Test User Helpers
# ─────────────────────────────────────────────────────────────────────────────

def get_test_person_id() -> str:
    """
    Get the test person ID to use.

    Returns DEMO_USER_ID if available, otherwise generates a test ID.
    This allows tests to run against seeded demo data or fresh test data.
    """
    # Check if we should use demo user
    use_demo = os.environ.get("SAKHI_TEST_USE_DEMO", "1") == "1"
    if use_demo:
        return DEMO_USER_ID
    return f"test-{datetime.now().strftime('%Y%m%d%H%M%S')}"


async def ensure_test_user(
    person_id: Optional[str] = None
) -> str:
    """
    Ensure a test user exists in the database.

    If person_id is DEMO_USER_ID and demo user exists, returns it.
    Otherwise creates a minimal test user.

    Args:
        person_id: Specific user ID to ensure (defaults to DEMO_USER_ID)

    Returns:
        The person_id that was ensured to exist
    """
    from sakhi.libs.db import get_db_pool

    pid = person_id or DEMO_USER_ID

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        # Check if user exists
        existing = await conn.fetchval(
            "SELECT person_id FROM personal_model WHERE person_id = $1",
            pid
        )

        if existing:
            return pid

        # Create minimal user for testing
        model = create_test_personal_model(person_id=pid)
        await conn.execute(
            """
            INSERT INTO personal_model (person_id, operating_system, life_context, updated_at)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (person_id) DO NOTHING
            """,
            pid,
            model["operating_system"],
            model["life_context"],
            datetime.now(),
        )

        return pid


async def cleanup_test_user(person_id: str) -> None:
    """
    Remove test user data from all tables.

    WARNING: This is destructive. Only use for test cleanup.
    Never call with DEMO_USER_ID unless you want to reset demo data.

    Args:
        person_id: User ID to clean up
    """
    from sakhi.libs.db import get_db_pool

    if person_id == DEMO_USER_ID:
        # Safety check - require explicit flag to delete demo user
        if os.environ.get("SAKHI_ALLOW_DEMO_DELETE") != "1":
            raise ValueError(
                "Cannot delete demo user without SAKHI_ALLOW_DEMO_DELETE=1"
            )

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        # Delete from tables with person_id
        tables_with_person_id = [
            "memory_short_term",
            "memory_episodic",
            "journal_entries",
            "intervention_plans",
            "intervention_checkins",
            "symptom_log",
            "behavior_log",
            "personal_patterns",
            "recommendation_feedback",
            "personal_model",
        ]

        for table in tables_with_person_id:
            try:
                await conn.execute(
                    f"DELETE FROM {table} WHERE person_id = $1",
                    person_id
                )
            except Exception:
                # Table might not exist or have different schema
                pass


# ─────────────────────────────────────────────────────────────────────────────
# Test Data Insertion Helpers
# ─────────────────────────────────────────────────────────────────────────────

async def insert_test_journal_entries(
    entries: list[dict],
) -> list[str]:
    """
    Insert test journal entries into database.

    Args:
        entries: List of journal entry dicts from factory

    Returns:
        List of inserted entry IDs
    """
    from sakhi.libs.db import get_db_pool

    pool = await get_db_pool()
    inserted_ids = []

    async with pool.acquire() as conn:
        for entry in entries:
            await conn.execute(
                """
                INSERT INTO journal_entries
                    (id, user_id, title, content, mood, facets, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (id) DO NOTHING
                """,
                entry["id"],
                entry["user_id"],
                entry["title"],
                entry["content"],
                entry["mood"],
                entry.get("facets", {}),
                entry["created_at"],
            )
            inserted_ids.append(entry["id"])

    return inserted_ids


async def insert_test_memories(
    memories: list[dict],
    table: str = "memory_short_term",
) -> list[str]:
    """
    Insert test memories into specified table.

    Args:
        memories: List of memory dicts from factory
        table: Table name (memory_short_term or memory_episodic)

    Returns:
        List of inserted memory IDs
    """
    from sakhi.libs.db import get_db_pool

    pool = await get_db_pool()
    inserted_ids = []

    async with pool.acquire() as conn:
        for mem in memories:
            if table == "memory_short_term":
                await conn.execute(
                    """
                    INSERT INTO memory_short_term
                        (id, person_id, content, source, created_at)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    mem["id"],
                    mem["person_id"],
                    mem["content"],
                    mem.get("source", "test"),
                    mem["created_at"],
                )
            elif table == "memory_episodic":
                await conn.execute(
                    """
                    INSERT INTO memory_episodic
                        (id, person_id, content, content_hash, created_at)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    mem["id"],
                    mem["person_id"],
                    mem["content"],
                    mem.get("content_hash", f"hash_{mem['id'][:8]}"),
                    mem["created_at"],
                )
            inserted_ids.append(mem["id"])

    return inserted_ids


# ─────────────────────────────────────────────────────────────────────────────
# Database State Helpers
# ─────────────────────────────────────────────────────────────────────────────

async def count_records(table: str, person_id: str) -> int:
    """
    Count records for a user in a table.

    Args:
        table: Table name
        person_id: User ID

    Returns:
        Number of records
    """
    from sakhi.libs.db import get_db_pool

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        count = await conn.fetchval(
            f"SELECT COUNT(*) FROM {table} WHERE person_id = $1",
            person_id
        )
        return count or 0


async def get_latest_record(table: str, person_id: str) -> Optional[dict]:
    """
    Get the most recent record for a user from a table.

    Args:
        table: Table name
        person_id: User ID

    Returns:
        Record as dict or None
    """
    from sakhi.libs.db import get_db_pool

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"""
            SELECT * FROM {table}
            WHERE person_id = $1
            ORDER BY created_at DESC
            LIMIT 1
            """,
            person_id
        )
        return dict(row) if row else None
