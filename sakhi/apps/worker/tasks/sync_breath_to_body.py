from __future__ import annotations

import json
import logging

from sakhi.apps.api.core.db import get_db
from sakhi.apps.api.core.event_logger import log_event

LOGGER = logging.getLogger(__name__)


async def sync_breath_to_body(person_id: str) -> None:
    """Update body metrics and rhythm forecasts using recent breath session."""

    if not person_id:
        return

    db = await get_db()
    try:
        row = await db.fetchrow(
            """
            SELECT avg_breath_rate, calm_score
            FROM breath_sessions
            WHERE person_id = $1
            ORDER BY created_at DESC
            LIMIT 1
            """,
            person_id,
        )
        if not row:
            return

        breath_rate = row.get("avg_breath_rate")
        calm_score = row.get("calm_score")

        await db.execute(
            """
            INSERT INTO body_metrics(person_id, breath_rate, activity_level, source)
            VALUES ($1, $2, $3, 'breath')
            """,
            person_id,
            breath_rate,
            calm_score,
        )

        await db.execute(
            """
            INSERT INTO rhythm_events (person_id, event_ts, kind, payload, created_at)
            VALUES ($1, NOW(), 'breath', $2::jsonb, NOW())
            """,
            person_id,
            json.dumps(
                {
                    "source": "breath_session",
                    "calm_score": calm_score,
                    "breath_rate": breath_rate,
                },
                ensure_ascii=False,
            ),
        )
        await log_event(
            person_id,
            "breath",
            "Calm score applied",
            {"score": calm_score, "breath_rate": breath_rate},
        )
        LOGGER.info("[Breath] Integrated calm score %.2f for %s", calm_score or 0.0, person_id)
    finally:
        await db.close()


__all__ = ["sync_breath_to_body"]
