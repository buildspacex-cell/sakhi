from __future__ import annotations

import datetime as dt
import os
from typing import Any, Dict

from rq import Queue
import redis

from sakhi.apps.api.core.db import q, exec as dbexec
from sakhi.apps.engine.nudge import compute_nudge
from sakhi.apps.api.core.person_utils import resolve_person_id


async def _send_nudge_message(person_id: str, message: str) -> None:
    """Placeholder for posting a system nudge into conversation feed."""
    try:
        await dbexec(
            """
            INSERT INTO nudge_log (person_id, category, message, forecast_snapshot, sent_at)
            VALUES ($1, $2, $3, '{}'::jsonb, NOW())
            """,
            person_id,
            "info",
            message,
        )
    except Exception:
        return


async def run_nudge_check(person_id: str) -> Dict[str, Any]:
    person_id = await resolve_person_id(person_id) or person_id
    forecast_row = await q(
        "SELECT forecast_state FROM forecast_cache WHERE person_id = $1",
        person_id,
        one=True,
    ) or {}
    pm_row = await q(
        "SELECT tone_state, nudge_state FROM personal_model WHERE person_id = $1",
        person_id,
        one=True,
    ) or {}
    tone_state = pm_row.get("tone_state") or {}
    forecast_state = forecast_row.get("forecast_state") or {}

    nudge = await compute_nudge(person_id, forecast_state, tone_state)
    if not nudge.get("should_send"):
        return nudge

    category = nudge.get("category") or "general"
    message = nudge.get("message") or ""
    try:
        await dbexec(
            """
            INSERT INTO nudge_log (person_id, category, message, forecast_snapshot, sent_at)
            VALUES ($1, $2, $3, $4, NOW())
            """,
            person_id,
            category,
            message,
            nudge.get("forecast_snapshot") or {},
        )
        await dbexec(
            """
            UPDATE personal_model
            SET nudge_state = $2
            WHERE person_id = $1
            """,
            person_id,
            {
                "last_category": category,
                "last_message": message,
                "last_sent_at": dt.datetime.utcnow().isoformat(),
            },
        )
    except Exception:
        # best effort
        pass

    try:
        await _send_nudge_message(person_id, message)
    except Exception:
        pass

    return nudge


def enqueue_nudge(person_id: str) -> None:
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    qobj = Queue("analytics", connection=redis.from_url(redis_url))
    qobj.enqueue(run_nudge_check, person_id)


__all__ = ["run_nudge_check", "enqueue_nudge"]
