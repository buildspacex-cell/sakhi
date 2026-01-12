from typing import Protocol, Dict, Any

from core.rhythm.energy.constants import ENERGY_PERSONAL_UPDATE_WEIGHT, ENERGY_CONFIDENCE_CAP
from core.rhythm.utils import log, clamp


class PersonalEnergyStorage(Protocol):
    def fetch_energy_monthly(self, person_id) -> Dict[str, Any]:
        ...

    def read_personal_energy(self, person_id) -> Dict[str, Any] | None:
        ...

    def upsert_personal_energy(
        self,
        *,
        person_id,
        traits: Dict[str, float],
        confidence: float,
    ) -> None:
        ...


def _weighted_average(old: float, new: float, weight: float) -> float:
    return old * (1 - weight) + new * weight


def run(person_id, storage: PersonalEnergyStorage) -> None:
    monthly = list(storage.fetch_energy_monthly(person_id))
    if not monthly:
        log.info("personal_energy_skip_no_monthly", extra={"person_id": person_id})
        return

    current = storage.read_personal_energy(person_id) or {"traits": {}, "confidence": 0.5}
    latest = max(monthly, key=lambda m: m["month_start"])

    traits = current.get("traits", {})
    new_traits = {
        "activation_tolerance": _weighted_average(
            traits.get("activation_tolerance", 0.5),
            clamp(1.0 - latest["activation_load"]),
            ENERGY_PERSONAL_UPDATE_WEIGHT,
        ),
        "recovery_half_life": _weighted_average(
            traits.get("recovery_half_life", 0.5),
            clamp(1.0 - latest["recovery_efficiency"]),
            ENERGY_PERSONAL_UPDATE_WEIGHT,
        ),
        "circulation_stability": _weighted_average(
            traits.get("circulation_stability", 0.5),
            clamp(latest["circulation"]),
            ENERGY_PERSONAL_UPDATE_WEIGHT,
        ),
        "grounding_baseline": _weighted_average(
            traits.get("grounding_baseline", 0.5),
            clamp(latest["grounding"]),
            ENERGY_PERSONAL_UPDATE_WEIGHT,
        ),
    }

    new_conf = min(
        ENERGY_CONFIDENCE_CAP,
        _weighted_average(current.get("confidence", 0.5), 1.0, ENERGY_PERSONAL_UPDATE_WEIGHT / 2),
    )

    storage.upsert_personal_energy(
        person_id=person_id,
        traits=new_traits,
        confidence=new_conf,
    )
    log.info(
        "personal_energy_updated",
        extra={"person_id": person_id, "traits": list(new_traits.keys()), "confidence": new_conf},
    )
