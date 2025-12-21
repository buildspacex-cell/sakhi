from __future__ import annotations

from sakhi.apps.engine.evening_closure.engine import (
    generate_evening_closure,
    persist_evening_closure,
)


async def run_evening_closure(person_id: str) -> None:
    closure = await generate_evening_closure(person_id)
    await persist_evening_closure(person_id, closure)


__all__ = ["run_evening_closure"]
