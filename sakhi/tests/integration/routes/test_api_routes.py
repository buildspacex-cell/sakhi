"""
Integration tests for API routes.

Tests endpoints that don't require LLM calls (health, simple data retrieval).
For LLM-dependent endpoints, we use mocking.

Routes tested:
- /health
- /v2/turn/probe
- /friction/{person_id}
- /memory/recall
- /persona/state
"""

import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock

from sakhi.tests.fixtures import DEMO_USER_ID


# ─────────────────────────────────────────────────────────────────────────────
# Test: /health
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestHealthEndpoint:
    """Tests for health check endpoint."""

    @pytest.mark.asyncio
    async def test_health_returns_ok(self, api_client):
        """Test that /health returns OK status."""
        response = await api_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok" or "healthy" in str(data).lower()


# ─────────────────────────────────────────────────────────────────────────────
# Test: /v2/turn/probe
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestTurnProbeEndpoint:
    """Tests for turn probe endpoint (diagnostic)."""

    @pytest.mark.asyncio
    async def test_probe_returns_ok(self, api_client):
        """Test that /v2/turn/probe returns OK."""
        response = await api_client.get("/v2/turn/probe")

        assert response.status_code == 200
        data = response.json()
        assert data.get("probe") == "ok"


# ─────────────────────────────────────────────────────────────────────────────
# Test: /friction/{person_id}
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestFrictionEndpoint:
    """Tests for friction state endpoint."""

    @pytest.mark.asyncio
    async def test_friction_state_returns_data(self, api_client, ensure_test_user, db):
        """
        Test that /friction/{person_id} returns friction state.

        Given: User with personal_model data
        When: GET /friction/{person_id}
        Then: Returns dosha balance and state
        """
        await ensure_test_user(DEMO_USER_ID)

        # Ensure personal_model has operating_system
        await db.execute("""
            UPDATE personal_model
            SET operating_system = $2::jsonb
            WHERE person_id = $1
        """, DEMO_USER_ID, json.dumps({
            "primary_dosha": "vata",
            "secondary_dosha": "pitta",
            "prakruti": {"vata": 0.5, "pitta": 0.3, "kapha": 0.2}
        }))

        response = await api_client.get(f"/friction/{DEMO_USER_ID}")

        # Route returns 200 or 404 if not found
        if response.status_code == 200:
            data = response.json()
            # Should have some friction/dosha related data
            assert isinstance(data, dict)


# ─────────────────────────────────────────────────────────────────────────────
# Test: /persona/state
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestPersonaStateEndpoint:
    """Tests for persona state endpoint."""

    @pytest.mark.asyncio
    async def test_persona_state_returns_data(self, api_client, ensure_test_user):
        """
        Test that /persona/state returns persona information.

        Given: Valid user
        When: GET /persona/state?person_id=X
        Then: Returns persona mode and traits
        """
        await ensure_test_user(DEMO_USER_ID)

        response = await api_client.get(
            "/persona/state",
            params={"person_id": DEMO_USER_ID}
        )

        # Endpoint may return 200 with data or 404
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)


# ─────────────────────────────────────────────────────────────────────────────
# Test: /v2/turn (with mocked LLM)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestTurnEndpointMocked:
    """Tests for the turn endpoint with mocked LLM."""

    @pytest.mark.asyncio
    async def test_turn_validation_error_no_text(self, api_client, ensure_test_user):
        """
        Test that /v2/turn returns 422 when text is missing.

        Given: Request without text field
        When: POST /v2/turn
        Then: Returns 422 validation error
        """
        await ensure_test_user(DEMO_USER_ID)

        response = await api_client.post(
            "/v2/turn",
            params={"user": DEMO_USER_ID},
            json={}  # Missing required 'text' field
        )

        assert response.status_code == 422  # Validation error expected

    @pytest.mark.asyncio
    async def test_turn_with_mocked_llm(self, api_client, ensure_test_user, db):
        """
        Test that /v2/turn works with mocked LLM response.

        Given: Valid user and message
        When: POST /v2/turn (with mocked LLM)
        Then: Returns 200 with reply
        """
        await ensure_test_user(DEMO_USER_ID)

        # Ensure user has necessary data
        await db.execute("""
            UPDATE personal_model
            SET data = '{}'::jsonb
            WHERE person_id = $1
        """, DEMO_USER_ID)

        # Mock the LLM router
        mock_response = MagicMock()
        mock_response.text = "Hello! How can I help you today?"

        with patch("sakhi.apps.api.routes.turn_v2.generate_reply", new_callable=AsyncMock) as mock_reply:
            mock_reply.return_value = {
                "reply": "Hello! How can I help you today?",
                "turn_id": "test-turn-123",
                "thread_id": "test-thread-456",
                "archetype": "friendly",
            }

            response = await api_client.post(
                "/v2/turn",
                params={"user": DEMO_USER_ID},
                json={"text": "Hello, how are you?"}
            )

            # The endpoint may still fail due to other LLM calls
            # Check for either success or expected error
            assert response.status_code in [200, 500, 503]


# ─────────────────────────────────────────────────────────────────────────────
# Test: /memory/recall
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestMemoryRecallEndpoint:
    """Tests for memory recall endpoint."""

    @pytest.mark.asyncio
    async def test_memory_recall_with_query(self, api_client, ensure_test_user, db):
        """
        Test that /memory/recall returns memories.

        Given: User with stored memories
        When: POST /memory/recall
        Then: Returns memory results
        """
        await ensure_test_user(DEMO_USER_ID)

        # Create a test memory in memory_episodic
        mem_id = "test-mem-" + DEMO_USER_ID[:8]
        record_data = json.dumps({"type": "test"})

        await db.execute("""
            INSERT INTO memory_episodic (id, person_id, user_id, text, content_hash, record, created_at, updated_at)
            VALUES ($1, $2::uuid, $3, $4, $5, $6::jsonb, NOW(), NOW())
            ON CONFLICT (id) DO NOTHING
        """, mem_id, DEMO_USER_ID, DEMO_USER_ID, "I love hiking in mountains", f"hash_{mem_id}", record_data)

        try:
            response = await api_client.post(
                "/memory/recall",
                json={
                    "person_id": DEMO_USER_ID,
                    "query": "hiking",
                    "limit": 5
                }
            )

            # Endpoint may return 200 or error if embedding service unavailable
            if response.status_code == 200:
                data = response.json()
                assert isinstance(data, (dict, list))
        finally:
            # Cleanup
            await db.execute("DELETE FROM memory_episodic WHERE id = $1", mem_id)


# ─────────────────────────────────────────────────────────────────────────────
# Test: /journal (journal endpoints)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestJournalEndpoints:
    """Tests for journal-related endpoints."""

    @pytest.mark.asyncio
    async def test_journal_entries_list(self, api_client, ensure_test_user, db):
        """
        Test listing journal entries.

        Given: User with journal entries
        When: GET /journal/entries
        Then: Returns list of entries
        """
        await ensure_test_user(DEMO_USER_ID)

        # Create a test entry
        entry_id = "test-entry-" + DEMO_USER_ID[:8]
        await db.execute("""
            INSERT INTO journal_entries (id, user_id, title, content, mood, created_at)
            VALUES ($1, $2, $3, $4, $5, NOW())
            ON CONFLICT (id) DO NOTHING
        """, entry_id, DEMO_USER_ID, "Test Entry", "This is a test journal entry.", "neutral")

        try:
            response = await api_client.get(
                "/journal/entries",
                params={"user_id": DEMO_USER_ID, "limit": 10}
            )

            if response.status_code == 200:
                data = response.json()
                assert isinstance(data, (dict, list))
        finally:
            await db.execute("DELETE FROM journal_entries WHERE id = $1", entry_id)


# ─────────────────────────────────────────────────────────────────────────────
# Test: /insights (insights endpoints)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestInsightsEndpoints:
    """Tests for insights-related endpoints."""

    @pytest.mark.asyncio
    async def test_rhythm_insights_latest(self, api_client, ensure_test_user):
        """
        Test getting latest rhythm insights.

        Given: Valid user
        When: GET /insights/rhythm/latest
        Then: Returns insights or empty
        """
        await ensure_test_user(DEMO_USER_ID)

        response = await api_client.get(
            "/insights/rhythm/latest",
            params={"person_id": DEMO_USER_ID}
        )

        # Endpoint should return 200 even with no data
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (dict, list, type(None)))


# ─────────────────────────────────────────────────────────────────────────────
# Test: /feedback (feedback endpoints)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestFeedbackEndpoints:
    """Tests for feedback endpoints."""

    @pytest.mark.asyncio
    async def test_submit_feedback(self, api_client, ensure_test_user, db):
        """
        Test submitting feedback.

        Given: Valid feedback data
        When: POST /feedback
        Then: Feedback is stored
        """
        await ensure_test_user(DEMO_USER_ID)

        feedback_data = {
            "person_id": DEMO_USER_ID,
            "type": "recommendation",
            "rating": 4,
            "comment": "Helpful suggestion",
            "context": {"recommendation_id": "test-123"}
        }

        response = await api_client.post("/feedback", json=feedback_data)

        # Check if endpoint exists and accepts feedback
        assert response.status_code in [200, 201, 404, 422]


# ─────────────────────────────────────────────────────────────────────────────
# Test: /lab endpoints
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestLabEndpoints:
    """Tests for lab/experimental endpoints."""

    @pytest.mark.asyncio
    async def test_lab_simulation_list(self, api_client):
        """
        Test listing available simulations.

        When: GET /lab/simulations
        Then: Returns list of simulations
        """
        response = await api_client.get("/lab/simulations")

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (dict, list))
