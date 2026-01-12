from __future__ import annotations

from sakhi.apps.engine.mini_flow.engine import generate_mini_flow, persist_mini_flow
from sakhi.libs.scaffolding import (
    require_suppression_check,
    SuppressionSensitivity,
)


@require_suppression_check(
    scaffold_type="mini_flow",
    sensitivity=SuppressionSensitivity.MEDIUM
)
async def run_mini_flow(person_id: str, intent_text: str | None = None) -> None:
    """Generate and persist mini flow - Suppression protected"""
    flow = await generate_mini_flow(person_id)
    await persist_mini_flow(person_id, flow)


__all__ = ["run_mini_flow"]
