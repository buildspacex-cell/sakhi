import asyncio
import json
import os

import pytest
from fastapi.testclient import TestClient

# Skip if integration env not enabled or DB not available (avoids DB/LLM wiring)
if os.getenv("RUN_API_INTEGRATION_TESTS") != "1" or os.getenv("RUN_API_DB_TESTS") != "1":  # pragma: no cover - env guard
    pytest.skip("Skipping API integration test; set RUN_API_INTEGRATION_TESTS=1 and RUN_API_DB_TESTS=1 to run", allow_module_level=True)

from sakhi.apps.api.main import app


class DummyAuth:
    def __call__(self):
        return "test-user-id"


@pytest.fixture(autouse=True)
def patch_auth(monkeypatch):
    use_real = os.getenv("RUN_API_REAL") == "1"
    monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.get_current_user_id", DummyAuth())
    if use_real:
        async def real_resolve(pid):
            return "565bdb63-124b-4692-a039-846fddceff90"
        monkeypatch.setattr("sakhi.apps.api.core.person_utils.resolve_person_id", real_resolve)
        monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.resolve_person_id", real_resolve)
        monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.BUILD32_MODE", False)
    else:
        async def fake_resolve(pid):
            return "565bdb63-124b-4692-a039-846fddceff90"

        monkeypatch.setattr("sakhi.apps.api.core.person_utils.resolve_person_id", fake_resolve)
        monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.resolve_person_id", fake_resolve)
        # Avoid DB load for memory context
        async def fake_load_context(person_id):
            return {"cache_hit": True}
        monkeypatch.setattr("sakhi.apps.api.services.turn.context_loader.load_memory_context", fake_load_context)
        monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.load_memory_context", fake_load_context)
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
        # Short-circuit unified turn to avoid DB/brain
        async def fake_run_unified_turn(person_id, text):
            return {
                "brain": {},
                "behavior_profile": {"conversation_depth": "reflective", "session_context": {"reason": "growth"}},
                "activation": {"planner": True, "insight": True, "rhythm": False, "relationship": True, "soul": False},
                "triage": {},
                "planner": None,
                "insight": None,
            }
        monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.run_unified_turn", fake_run_unified_turn)
        monkeypatch.setattr("sakhi.apps.logic.harmony.orchestrator.run_unified_turn", fake_run_unified_turn)
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
        async def fake_call_llm(*args, **kwargs):
            return {"text": "ok"}
        monkeypatch.setattr("sakhi.apps.api.core.llm.call_llm", fake_call_llm)


@pytest.mark.asyncio
async def test_turn_harmony_mock_queue(monkeypatch):
    enqueue_calls = []

    async def fake_run_unified_turn(person_id, user_text):
        return {
            "brain": {},
            "behavior_profile": {"conversation_depth": "reflective", "session_context": {"reason": "growth"}},
            "activation": {"planner": True, "insight": True, "rhythm": False, "relationship": True, "soul": False},
            "triage": {},
            "planner": None,
            "insight": None,
        }

    def fake_enqueue(turn_id, user_id, jobs, payload):
        enqueue_calls.append({"turn_id": turn_id, "user_id": user_id, "jobs": jobs, "payload": payload})

    async def fake_generate_reply(person_id: str, user_text: str, metadata=None, behavior_profile=None):
        return {"reply": "ok", "tone_blueprint": {}, "journaling_ai": None}

    monkeypatch.setattr("sakhi.apps.logic.harmony.orchestrator.run_unified_turn", fake_run_unified_turn)
    monkeypatch.setattr("sakhi.apps.api.services.turn.async_triggers.enqueue_turn_jobs", fake_enqueue)
    monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.enqueue_turn_jobs", fake_enqueue)
    monkeypatch.setattr("sakhi.apps.api.services.conversation_v2.conversation_engine.generate_reply", fake_generate_reply)

    client = TestClient(app)
    resp = client.post("/v2/turn", json={"text": "reflective turn"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["reply"] == "ok"
    assert enqueue_calls, "Expected jobs to be enqueued"
    jobs = enqueue_calls[0]["jobs"]
    assert "turn_insight_update" in jobs
    # payload should at least carry the text/ts; behavior profile may be omitted in lightweight path
    payload = enqueue_calls[0]["payload"]
    assert payload.get("text") == "reflective turn"
