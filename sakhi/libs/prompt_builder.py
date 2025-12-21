from __future__ import annotations

from typing import Any, Dict

from sakhi.apps.api.services.memory.personal_model_repo import get_raw


async def build_prompt(person_id: str, message: str) -> str:
    row = await get_raw(person_id)
    data: Dict[str, Any] = (row or {}).get("data") or {}

    def layer(name: str) -> str:
        layer_data = data.get(name) or {}
        summary = layer_data.get("summary")
        return summary or "—"

    return (
        "Person Model Snapshot:\n"
        f"BODY: {layer('body')}\n"
        f"MIND: {layer('mind')}\n"
        f"EMOTION: {layer('emotion')}\n"
        f"GOALS: {layer('goals')}\n"
        f"SOUL: {layer('soul')}\n"
        f"RHYTHM: {layer('rhythm')}\n\n"
        f"User just shared: {message}"
    )
