from __future__ import annotations

from sakhi.apps.engine.micro_momentum.engine import (
    generate_micro_momentum,
    persist_micro_momentum,
)


async def run_micro_momentum(person_id: str) -> None:
    nudge = await generate_micro_momentum(person_id)
    await persist_micro_momentum(person_id, nudge)


__all__ = ["run_micro_momentum"]
