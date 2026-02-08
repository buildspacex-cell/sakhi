"""
Learning Pipeline Worker Tasks
-------------------------------
Background jobs for the recommendation tracking / intervention system.
"""

from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)


def run_mark_missed() -> None:
    """Mark pending check-ins from past days as MISSED.

    Should be run daily as part of the scheduler.
    """
    from sakhi.apps.api.services.learning.intervention_plans import mark_missed_checkins

    try:
        count = asyncio.run(mark_missed_checkins())
        logger.info("[Learning] Marked %d check-ins as missed", count)
    except Exception as exc:
        logger.error("[Learning] mark_missed_checkins failed: %s", exc)
