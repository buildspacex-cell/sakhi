from __future__ import annotations

from fastapi import APIRouter, Query

from sakhi.apps.api.services.reflection.summarizer import summarize_reflections

router = APIRouter(prefix="/reflection-summary", tags=["reflections"])


@router.post("/generate/{person_id}")
async def generate_reflection_summary(
    person_id: str,
    kind: str = Query("weekly", pattern="^(weekly|monthly)$"),
):
    return await summarize_reflections(person_id, kind)


__all__ = ["router"]
