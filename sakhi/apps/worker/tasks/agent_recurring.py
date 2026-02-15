"""Worker task for executing due recurring agent schedules."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict

LOGGER = logging.getLogger(__name__)


async def _run_due_recurring_schedules(limit: int = 10) -> Dict[str, Any]:
    from sakhi.apps.api.services.agentic.recurring import execute_due_recurring_schedules

    result = await execute_due_recurring_schedules(limit=limit)
    LOGGER.info(
        "[agent_recurring_worker] processed=%s",
        result.get("processed", 0),
    )
    return result


def run_due_recurring_schedules(limit: int = 10) -> None:
    asyncio.run(_run_due_recurring_schedules(limit=limit))


__all__ = ["run_due_recurring_schedules", "_run_due_recurring_schedules"]
