from __future__ import annotations

from sakhi.apps.engine.mini_flow.engine import generate_mini_flow, persist_mini_flow


async def run_mini_flow(person_id: str, intent_text: str | None = None) -> None:
    flow = await generate_mini_flow(person_id)
    await persist_mini_flow(person_id, flow)


__all__ = ["run_mini_flow"]
