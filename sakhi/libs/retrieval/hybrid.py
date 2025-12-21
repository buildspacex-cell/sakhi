"""Hybrid retrieval primitives mixing FTS and pgvector."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import asyncpg


@dataclass(slots=True)
class RetrieverConfig:
    """Configurable knobs for the hybrid retrieval strategy."""

    table_name: str = "documents"
    text_column: str = "content"
    embedding_column: str = "embedding"
    match_count: int = 5


class HybridRetriever:
    """Coordinate hybrid search across Supabase Postgres."""

    def __init__(self, pool: asyncpg.Pool | None, config: RetrieverConfig | None = None) -> None:
        self._pool = pool
        self._config = config or RetrieverConfig()

    @classmethod
    async def create(cls, dsn: str, config: RetrieverConfig | None = None) -> "HybridRetriever":
        """Connect to Postgres and return a retriever instance."""

        pool = await asyncpg.create_pool(dsn)
        return cls(pool=pool, config=config)

    async def search(self, query: str, embedding: list[float] | None = None) -> list[dict[str, Any]]:
        """Run a hybrid search; falls back to a stub when metadata is absent."""

        if self._pool is None:
            # Allows local development to proceed without Postgres.
            return [
                {
                    "id": "stub",
                    "content": f"No database configured, echoing query: {query}",
                    "score": 0.0,
                }
            ]

        if embedding is None:
            sql = f"""
                with ranked as (
                    select
                        id,
                        {self._config.text_column} as content,
                        ts_rank_cd(to_tsvector('english', {self._config.text_column}), plainto_tsquery($1)) as score
                    from {self._config.table_name}
                )
                select id, content, score
                from ranked
                order by score desc nulls last
                limit $2
            """
            params: list[Any] = [query, self._config.match_count]
        else:
            sql = f"""
                with ranked as (
                    select
                        id,
                        {self._config.text_column} as content,
                        ts_rank_cd(to_tsvector('english', {self._config.text_column}), plainto_tsquery($1))
                        + coalesce(1 - ({self._config.embedding_column} <=> $2::vector), 0) as score
                    from {self._config.table_name}
                )
                select id, content, score
                from ranked
                order by score desc nulls last
                limit $3
            """
            params = [query, embedding, self._config.match_count]

        async with self._pool.acquire() as connection:
            try:
                rows = await connection.fetch(sql, *params)
            except Exception:
                return [
                    {
                        "id": "stub",
                        "content": f"Retrieval unavailable, echoing query: {query}",
                        "score": 0.0,
                    }
                ]

        return [dict(row) for row in rows]


__all__ = ["HybridRetriever", "RetrieverConfig"]
