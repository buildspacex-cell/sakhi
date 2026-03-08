"""Background job utilities for computing intention/action alignment."""

from __future__ import annotations

import json
import logging
from math import sqrt
from typing import Iterable, Sequence

from sakhi.libs.embeddings import embed_text
from sakhi.libs.security.journal_crypto import hydrate_journal_row
from sakhi.libs.schemas.db import get_async_pool

LOGGER = logging.getLogger(__name__)


async def _embed_texts(texts: Sequence[str]) -> Sequence[Sequence[float]]:
    """Return embedding vectors for the supplied texts."""

    if not texts:
        return []

    embeddings = await embed_text(list(texts))
    if isinstance(embeddings, list) and embeddings and isinstance(embeddings[0], list):
        return embeddings  # type: ignore[return-value]
    if isinstance(embeddings, list) and embeddings and isinstance(embeddings[0], (int, float)):
        return [embeddings]  # single vector fallback
    LOGGER.warning("Embedding pipeline returned unexpected payload; using zeros.")
    return [[0.0] * 1536 for _ in texts]


def _cosine_similarity(vec_a: Iterable[float], vec_b: Iterable[float]) -> float:
    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for a, b in zip(vec_a, vec_b):
        dot += a * b
        norm_a += a * a
        norm_b += b * b
    denom = sqrt(norm_a) * sqrt(norm_b) or 1e-8
    return round(dot / denom, 6)


async def compute_alignment(user_id: str, theme: str = "general") -> float:
    """Compute and persist alignment between user intentions and completed actions."""

    pool = await get_async_pool()
    async with pool.acquire() as connection:
        raw_journal_rows = await connection.fetch(
            """
            SELECT user_id, content, raw_encrypted, facets, created_at
            FROM journal_entries
            WHERE user_id = $1
            ORDER BY created_at DESC
            LIMIT 200
            """,
            user_id,
        )
        task_rows = await connection.fetch(
            """
            SELECT COALESCE(description, title) AS text
            FROM tasks
            WHERE user_id = $1
              AND status = 'completed'
            ORDER BY COALESCE(updated_at, created_at) DESC
            LIMIT 20
            """,
            user_id,
        )

    keyword_markers = ("intend", "goal", "plan", "decide", "priority")
    journal_rows = [hydrate_journal_row(dict(row)) for row in raw_journal_rows]
    intention_chunks: list[str] = []
    for row in journal_rows:
        text = (row.get("content") or "").strip()
        if not text:
            continue
        facets = row.get("facets") or {}
        if isinstance(facets, str):
            try:
                facets = json.loads(facets)
            except Exception:
                facets = {}
        has_intent_facet = False
        if isinstance(facets, dict):
            has_intent_facet = bool(facets.get("intent"))
        text_lower = text.lower()
        if has_intent_facet or any(marker in text_lower for marker in keyword_markers):
            intention_chunks.append(text)
        if len(intention_chunks) >= 20:
            break

    intentions_text = " ".join(intention_chunks) or "no intentions recorded"
    actions_text = " ".join((row["text"] or "").strip() for row in task_rows if row.get("text")) or "no actions completed"

    embeddings = await _embed_texts([intentions_text, actions_text])
    if len(embeddings) < 2:
        LOGGER.warning("Alignment embeddings unavailable for user_id=%s", user_id)
        similarity = 0.0
        intent_vec: Sequence[float] = []
        action_vec: Sequence[float] = []
    else:
        intent_vec = list(embeddings[0])
        action_vec = list(embeddings[1])
        similarity = _cosine_similarity(intent_vec, action_vec)

    async with pool.acquire() as connection:
        await connection.execute(
            """
            INSERT INTO alignment_scores (user_id, theme, intent_vec, action_vec, alignment)
            VALUES ($1, $2, $3, $4, $5)
            """,
            user_id,
            theme,
            intent_vec,
            action_vec,
            similarity,
        )

    return similarity
