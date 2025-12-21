from __future__ import annotations

from fastapi import APIRouter, Depends

from sakhi.apps.api.core.db import DBSession, get_db

router = APIRouter()


@router.get("/timeseries/{person_id}")
async def get_timeseries(person_id: str, db: DBSession = Depends(get_db)) -> list[dict[str, float | str]]:
    try:
        rows = await db.fetch(
            """
            SELECT date_trunc('day', r.created_at) AS day,
                   AVG(r.clarity_score) AS clarity,
                   AVG(f.energy_score) AS energy
            FROM reflections AS r
            JOIN rhythm_forecasts AS f USING (person_id)
            WHERE r.person_id = $1
              AND r.created_at > now() - interval '21 days'
            GROUP BY day
            ORDER BY day
            """,
            person_id,
        )
        return [dict(row) for row in rows]
    finally:
        await db.close()


__all__ = ["router"]
