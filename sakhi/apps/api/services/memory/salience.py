from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

from sakhi.libs.schemas.db import get_async_pool


def _to_uuid(val: Optional[str | uuid.UUID]) -> Optional[uuid.UUID | str]:
    if val is None or isinstance(val, uuid.UUID):
        return val
    try:
        return uuid.UUID(val)
    except Exception:
        return val


async def upsert_memory(
    user_id: str,
    session_id: Optional[str],
    kind: str,
    key: str,
    value: Dict[str, Any],
    salience: float = 0.7,
) -> None:
    pool = await get_async_pool()
    user_uuid = _to_uuid(user_id)
    session_uuid = _to_uuid(session_id)
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO salient_memories (id, user_id, session_id, kind, key, value, salience)
            VALUES (gen_random_uuid(), $1, $2, $3, $4, $5::jsonb, $6)
            """,
            user_uuid,
            session_uuid,
            kind,
            key,
            value,
            salience,
        )


async def load_memories(user_id: str, kinds: list[str]) -> dict:
    pool = await get_async_pool()
    user_uuid = _to_uuid(user_id)
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT kind, key, value
            FROM salient_memories
            WHERE user_id = $1 AND kind = ANY($2::text[])
            ORDER BY salience DESC
            LIMIT 50
            """,
            user_uuid,
            kinds,
        )
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        out.setdefault(row["kind"], {})[row["key"]] = row["value"]
    return out
