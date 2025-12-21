from __future__ import annotations

import uuid
from typing import Any, List, Optional

from sakhi.libs.schemas.db import get_async_pool


def _to_uuid(val: Optional[str | uuid.UUID]) -> Optional[uuid.UUID | str]:
    if val is None or isinstance(val, uuid.UUID):
        return val
    try:
        return uuid.UUID(val)
    except Exception:
        return val


async def ensure_project(conn, user_id: str, name: str) -> str:
    user_uuid = _to_uuid(user_id)
    row = await conn.fetchrow(
        """
        INSERT INTO projects (id, user_id, name, status)
        VALUES (gen_random_uuid(), $1, $2, 'active')
        ON CONFLICT (user_id, name) DO UPDATE SET name = EXCLUDED.name
        RETURNING id
        """,
        user_uuid,
        name,
    )
    return row["id"]


async def get_tasks(conn, user_id: str) -> List[dict]:
    user_uuid = _to_uuid(user_id)
    rows = await conn.fetch(
        "SELECT * FROM tasks WHERE user_id = $1 ORDER BY order_index, created_at",
        user_uuid,
    )
    return [dict(row) for row in rows]


async def get_deps(conn, user_id: str) -> List[dict]:
    user_uuid = _to_uuid(user_id)
    rows = await conn.fetch(
        """
        SELECT td.*
        FROM task_dependencies td
        JOIN tasks t ON t.id = td.task_id
        WHERE t.user_id = $1
        """,
        user_uuid,
    )
    return [dict(row) for row in rows]


async def create_task(
    conn,
    user_id: str,
    project_id: str,
    title: str,
    due: Optional[str] = None,
    notes: Optional[str] = None,
    parent_task_id: Optional[str] = None,
) -> dict[str, Any]:
    user_uuid = _to_uuid(user_id)
    project_uuid = _to_uuid(project_id)
    parent_uuid = _to_uuid(parent_task_id)
    row = await conn.fetchrow(
        """
        INSERT INTO tasks (
            id,
            user_id,
            project_id,
            parent_task_id,
            title,
            description,
            due_at,
            status
        )
        VALUES (gen_random_uuid(), $1, $2, $3, $4, $5, $6, 'todo')
        RETURNING *
        """,
        user_uuid,
        project_uuid,
        parent_uuid,
        title,
        notes,
        due,
    )
    return dict(row)


async def update_task_status(conn, user_id: str, task_id: str, status: str) -> None:
    user_uuid = _to_uuid(user_id)
    task_uuid = _to_uuid(task_id)
    await conn.execute(
        "UPDATE tasks SET status = $1 WHERE id = $2 AND user_id = $3",
        status,
        task_uuid,
        user_uuid,
    )


async def add_dependency(
    conn,
    user_id: str,
    task_id: str,
    depends_on_task_id: str,
    hard: bool = False,
) -> None:
    user_uuid = _to_uuid(user_id)
    task_uuid = _to_uuid(task_id)
    depends_uuid = _to_uuid(depends_on_task_id)
    await conn.execute(
        """
        INSERT INTO task_dependencies (task_id, depends_on_task_id, hard)
        SELECT $1, $2, $3
        WHERE EXISTS (SELECT 1 FROM tasks WHERE id = $1 AND user_id = $4)
          AND EXISTS (SELECT 1 FROM tasks WHERE id = $2 AND user_id = $4)
        """,
        task_uuid,
        depends_uuid,
        hard,
        user_uuid,
    )


async def remove_dependency(conn, user_id: str, task_id: str, depends_on_task_id: str) -> None:
    user_uuid = _to_uuid(user_id)
    task_uuid = _to_uuid(task_id)
    depends_uuid = _to_uuid(depends_on_task_id)
    await conn.execute(
        """
        DELETE FROM task_dependencies
        USING tasks t
        WHERE task_dependencies.task_id = $1
          AND task_dependencies.depends_on_task_id = $2
          AND t.id = task_dependencies.task_id
          AND t.user_id = $3
        """,
        task_uuid,
        depends_uuid,
        user_uuid,
    )


async def with_conn(fn, *args, **kwargs):
    pool = await get_async_pool()
    async with pool.acquire() as conn:
        return await fn(conn, *args, **kwargs)
