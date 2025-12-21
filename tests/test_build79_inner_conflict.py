import pytest
from httpx import AsyncClient, ASGITransport

from sakhi.apps.engine.inner_conflict import engine as conflict_engine
from sakhi.apps.api.main import app


@pytest.mark.asyncio
async def test_conflict_detection(monkeypatch):
    intents = [
        {"intent_name": "wake up early", "strength": 0.7, "trend": "up"},
        {"intent_name": "stay up late", "strength": 0.6, "trend": "down"},
    ]
    tasks = [
        {"id": "t1", "title": "heavy task", "status": "todo", "auto_priority": 0.8, "energy_cost": 0.9},
    ]

    async def fake_q(sql, *args, **kwargs):
        if "FROM intent_evolution" in sql:
            return intents
        if "FROM tasks" in sql:
            return tasks
        if "FROM personal_model" in sql:
            return {
                "identity_state": {"anchor_alignment": {"creative": 0.2, "disciplined": 0.7}},
                "emotion_state": {"trend": -0.2},
                "coherence_report": {"confidence": 0.3},
                "pattern_sense": {},
                "narrative_arcs": [],
            }
        if "FROM daily_alignment_cache" in sql:
            return {"alignment_map": {"avoid_actions": [1], "recommended_actions": [2]}}
        return None

    async def fake_resolve(pid):
        return pid

    monkeypatch.setattr(conflict_engine, "q", fake_q)
    monkeypatch.setattr(conflict_engine, "resolve_person_id", fake_resolve)

    state = await conflict_engine.compute_inner_conflict("demo")
    assert state["conflicts"]
    assert state["conflict_score"] > 0
    assert state["dominant_conflict"] is not None


@pytest.mark.asyncio
async def test_conflict_api(monkeypatch):
    async def fake_q(sql, *args, **kwargs):
        if "conflict_state" in sql and "personal_model" in sql:
            return {"conflict_state": {"conflict_score": 0.2}}
        return None

    monkeypatch.setattr("sakhi.apps.api.routes.inner_conflict.q", fake_q)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/v1/identity/conflict", params={"person_id": "demo"})
    assert resp.status_code == 200
    assert resp.json()["data"]["conflict_score"] == 0.2
