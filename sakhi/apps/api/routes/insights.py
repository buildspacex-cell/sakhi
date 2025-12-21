from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from sakhi.apps.api.core.db import q as db_fetch

router = APIRouter(prefix="/insights", tags=["insights"])


@router.get("/rhythm/latest")
async def get_rhythm_insight(person_id: UUID):
    rows = await db_fetch(
        "SELECT * FROM rhythm_insights WHERE person_id=$1 ORDER BY created_at DESC LIMIT 3",
        person_id,
    )
    return [dict(row) for row in rows]


__all__ = ["router"]
