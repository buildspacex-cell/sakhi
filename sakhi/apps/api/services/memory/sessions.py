from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

MAX_ACTIVE_SESSIONS = 6

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


async def ensure_session(user_id: str, slug: str = "journal") -> str:
    pool = await get_async_pool()
    user_uuid = _coerce_uuid(user_id)
    async with pool.acquire() as conn:
        existing = await conn.fetchrow(
            "SELECT id, status FROM conversation_sessions WHERE user_id = $1 AND slug = $2",
            user_uuid,
            slug,
        )
        if existing:
            session_id = existing["id"]
            await conn.execute(
                "UPDATE conversation_sessions SET status = 'active', last_active_at = now() WHERE id = $1",
                session_id,
            )
            return session_id

        active_count = await conn.fetchval(
            "SELECT COUNT(*) FROM conversation_sessions WHERE user_id = $1 AND status = 'active'",
            user_uuid,
        )
        if active_count >= MAX_ACTIVE_SESSIONS:
            await conn.execute(
                """
                WITH oldest AS (
                    SELECT id
                    FROM conversation_sessions
                    WHERE user_id = $1 AND status = 'active'
                    ORDER BY COALESCE(last_active_at, created_at) ASC
                    LIMIT 1
                )
                UPDATE conversation_sessions
                SET status = 'archived', archived_at = now()
                WHERE id IN (SELECT id FROM oldest)
                """,
                user_uuid,
            )

        row = await conn.fetchrow(
            """
            INSERT INTO conversation_sessions (id, user_id, slug, status, last_active_at, turn_count)
            VALUES (gen_random_uuid(), $1, $2, 'active', now(), 0)
            RETURNING id
            """,
            user_uuid,
            slug,
        )
        return row["id"]


async def append_turn(
    user_id: str,
    session_id: str,
    role: str,
    text: str,
    tone: Optional[str] = None,
    archetype: Optional[str] = None,
) -> None:
    pool = await get_async_pool()
    user_uuid = _coerce_uuid(user_id)
    session_uuid = _coerce_uuid(session_id)
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO conversation_turns (id, user_id, session_id, role, text, tone, archetype)
            VALUES (gen_random_uuid(), $1, $2, $3, $4, $5, $6)
            """,
            user_uuid,
            session_uuid,
            role,
            text,
            tone,
            archetype,
        )
        await conn.execute(
            """
            UPDATE conversation_sessions
            SET last_active_at = now(), turn_count = COALESCE(turn_count, 0) + 1
            WHERE id = $1
            """,
            session_uuid,
        )


async def load_recent_turns(session_id: str, limit: int = 12) -> List[Dict]:
    pool = await get_async_pool()
    session_uuid = _coerce_uuid(session_id)
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT role, text, tone, archetype
            FROM conversation_turns
            WHERE session_id = $1
            ORDER BY created_at DESC
            LIMIT $2
            """,
            session_uuid,
            limit,
        )
    return [dict(row) for row in reversed(rows)]


async def get_summary(session_id: str) -> str:
    pool = await get_async_pool()
    session_uuid = _coerce_uuid(session_id)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT summary FROM session_summaries WHERE session_id = $1",
            session_uuid,
        )
    return row["summary"] if row else ""


async def set_summary(session_id: str, summary: str) -> None:
    pool = await get_async_pool()
    session_uuid = _coerce_uuid(session_id)
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO session_summaries (session_id, summary, last_updated)
            VALUES ($1, $2, now())
            ON CONFLICT (session_id)
            DO UPDATE SET summary = EXCLUDED.summary, last_updated = now()
            """,
            session_uuid,
            summary,
        )


async def get_session_info(session_id: str) -> Dict[str, Any]:
    pool = await get_async_pool()
    session_uuid = _coerce_uuid(session_id)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, user_id, slug, title, status FROM conversation_sessions WHERE id = $1",
            session_uuid,
        )
    return dict(row) if row else {}


async def set_session_title(session_id: str, title: str) -> None:
    pool = await get_async_pool()
    session_uuid = _coerce_uuid(session_id)
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE conversation_sessions SET title = $2 WHERE id = $1",
            session_uuid,
            title,
        )
