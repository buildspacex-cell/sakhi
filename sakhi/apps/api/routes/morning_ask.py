from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, Query

from sakhi.apps.api.core.db import q
from sakhi.apps.api.core.person_utils import resolve_person_id


router = APIRouter(prefix="/v1", tags=["morning-ask"])


@router.get("/morning_ask")
async def get_morning_ask(person_id: str = Query(...)):
    resolved = await resolve_person_id(person_id) or person_id
    today = date.today()
    rows = await q(
        """
        SELECT ask_date, question, reason, generated_at
        FROM morning_ask_cache
        WHERE person_id = $1 AND ask_date = $2
        """,
        resolved,
        today,
    )
    if not rows:
        raise HTTPException(status_code=404, detail="No morning ask generated yet.")
    row = rows[0]
    return {
        "person_id": resolved,
        "ask_date": str(row.get("ask_date")),
        "question": row.get("question") or "",
        "reason": row.get("reason") or "",
        "generated_at": row.get("generated_at"),
    }
