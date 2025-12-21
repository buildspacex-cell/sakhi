"""Shared chat schemas for Sakhi."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class Message(BaseModel):
    """Represents a single conversational message."""

    role: Literal["system", "user", "assistant"]
    content: str
    metadata: dict[str, Any] | None = Field(default=None, description="Arbitrary tool metadata")


class ChatRequest(BaseModel):
    """Payload for requesting a response from the LLM router."""

    conversation_id: str = Field(min_length=1)
    messages: list[Message]
    tools: list[dict[str, Any] | str] = Field(
        default_factory=list,
        description="Optional tool definitions or identifiers",
    )


class ChatResponse(BaseModel):
    """Simplified response envelope returned by the LLM router."""

    conversation_id: str
    message: Message
    usage: dict[str, Any] = Field(default_factory=dict)


__all__ = ["ChatRequest", "ChatResponse", "Message"]
