from __future__ import annotations

import json
import os
from typing import Optional

from redis import Redis
from rq import Queue

from sakhi.apps.api.services.observe.models import ObserveJobPayload

_QUEUE_NAME = os.getenv("OBSERVE_PIPELINE_QUEUE", "observe")
_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
_JOB_TIMEOUT = int(os.getenv("OBSERVE_PIPELINE_TIMEOUT", "600"))

_redis_connection: Redis | None = None


def _get_queue() -> Queue:
    global _redis_connection
    if _redis_connection is None:
        _redis_connection = Redis.from_url(_REDIS_URL)
    return Queue(_QUEUE_NAME, connection=_redis_connection)


def enqueue_observe_job(payload: ObserveJobPayload) -> Optional[str]:
    """Push the observe pipeline job to the worker queue."""

    queue = _get_queue()
    job = queue.enqueue(
        "sakhi.apps.worker.pipelines.observe_pipeline.runner.run_pipeline_job",
        kwargs={"payload": payload.to_dict()},
        job_timeout=_JOB_TIMEOUT,
    )
    return job.id


__all__ = ["enqueue_observe_job"]
