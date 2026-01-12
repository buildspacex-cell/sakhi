from __future__ import annotations

from sakhi.apps.engine.morning_preview.engine import (
    generate_morning_preview,
    persist_morning_preview,
)
from sakhi.libs.scaffolding import (
    require_suppression_check,
    SuppressionSensitivity,
)


@require_suppression_check(
    scaffold_type="morning_preview",
    sensitivity=SuppressionSensitivity.MEDIUM
)
async def run_morning_preview(person_id: str) -> None:
    """
    Generate and persist morning preview for user

    **Suppression**: Protected by @require_suppression_check
    - Will not run if user is in vulnerable state
    - Returns None if suppressed
    - Logs suppression decision

    **Design Principle**: "Suppression First"
    - Every proactive scaffold checks suppression
    - User agency > system initiative
    """
    preview = await generate_morning_preview(person_id)
    await persist_morning_preview(person_id, preview)


__all__ = ["run_morning_preview"]
