from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, Query

from sakhi.apps.api.core.db import q
from sakhi.apps.api.core.person_utils import resolve_person_id


router = APIRouter(prefix="/v1", tags=["micro-momentum"])


@router.get("/micro_momentum")
async def get_micro_momentum(person_id: str = Query(...)):
    resolved = await resolve_person_id(person_id) or person_id
    today = date.today()
    rows = await q(
        """
        SELECT nudge_date, nudge, reason, generated_at
        FROM micro_momentum_cache
        WHERE person_id = $1 AND nudge_date = $2
        """,
        resolved,
        today,
    )
    if not rows:
        raise HTTPException(status_code=404, detail="No micro momentum generated yet.")
    row = rows[0]
    return {
        "person_id": resolved,
        "nudge_date": str(row.get("nudge_date")),
        "nudge": row.get("nudge") or "",
        "reason": row.get("reason") or "",
        "generated_at": row.get("generated_at"),
    }


__all__ = ["router"]
