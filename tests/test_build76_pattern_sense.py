import datetime as dt

import pytest

from sakhi.apps.engine.pattern_sense import engine as ps_engine
from sakhi.apps.worker.tasks import pattern_sense_refresh


@pytest.mark.asyncio
async def test_pattern_sense(monkeypatch):
    now = dt.datetime.utcnow()
    async def fake_q(sql, *args, **kwargs):
        if "FROM memory_episodic" in sql:
            return [
                {"updated_at": now.isoformat(), "triage": {"slots": {"mood_affect": {"score": -0.2}}}, "context_tags": [{"wellness_tags": {"body": 1, "mind": 1, "emotion": -0.2, "energy": 0}}]},
                {"updated_at": now.isoformat(), "triage": {"slots": {"mood_affect": {"score": 0.1}}}, "context_tags": [{"wellness_tags": {"body": 0, "mind": 0, "emotion": 0.1, "energy": 1}}]},
            ]
        if "FROM intent_evolution" in sql:
            return [{"intent_name": "plan", "strength": 0.5, "emotional_alignment": 0.1}]
        if "FROM tasks" in sql:
            return [{"status": "done", "energy_cost": 0.5}]
        if "FROM personal_os_brain" in sql:
            return {"rhythm_state": {"status": "stable"}}
        return None

    async def fake_resolve(pid):
        return pid

    monkeypatch.setattr(ps_engine, "q", fake_q)
    monkeypatch.setattr(ps_engine, "resolve_person_id", fake_resolve)

    patterns = await ps_engine.compute_patterns("p1")
    assert "emotional_patterns" in patterns
    assert "intent_couplings" in patterns

    # worker path
    async def fake_exec(*args, **kwargs):
        return None

    monkeypatch.setattr(pattern_sense_refresh, "pattern_engine", ps_engine)
    monkeypatch.setattr(pattern_sense_refresh, "dbexec", fake_exec)
    monkeypatch.setattr(pattern_sense_refresh, "resolve_person_id", fake_resolve)
    monkeypatch.setattr(pattern_sense_refresh, "q", fake_q)

    await pattern_sense_refresh.pattern_sense_refresh("p1")
