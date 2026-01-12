from __future__ import annotations

import datetime as dt
from typing import Any, Dict
from uuid import UUID
import logging

from sakhi.apps.api.core.db import exec as dbexec, q as dbq
from core.rhythm.workers.personal_model_elemental_worker import run as update_personal_elemental

logger = logging.getLogger(__name__)


class _PersonalStorage:
    def __init__(self, monthly: Dict[str, Any], existing: Dict[str, Any]) -> None:
        self.monthly = monthly
        self.existing = existing or {}
        self.pending: Dict[str, Any] = {}

    def fetch_monthly_summaries(self, person_id) -> Dict[str, Any]:
        return self.monthly

    def read_personal_model(self, person_id) -> Dict[str, Any] | None:
        return self.existing

    def upsert_personal_model(
        self,
        *,
        person_id,
        baseline: Dict[str, Dict[str, float]],
        volatility: Dict[str, float],
        confidence: float,
    ) -> None:
        self.pending = {
            "person_id": str(person_id),
            "baseline": baseline,
            "volatility": volatility,
            "confidence": confidence,
        }


async def run_personal_model_elemental_worker(person_id: UUID) -> Dict[str, Any]:
    monthly = await dbq(
        """
        SELECT person_id, month_start, dimension,
               earth_avg, water_avg, fire_avg, air_avg, ether_avg,
               volatility, week_count, created_at
        FROM elemental_summary_monthly
        WHERE person_id = $1
        ORDER BY month_start DESC
        """,
        str(person_id),
    )
    existing = await dbq(
        """
        SELECT baseline, volatility, confidence
        FROM personal_model_elemental
        WHERE person_id = $1
        """,
        str(person_id),
        one=True,
    )
    storage = _PersonalStorage(monthly or [], existing or {})
    update_personal_elemental(person_id, storage)  # type: ignore[arg-type]
    if storage.pending:
        await dbexec(
            """
            INSERT INTO personal_model_elemental (person_id, baseline, volatility, recovery_rate, coupling, confidence, updated_at)
            VALUES ($1, $2, $3, '{}'::jsonb, '{}'::jsonb, $4, NOW())
            ON CONFLICT (person_id) DO UPDATE SET
              baseline = EXCLUDED.baseline,
              volatility = EXCLUDED.volatility,
              confidence = EXCLUDED.confidence,
              updated_at = NOW()
            """,
            storage.pending["person_id"],
            storage.pending["baseline"],
            storage.pending["volatility"],
            storage.pending["confidence"],
        )
    logger.info(
        "personal_model_elemental_worker_done",
        extra={
            "person_id": str(person_id),
            "updated": bool(storage.pending),
            "monthlies": len(monthly or []),
        },
    )
    return {
        "worker_name": "personal_model_elemental",
        "status": "success",
        "inputs": {"person_id": str(person_id)},
        "outputs": {"updated": bool(storage.pending)},
        "executed_at": dt.datetime.utcnow().isoformat(),
    }
