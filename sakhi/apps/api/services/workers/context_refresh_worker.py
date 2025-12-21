from __future__ import annotations

import datetime as dt
from typing import List, Dict

from sakhi.apps.api.core.db import q, exec as dbexec


_DECAY_DAYS = 180
_VECTOR_DIM = 1536


def _now() -> dt.datetime:
    return dt.datetime.utcnow()


def _mean_vectors(vectors: List[List[float]]) -> List[float]:
    if not vectors:
        return []
    length = min(len(v) for v in vectors if v) if vectors[0] else _VECTOR_DIM
    acc = [0.0] * length
    for vec in vectors:
        for i in range(length):
            acc[i] += float(vec[i])
    return [value / len(vectors) for value in acc]


async def refresh_context(person_id: str) -> Dict[str, object]:
    """
    Build merged_context_vector from memory_short_term + memory_episodic.
    Dedup by content_hash and drop entries older than 180 days.
    """
    if not person_id:
        return {"error": "missing_person"}

    cutoff = _now() - dt.timedelta(days=_DECAY_DAYS)
    rows = await q(
        """
        SELECT vector_vec AS vec, content_hash, updated_at
        FROM memory_short_term
        WHERE person_id = $1
        UNION ALL
        SELECT vector_vec AS vec, content_hash, updated_at
        FROM memory_episodic
        WHERE person_id = $1
        """,
        person_id,
    )

    seen = set()
    vectors: List[List[float]] = []
    for row in rows:
        content_hash = row.get("content_hash")
        if not content_hash or content_hash in seen:
            continue
        ts = row.get("updated_at")
        if ts and isinstance(ts, dt.datetime) and ts < cutoff:
            continue
        vec = row.get("vec") or []
        if vec:
            seen.add(content_hash)
            vectors.append(list(vec))

    merged = _mean_vectors(vectors)

    await dbexec(
        """
        INSERT INTO memory_context_cache (person_id, merged_context_vector, updated_at)
        VALUES ($1, $2, now())
        ON CONFLICT (person_id) DO UPDATE
        SET merged_context_vector = EXCLUDED.merged_context_vector,
            updated_at = EXCLUDED.updated_at
        """,
        person_id,
        merged if merged else None,
    )

    return {"person_id": person_id, "vector_length": len(merged)}


__all__ = ["refresh_context"]
