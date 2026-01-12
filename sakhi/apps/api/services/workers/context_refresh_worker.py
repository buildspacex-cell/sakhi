from __future__ import annotations

import datetime as dt
from typing import List, Dict
from uuid import UUID

from sakhi.apps.api.core.db import q, exec as dbexec
from sakhi.libs.embeddings import to_pgvector


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


def _try_parse_uuid(value: str) -> UUID | None:
    try:
        return UUID(str(value))
    except Exception:
        return None


def _normalize_ts(ts: dt.datetime | None) -> dt.datetime | None:
    if not isinstance(ts, dt.datetime):
        return None
    if ts.tzinfo:
        return ts.astimezone(dt.timezone.utc).replace(tzinfo=None)
    return ts


def _coerce_vec(candidate: Any) -> list[float]:
    if candidate is None:
        return []
    if isinstance(candidate, (list, tuple)):
        try:
            return [float(x) for x in candidate]
        except Exception:
            return []
    if isinstance(candidate, (bytes, bytearray)):
        try:
            candidate = candidate.decode("utf-8")
        except Exception:
            return []
    if isinstance(candidate, str):
        text = candidate.strip()
        if text.startswith("[") and text.endswith("]"):
            text = text[1:-1]
        parts = [p.strip() for p in text.split(",") if p.strip()]
        try:
            return [float(p) for p in parts]
        except Exception:
            return []
    return []


async def refresh_context(person_id: str, ts: dt.datetime | str | None = None) -> Dict[str, object]:
    """
    Build merged_context_vector from memory_short_term + memory_episodic.
    Dedup by content_hash and drop entries older than 180 days.
    """
    if not person_id:
        return {"error": "missing_person"}

    ts_override: dt.datetime | None = None
    if isinstance(ts, dt.datetime):
        ts_override = _normalize_ts(ts)
    elif isinstance(ts, str):
        try:
            parsed = dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))
            ts_override = _normalize_ts(parsed)
        except Exception:
            ts_override = None
    now_ts = ts_override or _now()

    person_id_str = str(person_id)
    person_uuid = _try_parse_uuid(person_id_str)
    window_kind = "default"
    cutoff = now_ts - dt.timedelta(days=_DECAY_DAYS)
    rows = await q(
        """
        SELECT vector_vec AS vec, content_hash, updated_at
        FROM memory_short_term
        WHERE user_id = $1
        UNION ALL
        SELECT vector_vec AS vec, content_hash, updated_at
        FROM memory_episodic
        WHERE user_id = $1
           OR ($2::uuid IS NOT NULL AND person_id = $2::uuid)
        """,
        person_id_str,
        person_uuid,
    )

    seen = set()
    vectors: List[List[float]] = []
    for row in rows:
        content_hash = row.get("content_hash")
        if not content_hash or content_hash in seen:
            continue
        ts = _normalize_ts(row.get("updated_at"))
        if ts and ts < cutoff:
            continue
        vec = _coerce_vec(row.get("vec"))
        if not vec:
            continue
        seen.add(content_hash)
        vectors.append(vec)

    merged = _mean_vectors(vectors)
    merged_literal = to_pgvector(merged) if merged else None

    await dbexec(
        """
        INSERT INTO memory_context_cache (person_id, window_kind, merged_context_vector, updated_at)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (person_id, window_kind) DO UPDATE
        SET merged_context_vector = EXCLUDED.merged_context_vector,
            updated_at = EXCLUDED.updated_at
        """,
        person_id,
        window_kind,
        merged_literal,
        now_ts,
    )

    return {"person_id": person_id, "vector_length": len(merged)}


__all__ = ["refresh_context"]
