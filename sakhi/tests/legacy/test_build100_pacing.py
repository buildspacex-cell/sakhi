import datetime
import types

import pytest

from sakhi.apps.engine.micro_journey.pacing import (
    estimate_step_duration,
    estimate_flow_duration,
    apply_pacing,
)
from sakhi.apps.engine.micro_journey.engine import generate_micro_journey


def test_estimate_step_duration_keywords():
    assert estimate_step_duration({"text": "clean the desk"}) == 2
    assert estimate_step_duration({"text": "organize notes"}) == 5
    assert estimate_step_duration({"text": "plan the day"}) == 10
    assert estimate_step_duration({"text": "deep work session"}) == 15
    assert estimate_step_duration({"text": "unknown"}) == 5


def test_estimate_flow_duration():
    flow = {
        "steps": [
            {"text": "clean"},
            {"text": "plan"},
        ]
    }
    duration = estimate_flow_duration(flow)
    assert duration == (2 + 10 + 1)
    assert all("estimated_minutes" in step for step in flow["steps"])


def test_apply_pacing_sets_structure():
    journey = {
        "flows": [
            {"warmup_step": "clean", "focus_block_step": "plan", "closure_step": "wrap", "optional_reward": ""},
            {"warmup_step": "organize", "focus_block_step": "review", "closure_step": "close", "optional_reward": ""},
        ],
        "structure": {},
    }
    paced = apply_pacing(journey)
    assert paced["structure"]["total_estimated_minutes"] > 0
    assert "pacing" in paced["structure"]


@pytest.mark.asyncio
async def test_micro_journey_has_pacing(monkeypatch):
    async def fake_flow(pid):
        return {
            "warmup_step": "clean",
            "focus_block_step": "plan",
            "closure_step": "wrap",
            "optional_reward": "",
        }

    fake_dt = types.SimpleNamespace(datetime=datetime.datetime, date=datetime.date)
    monkeypatch.setattr("sakhi.apps.engine.micro_journey.engine.generate_mini_flow", fake_flow)
    monkeypatch.setattr("sakhi.apps.engine.micro_journey.engine.datetime", fake_dt)
    journey = await generate_micro_journey("p1")
    structure = journey.get("structure") or {}
    assert structure.get("total_estimated_minutes") is not None
    assert "pacing" in structure
