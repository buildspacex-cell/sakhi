from __future__ import annotations

from fastapi import APIRouter, Query

router = APIRouter(prefix="/presence", tags=["Presence"])


@router.get("/pending")
async def get_pending_prompts(person_id: str = Query(...)):
    # Placeholder implementation for monorepo-local API build.
    return {"prompts": []}


@router.post("/mark-delivered/{prompt_id}")
async def mark_delivered(prompt_id: str):
    # Stubbed response; data store is not wired in this container.
    return {"ok": True, "prompt_id": prompt_id}


@router.post("/reflect")
async def trigger_presence_reflection(person_id: str = Query(...)):
    # Queue/workers are not available in this trimmed container build.
    return {"status": "queued", "person_id": person_id}


__all__ = ["router"]
