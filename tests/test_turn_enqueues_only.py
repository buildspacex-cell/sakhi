import asyncio
import json
import os

import pytest
from fastapi.testclient import TestClient

# Skip if integration env not enabled or DB not available (avoids DB/LLM wiring)
if os.getenv("RUN_API_INTEGRATION_TESTS") != "1" or os.getenv("RUN_API_DB_TESTS") != "1":  # pragma: no cover - env guard
    pytest.skip("Skipping API integration test; set RUN_API_INTEGRATION_TESTS=1 and RUN_API_DB_TESTS=1 to run", allow_module_level=True)

from sakhi.apps.api.main import app
from sakhi.apps.api.core import person_utils


class DummyAuth:
    def __call__(self):
        return "test-user-id"


@pytest.fixture(autouse=True)
def patch_auth(monkeypatch):
    use_real = os.getenv("RUN_API_REAL") == "1"
    monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.get_current_user_id", DummyAuth())
    if use_real:
        # Real run: only ensure user_id is resolved to our seeded person_id
        async def real_resolve(pid):
            return "565bdb63-124b-4692-a039-846fddceff90"
        monkeypatch.setattr("sakhi.apps.api.core.person_utils.resolve_person_id", real_resolve)
        monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.resolve_person_id", real_resolve)
        # Ensure we hit full Build-50 path
        monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.BUILD32_MODE", False)
    else:
        async def fake_resolve(pid):
            return "565bdb63-124b-4692-a039-846fddceff90"

        monkeypatch.setattr("sakhi.apps.api.core.person_utils.resolve_person_id", fake_resolve)
        monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.resolve_person_id", fake_resolve)
        # Stub reply generation to avoid LLM initialisation
        async def fake_reply(**kwargs):
            return {"reply": "ok", "tone_blueprint": {}, "journaling_ai": None}

        monkeypatch.setattr(
            "sakhi.apps.api.services.conversation_v2.conversation_engine.generate_reply",
            fake_reply,
        )
        # Avoid DB load for memory context
        async def fake_load_context(person_id):
            return {"cache_hit": True}
        monkeypatch.setattr("sakhi.apps.api.services.turn.context_loader.load_memory_context", fake_load_context)
        monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.load_memory_context", fake_load_context)
        # Short-circuit unified turn to avoid DB/brain
        async def fake_run_unified_turn(person_id, text):
            return {
                "brain": {},
                "behavior_profile": {"conversation_depth": "surface"},
                "activation": {"planner": False, "insight": False, "rhythm": False, "relationship": True, "soul": False},
                "triage": {},
                "planner": None,
                "insight": None,
            }
        monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.run_unified_turn", fake_run_unified_turn)
        monkeypatch.setattr("sakhi.apps.logic.harmony.orchestrator.run_unified_turn", fake_run_unified_turn)
        # Short-circuit orchestrate_turn and memory write to avoid DB inserts
        async def fake_orchestrate_turn(person_id, text, clarity_hint=None):
            return {
                "entry_id": None,
                "embedding": [],
                "topics": [],
                "emotion": {},
                "intents": [],
                "plans": [],
                "rhythm_triggers": {},
                "meta_reflection_triggers": {},
                "triage": {},
            }

        async def fake_write_memory(**kwargs):
            return {}

        monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.orchestrate_turn", fake_orchestrate_turn)
        monkeypatch.setattr("sakhi.apps.logic.harmony.memory_write_controller.write_turn_memory", fake_write_memory)
        # Short-circuit lightweight reply path
        async def fake_build_turn_reply(**kwargs):
            return {"reply": "ok", "metadata": {}, "tone": {}, "journaling_ai": None}
        monkeypatch.setattr("sakhi.apps.api.services.turn.reply_service.build_turn_reply", fake_build_turn_reply)
        monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.build_turn_reply", fake_build_turn_reply)
        # Avoid DB recall/synthesis
        async def fake_synth(person_id, user_query, limit=350):
            return ""
        async def fake_recall(person_id, query, limit=5):
            return []
        monkeypatch.setattr("sakhi.apps.api.services.memory.context_synthesizer.synthesize_memory_context", fake_synth)
        monkeypatch.setattr("sakhi.apps.api.services.memory.recall.memory_recall", fake_recall)
        # Force lightweight path to avoid DB/LLM
        monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.BUILD32_MODE", True)
        # Stub call_llm to avoid router initialisation
        async def fake_call_llm(*args, **kwargs):
            return {"text": "ok"}
        monkeypatch.setattr("sakhi.apps.api.core.llm.call_llm", fake_call_llm)


@pytest.mark.asyncio
async def test_turn_endpoint_light(monkeypatch):
    enqueue_calls = []

    async def fake_run_unified_turn(person_id, user_text):
        return {
            "brain": {},
            "behavior_profile": {"conversation_depth": "surface"},
            "activation": {"planner": False, "insight": False, "rhythm": False, "relationship": True, "soul": False},
            "triage": {},
            "planner": None,
            "insight": None,
        }

    def fake_enqueue(turn_id, user_id, jobs, payload):
        enqueue_calls.append({"turn_id": turn_id, "user_id": user_id, "jobs": jobs, "payload": payload})

    # Patch orchestrator and enqueue
    monkeypatch.setattr("sakhi.apps.logic.harmony.orchestrator.run_unified_turn", fake_run_unified_turn)
    monkeypatch.setattr("sakhi.apps.api.services.turn.async_triggers.enqueue_turn_jobs", fake_enqueue)
    monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.enqueue_turn_jobs", fake_enqueue)
    client = TestClient(app)

    resp = client.post("/v2/turn", json={"text": "hello"})
    assert resp.status_code == 200
    data = resp.json()
    assert "reply" in data
    assert enqueue_calls, "Jobs were not enqueued"
    jobs = enqueue_calls[0]["jobs"]
    assert "turn_planner_update" in jobs
    assert "turn_insight_update" in jobs


def test_turn_invalid_user(monkeypatch):
    # Force resolver to fail and bypass DB
    async def fake_resolve_none(pid):
        return None

    async def fake_reply(**kwargs):
        return {"reply": "ok", "tone_blueprint": {}, "journaling_ai": None}

    monkeypatch.setattr("sakhi.apps.api.core.person_utils.resolve_person_id", fake_resolve_none)
    monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.resolve_person_id", fake_resolve_none)
    monkeypatch.setattr(
        "sakhi.apps.api.services.conversation_v2.conversation_engine.generate_reply",
        fake_reply,
    )
    client = TestClient(app)
    resp = client.post("/v2/turn", json={"text": "hello"})
    assert resp.status_code == 400
