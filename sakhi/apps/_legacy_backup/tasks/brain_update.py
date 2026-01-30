from __future__ import annotations

from sakhi.apps.logic.brain import brain_engine


async def run_brain_update(person_id: str) -> None:
    """Recompute and persist the Personal OS Brain, then refresh journey caches."""
    await brain_engine.refresh_brain(person_id, refresh_journey=True)


__all__ = ["run_brain_update"]
