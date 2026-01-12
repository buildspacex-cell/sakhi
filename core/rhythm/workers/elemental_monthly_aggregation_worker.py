from datetime import date
from typing import Protocol, Iterable, Dict, Any

from core.rhythm.constants import MIN_MONTHLY_WEEKS
from core.rhythm.utils import log


class MonthlyAggregationStorage(Protocol):
    def fetch_weekly_summaries(self, person_id, month_start: date, dimension: str) -> Iterable[Dict[str, Any]]:
        ...

    def monthly_summary_exists(self, person_id, month_start: date, dimension: str) -> bool:
        ...

    def insert_monthly_summary(
        self,
        *,
        person_id,
        month_start: date,
        dimension: str,
        averages: Dict[str, float],
        volatility: float,
        week_count: int,
    ) -> None:
        ...


def run(person_id, month_start: date, storage: MonthlyAggregationStorage) -> None:
    for dimension in ("body", "mind", "emotion"):
        if storage.monthly_summary_exists(person_id, month_start, dimension):
            log.info(
                "monthly_elemental_exists",
                extra={"person_id": person_id, "month_start": str(month_start), "dimension": dimension},
            )
            continue

        weeks = list(storage.fetch_weekly_summaries(person_id, month_start, dimension))
        if len(weeks) < MIN_MONTHLY_WEEKS:
            log.info(
                "monthly_elemental_skip_low_weeks",
                extra={"person_id": person_id, "month_start": str(month_start), "dimension": dimension, "count": len(weeks)},
            )
            continue

        weight = len(weeks)
        averages = {el: sum(w["averages"][el] for w in weeks) / weight for el in ["earth", "water", "fire", "air", "ether"]}
        volatility = sum(w["volatility"] for w in weeks) / weight

        storage.insert_monthly_summary(
            person_id=person_id,
            month_start=month_start,
            dimension=dimension,
            averages=averages,
            volatility=volatility,
            week_count=len(weeks),
        )
        log.info(
            "monthly_elemental_aggregated",
            extra={
                "person_id": person_id,
                "month_start": str(month_start),
                "dimension": dimension,
                "weeks": len(weeks),
                "volatility": volatility,
            },
        )
