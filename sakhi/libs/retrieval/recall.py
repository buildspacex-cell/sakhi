"""Hybrid recall scoring combining text, embeddings, salience, and recency."""

from __future__ import annotations

from datetime import datetime, timezone
from math import exp
from typing import Any, Dict, List, Sequence

from sakhi.libs.schemas.db import get_async_pool


def _recency_decay(timestamp: datetime) -> float:
    delta = datetime.now(timezone.utc) - timestamp
    days = max(delta.days, 0)
    return float(exp(-days / 14.0))


async def recall(
    user_id: str,
    query: str,
    k: int = 10,
    embedding: Sequence[float] | None = None,
) -> List[Dict[str, Any]]:
    pool = await get_async_pool()
    vector_literal = None
    if embedding:
        vector_literal = "(" + ",".join(f"{float(x):.8f}" for x in embedding) + ")"

    async with pool.acquire() as connection:
        rows = await connection.fetch(
            """
            WITH docs AS (
              SELECT je.id,
                     je.cleaned,
                     je.created_at,
                     COALESCE((je.facets_v2->>'sentiment')::float, 0) AS sent,
                     COALESCE((je.facets_v2->>'intent')::boolean, false) AS intent,
                     COALESCE((je.facets->>'salience')::float, 0.2) AS salience,
                     je.fts
              FROM journal_entries je
              JOIN journal_embeddings emb ON emb.entry_id = je.id
              WHERE je.user_id = $1
            ),
            fts AS (
              SELECT id, ts_rank_cd(fts, plainto_tsquery('english', $2)) AS fts_rank FROM docs
            ),
            vec AS (
              SELECT d.id,
                     CASE WHEN $3::text IS NULL THEN 0.0
                          ELSE 1 - (e.embedding <=> $3::vector)
                     END AS vscore
              FROM journal_embeddings e
              JOIN docs d ON d.id = e.entry_id
            ),
            base AS (
              SELECT d.id,
                     d.cleaned,
                     d.created_at,
                     COALESCE(f.fts_rank, 0) AS fts,
                     COALESCE(v.vscore, 0) AS vec,
                     d.salience
              FROM docs d
              LEFT JOIN fts f ON d.id = f.id
              LEFT JOIN vec v ON d.id = v.id
            )
            SELECT id,
                   LEFT(cleaned, 260) AS snippet,
                   created_at,
                   (0.5 * (fts + vec) + 0.3 * salience) AS score
            FROM base
            ORDER BY score DESC
            LIMIT $4
            """,
            user_id,
            query,
            vector_literal,
            k,
        )

    results: List[Dict[str, Any]] = []
    for row in rows:
        payload = dict(row)
        created_at = payload.get("created_at")
        if isinstance(created_at, datetime):
            payload["score"] = float(payload.get("score") or 0.0) * _recency_decay(created_at)
        else:
            payload["score"] = float(payload.get("score") or 0.0)
        results.append(payload)

    results.sort(key=lambda item: item.get("score", 0.0), reverse=True)
    return results
