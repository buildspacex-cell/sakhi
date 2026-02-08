"""Health trends - longitudinal trend computation from body_state_history."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sakhi.apps.api.core.db import dbfetchall

logger = logging.getLogger(__name__)


async def compute_health_trends(
    person_id: str,
    window_days: int = 14,
) -> Dict[str, Any]:
    """
    Compute multi-day health trends from body_state_history.

    Uses simple linear regression direction on key metrics to determine
    if health signals are improving, declining, or stable.

    Args:
        person_id: User's ID
        window_days: Number of days to analyze (default 14)

    Returns:
        Dict with trend directions for key metrics and dosha trajectory.
    """
    rows = await dbfetchall(
        """
        SELECT overall_score, vata_score, pitta_score, kapha_score,
               ojas_level, sleep_quality, energy_level, computed_at
        FROM body_state_history
        WHERE person_id = $1
          AND computed_at > NOW() - INTERVAL '%s days'
        ORDER BY computed_at ASC
        """ % window_days,
        person_id,
    )

    if not rows or len(rows) < 3:
        return {
            "sleep_trend": "insufficient_data",
            "hrv_trend": "insufficient_data",
            "energy_trend": "insufficient_data",
            "ojas_trend": "insufficient_data",
            "dosha_trajectory": {
                "vata": "insufficient_data",
                "pitta": "insufficient_data",
                "kapha": "insufficient_data",
            },
            "data_points": len(rows) if rows else 0,
            "window_days": window_days,
        }

    return {
        "sleep_trend": _compute_trend([r.get("sleep_quality") for r in rows]),
        "energy_trend": _compute_trend([r.get("energy_level") for r in rows]),
        "ojas_trend": _compute_trend([r.get("ojas_level") for r in rows]),
        "overall_trend": _compute_trend([r.get("overall_score") for r in rows]),
        "dosha_trajectory": {
            "vata": _compute_trend([r.get("vata_score") for r in rows]),
            "pitta": _compute_trend([r.get("pitta_score") for r in rows]),
            "kapha": _compute_trend([r.get("kapha_score") for r in rows]),
        },
        "data_points": len(rows),
        "window_days": window_days,
    }


def _compute_trend(values: List[Optional[float]]) -> str:
    """
    Compute trend direction using simple linear regression slope.

    Returns: "improving", "declining", or "stable"
    For dosha scores, higher = more imbalance, so "improving" means declining dosha score.
    We return raw direction here; interpretation is done by the caller.
    """
    # Filter out None values, keeping indices for regression
    clean = [(i, v) for i, v in enumerate(values) if v is not None]
    if len(clean) < 3:
        return "insufficient_data"

    n = len(clean)
    sum_x = sum(i for i, _ in clean)
    sum_y = sum(v for _, v in clean)
    sum_xy = sum(i * v for i, v in clean)
    sum_x2 = sum(i * i for i, _ in clean)

    denominator = n * sum_x2 - sum_x * sum_x
    if denominator == 0:
        return "stable"

    slope = (n * sum_xy - sum_x * sum_y) / denominator

    # Determine magnitude threshold relative to mean
    mean_y = sum_y / n
    if mean_y == 0:
        return "stable"

    # Slope as percentage of mean per data point
    relative_slope = slope / mean_y

    if relative_slope > 0.02:  # >2% per data point
        return "improving"
    elif relative_slope < -0.02:
        return "declining"
    else:
        return "stable"


__all__ = [
    "compute_health_trends",
]
