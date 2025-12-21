from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from sakhi.apps.api.core.db import q
from sakhi.apps.api.deps.auth import get_current_user_id
from sakhi.apps.api.core.person_utils import resolve_person_id

router = APIRouter(prefix="/v1/nudge", tags=["nudge"])


@router.get("/log")
async def list_nudges(person_id: str | None = None, user_id: str = Depends(get_current_user_id)):
    resolved = await resolve_person_id(person_id or user_id)
    if not resolved:
        raise HTTPException(status_code=400, detail="Invalid user")
    rows = await q(
        """
        SELECT category, message, forecast_snapshot, sent_at
        FROM nudge_log
        WHERE person_id = $1
        ORDER BY sent_at DESC
        LIMIT 20
        """,
        resolved,
    )
    return {"items": rows or []}
