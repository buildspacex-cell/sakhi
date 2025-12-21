from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, Query

from sakhi.apps.api.core.db import q
from sakhi.apps.api.core.person_utils import resolve_person_id


router = APIRouter(prefix="/v1", tags=["morning-preview"])


@router.get("/morning_preview")
async def get_morning_preview(person_id: str = Query(...)):
    resolved = await resolve_person_id(person_id) or person_id
    today = date.today()
    rows = await q(
        """
        SELECT preview_date, focus_areas, key_tasks, reminders, rhythm_hint, summary, generated_at
        FROM morning_preview_cache
        WHERE person_id = $1 AND preview_date = $2
        """,
        resolved,
        today,
    )
    if not rows:
        raise HTTPException(status_code=404, detail="No morning preview generated yet.")
    row = rows[0]
    return {
        "person_id": resolved,
        "preview_date": str(row.get("preview_date")),
        "focus_areas": row.get("focus_areas") or [],
        "key_tasks": row.get("key_tasks") or [],
        "reminders": row.get("reminders") or [],
        "rhythm_hint": row.get("rhythm_hint") or "",
        "summary": row.get("summary") or "",
        "generated_at": row.get("generated_at"),
    }
