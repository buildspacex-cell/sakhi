from __future__ import annotations

from sakhi.apps.engine.micro_momentum.engine import (
    generate_micro_momentum,
    persist_micro_momentum,
)
from sakhi.libs.scaffolding import (
    require_suppression_check,
    SuppressionSensitivity,
)


@require_suppression_check(
    scaffold_type="micro_momentum",
    sensitivity=SuppressionSensitivity.MEDIUM
)
async def run_micro_momentum(person_id: str) -> None:
    """Generate and persist micro momentum - Suppression protected"""
    nudge = await generate_micro_momentum(person_id)
    await persist_micro_momentum(person_id, nudge)


__all__ = ["run_micro_momentum"]
