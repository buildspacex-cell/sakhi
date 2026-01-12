from __future__ import annotations

import datetime as dt
from typing import Any, Dict
from uuid import UUID
import logging

from sakhi.apps.api.core.db import exec as dbexec, q as dbq
from core.rhythm.workers.energy_monthly_aggregation_worker import run as aggregate_energy_monthly

logger = logging.getLogger(__name__)


class _EnergyMonthlyStorage:
    def __init__(self, weeklies: List[Dict[str, Any]], exists: bool) -> None:
        self.weeklies = weeklies
        self.exists = exists
        self.to_insert: Dict[str, Any] = {}

    def fetch_energy_weekly(self, person_id, month_start: dt.date):
        return self.weeklies

    def energy_monthly_exists(self, person_id, month_start: dt.date) -> bool:
        return self.exists

    def insert_energy_monthly(
        self,
        *,
        person_id,
        month_start: dt.date,
        activation_load: float,
        grounding: float,
        circulation: float,
        recovery_efficiency: float,
        confidence: float,
        week_count: int,
    ) -> None:
        self.to_insert = {
            "person_id": str(person_id),
            "month_start": month_start,
            "activation_load": activation_load,
            "grounding": grounding,
            "circulation": circulation,
            "recovery_efficiency": recovery_efficiency,
            "confidence": confidence,
            "week_count": week_count,
        }


async def run_energy_monthly_worker(person_id: UUID, month_start: dt.date) -> Dict[str, Any]:
    next_month = (month_start.replace(day=1) + dt.timedelta(days=32)).replace(day=1)
    weeklies = await dbq(
        """
        SELECT person_id, week_start,
               activation_load, grounding, circulation, recovery_efficiency,
               confidence, created_at
        FROM energy_summary_weekly
        WHERE person_id = $1
          AND week_start >= $2
          AND week_start < $3
        ORDER BY week_start DESC
        """,
        str(person_id),
        month_start,
        next_month,
    )
    exists = bool(
        await dbq(
            "SELECT 1 FROM energy_summary_monthly WHERE person_id=$1 AND month_start=$2",
            str(person_id),
            month_start,
            one=True,
        )
    )
    storage = _EnergyMonthlyStorage(weeklies or [], exists)
    aggregate_energy_monthly(person_id, month_start, storage)  # type: ignore[arg-type]
    if storage.to_insert:
        row = storage.to_insert
        await dbexec(
            """
            INSERT INTO energy_summary_monthly (
              person_id, month_start,
              activation_load, grounding, circulation, recovery_efficiency,
              confidence, week_count, created_at
            )
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,NOW())
            ON CONFLICT (person_id, month_start) DO NOTHING
            """,
            row["person_id"],
            row["month_start"],
            row["activation_load"],
            row["grounding"],
            row["circulation"],
            row["recovery_efficiency"],
            row["confidence"],
            row["week_count"],
        )
    logger.info(
        "energy_monthly_worker_done",
        extra={
            "person_id": str(person_id),
            "month_start": str(month_start),
            "inserted": 1 if storage.to_insert else 0,
            "weeklies": len(weeklies or []),
        },
    )
    return {
        "worker_name": "energy_monthly",
        "status": "success",
        "inputs": {"person_id": str(person_id), "month_start": str(month_start)},
        "outputs": {"inserted": 1 if storage.to_insert else 0},
        "executed_at": dt.datetime.utcnow().isoformat(),
    }
