from __future__ import annotations

from sakhi.apps.engine.morning_momentum.engine import (
    generate_morning_momentum,
    persist_morning_momentum,
)
from sakhi.libs.scaffolding import (
    require_suppression_check,
    SuppressionSensitivity,
)


@require_suppression_check(
    scaffold_type="morning_momentum",
    sensitivity=SuppressionSensitivity.MEDIUM
)
async def run_morning_momentum(person_id: str) -> None:
    """Generate and persist morning momentum - Suppression protected"""
    momentum = await generate_morning_momentum(person_id)
    await persist_morning_momentum(person_id, momentum)


__all__ = ["run_morning_momentum"]
