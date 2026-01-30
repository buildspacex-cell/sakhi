from __future__ import annotations

from typing import Any, Dict

from sakhi.apps.api.core.dialog_state import update_dialog_state
from sakhi.apps.api.services.memory.ingest_reasoning import ingest_reasoning_to_memory


async def write_turn_memory(
    person_id: str,
    dialog_state: Dict[str, Any],
    reasoning: Dict[str, Any] | None,
    entry_id: str | None,
    user_text: str,
) -> Dict[str, Any]:
    """
    Single gateway for memory writes to avoid duplicates.
    """

    dialog_result: Dict[str, Any] | None = None
    reasoning_result: Dict[str, Any] | None = None

    try:
        dialog_result = await update_dialog_state(
            person_id=person_id,
            conv_id=entry_id or person_id,
            state=dialog_state,
        )
    except Exception as exc:  # pragma: no cover - best effort
        dialog_result = {"error": str(exc)}

    if reasoning:
        try:
            reasoning_result = await ingest_reasoning_to_memory(
                person_id=person_id,
                reasoning=reasoning,
                source_turn_id=entry_id or person_id,
            )
        except Exception as exc:  # pragma: no cover - best effort
            reasoning_result = {"error": str(exc)}

    return {"dialog_state": dialog_result, "reasoning_ingest": reasoning_result}


__all__ = ["write_turn_memory"]
