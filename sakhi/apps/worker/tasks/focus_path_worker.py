from __future__ import annotations

from sakhi.apps.engine.focus_path.engine import generate_focus_path, persist_focus_path
from sakhi.libs.scaffolding import (
    require_suppression_check,
    SuppressionSensitivity,
)


@require_suppression_check(
    scaffold_type="focus_path",
    sensitivity=SuppressionSensitivity.MEDIUM
)
async def run_focus_path(person_id: str, intent_text: str | None = None) -> None:
    """
    Generate and persist focus path for user

    **Suppression**: Protected by @require_suppression_check
    - Will not run if user is in vulnerable state
    - Returns None if suppressed
    - Logs suppression decision

    **Design Principle**: "Suppression First"
    - Every proactive scaffold checks suppression
    - User agency > system initiative
    """
    path = await generate_focus_path(person_id, intent_text=intent_text)
    await persist_focus_path(person_id, path)


__all__ = ["run_focus_path"]
