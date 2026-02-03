import os
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

os.environ.setdefault("SUPABASE_URL", "http://localhost")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-key")

from sakhi.apps.api.services import soul_engine  # noqa: E402
from sakhi.apps.api.routes import turn_v2  # noqa: E402


@pytest.mark.asyncio
async def test_values_extraction(monkeypatch: pytest.MonkeyPatch):
    async def fake_q(sql, *args, **kwargs):
        return {
            "long_term": {
                "observations": [
                    {"text": "I want to improve daily", "created_at": None},
                    {"text": "I need discipline to be better", "created_at": None},
                ]
            }
        }

    monkeypatch.setattr("sakhi.apps.api.services.soul_engine.q", fake_q)
    result = await soul_engine.compute("p1")
    values = result["metrics"]["values"]
    assert "growth" in values
    assert "stability" in values or "discipline" in " ".join(values)


@pytest.mark.asyncio
async def test_identity_anchors(monkeypatch: pytest.MonkeyPatch):
    async def fake_q(sql, *args, **kwargs):
        return {
            "long_term": {
                "observations": [
                    {"text": "I want to be the kind of person who practices daily", "created_at": None}
                ]
            }
        }

    monkeypatch.setattr("sakhi.apps.api.services.soul_engine.q", fake_q)
    result = await soul_engine.compute("p2")
    anchors = result["metrics"]["identity_anchors"]
    assert any("practices daily" in a for a in anchors)


@pytest.mark.asyncio
async def test_life_themes(monkeypatch: pytest.MonkeyPatch):
    async def fake_q(sql, *args, **kwargs):
        return {
            "long_term": {
                "observations": [
                    {"text": "guitar practice today", "created_at": "2025-01-01T00:00:00Z"},
                    {"text": "love music and guitar", "created_at": "2025-01-02T00:00:00Z"},
                    {"text": "another guitar session", "created_at": "2025-01-03T00:00:00Z"},
                ]
            }
        }

    monkeypatch.setattr("sakhi.apps.api.services.soul_engine.q", fake_q)
    result = await soul_engine.compute("p3")
    themes = result["metrics"]["life_themes"]
    assert any("guitar" in t for t in themes)


@pytest.mark.asyncio
async def test_soul_summary_stability(monkeypatch: pytest.MonkeyPatch):
    data = {
        "long_term": {
            "observations": [
                {"text": "learning and balance", "created_at": None},
                {"text": "I want to be the kind of person who stays disciplined", "created_at": None},
            ]
        }
    }

    async def fake_q(sql, *args, **kwargs):
        return data

    monkeypatch.setattr("sakhi.apps.api.services.soul_engine.q", fake_q)
    first = await soul_engine.compute("p4")
    second = await soul_engine.compute("p4")
    assert first["summary"] == second["summary"]


def test_turn_v2_metadata_soul(monkeypatch: pytest.MonkeyPatch):
    async def fake_q(sql, *args, **kwargs):
        if "personal_model" in sql:
            return {
                "long_term": {
                    "layers": {
                        "soul": {
                            "metrics": {
                                "values": ["growth"],
                                "identity_anchors": ["practices daily"],
                                "life_themes": ["music/guitar"],
                            }
                        }
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
    assert body.get("soul_values") == ["growth"]
    assert body.get("soul_identity") == ["practices daily"]
    assert body.get("life_themes") == ["music/guitar"]
