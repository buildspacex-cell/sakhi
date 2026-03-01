"""
Crystallization Engine — Pattern Promotion and Trajectory Tracking

This engine runs periodically (daily/weekly) to:
1. Aggregate pattern occurrences
2. Check against thresholds
3. Promote patterns to crystallized status when earned
4. Track trajectories (improving, worsening, stable, emerging, fading)
5. Decay unused patterns
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from kala.pattern.thresholds import (
    CRYSTALLIZATION_THRESHOLDS,
    calculate_decay,
    check_threshold,
)
from kala.pattern.trajectory import (
    CrystallizationResult,
    PatternCandidate,
    calculate_trajectory,
)
from sakhi.apps.api.core.db import exec as dbexec
from sakhi.apps.api.core.db import q as dbfetch

# Memory Graph wiring for cross-entity relationships
try:
    from sakhi.apps.api.services.memory_graph.wiring import wire_pattern_to_graph
    MEMORY_GRAPH_ENABLED = True
except ImportError:
    MEMORY_GRAPH_ENABLED = False

LOGGER = logging.getLogger(__name__)


def _coerce_json_object(value: Any) -> Dict[str, Any]:
    """Normalize DB JSON/JSONB payloads that may come back as strings."""
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            return {}
    return {}


async def aggregate_pattern_occurrences(
    person_id: str,
    window_days: int,
) -> Dict[str, List[PatternCandidate]]:
    """
    Aggregate pattern occurrences by type and value within window.

    Returns dict mapping pattern_type to list of candidates.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)

    rows = await dbfetch(
        """
        SELECT
            pattern_type,
            pattern_value,
            COUNT(*) as mention_count,
            COUNT(DISTINCT DATE(detected_at)) as distinct_days,
            AVG(confidence) as avg_confidence,
            MIN(detected_at) as first_seen,
            MAX(detected_at) as last_seen,
            ARRAY_AGG(id::text) as evidence_ids,
            ARRAY_AGG(
                jsonb_build_object(
                    'id', id::text,
                    'date', detected_at::date::text,
                    'snippet', LEFT(snippet, 200)
                )
            ) as evidence_snippets
        FROM pattern_occurrences
        WHERE person_id = $1
          AND detected_at > $2
        GROUP BY pattern_type, pattern_value
        ORDER BY mention_count DESC
        """,
        person_id,
        cutoff,
    )

    candidates: Dict[str, List[PatternCandidate]] = {}

    for row in rows:
        pattern_type = row.get("pattern_type")
        if not pattern_type:
            continue

        candidate = PatternCandidate(
            pattern_type=pattern_type,
            pattern_value=row.get("pattern_value", ""),
            mention_count=row.get("mention_count", 0),
            distinct_days=row.get("distinct_days", 0),
            avg_confidence=float(row.get("avg_confidence", 0.0)),
            first_seen=row.get("first_seen"),
            last_seen=row.get("last_seen"),
            evidence_ids=row.get("evidence_ids") or [],
            evidence_snippets=row.get("evidence_snippets") or [],
        )

        if pattern_type not in candidates:
            candidates[pattern_type] = []
        candidates[pattern_type].append(candidate)

    return candidates


# calculate_trajectory imported from kala.pattern.trajectory (see top of file)


async def crystallize_pattern(
    person_id: str,
    candidate: PatternCandidate,
    final_confidence: float,
) -> Optional[str]:
    """
    Create or update a crystallized pattern.

    Returns pattern ID if created/updated, None if failed.
    """
    now = datetime.now(timezone.utc)

    # Check if pattern already exists
    existing = await dbfetch(
        """
        SELECT id, mention_count, confidence, last_seen, trajectory_data
        FROM crystallized_patterns
        WHERE person_id = $1
          AND pattern_type = $2
          AND pattern_value = $3
        """,
        person_id,
        candidate.pattern_type,
        candidate.pattern_value,
        one=True,
    )

    span_days = (candidate.last_seen - candidate.first_seen).days if candidate.last_seen and candidate.first_seen else 0

    if existing:
        # Update existing pattern
        pattern_id = existing.get("id")
        previous_mentions = existing.get("mention_count", 0)

        trajectory = calculate_trajectory(
            candidate.mention_count,
            previous_mentions,
            span_days,
        )

        # Build trajectory data
        trajectory_data = _coerce_json_object(existing.get("trajectory_data"))
        trajectory_data[now.isoformat()] = {
            "mentions": candidate.mention_count,
            "confidence": final_confidence,
            "trajectory": trajectory,
        }

        try:
            await dbexec(
                """
                UPDATE crystallized_patterns
                SET
                    mention_count = $3,
                    distinct_days = $4,
                    confidence = $5,
                    evidence_ids = $6::uuid[],
                    evidence_snippets = $7::jsonb,
                    trajectory = $8,
                    trajectory_data = $9::jsonb,
                    last_seen = $10,
                    status = CASE WHEN status = 'emerging' THEN 'active' ELSE status END,
                    crystallized_at = COALESCE(crystallized_at, $10),
                    threshold_met_at = COALESCE(threshold_met_at, $10),
                    updated_at = NOW()
                WHERE id = $1 AND person_id = $2
                """,
                pattern_id,
                person_id,
                candidate.mention_count,
                candidate.distinct_days,
                final_confidence,
                candidate.evidence_ids,
                json.dumps(candidate.evidence_snippets[:10]),  # Keep last 10
                trajectory,
                json.dumps(trajectory_data),
                now,
            )

            # Log to crystallization_log
            await _log_crystallization(
                person_id=person_id,
                pattern_id=pattern_id,
                pattern_type=candidate.pattern_type,
                pattern_value=candidate.pattern_value,
                occurrence_count=candidate.mention_count,
                distinct_days=candidate.distinct_days,
                confidence=final_confidence,
                span_days=span_days,
                evidence_ids=candidate.evidence_ids,
                action="updated",
            )

            return str(pattern_id)

        except Exception as exc:
            LOGGER.warning(
                "[Crystallization] update failed",
                extra={
                    "person_id": person_id,
                    "pattern_type": candidate.pattern_type,
                    "error": str(exc),
                },
            )
            return None

    else:
        # Create new crystallized pattern
        try:
            result = await dbfetch(
                """
                INSERT INTO crystallized_patterns (
                    person_id, pattern_type, pattern_value,
                    mention_count, distinct_days, confidence,
                    evidence_ids, evidence_snippets,
                    trajectory, trajectory_data,
                    status, first_seen, last_seen,
                    crystallized_at, threshold_met_at
                )
                VALUES (
                    $1, $2, $3, $4, $5, $6,
                    $7::uuid[], $8::jsonb,
                    'emerging', '{}'::jsonb,
                    'active', $9, $10, $10, $10
                )
                RETURNING id
                """,
                person_id,
                candidate.pattern_type,
                candidate.pattern_value,
                candidate.mention_count,
                candidate.distinct_days,
                final_confidence,
                candidate.evidence_ids,
                json.dumps(candidate.evidence_snippets[:10]),
                candidate.first_seen,
                candidate.last_seen or now,
                one=True,
            )

            pattern_id = result.get("id") if result else None

            if pattern_id:
                await _log_crystallization(
                    person_id=person_id,
                    pattern_id=pattern_id,
                    pattern_type=candidate.pattern_type,
                    pattern_value=candidate.pattern_value,
                    occurrence_count=candidate.mention_count,
                    distinct_days=candidate.distinct_days,
                    confidence=final_confidence,
                    span_days=span_days,
                    evidence_ids=candidate.evidence_ids,
                    action="crystallized",
                )

                # Wire to memory graph for cross-entity relationships
                if MEMORY_GRAPH_ENABLED:
                    try:
                        await wire_pattern_to_graph(
                            person_id=person_id,
                            pattern_type=candidate.pattern_type,
                            pattern_value=candidate.pattern_value,
                            confidence=final_confidence,
                            evidence_snippet=candidate.evidence_snippets[0].get("snippet", "") if candidate.evidence_snippets else "",
                        )
                    except Exception as wire_exc:
                        LOGGER.debug(
                            "[Crystallization] memory graph wiring failed (non-fatal): %s",
                            wire_exc,
                        )

            return str(pattern_id) if pattern_id else None

        except Exception as exc:
            LOGGER.warning(
                "[Crystallization] insert failed",
                extra={
                    "person_id": person_id,
                    "pattern_type": candidate.pattern_type,
                    "error": str(exc),
                },
            )
            return None


async def _log_crystallization(
    person_id: str,
    pattern_id: str,
    pattern_type: str,
    pattern_value: str,
    occurrence_count: int,
    distinct_days: int,
    confidence: float,
    span_days: int,
    evidence_ids: List[str],
    action: str,
) -> None:
    """Log crystallization event for audit trail."""
    threshold = CRYSTALLIZATION_THRESHOLDS.get(pattern_type)
    threshold_config = {
        "min_mentions": threshold.min_mentions if threshold else 0,
        "window_days": threshold.window_days if threshold else 0,
        "min_confidence": threshold.min_confidence if threshold else 0,
        "min_distinct_days": threshold.min_distinct_days if threshold else 0,
    }

    try:
        await dbexec(
            """
            INSERT INTO crystallization_log (
                person_id, crystallized_pattern_id, pattern_type, pattern_value,
                occurrence_count, distinct_days, confidence, span_days,
                threshold_config, evidence_ids, action
            )
            VALUES ($1, $2::uuid, $3, $4, $5, $6, $7, $8, $9::jsonb, $10::uuid[], $11)
            """,
            person_id,
            pattern_id,
            pattern_type,
            pattern_value,
            occurrence_count,
            distinct_days,
            confidence,
            span_days,
            json.dumps(threshold_config),
            evidence_ids[:20],  # Limit to 20
            action,
        )
    except Exception as exc:
        LOGGER.warning(
            "[Crystallization] log failed",
            extra={"person_id": person_id, "error": str(exc)},
        )


async def decay_stale_patterns(person_id: str, stale_weeks: float = 2.0) -> int:
    """
    Apply decay to patterns not seen recently.

    Returns count of patterns decayed.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(weeks=stale_weeks)

    stale_patterns = await dbfetch(
        """
        SELECT id, pattern_type, confidence, last_seen
        FROM crystallized_patterns
        WHERE person_id = $1
          AND status = 'active'
          AND last_seen < $2
        """,
        person_id,
        cutoff,
    )

    decayed_count = 0

    for pattern in stale_patterns:
        pattern_id = pattern.get("id")
        pattern_type = pattern.get("pattern_type")
        current_confidence = float(pattern.get("confidence", 0.5))
        last_seen = pattern.get("last_seen")

        if not last_seen:
            continue

        weeks_since = (datetime.now(timezone.utc) - last_seen).days / 7
        new_confidence = calculate_decay(pattern_type, weeks_since, current_confidence)

        # If confidence drops below 0.2, mark as fading
        new_status = "fading" if new_confidence < 0.2 else "active"

        try:
            await dbexec(
                """
                UPDATE crystallized_patterns
                SET confidence = $3, status = $4, updated_at = NOW()
                WHERE id = $1 AND person_id = $2
                """,
                pattern_id,
                person_id,
                new_confidence,
                new_status,
            )
            decayed_count += 1
        except Exception:
            pass

    return decayed_count


async def crystallize_patterns(
    person_id: str,
    window_days: int = 30,
    run_type: str = "daily",
) -> CrystallizationResult:
    """
    Main crystallization function - run periodically.

    Args:
        person_id: Person to process
        window_days: How far back to look for occurrences
        run_type: 'daily', 'weekly', or 'monthly'

    Returns:
        CrystallizationResult with stats
    """
    LOGGER.info(
        "[Crystallization] starting",
        extra={"person_id": person_id, "run_type": run_type, "window_days": window_days},
    )

    # Aggregate occurrences
    candidates_by_type = await aggregate_pattern_occurrences(person_id, window_days)

    patterns_checked = 0
    patterns_crystallized = 0
    patterns_updated = 0
    new_patterns: List[str] = []
    updated_patterns: List[str] = []

    # Process each pattern type
    for pattern_type, candidates in candidates_by_type.items():
        for candidate in candidates:
            patterns_checked += 1

            span_days = (candidate.last_seen - candidate.first_seen).days if candidate.last_seen and candidate.first_seen else 0

            # Check threshold
            threshold_met, final_confidence, reason = check_threshold(
                pattern_type=candidate.pattern_type,
                mention_count=candidate.mention_count,
                distinct_days=candidate.distinct_days,
                avg_confidence=candidate.avg_confidence,
                span_days=span_days,
            )

            if not threshold_met:
                LOGGER.debug(
                    "[Crystallization] below threshold",
                    extra={
                        "person_id": person_id,
                        "pattern_type": candidate.pattern_type,
                        "pattern_value": candidate.pattern_value[:50],
                        "reason": reason,
                    },
                )
                continue

            # Crystallize the pattern
            pattern_id = await crystallize_pattern(person_id, candidate, final_confidence)

            if pattern_id:
                # Check if this was new or updated
                existing = await dbfetch(
                    """
                    SELECT created_at, updated_at
                    FROM crystallized_patterns
                    WHERE id = $1::uuid
                    """,
                    pattern_id,
                    one=True,
                )

                if existing:
                    created = existing.get("created_at")
                    updated = existing.get("updated_at")
                    # If created in last minute, it's new
                    if created and updated and (updated - created).total_seconds() < 60:
                        patterns_crystallized += 1
                        new_patterns.append(f"{candidate.pattern_type}:{candidate.pattern_value[:30]}")
                    else:
                        patterns_updated += 1
                        updated_patterns.append(f"{candidate.pattern_type}:{candidate.pattern_value[:30]}")

    # Decay stale patterns only on deeper cadence to avoid over-pruning.
    # Daily runs are intended to be incremental checks/promotions.
    patterns_decayed = 0
    if run_type in {"weekly", "monthly"}:
        patterns_decayed = await decay_stale_patterns(person_id)

    result = CrystallizationResult(
        person_id=person_id,
        run_type=run_type,
        window_days=window_days,
        patterns_checked=patterns_checked,
        patterns_crystallized=patterns_crystallized,
        patterns_updated=patterns_updated,
        patterns_decayed=patterns_decayed,
        new_patterns=new_patterns,
        updated_patterns=updated_patterns,
    )

    LOGGER.info(
        "[Crystallization] complete",
        extra={
            "person_id": person_id,
            "run_type": run_type,
            "checked": patterns_checked,
            "crystallized": patterns_crystallized,
            "updated": patterns_updated,
            "decayed": patterns_decayed,
        },
    )

    return result


async def get_active_patterns(
    person_id: str,
    pattern_types: Optional[List[str]] = None,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """
    Get active crystallized patterns for a person.

    Args:
        person_id: Person ID
        pattern_types: Optional filter by types
        limit: Max patterns to return

    Returns:
        List of pattern dicts
    """
    if pattern_types:
        rows = await dbfetch(
            """
            SELECT *
            FROM crystallized_patterns
            WHERE person_id = $1
              AND status = 'active'
              AND pattern_type = ANY($2::text[])
            ORDER BY confidence DESC, mention_count DESC
            LIMIT $3
            """,
            person_id,
            pattern_types,
            limit,
        )
    else:
        rows = await dbfetch(
            """
            SELECT *
            FROM crystallized_patterns
            WHERE person_id = $1
              AND status = 'active'
            ORDER BY confidence DESC, mention_count DESC
            LIMIT $2
            """,
            person_id,
            limit,
        )

    return [dict(row) for row in rows]


async def get_pattern_for_topic(
    person_id: str,
    topic: str,
) -> Optional[Dict[str, Any]]:
    """
    Get crystallized pattern matching a topic.

    Uses fuzzy matching on pattern_value.
    """
    row = await dbfetch(
        """
        SELECT *
        FROM crystallized_patterns
        WHERE person_id = $1
          AND status = 'active'
          AND (
            pattern_value ILIKE '%' || $2 || '%'
            OR $2 ILIKE '%' || pattern_value || '%'
          )
        ORDER BY confidence DESC
        LIMIT 1
        """,
        person_id,
        topic,
        one=True,
    )

    return dict(row) if row else None


__all__ = [
    "crystallize_patterns",
    "get_active_patterns",
    "get_pattern_for_topic",
    "CrystallizationResult",
]
