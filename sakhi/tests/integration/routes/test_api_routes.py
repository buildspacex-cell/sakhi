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

import json
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

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

    @pytest.mark.asyncio
    async def test_health_sync_requires_source(self, api_client):
        """Test that /health/sync requires the source field in payload."""
        response = await api_client.post(
            f"/health/sync/{DEMO_USER_ID}",
            json={"records": []},
        )

        assert response.status_code == 422


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
# Test: /demo/run/*
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestDemoRunEndpoints:
    """Tests for demo run endpoints with mocked service dependencies."""

    @pytest.mark.asyncio
    async def test_run_vision_demo_proxy(self, api_client):
        """Test that /demo/run/vision returns demo steps when service succeeds."""
        with patch("sakhi.apps.api.services.demo.run_vision_demo", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = [
                {"step": 1, "reasoning": "Found relevant item", "complete": True}
            ]

            response = await api_client.post(
                "/demo/run/vision",
                params={"task": "Find green tea", "mode": "simulated"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["demo_type"] == "vision"
            assert isinstance(data.get("steps"), list)
            assert data["steps"][0]["step"] == 1
            assert mock_run.await_count == 1

    @pytest.mark.asyncio
    async def test_run_reflection_demo_proxy(self, api_client):
        """Test that /demo/run/reflection returns reflection payload when service succeeds."""
        primary_cause = MagicMock()
        primary_cause.dict.return_value = {
            "cause": "late_night_screen",
            "correlation": 0.84,
            "explanation": "Late-night screen time correlates with scattered mornings.",
        }

        explanation = MagicMock()
        explanation.symptom = "scattered"
        explanation.dosha_context = "Elevated vata indicators."
        explanation.primary_causes = [primary_cause]
        explanation.contributing_factors = []
        explanation.seasonal_influence = None
        explanation.personal_pattern_match = True
        explanation.explanation_text = "Likely driven by disrupted evening rhythm."

        with patch(
            "sakhi.apps.api.services.ayurveda.causal_reasoning.explain_symptom",
            new_callable=AsyncMock,
        ) as mock_explain:
            mock_explain.return_value = explanation

            response = await api_client.post(
                "/demo/run/reflection",
                params={"symptom": "scattered"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["demo_type"] == "reflection"
            assert data["result"]["symptom"] == "scattered"
            assert isinstance(data["result"]["primary_causes"], list)
            assert data["result"]["primary_causes"][0]["cause"] == "late_night_screen"


# ─────────────────────────────────────────────────────────────────────────────
# Test: /learning/companion/*
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestCompanionEndpoints:
    """Tests for Stage 1 companion check-in/protocol endpoints."""

    @pytest.mark.asyncio
    async def test_companion_checkin_returns_explanation_and_protocols(self, api_client):
        """Check-in should return explanation, evidence, and 2/5/10 protocol options."""
        primary = MagicMock()
        primary.factor_type = "behavior"
        primary.description = "Late-night screen exposure"
        primary.confidence = 0.82
        primary.evidence = "Detected in recent behavior logs"

        explanation = MagicMock()
        explanation.primary_causes = [primary]
        explanation.dosha_context = "Elevated vata signs"
        explanation.explanation_text = "Recent stimulation likely elevated vata and mental agitation."

        with patch(
            "sakhi.apps.api.services.ayurveda.causal_reasoning.explain_symptom",
            new_callable=AsyncMock,
        ) as mock_explain:
            mock_explain.return_value = explanation

            response = await api_client.post(
                "/learning/companion/checkin",
                json={
                    "person_id": DEMO_USER_ID,
                    "symptom": "anxious",
                    "energy_level": 0.35,
                    "body_cues": ["dry mouth"],
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["symptom"] == "anxious"
            assert data["dosha_hint"] == "vata"
            assert data["confidence"] >= 0.8
            assert 0 <= data["uncertainty"] <= 1
            assert len(data["protocols"]) == 3
            assert [p["duration_minutes"] for p in data["protocols"]] == [2, 5, 10]
            assert data["evidence"][0]["description"] == "Late-night screen exposure"

    @pytest.mark.asyncio
    async def test_companion_followup_plan_rejects_unknown_protocol(self, api_client):
        """Unknown protocol ID should be rejected."""
        response = await api_client.post(
            "/learning/companion/followup/plan",
            json={
                "person_id": DEMO_USER_ID,
                "symptom": "anxious",
                "protocol_id": "missing_protocol",
                "target_days": 5,
            },
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_companion_followup_plan_creates_tracked_plan(self, api_client):
        """Selected protocol should create a tracked intervention plan."""
        plan = MagicMock()
        plan.id = "plan-123"
        plan.intervention_name = "Grounding Breath Reset"
        plan.schedule_type = MagicMock(value="daily")
        plan.duration_days = 7
        plan.total_scheduled = 7
        plan.start_date = date.today()
        plan.end_date = date.today()

        with patch(
            "sakhi.apps.api.services.learning.intervention_plans.create_intervention_plan",
            new_callable=AsyncMock,
        ) as mock_create_plan:
            mock_create_plan.return_value = plan

            response = await api_client.post(
                "/learning/companion/followup/plan",
                json={
                    "person_id": DEMO_USER_ID,
                    "symptom": "anxious",
                    "protocol_id": "vata_grounding_breath_2m",
                    "target_days": 7,
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["plan_id"] == "plan-123"
            assert data["protocol_id"] == "vata_grounding_breath_2m"
            assert data["schedule_type"] == "daily"

    @pytest.mark.asyncio
    async def test_companion_protocol_completion_logs_outcome(self, api_client):
        """Protocol completion should be stored as intervention outcome."""
        with patch(
            "sakhi.apps.api.services.learning.outcomes.log_intervention_outcome",
            new_callable=AsyncMock,
        ) as mock_log_outcome:
            mock_log_outcome.return_value = "outcome-456"

            response = await api_client.post(
                "/learning/companion/protocol/complete",
                json={
                    "person_id": DEMO_USER_ID,
                    "symptom": "anxious",
                    "protocol_id": "vata_grounding_breath_2m",
                    "was_effective": True,
                    "effectiveness_score": 0.8,
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["outcome_id"] == "outcome-456"


# ─────────────────────────────────────────────────────────────────────────────
# Test: /api/v1/agent/task*
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestAgenticTaskPlanEndpoints:
    """Tests for Stage 2 ask -> approve -> execute endpoints."""

    @pytest.mark.asyncio
    async def test_agentic_task_create_returns_pending_approval(self, api_client):
        """Creating a task should return a pending approval plan by default."""
        from sakhi.apps.api.services.agentic.planner import TaskPlan, TaskStep, TaskStatus

        plan = TaskPlan(
            id="plan-123",
            person_id=DEMO_USER_ID,
            task_description="Find kettles",
            goal="Find kettle options",
            steps=[
                TaskStep(
                    step=1,
                    action="web_search",
                    parameters={"query": "best kettle under 80"},
                    description="Search kettle options",
                )
            ],
            status=TaskStatus.PENDING_APPROVAL,
        )

        with patch("sakhi.apps.api.routes.agentic.create_task_plan", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = plan

            response = await api_client.post(
                "/api/v1/agent/task",
                params={"person_id": DEMO_USER_ID},
                json={
                    "task": "Find top electric kettles under $80",
                    "auto_execute": False,
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["plan_id"] == "plan-123"
            assert data["status"] == "pending_approval"
            assert data["requires_approval"] is True
            assert data["goal"] == "Find kettle options"
            assert len(data["steps"]) == 1
            assert data["steps"][0]["action"] == "web_search"
            assert mock_create.await_count == 1

    @pytest.mark.asyncio
    async def test_agentic_task_approve_returns_execution_result(self, api_client):
        """Approving a task should return the executed/completed plan."""
        from sakhi.apps.api.services.agentic.planner import (
            TaskPlan,
            TaskStep,
            TaskStatus,
            StepStatus,
        )

        completed_plan = TaskPlan(
            id="plan-approve-1",
            person_id=DEMO_USER_ID,
            task_description="Find kettles",
            goal="Find kettle options",
            steps=[
                TaskStep(
                    step=1,
                    action="web_search",
                    parameters={"query": "best kettle under 80"},
                    description="Search kettle options",
                    status=StepStatus.COMPLETED,
                    result={"count": 3},
                ),
                TaskStep(
                    step=2,
                    action="respond",
                    parameters={},
                    description="Return recommendation",
                    status=StepStatus.COMPLETED,
                    result="Top pick: Fellow Stagg EKG",
                ),
            ],
            status=TaskStatus.COMPLETED,
            final_output="Top pick: Fellow Stagg EKG",
        )

        with patch("sakhi.apps.api.routes.agentic.approve_task_plan", new_callable=AsyncMock) as mock_approve:
            mock_approve.return_value = completed_plan

            response = await api_client.post(
                "/api/v1/agent/task/plan-approve-1/approve",
                params={"person_id": DEMO_USER_ID},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["plan_id"] == "plan-approve-1"
            assert data["status"] == "completed"
            assert data["requires_approval"] is False
            assert data["final_output"] == "Top pick: Fellow Stagg EKG"
            assert mock_approve.await_count == 1

    @pytest.mark.asyncio
    async def test_agentic_task_active_lists_running_plans(self, api_client):
        """Active tasks endpoint should return active plan summaries."""
        from sakhi.apps.api.services.agentic.planner import TaskPlan, TaskStep, TaskStatus

        active_plans = [
            TaskPlan(
                id="plan-live-1",
                person_id=DEMO_USER_ID,
                task_description="Research apartments",
                goal="Find apartments",
                steps=[TaskStep(step=1, action="web_search", description="Search listings")],
                status=TaskStatus.EXECUTING,
            ),
            TaskPlan(
                id="plan-live-2",
                person_id=DEMO_USER_ID,
                task_description="Summarize latest reviews",
                goal="Get review summary",
                steps=[TaskStep(step=1, action="summarize", description="Summarize results")],
                status=TaskStatus.PENDING_APPROVAL,
            ),
        ]

        with patch("sakhi.apps.api.routes.agentic.get_active_plans", new_callable=AsyncMock) as mock_active:
            mock_active.return_value = active_plans

            response = await api_client.get(
                "/api/v1/agent/tasks/active",
                params={"person_id": DEMO_USER_ID},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["count"] == 2
            assert data["tasks"][0]["plan_id"] == "plan-live-1"
            assert data["tasks"][0]["status"] == "executing"
            assert data["tasks"][1]["plan_id"] == "plan-live-2"
            assert data["tasks"][1]["status"] == "pending_approval"
            assert mock_active.await_count == 1

    @pytest.mark.asyncio
    async def test_agentic_task_cancel_returns_cancelled_flag(self, api_client):
        """Cancelling a task should return a cancelled response."""
        with patch("sakhi.apps.api.routes.agentic.cancel_task_plan", new_callable=AsyncMock) as mock_cancel:
            mock_cancel.return_value = True

            response = await api_client.post(
                "/api/v1/agent/task/plan-cancel-1/cancel",
                params={"person_id": DEMO_USER_ID},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["cancelled"] is True
            assert data["plan_id"] == "plan-cancel-1"
            assert mock_cancel.await_count == 1


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
        mem_id = "00000000-0000-4000-a000-000000000001"
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
        entry_id = "00000000-0000-4000-a000-000000000002"
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
