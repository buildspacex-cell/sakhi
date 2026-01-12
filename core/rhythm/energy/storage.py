from __future__ import annotations

import json
import logging
from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID

from sakhi.apps.api.core.db import exec as dbexec, q as dbq

log = logging.getLogger(__name__)


def assert_unit_interval(value: float, name: str) -> None:
    if not (0.0 <= value <= 1.0):
        raise ValueError(f"{name} out of bounds: {value}")


def _assert_json_serializable(value: Any, name: str) -> None:
    try:
        json.dumps(value)
    except Exception as exc:
        raise ValueError(f"{name} is not JSON serializable") from exc


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


async def insert_energy_weekly_summary(
    person_id: UUID,
    week_start: date,
    activation_load: float,
    grounding: float,
    circulation: float,
    recovery_efficiency: float,
    confidence: float,
) -> None:
    assert_unit_interval(activation_load, "activation_load")
    assert_unit_interval(grounding, "grounding")
    assert_unit_interval(circulation, "circulation")
    assert_unit_interval(recovery_efficiency, "recovery_efficiency")
    assert_unit_interval(confidence, "confidence")

    sql = """
    insert into energy_summary_weekly (
      person_id, week_start, activation_load, grounding, circulation, recovery_efficiency, confidence
    )
    values ($1, $2, $3, $4, $5, $6, $7)
    on conflict (person_id, week_start) do nothing
    """
    result = await dbexec(sql, person_id, week_start, activation_load, grounding, circulation, recovery_efficiency, confidence)
    if result and result.endswith("0 0"):
        log.info(
            "energy_weekly_exists",
            extra={"person_id": str(person_id), "week_start": str(week_start), "confidence": confidence, "ts": _ts()},
        )
        return
    log.info(
        "energy_weekly_inserted",
        extra={"person_id": str(person_id), "week_start": str(week_start), "confidence": confidence, "ts": _ts()},
    )


async def insert_energy_monthly_summary(
    person_id: UUID,
    month_start: date,
    activation_load: float,
    grounding: float,
    circulation: float,
    recovery_efficiency: float,
    confidence: float,
) -> None:
    assert_unit_interval(activation_load, "activation_load")
    assert_unit_interval(grounding, "grounding")
    assert_unit_interval(circulation, "circulation")
    assert_unit_interval(recovery_efficiency, "recovery_efficiency")
    assert_unit_interval(confidence, "confidence")

    sql = """
    insert into energy_summary_monthly (
      person_id, month_start, activation_load, grounding, circulation, recovery_efficiency, confidence
    )
    values ($1, $2, $3, $4, $5, $6, $7)
    on conflict (person_id, month_start) do nothing
    """
    result = await dbexec(sql, person_id, month_start, activation_load, grounding, circulation, recovery_efficiency, confidence)
    if result and result.endswith("0 0"):
        log.info(
            "energy_monthly_exists",
            extra={"person_id": str(person_id), "month_start": str(month_start), "confidence": confidence, "ts": _ts()},
        )
        return
    log.info(
        "energy_monthly_inserted",
        extra={"person_id": str(person_id), "month_start": str(month_start), "confidence": confidence, "ts": _ts()},
    )


async def upsert_personal_model_energy(
    person_id: UUID,
    baseline: dict,
    volatility: dict,
    recovery_profile: dict,
    circulation_stability: dict,
    confidence: float,
) -> None:
    _assert_json_serializable(baseline, "baseline")
    _assert_json_serializable(volatility, "volatility")
    _assert_json_serializable(recovery_profile, "recovery_profile")
    _assert_json_serializable(circulation_stability, "circulation_stability")
    assert_unit_interval(confidence, "confidence")

    existing = await dbq(
        "select confidence from personal_model_energy where person_id = $1",
        person_id,
        one=True,
    )
    old_conf = existing.get("confidence") if existing else None

    sql = """
    insert into personal_model_energy (
      person_id, baseline, volatility, recovery_profile, circulation_stability, confidence, updated_at
    )
    values ($1, $2, $3, $4, $5, $6, now())
    on conflict (person_id) do update set
      baseline = excluded.baseline,
      volatility = excluded.volatility,
      recovery_profile = excluded.recovery_profile,
      circulation_stability = excluded.circulation_stability,
      confidence = excluded.confidence,
      updated_at = now()
    """
    await dbexec(
        sql,
        person_id,
        json.dumps(baseline),
        json.dumps(volatility),
        json.dumps(recovery_profile),
        json.dumps(circulation_stability),
        confidence,
    )
    log.info(
        "personal_energy_upserted",
        extra={
            "person_id": str(person_id),
            "old_confidence": old_conf,
            "new_confidence": confidence,
            "ts": _ts(),
        },
    )
