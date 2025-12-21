"""OpenAI provider implementation for the Sakhi LLM router."""

from __future__ import annotations

import asyncio
import os
from typing import Any, Mapping, Optional, Sequence

try:  # pragma: no cover - dependency optional in some environments
    import openai
    from openai import AsyncOpenAI
except ModuleNotFoundError:  # pragma: no cover - provide graceful fallback
    openai = None  # type: ignore[assignment]
    AsyncOpenAI = None  # type: ignore[assignment]


from .base import BaseProvider
from .types import LLMResponse, Task

if openai is not None:
    AuthenticationError = openai.AuthenticationError
    RateLimitError = openai.RateLimitError
    APIConnectionError = openai.APIConnectionError
else:  # pragma: no cover - fallback types when dependency missing
    class _MissingDependencyError(Exception):
        """Raised when the OpenAI client dependency is missing."""

    AuthenticationError = RateLimitError = APIConnectionError = _MissingDependencyError

_OPENAI_CLIENT: Optional[AsyncOpenAI] = None
_OPENAI_CLIENT_KEY: Optional[str] = None


def _get_openai_client() -> AsyncOpenAI:
    global _OPENAI_CLIENT, _OPENAI_CLIENT_KEY

    if AsyncOpenAI is None:
        raise RuntimeError(
            "OpenAI connection error: Missing 'openai' package. Install it with `pip install openai`."
        )

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OpenAI connection error: Missing OPENAI_API_KEY")

    if _OPENAI_CLIENT is None or _OPENAI_CLIENT_KEY != api_key:
        _OPENAI_CLIENT = AsyncOpenAI(api_key=api_key)
        _OPENAI_CLIENT_KEY = api_key

    return _OPENAI_CLIENT

class OpenAIProvider(BaseProvider):
    """Provider that talks directly to OpenAI's REST API."""

    def __init__(
        self,
        api_key: str,
        *,
        model_chat: str,
        model_embed: str | None = None,
        timeout: float = 30.0,
        base_url: str | None = None,
    ) -> None:
        super().__init__(name="openai")
        self._api_key = api_key
        self._model_chat = model_chat
        self._model_embed = model_embed or "text-embedding-3-small"
        self._timeout = timeout
        self._base_url = (base_url or os.getenv("OPENAI_BASE", "https://api.openai.com/v1")).rstrip("/")
        self._chat_url = f"{self._base_url}/chat/completions"
        self._embed_url = f"{self._base_url}/embeddings"
        self._headers = _headers(self._api_key)

    async def chat(
        self,
        *,
        messages: Sequence[dict[str, Any]],
        model: str | None = None,
        tools: Sequence[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        if not isinstance(messages, Sequence) or not messages:
            raise ValueError("OpenAI provider: 'messages' must be a non-empty sequence.")

        normalised_messages: list[dict[str, Any]] = []
        for message in messages:
            if not isinstance(message, Mapping):
                raise ValueError("Each message must be a mapping with 'role' and 'content'.")
            normalised_messages.append(dict(message))

        tools_list = list(tools) if tools else []
        kwargs = dict(kwargs)
        force_json = bool(kwargs.pop("force_json", False))
        tool_choice = kwargs.pop("tool_choice", None)
        response_format = kwargs.pop("response_format", None)
        temperature = kwargs.pop("temperature", 0.3)
        max_tokens = kwargs.pop("max_tokens", 400)

        if tool_choice == "required" and not tools_list:
            tool_choice = None

        if response_format is not None and not isinstance(response_format, Mapping):
            response_format = None

        if force_json and response_format is None:
            response_format = {"type": "json_object"}

        try:
            max_tokens = int(max_tokens)
        except (TypeError, ValueError):  # pragma: no cover - defensive
            max_tokens = 400
        if max_tokens <= 0:
            max_tokens = 400

        if not isinstance(temperature, (int, float)):
            temperature = 0.3
        else:
            temperature = float(temperature)

        for penalty in ("presence_penalty", "frequency_penalty"):
            if penalty in kwargs:
                value = kwargs[penalty]
                if isinstance(value, (int, float)):
                    kwargs[penalty] = max(-2.0, min(2.0, float(value)))
                else:
                    kwargs.pop(penalty)

        payload: dict[str, Any] = {
            "model": model or self._model_chat,
            "messages": normalised_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs,
        }
        if tools_list:
            payload["tools"] = tools_list
        if tool_choice:
            payload["tool_choice"] = tool_choice
        if response_format:
            payload["response_format"] = response_format

        try:
            client = _get_openai_client()
            try:
                response = await asyncio.wait_for(
                    client.chat.completions.create(**payload),
                    timeout=45,
                )
            except Exception as inner_exc:
                raise RuntimeError(f"OpenAI chat failed: {inner_exc}") from inner_exc
        except AuthenticationError as e:
            print("❌ OpenAI Authentication Error:", e)
            raise RuntimeError("OpenAI connection error: Invalid API key or unauthorized request") from e
        except RateLimitError as e:
            print("⚠️ OpenAI Rate Limit:", e)
            raise RuntimeError("OpenAI connection error: Rate limit reached") from e
        except APIConnectionError as e:
            print("🌐 Network error talking to OpenAI:", e)
            raise RuntimeError("OpenAI connection error: Network failure") from e
        except asyncio.TimeoutError as e:
            print("⏱️ OpenAI call timed out")
            raise RuntimeError("OpenAI connection error: Timeout") from e
        except Exception as e:  # pragma: no cover - defensive
            print("💥 LLM call failed:", repr(e))
            raise RuntimeError(f"OpenAI connection error: {e}") from e

        choice = response.choices[0] if response.choices else None
        message = getattr(choice, "message", None)
        text_content = ""
        if message is not None:
            text_content = getattr(message, "content", "") or ""
        raw_tool_calls = getattr(message, "tool_calls", None) if message is not None else None
        tool_calls_list: list[dict[str, Any]] = []
        if raw_tool_calls:
            for call in raw_tool_calls:
                if hasattr(call, "model_dump"):
                    tool_calls_list.append(call.model_dump())
                elif isinstance(call, Mapping):
                    tool_calls_list.append(dict(call))

        usage = response.usage
        if usage and hasattr(usage, "model_dump"):
            usage_dict = usage.model_dump()
        elif isinstance(usage, Mapping):
            usage_dict = dict(usage)
        else:
            usage_dict = {}

        raw_response = response.model_dump() if hasattr(response, "model_dump") else response

        return LLMResponse(
            model=getattr(response, "model", payload["model"]),
            task=Task.TOOL if tool_calls_list else Task.CHAT,
            text=text_content,
            provider=self.name,
            usage=usage_dict,
            tool_calls=tool_calls_list or None,
            raw=raw_response,
        )

    async def embed(self, *args: Any, **kwargs: Any) -> LLMResponse:  # pragma: no cover
        raise RuntimeError("Embedding is handled by sakhi.libs.embeddings.embed_text().")


def _headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def make_openai_provider_from_env() -> OpenAIProvider | None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    chat_model = os.getenv("OPENAI_MODEL_CHAT", os.getenv("MODEL_CHAT", "gpt-4o-mini"))
    embed_model = os.getenv("OPENAI_MODEL_EMBED", os.getenv("MODEL_EMBED", "text-embedding-3-small"))
    timeout = float(os.getenv("OPENAI_TIMEOUT", "30"))
    base_url = os.getenv("OPENAI_BASE")
    return OpenAIProvider(
        api_key,
        model_chat=chat_model,
        model_embed=embed_model,
        timeout=timeout,
        base_url=base_url,
    )
