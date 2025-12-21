from __future__ import annotations

import os
from typing import Any, Dict, List

import redis
from rq import Queue

from sakhi.apps.api.core.db import q, exec as dbexec
from sakhi.apps.api.core.person_utils import resolve_person_id
from sakhi.apps.engine.task_routing import classify_task, compute_routing


async def run_task_routing(person_id: str) -> Dict[str, Any]:
    person_id = await resolve_person_id(person_id) or person_id
    tasks: List[Dict[str, Any]] = await q(
        """
        SELECT id, title, description, status
        FROM tasks
        WHERE user_id = $1 AND (status IS NULL OR status NOT IN ('done','skipped'))
        """,
        person_id,
    ) or []
    summaries: List[Dict[str, Any]] = []
    for task in tasks:
        text = (task.get("title") or "") + " " + (task.get("description") or "")
        classification = classify_task(text)
        routing = await compute_routing(person_id, {"title": text, "classification": classification})
        routing_state = {
            "category": routing.get("category"),
            "recommended_window": routing.get("recommended_window"),
            "reason": routing.get("reason"),
        }
        summaries.append({"task_id": task.get("id"), **routing_state})
        try:
            await dbexec(
                """
                INSERT INTO task_routing_cache (task_id, person_id, category, recommended_window, reason, forecast_snapshot, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, NOW())
                ON CONFLICT (task_id) DO UPDATE
                SET category = EXCLUDED.category,
                    recommended_window = EXCLUDED.recommended_window,
                    reason = EXCLUDED.reason,
                    forecast_snapshot = EXCLUDED.forecast_snapshot,
                    updated_at = NOW()
                """,
                task.get("id"),
                person_id,
                routing_state.get("category"),
                routing_state.get("recommended_window"),
                routing_state.get("reason"),
                routing.get("forecast_snapshot") or {},
            )
            await dbexec(
                "UPDATE tasks SET routing_state = $2 WHERE id = $1",
                task.get("id"),
                routing_state,
            )
        except Exception:
            continue
    return {"count": len(summaries), "items": summaries}


def enqueue_task_routing(person_id: str) -> None:
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    qobj = Queue(os.getenv("ANALYTICS_QUEUE", "analytics"), connection=redis.from_url(redis_url))
    qobj.enqueue(run_task_routing, person_id)


__all__ = ["run_task_routing", "enqueue_task_routing"]
