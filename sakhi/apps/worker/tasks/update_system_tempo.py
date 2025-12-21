from __future__ import annotations

import datetime
import logging
from typing import List

import numpy as np

from sakhi.apps.api.core.db import get_db

LOGGER = logging.getLogger(__name__)


async def update_system_tempo() -> None:
    """Recalculate global breath tempo coherence from recent body metrics."""

    db = await get_db()
    try:
        LOGGER.info("[Breath] Updating system tempo coherence")
        rows = await db.fetch(
            """
            SELECT person_id, AVG(breath_rate) AS avg_breath
            FROM body_metrics
            WHERE ts > now() - interval '3 days'
            GROUP BY person_id
            """
        )
        now_phase = "inhale" if datetime.datetime.utcnow().second % 10 < 5 else "exhale"
        for row in rows:
            avg_breath = row.get("avg_breath") or 8.0
            tempo = max(6.0, min(12.0, float(avg_breath)))
            coherence = 1 - abs(tempo - 8.0) / 6.0
            await db.execute(
                """
                INSERT INTO system_tempo(person_id, phase, tempo, coherence)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (person_id)
                DO UPDATE SET phase = $2, tempo = $3, coherence = $4, updated_at = now()
                """,
                row["person_id"],
                now_phase,
                tempo,
                coherence,
            )
        LOGGER.info("[Breath] System tempo coherence updated for %s profiles", len(rows))
    finally:
        await db.close()


__all__ = ["update_system_tempo"]
