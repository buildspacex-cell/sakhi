from typing import Protocol, Iterable, Dict, Any, List, Tuple

from core.rhythm.constants import EPISODIC_PROMOTION_WEEKS
from core.rhythm.utils import log


class EpisodicPromotionStorage(Protocol):
    def fetch_recent_weeklies(self, person_id, lookback_weeks: int) -> Iterable[Dict[str, Any]]:
        ...

    def has_reported_strain(self, person_id, dimension: str, weeks: List[Dict[str, Any]]) -> bool:
        """
        Returns True only if journals or signals indicate discomfort, strain, or recovery debt during the same window.
        """
        ...

    def create_episode(self, person_id, summary: str) -> str:
        ...

    def link_elemental_episode(self, *, episode_id: str, person_id, dominant_dimension: str, dominant_elements: List[str]) -> None:
        ...


def _dominant_elements(summary: Dict[str, Any], top_n: int = 2) -> Tuple[str, ...]:
    sorted_pairs = sorted(summary["averages"].items(), key=lambda kv: kv[1], reverse=True)
    return tuple(el for el, _ in sorted_pairs[:top_n])


def run(person_id, storage: EpisodicPromotionStorage) -> None:
    weeklies = list(storage.fetch_recent_weeklies(person_id, lookback_weeks=EPISODIC_PROMOTION_WEEKS))
    if not weeklies:
        log.info("elemental_episode_skip_no_weeks", extra={"person_id": person_id})
        return

    by_dimension: Dict[str, List[Dict[str, Any]]] = {"body": [], "mind": [], "emotion": []}
    for w in weeklies:
        if w["dimension"] in by_dimension:
            by_dimension[w["dimension"]].append(w)

    for dimension, rows in by_dimension.items():
        if len(rows) < EPISODIC_PROMOTION_WEEKS:
            continue

        dom_sets = {_dominant_elements(w) for w in rows}
        if len(dom_sets) != 1:
            log.info(
                "elemental_episode_skip_inconsistent_dominant",
                extra={"person_id": person_id, "dimension": dimension, "dominant_sets": list(dom_sets)},
            )
            continue

        dominant_elements = list(dom_sets.pop())
        if not storage.has_reported_strain(person_id, dimension, rows):
            log.info(
                "elemental_episode_skip_no_strain",
                extra={"person_id": person_id, "dimension": dimension, "weeks": len(rows)},
            )
            continue

        summary = (
            f"{dimension.capitalize()} showed the same leading elements for {len(rows)} straight weeks. "
            "You noted related strain during this period."
        )
        episode_id = storage.create_episode(person_id=person_id, summary=summary)
        storage.link_elemental_episode(
            episode_id=episode_id,
            person_id=person_id,
            dominant_dimension=dimension,
            dominant_elements=dominant_elements,
        )
        log.info(
            "elemental_episode_promoted",
            extra={
                "person_id": person_id,
                "dimension": dimension,
                "weeks": len(rows),
                "dominant_elements": dominant_elements,
                "episode_id": episode_id,
            },
        )
