from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from sakhi.apps.api.services.turn import deterministic_context_loader as dcl


def _mock_brain_states() -> dict:
    return {
        "forecast_state": {},
        "coherence_state": {},
        "alignment_state": {},
        "nudge_state": {},
        "long_term": {},
    }


@pytest.mark.asyncio
async def test_load_deterministic_context_skips_rhythm_planner_alignment_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(dcl, "ENABLE_RHYTHM_PLANNER_ALIGNMENT", False)
    monkeypatch.setattr(dcl, "_load_personal_model_row", AsyncMock(return_value={}))
    monkeypatch.setattr(dcl, "load_internal_state", AsyncMock(return_value={}))
    monkeypatch.setattr(dcl, "load_brain_states", AsyncMock(return_value=_mock_brain_states()))
    monkeypatch.setattr(
        dcl,
        "load_friction_state",
        AsyncMock(
            return_value={
                "friction_state": "balanced",
                "drift_percentage": 0.0,
                "energy_mode": "sattva",
                "friction_info": {},
                "drift_direction": None,
                "primary_contributor": None,
            }
        ),
    )
    monkeypatch.setattr(dcl, "load_continuity_state", AsyncMock(return_value={}))
    monkeypatch.setattr(dcl, "calculate_gap_hours", AsyncMock(return_value=None))
    load_alignment = AsyncMock(return_value={"recommendations": {"peaks": []}})
    monkeypatch.setattr(dcl, "load_rhythm_planner_alignment", load_alignment)

    ctx = await dcl.load_deterministic_context("00000000-0000-0000-0000-000000000001", user_text="hello")

    assert ctx.rhythm_planner_alignment is None
    load_alignment.assert_not_awaited()


@pytest.mark.asyncio
async def test_load_deterministic_context_loads_rhythm_planner_alignment_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(dcl, "ENABLE_RHYTHM_PLANNER_ALIGNMENT", True)
    monkeypatch.setattr(dcl, "_load_personal_model_row", AsyncMock(return_value={}))
    monkeypatch.setattr(dcl, "load_internal_state", AsyncMock(return_value={}))
    monkeypatch.setattr(dcl, "load_brain_states", AsyncMock(return_value=_mock_brain_states()))
    monkeypatch.setattr(
        dcl,
        "load_friction_state",
        AsyncMock(
            return_value={
                "friction_state": "balanced",
                "drift_percentage": 0.0,
                "energy_mode": "sattva",
                "friction_info": {},
                "drift_direction": None,
                "primary_contributor": None,
            }
        ),
    )
    monkeypatch.setattr(dcl, "load_continuity_state", AsyncMock(return_value={}))
    monkeypatch.setattr(dcl, "calculate_gap_hours", AsyncMock(return_value=None))
    load_alignment = AsyncMock(return_value={"recommendations": {"peaks": [{"window": "10:00-11:00"}]}})
    monkeypatch.setattr(dcl, "load_rhythm_planner_alignment", load_alignment)

    ctx = await dcl.load_deterministic_context("00000000-0000-0000-0000-000000000001", user_text="hello")

    assert ctx.rhythm_planner_alignment == {"recommendations": {"peaks": [{"window": "10:00-11:00"}]}}
    load_alignment.assert_awaited_once()
