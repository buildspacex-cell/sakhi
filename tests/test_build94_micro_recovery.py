import datetime
import sys
import types

import pytest
from httpx import AsyncClient, ASGITransport

from sakhi.apps.api.main import app
from sakhi.apps.api.deps import auth as auth_deps
from sakhi.apps.engine.micro_recovery.engine import generate_micro_recovery
from sakhi.apps.worker.tasks.micro_recovery_worker import run_micro_recovery

# Patch missing coherence import for scheduler at import time
dummy_coherence = types.ModuleType("sakhi.apps.engine.coherence")
dummy_coherence.compute_coherence = lambda *args, **kwargs: {}
sys.modules["sakhi.apps.engine.coherence"] = dummy_coherence
from sakhi.apps.worker import scheduler  # noqa: E402


@pytest.mark.asyncio
async def test_micro_recovery_engine(monkeypatch):
    async def fake_resolve(pid):
        return pid

    async def fake_q(sql, *args, **kwargs):
        if "daily_closure_cache" in sql:
            return {"pending": ["x"]}
        if "tasks" in sql:
            return {"open_count": 5, "active_count": 0}
        if "conversation_turns" in sql:
            return {"created_at": datetime.datetime.utcnow() - datetime.timedelta(hours=4)}
        return {}

    monkeypatch.setattr("sakhi.apps.engine.micro_recovery.engine.resolve_person_id", fake_resolve)
    monkeypatch.setattr("sakhi.apps.engine.micro_recovery.engine.q", fake_q)

    res = await generate_micro_recovery("p1")
    assert res["nudge"]
    assert res["reason"]


@pytest.mark.asyncio
async def test_micro_recovery_deterministic(monkeypatch):
    async def fake_resolve(pid):
        return pid

    async def fake_q(sql, *args, **kwargs):
        return {}

    monkeypatch.setattr("sakhi.apps.engine.micro_recovery.engine.resolve_person_id", fake_resolve)
    monkeypatch.setattr("sakhi.apps.engine.micro_recovery.engine.q", fake_q)

    a1 = await generate_micro_recovery("p1")
    a2 = await generate_micro_recovery("p1")
    assert a1["nudge"] == a2["nudge"]
    assert a1["reason"] == a2["reason"]


@pytest.mark.asyncio
async def test_micro_recovery_worker(monkeypatch):
    calls = []

    async def fake_resolve(pid):
        return pid

    async def fake_q(*args, **kwargs):
        return {}

    async def fake_exec(*args, **kwargs):
        calls.append(args[0])

    monkeypatch.setattr("sakhi.apps.engine.micro_recovery.engine.resolve_person_id", fake_resolve)
    monkeypatch.setattr("sakhi.apps.engine.micro_recovery.engine.q", fake_q)
    monkeypatch.setattr("sakhi.apps.engine.micro_recovery.engine.dbexec", fake_exec)

    await run_micro_recovery("p1")
    assert any("micro_recovery_cache" in c for c in calls)
    assert any("personal_model" in c for c in calls)


def test_micro_recovery_scheduler(monkeypatch):
    enqueued = []
    monkeypatch.setattr("sakhi.apps.worker.scheduler.DEFAULT_USER_ID", "user")
    monkeypatch.setattr("sakhi.apps.worker.scheduler._should_run_hour", lambda target: True)
    monkeypatch.setattr("sakhi.apps.worker.scheduler._should_run_minute", lambda target: True)
    monkeypatch.setattr(
        "sakhi.apps.worker.scheduler._enqueue",
        lambda queue, func, *args, **kwargs: enqueued.append(func.__name__),
    )
    scheduler.schedule_micro_recovery()
    assert "run_micro_recovery" in enqueued


@pytest.mark.asyncio
async def test_micro_recovery_route(monkeypatch):
    async def fake_q(sql, *args, **kwargs):
        return [
            {
                "recovery_date": datetime.date.today(),
                "nudge": "n1",
                "reason": "r",
                "generated_at": "now",
            }
        ]

    async def fake_resolve(pid):
        return pid

    monkeypatch.setattr("sakhi.apps.api.routes.micro_recovery.q", fake_q)
    monkeypatch.setattr("sakhi.apps.api.routes.micro_recovery.resolve_person_id", fake_resolve)
    app.dependency_overrides[auth_deps.get_current_user_id] = lambda: "user"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/v1/micro_recovery", params={"person_id": "p1"})
    assert resp.status_code == 200
    assert resp.json()["nudge"] == "n1"


@pytest.mark.asyncio
async def test_micro_recovery_in_turn(monkeypatch):
    class FakeDateTime(datetime.datetime):
        @classmethod
        def utcnow(cls):
            return datetime.datetime(2025, 1, 1, 15, 0, 0)

        @classmethod
        def today(cls):
            return datetime.date(2025, 1, 1)

    fake_datetime_module = types.SimpleNamespace(datetime=FakeDateTime, date=datetime.date)

    async def fake_q(sql, *args, **kwargs):
        if "micro_recovery_cache" in sql:
            return [
                {
                    "recovery_date": datetime.date(2025, 1, 1),
                    "nudge": "n1",
                    "reason": "r",
                    "generated_at": "now",
                }
            ]
        if "conversation_turns" in sql:
            return [{"created_at": datetime.datetime(2025, 1, 1, 10, 0, 0)}]
        return []

    async def fake_resolve(pid):
        return "00000000-0000-0000-0000-000000000050"

    async def fake_orchestrate(**kwargs):
        return {
            "entry_id": "e1",
            "topics": [],
            "emotion": {},
            "intents": [],
            "plans": [],
            "triage": {},
            "rhythm_triggers": None,
            "meta_reflection_triggers": None,
        }

    async def fake_run_unified(*args, **kwargs):
        return {
            "behavior_profile": {},
            "planner": None,
            "insight": None,
            "activation": {},
            "triage": {},
            "emotion": {},
            "pattern_sense": {},
            "forecast_state": {},
            "brain": {"emotion_state": {}, "soul_state": {}, "rhythm_state": {}},
        }

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
        resp = await ac.post("/v2/turn", json={"text": "hello, let's restart"})
    assert resp.status_code == 200
    data = resp.json()
    assert "micro_recovery" in data
