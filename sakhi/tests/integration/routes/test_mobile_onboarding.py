"""
Integration tests for mobile phased onboarding API.

Tests the POST /onboarding/submit endpoint which supports:
- Phase 1: 3 mandatory questions
- Phase 2a: 3 optional questions (energy/recovery)
- Phase 2b: 7 optional questions (life context/decisions)

Each phase computes and returns an Operating System with confidence score.
"""

import json
from datetime import datetime, timezone

import pytest

from sakhi.tests.fixtures import DEMO_USER_ID

# Use the demo user ID for all tests
TEST_PERSON_ID = DEMO_USER_ID


# ─────────────────────────────────────────────────────────────────────────────
# Test Data
# ─────────────────────────────────────────────────────────────────────────────

PHASE1_RESPONSES = {
    "preferred_name": "Test User",
    "clarity_window": "morning",
    "pacing_under_demand": "push_harder",
    "first_stress_signal": "irritability",
}

PHASE2A_RESPONSES = {
    "current_energy": "steady",
    "body_request": "quiet_space",
    "fastest_recovery": "calm_time",
}

PHASE2B_RESPONSES = {
    "life_phase": "building",
    "active_roles": ["professional", "partner_family"],
    "responsibility_load": "shared",
    "time_horizon": "year_two",
    "decision_driver": "make_progress",
    "flexibility_under_load": "reorganize",
    "body_rhythm": "menstrual_cycle",
}


async def reset_personal_model_for_test(db, person_id: str) -> None:
    """Reset the personal_model onboarding data for a test user.

    This only clears the onboarding-related fields, not the entire record,
    to avoid foreign key issues with the demo user.
    """
    await db.execute("""
        UPDATE personal_model
        SET operating_system = NULL,
            onboarding_source = NULL,
            onboarding_phase = NULL,
            phase1_completed_at = NULL,
            phase2a_completed_at = NULL,
            phase2b_completed_at = NULL
        WHERE person_id = $1
    """, person_id)


# ─────────────────────────────────────────────────────────────────────────────
# Test: POST /onboarding/submit - Phase 1
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestMobileOnboardingPhase1:
    """Tests for Phase 1 (mandatory) onboarding submission."""

    @pytest.mark.asyncio
    async def test_phase1_returns_operating_system(self, api_client, ensure_test_user, db):
        """
        Test that Phase 1 submission returns an Operating System.

        Given: Phase 1 responses (3 mandatory questions)
        When: POST /onboarding/submit with phase=phase1
        Then: Returns OS type, confidence ~0.55, label "Early snapshot"
        """
        test_person_id = TEST_PERSON_ID

        # Reset onboarding data
        await reset_personal_model_for_test(db, test_person_id)

        response = await api_client.post(
            "/onboarding/submit",
            json={
                "person_id": test_person_id,
                "source": "mobile",
                "phase": "phase1",
                "responses": PHASE1_RESPONSES,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Check response structure
        assert data["success"] is True
        assert data["person_id"] == test_person_id
        assert data["phase_completed"] == "phase1"
        assert "phase2a" in data["phases_remaining"]
        assert "phase2b" in data["phases_remaining"]

        # Check OS result
        assert data["operating_system"] in [
            "Adaptive", "Performance", "Conservation",
            "Adaptive-Performance", "Performance-Conservation",
            "Adaptive-Conservation", "Balanced"
        ]
        assert data["os_confidence"] >= 0.5
        assert data["os_confidence"] <= 0.6
        assert data["os_label"] == "Early snapshot"

        # Check OS details
        assert "os_details" in data
        assert len(data["os_details"]["strengths"]) > 0
        assert len(data["os_details"]["patterns_to_watch"]) > 0

        # Cleanup
        await reset_personal_model_for_test(db, test_person_id)

    @pytest.mark.asyncio
    async def test_phase1_stores_data_in_personal_model(self, api_client, db):
        """
        Test that Phase 1 submission stores data in personal_model.

        Given: Phase 1 responses
        When: POST /onboarding/submit
        Then: personal_model is created/updated with OS and phase tracking
        """
        test_person_id = TEST_PERSON_ID

        # Reset onboarding data
        await reset_personal_model_for_test(db, test_person_id)

        response = await api_client.post(
            "/onboarding/submit",
            json={
                "person_id": test_person_id,
                "source": "mobile",
                "phase": "phase1",
                "responses": PHASE1_RESPONSES,
            }
        )

        assert response.status_code == 200

        # Verify data was stored
        row = await db.fetchrow(
            "SELECT operating_system, onboarding_source, onboarding_phase FROM personal_model WHERE person_id = $1",
            test_person_id
        )

        assert row is not None
        assert row["onboarding_source"] == "mobile"
        assert row["onboarding_phase"] == "phase1"

        os_data = row["operating_system"]
        if isinstance(os_data, str):
            os_data = json.loads(os_data)
        assert os_data["phase"] == "phase1"
        assert os_data["source"] == "mobile"
        assert "onboarding_responses" in os_data

        # Cleanup
        await reset_personal_model_for_test(db, test_person_id)


# ─────────────────────────────────────────────────────────────────────────────
# Test: POST /onboarding/submit - Phase 2a
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestMobileOnboardingPhase2a:
    """Tests for Phase 2a (energy/recovery) onboarding submission."""

    @pytest.mark.asyncio
    async def test_phase2a_merges_with_phase1(self, api_client, db):
        """
        Test that Phase 2a merges responses with previously stored Phase 1.

        Given: Phase 1 completed, then Phase 2a submitted
        When: POST /onboarding/submit with phase=phase2a
        Then: Responses merged, OS recalculated, confidence increases
        """
        test_person_id = TEST_PERSON_ID

        # Reset onboarding data
        await reset_personal_model_for_test(db, test_person_id)

        # First, complete Phase 1
        response1 = await api_client.post(
            "/onboarding/submit",
            json={
                "person_id": test_person_id,
                "source": "mobile",
                "phase": "phase1",
                "responses": PHASE1_RESPONSES,
            }
        )
        assert response1.status_code == 200

        # Now complete Phase 2a
        response2 = await api_client.post(
            "/onboarding/submit",
            json={
                "person_id": test_person_id,
                "source": "mobile",
                "phase": "phase2a",
                "responses": PHASE2A_RESPONSES,
            }
        )

        assert response2.status_code == 200
        data = response2.json()

        # Check response
        assert data["phase_completed"] == "phase2a"
        assert data["phases_remaining"] == ["phase2b"]
        assert data["os_confidence"] >= 0.65
        assert data["os_confidence"] <= 0.75
        assert data["os_label"] == "Getting clearer"

        # Verify merged responses stored
        row = await db.fetchrow(
            "SELECT operating_system FROM personal_model WHERE person_id = $1",
            test_person_id
        )
        os_data = row["operating_system"]
        if isinstance(os_data, str):
            os_data = json.loads(os_data)

        merged_responses = os_data.get("onboarding_responses", {})
        # Should have both Phase 1 and Phase 2a responses
        assert "clarity_window" in merged_responses  # From Phase 1
        assert "current_energy" in merged_responses  # From Phase 2a

        # Cleanup
        await reset_personal_model_for_test(db, test_person_id)


# ─────────────────────────────────────────────────────────────────────────────
# Test: POST /onboarding/submit - Phase 2b
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestMobileOnboardingPhase2b:
    """Tests for Phase 2b (life context) onboarding submission."""

    @pytest.mark.asyncio
    async def test_phase2b_completes_onboarding(self, api_client, db):
        """
        Test that Phase 2b completes the full mobile onboarding flow.

        Given: Phase 1 and 2a completed
        When: POST /onboarding/submit with phase=phase2b
        Then: phases_remaining is empty, confidence is high, label is "Ready to go"
        """
        test_person_id = TEST_PERSON_ID

        # Reset onboarding data
        await reset_personal_model_for_test(db, test_person_id)

        # Complete Phase 1
        await api_client.post(
            "/onboarding/submit",
            json={
                "person_id": test_person_id,
                "source": "mobile",
                "phase": "phase1",
                "responses": PHASE1_RESPONSES,
            }
        )

        # Complete Phase 2a
        await api_client.post(
            "/onboarding/submit",
            json={
                "person_id": test_person_id,
                "source": "mobile",
                "phase": "phase2a",
                "responses": PHASE2A_RESPONSES,
            }
        )

        # Complete Phase 2b
        response = await api_client.post(
            "/onboarding/submit",
            json={
                "person_id": test_person_id,
                "source": "mobile",
                "phase": "phase2b",
                "responses": PHASE2B_RESPONSES,
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Check response
        assert data["phase_completed"] == "phase2b"
        assert data["phases_remaining"] == []
        assert data["os_confidence"] >= 0.80
        assert data["os_label"] == "Ready to go"

        # Verify all responses merged
        row = await db.fetchrow(
            "SELECT operating_system, life_context, decision_profile FROM personal_model WHERE person_id = $1",
            test_person_id
        )
        os_data = row["operating_system"]
        if isinstance(os_data, str):
            os_data = json.loads(os_data)

        merged_responses = os_data.get("onboarding_responses", {})
        # Should have responses from all phases
        assert "clarity_window" in merged_responses  # Phase 1
        assert "current_energy" in merged_responses  # Phase 2a
        assert "life_phase" in merged_responses      # Phase 2b
        assert "body_rhythm" in merged_responses     # Phase 2b (mobile-only)

        # Cleanup
        await reset_personal_model_for_test(db, test_person_id)


# ─────────────────────────────────────────────────────────────────────────────
# Test: Validation
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestMobileOnboardingValidation:
    """Tests for validation of onboarding requests."""

    @pytest.mark.asyncio
    async def test_invalid_phase_returns_400(self, api_client):
        """Test that invalid phase returns 400 error."""
        response = await api_client.post(
            "/onboarding/submit",
            json={
                "person_id": TEST_PERSON_ID,
                "source": "mobile",
                "phase": "invalid_phase",
                "responses": PHASE1_RESPONSES,
            }
        )

        assert response.status_code == 400
        assert "Invalid phase" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_missing_person_id_returns_422(self, api_client):
        """Test that missing person_id returns 422 validation error."""
        response = await api_client.post(
            "/onboarding/submit",
            json={
                "source": "mobile",
                "phase": "phase1",
                "responses": PHASE1_RESPONSES,
            }
        )

        assert response.status_code == 422


# ─────────────────────────────────────────────────────────────────────────────
# Test: Web Source Compatibility
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestWebSourceOnboarding:
    """Tests for web source using the new unified endpoint."""

    @pytest.mark.asyncio
    async def test_web_source_full_phase(self, api_client, db):
        """
        Test that web source can use 'full' phase for complete onboarding.

        Given: Web source with all responses
        When: POST /onboarding/submit with phase=full
        Then: Returns high confidence OS
        """
        test_person_id = TEST_PERSON_ID

        # Reset onboarding data
        await reset_personal_model_for_test(db, test_person_id)

        # Combine all responses
        all_responses = {
            **PHASE1_RESPONSES,
            **PHASE2A_RESPONSES,
            **PHASE2B_RESPONSES,
            "location": "San Francisco",
            "age_range": "35-44",
        }

        response = await api_client.post(
            "/onboarding/submit",
            json={
                "person_id": test_person_id,
                "source": "web",
                "phase": "full",
                "responses": all_responses,
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert data["phase_completed"] == "full"
        assert data["phases_remaining"] == []
        assert data["os_confidence"] >= 0.90
        assert data["os_label"] == "Complete profile"

        # Cleanup
        await reset_personal_model_for_test(db, test_person_id)
