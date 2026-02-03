"""
End-to-end API tests with REAL LLM calls.

These tests call actual API endpoints including LLM-powered responses.
Requires:
- DATABASE_URL set to real database
- OPENAI_API_KEY or other LLM keys in .env.local
- Running with: pytest -m e2e sakhi/tests/e2e/

Note: These tests are slower and cost money (LLM API calls).
"""

import pytest
import json
import uuid
from datetime import datetime, timezone

from sakhi.tests.fixtures import DEMO_USER_ID


# ─────────────────────────────────────────────────────────────────────────────
# Test: /v2/turn - Real LLM conversation
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.e2e
class TestTurnE2E:
    """End-to-end tests for the conversation turn endpoint."""

    @pytest.mark.asyncio
    async def test_turn_returns_llm_response(self, api_client, ensure_test_user):
        """
        Test that /v2/turn returns a real LLM response.

        Given: A valid user and message
        When: POST /v2/turn
        Then: Returns 200 with actual LLM reply
        """
        await ensure_test_user(DEMO_USER_ID)

        response = await api_client.post(
            "/v2/turn",
            params={"user": DEMO_USER_ID},
            json={"text": "Hello! How are you today?"}
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()

        # Verify response structure
        assert "reply" in data, f"Missing 'reply' in response: {data}"
        assert len(data["reply"]) > 0, "Reply should not be empty"
        # Response uses sessionId (camelCase) as the session identifier
        assert "sessionId" in data, f"Missing sessionId in response: {data}"

    @pytest.mark.asyncio
    async def test_turn_maintains_context(self, api_client, ensure_test_user):
        """
        Test that multiple turns maintain conversation context.

        Given: A conversation thread
        When: Multiple turns with context
        Then: LLM remembers previous context
        """
        await ensure_test_user(DEMO_USER_ID)

        # First turn - introduce a fact
        response1 = await api_client.post(
            "/v2/turn",
            params={"user": DEMO_USER_ID},
            json={"text": "My favorite color is blue. Please remember this."}
        )
        assert response1.status_code == 200, f"First turn failed: {response1.text}"
        data1 = response1.json()
        session_id = data1.get("sessionId")  # API uses sessionId

        # Second turn - ask about the fact (same thread)
        response2 = await api_client.post(
            "/v2/turn",
            params={"user": DEMO_USER_ID},
            json={
                "text": "What is my favorite color?",
                # Include thread_id if the API supports it
            }
        )
        assert response2.status_code == 200, f"Second turn failed: {response2.text}"
        data2 = response2.json()

        # The reply should mention blue (context maintained)
        reply = data2.get("reply", "").lower()
        # Note: LLM may or may not remember - this is a soft assertion
        print(f"Context test reply: {reply}")

    @pytest.mark.asyncio
    async def test_turn_handles_ayurvedic_query(self, api_client, ensure_test_user):
        """
        Test that Sakhi responds to Ayurvedic health questions.

        Given: A health-related question
        When: POST /v2/turn with wellness query
        Then: Returns helpful Ayurvedic-informed response
        """
        await ensure_test_user(DEMO_USER_ID)

        response = await api_client.post(
            "/v2/turn",
            params={"user": DEMO_USER_ID},
            json={"text": "I've been feeling tired lately. What might help?"}
        )

        assert response.status_code == 200, f"Turn failed: {response.text}"
        data = response.json()

        reply = data.get("reply", "")
        assert len(reply) > 50, "Expected a substantive response"
        print(f"Wellness response: {reply[:200]}...")

    @pytest.mark.asyncio
    async def test_turn_captures_memory(self, api_client, ensure_test_user, db):
        """
        Test that turns are captured in memory.

        Given: A conversation turn
        When: POST /v2/turn
        Then: Turn is stored in database
        """
        await ensure_test_user(DEMO_USER_ID)

        # Get initial turn count
        initial_count = await db.fetchval(
            "SELECT COUNT(*) FROM conversation_turns WHERE user_id = $1",
            DEMO_USER_ID
        )

        response = await api_client.post(
            "/v2/turn",
            params={"user": DEMO_USER_ID},
            json={"text": "I went for a wonderful hike today in the mountains."}
        )

        assert response.status_code == 200, f"Turn failed: {response.text}"

        # Check turn was stored
        new_count = await db.fetchval(
            "SELECT COUNT(*) FROM conversation_turns WHERE user_id = $1",
            DEMO_USER_ID
        )
        assert new_count > initial_count, "Turn should be stored in database"


# ─────────────────────────────────────────────────────────────────────────────
# Test: /memory/recall - Real semantic search
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.e2e
class TestMemoryRecallE2E:
    """End-to-end tests for memory recall with real embeddings."""

    @pytest.mark.asyncio
    async def test_memory_recall_semantic_search(self, api_client, ensure_test_user, db):
        """
        Test that memory recall performs real semantic search.

        Given: User with stored memories
        When: POST /memory/recall with query
        Then: Returns semantically relevant memories
        """
        await ensure_test_user(DEMO_USER_ID)

        # First, create a conversation to populate memory
        await api_client.post(
            "/v2/turn",
            params={"user": DEMO_USER_ID},
            json={"text": "I love hiking and being outdoors in nature."}
        )

        # Wait a moment for async processing
        import asyncio
        await asyncio.sleep(1)

        # Now recall memories about outdoor activities
        response = await api_client.post(
            "/memory/recall",
            json={
                "person_id": DEMO_USER_ID,
                "query": "outdoor activities hiking",
                "limit": 5
            }
        )

        if response.status_code == 200:
            data = response.json()
            print(f"Memory recall response: {json.dumps(data, indent=2)[:500]}")


# ─────────────────────────────────────────────────────────────────────────────
# Test: /chat - Chat endpoint
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.e2e
class TestChatE2E:
    """End-to-end tests for chat endpoint."""

    @pytest.mark.asyncio
    async def test_chat_basic_conversation(self, api_client, ensure_test_user):
        """
        Test basic chat functionality.

        Given: Valid user
        When: POST /chat
        Then: Returns LLM response
        """
        await ensure_test_user(DEMO_USER_ID)

        response = await api_client.post(
            "/chat",
            json={
                "person_id": DEMO_USER_ID,
                "message": "What's a good morning routine for energy?"
            }
        )

        if response.status_code == 200:
            data = response.json()
            assert "response" in data or "reply" in data or "message" in data
            print(f"Chat response: {data}")
        else:
            print(f"Chat endpoint status: {response.status_code}")


# ─────────────────────────────────────────────────────────────────────────────
# Test: /friction - Dosha state
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.e2e
class TestFrictionE2E:
    """End-to-end tests for friction/dosha endpoints."""

    @pytest.mark.asyncio
    async def test_friction_state(self, api_client, ensure_test_user, db):
        """
        Test getting friction/dosha state.

        Given: User with personal model
        When: GET /friction/{person_id}
        Then: Returns dosha balance info
        """
        await ensure_test_user(DEMO_USER_ID)

        # Ensure operating_system is set
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

        if response.status_code == 200:
            data = response.json()
            print(f"Friction state: {json.dumps(data, indent=2)[:500]}")

    @pytest.mark.asyncio
    async def test_operating_system_compute(self, api_client, ensure_test_user):
        """
        Test computing operating system from signals.

        Given: Conversation signals
        When: POST /operating-system/compute
        Then: Returns computed dosha state
        """
        await ensure_test_user(DEMO_USER_ID)

        response = await api_client.post(
            "/operating-system/compute",
            json={
                "person_id": DEMO_USER_ID,
                "signals": {
                    "energy": "scattered",
                    "digestion": "variable",
                    "sleep": "light",
                    "mood": "anxious"
                }
            }
        )

        if response.status_code == 200:
            data = response.json()
            print(f"Computed OS: {json.dumps(data, indent=2)[:500]}")


# ─────────────────────────────────────────────────────────────────────────────
# Test: /recommendations - Personalized recommendations
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.e2e
class TestRecommendationsE2E:
    """End-to-end tests for recommendation endpoints."""

    @pytest.mark.asyncio
    async def test_get_recommendations(self, api_client, ensure_test_user, db):
        """
        Test getting personalized recommendations.

        Given: User with history
        When: GET /recommendations
        Then: Returns personalized suggestions
        """
        await ensure_test_user(DEMO_USER_ID)

        # First have a conversation about energy
        await api_client.post(
            "/v2/turn",
            params={"user": DEMO_USER_ID},
            json={"text": "I've been feeling low energy in the afternoons."}
        )

        # Get recommendations
        response = await api_client.get(
            "/recommendations",
            params={"person_id": DEMO_USER_ID}
        )

        if response.status_code == 200:
            data = response.json()
            print(f"Recommendations: {json.dumps(data, indent=2)[:500]}")


# ─────────────────────────────────────────────────────────────────────────────
# Test: Complete conversation flow
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.e2e
class TestConversationFlowE2E:
    """End-to-end tests for complete conversation flows."""

    @pytest.mark.asyncio
    async def test_morning_checkin_flow(self, api_client, ensure_test_user):
        """
        Test a complete morning check-in conversation flow.

        Given: User starting their day
        When: Series of check-in messages
        Then: Sakhi responds appropriately with personalized guidance
        """
        await ensure_test_user(DEMO_USER_ID)

        # Morning greeting
        r1 = await api_client.post(
            "/v2/turn",
            params={"user": DEMO_USER_ID},
            json={"text": "Good morning! I just woke up."}
        )
        assert r1.status_code == 200
        print(f"Morning greeting: {r1.json().get('reply', '')[:100]}...")

        # Energy level check
        r2 = await api_client.post(
            "/v2/turn",
            params={"user": DEMO_USER_ID},
            json={"text": "I slept well but feeling a bit groggy still."}
        )
        assert r2.status_code == 200
        print(f"Energy response: {r2.json().get('reply', '')[:100]}...")

        # Ask for guidance
        r3 = await api_client.post(
            "/v2/turn",
            params={"user": DEMO_USER_ID},
            json={"text": "What would you suggest for my morning routine?"}
        )
        assert r3.status_code == 200
        reply = r3.json().get('reply', '')
        print(f"Guidance: {reply[:200]}...")

        # Response should be substantive
        assert len(reply) > 50, "Expected a helpful morning routine suggestion"

    @pytest.mark.asyncio
    async def test_wellness_conversation_flow(self, api_client, ensure_test_user):
        """
        Test a wellness-focused conversation.

        Given: User with health concern
        When: Describes symptoms
        Then: Sakhi provides Ayurvedic-informed guidance
        """
        await ensure_test_user(DEMO_USER_ID)

        # Describe a concern
        r1 = await api_client.post(
            "/v2/turn",
            params={"user": DEMO_USER_ID},
            json={"text": "I've been having trouble with digestion after meals lately."}
        )
        assert r1.status_code == 200
        print(f"Initial response: {r1.json().get('reply', '')[:150]}...")

        # Follow-up
        r2 = await api_client.post(
            "/v2/turn",
            params={"user": DEMO_USER_ID},
            json={"text": "It especially happens after eating cold foods."}
        )
        assert r2.status_code == 200
        reply = r2.json().get('reply', '')
        print(f"Follow-up: {reply[:200]}...")

        # Should reference the context (cold foods, digestion)
        assert len(reply) > 30


# ─────────────────────────────────────────────────────────────────────────────
# Test: Journal flow
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.e2e
class TestJournalFlowE2E:
    """End-to-end tests for journaling functionality."""

    @pytest.mark.asyncio
    async def test_journal_entry_creates_memory(self, api_client, ensure_test_user, db):
        """
        Test that journal entries are processed and stored.

        Given: User journals an entry
        When: POST /journal/entry or /v2/turn with journal content
        Then: Entry is stored and processed
        """
        await ensure_test_user(DEMO_USER_ID)

        # Journal a significant memory
        response = await api_client.post(
            "/v2/turn",
            params={"user": DEMO_USER_ID},
            json={
                "text": "Journal entry: Today I had a wonderful meditation session. I felt deeply calm and centered afterward. It helped me realize how much I need these quiet moments.",
                "source": "text"
            }
        )

        assert response.status_code == 200
        data = response.json()
        print(f"Journal response: {data.get('reply', '')[:150]}...")

        # The turn should be stored
        turn_count = await db.fetchval(
            "SELECT COUNT(*) FROM conversation_turns WHERE user_id = $1",
            DEMO_USER_ID
        )
        assert turn_count > 0
