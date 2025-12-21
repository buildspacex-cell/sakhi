import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from sakhi.core.soul.identity_timeline_engine import compute_fast_identity_timeline_frame, compute_deep_identity_timeline
from sakhi.apps.worker import identity_timeline_deep
from sakhi.apps.api.routes import identity_timeline as identity_timeline_route


def test_fast_identity_timeline_frame():
    out = compute_fast_identity_timeline_frame(
        [{"text": "new change"}],
        {"identity_themes": ["learning"], "shadow": ["doubt"], "light": ["optimism"], "friction": ["time"]},
        {"dominant": "joy"},
        {"body_energy": 0.7, "mind_focus": 0.6},
        {"momentum_score": 0.8},
    )
    assert "current_phase" in out
    assert "persona_shift_tendency" in out
    assert 0 <= out["phase_intensity"] <= 1


@pytest.mark.asyncio
async def test_deep_identity_timeline(monkeypatch):
    async def fake_llm(messages=None, **kwargs):
        return {"weekly_identity_phase": "growth", "persona_evolution": {"arc": "up"}}

    async def fake_dbexec(sql, *args, **kwargs):
        pass

    async def fake_q(*a, **k):
        return []

    monkeypatch.setattr("sakhi.core.soul.identity_timeline_engine.call_llm", fake_llm, raising=False)
    monkeypatch.setattr("sakhi.apps.worker.identity_timeline_deep.dbexec", fake_dbexec)
    monkeypatch.setattr("sakhi.apps.worker.identity_timeline_deep.q", fake_q)

    res = await compute_deep_identity_timeline("pid", [], {}, {}, {}, {})
    assert "weekly_identity_phase" in res or "identity_arc" in res
    await identity_timeline_deep.run_identity_timeline_deep("pid")


def test_identity_timeline_api(monkeypatch):
    app = FastAPI()

    async def fake_q(query, person_id, one=False):
        return {
            "soul_state": {"identity_themes": ["learning"]},
            "emotion_state": {"dominant": "joy"},
            "rhythm_state": {"body_energy": 0.5},
            "identity_momentum_state": {"momentum_score": 0.5},
            "identity_timeline": {"weekly_identity_phase": "growth"},
            "persona_evolution_state": {"arc": "up"},
        }

    monkeypatch.setattr("sakhi.apps.api.routes.identity_timeline.q", fake_q)
    app.include_router(identity_timeline_route.router)
    client = TestClient(app)
    resp = client.get("/identity_timeline/demo")
    assert resp.status_code == 200
    data = resp.json()
    assert "fast" in data
    assert "deep" in data and "timeline" in data["deep"]
