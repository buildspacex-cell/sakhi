from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, Query

from sakhi.apps.api.core.db import q
from sakhi.apps.api.core.person_utils import resolve_person_id


router = APIRouter(prefix="/v1", tags=["morning-momentum"])


@router.get("/morning_momentum")
async def get_morning_momentum(person_id: str = Query(...)):
    resolved = await resolve_person_id(person_id) or person_id
    today = date.today()
    rows = await q(
        """
        SELECT momentum_date, momentum_hint, suggested_start, reason, generated_at
        FROM morning_momentum_cache
        WHERE person_id = $1 AND momentum_date = $2
        """,
        resolved,
        today,
    )
    if not rows:
        raise HTTPException(status_code=404, detail="No morning momentum generated yet.")
    row = rows[0]
    return {
        "person_id": resolved,
        "momentum_date": str(row.get("momentum_date")),
        "momentum_hint": row.get("momentum_hint") or "",
        "suggested_start": row.get("suggested_start") or "",
        "reason": row.get("reason") or "",
        "generated_at": row.get("generated_at"),
    }
