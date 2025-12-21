from __future__ import annotations

import asyncio
import logging

from sakhi.apps.api.core.db import q, exec as dbexec
from sakhi.apps.engine.hands import weaver

logger = logging.getLogger(__name__)


async def task_weaver_refresh(person_id: str) -> None:
    """
    Recompute auto_priority for today's atoms based on stored signals.
    Best-effort; failures are logged and ignored.
    """
    try:
        rows = await q(
            """
            SELECT id, title, inferred_time_horizon, emotional_fit
            FROM tasks
            WHERE user_id = $1 AND (inferred_time_horizon IS NULL OR inferred_time_horizon = 'today')
            """,
            person_id,
        )
    except Exception as exc:
        logger.warning("task_weaver_refresh load failed person=%s err=%s", person_id, exc)
        return

    for row in rows or []:
        horizon = row.get("inferred_time_horizon") or "today"
        emotion_state = {"summary": row.get("emotional_fit")} if row.get("emotional_fit") else {}
        energy_cost = weaver.compute_energy_cost(row.get("title") or "", emotion_state)
        priority = weaver.compute_auto_priority(horizon, energy_cost, emotion_state)
        try:
            await dbexec(
                """
                UPDATE tasks
                SET energy_cost = $2, auto_priority = $3, inferred_time_horizon = COALESCE(inferred_time_horizon, $4)
                WHERE id = $1
                """,
                row["id"],
                energy_cost,
                priority,
                horizon,
            )
        except Exception as exc:
            logger.warning("task_weaver_refresh update failed task=%s err=%s", row["id"], exc)


def enqueue_task_weaver_refresh(person_id: str) -> None:
    try:
        asyncio.create_task(task_weaver_refresh(person_id))
    except Exception:
        # async context might be absent in worker threads; ignore
        pass


__all__ = ["task_weaver_refresh", "enqueue_task_weaver_refresh"]
