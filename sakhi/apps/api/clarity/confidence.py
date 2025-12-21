from __future__ import annotations

from typing import Dict

from sakhi.apps.api.core.db import q


async def anchor_confidence_from_provenance(person_id: str) -> Dict[str, float]:
    rows = await q(
        """
        SELECT
            (
                SELECT COUNT(*)
                FROM aw_event
                WHERE person_id = $1
                  AND modality = 'text'
                  AND ts > NOW() - INTERVAL '14 days'
            ) AS recent_events,
            (
                SELECT COUNT(*)
                FROM preferences
                WHERE person_id = $1
            ) AS prefs,
            (
                SELECT COUNT(*)
                FROM goals
                WHERE person_id = $1
                  AND status IN ('active', 'proposed')
            ) AS goals
        """,
        person_id,
        one=True,
    ) or {}

    def scale(value: object) -> float:
        count = float(value or 0)
        return min(0.9, 0.3 + 0.08 * count)

    values_count = float(rows.get("prefs") or 0)
    return {
        "time": scale(rows.get("recent_events")),
        "energy": scale(rows.get("recent_events")),
        "finance": 0.4,
        "values": min(0.9, 0.5 + 0.05 * values_count),
    }
