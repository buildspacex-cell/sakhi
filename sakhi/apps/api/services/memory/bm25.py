"""
BM25 Keyword Search for Sakhi Memory
------------------------------------
Implements keyword-based search using PostgreSQL full-text search.
Borrowed from OpenClaw's hybrid search approach.

Combined with vector similarity for better recall accuracy:
- Vector search: semantic similarity (0.7 weight)
- BM25 search: exact keyword matches (0.3 weight)

This catches cases where pure vector similarity misses exact matches.
E.g., "Manali cabin" should find the exact mention, not just similar concepts.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Tuple, Optional

from sakhi.apps.api.core.db import q as dbfetch

LOGGER = logging.getLogger(__name__)


async def bm25_search_journals(
    person_id: str,
    query: str,
    limit: int = 30,
) -> List[Tuple[str, float]]:
    """
    BM25 keyword search on journal entries using PostgreSQL ts_rank.

    Uses ts_rank_cd for cover density ranking which gives better results
    for proximity-based queries.

    Returns:
        List of (entry_id, normalized_score) tuples
    """
    if not query or not query.strip():
        return []

    try:
        rows = await dbfetch(
            """
            SELECT
                id,
                ts_rank_cd(
                    to_tsvector('english', COALESCE(content, '')),
                    plainto_tsquery('english', $2),
                    32  -- normalization: divide rank by document length
                ) as rank
            FROM journal_entries
            WHERE user_id = $1
              AND to_tsvector('english', COALESCE(content, '')) @@ plainto_tsquery('english', $2)
            ORDER BY rank DESC
            LIMIT $3
            """,
            person_id,
            query,
            limit,
        )

        if not rows:
            return []

        # Normalize scores to 0-1 range
        max_score = max(r["rank"] for r in rows) if rows else 1.0
        if max_score == 0:
            max_score = 1.0

        return [
            (str(r["id"]), float(r["rank"]) / max_score)
            for r in rows
        ]

    except Exception as e:
        LOGGER.warning("[BM25] Journal search failed: %s", e)
        return []


async def bm25_search_reflections(
    person_id: str,
    query: str,
    limit: int = 20,
) -> List[Tuple[str, float]]:
    """
    BM25 keyword search on reflections.

    Returns:
        List of (reflection_id, normalized_score) tuples
    """
    if not query or not query.strip():
        return []

    try:
        rows = await dbfetch(
            """
            SELECT
                id,
                ts_rank_cd(
                    to_tsvector('english', COALESCE(content, '') || ' ' || COALESCE(theme, '')),
                    plainto_tsquery('english', $2),
                    32
                ) as rank
            FROM reflections
            WHERE user_id = $1
              AND to_tsvector('english', COALESCE(content, '') || ' ' || COALESCE(theme, ''))
                  @@ plainto_tsquery('english', $2)
            ORDER BY rank DESC
            LIMIT $3
            """,
            person_id,
            query,
            limit,
        )

        if not rows:
            return []

        max_score = max(r["rank"] for r in rows) if rows else 1.0
        if max_score == 0:
            max_score = 1.0

        return [
            (str(r["id"]), float(r["rank"]) / max_score)
            for r in rows
        ]

    except Exception as e:
        LOGGER.warning("[BM25] Reflection search failed: %s", e)
        return []


async def bm25_search_memory_nodes(
    person_id: str,
    query: str,
    limit: int = 20,
) -> List[Tuple[str, float]]:
    """
    BM25 keyword search on memory graph nodes.

    Returns:
        List of (node_id, normalized_score) tuples
    """
    if not query or not query.strip():
        return []

    try:
        rows = await dbfetch(
            """
            SELECT
                id,
                ts_rank_cd(
                    to_tsvector('english', COALESCE(label, '') || ' ' || COALESCE(node_kind, '')),
                    plainto_tsquery('english', $2),
                    32
                ) as rank
            FROM memory_nodes
            WHERE person_id = $1
              AND to_tsvector('english', COALESCE(label, '') || ' ' || COALESCE(node_kind, ''))
                  @@ plainto_tsquery('english', $2)
            ORDER BY rank DESC
            LIMIT $3
            """,
            person_id,
            query,
            limit,
        )

        if not rows:
            return []

        max_score = max(r["rank"] for r in rows) if rows else 1.0
        if max_score == 0:
            max_score = 1.0

        return [
            (str(r["id"]), float(r["rank"]) / max_score)
            for r in rows
        ]

    except Exception as e:
        LOGGER.warning("[BM25] Memory node search failed: %s", e)
        return []


async def bm25_search_facts(
    person_id: str,
    query: str,
    limit: int = 20,
) -> List[Tuple[str, float]]:
    """
    BM25 keyword search on facts.

    Returns:
        List of (fact_id, normalized_score) tuples
    """
    if not query or not query.strip():
        return []

    try:
        rows = await dbfetch(
            """
            SELECT
                id,
                ts_rank_cd(
                    to_tsvector('english', COALESCE(key, '') || ' ' || COALESCE(value, '')),
                    plainto_tsquery('english', $2),
                    32
                ) as rank
            FROM facts
            WHERE person_id = $1
              AND to_tsvector('english', COALESCE(key, '') || ' ' || COALESCE(value, ''))
                  @@ plainto_tsquery('english', $2)
            ORDER BY rank DESC
            LIMIT $3
            """,
            person_id,
            query,
            limit,
        )

        if not rows:
            return []

        max_score = max(r["rank"] for r in rows) if rows else 1.0
        if max_score == 0:
            max_score = 1.0

        return [
            (str(r["id"]), float(r["rank"]) / max_score)
            for r in rows
        ]

    except Exception as e:
        LOGGER.warning("[BM25] Facts search failed: %s", e)
        return []


async def bm25_search_all(
    person_id: str,
    query: str,
    limit: int = 30,
) -> Dict[str, Dict[str, float]]:
    """
    Run BM25 search across all memory sources in parallel.

    Returns:
        Dict mapping source_type to {id: score} dict
        E.g., {"journal": {"uuid1": 0.8, "uuid2": 0.5}, "reflection": {...}}
    """
    import asyncio

    # Run all searches in parallel
    journal_task = bm25_search_journals(person_id, query, limit)
    reflection_task = bm25_search_reflections(person_id, query, limit)
    node_task = bm25_search_memory_nodes(person_id, query, limit)
    fact_task = bm25_search_facts(person_id, query, limit)

    results = await asyncio.gather(
        journal_task,
        reflection_task,
        node_task,
        fact_task,
        return_exceptions=True,
    )

    # Process results
    output: Dict[str, Dict[str, float]] = {
        "journal": {},
        "reflection": {},
        "node": {},
        "fact": {},
    }

    source_names = ["journal", "reflection", "node", "fact"]

    for i, result in enumerate(results):
        if isinstance(result, Exception):
            LOGGER.warning("[BM25] Search for %s failed: %s", source_names[i], result)
            continue
        if isinstance(result, list):
            output[source_names[i]] = {id_: score for id_, score in result}

    return output


def merge_hybrid_scores(
    vector_score: float,
    keyword_score: float,
    vector_weight: float = 0.7,
    keyword_weight: float = 0.3,
) -> float:
    """
    Merge vector similarity and BM25 keyword scores.

    Formula borrowed from OpenClaw's hybrid search:
    final_score = vector_weight * vector_score + keyword_weight * keyword_score

    Default weights: 0.7 vector + 0.3 keyword

    This ensures:
    - Semantic similarity still dominates
    - Exact keyword matches get a boost
    - "Manali cabin" finds the exact mention first
    """
    return (vector_weight * vector_score) + (keyword_weight * keyword_score)


__all__ = [
    "bm25_search_journals",
    "bm25_search_reflections",
    "bm25_search_memory_nodes",
    "bm25_search_facts",
    "bm25_search_all",
    "merge_hybrid_scores",
]
