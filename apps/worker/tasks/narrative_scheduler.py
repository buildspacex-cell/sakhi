from __future__ import annotations

import datetime
from typing import Iterable, Mapping, Any

from sakhi.apps.worker.narrative_deep import generate_deep_soul_narrative
from sakhi.apps.worker.alignment_refresh import refresh_alignment


async def weekly_refresh(person_ids: Iterable[str]) -> None:
    """
    Intended to be invoked by an external scheduler (e.g., every Monday 08:00).
    Runs deep narrative + alignment refresh for the provided users.
    """
    for pid in person_ids:
        await generate_deep_soul_narrative(pid)
        await refresh_alignment(pid)


async def on_soul_delta(person_id: str, delta: Mapping[str, Any]) -> None:
    """
    Trigger when soul_state changes meaningfully.
    Caller should detect deltas (e.g., values/shadow changes) and invoke this.
    """
    if not delta:
        return
    await generate_deep_soul_narrative(person_id)
    await refresh_alignment(person_id)
