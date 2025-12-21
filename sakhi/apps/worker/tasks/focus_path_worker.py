from __future__ import annotations

from sakhi.apps.engine.focus_path.engine import generate_focus_path, persist_focus_path


async def run_focus_path(person_id: str, intent_text: str | None = None) -> None:
    path = await generate_focus_path(person_id, intent_text=intent_text)
    await persist_focus_path(person_id, path)


__all__ = ["run_focus_path"]
