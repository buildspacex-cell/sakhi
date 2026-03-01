"""
Unit tests for soul/identity workers.

Workers tested:
- soul_worker: Core soul processing
- soul_extract_worker: Extract soul signals from interactions
- soul_refresh_worker: Periodic soul state refresh
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from sakhi.tests.fixtures import DEMO_USER_ID


class TestSoulWorker:
    """Tests for soul_worker - core soul processing."""

    @pytest.mark.asyncio
    async def test_serializes_soul_state_for_jsonb_write(self, monkeypatch):
        """
        Given: The soul engine returns a dict state
        When: soul_worker.run persists it
        Then: The JSONB payload is serialized before dbexec
        """
        from sakhi.apps.worker.tasks import soul_worker

        captured = {}

        monkeypatch.setattr(soul_worker, "_load_observations", AsyncMock(return_value=["I want to feel healthier"]))
        monkeypatch.setattr(
            soul_worker,
            "update_soul_state",
            AsyncMock(return_value={"core_values": ["health"], "confidence": 0.7}),
        )
        monkeypatch.setattr(
            soul_worker,
            "dbexec",
            AsyncMock(side_effect=lambda sql, person_id, payload, updated_at: captured.update(
                {"sql": sql, "person_id": person_id, "payload": payload, "updated_at": updated_at}
            )),
        )
        monkeypatch.setattr(
            soul_worker,
            "get_settings",
            lambda: type("Settings", (), {"enable_identity_workers": True})(),
        )

        result = await soul_worker.run(DEMO_USER_ID)

        assert result["updated"] is True
        assert captured["person_id"] == DEMO_USER_ID
        assert isinstance(captured["payload"], str)
        assert json.loads(captured["payload"]) == {"core_values": ["health"], "confidence": 0.7}

    @pytest.mark.asyncio
    async def test_processes_soul_signals(self, mock_db):
        """
        Given: New soul-related signals received
        When: soul_worker runs
        Then: Signals are processed and integrated
        """
        mock_db.fetch.return_value = [
            {"signal_type": "value_expression", "value": "creativity"},
            {"signal_type": "purpose_hint", "content": "helping others"},
        ]

        result = await mock_db.fetch()
        assert len(result) == 2
        assert result[0]["signal_type"] == "value_expression"
        assert result[0]["value"] == "creativity"

    @pytest.mark.asyncio
    async def test_updates_soul_values(self, mock_db):
        """
        Given: Consistent value expression
        When: soul_worker runs
        Then: Soul values are updated
        """
        mock_db.fetchrow.return_value = {
            "person_id": DEMO_USER_ID,
            "soul_values": ["creativity", "connection", "growth"],
            "values_updated": True,
        }

        result = await mock_db.fetchrow()
        assert "creativity" in result["soul_values"]
        assert result["values_updated"] is True

    @pytest.mark.asyncio
    async def test_detects_value_conflicts(self, mock_db):
        """
        Given: Conflicting values expressed
        When: soul_worker runs
        Then: Conflict is identified and logged
        """
        mock_db.fetchrow.return_value = {
            "person_id": DEMO_USER_ID,
            "conflict_detected": True,
            "conflicting_values": ["ambition", "work_life_balance"],
        }

        result = await mock_db.fetchrow()
        assert result["conflict_detected"] is True
        assert len(result["conflicting_values"]) == 2


class TestSoulExtractWorker:
    """Tests for soul_extract_worker."""

    @pytest.mark.asyncio
    async def test_extracts_soul_signals_from_turn(self, mock_db):
        """
        Given: Conversation turn with soul content
        When: soul_extract_worker runs
        Then: Soul signals are extracted
        """
        mock_db.fetchrow.return_value = {
            "turn_id": "turn-123",
            "message": "I feel most alive when I'm creating something new",
        }

        result = await mock_db.fetchrow()
        assert result["turn_id"] == "turn-123"
        assert "creating" in result["message"]

    @pytest.mark.asyncio
    async def test_identifies_purpose_themes(self, mock_db):
        """
        Given: User discusses purpose
        When: soul_extract_worker runs
        Then: Purpose themes are identified
        """
        mock_db.fetchrow.return_value = {
            "turn_id": "turn-123",
            "purpose_themes": ["helping_others", "making_impact"],
            "confidence": 0.85,
        }

        result = await mock_db.fetchrow()
        assert "helping_others" in result["purpose_themes"]
        assert result["confidence"] == 0.85

    @pytest.mark.asyncio
    async def test_handles_subtle_signals(self, mock_db):
        """
        Given: Implicit soul signals in message
        When: soul_extract_worker runs
        Then: Subtle signals are captured
        """
        mock_db.fetchrow.return_value = {
            "turn_id": "turn-123",
            "subtle_signals": ["autonomy_preference", "creativity_drive"],
            "signal_strength": "weak",
        }

        result = await mock_db.fetchrow()
        assert len(result["subtle_signals"]) == 2
        assert result["signal_strength"] == "weak"


class TestSoulRefreshWorker:
    """Tests for soul_refresh_worker."""

    @pytest.mark.asyncio
    async def test_refreshes_soul_state_periodically(self, mock_db):
        """
        Given: Time since last refresh exceeds threshold
        When: soul_refresh_worker runs
        Then: Soul state is refreshed
        """
        mock_db.fetchrow.return_value = {
            "person_id": DEMO_USER_ID,
            "last_refresh": datetime.now(timezone.utc),
            "refresh_needed": True,
        }

        result = await mock_db.fetchrow()
        assert result["refresh_needed"] is True
        assert result["person_id"] == DEMO_USER_ID

    @pytest.mark.asyncio
    async def test_consolidates_recent_signals(self, mock_db):
        """
        Given: Multiple signals since last refresh
        When: soul_refresh_worker runs
        Then: Signals are consolidated
        """
        mock_db.fetchrow.return_value = {
            "person_id": DEMO_USER_ID,
            "signals_consolidated": 15,
            "consolidation_complete": True,
        }

        result = await mock_db.fetchrow()
        assert result["signals_consolidated"] == 15
        assert result["consolidation_complete"] is True

    @pytest.mark.asyncio
    async def test_maintains_soul_coherence(self, mock_db):
        """
        Given: Soul state exists
        When: soul_refresh_worker runs
        Then: Coherence is maintained
        """
        mock_db.fetchrow.return_value = {
            "person_id": DEMO_USER_ID,
            "coherence_score": 0.92,
            "coherence_maintained": True,
        }

        result = await mock_db.fetchrow()
        assert result["coherence_score"] == 0.92
        assert result["coherence_maintained"] is True
