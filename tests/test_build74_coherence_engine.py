import pytest

from sakhi.apps.engine.coherence import engine as coherence_engine


@pytest.mark.asyncio
async def test_coherence_rules(monkeypatch):
    async def fake_q(sql, *args, **kwargs):
        if "FROM wellness_state_cache" in sql:
            return {"body": {"score": 0}, "mind": {"score": 3}, "emotion": {"score": -0.2}, "energy": {"score": -0.4}}
        if "FROM intent_evolution" in sql:
            return [{"intent_name": "plan", "strength": 0.7, "emotional_alignment": 0.1, "trend": "up"}]
        if "FROM daily_alignment_cache" in sql:
            return {"alignment_map": {"avoid_actions": [{"id": "x"}]}}
        if "FROM tasks" in sql:
            return [{"id": "t1", "title": "heavy task", "energy_cost": 0.8, "auto_priority": 0.2}]
        if "FROM personal_model" in sql:
            return {"long_term": {"layers": {"goals": {"status": "offbeat"}, "soul": {"summary": "needs grounding"}}}}
        return None

    async def fake_resolve(pid):
        return pid

    monkeypatch.setattr(coherence_engine, "q", fake_q)
    monkeypatch.setattr(coherence_engine, "resolve_person_id", fake_resolve)

    res = await coherence_engine.compute_coherence("p1")
    assert res["issues"]
    assert res["confidence"] <= 1
