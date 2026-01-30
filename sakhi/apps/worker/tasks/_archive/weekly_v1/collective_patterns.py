from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Tuple

import numpy as np

from sakhi.apps.api.core.db import get_db

LOGGER = logging.getLogger(__name__)


async def aggregate_embeddings(rows: List[Dict[str, Any]], noise: float = 0.02) -> Tuple[List[float], List[float], int]:
    """Compute anonymized mean/std with differential privacy noise."""

    if not rows:
        return [], [], 0

    embeddings = np.stack([np.asarray(row["embedding"], dtype=float) for row in rows])
    mean = embeddings.mean(axis=0)
    std = embeddings.std(axis=0)
    if noise and noise > 0:
        mean += np.random.laplace(0, noise, mean.shape)
        std += np.random.laplace(0, noise, std.shape)
    return mean.tolist(), std.tolist(), embeddings.shape[0]


async def collect_patterns_weekly() -> None:
    """
    Aggregate anonymized embedding statistics for collective rhythm patterns.
    """

    db = await get_db()
    try:
        LOGGER.info("[Collective] Starting weekly pattern aggregation")
        rows = await db.fetch(
            """
            SELECT
                COALESCE(je.person_id, je.user_id) AS person_id,
                emb.embedding,
                emb.created_at,
                COALESCE(je.facets_v2->>'theme', je.facets->>'theme', 'general') AS theme
            FROM journal_embeddings AS emb
            JOIN journal_entries AS je
              ON je.id = emb.entry_id
            WHERE emb.created_at >= now() - interval '7 days'
              AND COALESCE(je.person_id, je.user_id) IS NOT NULL
            """
        )
        if not rows:
            LOGGER.info("[Collective] No data to aggregate this week")
            return

        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for row in rows:
            pattern_type = row.get("theme") or "general"
            grouped.setdefault(pattern_type, []).append(row)

        for pattern_type, subset in grouped.items():
            mean_vec, std_vec, support = await aggregate_embeddings(subset)
            if support == 0:
                continue
            await db.execute(
                """
                INSERT INTO collective_patterns(pattern_type, mean_vector, std_dev_vector, support_count, last_updated)
                VALUES ($1, $2::jsonb, $3::jsonb, $4, now())
                ON CONFLICT (pattern_type) DO UPDATE
                  SET mean_vector = $2::jsonb,
                      std_dev_vector = $3::jsonb,
                      support_count = collective_patterns.support_count + $4,
                      last_updated = now()
                """,
                pattern_type,
                json.dumps(mean_vec, ensure_ascii=False),
                json.dumps(std_vec, ensure_ascii=False),
                support,
            )

        LOGGER.info("[Collective] Aggregated %s pattern types", len(grouped))
    finally:
        await db.close()


__all__ = ["aggregate_embeddings", "collect_patterns_weekly"]
