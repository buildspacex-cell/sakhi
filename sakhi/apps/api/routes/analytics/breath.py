from __future__ import annotations

from fastapi import APIRouter, Depends

from sakhi.apps.api.core.db import DBSession, get_db

router = APIRouter()


@router.get("/breath_metrics/{person_id}")
async def get_breath_metrics(person_id: str, db: DBSession = Depends(get_db)) -> list[dict[str, float | str]]:
    try:
        rows = await db.fetch(
            """
            SELECT date_trunc('day', start_time) AS day,
                   AVG(avg_breath_rate) AS rate,
                   AVG(calm_score) AS calm
            FROM breath_sessions
            WHERE person_id = $1
              AND start_time > now() - interval '30 days'
            GROUP BY day
            ORDER BY day
            """,
            person_id,
        )
        return [dict(row) for row in rows]
    finally:
        await db.close()


__all__ = ["router"]
