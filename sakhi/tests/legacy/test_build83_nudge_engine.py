import datetime as dt
import os

# ensure auth dependency has required envs for import
os.environ.setdefault("SUPABASE_URL", "http://localhost")
os.environ.setdefault("SUPABASE_ANON_KEY", "dummy")

import pytest

from sakhi.apps.engine.nudge import engine as nudge_engine
from sakhi.apps.worker.tasks import nudge_worker
from sakhi.apps.api.routes import nudge as nudge_route


@pytest.mark.asyncio
async def test_compute_nudge_energy(monkeypatch):
    async def fake_q(sql, *args, **kwargs):
        return {"nudge_state": {}}

    async def fake_resolve(pid):
        return pid

    monkeypatch.setattr(nudge_engine, "q", fake_q)
    monkeypatch.setattr(nudge_engine, "resolve_person_id", fake_resolve)
    forecast_state = {"emotion_forecast": {"fatigue": 0.7}}
    tone_state = {"final": "warm + soft"}
    nudge = await nudge_engine.compute_nudge("person", forecast_state, tone_state)
    assert nudge["should_send"] is True
    assert nudge["category"] == "energy"
    assert "stretch" in nudge["message"]


@pytest.mark.asyncio
async def test_compute_nudge_cooldown(monkeypatch):
    last_ts = dt.datetime.utcnow().isoformat()

    async def fake_q(sql, *args, **kwargs):
        return {"nudge_state": {"last_sent_at": last_ts}}

    async def fake_resolve(pid):
        return pid

    monkeypatch.setattr(nudge_engine, "q", fake_q)
    monkeypatch.setattr(nudge_engine, "resolve_person_id", fake_resolve)
    nudge = await nudge_engine.compute_nudge("person", {"emotion_forecast": {"fatigue": 0.9}}, {"final": "warm"})
    assert nudge["should_send"] is False


@pytest.mark.asyncio
async def test_worker_persists(monkeypatch):
    calls = {"insert": 0, "update": 0}

    async def fake_q(sql, *args, **kwargs):
        if "forecast_cache" in sql:
            return {"forecast_state": {"emotion_forecast": {"irritability": 0.7}}}
        return {"tone_state": {"final": "warm"}, "nudge_state": {}}

    async def fake_dbexec(sql, *args, **kwargs):
        if "INSERT INTO nudge_log" in sql:
            calls["insert"] += 1
        if "UPDATE personal_model" in sql:
            calls["update"] += 1

    async def fake_compute(person_id, forecast_state, tone_state):
        return {"should_send": True, "category": "calming", "message": "msg", "forecast_snapshot": {}}

    async def fake_resolve(pid):
        return pid

    monkeypatch.setattr(nudge_worker, "q", fake_q)
    monkeypatch.setattr(nudge_worker, "dbexec", fake_dbexec)
    monkeypatch.setattr(nudge_worker, "resolve_person_id", fake_resolve)
    monkeypatch.setattr(nudge_worker, "compute_nudge", fake_compute)
    result = await nudge_worker.run_nudge_check("p1")
    assert result["should_send"] is True
    assert calls["insert"] >= 1
    assert calls["update"] == 1


@pytest.mark.asyncio
async def test_nudge_route(monkeypatch):
    async def fake_q(sql, *args, **kwargs):
        return [{"category": "energy", "message": "hi", "forecast_snapshot": {}, "sent_at": "now"}]

    async def fake_resolve(pid):
        return pid

    monkeypatch.setattr(nudge_route, "q", fake_q)
    monkeypatch.setattr(nudge_route, "resolve_person_id", fake_resolve)
    resp = await nudge_route.list_nudges(person_id="user", user_id="user")
    assert resp["items"][0]["category"] == "energy"
