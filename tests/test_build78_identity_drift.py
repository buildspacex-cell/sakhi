import pytest
from httpx import AsyncClient, ASGITransport

from sakhi.apps.engine.identity_drift import engine as identity_engine
from sakhi.apps.api.main import app


@pytest.mark.asyncio
async def test_identity_state_computation(monkeypatch):
    intents = [
        {"intent_name": "learn guitar", "strength": 0.7, "trend": "up", "emotional_alignment": 0.2},
        {"intent_name": "plan", "strength": 0.4, "trend": "stable", "emotional_alignment": 0.0},
    ]
    arcs = [{"intent": "learn guitar", "stage": "Rising Action", "momentum": 0.5}]

    async def fake_q(sql, *args, **kwargs):
        if "FROM intent_evolution" in sql:
            return intents
        if "FROM personal_model" in sql:
            return {
                "narrative_arcs": arcs,
                "pattern_sense": {},
                "emotion_state": {"trend": 0.1, "drift": 0.1},
                "coherence_report": {"confidence": 0.9},
                "inner_dialogue_state": {},
                "long_term": {"layers": {"soul": {"summary": "steady"}, "goals": {}}},
            }
        if "FROM daily_alignment_cache" in sql:
            return {"alignment_map": {"energy_profile": "high"}}
        if "FROM wellness_state_cache" in sql:
            return {"body": {"score": 0}, "mind": {"score": 1}, "emotion": {"score": 0}, "energy": {"score": 0}}
        return None

    async def fake_resolve(pid):
        return pid

    monkeypatch.setattr(identity_engine, "q", fake_q)
    monkeypatch.setattr(identity_engine, "resolve_person_id", fake_resolve)

    state = await identity_engine.compute_identity_state("demo-user")
    assert state["anchors"]
    assert "identity_movement" in state
    assert state["drift_score"] != 0
    assert any("Lean into" in msg for msg in state["opportunities"])


@pytest.mark.asyncio
async def test_identity_state_api(monkeypatch):
    async def fake_q(sql, *args, **kwargs):
        if "identity_state" in sql and "personal_model" in sql:
            return {"identity_state": {"identity_movement": "stable"}}
        return None

    monkeypatch.setattr("sakhi.apps.api.routes.identity_state.q", fake_q)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/v1/identity/state", params={"person_id": "demo"})
    assert resp.status_code == 200
    assert resp.json()["data"]["identity_movement"] == "stable"
