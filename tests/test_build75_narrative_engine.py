import pytest

from sakhi.apps.engine.narrative import engine as narrative_engine


@pytest.mark.asyncio
async def test_narrative_arcs_rules(monkeypatch):
    async def fake_intents(*args, **kwargs):
        return [
            {"intent_name": "plan", "strength": 0.7, "emotional_alignment": 0.1, "trend": "up"},
            {"intent_name": "light", "strength": 0.2, "emotional_alignment": 0.0, "trend": "stable"},
        ]

    async def fake_tasks(person_id, intent_name):
        return [
            {"id": "t1", "title": f"{intent_name} task", "status": "todo", "energy_cost": 0.3, "auto_priority": 0.5}
        ]

    async def fake_q(sql, *args, **kwargs):
        if "FROM personal_model" in sql:
            return {"long_term": {"coherence_report": {"issues": ["Some issue"]}, "emotion_state": {"drift": -0.3}}}
        if "FROM daily_alignment_cache" in sql:
            return {"alignment_map": {"avoid_actions": []}}
        return None

    async def fake_resolve(pid):
        return pid

    monkeypatch.setattr(narrative_engine, "_fetch_intents", fake_intents)
    monkeypatch.setattr(narrative_engine, "_fetch_tasks", fake_tasks)
    monkeypatch.setattr(narrative_engine, "q", fake_q)
    monkeypatch.setattr(narrative_engine, "resolve_person_id", fake_resolve)

    arcs = await narrative_engine.compute_narrative_arcs("p1")
    assert len(arcs) == 1
    arc = arcs[0]
    assert arc["intent"] == "plan"
    assert arc["stage"] in {"Initiation", "Plateau", "Rising Action", "Climax", "Recovery"}
    assert arc["warnings"]
    assert arc["momentum"] >= 0
