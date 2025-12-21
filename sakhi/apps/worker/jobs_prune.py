"""Prune low-salience journal entries by marking them hidden."""

from __future__ import annotations

from typing import Any, Dict

from sakhi.libs.schemas.db import get_async_pool


async def prune_low_salience(user_id: str, keep: int = 500) -> Dict[str, Any]:
    pool = await get_async_pool()
    async with pool.acquire() as connection:
        rows = await connection.fetch(
            """
            SELECT id
            FROM journal_entries
            WHERE user_id = $1
            ORDER BY COALESCE((facets_v2->>'sentiment')::float, 0) DESC,
                     COALESCE((facets->>'salience')::float, 0) DESC,
                     created_at DESC
            OFFSET $2
            """,
            user_id,
            keep,
        )
        ids = [row["id"] for row in rows]
        if ids:
            await connection.executemany(
                """
                INSERT INTO journal_inference (entry_id, container, payload, inference_type, source)
                VALUES ($1, 'context', jsonb_build_object('hidden', true), 'structural', 'jobs_prune')
                """,
                [(entry_id,) for entry_id in ids],
            )
    return {"hidden": len(ids)}
