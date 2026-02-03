"""
Unit tests for presence/nudge workers.

Workers tested:
- send_rhythm_nudge: Send contextual nudges based on rhythm
- check_inactive_users: Detect and handle inactive users
- nudge_worker: Core nudge delivery logic
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta

from sakhi.tests.fixtures import DEMO_USER_ID


class TestSendRhythmNudge:
    """Tests for send_rhythm_nudge worker."""

    @pytest.mark.asyncio
    async def test_sends_nudge_when_rhythm_exists(self, mock_db):
        """
        Given: User has rhythm data
        When: send_rhythm_nudge runs
        Then: Nudge is composed and sent
        """
        with patch("sakhi.apps.worker.tasks.send_rhythm_nudge.db_fetch") as mock_fetch, \
             patch("sakhi.apps.worker.tasks.send_rhythm_nudge.compose_response", new_callable=AsyncMock) as mock_compose, \
             patch("sakhi.apps.worker.tasks.send_rhythm_nudge.send_message") as mock_send:

            mock_fetch.return_value = {
                "person_id": DEMO_USER_ID,
                "avg_energy": 0.7,
                "avg_mood": 0.6,
            }
            mock_compose.return_value = "Take a mindful break!"

            from sakhi.apps.worker.tasks.send_rhythm_nudge import send_rhythm_nudge
            await send_rhythm_nudge(DEMO_USER_ID)

            mock_fetch.assert_called_once_with("rhythmprint", {"person_id": DEMO_USER_ID})
            mock_compose.assert_called_once()
            mock_send.assert_called_once_with(DEMO_USER_ID, "Take a mindful break!")

    @pytest.mark.asyncio
    async def test_skips_nudge_when_no_rhythm(self, mock_db):
        """
        Given: User has no rhythm data
        When: send_rhythm_nudge runs
        Then: No nudge is sent
        """
        with patch("sakhi.apps.worker.tasks.send_rhythm_nudge.db_fetch") as mock_fetch, \
             patch("sakhi.apps.worker.tasks.send_rhythm_nudge.send_message") as mock_send:

            mock_fetch.return_value = None

            from sakhi.apps.worker.tasks.send_rhythm_nudge import send_rhythm_nudge
            await send_rhythm_nudge(DEMO_USER_ID)

            mock_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_uses_default_energy_when_missing(self, mock_db):
        """
        Given: Rhythm data without energy field
        When: send_rhythm_nudge runs
        Then: Uses default energy of 0.5
        """
        with patch("sakhi.apps.worker.tasks.send_rhythm_nudge.db_fetch") as mock_fetch, \
             patch("sakhi.apps.worker.tasks.send_rhythm_nudge.compose_response", new_callable=AsyncMock) as mock_compose, \
             patch("sakhi.apps.worker.tasks.send_rhythm_nudge.send_message"):

            mock_fetch.return_value = {"person_id": DEMO_USER_ID}
            mock_compose.return_value = "nudge"

            from sakhi.apps.worker.tasks.send_rhythm_nudge import send_rhythm_nudge
            await send_rhythm_nudge(DEMO_USER_ID)

            # Check compose was called with default energy
            call_args = mock_compose.call_args
            assert call_args[1]["context"]["energy"] == 0.5


class TestCheckInactiveUsers:
    """Tests for check_inactive_users worker."""

    @pytest.mark.asyncio
    async def test_detects_inactive_user(self, mock_db):
        """
        Given: User hasn't interacted for 24+ hours
        When: check_inactive_users runs
        Then: Reconnection nudge is sent
        """
        old_time = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()

        with patch("sakhi.apps.worker.tasks.check_inactive_users.db_find") as mock_find, \
             patch("sakhi.apps.worker.tasks.check_inactive_users.compose_response", new_callable=AsyncMock) as mock_compose, \
             patch("sakhi.apps.worker.tasks.check_inactive_users.send_message") as mock_send:

            mock_find.return_value = [{
                "person_id": DEMO_USER_ID,
                "last_interaction_ts": old_time,
                "last_emotion": "calm",
            }]
            mock_compose.return_value = "We miss you!"

            from sakhi.apps.worker.tasks.check_inactive_users import _check_inactive_users_async
            await _check_inactive_users_async()

            mock_compose.assert_called_once()
            mock_send.assert_called_once_with(DEMO_USER_ID, "We miss you!")

    @pytest.mark.asyncio
    async def test_skips_active_user(self, mock_db):
        """
        Given: User interacted within 24 hours
        When: check_inactive_users runs
        Then: No nudge is sent
        """
        recent_time = (datetime.now(timezone.utc) - timedelta(hours=12)).isoformat()

        with patch("sakhi.apps.worker.tasks.check_inactive_users.db_find") as mock_find, \
             patch("sakhi.apps.worker.tasks.check_inactive_users.send_message") as mock_send:

            mock_find.return_value = [{
                "person_id": DEMO_USER_ID,
                "last_interaction_ts": recent_time,
            }]

            from sakhi.apps.worker.tasks.check_inactive_users import _check_inactive_users_async
            await _check_inactive_users_async()

            mock_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_handles_empty_user_list(self, mock_db):
        """
        Given: No users in session continuity
        When: check_inactive_users runs
        Then: Completes without error
        """
        with patch("sakhi.apps.worker.tasks.check_inactive_users.db_find") as mock_find:
            mock_find.return_value = []

            from sakhi.apps.worker.tasks.check_inactive_users import _check_inactive_users_async
            await _check_inactive_users_async()  # Should not raise


class TestNudgeWorker:
    """Tests for nudge_worker - core nudge delivery."""

    @pytest.mark.asyncio
    async def test_sends_nudge_when_should_send(self, mock_db):
        """
        Given: compute_nudge returns should_send=True
        When: run_nudge_check runs
        Then: Nudge is logged and sent
        """
        with patch("sakhi.apps.worker.tasks.nudge_worker.resolve_person_id", new_callable=AsyncMock) as mock_resolve, \
             patch("sakhi.apps.worker.tasks.nudge_worker.q", new_callable=AsyncMock) as mock_q, \
             patch("sakhi.apps.worker.tasks.nudge_worker.dbexec", new_callable=AsyncMock) as mock_exec, \
             patch("sakhi.apps.worker.tasks.nudge_worker.compute_nudge", new_callable=AsyncMock) as mock_compute, \
             patch("sakhi.libs.scaffolding.suppression_engine.check_scaffold_suppression", new_callable=AsyncMock) as mock_suppress:

            mock_resolve.return_value = DEMO_USER_ID
            mock_q.return_value = {"forecast_state": {}}
            # Suppression returns ALLOW action
            mock_suppress.return_value = MagicMock(action=MagicMock(value="allow"))
            mock_compute.return_value = {
                "should_send": True,
                "category": "wellness",
                "message": "Time for a stretch!",
            }

            from sakhi.apps.worker.tasks.nudge_worker import run_nudge_check
            result = await run_nudge_check(DEMO_USER_ID)

            assert result["should_send"] is True
            assert mock_exec.called  # Logged to nudge_log

    @pytest.mark.asyncio
    async def test_skips_nudge_when_should_not_send(self, mock_db):
        """
        Given: compute_nudge returns should_send=False
        When: run_nudge_check runs
        Then: No nudge is logged
        """
        with patch("sakhi.apps.worker.tasks.nudge_worker.resolve_person_id", new_callable=AsyncMock) as mock_resolve, \
             patch("sakhi.apps.worker.tasks.nudge_worker.q", new_callable=AsyncMock) as mock_q, \
             patch("sakhi.apps.worker.tasks.nudge_worker.dbexec", new_callable=AsyncMock) as mock_exec, \
             patch("sakhi.apps.worker.tasks.nudge_worker.compute_nudge", new_callable=AsyncMock) as mock_compute, \
             patch("sakhi.libs.scaffolding.suppression_engine.check_scaffold_suppression", new_callable=AsyncMock) as mock_suppress:

            mock_resolve.return_value = DEMO_USER_ID
            mock_q.return_value = {}
            mock_suppress.return_value = MagicMock(action=MagicMock(value="allow"))
            mock_compute.return_value = {"should_send": False}

            from sakhi.apps.worker.tasks.nudge_worker import run_nudge_check
            result = await run_nudge_check(DEMO_USER_ID)

            assert result["should_send"] is False
            mock_exec.assert_not_called()

    @pytest.mark.asyncio
    async def test_handles_missing_forecast(self, mock_db):
        """
        Given: No forecast data exists
        When: run_nudge_check runs
        Then: Uses empty dict and completes
        """
        with patch("sakhi.apps.worker.tasks.nudge_worker.resolve_person_id", new_callable=AsyncMock) as mock_resolve, \
             patch("sakhi.apps.worker.tasks.nudge_worker.q", new_callable=AsyncMock) as mock_q, \
             patch("sakhi.apps.worker.tasks.nudge_worker.compute_nudge", new_callable=AsyncMock) as mock_compute, \
             patch("sakhi.libs.scaffolding.suppression_engine.check_scaffold_suppression", new_callable=AsyncMock) as mock_suppress:

            mock_resolve.return_value = DEMO_USER_ID
            mock_q.return_value = None  # No forecast
            mock_suppress.return_value = MagicMock(action=MagicMock(value="allow"))
            mock_compute.return_value = {"should_send": False}

            from sakhi.apps.worker.tasks.nudge_worker import run_nudge_check
            result = await run_nudge_check(DEMO_USER_ID)

            # Should complete without error
            assert "should_send" in result
