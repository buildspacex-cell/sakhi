from typing import Protocol, Dict, Any

from core.rhythm.constants import PERSONAL_MODEL_UPDATE_WEIGHT
from core.rhythm.utils import log


class PersonalModelStorage(Protocol):
    def fetch_monthly_summaries(self, person_id) -> Dict[str, Any]:
        ...

    def read_personal_model(self, person_id) -> Dict[str, Any] | None:
        ...

    def upsert_personal_model(
        self,
        *,
        person_id,
        baseline: Dict[str, Dict[str, float]],
        volatility: Dict[str, float],
        confidence: float,
    ) -> None:
        ...


def _weighted_average(old: float, new: float, weight: float) -> float:
    return old * (1 - weight) + new * weight


def run(person_id, storage: PersonalModelStorage) -> None:
    monthly = list(storage.fetch_monthly_summaries(person_id))
    if not monthly:
        log.info("personal_model_elemental_skip_no_monthly", extra={"person_id": person_id})
        return

    current = storage.read_personal_model(person_id) or {"baseline": {}, "volatility": {}, "confidence": 0.5}

    latest_by_dimension: Dict[str, Dict[str, Any]] = {}
    for summary in monthly:
        dim = summary["dimension"]
        if dim not in latest_by_dimension or summary["month_start"] > latest_by_dimension[dim]["month_start"]:
            latest_by_dimension[dim] = summary

    baseline: Dict[str, Dict[str, float]] = {}
    vol: Dict[str, float] = {}
    for dim, summary in latest_by_dimension.items():
        prior_dim = current["baseline"].get(dim, {})
        baseline[dim] = {
            el: _weighted_average(prior_dim.get(el, 0.0), summary["averages"][el], PERSONAL_MODEL_UPDATE_WEIGHT)
            for el in ["earth", "water", "fire", "air", "ether"]
        }
        vol[dim] = _weighted_average(
            current["volatility"].get(dim, 0.0), summary["volatility"], PERSONAL_MODEL_UPDATE_WEIGHT
        )

    new_conf = min(0.95, _weighted_average(current.get("confidence", 0.5), 1.0, PERSONAL_MODEL_UPDATE_WEIGHT / 2))

    storage.upsert_personal_model(
        person_id=person_id,
        baseline=baseline,
        volatility=vol,
        confidence=new_conf,
    )
    log.info(
        "personal_model_elemental_updated",
        extra={"person_id": person_id, "dimensions": list(baseline.keys()), "confidence": new_conf},
    )
