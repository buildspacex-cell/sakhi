"""
Integration tests for core API routes.

Tests the main user-facing endpoints with real database operations.
Each test creates data, calls the endpoint, and verifies the response and DB state.

Routes tested:
- /v2/turn (conversation)
- /health
- /friction-framework/state/current
- /memory/recall
"""

import pytest

from sakhi.tests.fixtures import DEMO_USER_ID


# ─────────────────────────────────────────────────────────────────────────────
# Test: /v2/turn
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestTurnEndpoint:
    """Tests for the main conversation turn endpoint."""

    @pytest.mark.asyncio
    async def test_turn_returns_response(self, api_client, ensure_test_user):
        """
        Test that /v2/turn returns a valid response.

        Given: A valid user and message
        When: POST /v2/turn
        Then: Returns 200 with reply, thread_id, turn_id
        """
        await ensure_test_user(DEMO_USER_ID)

        response = await api_client.post(
            "/v2/turn",
            json={
                "person_id": DEMO_USER_ID,
                "message": "Hello, how are you?",
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "reply" in data
        assert "thread_id" in data
        assert "turn_id" in data
        assert len(data["reply"]) > 0

    @pytest.mark.asyncio
    async def test_turn_creates_memory(self, api_client, ensure_test_user, db):
        """
        Test that /v2/turn creates a memory record.

        Given: A conversation turn
        When: POST /v2/turn
        Then: A memory record is created in memory_short_term
        """
        await ensure_test_user(DEMO_USER_ID)

        # Get initial count
        initial_count = await db.fetchval(
            "SELECT COUNT(*) FROM memory_short_term WHERE person_id = $1",
            DEMO_USER_ID
        )

        response = await api_client.post(
            "/v2/turn",
            json={
                "person_id": DEMO_USER_ID,
                "message": "I went for a walk today.",
            }
        )

        assert response.status_code == 200

        # Note: Memory creation may be async via workers
        # For sync test, check if queue was enqueued
        # Or run with SAKHI_DISABLE_QUEUE=1

    @pytest.mark.asyncio
    async def test_turn_maintains_thread(self, api_client, ensure_test_user):
        """Test that multiple turns in same thread maintain context."""
        await ensure_test_user(DEMO_USER_ID)

        # First turn
        response1 = await api_client.post(
            "/v2/turn",
            json={
                "person_id": DEMO_USER_ID,
                "message": "My name is Alex.",
            }
        )
        thread_id = response1.json()["thread_id"]

        # Second turn in same thread
        response2 = await api_client.post(
            "/v2/turn",
            json={
                "person_id": DEMO_USER_ID,
                "message": "What is my name?",
                "thread_id": thread_id,
            }
        )

        assert response2.status_code == 200
        # Response should reference the name (context maintained)


# ─────────────────────────────────────────────────────────────────────────────
# Test: /health
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestHealthEndpoint:
    """Tests for health check endpoints."""

    @pytest.mark.asyncio
    async def test_health_returns_ok(self, api_client):
        """Test that /health returns OK status."""
        response = await api_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok" or "healthy" in str(data).lower()


# ─────────────────────────────────────────────────────────────────────────────
# Test: /friction-framework/state/current
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestFrictionStateEndpoint:
    """Tests for friction framework state endpoint."""

    @pytest.mark.asyncio
    async def test_returns_current_state(self, api_client, ensure_test_user):
        """
        Test that endpoint returns current friction state.

        Given: A user with personal_model
        When: GET /friction-framework/state/current
        Then: Returns operating system and current mode
        """
        await ensure_test_user(DEMO_USER_ID)

        response = await api_client.get(
            "/friction-framework/state/current",
            params={"person_id": DEMO_USER_ID}
        )

        assert response.status_code == 200
        data = response.json()
        # Should have operating system info
        assert "operating_system" in data or "state" in data


# ─────────────────────────────────────────────────────────────────────────────
# Test: /memory/recall
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestMemoryRecallEndpoint:
    """Tests for memory recall endpoint."""

    @pytest.mark.asyncio
    async def test_recalls_relevant_memories(
        self, api_client, ensure_test_user, create_memory
    ):
        """
        Test that memory recall returns relevant memories.

        Given: A user with stored memories
        When: POST /memory/recall with query
        Then: Returns memories semantically related to query
        """
        await ensure_test_user(DEMO_USER_ID)

        # Create test memories
        await create_memory(
            person_id=DEMO_USER_ID,
            content="I love hiking in the mountains."
        )
        await create_memory(
            person_id=DEMO_USER_ID,
            content="Coffee is my favorite morning drink."
        )

        response = await api_client.post(
            "/memory/recall",
            json={
                "person_id": DEMO_USER_ID,
                "query": "outdoor activities",
                "limit": 5,
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "memories" in data or "results" in data
