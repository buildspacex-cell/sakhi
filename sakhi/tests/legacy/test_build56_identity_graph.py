import os
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

os.environ.setdefault("SUPABASE_URL", "http://localhost")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-key")

from sakhi.apps.api.services import identity_graph_engine  # noqa: E402
from sakhi.apps.api.routes import turn_v2  # noqa: E402


@pytest.mark.asyncio
async def test_coherence_links(monkeypatch: pytest.MonkeyPatch):
    async def fake_q(sql, *args, **kwargs):
        if "personal_model" in sql:
            return {
                "long_term": {
                    "layers": {
                        "soul": {"metrics": {"values": ["growth"], "life_themes": ["music/guitar"], "identity_anchors": []}},
                        "mind": {"metrics": {"priority_topics": ["guitar practice"], "cognitive_load": 0.2}, "summary": "focused"},
                        "emotion": {"summary": "positive"},
                        "goals": {"summary": ["learn guitar"]},
                    }
                }
            }
        if "memory_short_term" in sql:
            return [{"text": "guitar focus"}, {"text": "music practice"}]
        return None

    monkeypatch.setattr("sakhi.apps.api.services.identity_graph_engine.q", fake_q)
    result = await identity_graph_engine.build("p-coherence")
    coherence = result["edges"]["coherence"]
    assert ("growth", "guitar practice") in coherence or ("growth", "guitar") in coherence


@pytest.mark.asyncio
async def test_conflict_links(monkeypatch: pytest.MonkeyPatch):
    async def fake_q(sql, *args, **kwargs):
        if "personal_model" in sql:
            return {
                "long_term": {
                    "layers": {
                        "soul": {"metrics": {"values": ["discipline"], "life_themes": [], "identity_anchors": []}},
                        "mind": {"metrics": {"priority_topics": ["planning"], "cognitive_load": 0.9}, "summary": "overloaded"},
                        "emotion": {"summary": "negative"},
                        "goals": {},
                    }
                }
            }
        if "memory_short_term" in sql:
            return [{"text": "too many plans"}, {"text": "overwhelmed"}]
        return None

    monkeypatch.setattr("sakhi.apps.api.services.identity_graph_engine.q", fake_q)
    result = await identity_graph_engine.build("p-conflict")
    conflicts = result["edges"]["conflicts"]
    assert ("discipline", "overwhelm") in conflicts or ("discipline", "confusion") in conflicts


@pytest.mark.asyncio
async def test_reinforcements(monkeypatch: pytest.MonkeyPatch):
    async def fake_q(sql, *args, **kwargs):
        if "personal_model" in sql:
            return {
                "long_term": {
                    "layers": {
                        "soul": {"metrics": {"values": ["creativity"], "life_themes": ["music/guitar"], "identity_anchors": []}},
                        "mind": {"metrics": {"priority_topics": ["guitar practice"], "cognitive_load": 0.2}},
                        "emotion": {"summary": "positive"},
                        "goals": {},
                    }
                }
            }
        if "memory_short_term" in sql:
            return [{"text": "guitar session"}, {"text": "creative music"}]
        return None

    monkeypatch.setattr("sakhi.apps.api.services.identity_graph_engine.q", fake_q)
    result = await identity_graph_engine.build("p-reinforce")
    reinf = result["edges"]["reinforcements"]
    assert ("music/guitar", "guitar practice") in reinf or ("creativity", "guitar practice") in reinf


@pytest.mark.asyncio
async def test_identity_graph_persisted(monkeypatch: pytest.MonkeyPatch):
    async def fake_q(sql, *args, **kwargs):
        if "personal_model" in sql:
            return {
                "long_term": {
                    "layers": {
                        "soul": {"metrics": {"values": ["growth"], "life_themes": [], "identity_anchors": []}},
                        "mind": {"metrics": {"priority_topics": [], "cognitive_load": 0.1}},
                        "emotion": {"summary": "positive"},
                        "goals": {},
                    }
                }
            }
        if "memory_short_term" in sql:
            return []
        return None

    monkeypatch.setattr("sakhi.apps.api.services.identity_graph_engine.q", fake_q)
    graph = await identity_graph_engine.build("p-graph")
    assert "nodes" in graph and "edges" in graph


def test_turn_v2_metadata_identity(monkeypatch: pytest.MonkeyPatch):
    async def fake_q(sql, *args, **kwargs):
        if "personal_model" in sql:
            return {
                "long_term": {
                    "identity_graph": {
                        "edges": {"coherence": [("growth", "guitar")], "conflicts": [], "reinforcements": []}
                    },
                    "layers": {
                        "soul": {"metrics": {"values": ["growth"], "identity_anchors": [], "life_themes": []}},
                        "mind": {"metrics": {"priority_topics": [], "cognitive_load": 0.1}},
                    },
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
    assert "identity_graph" in body
    assert body["identity_graph"]["edges"]["coherence"] == [["growth", "guitar"]]
