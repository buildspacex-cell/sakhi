from __future__ import annotations

from typing import Any, Dict, List


async def plan_from_intents(*, person_id: str, intents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Extremely lightweight planner: convert each intent into a suggested plan item.
    More advanced planning happens elsewhere (planner engine).
    """

    plans: List[Dict[str, Any]] = []
    for intent in intents:
        description = intent.get("description") or intent.get("kind") or "Focus"
        plans.append(
            {
                "label": description,
                "intent_id": intent.get("id"),
                "person_id": person_id,
                "timeline": intent.get("timeline"),
                "priority": intent.get("confidence", 0.5),
            }
        )
    return plans


__all__ = ["plan_from_intents"]
