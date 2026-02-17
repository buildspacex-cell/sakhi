"""
Unit tests for state update workers.

Workers tested:
- task_weaver_refresh: Refreshes task priorities
- soul_refresh_worker: Refreshes soul/prakriti state
- identity_momentum_deep: Tracks identity momentum
- coherence_refresh: Refreshes coherence state
- alignment_refresh: Refreshes alignment state
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from sakhi.tests.fixtures import DEMO_USER_ID
from sakhi.apps.worker.tasks.alignment_refresh import (
    run_alignment_refresh,
    _derive_alignment_state,
)
from sakhi.apps.worker.tasks.coherence_refresh import run_coherence_refresh


class TestTaskWeaverRefresh:
    """Tests for task_weaver_refresh worker."""

    @pytest.mark.asyncio
    async def test_prioritizes_urgent_tasks(self, mock_db):
        """
        Given: Tasks with various deadlines
        When: task_weaver_refresh runs
        Then: Urgent tasks are prioritized
        """
        pass  # TODO: Implement

    @pytest.mark.asyncio
    async def test_considers_energy_state(self, mock_db):
        """
        Given: User's current energy level
        When: task_weaver_refresh runs
        Then: Task ordering respects energy
        """
        pass  # TODO: Implement

    @pytest.mark.asyncio
    async def test_respects_user_preferences(self, mock_db):
        """
        Given: User's task preferences
        When: task_weaver_refresh runs
        Then: Preferences influence ordering
        """
        pass  # TODO: Implement


class TestSoulRefreshWorker:
    """Tests for soul_refresh_worker."""

    @pytest.mark.asyncio
    async def test_refreshes_prakriti_state(self, mock_db):
        """
        Given: User's baseline constitution
        When: soul_refresh_worker runs
        Then: Prakriti state is refreshed
        """
        pass  # TODO: Implement

    @pytest.mark.asyncio
    async def test_updates_soul_values(self, mock_db):
        """
        Given: Value-related observations
        When: soul_refresh_worker runs
        Then: Soul values are updated
        """
        pass  # TODO: Implement

    @pytest.mark.asyncio
    async def test_tracks_purpose_evolution(self, mock_db):
        """
        Given: Purpose-related conversations
        When: soul_refresh_worker runs
        Then: Purpose themes are tracked
        """
        pass  # TODO: Implement


class TestIdentityMomentumDeep:
    """Tests for identity_momentum_deep worker."""

    @pytest.mark.asyncio
    async def test_tracks_identity_changes(self, mock_db):
        """
        Given: Changes in user expression
        When: identity_momentum_deep runs
        Then: Changes are tracked
        """
        pass  # TODO: Implement

    @pytest.mark.asyncio
    async def test_detects_growth_patterns(self, mock_db):
        """
        Given: Progressive changes
        When: identity_momentum_deep runs
        Then: Growth pattern is detected
        """
        pass  # TODO: Implement

    @pytest.mark.asyncio
    async def test_maintains_momentum_score(self, mock_db):
        """
        Given: Identity trajectory
        When: identity_momentum_deep runs
        Then: Momentum score is updated
        """
        pass  # TODO: Implement


class TestCoherenceRefresh:
    """Tests for run_coherence_refresh worker."""

    @pytest.mark.asyncio
    @patch("sakhi.apps.worker.tasks.coherence_refresh.resolve_person_id", new_callable=AsyncMock)
    @patch("sakhi.apps.worker.tasks.coherence_refresh.compute_coherence", new_callable=AsyncMock)
    @patch("sakhi.apps.worker.tasks.coherence_refresh.dbexec", new_callable=AsyncMock)
    @patch("sakhi.apps.worker.tasks.coherence_refresh.get_settings")
    async def test_writes_coherence_state(self, mock_settings, mock_dbexec, mock_compute, mock_resolve):
        """
        Given: compute_coherence returns a valid state
        When: run_coherence_refresh runs
        Then: coherence_cache and personal_model are both updated
        """
        mock_settings.return_value = MagicMock(enable_identity_workers=True)
        mock_resolve.return_value = DEMO_USER_ID
        mock_compute.return_value = {
            "coherence_score": 0.72,
            "fragmentation_index": 0.15,
            "coherence_map": {"thought": 0.8, "emotion": 0.7},
            "issues": [],
            "adjustments": [],
            "summary": "Coherence stable",
            "confidence": 0.85,
            "updated_at": "2026-02-17T00:00:00",
        }

        result = await run_coherence_refresh(DEMO_USER_ID)

        assert result["updated"] is True
        assert result["coherence_score"] == 0.72
        assert mock_dbexec.call_count == 2
        # First call: coherence_cache UPSERT
        assert "coherence_cache" in mock_dbexec.call_args_list[0][0][0]
        # Second call: personal_model UPDATE
        assert "personal_model" in mock_dbexec.call_args_list[1][0][0]

    @pytest.mark.asyncio
    @patch("sakhi.apps.worker.tasks.coherence_refresh.get_settings")
    async def test_skips_when_disabled(self, mock_settings):
        """
        Given: enable_identity_workers is False
        When: run_coherence_refresh runs
        Then: No DB writes, returns disabled reason
        """
        mock_settings.return_value = MagicMock(enable_identity_workers=False)

        result = await run_coherence_refresh(DEMO_USER_ID)

        assert result["updated"] is False
        assert result["reason"] == "disabled"

    @pytest.mark.asyncio
    @patch("sakhi.apps.worker.tasks.coherence_refresh.resolve_person_id", new_callable=AsyncMock)
    @patch("sakhi.apps.worker.tasks.coherence_refresh.compute_coherence", new_callable=AsyncMock)
    @patch("sakhi.apps.worker.tasks.coherence_refresh.get_settings")
    async def test_handles_engine_error(self, mock_settings, mock_compute, mock_resolve):
        """
        Given: compute_coherence raises an exception
        When: run_coherence_refresh runs
        Then: Returns error result, does not crash
        """
        mock_settings.return_value = MagicMock(enable_identity_workers=True)
        mock_resolve.return_value = DEMO_USER_ID
        mock_compute.side_effect = RuntimeError("DB connection failed")

        result = await run_coherence_refresh(DEMO_USER_ID)

        assert result["updated"] is False
        assert "DB connection failed" in result["error"]


class TestAlignmentRefresh:
    """Tests for run_alignment_refresh worker."""

    @pytest.mark.asyncio
    @patch("sakhi.apps.worker.tasks.alignment_refresh.resolve_person_id", new_callable=AsyncMock)
    @patch("sakhi.apps.worker.tasks.alignment_refresh.compute_alignment_map", new_callable=AsyncMock)
    @patch("sakhi.apps.worker.tasks.alignment_refresh.dbexec", new_callable=AsyncMock)
    async def test_writes_alignment_state(self, mock_dbexec, mock_compute, mock_resolve):
        """
        Given: compute_alignment_map returns a valid map
        When: run_alignment_refresh runs
        Then: daily_alignment_cache and personal_model are both updated
        """
        mock_resolve.return_value = DEMO_USER_ID
        mock_compute.return_value = {
            "recommended_actions": [
                {"id": "1", "title": "Morning walk", "score": 0.8, "energy_cost": 0.3},
                {"id": "2", "title": "Read chapter", "score": 0.6, "energy_cost": 0.2},
            ],
            "avoid_actions": [
                {"id": "3", "title": "Heavy workout", "score": 0.2, "energy_cost": 0.9},
            ],
            "energy_profile": "medium",
            "focus_profile": "scattered",
            "intent_alignment": [],
            "emotional_safeguards": [],
            "self_care_suggestions": ["grounding breath cycle"],
        }

        result = await run_alignment_refresh(DEMO_USER_ID)

        assert result["updated"] is True
        assert result["alignment_score"] > 0
        assert mock_dbexec.call_count == 2
        # First call: daily_alignment_cache UPSERT
        assert "daily_alignment_cache" in mock_dbexec.call_args_list[0][0][0]
        # Second call: personal_model UPDATE
        assert "personal_model" in mock_dbexec.call_args_list[1][0][0]

    def test_derives_scores_correctly(self):
        """
        Given: An alignment map with known recommended/avoid/safeguard counts
        When: _derive_alignment_state is called
        Then: alignment_score, tension_score, conflict_zones are correct
        """
        alignment_map = {
            "recommended_actions": [
                {"title": "Walk", "score": 0.8, "energy_cost": 0.3},
                {"title": "Read", "score": 0.6, "energy_cost": 0.2},
                {"title": "Meditate", "score": 0.7, "energy_cost": 0.1},
            ],
            "avoid_actions": [
                {"title": "Heavy workout", "score": 0.2, "energy_cost": 0.9},
            ],
            "energy_profile": "medium",
            "focus_profile": "clear",
            "emotional_safeguards": ["delay difficult tasks"],
            "self_care_suggestions": ["rest"],
        }

        state = _derive_alignment_state(alignment_map)

        # 3 recommended / 4 total = 0.75
        assert state["alignment_score"] == 0.75
        # 1 avoid / 4 total + 0.1 * 1 safeguard = 0.25 + 0.1 = 0.35
        assert state["tension_score"] == 0.35
        assert "Heavy workout" in state["conflict_zones"]
        assert "delay difficult tasks" in state["conflict_zones"]
        assert "Walk" in state["action_suggestions"]
        assert state["energy_profile"] == "medium"
        assert state["self_care_suggestions"] == ["rest"]

    def test_derives_scores_all_recommended(self):
        """
        Given: All tasks are recommended, no avoid, no safeguards
        When: _derive_alignment_state is called
        Then: alignment_score is 1.0, tension_score is 0.0
        """
        alignment_map = {
            "recommended_actions": [{"title": "Task A"}, {"title": "Task B"}],
            "avoid_actions": [],
            "emotional_safeguards": [],
            "self_care_suggestions": [],
        }

        state = _derive_alignment_state(alignment_map)

        assert state["alignment_score"] == 1.0
        assert state["tension_score"] == 0.0
        assert state["conflict_zones"] == []

    @pytest.mark.asyncio
    @patch("sakhi.apps.worker.tasks.alignment_refresh.resolve_person_id", new_callable=AsyncMock)
    @patch("sakhi.apps.worker.tasks.alignment_refresh.compute_alignment_map", new_callable=AsyncMock)
    async def test_handles_no_data(self, mock_compute, mock_resolve):
        """
        Given: compute_alignment_map returns None
        When: run_alignment_refresh runs
        Then: Returns no_data result
        """
        mock_resolve.return_value = DEMO_USER_ID
        mock_compute.return_value = None

        result = await run_alignment_refresh(DEMO_USER_ID)

        assert result["updated"] is False
        assert result["reason"] == "no_data"
