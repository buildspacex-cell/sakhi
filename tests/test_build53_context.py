import uuid
import asyncio
import os
from typing import Any, Dict, List

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

os.environ.setdefault("SUPABASE_URL", "http://localhost")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-key")

from sakhi.apps.api.services.workers import context_refresh_worker as ctx_worker  # noqa: E402
from sakhi.apps.api.services.emotion_engine import compute as compute_emotion  # noqa: E402
from sakhi.apps.api.services.mind_engine import compute as compute_mind  # noqa: E402
from sakhi.apps.api.routes import turn_v2  # noqa: E402


class MemoryDB:
    def __init__(self):
        self.st_rows: List[Dict[str, Any]] = []
        self.ep_rows: List[Dict[str, Any]] = []
        self.cache_row: Dict[str, Any] | None = None

    async def q(self, sql: str, *args, one: bool = False):
        if "memory_short_term" in sql:
            return list(self.st_rows)
        if "memory_episodic" in sql:
            return list(self.ep_rows)
        if "personal_model" in sql:
            return {
                "long_term": {
                    "layers": {
                        "emotion": {"summary": "calm"},
                        "mind": {"summary": "planning"},
                    }
                }
            }
        if "memory_context_cache" in sql:
            return {"merged_context_vector": [0.1, 0.1]}
        return None if one else []

    async def exec(self, sql: str, *args):
        if "memory_context_cache" in sql:
            self.cache_row = {
                "person_id": args[0],
                "merged_context_vector": args[1],
            }
            return


@pytest.mark.asyncio
async def test_context_vector_generated(monkeypatch: pytest.MonkeyPatch):
    db = MemoryDB()
    db.st_rows = [
        {"vec": [1.0, 1.0], "content_hash": "a", "updated_at": None},
        {"vec": [3.0, 3.0], "content_hash": "b", "updated_at": None},
    ]
    monkeypatch.setattr(ctx_worker, "q", db.q)
    monkeypatch.setattr(ctx_worker, "dbexec", db.exec)

    result = await ctx_worker.refresh_context("p1")
    assert result["vector_length"] == 2
    assert db.cache_row is not None
    assert db.cache_row["merged_context_vector"] == [2.0, 2.0]


@pytest.mark.asyncio
async def test_emotion_engine_from_keywords(monkeypatch: pytest.MonkeyPatch):
    async def fake_q(sql, *args, **kwargs):
        return [
            {"triage": {}, "text": "i feel very tired today", "updated_at": None},
            {"triage": {"slots": {"mood_affect": {"label": "motivated", "score": 0.8}}}, "text": "motivated", "updated_at": None},
        ]

    monkeypatch.setattr("sakhi.apps.api.services.emotion_engine.q", fake_q)

    summary = await compute_emotion("p2")
    assert "tired" in summary["summary"] or "motivat" in summary["summary"]
    assert summary["confidence"] > 0.3


@pytest.mark.asyncio
async def test_mind_engine_planning(monkeypatch: pytest.MonkeyPatch):
    async def fake_q(sql, *args, **kwargs):
        return [
            {"triage": {"type": "reflection_observation"}, "text": "need to plan next week", "updated_at": None}
        ]

    monkeypatch.setattr("sakhi.apps.api.services.mind_engine.q", fake_q)

    summary = await compute_mind("p3")
    assert "planning" in summary["summary"]


def test_turn_v2_internal_state(monkeypatch: pytest.MonkeyPatch):
    # Patch dependencies to keep route lightweight
    async def fake_q(sql, *args, **kwargs):
        if "personal_model" in sql:
            return {
                "long_term": {
                    "layers": {
                        "emotion": {"summary": "calm"},
                        "mind": {"summary": "planning"},
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

    monkeypatch.setattr(turn_v2, "q", fake_q)
    monkeypatch.setattr(turn_v2, "orchestrate_turn", fake_orchestrate_turn)
    monkeypatch.setattr(turn_v2, "run_unified_turn", fake_run_unified_turn)
    monkeypatch.setattr(turn_v2, "generate_reply", fake_generate_reply)
    async def _resolve(pid):
        return pid

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
    assert "internal_state" in body
    assert body["internal_state"]["emotion"] == "calm"
    assert body["internal_state"]["mind"] == "planning"
