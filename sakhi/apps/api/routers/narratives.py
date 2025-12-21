from __future__ import annotations

from fastapi import APIRouter, Query

from sakhi.apps.api.services.narratives.episodic import generate_episodic_narrative

router = APIRouter(prefix="/narratives", tags=["narratives"])


@router.post("/generate/{person_id}")
async def generate_narrative(
    person_id: str,
    kind: str = Query("weekly", pattern="^(weekly|monthly)$"),
):
    """
    Generate and persist an episodic narrative for a user.
    """

    return await generate_episodic_narrative(person_id, kind=kind)


__all__ = ["router"]
