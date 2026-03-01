import asyncio
from unittest.mock import AsyncMock

import pytest

from scripts.run_demo_personas import DemoPersonaRunner


def _make_runner() -> DemoPersonaRunner:
    return DemoPersonaRunner(
        persona={"id": "test"},
        user_id="test-user",
        db_query=AsyncMock(),
        db_exec=AsyncMock(),
    )


@pytest.mark.asyncio
async def test_drain_background_tasks_waits_for_spawned_children(monkeypatch: pytest.MonkeyPatch):
    runner = _make_runner()
    reset_pool = AsyncMock()
    monkeypatch.setattr(runner, "_reset_db_pool", reset_pool)

    spawned: list[asyncio.Task] = []

    async def child() -> None:
        await asyncio.sleep(0.01)

    async def parent() -> None:
        await asyncio.sleep(0)
        spawned.append(asyncio.create_task(child()))

    runner._tasks_before_turn = runner._snapshot_tasks()
    parent_task = asyncio.create_task(parent())

    await runner._drain_background_tasks(timeout=1.0)

    assert parent_task.done()
    assert spawned
    assert all(task.done() for task in spawned)
    reset_pool.assert_not_awaited()


@pytest.mark.asyncio
async def test_drain_background_tasks_resets_db_pool_after_timeout(monkeypatch: pytest.MonkeyPatch):
    runner = _make_runner()
    reset_pool = AsyncMock()
    monkeypatch.setattr(runner, "_reset_db_pool", reset_pool)

    blocker = asyncio.Event()

    async def stuck() -> None:
        await blocker.wait()

    runner._tasks_before_turn = runner._snapshot_tasks()
    stuck_task = asyncio.create_task(stuck())

    await runner._drain_background_tasks(timeout=0.01)

    assert stuck_task.done()
    assert stuck_task.cancelled()
    reset_pool.assert_awaited_once()
