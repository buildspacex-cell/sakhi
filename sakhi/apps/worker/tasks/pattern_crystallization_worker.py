"""
Pattern Crystallization Worker — Periodic Pattern Promotion

Runs on schedule to:
1. Aggregate pattern occurrences
2. Check against thresholds
3. Promote patterns to crystallized status when earned
4. Apply decay to stale patterns

Schedule:
- Daily: Quick check with 14-day window (frequency, recurrence)
- Weekly: Deeper check with 30-day window (trajectory, consistency)
- Monthly: Full check with 60-day window (themes, traits, identity)
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict

from sakhi.apps.api.services.crystallization.engine import crystallize_patterns
from sakhi.apps.api.core.db import q as dbfetch

LOGGER = logging.getLogger(__name__)


async def run_daily_crystallization(person_id: str) -> Dict[str, Any]:
    """
    Daily crystallization run - focuses on frequency and recurrence.

    Window: 14 days
    Focus: concerns, goals, emerging patterns
    """
    LOGGER.info("[CrystallizationWorker] daily run starting", extra={"person_id": person_id})

    result = await crystallize_patterns(
        person_id=person_id,
        window_days=14,
        run_type="daily",
    )

    return {
        "run_type": "daily",
        "person_id": person_id,
        "patterns_checked": result.patterns_checked,
        "patterns_crystallized": result.patterns_crystallized,
        "patterns_updated": result.patterns_updated,
        "patterns_decayed": result.patterns_decayed,
        "new_patterns": result.new_patterns,
    }


async def run_weekly_crystallization(person_id: str) -> Dict[str, Any]:
    """
    Weekly crystallization run - focuses on trajectory and consistency.

    Window: 30 days
    Focus: themes, relationships, shadows/lights
    """
    LOGGER.info("[CrystallizationWorker] weekly run starting", extra={"person_id": person_id})

    result = await crystallize_patterns(
        person_id=person_id,
        window_days=30,
        run_type="weekly",
    )

    return {
        "run_type": "weekly",
        "person_id": person_id,
        "patterns_checked": result.patterns_checked,
        "patterns_crystallized": result.patterns_crystallized,
        "patterns_updated": result.patterns_updated,
        "patterns_decayed": result.patterns_decayed,
        "new_patterns": result.new_patterns,
    }


async def run_monthly_crystallization(person_id: str) -> Dict[str, Any]:
    """
    Monthly crystallization run - focuses on identity-level patterns.

    Window: 60 days
    Focus: core values, traits, contradictions
    """
    LOGGER.info("[CrystallizationWorker] monthly run starting", extra={"person_id": person_id})

    result = await crystallize_patterns(
        person_id=person_id,
        window_days=60,
        run_type="monthly",
    )

    return {
        "run_type": "monthly",
        "person_id": person_id,
        "patterns_checked": result.patterns_checked,
        "patterns_crystallized": result.patterns_crystallized,
        "patterns_updated": result.patterns_updated,
        "patterns_decayed": result.patterns_decayed,
        "new_patterns": result.new_patterns,
    }


async def run_crystallization_for_all_users(run_type: str = "daily") -> Dict[str, Any]:
    """
    Run crystallization for all active users.

    Used by scheduler for batch processing.
    """
    # Get all users with recent activity
    cutoff_days = 7 if run_type == "daily" else 30

    users = await dbfetch(
        f"""
        SELECT DISTINCT user_id
        FROM journal_entries
        WHERE ts > NOW() - INTERVAL '{cutoff_days} days'
        """
    )

    results = []
    for user_row in users:
        person_id = user_row.get("user_id")
        if not person_id:
            continue

        try:
            if run_type == "daily":
                result = await run_daily_crystallization(str(person_id))
            elif run_type == "weekly":
                result = await run_weekly_crystallization(str(person_id))
            else:
                result = await run_monthly_crystallization(str(person_id))

            results.append(result)
        except Exception as exc:
            LOGGER.warning(
                "[CrystallizationWorker] user failed",
                extra={"person_id": person_id, "error": str(exc)},
            )

    return {
        "run_type": run_type,
        "users_processed": len(results),
        "total_crystallized": sum(r.get("patterns_crystallized", 0) for r in results),
        "total_updated": sum(r.get("patterns_updated", 0) for r in results),
    }


def main() -> None:
    """CLI entry point for manual runs."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m sakhi.apps.worker.tasks.pattern_crystallization_worker <person_id> [run_type]")
        print("  run_type: daily (default), weekly, monthly")
        return

    person_id = sys.argv[1]
    run_type = sys.argv[2] if len(sys.argv) > 2 else "daily"

    if run_type == "daily":
        result = asyncio.run(run_daily_crystallization(person_id))
    elif run_type == "weekly":
        result = asyncio.run(run_weekly_crystallization(person_id))
    elif run_type == "monthly":
        result = asyncio.run(run_monthly_crystallization(person_id))
    else:
        print(f"Unknown run_type: {run_type}")
        return

    print(f"Crystallization {run_type} complete:")
    print(f"  Patterns checked: {result.get('patterns_checked', 0)}")
    print(f"  Patterns crystallized: {result.get('patterns_crystallized', 0)}")
    print(f"  Patterns updated: {result.get('patterns_updated', 0)}")
    print(f"  Patterns decayed: {result.get('patterns_decayed', 0)}")
    if result.get("new_patterns"):
        print(f"  New patterns: {', '.join(result['new_patterns'])}")


if __name__ == "__main__":
    main()


__all__ = [
    "run_daily_crystallization",
    "run_weekly_crystallization",
    "run_monthly_crystallization",
    "run_crystallization_for_all_users",
]
