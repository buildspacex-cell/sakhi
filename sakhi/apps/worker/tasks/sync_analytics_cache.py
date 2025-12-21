from __future__ import annotations

import logging

from sakhi.apps.api.core.db import get_db
from sakhi.apps.api.core.event_logger import log_event

LOGGER = logging.getLogger(__name__)


async def sync_analytics_cache() -> None:
    """Nightly job to refresh cached analytics metrics."""

    db = await get_db()
    try:
        LOGGER.info("[Analytics] Nightly cache sync started")
        profiles = await db.fetch("SELECT user_id FROM profiles")
        for profile in profiles:
            person_id = profile.get("user_id")
            if not person_id:
                continue

            clarity = await db.fetchrow(
                """
                SELECT
                    COALESCE(AVG(coherence), 0) AS value
                FROM reflections
                WHERE user_id = $1 AND created_at > now() - interval '7 days'
                """,
                person_id,
            )
            energy = await db.fetchrow(
                """
                SELECT AVG(predicted_energy) AS value
                FROM rhythm_forecasts
                WHERE person_id = $1 AND created_at > now() - interval '7 days'
                """,
                person_id,
            )
            tone = await db.fetchrow(
                """
                SELECT mode() WITHIN GROUP (ORDER BY dominant_emotion) AS tone
                FROM emotional_tones
                WHERE person_id = $1 AND created_at > now() - interval '7 days'
                """,
                person_id,
            )

            metrics = {
                "clarity_index": float((clarity or {}).get("value") or 0.0),
                "energy_index": float((energy or {}).get("value") or 0.0),
            }
            for metric, value in metrics.items():
                await db.execute(
                    """
                    DELETE FROM analytics_cache
                    WHERE person_id = $1 AND metric = $2 AND period = 'weekly'
                    """,
                    person_id,
                    metric,
                )
                await db.execute(
                    """
                    INSERT INTO analytics_cache(person_id, metric, value, period, computed_at)
                    VALUES ($1, $2, $3, 'weekly', now())
                    """,
                    person_id,
                    metric,
                    value,
                )

            if tone and tone.get("tone"):
                await db.execute(
                    """
                    DELETE FROM analytics_cache
                    WHERE person_id = $1 AND metric = 'dominant_tone' AND period = 'weekly'
                    """,
                    person_id,
                )
                await db.execute(
                    """
                    INSERT INTO analytics_cache(person_id, metric, value, period, computed_at)
                    VALUES ($1, 'dominant_tone', 0, 'weekly', now())
                    """,
                    person_id,
                )

            LOGGER.info("[Analytics] Cached summary for %s", person_id)
            await log_event(
                person_id,
                "analytics",
                "Cache refreshed",
                {"clarity": metrics["clarity_index"], "energy": metrics["energy_index"]},
            )

        LOGGER.info("[Analytics] Nightly cache sync complete")
    finally:
        await db.close()


__all__ = ["sync_analytics_cache"]
