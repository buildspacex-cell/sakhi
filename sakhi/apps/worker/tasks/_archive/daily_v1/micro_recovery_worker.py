from __future__ import annotations

from sakhi.apps.engine.micro_recovery.engine import (
    generate_micro_recovery,
    persist_micro_recovery,
)
from sakhi.libs.scaffolding import (
    require_suppression_check,
    SuppressionSensitivity,
)


@require_suppression_check(
    scaffold_type="micro_recovery",
    sensitivity=SuppressionSensitivity.MEDIUM
)
async def run_micro_recovery(person_id: str) -> None:
    """Generate and persist micro recovery - Suppression protected"""
    rec = await generate_micro_recovery(person_id)
    await persist_micro_recovery(person_id, rec)


__all__ = ["run_micro_recovery"]
