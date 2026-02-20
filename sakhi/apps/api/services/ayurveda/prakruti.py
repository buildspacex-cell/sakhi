"""
Prakruti Service — Constitutional Type Computation

Prakruti (Sanskrit: "nature") represents the innate constitution a person
is born with. This baseline doesn't change but understanding it helps
interpret current state (Vikriti) deviations.

User-Facing Names (Friction Framework):
- Adaptive (Vata-dominant): Creative, quick-thinking, variable energy
- Performance (Pitta-dominant): Driven, focused, goal-oriented
- Conservation (Kapha-dominant): Steady, grounded, methodical

Combined types use hyphenated names: Adaptive-Performance, Performance-Conservation, etc.

Pure constitution math lives in ``kala.state.constitution``.
This module adds DB-backed storage + retrieval + history inference.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# Re-export pure computation from kala (single source of truth)
from kala.state.constitution import (  # noqa: F401
    CONSTITUTION_NAMES,
    DOSHA_FROM_NAME,
)
from kala.state.constitution import (
    compute_dosha_from_quiz as _compute_dosha_from_quiz,
)
from kala.state.constitution import (
    determine_constitution_type as _determine_constitution_type,
)
from sakhi.apps.api.core.db import exec as dbexec
from sakhi.apps.api.core.db import q as dbfetch

LOGGER = logging.getLogger(__name__)


async def compute_prakruti_from_onboarding(
    person_id: str,
    responses: Dict[str, Any],
    store: bool = True,
) -> Dict[str, Any]:
    """
    Compute Prakruti (constitutional type) from onboarding quiz responses.

    Args:
        person_id: The person's ID
        responses: Quiz response dictionary
        store: Whether to store in personal_model.operating_system

    Returns:
        Dict with type, primary dosha, dosha_baseline, and source
    """
    dosha_baseline = _compute_dosha_from_quiz(responses)
    primary, constitution_name = _determine_constitution_type(dosha_baseline)

    result = {
        "type": constitution_name,
        "primary": primary,
        "dosha_baseline": dosha_baseline,
        "source": "onboarding_quiz",
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }

    if store:
        try:
            # Store in personal_model.operating_system
            await dbexec(
                """
                UPDATE personal_model
                SET operating_system = $2::jsonb,
                    updated_at = NOW()
                WHERE person_id = $1
                """,
                person_id,
                result,
            )
            LOGGER.info(
                "[Prakruti] stored constitution",
                extra={
                    "person_id": person_id,
                    "type": constitution_name,
                    "primary": primary,
                },
            )
        except Exception as exc:
            LOGGER.warning(
                "[Prakruti] failed to store",
                extra={"person_id": person_id, "error": str(exc)},
            )

    return result


async def get_prakruti(person_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve stored Prakruti for a person.

    Returns None if not yet computed.
    """
    try:
        row = await dbfetch(
            """
            SELECT operating_system
            FROM personal_model
            WHERE person_id = $1
            """,
            person_id,
            one=True,
        )
        if row and row.get("operating_system"):
            os_data = row["operating_system"]
            # Handle case where data is stored as JSON string
            if isinstance(os_data, str):
                import json
                try:
                    os_data = json.loads(os_data)
                except json.JSONDecodeError:
                    return None
            return os_data
    except Exception as exc:
        LOGGER.warning(
            "[Prakruti] failed to retrieve",
            extra={"person_id": person_id, "error": str(exc)},
        )
    return None


async def infer_prakruti_from_history(
    person_id: str,
    window_days: int = 30,
) -> Optional[Dict[str, Any]]:
    """
    Infer Prakruti from historical episodic data if no onboarding quiz.

    Uses aggregated state_vector patterns over time to estimate baseline.
    This is a fallback for users who skip onboarding.
    """
    try:
        rows = await dbfetch(
            """
            SELECT state_vector
            FROM memory_episodic
            WHERE user_id = $1
              AND state_vector IS NOT NULL
              AND created_at > NOW() - INTERVAL '%s days'
            ORDER BY created_at ASC
            """ % window_days,
            person_id,
        )

        if not rows or len(rows) < 5:
            return None

        # Average the dosha scores across all episodes
        totals = {"vata": 0.0, "pitta": 0.0, "kapha": 0.0}
        count = 0

        for row in rows:
            sv = row.get("state_vector") or {}
            dosha = sv.get("dosha") or {}
            if dosha:
                totals["vata"] += dosha.get("vata", 0.33)
                totals["pitta"] += dosha.get("pitta", 0.33)
                totals["kapha"] += dosha.get("kapha", 0.34)
                count += 1

        if count == 0:
            return None

        # Average and normalize
        dosha_baseline = {k: round(v / count, 2) for k, v in totals.items()}
        total = sum(dosha_baseline.values())
        if total > 0:
            dosha_baseline = {k: round(v / total, 2) for k, v in dosha_baseline.items()}

        primary, constitution_name = _determine_constitution_type(dosha_baseline)

        return {
            "type": constitution_name,
            "primary": primary,
            "dosha_baseline": dosha_baseline,
            "source": "inferred_from_history",
            "episode_count": count,
            "computed_at": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as exc:
        LOGGER.warning(
            "[Prakruti] inference failed",
            extra={"person_id": person_id, "error": str(exc)},
        )
        return None


__all__ = [
    "compute_prakruti_from_onboarding",
    "get_prakruti",
    "infer_prakruti_from_history",
    "CONSTITUTION_NAMES",
    "DOSHA_FROM_NAME",
]
