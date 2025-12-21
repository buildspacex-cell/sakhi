import asyncio

import pytest

from sakhi.apps.brain import micro_goals
from sakhi.apps.services import micro_goals_service


def test_normalize_intention_removes_prefix():
    assert micro_goals.normalize_intention("I want to Learn Guitar!") == "learn guitar"


def test_extract_micro_steps_returns_atomic_actions():
    steps = micro_goals.extract_micro_steps("I want to learn guitar basics")
    assert 3 <= len(steps) <= 5
    assert all(step["difficulty"] <= 5 for step in steps)


def test_extract_micro_steps_empty_for_emotion_only():
    steps = micro_goals.extract_micro_steps("I feel really tired today")
    assert steps == []


def test_score_confidence_repeated_intent_high():
    steps = micro_goals.extract_micro_steps("I want to learn learn guitar")
    score = micro_goals.score_confidence("I want to learn learn guitar", steps)
    assert score >= 0.8


@pytest.mark.asyncio
async def test_service_blocks_harmful(monkeypatch):
    recorded = {}

    async def fake_exec(*args, **kwargs):
        recorded["called"] = True

    monkeypatch.setattr(micro_goals_service, "dbexec", fake_exec)
    res = await micro_goals_service.create_micro_goals("00000000-0000-0000-0000-000000000000", "I want to buy a weapon")
    assert res["blocked"] is True
    assert res["steps_count"] == 0
