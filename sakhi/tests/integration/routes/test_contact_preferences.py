"""
Integration tests for contact preferences API routes.

Tests the full API flow: create, read, update, delete preferences.
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
# CRUD Tests
# =============================================================================


class TestPreferencesCRUD:
    """Tests for contact preferences CRUD operations."""

    def test_list_preferences_empty(self, client):
        """GET /email/preferences should return empty list for new user."""
        with patch(
            "sakhi.apps.api.services.email.contact_preferences.dbfetch",
            new_callable=AsyncMock,
            return_value=[],
        ):
            response = client.get(f"/email/preferences?person_id={DEMO_USER_ID}")
            assert response.status_code == 200
            data = response.json()
            assert "preferences" in data
            assert data["preferences"] == []

    def test_create_preference(self, client):
        """PUT /email/preferences should create a new preference."""
        import uuid
        from datetime import datetime, timezone

        mock_row = {
            "id": uuid.uuid4(),
            "person_id": uuid.UUID(DEMO_USER_ID),
            "contact_identifier": "boss@acme.com",
            "channel": "email",
            "display_name": "Sarah",
            "relationship": "boss",
            "organization": "Acme Corp",
            "priority": "critical",
            "notes": "Always reply same day",
            "learned_from": "user_set",
            "confidence": 1.0,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }

        with patch(
            "sakhi.apps.api.services.email.contact_preferences.dbfetch",
            new_callable=AsyncMock,
            return_value=mock_row,
        ):
            response = client.put(
                f"/email/preferences?person_id={DEMO_USER_ID}",
                json={
                    "contact_identifier": "boss@acme.com",
                    "display_name": "Sarah",
                    "relationship": "boss",
                    "organization": "Acme Corp",
                    "priority": "critical",
                    "notes": "Always reply same day",
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["contact_identifier"] == "boss@acme.com"
            assert data["priority"] == "critical"

    def test_create_preference_validates_priority(self, client):
        """PUT /email/preferences should reject invalid priority."""
        response = client.put(
            f"/email/preferences?person_id={DEMO_USER_ID}",
            json={
                "contact_identifier": "boss@acme.com",
                "priority": "super_important",
            },
        )
        assert response.status_code == 400
        assert "priority" in response.json()["detail"]

    def test_create_preference_validates_empty_identifier(self, client):
        """PUT /email/preferences should reject empty contact_identifier."""
        response = client.put(
            f"/email/preferences?person_id={DEMO_USER_ID}",
            json={
                "contact_identifier": "  ",
                "priority": "high",
            },
        )
        assert response.status_code == 400
        assert "contact_identifier" in response.json()["detail"]

    def test_delete_preference_success(self, client):
        """DELETE /email/preferences/{id} should delete preference."""
        with patch(
            "sakhi.apps.api.services.email.contact_preferences.dbexec",
            new_callable=AsyncMock,
            return_value="DELETE 1",
        ):
            response = client.delete(
                f"/email/preferences/some-uuid?person_id={DEMO_USER_ID}"
            )
            assert response.status_code == 200
            assert response.json()["deleted"] is True

    def test_delete_preference_not_found(self, client):
        """DELETE /email/preferences/{id} should return 404 if not found."""
        with patch(
            "sakhi.apps.api.services.email.contact_preferences.dbexec",
            new_callable=AsyncMock,
            return_value="DELETE 0",
        ):
            response = client.delete(
                f"/email/preferences/nonexistent?person_id={DEMO_USER_ID}"
            )
            assert response.status_code == 404


# =============================================================================
# Suggestions Tests
# =============================================================================


class TestPreferenceSuggestions:
    """Tests for dismiss-based suggestions endpoint."""

    def test_suggestions_returns_mute_candidates(self, client):
        """GET /email/preferences/suggestions should return senders to mute."""
        mock_rows = [
            {"contact_identifier": "vendor@spam.com", "dismiss_count": 5},
        ]

        with patch(
            "sakhi.apps.api.services.email.contact_preferences.dbfetch",
            new_callable=AsyncMock,
            return_value=mock_rows,
        ):
            response = client.get(
                f"/email/preferences/suggestions?person_id={DEMO_USER_ID}"
            )
            assert response.status_code == 200
            data = response.json()
            assert "suggestions" in data
            assert len(data["suggestions"]) == 1
            assert data["suggestions"][0]["suggested_priority"] == "muted"

    def test_suggestions_empty_when_no_dismissals(self, client):
        """GET /email/preferences/suggestions should return empty if no patterns."""
        with patch(
            "sakhi.apps.api.services.email.contact_preferences.dbfetch",
            new_callable=AsyncMock,
            return_value=[],
        ):
            response = client.get(
                f"/email/preferences/suggestions?person_id={DEMO_USER_ID}"
            )
            assert response.status_code == 200
            assert response.json()["suggestions"] == []
