import asyncio
import os

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from sakhi.core.rhythm.rhythm_soul_engine import compute_fast_rhythm_soul_frame, compute_deep_rhythm_soul
from sakhi.apps.worker import rhythm_soul_deep
from sakhi.apps.api.routes import rhythm_soul as rhythm_soul_route
from sakhi.apps.worker import scheduler as worker_scheduler


def test_fast_rhythm_soul_frame_fields():
    out = compute_fast_rhythm_soul_frame(
        [],
        {"body_energy": 0.8, "mind_focus": 0.7},
        {"core_values": ["growth"], "shadow": ["doubt"], "light": ["optimism"], "conflicts": []},
    )
    assert 0 <= out["coherence_score"] <= 1
    assert "identity_momentum" in out
    assert "shadow_disruption" in out
    assert out["rhythm_tone_adjustment"] in {"soft", "steady", "energized"}


@pytest.mark.asyncio
async def test_deep_rhythm_soul_writes(monkeypatch):
    captured = {}

    async def fake_llm(messages=None, **kwargs):
        return {"weekly_coherence_summary": "ok", "recommended_pacing_style": "steady"}

    async def fake_dbexec(sql, *args, **kwargs):
        captured["sql"] = sql
        captured["args"] = args

    monkeypatch.setattr("sakhi.core.rhythm.rhythm_soul_engine.call_llm", fake_llm, raising=False)
    monkeypatch.setattr("sakhi.apps.api.core.llm.call_llm", fake_llm, raising=False)
    async def fake_q(*a, **k):
        return []

    monkeypatch.setattr("sakhi.apps.worker.rhythm_soul_deep.dbexec", fake_dbexec)
    monkeypatch.setattr("sakhi.apps.worker.rhythm_soul_deep.q", fake_q)

    result = await compute_deep_rhythm_soul("pid", [], {}, {})
    assert "weekly_coherence_summary" in result
    # simulate worker
    await rhythm_soul_deep.run_rhythm_soul_deep("pid")
    assert "sql" in captured


def test_rhythm_soul_api(monkeypatch):
    app = FastAPI()

    async def fake_q(query, person_id, one=False):
        return {"rhythm_state": {"body_energy": 0.5}, "soul_state": {"core_values": ["care"]}, "rhythm_soul_state": {"deep": True}}

    monkeypatch.setattr("sakhi.apps.api.routes.rhythm_soul.q", fake_q)
    app.include_router(rhythm_soul_route.router)
    client = TestClient(app)
    resp = client.get("/rhythm_soul/demo")
    assert resp.status_code == 200
    data = resp.json()
    assert "fast" in data and "deep" in data


def test_scheduler_rhythm_soul(monkeypatch):
    calls = []

    def fake_enqueue(queue, func, *args, **kwargs):
        calls.append((queue.name, func.__name__, args))

    monkeypatch.setattr(worker_scheduler, "_enqueue", fake_enqueue)
    # force run: set env to always for hour check
    monkeypatch.setattr(worker_scheduler, "RHYTHM_SOUL_DAILY_HOUR", worker_scheduler._RUN_ALWAYS)
    worker_scheduler.schedule_rhythm_soul_daily()
    assert any(func == "run_rhythm_soul_deep" for _, func, _ in calls)
