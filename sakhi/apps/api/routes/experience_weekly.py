from __future__ import annotations

import datetime as dt
import logging
import time
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from sakhi.apps.api.core.db import q
from sakhi.apps.worker.tasks.weekly_rhythm_rollup_worker import (
    run_weekly_rhythm_rollup,
)
from sakhi.apps.worker.tasks.weekly_planner_pressure_worker import (
    run_weekly_planner_pressure,
)
from sakhi.apps.worker.tasks.weekly_signals_worker import (
    run_weekly_signals_worker,
)
from sakhi.apps.worker.tasks.turn_personal_model_update import (
    run_turn_personal_model_update,
)
from sakhi.apps.worker.tasks.weekly_reflection import generate_weekly_reflection
from sakhi.libs.schemas.settings import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/experience", tags=["experience-weekly"])


def _week_bounds(reference: dt.date | None = None) -> tuple[dt.date, dt.date]:
    today = reference or dt.datetime.utcnow().date()
    monday = today - dt.timedelta(days=today.weekday())
    sunday = monday + dt.timedelta(days=6)
    return monday, sunday


@router.get("/weekly")
async def experience_weekly(person_id: str) -> Dict[str, Any]:
    settings = get_settings()
    logger.error("WEEKLY_DEBUG: endpoint entered", extra={"person_id": person_id})
    logger.error("WEEKLY_DEBUG: DEBUG_WEEKLY_PIPELINE=%s", settings.debug_weekly_pipeline)
    week_start, week_end = _week_bounds()
    if not person_id:
        raise HTTPException(status_code=400, detail="person_id is required")

    try:
        if settings.debug_weekly_pipeline:
            timings: Dict[str, float] = {}
            start = time.perf_counter()
            logger.error("WEEKLY_DEBUG: starting weekly_rhythm_rollup_worker")
            await run_weekly_rhythm_rollup(person_id)
            logger.error("WEEKLY_DEBUG: finished weekly_rhythm_rollup_worker")
            timings["rhythm_ms"] = (time.perf_counter() - start) * 1000

            start = time.perf_counter()
            logger.error("WEEKLY_DEBUG: starting weekly_planner_pressure_worker")
            await run_weekly_planner_pressure(person_id)
            logger.error("WEEKLY_DEBUG: finished weekly_planner_pressure_worker")
            timings["planner_ms"] = (time.perf_counter() - start) * 1000

            start = time.perf_counter()
            logger.error("WEEKLY_DEBUG: starting weekly_signals_worker")
            await run_weekly_signals_worker(person_id)
            logger.error("WEEKLY_DEBUG: finished weekly_signals_worker")
            timings["signals_ms"] = (time.perf_counter() - start) * 1000

            start = time.perf_counter()
            logger.error("WEEKLY_DEBUG: starting turn_personal_model_update")
            await run_turn_personal_model_update(person_id)
            logger.error("WEEKLY_DEBUG: finished turn_personal_model_update")
            timings["personal_model_ms"] = (time.perf_counter() - start) * 1000

            row = await q(
                "SELECT longitudinal_state FROM personal_model WHERE person_id = $1",
                person_id,
                one=True,
            )
            longitudinal_state = row.get("longitudinal_state") if row else {}

            logger.error("WEEKLY_DEBUG: starting weekly_reflection render")
            reflection = await generate_weekly_reflection(person_id, longitudinal_state or {})
            logger.error("WEEKLY_DEBUG: finished weekly_reflection render")
            reflection["window"] = f"{week_start.isoformat()} \u2192 {week_end.isoformat()}"

            timings["total_ms"] = sum(timings.values())

            logger.error("WEEKLY_DEBUG: returning response")
            return {
                "status": "ok",
                "person_id": person_id,
                "week_start": week_start.isoformat(),
                "week_end": week_end.isoformat(),
                "reflection": reflection,
                "timing": timings,
            }

        logger.error("WEEKLY_DEBUG: returning pending response (non-debug)")
        return {
            "status": "pending",
            "person_id": person_id,
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
        }
    except Exception:
        logger.exception("WEEKLY_DEBUG: exception occurred")
        raise


__all__ = ["router"]
