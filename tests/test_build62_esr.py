import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from sakhi.core.emotion.emotion_soul_rhythm_engine import compute_fast_esr_frame, compute_deep_esr
from sakhi.apps.worker import esr_deep
from sakhi.apps.api.routes import emotion_soul_rhythm as esr_route


def test_fast_esr_frame_ranges():
    out = compute_fast_esr_frame(
        {"dominant": "joy"},
        {"core_values": ["growth"], "shadow": ["doubt"], "friction": ["overwork"], "light": ["optimism"]},
        {"body_energy": 0.7, "mind_focus": 0.6},
    )
    assert 0 <= out["coherence_score"] <= 1
    assert -1 <= out["emotion_vs_soul"] <= 1
    assert -1 <= out["emotion_vs_rhythm"] <= 1
    assert -1 <= out["soul_vs_rhythm"] <= 1
    assert "dominant_friction_zone" in out


@pytest.mark.asyncio
async def test_deep_esr(monkeypatch):
    async def fake_llm(messages=None, **kwargs):
        return {"weekly_coherence_map": "ok", "recommended_pacing": "steady"}

    async def fake_dbexec(sql, *args, **kwargs):
        pass

    async def fake_q(*a, **k):
        return []

    monkeypatch.setattr("sakhi.core.emotion.emotion_soul_rhythm_engine.call_llm", fake_llm, raising=False)
    monkeypatch.setattr("sakhi.apps.worker.esr_deep.dbexec", fake_dbexec)
    monkeypatch.setattr("sakhi.apps.worker.esr_deep.q", fake_q)

    res = await compute_deep_esr("pid", [], {}, {}, {})
    assert "weekly_coherence_map" in res
    await esr_deep.run_esr_deep("pid")


def test_esr_api(monkeypatch):
    app = FastAPI()

    async def fake_q(query, person_id, one=False):
        return {"emotion_state": {"dominant": "joy"}, "soul_state": {"core_values": ["care"]}, "rhythm_state": {"body_energy": 0.5}, "emotion_soul_rhythm_state": {"deep": True}}

    monkeypatch.setattr("sakhi.apps.api.routes.emotion_soul_rhythm.q", fake_q)
    app.include_router(esr_route.router)
    client = TestClient(app)
    resp = client.get("/esr/demo")
    assert resp.status_code == 200
    data = resp.json()
    assert "fast" in data and "deep" in data
