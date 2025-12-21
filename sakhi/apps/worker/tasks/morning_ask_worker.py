from __future__ import annotations

from sakhi.apps.engine.morning_ask.engine import generate_morning_ask, persist_morning_ask


async def run_morning_ask(person_id: str) -> None:
    ask = await generate_morning_ask(person_id)
    await persist_morning_ask(person_id, ask)


__all__ = ["run_morning_ask"]
