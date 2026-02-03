"""
A.7.5 Learning Trigger
----------------------
Run correlation updates on threshold or schedule.

The trigger decides WHEN to run the learning pipeline:
1. After N new behaviors/symptoms logged
2. On a schedule (weekly)
3. Manually triggered

When triggered, it runs:
1. Pattern detection from pattern_learning.py
2. Preference updates from feedback
3. Intervention effectiveness aggregation
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from dataclasses import dataclass

from sakhi.apps.api.core.db import q as dbfetch, exec as execute

logger = logging.getLogger(__name__)


@dataclass
class LearningRunResult:
    """Result of a learning cycle run."""
    run_id: str
    person_id: str
    behaviors_processed: int
    symptoms_processed: int
    patterns_detected: int
    patterns_strengthened: int
    preferences_updated: int
    duration_ms: int
    status: str
    error: Optional[str] = None


# Thresholds for triggering learning
BEHAVIOR_THRESHOLD = 10  # After 10 new behaviors
SYMPTOM_THRESHOLD = 5    # After 5 new symptoms
MIN_HOURS_BETWEEN_RUNS = 4  # Don't run more often than every 4 hours


async def should_trigger_learning(
    person_id: str,
    force: bool = False,
) -> tuple[bool, str]:
    """
    Check if learning should run for this user.

    Args:
        person_id: User ID
        force: Force trigger regardless of thresholds

    Returns:
        Tuple of (should_run, reason)
    """
    if force:
        return True, "forced"

    try:
        # Check last run time
        last_run = await dbfetch(
            """
            SELECT started_at FROM learning_runs
            WHERE person_id = $1 AND status = 'completed'
            ORDER BY started_at DESC
            LIMIT 1
            """,
            person_id,
            one=True,
        )

        cutoff = datetime.utcnow() - timedelta(hours=MIN_HOURS_BETWEEN_RUNS)
        if last_run and last_run["started_at"]:
            # Handle timezone-aware vs naive datetime comparison
            last_started = last_run["started_at"]
            if last_started.tzinfo is not None:
                from datetime import timezone
                cutoff = cutoff.replace(tzinfo=timezone.utc)
            if last_started > cutoff:
                return False, "too_recent"

        # Check behavior count since last run
        last_run_time = last_run["started_at"] if last_run else datetime.utcnow() - timedelta(days=30)

        behavior_count = await dbfetch(
            """
            SELECT COUNT(*) as cnt FROM behavior_log
            WHERE person_id = $1 AND created_at > $2
            """,
            person_id,
            last_run_time,
            one=True,
        )

        if behavior_count and behavior_count["cnt"] >= BEHAVIOR_THRESHOLD:
            return True, "behavior_threshold"

        # Check symptom count
        symptom_count = await dbfetch(
            """
            SELECT COUNT(*) as cnt FROM symptom_log
            WHERE person_id = $1 AND created_at > $2
            """,
            person_id,
            last_run_time,
            one=True,
        )

        if symptom_count and symptom_count["cnt"] >= SYMPTOM_THRESHOLD:
            return True, "symptom_threshold"

        return False, "no_threshold_met"

    except Exception as e:
        logger.warning(f"Error checking learning trigger: {e}")
        return False, f"error: {e}"


async def run_learning_cycle(
    person_id: str,
    trigger_reason: str = "manual",
    lookback_days: int = 14,
) -> LearningRunResult:
    """
    Run a full learning cycle for a user.

    This:
    1. Detects patterns from recent behaviors/symptoms
    2. Updates pattern strengths
    3. Applies feedback to preferences
    4. Records the run

    Args:
        person_id: User ID
        trigger_reason: Why learning was triggered
        lookback_days: How many days to analyze

    Returns:
        LearningRunResult with stats
    """
    import time
    start_time = time.time()

    # Create run record
    run_record = await dbfetch(
        """
        INSERT INTO learning_runs (person_id, run_type, trigger_reason, status)
        VALUES ($1, 'full', $2, 'running')
        RETURNING id
        """,
        person_id,
        trigger_reason,
        one=True,
    )
    run_id = str(run_record["id"]) if run_record else "unknown"

    result = LearningRunResult(
        run_id=run_id,
        person_id=person_id,
        behaviors_processed=0,
        symptoms_processed=0,
        patterns_detected=0,
        patterns_strengthened=0,
        preferences_updated=0,
        duration_ms=0,
        status="running",
    )

    try:
        # 1. Get counts of recent data
        cutoff = datetime.utcnow() - timedelta(days=lookback_days)

        behavior_count = await dbfetch(
            "SELECT COUNT(*) as cnt FROM behavior_log WHERE person_id = $1 AND occurred_at > $2",
            person_id, cutoff, one=True
        )
        result.behaviors_processed = behavior_count["cnt"] if behavior_count else 0

        symptom_count = await dbfetch(
            "SELECT COUNT(*) as cnt FROM symptom_log WHERE person_id = $1 AND occurred_at > $2",
            person_id, cutoff, one=True
        )
        result.symptoms_processed = symptom_count["cnt"] if symptom_count else 0

        # 2. Run pattern detection
        from sakhi.apps.api.services.ayurveda.pattern_learning import detect_patterns
        detected = await detect_patterns(person_id, lookback_days)

        for pattern in detected:
            if pattern.get("status") == "new":
                result.patterns_detected += 1
            elif pattern.get("status") == "strengthened":
                result.patterns_strengthened += 1

        # 3. Apply pending feedback to preferences
        from sakhi.apps.api.services.learning.preference_updater import process_pending_feedback
        feedback_result = await process_pending_feedback(person_id)
        result.preferences_updated = feedback_result.get("adjustments_made", 0)

        # 4. Mark run complete
        duration_ms = int((time.time() - start_time) * 1000)
        result.duration_ms = duration_ms
        result.status = "completed"

        await execute(
            """
            UPDATE learning_runs
            SET status = 'completed',
                completed_at = NOW(),
                duration_ms = $1,
                behaviors_processed = $2,
                symptoms_processed = $3,
                patterns_detected = $4,
                patterns_strengthened = $5,
                preferences_updated = $6
            WHERE id = $7
            """,
            duration_ms,
            result.behaviors_processed,
            result.symptoms_processed,
            result.patterns_detected,
            result.patterns_strengthened,
            result.preferences_updated,
            run_id,
        )

        logger.info(
            "[trigger] Learning cycle complete for %s: %d patterns, %d pref updates in %dms",
            person_id[:8], result.patterns_detected + result.patterns_strengthened,
            result.preferences_updated, duration_ms
        )

    except Exception as e:
        result.status = "failed"
        result.error = str(e)

        await execute(
            "UPDATE learning_runs SET status = 'failed', error_message = $1 WHERE id = $2",
            str(e), run_id
        )

        logger.error(f"Learning cycle failed for {person_id[:8]}: {e}")

    return result


async def get_learning_history(
    person_id: str,
    limit: int = 10,
) -> list[Dict[str, Any]]:
    """Get recent learning run history for a user."""
    try:
        results = await dbfetch(
            """
            SELECT id, run_type, trigger_reason, status,
                   behaviors_processed, symptoms_processed,
                   patterns_detected, patterns_strengthened,
                   preferences_updated, duration_ms,
                   started_at, completed_at, error_message
            FROM learning_runs
            WHERE person_id = $1
            ORDER BY started_at DESC
            LIMIT $2
            """,
            person_id,
            limit,
        )

        return [
            {
                "run_id": str(r["id"]),
                "run_type": r["run_type"],
                "trigger_reason": r["trigger_reason"],
                "status": r["status"],
                "behaviors_processed": r["behaviors_processed"],
                "symptoms_processed": r["symptoms_processed"],
                "patterns_detected": r["patterns_detected"],
                "patterns_strengthened": r["patterns_strengthened"],
                "preferences_updated": r["preferences_updated"],
                "duration_ms": r["duration_ms"],
                "started_at": r["started_at"].isoformat() if r["started_at"] else None,
                "completed_at": r["completed_at"].isoformat() if r["completed_at"] else None,
                "error": r["error_message"],
            }
            for r in (results or [])
        ]

    except Exception as e:
        logger.warning(f"Failed to get learning history: {e}")
        return []
