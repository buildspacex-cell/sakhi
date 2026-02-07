"""
Integration tests for email API routes.

Tests the full API flow for email integration.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from sakhi.apps.api.main import app
from sakhi.tests.fixtures import DEMO_USER_ID

# =============================================================================
# Test Client
# =============================================================================

@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


# =============================================================================
# OAuth Flow Tests
# =============================================================================

class TestOAuthFlow:
    """Tests for Gmail OAuth connection flow."""

    def test_connect_gmail_returns_auth_url(self, client):
        """POST /email/connect/gmail should return Google OAuth URL."""
        with patch.dict("os.environ", {
            "GOOGLE_CLIENT_ID": "test-client-id",
            "GOOGLE_CLIENT_SECRET": "test-secret",
            "GMAIL_OAUTH_CALLBACK_URL": "http://localhost:8080/email/connect/gmail/callback",
        }):
            response = client.post(
                f"/email/connect/gmail?person_id={DEMO_USER_ID}",
                json={"app_redirect_uri": "http://localhost:3000/settings"},
            )

            assert response.status_code == 200
            data = response.json()
            assert "auth_url" in data
            assert "accounts.google.com" in data["auth_url"]
            assert "state" in data

    def test_connect_gmail_includes_readonly_scope(self, client):
        """OAuth URL should request read-only scope."""
        with patch.dict("os.environ", {
            "GOOGLE_CLIENT_ID": "test-client-id",
            "GOOGLE_CLIENT_SECRET": "test-secret",
        }):
            response = client.post(
                f"/email/connect/gmail?person_id={DEMO_USER_ID}",
                json={"app_redirect_uri": "http://localhost:3000/settings"},
            )

            data = response.json()
            assert "gmail.readonly" in data["auth_url"]

    def test_connect_gmail_requires_person_id(self, client):
        """Should require person_id parameter."""
        response = client.post(
            "/email/connect/gmail",
            json={"app_redirect_uri": "http://localhost:3000"},
        )

        assert response.status_code == 422  # Validation error

    def test_connect_gmail_requires_redirect_uri(self, client):
        """Should require app_redirect_uri in body."""
        response = client.post(
            f"/email/connect/gmail?person_id={DEMO_USER_ID}",
            json={},
        )

        assert response.status_code == 422


# =============================================================================
# Status Endpoint Tests
# =============================================================================

class TestStatusEndpoint:
    """Tests for email sync status endpoint."""

    def test_status_not_connected(self, client):
        """Should return not_connected for new users."""
        with patch(
            "sakhi.apps.api.routes.email.get_sync_state",
            new_callable=AsyncMock,
            return_value=None,
        ):
            response = client.get(
                f"/email/status?person_id={DEMO_USER_ID}"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["connected"] is False
            assert data["status"] == "not_connected"

    def test_status_requires_person_id(self, client):
        """Should require person_id parameter."""
        response = client.get("/email/status")

        assert response.status_code == 422


# =============================================================================
# Signals Endpoint Tests
# =============================================================================

class TestSignalsEndpoint:
    """Tests for email signals endpoints."""

    def test_signals_returns_structure(self, client):
        """GET /email/signals should return proper structure."""
        mock_signals = {
            "status": "loaded",
            "subscriptions": [],
            "avoidance": [],
            "boundary": {"erosion_score": 0.1},
            "cognitive_load": {"overwhelm_risk": "low"},
        }

        with patch(
            "sakhi.apps.api.routes.email.get_stored_signals",
            new_callable=AsyncMock,
            return_value=mock_signals,
        ):
            response = client.get(
                f"/email/signals?person_id={DEMO_USER_ID}"
            )

            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert "subscriptions" in data
            assert "avoidance" in data

    def test_avoidance_signals_filters_by_days(self, client):
        """Should filter avoidance by minimum days."""
        mock_signals = {
            "status": "loaded",
            "avoidance": [
                {"duration_days": 5, "thread_id": "short"},
                {"duration_days": 15, "thread_id": "long"},
            ],
        }

        with patch(
            "sakhi.apps.api.routes.email.get_stored_signals",
            new_callable=AsyncMock,
            return_value=mock_signals,
        ):
            response = client.get(
                f"/email/signals/avoidance?person_id={DEMO_USER_ID}&min_days=10"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["count"] == 1
            assert data["patterns"][0]["thread_id"] == "long"

    def test_subscription_signals_filters_by_category(self, client):
        """Should filter subscriptions by category."""
        mock_signals = {
            "status": "loaded",
            "subscriptions": [
                {"sender_email": "news@example.com", "category": "news"},
                {"sender_email": "promo@store.com", "category": "marketing"},
            ],
        }

        with patch(
            "sakhi.apps.api.routes.email.get_stored_signals",
            new_callable=AsyncMock,
            return_value=mock_signals,
        ):
            response = client.get(
                f"/email/signals/subscriptions?person_id={DEMO_USER_ID}&category=news"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["count"] == 1


# =============================================================================
# Insight Endpoint Tests
# =============================================================================

class TestInsightEndpoint:
    """Tests for surfaceable insight endpoint."""

    def test_insight_no_data(self, client):
        """Should return has_insight=false when no signals."""
        with patch(
            "sakhi.apps.api.routes.email.get_surfaceable_insight",
            new_callable=AsyncMock,
            return_value=None,
        ):
            response = client.get(
                f"/email/insight?person_id={DEMO_USER_ID}"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["has_insight"] is False

    def test_insight_with_avoidance(self, client):
        """Should return insight when avoidance pattern exists."""
        mock_insight = {
            "type": "avoidance",
            "suggested_phrasing": "You have an email waiting...",
            "data": {"thread_id": "test", "duration_days": 10},
        }

        with patch(
            "sakhi.apps.api.routes.email.get_surfaceable_insight",
            new_callable=AsyncMock,
            return_value=mock_insight,
        ):
            response = client.get(
                f"/email/insight?person_id={DEMO_USER_ID}"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["has_insight"] is True
            assert data["type"] == "avoidance"
            assert "suggested_phrasing" in data


# =============================================================================
# Context Endpoint Tests
# =============================================================================

class TestContextEndpoint:
    """Tests for conversation context endpoint."""

    def test_context_returns_summary(self, client):
        """Should return context summary for conversation."""
        mock_context = "Email patterns:\n- 2 threads awaiting reply"

        with patch(
            "sakhi.apps.api.routes.email.get_email_context_for_conversation",
            new_callable=AsyncMock,
            return_value=mock_context,
        ):
            response = client.get(
                f"/email/context?person_id={DEMO_USER_ID}"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["has_context"] is True
            assert "Email patterns" in data["context"]


# =============================================================================
# Disconnect Endpoint Tests
# =============================================================================

class TestDisconnectEndpoint:
    """Tests for email disconnection."""

    def test_disconnect_success(self, client):
        """Should disconnect and return success."""
        with patch(
            "sakhi.apps.api.routes.email.disconnect_email",
            new_callable=AsyncMock,
            return_value=True,
        ):
            response = client.post(
                f"/email/disconnect?person_id={DEMO_USER_ID}"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "disconnected"

    def test_disconnect_not_connected(self, client):
        """Should handle disconnect when not connected."""
        with patch(
            "sakhi.apps.api.routes.email.disconnect_email",
            new_callable=AsyncMock,
            return_value=False,
        ):
            response = client.post(
                f"/email/disconnect?person_id={DEMO_USER_ID}"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "not_connected"


# =============================================================================
# Sync Endpoint Tests
# =============================================================================

class TestSyncEndpoints:
    """Tests for sync control endpoints."""

    def test_sync_requires_connection(self, client):
        """Should error when trying to sync without connection."""
        with patch(
            "sakhi.apps.api.routes.email.get_sync_state",
            new_callable=AsyncMock,
            return_value=None,
        ):
            response = client.post(
                f"/email/sync?person_id={DEMO_USER_ID}"
            )

            assert response.status_code == 400

    def test_pause_sync(self, client):
        """Should pause sync successfully."""
        with patch(
            "sakhi.apps.api.routes.email.pause_sync",
            new_callable=AsyncMock,
            return_value=True,
        ):
            response = client.post(
                f"/email/sync/pause?person_id={DEMO_USER_ID}"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "paused"
