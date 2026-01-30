from __future__ import annotations

import json
import logging
import os
from typing import Dict, List

import numpy as np

from sakhi.apps.api.core.db import get_db

LOGGER = logging.getLogger(__name__)
LEARNING_RATE = float(os.getenv("RHYTHM_LEARNING_RATE", "0.1"))
MIN_SUPPORT = int(os.getenv("COLLECTIVE_MIN_SUPPORT", "10"))


async def apply_rhythm_adjustments() -> None:
    """
    Adjust user rhythm embeddings toward collective patterns with DP-safe updates.
    """

    db = await get_db()
    try:
        LOGGER.info("[Rhythm] Starting rhythm model self-adjustment")
        patterns = await db.fetch(
            """
            SELECT pattern_type, mean_vector
            FROM collective_patterns
            WHERE support_count >= $1
            """,
            MIN_SUPPORT,
        )
        if not patterns:
            LOGGER.info("[Rhythm] No collective patterns meet support threshold")
            return

        pattern_map: Dict[str, np.ndarray] = {
            row["pattern_type"]: np.asarray(row["mean_vector"], dtype=float)
            for row in patterns
        }

        forecasts = await db.fetch(
            """
            SELECT person_id, pattern_type, embedding
            FROM rhythm_forecasts
            WHERE created_at > now() - interval '7 days'
              AND array_length(embedding, 1) = 1536
            """
        )

        updated = 0
        for forecast in forecasts:
            collective_vec = pattern_map.get(forecast.get("pattern_type"))
            if collective_vec is None:
                continue

            user_vec = np.asarray(forecast["embedding"], dtype=float)
            delta = (collective_vec - user_vec) * LEARNING_RATE
            new_vec = user_vec + delta

            await db.execute(
                """
                UPDATE rhythm_forecasts
                SET embedding = $1
                WHERE person_id = $2 AND pattern_type = $3
                """,
                json.dumps(new_vec.tolist(), ensure_ascii=False),
                forecast["person_id"],
                forecast["pattern_type"],
            )
            await db.execute(
                """
                INSERT INTO model_adjustments(person_id, pattern_type, delta, learning_rate, applied_at)
                VALUES ($1, $2, $3, $4, now())
                """,
                forecast["person_id"],
                forecast["pattern_type"],
                json.dumps(delta.tolist(), ensure_ascii=False),
                LEARNING_RATE,
            )
            updated += 1

        LOGGER.info("[Rhythm] Adjusted %s forecasts using collective patterns", updated)
    finally:
        await db.close()


__all__ = ["apply_rhythm_adjustments"]
