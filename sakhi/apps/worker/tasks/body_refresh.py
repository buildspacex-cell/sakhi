"""Body refresh worker - updates body_state from health data."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from sakhi.apps.api.services.body.state_engine import (
    update_body_state_from_health_data,
    get_body_state,
)

logger = logging.getLogger(__name__)


async def run_body_refresh(person_id: str) -> Dict[str, Any]:
    """
    Refresh body_state for a person from latest health data.

    This worker:
    1. Pulls unprocessed health data from health_data_sync
    2. Aggregates vitals, sleep, activity, etc.
    3. Infers Ayurvedic dosha imbalances
    4. Computes agni, ojas, prana states
    5. Updates personal_model.body_state
    6. Stores snapshot in body_state_history

    Called:
    - After new health data is synced from mobile apps
    - On a schedule (every 15-30 minutes if there's new data)
    - After self-report body check-ins
    """
    logger.info(f"[body_refresh] Starting for person_id={person_id}")

    try:
        body_state = await update_body_state_from_health_data(person_id)

        summary = body_state.get("summary", {})
        logger.info(
            f"[body_refresh] Completed for person_id={person_id}: "
            f"overall_score={summary.get('overall_score')}, "
            f"primary_need={summary.get('primary_need')}, "
            f"confidence={summary.get('confidence')}"
        )

        return {
            "success": True,
            "person_id": person_id,
            "overall_score": summary.get("overall_score"),
            "primary_need": summary.get("primary_need"),
            "dosha_imbalance": body_state.get("dosha_body", {}).get("dominant_imbalance"),
        }

    except Exception as e:
        logger.error(f"[body_refresh] Error for person_id={person_id}: {e}")
        return {
            "success": False,
            "person_id": person_id,
            "error": str(e),
        }


async def run_body_refresh_all() -> Dict[str, Any]:
    """
    Refresh body_state for all persons with unprocessed health data.

    Called by scheduler to batch process health updates.
    """
    from sakhi.apps.api.core.db import dbfetchall

    logger.info("[body_refresh_all] Starting batch refresh")

    # Find persons with unprocessed health data
    rows = await dbfetchall(
        """
        SELECT DISTINCT person_id
        FROM health_data_sync
        WHERE NOT processed
        ORDER BY person_id
        LIMIT 100
        """
    )

    if not rows:
        logger.info("[body_refresh_all] No unprocessed health data")
        return {"success": True, "processed": 0}

    person_ids = [str(row["person_id"]) for row in rows]
    logger.info(f"[body_refresh_all] Processing {len(person_ids)} persons")

    results = []
    for person_id in person_ids:
        result = await run_body_refresh(person_id)
        results.append(result)

    success_count = sum(1 for r in results if r.get("success"))
    error_count = len(results) - success_count

    logger.info(
        f"[body_refresh_all] Completed: {success_count} success, {error_count} errors"
    )

    return {
        "success": True,
        "processed": len(results),
        "success_count": success_count,
        "error_count": error_count,
    }


def body_refresh_task(person_id: str) -> Dict[str, Any]:
    """Synchronous wrapper for RQ worker."""
    return asyncio.run(run_body_refresh(person_id))


def body_refresh_all_task() -> Dict[str, Any]:
    """Synchronous wrapper for scheduled batch refresh."""
    return asyncio.run(run_body_refresh_all())


__all__ = [
    "run_body_refresh",
    "run_body_refresh_all",
    "body_refresh_task",
    "body_refresh_all_task",
]
