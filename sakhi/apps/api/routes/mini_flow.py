from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from sakhi.apps.api.core.db import q
from sakhi.apps.api.core.person_utils import resolve_person_id
from sakhi.apps.engine.mini_flow.engine import generate_mini_flow, persist_mini_flow


class MiniFlowIn(BaseModel):
    person_id: str
    intent: Optional[str] = None


router = APIRouter(prefix="/v1", tags=["mini-flow"])


@router.post("/mini_flow")
async def post_mini_flow(body: MiniFlowIn):
    resolved = await resolve_person_id(body.person_id) or body.person_id
    flow = await generate_mini_flow(resolved)
    await persist_mini_flow(resolved, flow)
    return {"person_id": resolved, **flow}


@router.get("/mini_flow")
async def get_mini_flow(person_id: str):
    resolved = await resolve_person_id(person_id) or person_id
    today = date.today()
    rows = await q(
        """
        SELECT flow_date, warmup_step, focus_block_step, closure_step, optional_reward, source, rhythm_slot, generated_at
        FROM mini_flow_cache
        WHERE person_id = $1 AND flow_date = $2
        """,
        resolved,
        today,
    )
    if not rows:
        raise HTTPException(status_code=404, detail="No mini flow generated yet.")
    row = rows[0]
    return {
        "person_id": resolved,
        "flow_date": str(row.get("flow_date")),
        "warmup_step": row.get("warmup_step") or "",
        "focus_block_step": row.get("focus_block_step") or "",
        "closure_step": row.get("closure_step") or "",
        "optional_reward": row.get("optional_reward") or "",
        "source": row.get("source") or "",
        "rhythm_slot": row.get("rhythm_slot"),
        "generated_at": row.get("generated_at"),
    }


__all__ = ["router"]
