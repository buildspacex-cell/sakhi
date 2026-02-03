import asyncio
import pytest

from sakhi.apps.logic import harmony


@pytest.mark.asyncio
async def test_run_unified_turn_activations(monkeypatch):
    async def fake_brain(person_id, force_refresh=False):
        return {"rhythm_state": {}, "emotional_state": {}, "relationship_state": {}, "environment_state": {}, "habits_state": {}, "focus_state": {}, "identity_state": {}}

    async def fake_insight(person_id, mode="today", behavior_profile=None):
        return {"summary": "ok"}

    monkeypatch.setattr(harmony.orchestrator.brain_engine, "get_brain_state", fake_brain)
    # leave behavior_engine to compute from minimal brain
    monkeypatch.setattr(harmony.orchestrator.insight_engine, "generate_insights", fake_insight)

    result = await harmony.orchestrator.run_unified_turn("person", "help me plan my day")
    activation = result.get("activation") or {}
    assert activation.get("planner") is True
    assert activation.get("insight") is False  # not reflective by default
    # planner payload stays None in orchestrator
    assert result.get("planner") is None


@pytest.mark.asyncio
async def test_run_unified_turn_reflective_calls_insight(monkeypatch):
    async def fake_brain(person_id, force_refresh=False):
        return {"rhythm_state": {}, "emotional_state": {}, "relationship_state": {}, "environment_state": {}, "habits_state": {}, "focus_state": {}, "identity_state": {}}

    call_flag = {"called": False}

    async def fake_insight(person_id, mode="today", behavior_profile=None):
        call_flag["called"] = True
        return {"summary": "reflective"}

    def fake_behavior(brain):
        return {"conversation_depth": "reflective", "planner_style": "structured", "session_context": {"reason": "growth"}}

    monkeypatch.setattr(harmony.orchestrator.brain_engine, "get_brain_state", fake_brain)
    monkeypatch.setattr(harmony.orchestrator.insight_engine, "generate_insights", fake_insight)
    monkeypatch.setattr(harmony.orchestrator, "compute_behavior_profile", fake_behavior)

    result = await harmony.orchestrator.run_unified_turn("person", "why do I feel this way?")
    activation = result.get("activation") or {}
    assert activation.get("insight") is True
    assert call_flag["called"] is True

