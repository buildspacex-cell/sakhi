"""Shared type utilities for the LLM router."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping


class Task(str, Enum):
    """Supported LLM task types."""

    CHAT = "chat"
    TOOL = "tool"
    # Embeddings are NOT routed. Use sakhi.libs.embeddings.embed_text(text).


@dataclass(slots=True)
class LLMResponse:
    """Normalised LLM response payload returned by providers."""

    model: str
    task: Task
    text: str | None = None
    tool_calls: list[dict[str, Any]] | None = None
    usage: Mapping[str, Any] | None = None
    cost: float | None = None
    provider: str | None = None
    raw: Mapping[str, Any] | None = None


__all__ = ["LLMResponse", "Task"]
