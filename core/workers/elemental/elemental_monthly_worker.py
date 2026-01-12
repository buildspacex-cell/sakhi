from __future__ import annotations

import datetime as dt
from typing import Any, Dict
from uuid import UUID
import logging

from sakhi.apps.api.core.db import exec as dbexec, q as dbq
from core.rhythm.workers.elemental_monthly_aggregation_worker import run as aggregate_monthly

logger = logging.getLogger(__name__)


class _MonthlyStorage:
    def __init__(self, weekly_rows: Dict[str, List[Dict[str, Any]]], existing: set[str]) -> None:
        self.weekly_rows = weekly_rows
        self.existing = existing
        self.to_insert: List[Dict[str, Any]] = []

    def fetch_weekly_summaries(self, person_id, month_start: dt.date, dimension: str):
        return self.weekly_rows.get(dimension, [])

    def monthly_summary_exists(self, person_id, month_start: dt.date, dimension: str) -> bool:
        return f"{person_id}:{dimension}" in self.existing

    def insert_monthly_summary(
        self,
        *,
        person_id,
        month_start: dt.date,
        dimension: str,
        averages: Dict[str, float],
        volatility: float,
        week_count: int,
    ) -> None:
        self.to_insert.append(
            {
                "person_id": str(person_id),
                "month_start": month_start,
                "dimension": dimension,
                "averages": averages,
                "volatility": volatility,
                "week_count": week_count,
            }
        )


async def run_elemental_monthly_worker(person_id: UUID, month_start: dt.date) -> Dict[str, Any]:
    next_month = (month_start.replace(day=1) + dt.timedelta(days=32)).replace(day=1)
    weeklies = await dbq(
        """
        SELECT *
        FROM elemental_summary_weekly
        WHERE person_id = $1
          AND week_start >= $2
          AND week_start < $3
        ORDER BY week_start DESC
        """,
        str(person_id),
        month_start,
        next_month,
    )
    existing_rows = await dbq(
        "SELECT dimension FROM elemental_summary_monthly WHERE person_id=$1 AND month_start=$2",
        str(person_id),
        month_start,
    )
    weekly_by_dim: Dict[str, List[Dict[str, Any]]] = {"body": [], "mind": [], "emotion": []}
    for r in weeklies or []:
        dim = r.get("dimension")
        if dim in weekly_by_dim:
            weekly_by_dim[dim].append(r)
    existing = {f"{person_id}:{row.get('dimension')}" for row in (existing_rows or []) if row.get("dimension")}

    storage = _MonthlyStorage(weekly_by_dim, existing)
    aggregate_monthly(person_id, month_start, storage)  # type: ignore[arg-type]
    for row in storage.to_insert:
        await dbexec(
            """
            INSERT INTO elemental_summary_monthly (
              person_id, month_start, dimension,
              earth_avg, water_avg, fire_avg, air_avg, ether_avg,
              volatility, week_count, created_at
            )
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,NOW())
            ON CONFLICT (person_id, month_start, dimension) DO NOTHING
            """,
            row["person_id"],
            row["month_start"],
            row["dimension"],
            row["averages"].get("earth", 0.0),
            row["averages"].get("water", 0.0),
            row["averages"].get("fire", 0.0),
            row["averages"].get("air", 0.0),
            row["averages"].get("ether", 0.0),
            row["volatility"],
            row["week_count"],
        )
    logger.info(
        "elemental_monthly_worker_done",
        extra={
            "person_id": str(person_id),
            "month_start": str(month_start),
            "inserted": len(storage.to_insert),
            "weekly_counts": {k: len(v) for k, v in weekly_by_dim.items()},
        },
    )
    return {
        "worker_name": "elemental_monthly",
        "status": "success",
        "inputs": {"person_id": str(person_id), "month_start": str(month_start)},
        "outputs": {"inserted": len(storage.to_insert)},
        "executed_at": dt.datetime.utcnow().isoformat(),
    }
