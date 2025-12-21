from __future__ import annotations

from sakhi.apps.engine.micro_recovery.engine import (
    generate_micro_recovery,
    persist_micro_recovery,
)


async def run_micro_recovery(person_id: str) -> None:
    rec = await generate_micro_recovery(person_id)
    await persist_micro_recovery(person_id, rec)


__all__ = ["run_micro_recovery"]
