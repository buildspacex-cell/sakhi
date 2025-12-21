from __future__ import annotations

import json
import uuid

from sakhi.libs.schemas.db import get_async_pool


def _coerce_uuid(value: uuid.UUID | str | None) -> uuid.UUID | str | None:
    if isinstance(value, uuid.UUID):
        return value
    if value is None:
        return None
    try:
        return uuid.UUID(value)
    except Exception:
        return value


async def create_event(user_id: str, payload: dict) -> None:
    pool = await get_async_pool()
    user_uuid = _coerce_uuid(user_id)
    async with pool.acquire() as conn:
        payload_json = json.dumps(payload, ensure_ascii=False)
        await conn.execute(
            """
            INSERT INTO events (id, user_id, event_type, payload, occurred_at)
            VALUES (gen_random_uuid(), $1, 'calendar.create', $2::jsonb, now())
            """,
            user_uuid,
            payload_json,
        )


async def update_event_meta(user_id: str, event_id: str, payload: dict) -> None:
    pool = await get_async_pool()
    user_uuid = _coerce_uuid(user_id)
    event_uuid = _coerce_uuid(event_id)
    async with pool.acquire() as conn:
        payload_json = json.dumps(payload, ensure_ascii=False)
        await conn.execute(
            """
            UPDATE events
            SET payload = coalesce(payload, '{}'::jsonb) || $3::jsonb
            WHERE id = $1 AND user_id = $2
            """,
            event_uuid,
            user_uuid,
            payload_json,
        )
