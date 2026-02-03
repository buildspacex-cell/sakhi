import datetime
import sys
import types

import pytest
from httpx import AsyncClient, ASGITransport

from sakhi.apps.api.main import app
from sakhi.apps.api.deps import auth as auth_deps
from sakhi.apps.engine.evening_closure.engine import generate_evening_closure
from sakhi.apps.worker.tasks.evening_closure_worker import run_evening_closure
dummy_module = types.ModuleType("sakhi.apps.engine.coherence")
dummy_module.compute_coherence = lambda *args, **kwargs: {}
sys.modules["sakhi.apps.engine.coherence"] = dummy_module
from sakhi.apps.worker import scheduler


@pytest.mark.asyncio
async def test_evening_closure_engine_deterministic(monkeypatch):
    async def fake_resolve(pid):
        return pid

    async def fake_q(sql, *args, **kwargs):
        if "session_continuity" in sql:
            return {"continuity_state": {"last_tasks": [{"status": "done"}, {"status": "todo"}], "last_emotion_snapshots": [{"mode": "calm"}]}}
        return {}

    monkeypatch.setattr("sakhi.apps.engine.evening_closure.engine.resolve_person_id", fake_resolve)
    monkeypatch.setattr("sakhi.apps.engine.evening_closure.engine.q", fake_q)

    r1 = await generate_evening_closure("p1")
    r2 = await generate_evening_closure("p1")
    assert r1["summary"] == r2["summary"]
    assert r1["pending"] and r1["completed"]


@pytest.mark.asyncio
async def test_evening_closure_worker_upsert(monkeypatch):
    calls = []

    async def fake_resolve(pid):
        return pid

    async def fake_q(*args, **kwargs):
        return {"continuity_state": {}}

    async def fake_exec(sql, *args, **kwargs):
        calls.append((sql, args))

    monkeypatch.setattr("sakhi.apps.engine.evening_closure.engine.resolve_person_id", fake_resolve)
    monkeypatch.setattr("sakhi.apps.engine.evening_closure.engine.q", fake_q)
    monkeypatch.setattr("sakhi.apps.engine.evening_closure.engine.dbexec", fake_exec)

    await run_evening_closure("p1")
    assert calls
    # update personal_model happens in second exec call
    assert any("personal_model" in c[0] for c in calls)


def test_evening_closure_scheduler(monkeypatch):
    enqueued = []

    monkeypatch.setattr("sakhi.apps.worker.scheduler._should_run_hour", lambda target: True)
    monkeypatch.setattr(
        "sakhi.apps.worker.scheduler._enqueue",
        lambda queue, func, *args, **kwargs: enqueued.append(func.__name__),
    )
    monkeypatch.setattr("sakhi.apps.worker.scheduler.DEFAULT_USER_ID", "user")
    scheduler.schedule_evening_closure()
    assert "run_evening_closure" in enqueued


@pytest.mark.asyncio
async def test_evening_closure_route(monkeypatch):
    async def fake_q(sql, *args, **kwargs):
        return [
            {
                "closure_date": datetime.date.today(),
                "completed": ["a"],
                "pending": [],
                "signals": {"energy": "steady"},
                "summary": "ok",
                "generated_at": "now",
            }
        ]

    async def fake_resolve(pid):
        return pid

    monkeypatch.setattr("sakhi.apps.api.routes.evening_closure.q", fake_q)
    monkeypatch.setattr("sakhi.apps.api.routes.evening_closure.resolve_person_id", fake_resolve)
    app.dependency_overrides[auth_deps.get_current_user_id] = lambda: "user"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/v1/evening_closure", params={"person_id": "p1"})
    assert resp.status_code == 200
    assert resp.json()["summary"] == "ok"


@pytest.mark.asyncio
async def test_evening_closure_in_turn(monkeypatch):
    # force time >= 20
    class FakeDateTime(datetime.datetime):
        @classmethod
        def utcnow(cls):
            return datetime.datetime(2025, 1, 1, 21, 0, 0)

        @classmethod
        def today(cls):
            return datetime.date(2025, 1, 1)

    fake_datetime_module = types.SimpleNamespace(datetime=FakeDateTime, date=datetime.date)

    async def fake_q(sql, *args, **kwargs):
        if "daily_closure_cache" in sql:
            return [
                {
                    "completed": ["x"],
                    "pending": ["y"],
                    "signals": {},
                    "summary": "done",
                    "closure_date": datetime.date(2025, 1, 1),
                    "generated_at": "now",
                }
            ]
        if "daily_reflection_cache" in sql:
            return []
        return []

    async def fake_resolve(pid):
        return "00000000-0000-0000-0000-000000000050"

    async def fake_orchestrate(**kwargs):
        return {"entry_id": "e1", "topics": [], "emotion": {}, "intents": [], "plans": [], "triage": {}, "rhythm_triggers": None, "meta_reflection_triggers": None}

    async def fake_run_unified(*args, **kwargs):
        return {"behavior_profile": {}, "planner": None, "insight": None, "activation": {}, "triage": {}, "emotion": {}, "pattern_sense": {}, "forecast_state": {}, "brain": {"emotion_state": {}, "soul_state": {}, "rhythm_state": {}}}

    async def fake_reply(*args, **kwargs):
        return {"reply": "ok", "tone_blueprint": {"style": "auto"}, "journaling_ai": None}

    async def fake_load_continuity(*args, **kwargs):
        return {}

    async def fake_update_continuity(*args, **kwargs):
        return {}

    async def fake_memory_recall(**kwargs):
        return {}

    monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.datetime", fake_datetime_module)
    monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.q", fake_q)
    monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.resolve_person_id", fake_resolve)
    monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.orchestrate_turn", fake_orchestrate)
    monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.run_unified_turn", fake_run_unified)
    monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.compute_microreg", lambda *args, **kwargs: {})
    monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.compute_empathy", lambda *args, **kwargs: {})
    monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.compute_tone", lambda *args, **kwargs: {})
    monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.compute_alignment", lambda *args, **kwargs: {})
    monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.compute_fast_rhythm_soul_frame", lambda *args, **kwargs: {})
    monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.compute_fast_esr_frame", lambda *args, **kwargs: {})
    monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.compute_fast_identity_momentum", lambda *args, **kwargs: {})
    monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.compute_fast_identity_timeline_frame", lambda *args, **kwargs: {})
    monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.compute_fast_narrative", lambda *args, **kwargs: {})
    monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.personal_brain", type("pb", (), {"get_brain_state": lambda *args, **kwargs: {}}), raising=False)
    monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.compute_behavior_profile", lambda *args, **kwargs: {}, raising=False)
    monkeypatch.setattr("sakhi.apps.engine.continuity.engine.load_continuity", fake_load_continuity)
    monkeypatch.setattr("sakhi.apps.engine.continuity.engine.update_continuity", fake_update_continuity)
    monkeypatch.setattr("sakhi.apps.api.services.memory.recall.memory_recall", fake_memory_recall)
    monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.generate_reply", fake_reply)

    app.dependency_overrides[auth_deps.get_current_user_id] = lambda: "user"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/v2/turn", json={"text": "hello"})
    assert resp.status_code == 200
    data = resp.json()
    assert "evening_closure" in data
