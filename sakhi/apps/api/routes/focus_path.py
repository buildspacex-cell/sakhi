from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from sakhi.apps.api.core.db import q
from sakhi.apps.api.core.person_utils import resolve_person_id
from sakhi.apps.engine.focus_path.engine import generate_focus_path, persist_focus_path


class FocusPathIn(BaseModel):
    person_id: str
    intent: Optional[str] = None


router = APIRouter(prefix="/v1", tags=["focus-path"])


@router.post("/focus_path")
async def post_focus_path(body: FocusPathIn):
    resolved = await resolve_person_id(body.person_id) or body.person_id
    path = await generate_focus_path(resolved, intent_text=body.intent)
    await persist_focus_path(resolved, path)
    return {
        "person_id": resolved,
        **path,
    }


@router.get("/focus_path")
async def get_focus_path(person_id: str):
    resolved = await resolve_person_id(person_id) or person_id
    today = date.today()
    rows = await q(
        """
        SELECT path_date, anchor_step, progress_step, closure_step, intent_source, generated_at
        FROM focus_path_cache
        WHERE person_id = $1 AND path_date = $2
        """,
        resolved,
        today,
    )
    if not rows:
        raise HTTPException(status_code=404, detail="No focus path generated yet.")
    row = rows[0]
    return {
        "person_id": resolved,
        "path_date": str(row.get("path_date")),
        "anchor_step": row.get("anchor_step") or "",
        "progress_step": row.get("progress_step") or "",
        "closure_step": row.get("closure_step") or "",
        "intent_source": row.get("intent_source") or "",
        "generated_at": row.get("generated_at"),
    }


__all__ = ["router"]
