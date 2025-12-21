import datetime
import sys
import types

import pytest

from sakhi.apps.engine.mini_flow.adjuster import determine_rhythm_slot, adjust_mini_flow
from sakhi.apps.engine.mini_flow.engine import generate_mini_flow
from sakhi.apps.worker.tasks.mini_flow_worker import run_mini_flow

# Patch missing coherence import for scheduler at import time
dummy_coherence = types.ModuleType("sakhi.apps.engine.coherence")
dummy_coherence.compute_coherence = lambda *args, **kwargs: {}
sys.modules["sakhi.apps.engine.coherence"] = dummy_coherence


def test_determine_rhythm_slot():
    assert determine_rhythm_slot(datetime.datetime(2025, 1, 1, 5, 0)) == "morning"
    assert determine_rhythm_slot(datetime.datetime(2025, 1, 1, 12, 0)) == "midday"
    assert determine_rhythm_slot(datetime.datetime(2025, 1, 1, 16, 0)) == "afternoon"
    assert determine_rhythm_slot(datetime.datetime(2025, 1, 1, 20, 0)) == "evening"
    assert determine_rhythm_slot(datetime.datetime(2025, 1, 1, 2, 0)) == "night"


def test_adjuster_rules():
    base = {
        "warmup_step": "wu",
        "focus_block_step": "fb",
        "closure_step": "cl",
        "optional_reward": "or",
        "source": "focus_path",
        "date": datetime.date.today().isoformat(),
        "generated_at": datetime.datetime.utcnow().isoformat(),
    }
    morning = adjust_mini_flow(base, "morning")
    assert "Quick" in morning["warmup_step"]
    assert "~10 minutes" in morning["focus_block_step"]
    evening = adjust_mini_flow(base, "evening")
    assert "~5 minutes" in evening["focus_block_step"]
    night = adjust_mini_flow(base, "night")
    assert "<2-minute" in night["focus_block_step"]
    assert night["optional_reward"] == ""


@pytest.mark.asyncio
async def test_engine_includes_rhythm_slot(monkeypatch):
    async def fake_resolve(pid):
        return pid

    async def fake_q(sql, *args, **kwargs):
        return {}

    monkeypatch.setattr("sakhi.apps.engine.mini_flow.engine.resolve_person_id", fake_resolve)
    monkeypatch.setattr("sakhi.apps.engine.mini_flow.engine.q", fake_q)
    monkeypatch.setattr("sakhi.apps.engine.mini_flow.engine.datetime", types.SimpleNamespace(datetime=datetime.datetime, date=datetime.date, timezone=datetime.timezone))
    flow = await generate_mini_flow("p1")
    assert flow.get("rhythm_slot")


@pytest.mark.asyncio
async def test_worker_persists_rhythm_slot(monkeypatch):
    calls = []

    async def fake_resolve(pid):
        return pid

    async def fake_q(*args, **kwargs):
        return {}

    async def fake_exec(*args, **kwargs):
        calls.append(args[0])

    monkeypatch.setattr("sakhi.apps.engine.mini_flow.engine.resolve_person_id", fake_resolve)
    monkeypatch.setattr("sakhi.apps.engine.mini_flow.engine.q", fake_q)
    monkeypatch.setattr("sakhi.apps.engine.mini_flow.engine.dbexec", fake_exec)

    await run_mini_flow("p1")
    assert any("mini_flow_cache" in c for c in calls)

