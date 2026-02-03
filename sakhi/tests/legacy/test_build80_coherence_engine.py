import pytest
from httpx import AsyncClient, ASGITransport

from sakhi.apps.engine.coherence import engine as coherence_engine
from sakhi.apps.api.main import app


@pytest.mark.asyncio
async def test_coherence_computation(monkeypatch):
    intents = [
        {"intent_name": "learn", "strength": 0.7, "emotional_alignment": 0.1, "trend": "up"},
        {"intent_name": "rest", "strength": 0.6, "emotional_alignment": 0.0, "trend": "down"},
    ]
    tasks = [
        {"id": "t1", "title": "task", "energy_cost": 0.8, "auto_priority": 0.7, "status": "todo"},
    ]

    async def fake_q(sql, *args, **kwargs):
        if "FROM wellness_state_cache" in sql:
            return {"body": {"score": 0}, "mind": {"score": 1}, "emotion": {"score": 0}, "energy": {"score": -0.4}}
        if "FROM intent_evolution" in sql:
            return intents
        if "FROM daily_alignment_cache" in sql:
            return {"alignment_map": {"avoid_actions": [1], "recommended_actions": [2]}}
        if "FROM tasks" in sql:
            return tasks
        if "FROM personal_model" in sql:
            return {
                "narrative_arcs": [{"momentum": 0.4}],
                "identity_state": {"anchor_alignment": {"creative": 0.2, "discipline": 0.8}, "drift_score": -0.2},
                "conflict_state": {"conflicts": [{"a": "self", "b": "self"}]},
                "emotion_state": {"trend": -0.1, "volatility": 0.2},
                "pattern_sense": {},
                "coherence_report": {"confidence": 0.9},
            }
        return None

    async def fake_resolve(pid):
        return pid

    monkeypatch.setattr(coherence_engine, "q", fake_q)
    monkeypatch.setattr(coherence_engine, "resolve_person_id", fake_resolve)

    state = await coherence_engine.compute_coherence("demo")
    assert "coherence_score" in state
    assert "fragmentation_index" in state
    assert state["coherence_map"]
    assert state["issues"]  # should detect low energy vs heavy tasks


@pytest.mark.asyncio
async def test_coherence_api(monkeypatch):
    async def fake_q(sql, *args, **kwargs):
        if "coherence_state" in sql and "personal_model" in sql:
            return {"coherence_state": {"coherence_score": 0.5}}
        return None

    monkeypatch.setattr("sakhi.apps.api.routes.coherence.q", fake_q)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/v1/coherence/report", params={"person_id": "demo"})
    assert resp.status_code == 200
    assert resp.json()["data"]["coherence_score"] == 0.5
