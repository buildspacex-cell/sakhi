from __future__ import annotations

import os

from fastapi import APIRouter, Query
from redis import Redis
from rq import Queue

from sakhi.apps.api.core.db import q as db_fetch, exec as db_exec
from sakhi.apps.worker.tasks.presence_reflection import run_presence_reflection

router = APIRouter(prefix="/presence", tags=["Presence"])


def _presence_queue() -> Queue:
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    return Queue("presence", connection=Redis.from_url(redis_url))


@router.get("/pending")
async def get_pending_prompts(person_id: str = Query(...)):
    rows = await db_fetch(
        """
        SELECT id, theme, message, scheduled_for
        FROM presence_prompts
        WHERE person_id = $1 AND status = 'pending'
        ORDER BY scheduled_for ASC
        """,
        person_id,
    )
    return {"prompts": rows}


@router.post("/mark-delivered/{prompt_id}")
async def mark_delivered(prompt_id: str):
    await db_exec(
        "UPDATE presence_prompts SET status = 'delivered', delivered_at = now() WHERE id = $1",
        prompt_id,
    )
    return {"ok": True}


@router.post("/reflect")
async def trigger_presence_reflection(person_id: str = Query(...)):
    queue = _presence_queue()
    job = queue.enqueue(run_presence_reflection, person_id)
    return {"status": "queued", "job_id": str(job.id)}


__all__ = ["router"]
