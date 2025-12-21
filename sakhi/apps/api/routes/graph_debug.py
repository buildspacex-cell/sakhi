from __future__ import annotations

from fastapi import APIRouter, Depends

from sakhi.apps.api.deps.auth import get_current_user_id
from sakhi.libs.schemas.db import get_async_pool

router = APIRouter(prefix="/debug", tags=["debug"])


@router.get("/graph")
async def graph(user_id: str = Depends(get_current_user_id)):
    pool = await get_async_pool()
    async with pool.acquire() as conn:
        tasks = await conn.fetch("SELECT * FROM tasks WHERE user_id = $1", user_id)
        deps = await conn.fetch(
            """
            SELECT td.*
            FROM task_dependencies td
            JOIN tasks t ON t.id = td.task_id
            WHERE t.user_id = $1
            """,
            user_id,
        )
    return {"tasks": [dict(row) for row in tasks], "deps": [dict(row) for row in deps]}
