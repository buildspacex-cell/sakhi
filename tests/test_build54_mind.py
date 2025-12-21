import os
import uuid
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

os.environ.setdefault("SUPABASE_URL", "http://localhost")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-key")

from sakhi.apps.api.services import mind_engine  # noqa: E402
from sakhi.apps.api.routes import turn_v2  # noqa: E402


@pytest.mark.asyncio
async def test_cognitive_load_high(monkeypatch: pytest.MonkeyPatch):
    async def fake_q(sql, *args, **kwargs):
        return [
            {"triage": {"type": "task"}, "text": "need to figure out finance plan", "updated_at": None},
            {"triage": {"type": "plan_needed"}, "text": "urgent work project", "updated_at": None},
            {"triage": {"type": "info_needed"}, "text": "confused about health routine", "updated_at": None},
            {"triage": {"type": "decision_needed"}, "text": "must decide on relationships topic", "updated_at": None},
        ]

    monkeypatch.setattr("sakhi.apps.api.services.mind_engine.q", fake_q)
    summary = await mind_engine.compute("p-load")
    assert summary["metrics"]["cognitive_load"] >= 0.7


@pytest.mark.asyncio
async def test_priority_extraction(monkeypatch: pytest.MonkeyPatch):
    async def fake_q(sql, *args, **kwargs):
        return [
            {"triage": {}, "text": "guitar practice today", "updated_at": None},
            {"triage": {}, "text": "must improve guitar practice routine", "updated_at": None},
            {"triage": {}, "text": "music and guitar session", "updated_at": None},
        ]

    monkeypatch.setattr("sakhi.apps.api.services.mind_engine.q", fake_q)
    summary = await mind_engine.compute("p-priority")
    assert summary["metrics"]["top_priority"] == "guitar practice"
    assert "guitar practice" in summary["metrics"]["priority_topics"]


def test_mind_summary_text():
    # Directly test summary phrasing based on score thresholds
    metrics_low = {"summary": "mind relatively clear; focused", "metrics": {"cognitive_load": 0.2}}
    assert "clear" in metrics_low["summary"]


def test_turn_v2_metadata_injection(monkeypatch: pytest.MonkeyPatch):
    async def fake_q(sql, *args, **kwargs):
        if "personal_model" in sql:
            return {
                "long_term": {
                    "layers": {
                        "mind": {
                            "summary": "managing several things; moderate load. Current top concern: planning.",
                            "metrics": {"cognitive_load": 0.5, "top_priority": "planning", "priority_topics": ["planning"]},
                        },
                        "emotion": {"summary": "neutral"},
                    }
                }
            }
        if "memory_context_cache" in sql:
            return {"merged_context_vector": [0.1, 0.1]}
        return None

    async def fake_orchestrate_turn(**kwargs):
        return {"entry_id": None, "embedding": [], "topics": [], "emotion": {}, "intents": [], "plans": []}

    async def fake_run_unified_turn(person_id, text):
        return {"behavior_profile": {}, "planner": None, "insight": None, "activation": {}, "triage": {}}

    async def fake_generate_reply(**kwargs):
        return {"reply": "ok", "tone_blueprint": {}, "journaling_ai": None}

    async def _resolve(pid):
        return pid

    monkeypatch.setattr(turn_v2, "q", fake_q)
    monkeypatch.setattr(turn_v2, "orchestrate_turn", fake_orchestrate_turn)
    monkeypatch.setattr(turn_v2, "run_unified_turn", fake_run_unified_turn)
    monkeypatch.setattr(turn_v2, "generate_reply", fake_generate_reply)
    monkeypatch.setattr(turn_v2, "resolve_person_id", _resolve)
    monkeypatch.setattr(turn_v2, "load_memory_context", lambda person_id: {})

    app = FastAPI()
    demo_id = os.getenv("DEMO_USER_ID", "565bdb63-124b-4692-a039-846fddceff90")
    app.dependency_overrides[turn_v2.get_current_user_id] = lambda: demo_id
    app.include_router(turn_v2.router)

    client = TestClient(app)
    resp = client.post("/v2/turn", json={"text": "hello"})
    assert resp.status_code == 200
    body = resp.json()
    assert "cognitive_load" in body
    assert body["cognitive_load"] == 0.5
    assert body["priority"] == "planning"
