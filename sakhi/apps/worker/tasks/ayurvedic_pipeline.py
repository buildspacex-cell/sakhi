import logging
import datetime as dt
from typing import Dict, Any
from uuid import UUID

from sakhi.apps.api.core.db import q as dbq
from core.rhythm.constants import MIN_WEEKLY_SIGNALS

logger = logging.getLogger(__name__)


async def _anchor_dates_from_stm(person_id: str) -> Dict[str, dt.date]:
    row = await dbq(
        "SELECT max(created_at) AS latest FROM memory_short_term WHERE person_id::text = $1 OR user_id::text = $1",
        person_id,
        one=True,
    )
    latest = row.get("latest") if row else None
    if isinstance(latest, str):
        try:
            latest = dt.datetime.fromisoformat(latest)
        except Exception:
            latest = None
    if not isinstance(latest, dt.datetime):
        anchor_date = dt.date.today()
    else:
        anchor_date = latest.date()
    week_start = anchor_date - dt.timedelta(days=anchor_date.weekday())
    month_start = anchor_date.replace(day=1)
    return {"week_start": week_start, "month_start": month_start, "anchor_date": anchor_date}


async def _anchor_dates_from_elemental(person_id: str, reference_date: dt.date | None = None) -> Dict[str, dt.date] | None:
    row = await dbq(
        """
        SELECT max(created_at) AS latest
        FROM elemental_signal_stm
        WHERE person_id = $1
          AND ($2::timestamptz IS NULL OR created_at <= $2)
        """,
        person_id,
        dt.datetime.combine(reference_date, dt.time.min, tzinfo=None) if reference_date else None,
        one=True,
    )
    latest = row.get("latest") if row else None  # type: ignore[attr-defined]
    if isinstance(latest, str):
        try:
            latest = dt.datetime.fromisoformat(latest)
        except Exception:
            latest = None
    if not isinstance(latest, dt.datetime):
        return None
    anchor_date = latest.date()
    week_start = anchor_date - dt.timedelta(days=anchor_date.weekday())
    month_start = anchor_date.replace(day=1)
    return {"week_start": week_start, "month_start": month_start, "anchor_date": anchor_date}


async def _best_week_from_elemental(person_id: str) -> dt.date | None:
    """
    Finds the latest week where every dimension has at least MIN_WEEKLY_SIGNALS
    non-expired STM rows. Returns the week_start date or None if none qualify.
    """
    row = await dbq(
        """
        WITH per_dim AS (
          SELECT date_trunc('week', created_at)::date AS week_start,
                 dimension,
                 count(*) AS c
          FROM elemental_signal_stm
          WHERE person_id = $1
            AND expires_at >= NOW()
          GROUP BY week_start, dimension
        )
        SELECT week_start
        FROM per_dim
        GROUP BY week_start
        HAVING min(c) >= $2
        ORDER BY week_start DESC
        LIMIT 1
        """,
        person_id,
        MIN_WEEKLY_SIGNALS,
        one=True,
    )
    return row.get("week_start") if row else None  # type: ignore[return-value]


async def run_ayurvedic_pipeline(person_id: str) -> Dict[str, Any]:
    """
    Orchestrates elemental and energy pipelines as a single composite worker.
    Sub-workers are expected to be idempotent; this function just sequences calls.
    """
    # Run each step; errors are not swallowed so the caller can handle them.
    from core.workers.signals.neutral_signal_extraction_worker import run_neutral_signal_extraction_worker
    from core.workers.elemental.elemental_stm_worker import run_elemental_stm_worker
    from core.workers.elemental.elemental_weekly_worker import run_elemental_weekly_worker
    from core.workers.elemental.elemental_monthly_worker import run_elemental_monthly_worker
    from core.workers.elemental.personal_model_elemental_worker import run_personal_model_elemental_worker
    from core.workers.energy.energy_weekly_worker import run_energy_weekly_worker
    from core.workers.energy.energy_monthly_worker import run_energy_monthly_worker
    from core.workers.energy.personal_model_energy_worker import run_personal_model_energy_worker

    anchors = await _anchor_dates_from_stm(person_id)
    week_start = anchors["week_start"]
    month_start = anchors["month_start"]
    anchor_date = anchors.get("anchor_date")

    person_uuid = UUID(str(person_id))
    steps = []
    try:
        logger.info(
            "[AyurvedicPipeline] starting",
            extra={
                "person_id": person_id,
                "week_start": str(week_start),
                "month_start": str(month_start),
                "anchor_date": str(anchors.get("anchor_date")),
            },
        )
        steps.append(await run_neutral_signal_extraction_worker(person_uuid, dt.datetime.utcnow(), mode="pipeline"))
        steps.append(await run_elemental_stm_worker(person_uuid, dt.datetime.utcnow(), mode="pipeline"))
        anchors_after = await _anchor_dates_from_elemental(person_id, anchor_date) or anchors
        week_start = anchors_after["week_start"]
        month_start = anchors_after["month_start"]
        fallback_week = await _best_week_from_elemental(person_id)
        if fallback_week and fallback_week != week_start:
            logger.info(
                "[AyurvedicPipeline] using_best_available_week",
                extra={"person_id": person_id, "prev_week": str(week_start), "new_week": str(fallback_week)},
            )
            week_start = fallback_week
            month_start = week_start.replace(day=1)
        steps.append(await run_elemental_weekly_worker(person_uuid, week_start))
        steps.append(await run_elemental_monthly_worker(person_uuid, month_start))
        steps.append(await run_personal_model_elemental_worker(person_uuid))

        steps.append(await run_energy_weekly_worker(person_uuid, week_start))
        steps.append(await run_energy_monthly_worker(person_uuid, month_start))
        steps.append(await run_personal_model_energy_worker(person_uuid))
    except Exception as exc:
        logger.error("[AyurvedicPipeline] error", extra={"person_id": person_id, "error": str(exc)})
        raise

    logger.info(
        "[AyurvedicPipeline] completed",
        extra={
            "person_id": person_id,
            "steps": [s.get("worker_name") for s in steps],
            "outputs": steps,
        },
    )
    executed = [
        "neutral_signal_extraction",
        "elemental_stm",
        "elemental_weekly",
        "elemental_monthly",
        "personal_model_elemental",
        "energy_weekly",
        "energy_monthly",
        "personal_model_energy",
    ]
    return {"executed": executed}
