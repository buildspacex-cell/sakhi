"""Abstract adapter interfaces for external dependencies.

Kala is dependency-agnostic — it defines what it needs via these ABCs.
Consuming applications (e.g. Sakhi) provide concrete implementations
that bridge to their specific DB, embedding, and LLM infrastructure.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any


class DatabaseAdapter(ABC):
    """Abstract database interface for temporal state storage."""

    @abstractmethod
    async def fetch(self, sql: str, *args: Any) -> list[dict[str, Any]]:
        """Execute a query and return all rows as dicts."""
        ...

    @abstractmethod
    async def fetch_one(self, sql: str, *args: Any) -> dict[str, Any] | None:
        """Execute a query and return the first row, or None."""
        ...

    @abstractmethod
    async def execute(self, sql: str, *args: Any) -> str:
        """Execute a statement (INSERT/UPDATE/DELETE)."""
        ...


class EmbeddingAdapter(ABC):
    """Abstract embedding interface for vector operations."""

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """Generate an embedding vector for the given text."""
        ...

    @abstractmethod
    async def embed_batch(self, texts: Sequence[str]) -> list[list[float]]:
        """Generate embedding vectors for multiple texts."""
        ...


class LLMAdapter(ABC):
    """Abstract LLM interface for text generation."""

    @abstractmethod
    async def complete(self, prompt: str, **kwargs: Any) -> str:
        """Generate a completion for the given prompt."""
        ...
