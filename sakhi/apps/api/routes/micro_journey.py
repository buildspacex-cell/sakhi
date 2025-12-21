from __future__ import annotations

from fastapi import APIRouter, HTTPException, Path

from sakhi.apps.api.core.db import q
from sakhi.apps.api.core.person_utils import resolve_person_id

router = APIRouter(prefix="/v1", tags=["micro-journey"])


@router.get("/micro_journey/{person_id}")
async def get_micro_journey(person_id: str = Path(...)) -> dict:
    resolved = await resolve_person_id(person_id) or person_id
    rows = await q(
        """
        SELECT rhythm_slot, flow_count, journey, generated_at
        FROM micro_journey_cache
        WHERE person_id = $1
        """,
        resolved,
    )
    if not rows:
        raise HTTPException(status_code=404, detail="No micro journey generated yet.")
    row = rows[0]
    journey = row.get("journey") or {}
    structure = journey.get("structure") or {}
    return {
        "person_id": resolved,
        "rhythm_slot": row.get("rhythm_slot"),
        "flow_count": row.get("flow_count"),
        "journey": journey,
        "total_estimated_minutes": structure.get("total_estimated_minutes"),
        "pacing": structure.get("pacing") or {},
        "generated_at": row.get("generated_at"),
    }


__all__ = ["router"]
