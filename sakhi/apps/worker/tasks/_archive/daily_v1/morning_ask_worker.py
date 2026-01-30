from __future__ import annotations

from sakhi.apps.engine.morning_ask.engine import generate_morning_ask, persist_morning_ask
from sakhi.libs.scaffolding import (
    require_suppression_check,
    SuppressionSensitivity,
)


@require_suppression_check(
    scaffold_type="morning_ask",
    sensitivity=SuppressionSensitivity.MEDIUM
)
async def run_morning_ask(person_id: str) -> None:
    """Generate and persist morning ask - Suppression protected"""
    ask = await generate_morning_ask(person_id)
    await persist_morning_ask(person_id, ask)


__all__ = ["run_morning_ask"]
