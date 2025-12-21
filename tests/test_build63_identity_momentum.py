import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from sakhi.core.soul.identity_momentum_engine import compute_fast_identity_momentum, compute_deep_identity_momentum
from sakhi.apps.worker import identity_momentum_deep
from sakhi.apps.api.routes import identity_momentum as identity_momentum_route


def test_fast_identity_momentum_ranges():
    out = compute_fast_identity_momentum(
        [{"text": "made progress"}],
        {"core_values": ["growth"], "shadow": ["doubt"], "light": ["optimism"], "friction": ["overwork"]},
        {"dominant": "joy"},
        {"body_energy": 0.7, "mind_focus": 0.6},
    )
    assert 0 <= out["momentum_score"] <= 1
    assert out["momentum_direction"] in {"forward", "stagnant", "regressing"}
    assert 0 <= out["emotional_drag"] <= 1
    assert 0 <= out["shadow_interference"] <= 1
    assert out["identity_push_pull"] in {"push", "pull", "neutral"}


@pytest.mark.asyncio
async def test_deep_identity_momentum(monkeypatch):
    async def fake_llm(messages=None, **kwargs):
        return {"identity_arc_summary": "ok", "growth_phase": "up"}

    async def fake_dbexec(sql, *args, **kwargs):
        pass

    async def fake_q(*a, **k):
        return []

    monkeypatch.setattr("sakhi.core.soul.identity_momentum_engine.call_llm", fake_llm, raising=False)
    monkeypatch.setattr("sakhi.apps.worker.identity_momentum_deep.dbexec", fake_dbexec)
    monkeypatch.setattr("sakhi.apps.worker.identity_momentum_deep.q", fake_q)

    res = await compute_deep_identity_momentum("pid", [], {}, {}, {})
    assert "identity_arc_summary" in res
    await identity_momentum_deep.run_identity_momentum_deep("pid")


def test_identity_momentum_api(monkeypatch):
    app = FastAPI()

    async def fake_q(query, person_id, one=False):
        return {
            "soul_state": {"core_values": ["growth"]},
            "emotion_state": {"dominant": "joy"},
            "rhythm_state": {"body_energy": 0.5},
            "identity_momentum_state": {"deep": True},
        }

    monkeypatch.setattr("sakhi.apps.api.routes.identity_momentum.q", fake_q)
    app.include_router(identity_momentum_route.router)
    client = TestClient(app)
    resp = client.get("/identity_momentum/demo")
    assert resp.status_code == 200
    data = resp.json()
    assert "fast" in data and "deep" in data
