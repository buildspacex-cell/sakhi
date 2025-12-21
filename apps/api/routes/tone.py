from __future__ import annotations

import os

from fastapi import APIRouter, Query
from redis import Redis
from rq import Queue

from sakhi.apps.worker.tasks.tone_continuity import run_tone_continuity

router = APIRouter(prefix="/tone", tags=["Tone"])


def _reflection_queue() -> Queue:
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    return Queue(os.getenv("TONE_QUEUE", "reflection"), connection=Redis.from_url(redis_url))


@router.post("/refresh")
async def trigger_tone_refresh(person_id: str = Query(...)):
    queue = _reflection_queue()
    job = queue.enqueue(run_tone_continuity, person_id)
    return {"status": "queued", "job_id": str(job.id)}


__all__ = ["router"]
