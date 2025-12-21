from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, Query

from sakhi.apps.api.core.db import q
from sakhi.apps.api.core.person_utils import resolve_person_id


router = APIRouter(prefix="/v1", tags=["evening-closure"])


@router.get("/evening_closure")
async def get_evening_closure(person_id: str = Query(...)):
    resolved = await resolve_person_id(person_id) or person_id
    today = date.today()
    rows = await q(
        """
        SELECT closure_date, completed, pending, signals, summary, generated_at
        FROM daily_closure_cache
        WHERE person_id = $1 AND closure_date = $2
        """,
        resolved,
        today,
    )
    if not rows:
        raise HTTPException(status_code=404, detail="No evening closure generated yet.")
    row = rows[0]
    return {
        "person_id": resolved,
        "closure_date": str(row.get("closure_date")),
        "completed": row.get("completed") or [],
        "pending": row.get("pending") or [],
        "signals": row.get("signals") or {},
        "summary": row.get("summary") or "",
        "generated_at": row.get("generated_at"),
    }
