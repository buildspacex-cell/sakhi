from __future__ import annotations

from sakhi.apps.engine.morning_preview.engine import (
    generate_morning_preview,
    persist_morning_preview,
)


async def run_morning_preview(person_id: str) -> None:
    preview = await generate_morning_preview(person_id)
    await persist_morning_preview(person_id, preview)


__all__ = ["run_morning_preview"]
