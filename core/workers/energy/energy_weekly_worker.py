from __future__ import annotations

import datetime as dt
from typing import Any, Dict
from uuid import UUID
import logging

from sakhi.apps.api.core.db import exec as dbexec, q as dbq
from core.rhythm.workers.energy_weekly_aggregation_worker import run as aggregate_energy_weekly

logger = logging.getLogger(__name__)


class _EnergyWeeklyStorage:
    def __init__(self, elementals: List[Dict[str, Any]], recovery: Dict[str, float], exists: bool) -> None:
        self.elementals = elementals
        self.recovery = recovery
        self.exists = exists
        self.to_insert: Dict[str, Any] = {}

    def fetch_elemental_weekly(self, person_id, week_start: dt.date):
        return self.elementals

    def fetch_recovery_rates(self, person_id) -> Dict[str, float]:
        return self.recovery

    def energy_weekly_exists(self, person_id, week_start: dt.date) -> bool:
        return self.exists

    def insert_energy_weekly(
        self,
        *,
        person_id,
        week_start: dt.date,
        activation_load: float,
        grounding: float,
        circulation: float,
        recovery_efficiency: float,
        confidence: float,
    ) -> None:
        self.to_insert = {
            "person_id": str(person_id),
            "week_start": week_start,
            "activation_load": activation_load,
            "grounding": grounding,
            "circulation": circulation,
            "recovery_efficiency": recovery_efficiency,
            "confidence": confidence,
        }


async def run_energy_weekly_worker(person_id: UUID, week_start: dt.date) -> Dict[str, Any]:
    next_week = week_start + dt.timedelta(days=7)
    elementals = await dbq(
        """
        SELECT person_id, week_start, dimension,
               earth_avg, water_avg, fire_avg, air_avg, ether_avg,
               volatility, signal_count
        FROM elemental_summary_weekly
        WHERE person_id = $1
          AND week_start >= $2
          AND week_start < $3
        ORDER BY week_start DESC
        """,
        str(person_id),
        week_start,
        next_week,
    )
    rec_row = await dbq(
        "SELECT recovery_rate FROM personal_model_elemental WHERE person_id = $1",
        str(person_id),
        one=True,
    )
    recovery = rec_row.get("recovery_rate") if rec_row else {}
    exists = bool(
        await dbq(
            "SELECT 1 FROM energy_summary_weekly WHERE person_id=$1 AND week_start=$2",
            str(person_id),
            week_start,
            one=True,
        )
    )

    storage = _EnergyWeeklyStorage(elementals or [], recovery if isinstance(recovery, dict) else {}, exists)
    aggregate_energy_weekly(person_id, week_start, storage)  # type: ignore[arg-type]
    if storage.to_insert:
        row = storage.to_insert
        await dbexec(
            """
            INSERT INTO energy_summary_weekly (
              person_id, week_start,
              activation_load, grounding, circulation, recovery_efficiency,
              confidence, created_at
            ) VALUES ($1,$2,$3,$4,$5,$6,$7,NOW())
            ON CONFLICT (person_id, week_start) DO NOTHING
            """,
            row["person_id"],
            row["week_start"],
            row["activation_load"],
            row["grounding"],
            row["circulation"],
            row["recovery_efficiency"],
            row["confidence"],
        )
    logger.info(
        "energy_weekly_worker_done",
        extra={
            "person_id": str(person_id),
            "week_start": str(week_start),
            "inserted": 1 if storage.to_insert else 0,
            "elemental_rows": len(elementals or []),
        },
    )
    return {
        "worker_name": "energy_weekly",
        "status": "success",
        "inputs": {"person_id": str(person_id), "week_start": str(week_start)},
        "outputs": {"inserted": 1 if storage.to_insert else 0},
        "executed_at": dt.datetime.utcnow().isoformat(),
    }
