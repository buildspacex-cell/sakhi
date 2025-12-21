import pytest

from sakhi.apps.engine.emotion_loop import engine as emo_engine
from sakhi.apps.worker.tasks import emotion_loop_refresh


def test_trend_and_mode():
    sentiments = [-0.2, -0.1, 0.0, 0.1, 0.2]
    res = emo_engine.compute_emotion_loop("p1", sentiments)
    assert res["trend"] > 0
    assert res["mode"] in {"rising", "recovery", "stable", "volatile"}
    assert res["volatility"] >= 0


def test_volatility_inertia():
    sentiments = [0.5, -0.5, 0.5, -0.5]
    res = emo_engine.compute_emotion_loop("p1", sentiments)
    assert res["volatility"] > 0.4
    assert res["inertia"] > 0


@pytest.mark.asyncio
async def test_emotion_loop_refresh(monkeypatch):
    async def fake_compute(person_id):
        return {"mode": "stable", "trend": 0.0, "drift": 0.0, "inertia": 0.1, "volatility": 0.1, "is_recovery": False, "updated_at": "now"}

    async def fake_q(sql, *args, **kwargs):
        return {"long_term": {}}

    async def fake_exec(sql, *args, **kwargs):
        return None

    async def fake_resolve(pid):
        return pid

    monkeypatch.setattr(emotion_loop_refresh, "emotion_loop_engine", type("obj", (), {"compute_emotion_loop_for_person": fake_compute}))
    monkeypatch.setattr(emotion_loop_refresh, "q", fake_q)
    monkeypatch.setattr(emotion_loop_refresh, "dbexec", fake_exec)
    monkeypatch.setattr(emotion_loop_refresh, "resolve_person_id", fake_resolve)

    await emotion_loop_refresh.emotion_loop_refresh("00000000-0000-0000-0000-000000000000")
