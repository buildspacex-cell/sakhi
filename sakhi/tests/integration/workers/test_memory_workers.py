"""
Integration tests for memory processing workers.

These workers handle memory fanout, synthesis, and consolidation.
Tests verify that memories are correctly processed and stored.

Workers tested:
- memory_fanout
- memory_synthesis
"""

import pytest
from datetime import datetime, timezone

from sakhi.tests.fixtures import DEMO_USER_ID


# ─────────────────────────────────────────────────────────────────────────────
# Test: memory_fanout
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestMemoryFanout:
    """Tests for memory_fanout worker."""

    @pytest_asyncio.fixture(autouse=True)
    async def setup(self, ensure_test_user, db):
        self.person_id = await ensure_test_user(DEMO_USER_ID)
        self.db = db

    @pytest.mark.asyncio
    async def test_fans_out_to_multiple_memory_stores(self, create_journal_entry):
        """
        Test that memory fanout distributes content to appropriate stores.

        Given: A rich journal entry
        When: memory_fanout worker runs
        Then: Content is stored in STM, facts are extracted, graph nodes created
        """
        entry_id = await create_journal_entry(
            person_id=self.person_id,
            content="I love hiking in the mountains. Did a 5-mile trail today with Sarah."
        )

        # TODO: Import and call worker
        # from sakhi.apps.worker.tasks.memory_fanout import run
        # await run(self.person_id, entry_id)

        # Assert memories were created in multiple stores
        # stm_count = await self.db.fetchval(
        #     "SELECT COUNT(*) FROM memory_short_term WHERE person_id = $1",
        #     self.person_id
        # )
        # assert stm_count > 0
        pytest.skip("Worker import pending")

    @pytest.mark.asyncio
    async def test_extracts_facts_from_content(self, create_journal_entry):
        """Test that facts are extracted from content."""
        entry_id = await create_journal_entry(
            person_id=self.person_id,
            content="My favorite coffee is Ethiopian Yirgacheffe from Blue Bottle."
        )

        # TODO: Verify fact was extracted to facts table
        pytest.skip("Worker import pending")


# ─────────────────────────────────────────────────────────────────────────────
# Test: memory_synthesis
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestMemorySynthesis:
    """Tests for memory_synthesis worker."""

    @pytest_asyncio.fixture(autouse=True)
    async def setup(self, ensure_test_user, db):
        self.person_id = await ensure_test_user(DEMO_USER_ID)
        self.db = db

    @pytest.mark.asyncio
    async def test_synthesizes_related_memories(self, create_memory):
        """
        Test that synthesis worker combines related memories.

        Given: Multiple related memories
        When: memory_synthesis worker runs
        Then: A synthesized summary is created
        """
        # Create related memories
        await create_memory(
            person_id=self.person_id,
            content="Had trouble sleeping last night."
        )
        await create_memory(
            person_id=self.person_id,
            content="Feeling tired today."
        )
        await create_memory(
            person_id=self.person_id,
            content="Skipped my morning workout due to fatigue."
        )

        # TODO: Run synthesis worker and verify
        pytest.skip("Worker import pending")

    @pytest.mark.asyncio
    async def test_preserves_important_details(self):
        """Test that synthesis preserves key details from source memories."""
        pytest.skip("Worker import pending")
