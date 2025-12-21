from __future__ import annotations

from sakhi.apps.engine.morning_momentum.engine import (
    generate_morning_momentum,
    persist_morning_momentum,
)


async def run_morning_momentum(person_id: str) -> None:
    momentum = await generate_morning_momentum(person_id)
    await persist_morning_momentum(person_id, momentum)


__all__ = ["run_morning_momentum"]
