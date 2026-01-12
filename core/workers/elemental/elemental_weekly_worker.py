from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List
from uuid import UUID
import logging

from sakhi.apps.api.core.db import exec as dbexec, q as dbq
from core.rhythm.workers.elemental_weekly_aggregation_worker import run as aggregate_weekly

logger = logging.getLogger(__name__)


class _WeeklyStorage:
    def __init__(self, rows_by_dim: Dict[str, List[Dict[str, Any]]], existing: set[str]) -> None:
        self.rows_by_dim = rows_by_dim
        self.existing = existing
        self.to_insert: List[Dict[str, Any]] = []

    def fetch_nonexpired_elemental_stm(self, person_id, week_start: dt.date, dimension: str):
        return self.rows_by_dim.get(dimension, [])

    def weekly_summary_exists(self, person_id, week_start: dt.date, dimension: str) -> bool:
        key = f"{person_id}:{dimension}"
        return key in self.existing

    def insert_weekly_summary(
        self,
        *,
        person_id,
        week_start: dt.date,
        dimension: str,
        averages: Dict[str, float],
        volatility: float,
        signal_count: int,
    ) -> None:
        self.to_insert.append(
            {
                "person_id": str(person_id),
                "week_start": week_start,
                "dimension": dimension,
                "averages": averages,
                "volatility": volatility,
                "signal_count": signal_count,
            }
        )


async def run_elemental_weekly_worker(person_id: UUID, week_start: dt.date) -> Dict[str, Any]:
    start = week_start
    end = week_start + dt.timedelta(days=7)
    rows = await dbq(
        """
        SELECT *
        FROM elemental_signal_stm
        WHERE person_id = $1
          AND created_at >= $2
          AND created_at < $3
          AND expires_at >= NOW()
        ORDER BY created_at DESC
        """,
        str(person_id),
        start,
        end,
    )
    existing_rows = await dbq(
        "SELECT dimension FROM elemental_summary_weekly WHERE person_id=$1 AND week_start=$2",
        str(person_id),
        week_start,
    )
    by_dim: Dict[str, List[Dict[str, Any]]] = {"body": [], "mind": [], "emotion": []}
    for r in rows or []:
        dim = r.get("dimension")
        if dim in by_dim:
            by_dim[dim].append(r)
    existing = {f"{person_id}:{row.get('dimension')}" for row in (existing_rows or []) if row.get("dimension")}

    storage = _WeeklyStorage(by_dim, existing)
    aggregate_weekly(person_id, week_start, storage)  # type: ignore[arg-type]
    for row in storage.to_insert:
        await dbexec(
            """
            INSERT INTO elemental_summary_weekly (
              person_id, week_start, dimension,
              earth_avg, water_avg, fire_avg, air_avg, ether_avg,
              volatility, signal_count, created_at
            )
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,NOW())
            ON CONFLICT (person_id, week_start, dimension) DO NOTHING
            """,
            row["person_id"],
            row["week_start"],
            row["dimension"],
            row["averages"].get("earth", 0.0),
            row["averages"].get("water", 0.0),
            row["averages"].get("fire", 0.0),
            row["averages"].get("air", 0.0),
            row["averages"].get("ether", 0.0),
            row["volatility"],
            row["signal_count"],
        )
    logger.info(
        "elemental_weekly_worker_done",
        extra={
            "person_id": str(person_id),
            "week_start": str(week_start),
            "inserted": len(storage.to_insert),
            "rows_by_dim": {k: len(v) for k, v in by_dim.items()},
        },
    )
    return {
        "worker_name": "elemental_weekly",
        "status": "success",
        "inputs": {"person_id": str(person_id), "week_start": str(week_start)},
        "outputs": {"inserted": len(storage.to_insert)},
        "executed_at": dt.datetime.utcnow().isoformat(),
    }
