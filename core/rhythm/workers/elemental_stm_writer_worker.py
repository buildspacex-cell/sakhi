from typing import Protocol, Iterable, Dict, Any

from core.rhythm.elemental_projection_engine import project_to_elements
from core.rhythm.utils import log


class STMWriterStorage(Protocol):
    def fetch_stm_signals(self, person_id) -> Iterable[Dict[str, Any]]:
        ...

    def elemental_stm_exists(self, person_id, source_signal_id, dimension: str) -> bool:
        ...

    def insert_elemental_stm(
        self,
        *,
        person_id,
        source_signal_id,
        source_type: str,
        dimension: str,
        distribution: Dict[str, float],
        magnitude: float,
        confidence: float,
        expires_at,
    ) -> None:
        ...


def run(person_id, storage: STMWriterStorage) -> None:
    """
    Writes elemental projections into STM (one row per dimension).
    Idempotent per (person_id, source_signal_id, dimension).
    """
    signals = storage.fetch_stm_signals(person_id)
    for sig in signals:
        projection = project_to_elements(sig)
        for dimension, vec in projection["vector"].items():
            if storage.elemental_stm_exists(person_id, sig["id"], dimension):
                log.info(
                    "elemental_stm_skip_existing",
                    extra={"person_id": person_id, "signal_id": sig["id"], "dimension": dimension},
                )
                continue
            storage.insert_elemental_stm(
                person_id=person_id,
                source_signal_id=sig["id"],
                source_type=sig.get("source_type", "signal"),
                dimension=dimension,
                distribution=vec["distribution"],
                magnitude=vec["magnitude"],
                confidence=projection["confidence"],
                expires_at=projection["expires_at"],
            )
            log.info(
                "elemental_stm_written",
                extra={
                    "person_id": person_id,
                    "signal_id": sig["id"],
                    "dimension": dimension,
                    "expires_at": projection["expires_at"].isoformat(),
                    "magnitude": vec["magnitude"],
                },
            )
