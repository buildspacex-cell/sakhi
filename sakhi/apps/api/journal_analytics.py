"""Journal analytics endpoints for themes and trends."""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from sakhi.libs.schemas.db import get_async_pool

jr = APIRouter(prefix="/journal")


@jr.get("/themes")
async def themes(user_id: str, window: str = "week") -> Dict[str, Any]:
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")

    if window not in {"week", "month"}:
        raise HTTPException(status_code=400, detail="window must be 'week' or 'month'")

    if window == "week":
        sql = """
        SELECT date_part('year', created_at) || '-W' || to_char(created_at, 'IW') AS bucket,
               array_remove(array_agg(DISTINCT unnest(coalesce(facets_v2->'tags'::text[]) )), NULL) AS tags
        FROM journal_entries
        WHERE user_id = $1
        GROUP BY bucket
        ORDER BY bucket DESC
        LIMIT 8
        """
    else:
        sql = """
        SELECT to_char(created_at, 'YYYY-MM') AS bucket,
               array_remove(array_agg(DISTINCT unnest(coalesce(facets_v2->'tags'::text[]) )), NULL) AS tags
        FROM journal_entries
        WHERE user_id = $1
        GROUP BY bucket
        ORDER BY bucket DESC
        LIMIT 6
        """

    pool = await get_async_pool()
    async with pool.acquire() as connection:
        rows = await connection.fetch(sql, user_id)
    return {"buckets": [dict(row) for row in rows]}


@jr.get("/trends")
async def trends(user_id: str, days: int = 30) -> Dict[str, Any]:
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    if days <= 0:
        raise HTTPException(status_code=400, detail="days must be positive")

    pool = await get_async_pool()
    async with pool.acquire() as connection:
        rows = await connection.fetch(
            """
            SELECT date_trunc('day', created_at) AS day,
                   AVG(COALESCE((facets_v2->>'sentiment')::float, 0)) AS avg_sentiment,
                   COUNT(*) AS entries
            FROM journal_entries
            WHERE user_id = $1 AND created_at >= now() - ($2 || ' days')::interval
            GROUP BY day
            ORDER BY day
            """,
            user_id,
            days,
        )

    series = [
        {
            "day": row["day"].date().isoformat(),
            "avg_sentiment": float(row["avg_sentiment"] or 0.0),
            "entries": int(row["entries"] or 0),
        }
        for row in rows
    ]
    return {"series": series}
