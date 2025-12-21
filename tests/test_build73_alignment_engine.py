import pytest

from sakhi.apps.engine.alignment import engine as align_engine
from sakhi.apps.worker.tasks import alignment_refresh


@pytest.mark.asyncio
async def test_alignment_profiles(monkeypatch):
    async def fake_q(sql, *args, **kwargs):
        if "FROM wellness_state_cache" in sql:
            return {"body": {"score": 0.1}, "mind": {"score": 1}, "emotion": {"score": -0.1}, "energy": {"score": 0.6}}
        if "FROM intent_evolution" in sql:
            return [{"intent_name": "plan", "strength": 0.6, "emotional_alignment": 0.2, "trend": "up"}]
        if "FROM tasks" in sql:
            return [{"id": "t1", "title": "plan roadmap", "energy_cost": 0.2, "auto_priority": 0.5, "anchor_goal_id": None}]
        if "emotion_state" in sql:
            return {}
        return None

    async def fake_exec(*args, **kwargs):
        return None

    async def fake_resolve(pid):
        return pid

    monkeypatch.setattr(align_engine, "q", fake_q)
    monkeypatch.setattr(alignment_refresh, "alignment_engine", align_engine)
    monkeypatch.setattr(alignment_refresh, "q", fake_q)
    monkeypatch.setattr(alignment_refresh, "dbexec", fake_exec)
    monkeypatch.setattr(alignment_refresh, "resolve_person_id", fake_resolve)

    res = await align_engine.compute_alignment_map("p1")
    assert res["energy_profile"] == "high"
    assert res["focus_profile"] == "scattered"
    assert res["recommended_actions"]

    await alignment_refresh.alignment_refresh("p1")
