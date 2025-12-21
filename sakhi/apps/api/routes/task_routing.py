from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from sakhi.apps.api.deps.auth import get_current_user_id
from sakhi.apps.api.core.person_utils import resolve_person_id
from sakhi.apps.api.core.db import q


router = APIRouter(prefix="/v1/tasks", tags=["tasks-routing"])


@router.get("/routing")
async def list_routing(person_id: str | None = None, user_id: str = Depends(get_current_user_id)):
    resolved = await resolve_person_id(person_id or user_id)
    if not resolved:
        raise HTTPException(status_code=400, detail="Invalid user")
    rows = await q(
        """
        SELECT task_id, category, recommended_window, reason, forecast_snapshot, updated_at
        FROM task_routing_cache
        WHERE person_id = $1
        ORDER BY updated_at DESC
        """,
        resolved,
    )
    return {"items": rows or []}

