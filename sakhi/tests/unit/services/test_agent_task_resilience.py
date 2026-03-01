from unittest.mock import AsyncMock

import pytest

from sakhi.apps.api.services.agent import chat_bridge
from sakhi.apps.api.services.agent import task_orchestrator
from sakhi.apps.api.services.memory import food_memory


@pytest.mark.asyncio
async def test_create_pending_task_persists_pending_confirmation_db_status(monkeypatch: pytest.MonkeyPatch):
    mock_dbexec = AsyncMock()
    monkeypatch.setattr(chat_bridge, "dbexec", mock_dbexec)
    chat_bridge._pending_tasks.clear()

    task = await chat_bridge.create_pending_task(
        person_id="person-1",
        task_type=chat_bridge.AgentTaskType.SHOPPING,
        original_request="Order groceries",
        plan_steps=[{"action": "search", "description": "Find groceries"}],
        context_used={"constraints": []},
    )

    sql = mock_dbexec.await_args.args[0]

    assert task.status == "pending_confirmation"
    assert "pending_confirmation" in sql
    assert "'planned'" not in sql
    chat_bridge._pending_tasks.clear()


@pytest.mark.asyncio
async def test_get_recent_meals_queries_food_experiences_directly(monkeypatch: pytest.MonkeyPatch):
    queries: list[str] = []

    async def fake_dbfetch(sql: str, *args, one: bool = False):
        queries.append(sql)
        return []

    monkeypatch.setattr(food_memory, "dbfetch", fake_dbfetch)

    recent = await food_memory.get_recent_meals("person-1")

    assert recent == []
    assert len(queries) == 1
    assert "FROM food_experiences" in queries[0]


def test_task_orchestrator_keeps_food_memory_out_of_generic_order_flows():
    orchestrator = task_orchestrator.TaskOrchestrator(
        person_id="person-1",
        agent_id="agent-1",
    )

    assert orchestrator._classify_task("Order groceries for tomorrow") == task_orchestrator.TaskType.SHOPPING
    assert orchestrator._classify_task("Order dinner for tonight") == task_orchestrator.TaskType.FOOD
