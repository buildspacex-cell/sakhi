import pytest
from httpx import AsyncClient, ASGITransport

from sakhi.apps.engine.forecast import engine as forecast_engine
from sakhi.apps.api.main import app


@pytest.mark.asyncio
async def test_forecast_rules(monkeypatch):
    emotion_rows = [{"emotion_loop": {"trend": -0.2}}, {"emotion_loop": {"trend": -0.1}}, {"emotion_loop": {"trend": 0.0}}]
    intents = [
        {"intent_name": "plan", "strength": 0.7, "trend": "up"},
    ]
    tasks = [{"status": "done", "auto_priority": 0.7, "energy_cost": 0.5, "updated_at": None}]

    async def fake_q(sql, *args, **kwargs):
        if "FROM personal_model" in sql:
            return {
                "identity_state": {"drift_score": -0.2},
                "conflict_state": {"conflicts": []},
                "coherence_state": {"fragmentation_index": 0.3},
                "pattern_sense": {},
                "forecast_state": {},
            }
        if "FROM memory_episodic" in sql:
            return emotion_rows
        if "FROM intent_evolution" in sql:
            return intents
        if "FROM tasks" in sql:
            return tasks
        return None

    async def fake_resolve(pid):
        return pid

    monkeypatch.setattr(forecast_engine, "q", fake_q)
    monkeypatch.setattr(forecast_engine, "resolve_person_id", fake_resolve)

    state = await forecast_engine.compute_forecast("demo")
    assert "emotion_forecast" in state
    assert state["clarity_forecast"]["clarity_score"] < 1
    assert state["risk_windows"]
    assert state["summary_text"]


@pytest.mark.asyncio
async def test_forecast_api(monkeypatch):
    async def fake_q(sql, *args, **kwargs):
        if "forecast_state" in sql and "personal_model" in sql:
            return {"forecast_state": {"summary_text": "ok"}}
        return None

    monkeypatch.setattr("sakhi.apps.api.routes.forecast.q", fake_q)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/v1/forecast", params={"person_id": "demo"})
    assert resp.status_code == 200
    assert resp.json()["data"]["summary_text"] == "ok"
