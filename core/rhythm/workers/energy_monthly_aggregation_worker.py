from datetime import date
from typing import Protocol, Iterable, Dict, Any

from core.rhythm.constants import MIN_MONTHLY_WEEKS
from core.rhythm.energy.constants import ENERGY_CONFIDENCE_CAP, ENERGY_CONFIDENCE_FLOOR
from core.rhythm.utils import log, clamp


class EnergyMonthlyStorage(Protocol):
    def fetch_energy_weekly(self, person_id, month_start: date) -> Iterable[Dict[str, Any]]:
        ...

    def energy_monthly_exists(self, person_id, month_start: date) -> bool:
        ...

def insert_energy_monthly(
        self,
        *,
        person_id,
        month_start: date,
        activation_load: float,
        grounding: float,
        circulation: float,
        recovery_efficiency: float,
        confidence: float,
        week_count: int,
    ) -> None:
        ...


def _confidence(week_count: int) -> float:
    coverage = min(1.0, week_count / max(MIN_MONTHLY_WEEKS, 1))
    raw = ENERGY_CONFIDENCE_FLOOR + (coverage * (ENERGY_CONFIDENCE_CAP - ENERGY_CONFIDENCE_FLOOR))
    return min(ENERGY_CONFIDENCE_CAP, raw)


def run(person_id, month_start: date, storage: EnergyMonthlyStorage) -> None:
    if storage.energy_monthly_exists(person_id, month_start):
        log.info(
            "energy_monthly_exists",
            extra={"person_id": person_id, "month_start": str(month_start)},
        )
        return

    weeklies = list(storage.fetch_energy_weekly(person_id, month_start))
    if len(weeklies) < MIN_MONTHLY_WEEKS:
        log.info(
            "energy_monthly_skip_low_weeks",
            extra={"person_id": person_id, "month_start": str(month_start), "count": len(weeklies)},
        )
        return

    weight = len(weeklies)
    activation_load = sum(w["activation_load"] for w in weeklies) / weight
    grounding = sum(w["grounding"] for w in weeklies) / weight
    circulation = sum(w["circulation"] for w in weeklies) / weight
    recovery_efficiency = sum(w["recovery_efficiency"] for w in weeklies) / weight

    conf = _confidence(len(weeklies))
    storage.insert_energy_monthly(
        person_id=person_id,
        month_start=month_start,
        activation_load=clamp(activation_load),
        grounding=clamp(grounding),
        circulation=clamp(circulation),
        recovery_efficiency=clamp(recovery_efficiency),
        confidence=conf,
        week_count=len(weeklies),
    )
    log.info(
        "energy_monthly_written",
        extra={
            "person_id": person_id,
            "month_start": str(month_start),
            "weeks": len(weeklies),
            "activation_load": activation_load,
            "grounding": grounding,
            "circulation": circulation,
            "recovery_efficiency": recovery_efficiency,
            "confidence": conf,
        },
    )
