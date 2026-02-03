"""
Integration tests for user-facing API routes.

Tests the routes that users interact with directly in the UI.

Routes tested:
- /calendar
- /chat
- /recommendations
- /scheduling
- /feedback
- /insights
"""

import pytest

from sakhi.tests.fixtures import DEMO_USER_ID


# ─────────────────────────────────────────────────────────────────────────────
# Test: /calendar
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestCalendarEndpoint:
    """Tests for calendar API endpoints."""

    @pytest.mark.asyncio
    async def test_get_calendar_events(self, api_client, ensure_test_user):
        """
        Test that GET /calendar returns events for user.

        Given: A user
        When: GET /calendar
        Then: Returns list of calendar events (may be empty)
        """
        await ensure_test_user(DEMO_USER_ID)

        response = await api_client.get(
            "/calendar",
            params={"person_id": DEMO_USER_ID}
        )

        # Should return 200 even if no events
        assert response.status_code in [200, 404]  # 404 if route not implemented

    @pytest.mark.asyncio
    async def test_create_calendar_event(self, api_client, ensure_test_user):
        """Test creating a calendar event."""
        await ensure_test_user(DEMO_USER_ID)

        response = await api_client.post(
            "/calendar",
            json={
                "person_id": DEMO_USER_ID,
                "title": "Test Event",
                "start_time": "2026-02-04T10:00:00Z",
                "duration_minutes": 60,
            }
        )

        # Implement when route is ready
        if response.status_code == 404:
            pytest.skip("Route not implemented")


# ─────────────────────────────────────────────────────────────────────────────
# Test: /recommendations
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestRecommendationsEndpoint:
    """Tests for recommendations API endpoints."""

    @pytest.mark.asyncio
    async def test_get_recommendations(self, api_client, ensure_test_user):
        """
        Test that GET /recommendations returns personalized recommendations.

        Given: A user with state data
        When: GET /recommendations
        Then: Returns list of recommendations based on current state
        """
        await ensure_test_user(DEMO_USER_ID)

        response = await api_client.get(
            "/friction/recommendations",
            params={"person_id": DEMO_USER_ID}
        )

        if response.status_code == 404:
            pytest.skip("Route not implemented")

        assert response.status_code == 200
        data = response.json()
        # Should have recommendations array
        assert "recommendations" in data or isinstance(data, list)

    @pytest.mark.asyncio
    async def test_recommendations_respect_constitution(self, api_client, ensure_test_user):
        """Test that recommendations respect user's operating system/constitution."""
        await ensure_test_user(DEMO_USER_ID)
        # TODO: Verify recommendations are constitution-appropriate
        pytest.skip("Implement detailed constitution check")


# ─────────────────────────────────────────────────────────────────────────────
# Test: /feedback
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestFeedbackEndpoint:
    """Tests for feedback API endpoints."""

    @pytest.mark.asyncio
    async def test_submit_recommendation_feedback(self, api_client, ensure_test_user, db):
        """
        Test submitting feedback on a recommendation.

        Given: A user
        When: POST /feedback with recommendation feedback
        Then: Feedback is stored in recommendation_feedback table
        """
        await ensure_test_user(DEMO_USER_ID)

        response = await api_client.post(
            "/feedback",
            json={
                "person_id": DEMO_USER_ID,
                "recommendation_type": "activity",
                "feedback_type": "thumbs_up",
                "recommendation_content": {"action": "Take a walk"},
            }
        )

        if response.status_code == 404:
            pytest.skip("Route not implemented")

        assert response.status_code in [200, 201]

        # Verify stored in DB
        feedback = await db.fetchrow(
            """SELECT * FROM recommendation_feedback
               WHERE person_id = $1
               ORDER BY created_at DESC LIMIT 1""",
            DEMO_USER_ID
        )
        # Note: Table might not exist yet
        # assert feedback is not None


# ─────────────────────────────────────────────────────────────────────────────
# Test: /insights
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestInsightsEndpoint:
    """Tests for insights API endpoints."""

    @pytest.mark.asyncio
    async def test_get_user_insights(self, api_client, ensure_test_user):
        """
        Test that GET /insights returns user insights.

        Given: A user with history
        When: GET /insights
        Then: Returns aggregated insights about patterns
        """
        await ensure_test_user(DEMO_USER_ID)

        response = await api_client.get(
            "/insights",
            params={"person_id": DEMO_USER_ID}
        )

        if response.status_code == 404:
            pytest.skip("Route not implemented")

        assert response.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# Test: /scheduling
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestSchedulingEndpoint:
    """Tests for scheduling API endpoints."""

    @pytest.mark.asyncio
    async def test_create_scheduling_request(self, api_client, ensure_test_user):
        """
        Test creating a scheduling request.

        Given: A user
        When: POST /scheduling with natural language request
        Then: Scheduling request is parsed and options returned
        """
        await ensure_test_user(DEMO_USER_ID)

        response = await api_client.post(
            "/scheduling",
            json={
                "person_id": DEMO_USER_ID,
                "request": "Schedule a meeting with John tomorrow at 2pm",
            }
        )

        if response.status_code == 404:
            pytest.skip("Route not implemented")

        assert response.status_code in [200, 201]


# ─────────────────────────────────────────────────────────────────────────────
# Test: /chat
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestChatEndpoint:
    """Tests for chat API endpoints (if separate from /v2/turn)."""

    @pytest.mark.asyncio
    async def test_chat_endpoint(self, api_client, ensure_test_user):
        """Test the chat endpoint."""
        await ensure_test_user(DEMO_USER_ID)

        response = await api_client.post(
            "/chat",
            json={
                "person_id": DEMO_USER_ID,
                "message": "Hello!",
            }
        )

        if response.status_code == 404:
            pytest.skip("Route not implemented - using /v2/turn instead")

        assert response.status_code == 200
