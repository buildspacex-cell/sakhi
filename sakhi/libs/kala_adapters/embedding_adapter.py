"""Sakhi EmbeddingAdapter — bridges kala to sakhi.libs.embeddings."""

from __future__ import annotations

from collections.abc import Sequence

from kala.adapters.base import EmbeddingAdapter


class SakhiEmbeddingAdapter(EmbeddingAdapter):
    """Concrete embedding adapter using Sakhi's OpenAI embeddings."""

    async def embed(self, text: str) -> list[float]:
        from sakhi.libs.embeddings import embed_text

        result = await embed_text(text)
        # embed_text returns List[float] for a single string
        if isinstance(result[0], list):
            return result[0]
        return result

    async def embed_batch(self, texts: Sequence[str]) -> list[list[float]]:
        from sakhi.libs.embeddings import embed_text

        result = await embed_text(list(texts))
        # embed_text returns List[List[float]] for a list of strings
        if result and not isinstance(result[0], list):
            return [result]
        return result
