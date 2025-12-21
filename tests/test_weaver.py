import pytest

from sakhi.apps.engine.hands import weaver


def test_classify_time_horizon_keywords():
    assert weaver.classify_time_horizon("Finish report today") == "today"
    assert weaver.classify_time_horizon("Plan for next month") == "month"


def test_energy_cost_and_priority():
    cost = weaver.compute_energy_cost("Deep research on topic", {"summary": "tired"})
    assert cost >= 0.5
    priority = weaver.compute_auto_priority("today", cost, {"summary": "neutral"})
    assert 0.1 <= priority <= 1.0


@pytest.mark.asyncio
async def test_generate_structure_links_parents():
    tasks, content_hash = await weaver.generate_structure("user", "Write summary", {}, {})
    assert len(tasks) == 4
    ids = {t["id"] for t in tasks}
    # ensure parent references exist in set (except anchor None)
    for t in tasks:
        parent = t.get("parent")
        if parent:
            assert parent in ids
    assert content_hash
