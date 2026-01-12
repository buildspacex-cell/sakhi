from __future__ import annotations

import datetime as dt
from typing import Any, Dict
from uuid import UUID
import logging

from sakhi.apps.api.core.db import exec as dbexec, q as dbq
from core.rhythm.workers.personal_model_energy_worker import run as update_personal_energy

logger = logging.getLogger(__name__)


class _PersonalEnergyStorage:
    def __init__(self, monthly: Dict[str, Any], existing: Dict[str, Any]) -> None:
        self.monthly = monthly
        self.existing = existing or {}
        self.pending: Dict[str, Any] = {}

    def fetch_energy_monthly(self, person_id) -> Dict[str, Any]:
        return self.monthly

    def read_personal_energy(self, person_id) -> Dict[str, Any] | None:
        return self.existing

    def upsert_personal_energy(
        self,
        *,
        person_id,
        traits: Dict[str, float],
        confidence: float,
    ) -> None:
        self.pending = {
            "person_id": str(person_id),
            "traits": traits,
            "confidence": confidence,
        }


async def run_personal_model_energy_worker(person_id: UUID) -> Dict[str, Any]:
    monthly = await dbq(
        """
        SELECT person_id, month_start,
               activation_load, grounding, circulation, recovery_efficiency,
               confidence, created_at
        FROM energy_summary_monthly
        WHERE person_id = $1
        ORDER BY month_start DESC
        """,
        str(person_id),
    )
    existing = await dbq(
        """
        SELECT baseline, volatility, recovery_profile, circulation_stability, confidence
        FROM personal_model_energy
        WHERE person_id = $1
        """,
        str(person_id),
        one=True,
    )
    if existing and "baseline" in existing and "traits" not in existing:
        existing["traits"] = existing.get("baseline") or {}
    storage = _PersonalEnergyStorage(monthly or [], existing or {})
    update_personal_energy(person_id, storage)  # type: ignore[arg-type]
    if storage.pending:
        await dbexec(
            """
            INSERT INTO personal_model_energy (person_id, baseline, volatility, recovery_profile, circulation_stability, confidence, updated_at)
            VALUES ($1, $2, '{}'::jsonb, '{}'::jsonb, '{}'::jsonb, $3, NOW())
            ON CONFLICT (person_id) DO UPDATE SET
              baseline = EXCLUDED.baseline,
              volatility = EXCLUDED.volatility,
              recovery_profile = EXCLUDED.recovery_profile,
              circulation_stability = EXCLUDED.circulation_stability,
              confidence = EXCLUDED.confidence,
              updated_at = NOW()
            """,
            storage.pending["person_id"],
            storage.pending["traits"],
            storage.pending["confidence"],
        )
    logger.info(
        "personal_model_energy_worker_done",
        extra={
            "person_id": str(person_id),
            "updated": bool(storage.pending),
            "monthlies": len(monthly or []),
        },
    )
    return {
        "worker_name": "personal_model_energy",
        "status": "success",
        "inputs": {"person_id": str(person_id)},
        "outputs": {"updated": bool(getattr(storage, "pending", None))},
        "executed_at": dt.datetime.utcnow().isoformat(),
    }
