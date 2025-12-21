from __future__ import annotations

from fastapi import APIRouter

from sakhi.apps.api.core.db import q
from sakhi.apps.api.schemas.narrative import NarrativeState, AlignmentState

router = APIRouter(prefix="/soul", tags=["soul"])


@router.get("/narrative/{person_id}")
async def get_narrative(person_id: str):
    pm = await q("SELECT soul_narrative FROM personal_model WHERE person_id = $1", person_id, one=True)
    payload = pm.get("soul_narrative") if pm else {}
    return NarrativeState(**(payload or {}))


@router.get("/alignment/{person_id}")
async def get_alignment(person_id: str):
    pm = await q("SELECT alignment_state FROM personal_model WHERE person_id = $1", person_id, one=True)
    payload = pm.get("alignment_state") if pm else {}
    return AlignmentState(**(payload or {}))
