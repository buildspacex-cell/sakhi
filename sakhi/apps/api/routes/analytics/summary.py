from __future__ import annotations

from fastapi import APIRouter, Depends

from sakhi.apps.api.core.db import DBSession, get_db

router = APIRouter()

_CACHE_TTL = "2 days"


async def _fetch_scalar(db: DBSession, sql: str, *args: str) -> float | None:
    row = await db.fetchrow(sql, *args)
    if not row:
        return None
    return next(iter(row.values()))


async def _fetch_cached_metric(db: DBSession, person_id: str, metric: str) -> float | None:
    row = await db.fetchrow(
        """
        SELECT value
        FROM analytics_cache
        WHERE person_id = $1
          AND metric = $2
          AND computed_at > now() - interval $3
        """,
        person_id,
        metric,
        _CACHE_TTL,
    )
    return row.get("value") if row else None


@router.get("/summary/{person_id}")
async def get_summary(person_id: str, db: DBSession = Depends(get_db)) -> dict[str, float | str]:
    period = "7 days"
    try:
        clarity = await _fetch_cached_metric(db, person_id, "clarity_index")
        if clarity is None:
            clarity = await _fetch_scalar(
                db,
                """
                SELECT AVG(clarity_score)
                FROM reflections
                WHERE person_id = $1 AND created_at > now() - interval $2
                """,
                person_id,
                period,
            )

        energy = await _fetch_cached_metric(db, person_id, "energy_index")
        if energy is None:
            energy = await _fetch_scalar(
                db,
                """
                SELECT AVG(energy_score)
                FROM rhythm_forecasts
                WHERE person_id = $1 AND created_at > now() - interval $2
                """,
                person_id,
                period,
            )

        tone = await _fetch_cached_metric(db, person_id, "dominant_tone")
        if tone is None:
            tone = await _fetch_scalar(
                db,
                """
                SELECT mode() WITHIN GROUP (ORDER BY emotion)
                FROM reflections
                WHERE person_id = $1 AND created_at > now() - interval $2
                """,
                person_id,
                period,
            )

        return {
            "clarity_index": round(float(clarity or 0.0), 2),
            "energy_index": round(float(energy or 0.0), 2),
            "dominant_tone": tone or "neutral",
        }
    finally:
        await db.close()


__all__ = ["router"]
