"""Abstract provider interfaces for the LLM router."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Mapping, Sequence

from .types import LLMResponse


class BaseProvider(ABC):
    """Common interface all LLM providers must implement."""

    def __init__(self, name: str) -> None:
        self.name = name

    @abstractmethod
    async def chat(
        self,
        *,
        messages: Sequence[Mapping[str, Any]],
        model: str,
        tools: Sequence[Mapping[str, Any]] | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Perform a chat completion request."""

    async def embed(self, *args: Any, **kwargs: Any) -> LLMResponse:  # pragma: no cover
        """Embeddings are handled outside the router."""
        raise NotImplementedError(
            "Embedding is disabled for providers. Use sakhi.libs.embeddings.embed_text(text)."
        )


__all__ = ["BaseProvider"]
