from __future__ import annotations

import json
import os
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Sequence

import httpx

OPENAI_BASE = os.getenv("OPENAI_BASE", "https://api.openai.com/v1")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")


class OpenAIChat:
    """Minimal async client wrapper for OpenAI chat completions with guardrails."""

    def __init__(self, model: str = "gpt-4o-mini", *, timeout: float = 60.0) -> None:
        if not OPENAI_KEY:
            raise RuntimeError("OPENAI_API_KEY is not set")
        self.model = model
        self.timeout = timeout
        self.headers = {
            "Authorization": f"Bearer {OPENAI_KEY}",
            "Content-Type": "application/json",
        }

    async def chat(
        self,
        messages: Sequence[Mapping[str, Any]],
        **kwargs: Any,
    ) -> str:
        payload_kwargs: Dict[str, Any] = dict(kwargs)

        tools = payload_kwargs.get("tools")
        tool_choice = payload_kwargs.get("tool_choice")
        if tool_choice == "required" and not tools:
            payload_kwargs.pop("tool_choice", None)

        response_format = payload_kwargs.get("response_format")
        if response_format is not None and not isinstance(response_format, dict):
            payload_kwargs.pop("response_format", None)

        payload: Dict[str, Any] = {
            "model": payload_kwargs.pop("model", self.model),
            "messages": list(messages),
            "temperature": payload_kwargs.pop("temperature", 0.3),
            "max_tokens": payload_kwargs.pop("max_tokens", 400),
        }
        payload.update(payload_kwargs)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{OPENAI_BASE}/chat/completions",
                headers=self.headers,
                json=payload,
            )
            if response.status_code >= 400:
                try:
                    body = response.json()
                except ValueError:
                    body = response.text
                raise httpx.HTTPStatusError(
                    f"OpenAI request failed ({response.status_code}): {body}",
                    request=response.request,
                    response=response,
                )
            data = response.json()
        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError("OpenAI response missing choices field")
        message = (choices[0] or {}).get("message") or {}
        content = message.get("content")
        if content is None:
            raise RuntimeError("OpenAI response missing message content")
        return content
