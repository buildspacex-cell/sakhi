import datetime
import sys
import types

import pytest
from httpx import AsyncClient, ASGITransport

from sakhi.apps.api.main import app
from sakhi.apps.api.deps import auth as auth_deps
from sakhi.apps.engine.focus_path.engine import generate_focus_path
from sakhi.apps.worker.tasks.focus_path_worker import run_focus_path

# Patch missing coherence import for scheduler at import time
dummy_coherence = types.ModuleType("sakhi.apps.engine.coherence")
dummy_coherence.compute_coherence = lambda *args, **kwargs: {}
sys.modules["sakhi.apps.engine.coherence"] = dummy_coherence
from sakhi.apps.worker import scheduler  # noqa: E402


@pytest.mark.asyncio
async def test_focus_path_engine(monkeypatch):
    async def fake_resolve(pid):
        return pid

    async def fake_q(sql, *args, **kwargs):
        if "morning_preview_cache" in sql:
            return {"key_tasks": ["k1"], "reminders": []}
        if "daily_closure_cache" in sql:
            return {"pending": []}
        if "tasks" in sql:
            return {"labels": ["t1", "t2"]}
        return {}

    monkeypatch.setattr("sakhi.apps.engine.focus_path.engine.resolve_person_id", fake_resolve)
    monkeypatch.setattr("sakhi.apps.engine.focus_path.engine.q", fake_q)

    res = await generate_focus_path("p1")
    assert res["anchor_step"]
    assert res["intent_source"]


@pytest.mark.asyncio
async def test_focus_path_deterministic(monkeypatch):
    async def fake_resolve(pid):
        return pid

    async def fake_q(sql, *args, **kwargs):
        return {}

    monkeypatch.setattr("sakhi.apps.engine.focus_path.engine.resolve_person_id", fake_resolve)
    monkeypatch.setattr("sakhi.apps.engine.focus_path.engine.q", fake_q)

    a1 = await generate_focus_path("p1")
    a2 = await generate_focus_path("p1")
    assert a1["anchor_step"] == a2["anchor_step"]
    assert a1["progress_step"] == a2["progress_step"]


@pytest.mark.asyncio
async def test_focus_path_worker(monkeypatch):
    calls = []

    async def fake_resolve(pid):
        return pid

    async def fake_q(*args, **kwargs):
        return {}

    async def fake_exec(*args, **kwargs):
        calls.append(args[0])

    monkeypatch.setattr("sakhi.apps.engine.focus_path.engine.resolve_person_id", fake_resolve)
    monkeypatch.setattr("sakhi.apps.engine.focus_path.engine.q", fake_q)
    monkeypatch.setattr("sakhi.apps.engine.focus_path.engine.dbexec", fake_exec)

    await run_focus_path("p1")
    assert any("focus_path_cache" in c for c in calls)
    assert any("personal_model" in c for c in calls)


def test_focus_path_scheduler(monkeypatch):
    enqueued = []
    monkeypatch.setattr("sakhi.apps.worker.scheduler.DEFAULT_USER_ID", "user")
    monkeypatch.setattr("sakhi.apps.worker.scheduler._should_run_hour", lambda target: True)
    monkeypatch.setattr("sakhi.apps.worker.scheduler._should_run_minute", lambda target: True)
    monkeypatch.setattr(
        "sakhi.apps.worker.scheduler._enqueue",
        lambda queue, func, *args, **kwargs: enqueued.append(func.__name__),
    )
    scheduler.schedule_focus_path()
    assert "run_focus_path" in enqueued


@pytest.mark.asyncio
async def test_focus_path_route(monkeypatch):
    async def fake_resolve(pid):
        return pid

    async def fake_generate(pid, intent_text=None):
        return {
            "date": datetime.date.today().isoformat(),
            "anchor_step": "a",
            "progress_step": "b",
            "closure_step": "c",
            "intent_source": "default",
            "generated_at": datetime.datetime.utcnow().isoformat(),
        }

    async def fake_persist(pid, path):
        return None

    monkeypatch.setattr("sakhi.apps.api.routes.focus_path.resolve_person_id", fake_resolve)
    monkeypatch.setattr("sakhi.apps.api.routes.focus_path.generate_focus_path", fake_generate)
    monkeypatch.setattr("sakhi.apps.api.routes.focus_path.persist_focus_path", fake_persist)
    app.dependency_overrides[auth_deps.get_current_user_id] = lambda: "user"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/v1/focus_path", json={"person_id": "p1"})
    assert resp.status_code == 200
    assert resp.json()["anchor_step"] == "a"


@pytest.mark.asyncio
async def test_focus_path_in_turn(monkeypatch):
    class FakeDateTime(datetime.datetime):
        @classmethod
        def utcnow(cls):
            return datetime.datetime(2025, 1, 1, 8, 30, 0)

        @classmethod
        def today(cls):
            return datetime.date(2025, 1, 1)

    fake_datetime_module = types.SimpleNamespace(datetime=FakeDateTime, date=datetime.date)

    async def fake_q(sql, *args, **kwargs):
        if "focus_path_cache" in sql:
            return [
                {
                    "path_date": datetime.date(2025, 1, 1),
                    "anchor_step": "a",
                    "progress_step": "b",
                    "closure_step": "c",
                    "intent_source": "default",
                    "generated_at": "now",
                }
            ]
        if "conversation_turns" in sql:
            return [{"created_at": datetime.datetime(2025, 1, 1, 7, 0, 0)}]
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
        resp = await ac.post("/v2/turn", json={"text": "help me focus"})
    assert resp.status_code == 200
    data = resp.json()
    assert "focus_path" in data
