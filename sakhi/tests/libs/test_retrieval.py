import asyncio

import pytest

from sakhi.libs.retrieval.hybrid import HybridRetriever, RetrieverConfig


@pytest.mark.asyncio
async def test_hybrid_retriever_returns_stub_when_pool_missing() -> None:
    retriever = HybridRetriever(pool=None, config=RetrieverConfig(match_count=3))
    results = await retriever.search("breathing practice")

    assert len(results) == 1
    result = results[0]
    assert result["id"] == "stub"
    assert "breathing practice" in result["content"]
