import datetime
import types

import pytest

from sakhi.apps.engine.micro_journey.sequencer import (
    compute_flow_effort,
    reorder_flows,
    apply_adaptive_sequencing,
)
from sakhi.apps.engine.micro_journey.engine import generate_micro_journey


def _flow(text: str) -> dict:
    return {"warmup_step": text, "focus_block_step": text, "closure_step": text, "optional_reward": ""}


def test_compute_flow_effort():
    assert compute_flow_effort(_flow("clean desk")) == 1
    assert compute_flow_effort(_flow("organize notes")) == 2
    assert compute_flow_effort(_flow("plan the day")) == 3
    assert compute_flow_effort(_flow("deep work block")) == 4


def test_reorder_flows_basic():
    flows = [_flow("plan work"), _flow("clean desk"), _flow("deep work block")]
    reordered = reorder_flows(flows, "midday")
    efforts = [compute_flow_effort(f) for f in reordered]
    assert efforts == sorted(efforts)


def test_reorder_flows_rhythm_overrides():
    flows = [_flow("deep work block"), _flow("clean desk"), _flow("plan report")]
    evening_order = reorder_flows(flows, "evening")
    assert compute_flow_effort(evening_order[-1]) >= 3
    morning_order = reorder_flows(flows, "morning")
    assert compute_flow_effort(morning_order[0]) >= 3  # planning bubbled up


def test_apply_adaptive_sequencing():
    journey = {
        "flows": [_flow("clean"), _flow("plan day")],
        "rhythm_slot": "morning",
        "structure": {},
    }
    updated = apply_adaptive_sequencing(journey)
    assert updated["structure"].get("reordered") is True
    assert "rules_used" in updated["structure"]


@pytest.mark.asyncio
async def test_generate_micro_journey_applies_sequencer(monkeypatch):
    async def fake_flow(pid):
        return _flow("plan day")

    fake_dt = types.SimpleNamespace(datetime=datetime.datetime, date=datetime.date)
    monkeypatch.setattr("sakhi.apps.engine.micro_journey.engine.generate_mini_flow", fake_flow)
    monkeypatch.setattr("sakhi.apps.engine.micro_journey.engine.datetime", fake_dt)
    journey = await generate_micro_journey("p1")
    assert journey["structure"].get("reordered") is True
