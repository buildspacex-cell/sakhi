from datetime import date
from typing import Protocol, Iterable, Dict, Any

from core.rhythm.constants import MIN_WEEKLY_SIGNALS
from core.rhythm.utils import decay_weight, log
from core.rhythm.volatility import compute_volatility

EPSILON = 1e-6  # Minimum total weighted magnitude to consider a week valid.


class WeeklyAggregationStorage(Protocol):
    def fetch_nonexpired_elemental_stm(self, person_id, week_start: date, dimension: str) -> Iterable[Dict[str, Any]]:
        ...

    def weekly_summary_exists(self, person_id, week_start: date, dimension: str) -> bool:
        ...

    def insert_weekly_summary(
        self,
        *,
        person_id,
        week_start: date,
        dimension: str,
        averages: Dict[str, float],
        volatility: float,
        signal_count: int,
    ) -> None:
        ...


def _age_in_days(created_at, reference_date: date) -> int:
    """Age is computed relative to the target week, not today's clock."""
    return max((reference_date - created_at.date()).days, 0)


def run(person_id, week_start: date, storage: WeeklyAggregationStorage) -> None:
    for dimension in ("body", "mind", "emotion"):
        if storage.weekly_summary_exists(person_id, week_start, dimension):
            log.info(
                "weekly_elemental_exists",
                extra={"person_id": person_id, "week_start": str(week_start), "dimension": dimension},
            )
            continue

        stm_rows = list(storage.fetch_nonexpired_elemental_stm(person_id, week_start, dimension))
        if len(stm_rows) < MIN_WEEKLY_SIGNALS:
            log.info(
                "weekly_elemental_skip_low_signals",
                extra={"person_id": person_id, "week_start": str(week_start), "dimension": dimension, "count": len(stm_rows)},
            )
            continue

        totals = {"earth": 0.0, "water": 0.0, "fire": 0.0, "air": 0.0, "ether": 0.0}
        total_weight = 0.0
        volatility_vectors = []

        for row in stm_rows:
            age_days = _age_in_days(row["created_at"], week_start)
            magnitude = float(row["magnitude"])
            confidence = float(row["confidence"])
            weight = decay_weight(age_days, magnitude, confidence)
            if weight <= 0:
                continue
            total_weight += weight
            dist = {
                "earth": float(row["earth"]),
                "water": float(row["water"]),
                "fire": float(row["fire"]),
                "air": float(row["air"]),
                "ether": float(row["ether"]),
            }
            for el, val in dist.items():
                totals[el] += val * weight
            volatility_vectors.append({k: v * weight for k, v in dist.items()})

        if total_weight <= EPSILON:
            log.info(
                "weekly_elemental_skip_low_magnitude",
                extra={"person_id": person_id, "week_start": str(week_start), "dimension": dimension, "count": len(stm_rows)},
            )
            continue

        averages = {el: totals[el] / total_weight for el in totals}
        volatility = compute_volatility(volatility_vectors)

        storage.insert_weekly_summary(
            person_id=person_id,
            week_start=week_start,
            dimension=dimension,
            averages=averages,
            volatility=volatility,
            signal_count=len(stm_rows),
        )
        log.info(
            "weekly_elemental_aggregated",
            extra={
                "person_id": person_id,
                "week_start": str(week_start),
                "dimension": dimension,
                "signal_count": len(stm_rows),
                "volatility": volatility,
            },
        )
