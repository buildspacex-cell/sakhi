from __future__ import annotations

import os
from typing import Any, Dict, Iterable

from redis import Redis
from rq import Queue

_QUEUE_NAME = os.getenv("TURN_JOBS_QUEUE", "turn_updates")
_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
_JOB_TIMEOUT = int(os.getenv("TURN_JOBS_TIMEOUT", "300"))

_redis_connection: Redis | None = None


def _get_queue() -> Queue:
    global _redis_connection
    if _redis_connection is None:
        _redis_connection = Redis.from_url(_REDIS_URL)
    return Queue(_QUEUE_NAME, connection=_redis_connection)


def enqueue_turn_jobs(turn_id: str, person_id: str, jobs: Iterable[str], payload: Dict[str, Any]) -> None:
    """Schedule optional async jobs for a processed turn."""

    queue = _get_queue()
    payload = dict(payload)
    payload.setdefault("thread_id", person_id)  # default continuity per person if not set
    for job_type in jobs:
        queue.enqueue(
            "sakhi.apps.worker.pipelines.turn_updates.runner.process_turn_job",
            kwargs={
                "job_type": job_type,
                "turn_id": turn_id,
                "person_id": person_id,
                "payload": payload,
            },
            job_timeout=_JOB_TIMEOUT,
        )


__all__ = ["enqueue_turn_jobs"]
