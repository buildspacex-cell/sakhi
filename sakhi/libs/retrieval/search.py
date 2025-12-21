"""High-level retrieval helpers."""

from __future__ import annotations

from typing import Any, List, Mapping

from .hybrid import HybridRetriever


async def search_journals(
    retriever: HybridRetriever | None,
    query: str,
    *,
    embedding: list[float] | None = None,
) -> List[Mapping[str, Any]]:
    """Search journal entries using the provided retriever instance."""

    if retriever is None:
        return [
            {
                "id": "stub",
                "content": f"Retrieval unavailable, echoing query: {query}",
                "score": 0.0,
            }
        ]

    results = await retriever.search(query, embedding=embedding)
    return [dict(result) for result in results]


__all__ = ["search_journals"]

