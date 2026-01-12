from __future__ import annotations

from sakhi.apps.engine.evening_closure.engine import (
    generate_evening_closure,
    persist_evening_closure,
)
from sakhi.libs.scaffolding import (
    require_suppression_check,
    SuppressionSensitivity,
)


@require_suppression_check(
    scaffold_type="evening_closure",
    sensitivity=SuppressionSensitivity.LOW  # End-of-day closure can be low sensitivity
)
async def run_evening_closure(person_id: str) -> None:
    """Generate and persist evening closure - Suppression protected"""
    closure = await generate_evening_closure(person_id)
    await persist_evening_closure(person_id, closure)


__all__ = ["run_evening_closure"]
