from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, List

from sakhi.apps.api.core.db import q as dbfetch
from sakhi.libs.embeddings import to_pgvector

LOGGER = logging.getLogger(__name__)


async def retrieve_episodic_slices(
    *,
    user_id: str,
    query_vector: List[float],
    k: int = 5,
    days_back: int = 1500,  # TODO: tighten this window after debugging lab historical runs
    min_similarity: float = 0.15,
) -> List[Dict]:
    """
    Read-only episodic retrieval.
    Returns ranked episodic slices relevant to the query.
    """
    if k <= 0:
        return []

    vector_literal = to_pgvector(query_vector)
    limit = max(k * 3, k)
    rows = await dbfetch(
        f"""
        SELECT
          id,
          text,
          record,
          ts,
          created_at,
          context_tags,
          1 - (vector_vec <=> $1) AS similarity
        FROM memory_episodic
        WHERE user_id = $2
          AND vector_vec IS NOT NULL
          AND ts >= NOW() - INTERVAL '{days_back} days'
        ORDER BY vector_vec <=> $1
        LIMIT $3;
        """,
        vector_literal,
        user_id,
        limit,
    )

    now = datetime.now(timezone.utc)
    candidates: List[Dict] = []
    for row in rows:
        sim = float(row.get("similarity") or 0.0)
        if sim < min_similarity:
            continue

        ts_val = row.get("ts")
        if isinstance(ts_val, datetime):
            ts = ts_val if ts_val.tzinfo else ts_val.replace(tzinfo=timezone.utc)
        else:
            try:
                ts = datetime.fromisoformat(str(ts_val)).replace(tzinfo=timezone.utc)
            except Exception:
                ts = now

        days_ago = max(0, (now - ts).days)
        decay = max(0.3, 1.0 - (days_ago / days_back))
        score = sim * decay

        record = row.get("record") or {}
        if isinstance(record, str):
            try:
                import json

                record = json.loads(record)
            except Exception:
                record = {}

        payload = {
            "episode_id": str(row.get("id")),
            "summary": row.get("text") or "",
            "window_start": (record or {}).get("window_start"),
            "window_end": (record or {}).get("window_end"),
            "ts": ts.isoformat(),
            "similarity": sim,
            "score": score,
            "context_tags": row.get("context_tags") or [],
        }
        candidates.append(payload)

    candidates.sort(key=lambda item: item.get("score", 0.0), reverse=True)
    result = candidates[:k]
    LOGGER.info(
        "[episodic_retrieval] user_id=%s candidates=%s returned=%s",
        user_id,
        len(candidates),
        len(result),
    )
    return result


__all__ = ["retrieve_episodic_slices"]
