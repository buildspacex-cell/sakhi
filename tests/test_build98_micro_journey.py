import datetime
import sys
import types

import pytest
from httpx import AsyncClient, ASGITransport

from sakhi.apps.api.main import app
from sakhi.apps.api.deps import auth as auth_deps
from sakhi.apps.engine.micro_journey.engine import select_flow_count, generate_micro_journey
from sakhi.apps.worker.tasks.micro_journey_worker import run_micro_journey

# Patch missing coherence import for scheduler at import time
dummy_coherence = types.ModuleType("sakhi.apps.engine.coherence")
dummy_coherence.compute_coherence = lambda *args, **kwargs: {}
sys.modules["sakhi.apps.engine.coherence"] = dummy_coherence
from sakhi.apps.worker import scheduler  # noqa: E402


def test_select_flow_count_windows():
    assert select_flow_count(datetime.datetime(2025, 1, 1, 5, 0)) == 3
    assert select_flow_count(datetime.datetime(2025, 1, 1, 12, 0)) == 3
    assert select_flow_count(datetime.datetime(2025, 1, 1, 16, 0)) == 2
    assert select_flow_count(datetime.datetime(2025, 1, 1, 20, 0)) == 2
    assert select_flow_count(datetime.datetime(2025, 1, 1, 23, 30)) == 1


@pytest.mark.asyncio
async def test_generate_micro_journey(monkeypatch):
    async def fake_flow(pid):
        return {"warmup_step": "w", "focus_block_step": "f", "closure_step": "c", "flow_date": datetime.date.today().isoformat()}

    monkeypatch.setattr("sakhi.apps.engine.micro_journey.engine.generate_mini_flow", fake_flow)
    journey = await generate_micro_journey("p1")
    assert journey["flow_count"] == len(journey["flows"])
    assert journey["rhythm_slot"]


@pytest.mark.asyncio
async def test_micro_journey_worker(monkeypatch):
    calls = []

    async def fake_resolve(pid):
        return pid

    async def fake_exec(*args, **kwargs):
        calls.append(args[0])

    async def fake_flow(pid):
        return {
            "person_id": pid,
            "generated_at": datetime.datetime.utcnow().isoformat(),
            "rhythm_slot": "morning",
            "flow_count": 1,
            "flows": [],
            "structure": {},
        }

    monkeypatch.setattr("sakhi.apps.engine.micro_journey.engine.resolve_person_id", fake_resolve)
    monkeypatch.setattr("sakhi.apps.engine.micro_journey.engine.dbexec", fake_exec)
    monkeypatch.setattr("sakhi.apps.engine.micro_journey.engine.generate_micro_journey", fake_flow)

    await run_micro_journey("p1")
    assert any("micro_journey_cache" in c for c in calls)
    assert any("personal_model" in c for c in calls)


def test_schedule_micro_journey(monkeypatch):
    enqueued = []
    monkeypatch.setattr("sakhi.apps.worker.scheduler.DEFAULT_USER_ID", "user")
    monkeypatch.setattr("sakhi.apps.worker.scheduler._should_run_hour", lambda target: True)
    monkeypatch.setattr("sakhi.apps.worker.scheduler._should_run_minute", lambda target: True)
    monkeypatch.setattr(
        "sakhi.apps.worker.scheduler._enqueue",
        lambda queue, func, *args, **kwargs: enqueued.append(func.__name__),
    )
    scheduler.schedule_micro_journey_daily()
    assert "run_micro_journey" in enqueued


@pytest.mark.asyncio
async def test_micro_journey_route(monkeypatch):
    async def fake_resolve(pid):
        return pid

    async def fake_q(sql, *args, **kwargs):
        return [
            {
                "flow_count": 2,
                "rhythm_slot": "morning",
                "journey": {"flows": []},
                "generated_at": "now",
            }
        ]

    monkeypatch.setattr("sakhi.apps.api.routes.micro_journey.resolve_person_id", fake_resolve)
    monkeypatch.setattr("sakhi.apps.api.routes.micro_journey.q", fake_q)
    app.dependency_overrides[auth_deps.get_current_user_id] = lambda: "user"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/v1/micro_journey/p1")
    assert resp.status_code == 200
    assert resp.json()["flow_count"] == 2


@pytest.mark.asyncio
async def test_micro_journey_in_turn(monkeypatch):
    class FakeDateTime(datetime.datetime):
        @classmethod
        def utcnow(cls):
            return datetime.datetime(2025, 1, 1, 9, 0, 0)

        @classmethod
        def today(cls):
            return datetime.date(2025, 1, 1)

    fake_datetime_module = types.SimpleNamespace(datetime=FakeDateTime, date=datetime.date)

    async def fake_q(sql, *args, **kwargs):
        if "micro_journey_cache" in sql:
            return [
                {
                    "flow_count": 2,
                    "rhythm_slot": "morning",
                    "journey": {"flows": [{"anchor_step": "a"}]},
                    "generated_at": "now",
                }
            ]
        if "mini_flow_cache" in sql:
            return []
        if "focus_path_cache" in sql:
            return []
        if "conversation_turns" in sql:
            return [{"created_at": datetime.datetime(2025, 1, 1, 7, 0, 0)}]
        return []

    async def fake_resolve(pid):
        return "00000000-0000-0000-0000-000000000098"

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
        resp = await ac.post("/v2/turn", json={"text": "hello"})
    assert resp.status_code == 200
    data = resp.json()
    assert "micro_journey" in data

