from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Query, HTTPException

from sakhi.apps.api.core.db import q
from sakhi.apps.api.core.person_utils import resolve_person_id


router = APIRouter(prefix="/v1", tags=["daily-reflection"])


@router.get("/daily_reflection")
async def get_daily_reflection(person_id: str = Query(...)):
    resolved = await resolve_person_id(person_id) or person_id
    today = date.today()
    rows = await q(
        """
        SELECT reflection_date, summary, generated_at
        FROM daily_reflection_cache
        WHERE person_id = $1 AND reflection_date = $2
        """,
        resolved,
        today,
    )
    if not rows:
        raise HTTPException(status_code=404, detail="No reflection generated yet.")
    row = rows[0]
    return {
        "person_id": resolved,
        "reflected_on": str(row.get("reflection_date")),
        "summary": row.get("summary"),
        "generated_at": row.get("generated_at"),
    }
