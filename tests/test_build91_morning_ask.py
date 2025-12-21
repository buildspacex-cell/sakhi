import datetime
import sys
import types

import pytest
from httpx import AsyncClient, ASGITransport

from sakhi.apps.api.main import app
from sakhi.apps.api.deps import auth as auth_deps
from sakhi.apps.engine.morning_ask.engine import generate_morning_ask
from sakhi.apps.worker.tasks.morning_ask_worker import run_morning_ask

# Patch missing coherence import for scheduler at import time
dummy_coherence = types.ModuleType("sakhi.apps.engine.coherence")
dummy_coherence.compute_coherence = lambda *args, **kwargs: {}
sys.modules["sakhi.apps.engine.coherence"] = dummy_coherence
from sakhi.apps.worker import scheduler


@pytest.mark.asyncio
async def test_morning_ask_engine_templates(monkeypatch):
    async def fake_resolve(pid):
        return pid

    async def fake_q(sql, *args, **kwargs):
        if "morning_preview_cache" in sql:
            return {"focus_areas": ["a", "b"], "key_tasks": ["task1"], "reminders": []}
        if "daily_closure_cache" in sql:
            return {"pending": ["p1", "p2"]}
        if "tasks" in sql:
            return {"labels": ["x"]}
        return {}

    monkeypatch.setattr("sakhi.apps.engine.morning_ask.engine.resolve_person_id", fake_resolve)
    monkeypatch.setattr("sakhi.apps.engine.morning_ask.engine.q", fake_q)

    ask = await generate_morning_ask("u1")
    assert ask["question"]
    assert ask["reason"] in {"pending_items", "multi_focus", "key_tasks", "open_tasks", "default"}


@pytest.mark.asyncio
async def test_morning_ask_engine_deterministic(monkeypatch):
    async def fake_resolve(pid):
        return pid

    async def fake_q(sql, *args, **kwargs):
        return {}

    monkeypatch.setattr("sakhi.apps.engine.morning_ask.engine.resolve_person_id", fake_resolve)
    monkeypatch.setattr("sakhi.apps.engine.morning_ask.engine.q", fake_q)

    a1 = await generate_morning_ask("u1")
    a2 = await generate_morning_ask("u1")
    assert a1["question"] == a2["question"]


@pytest.mark.asyncio
async def test_morning_ask_worker(monkeypatch):
    calls = []

    async def fake_resolve(pid):
        return pid

    async def fake_q(*args, **kwargs):
        return {}

    async def fake_exec(*args, **kwargs):
        calls.append(args[0])

    monkeypatch.setattr("sakhi.apps.engine.morning_ask.engine.resolve_person_id", fake_resolve)
    monkeypatch.setattr("sakhi.apps.engine.morning_ask.engine.q", fake_q)
    monkeypatch.setattr("sakhi.apps.engine.morning_ask.engine.dbexec", fake_exec)

    await run_morning_ask("u1")
    assert any("morning_ask_cache" in c for c in calls)
    assert any("personal_model" in c for c in calls)


def test_morning_ask_scheduler(monkeypatch):
    enqueued = []
    monkeypatch.setattr("sakhi.apps.worker.scheduler.DEFAULT_USER_ID", "user")
    monkeypatch.setattr("sakhi.apps.worker.scheduler._should_run_hour", lambda target: True)
    monkeypatch.setattr("sakhi.apps.worker.scheduler._should_run_minute", lambda target: True)
    monkeypatch.setattr("sakhi.apps.worker.scheduler._enqueue", lambda queue, func, *args, **kwargs: enqueued.append(func.__name__))
    scheduler.schedule_morning_ask()
    assert "run_morning_ask" in enqueued


@pytest.mark.asyncio
async def test_morning_ask_route(monkeypatch):
    async def fake_q(sql, *args, **kwargs):
        return [
            {"ask_date": datetime.date.today(), "question": "q", "reason": "r", "generated_at": "now"}
        ]

    async def fake_resolve(pid):
        return pid

    monkeypatch.setattr("sakhi.apps.api.routes.morning_ask.q", fake_q)
    monkeypatch.setattr("sakhi.apps.api.routes.morning_ask.resolve_person_id", fake_resolve)
    app.dependency_overrides[auth_deps.get_current_user_id] = lambda: "user"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/v1/morning_ask", params={"person_id": "p1"})
    assert resp.status_code == 200
    assert resp.json()["question"] == "q"


@pytest.mark.asyncio
async def test_morning_ask_in_turn(monkeypatch):
    class FakeDateTime(datetime.datetime):
        @classmethod
        def utcnow(cls):
            return datetime.datetime(2025, 1, 1, 9, 0, 0)

        @classmethod
        def today(cls):
            return datetime.date(2025, 1, 1)

    fake_datetime_module = types.SimpleNamespace(datetime=FakeDateTime, date=datetime.date)

    async def fake_q(sql, *args, **kwargs):
        if "morning_ask_cache" in sql:
            return [
                {
                    "ask_date": datetime.date(2025, 1, 1),
                    "question": "q",
                    "reason": "r",
                    "generated_at": "now",
                }
            ]
        if "morning_preview_cache" in sql:
            return []
        if "daily_reflection_cache" in sql or "daily_closure_cache" in sql:
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
    assert "morning_ask" in data
