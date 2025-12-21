from __future__ import annotations

from sakhi.apps.engine.micro_journey.engine import (
    generate_micro_journey,
    persist_micro_journey,
)


async def run_micro_journey(person_id: str) -> None:
    journey = await generate_micro_journey(person_id)
    await persist_micro_journey(person_id, journey)


__all__ = ["run_micro_journey"]
