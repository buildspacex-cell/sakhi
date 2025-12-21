import pytest

from sakhi.apps.logic.harmony.orchestrator import triage_text, decide_activation


def test_triage_detects_reflection_and_intent():
    behavior = {"conversation_depth": "reflective", "planner_style": "structured"}
    triage = triage_text("Why do I feel tired and what should I plan next?", behavior)
    assert triage["reflective_request"] is True
    assert triage["intent_request"] is True
    assert triage["energy_request"] is True


def test_activation_rules_follow_behavior():
    behavior = {"conversation_depth": "reflective", "planner_style": "structured"}
    triage = {"intent_request": True, "reflective_request": True, "energy_request": False, "identity_focus": False}
    activation = decide_activation(triage, behavior)
    assert activation["planner"] is True
    assert activation["insight"] is True
    assert activation["rhythm"] is False


def test_activation_respects_light_touch_planner():
    behavior = {"conversation_depth": "surface", "planner_style": "light-touch"}
    triage = {"intent_request": True, "reflective_request": False, "energy_request": False, "identity_focus": False}
    activation = decide_activation(triage, behavior)
    assert activation["planner"] is False  # surface + light-touch keeps planner off
