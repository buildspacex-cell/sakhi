"""Sakhi LLMAdapter — bridges kala to sakhi.apps.api.core.llm."""

from __future__ import annotations

from typing import Any

from kala.adapters.base import LLMAdapter


class SakhiLLMAdapter(LLMAdapter):
    """Concrete LLM adapter using Sakhi's OpenAI call_llm."""

    async def complete(self, prompt: str, **kwargs: Any) -> str:
        from sakhi.apps.api.core.llm import call_llm

        result = await call_llm(prompt, **kwargs)
        if isinstance(result, dict):
            return result.get("reply") or result.get("text") or str(result)
        return str(result)
