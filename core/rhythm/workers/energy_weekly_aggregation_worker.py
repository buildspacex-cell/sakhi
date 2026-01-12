from datetime import date
from typing import Protocol, Iterable, Dict, Any

from core.rhythm.energy.constants import ENERGY_CONFIDENCE_CAP, ENERGY_CONFIDENCE_FLOOR, EPSILON
from core.rhythm.energy.energy_computation import compute_energy_primitives
from core.rhythm.utils import log


class EnergyWeeklyStorage(Protocol):
    def fetch_elemental_weekly(self, person_id, week_start: date) -> Iterable[Dict[str, Any]]:
        ...

    def fetch_recovery_rates(self, person_id) -> Dict[str, float]:
        ...

    def energy_weekly_exists(self, person_id, week_start: date) -> bool:
        ...

    def insert_energy_weekly(
        self,
        *,
        person_id,
        week_start: date,
        activation_load: float,
        grounding: float,
        circulation: float,
        recovery_efficiency: float,
        confidence: float,
    ) -> None:
        ...


def _confidence(num_dimensions_present: int) -> float:
    coverage = num_dimensions_present / 3.0
    raw = ENERGY_CONFIDENCE_FLOOR + (coverage * (ENERGY_CONFIDENCE_CAP - ENERGY_CONFIDENCE_FLOOR))
    return min(ENERGY_CONFIDENCE_CAP, raw)


def run(person_id, week_start: date, storage: EnergyWeeklyStorage) -> None:
    if storage.energy_weekly_exists(person_id, week_start):
        log.info(
            "energy_weekly_exists",
            extra={"person_id": person_id, "week_start": str(week_start)},
        )
        return

    summaries = list(storage.fetch_elemental_weekly(person_id, week_start))
    if not summaries:
        log.info(
            "energy_weekly_skip_no_elementals",
            extra={"person_id": person_id, "week_start": str(week_start)},
        )
        return

    recovery_rates = storage.fetch_recovery_rates(person_id) or {}
    energy = compute_energy_primitives(weekly_elementals=summaries, recovery_rates=recovery_rates)

    if (
        energy["activation_load"] <= EPSILON
        and energy["grounding"] <= EPSILON
        and energy["circulation"] <= EPSILON
        and energy["recovery_efficiency"] <= EPSILON
    ):
        log.info(
            "energy_weekly_skip_low_signal",
            extra={"person_id": person_id, "week_start": str(week_start)},
        )
        return

    conf = _confidence(len(summaries))
    storage.insert_energy_weekly(
        person_id=person_id,
        week_start=week_start,
        activation_load=energy["activation_load"],
        grounding=energy["grounding"],
        circulation=energy["circulation"],
        recovery_efficiency=energy["recovery_efficiency"],
        confidence=conf,
    )
    log.info(
        "energy_weekly_written",
        extra={
            "person_id": person_id,
            "week_start": str(week_start),
            "activation_load": energy["activation_load"],
            "grounding": energy["grounding"],
            "circulation": energy["circulation"],
            "recovery_efficiency": energy["recovery_efficiency"],
            "confidence": conf,
        },
    )
