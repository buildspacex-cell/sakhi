from __future__ import annotations

from typing import List

from sakhi.libs.schemas.db import get_async_pool

from .tasks_dao import create_task, ensure_project


async def add_items(user_id: str, list_name: str, items: List[str]) -> None:
    pool = await get_async_pool()
    async with pool.acquire() as conn:
        project_id = await ensure_project(conn, user_id, list_name)
        for item in items:
            await create_task(conn, user_id, project_id, item)
