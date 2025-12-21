from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional, Sequence, Tuple

from sakhi.libs.embeddings import embed_text, parse_pgvector
from sakhi.libs.schemas.db import get_async_pool

SIM_MATCH = 0.80
SIM_MAYBE = 0.65


def _recency_boost(minutes_since: float) -> float:
    if minutes_since <= 60:
        return 0.10
    if minutes_since <= 360:
        return 0.05
    return 0.0


async def list_candidates(user_id: str, limit: int = 6) -> List[Dict]:
    pool = await get_async_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, slug, title, last_active_at, summary_vec
            FROM conversation_sessions
            WHERE user_id = $1 AND status = 'active'
            ORDER BY last_active_at DESC
            LIMIT $2
            """,
            user_id,
            limit,
        )
    return [dict(row) for row in rows]


async def best_match(user_id: str, text: str) -> Tuple[Optional[Dict], float]:
    candidates = await list_candidates(user_id)
    if not candidates:
        return None, 0.0

    query_vec = await embed_text(text)
    best: Optional[Dict] = None
    best_score = 0.0
    now = datetime.now(timezone.utc)

    for candidate in candidates:
        vec = parse_pgvector(candidate.get("summary_vec"))
        if len(vec) != len(query_vec):
            continue

        score = _cosine_similarity(query_vec, vec)
        minutes_since = (
            (now - candidate.get("last_active_at", now)).total_seconds() / 60.0
            if candidate.get("last_active_at")
            else 9999
        )
        score += _recency_boost(minutes_since)
        if score > best_score:
            best = candidate
            best_score = score

    return best, best_score


def _cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    if not a or not b:
        return 0.0
    numerator = sum(x * y for x, y in zip(a, b))
    denom_a = sum(x * x for x in a) ** 0.5
    denom_b = sum(y * y for y in b) ** 0.5
    if denom_a == 0 or denom_b == 0:
        return 0.0
    return numerator / (denom_a * denom_b)
