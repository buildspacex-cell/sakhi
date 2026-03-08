from __future__ import annotations

from typing import Any

from sakhi.apps.api.services.demo.simulation_continuity import (
    ClassificationState,
    classify_simulation_entry,
    compile_simulation_continuity,
)


def classify_entry_for_continuity(entry: dict[str, Any]) -> dict[str, Any]:
    return classify_simulation_entry(entry)


def compile_entries_for_continuity(
    *,
    person_id: str,
    entries: list[dict[str, Any]],
    max_gap_days: int = 21,
    min_len: int = 3,
) -> dict[str, Any]:
    return compile_simulation_continuity(
        persona_id=person_id,
        entries=entries,
        max_gap_days=max_gap_days,
        min_len=min_len,
    )


__all__ = [
    "ClassificationState",
    "classify_entry_for_continuity",
    "compile_entries_for_continuity",
]
