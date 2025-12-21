"""OpenRouter provider implementation supporting DeepSeek and other models."""

from __future__ import annotations

import json
import logging
from typing import Any, Mapping, Sequence

import httpx
from jsonschema import Draft7Validator, ValidationError
from jsonschema.exceptions import SchemaError

from .base import BaseProvider
from .types import LLMResponse, Task

OPENROUTER_DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"


class OpenRouterProvider(BaseProvider):
    """Provider that proxies chat and embedding requests through OpenRouter."""

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str | None = None,
        timeout: float = 60.0,
        tenant: str | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("OpenRouter API key is required")

        super().__init__(name="openrouter")
        self._api_key = api_key
        self._base_url = base_url or OPENROUTER_DEFAULT_BASE_URL
        self._timeout = timeout
        self._tenant = tenant
        self._logger = logging.getLogger(__name__)

    async def chat(
        self,
        *,
        messages: Sequence[Mapping[str, Any]],
        model: str,
        tools: Sequence[Mapping[str, Any]] | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Execute a chat completion request."""

        kwargs.pop("force_json", None)
        kwargs.pop("response_format", None)

        payload_tools, validators = self._prepare_tools(tools)
        payload = {
            "model": model,
            "messages": [self._serialise_message(message) for message in messages],
            **kwargs,
        }
        if payload_tools:
            payload["tools"] = payload_tools

        response_json, headers = await self._post("/chat/completions", payload)
        choice = (response_json.get("choices") or [{}])[0]
        message = choice.get("message") or {}

        normalized_tools = self._normalise_tool_calls(message, validators)
        text_content = message.get("content")

        usage = response_json.get("usage") or {}
        cost = self._extract_cost(response_json, headers)

        return LLMResponse(
            model=response_json.get("model") or model,
            task=Task.CHAT if not normalized_tools else Task.TOOL,
            text=text_content,
            tool_calls=normalized_tools.get("tool_calls") if normalized_tools else None,
            usage=usage,
            cost=cost,
            provider=self.name,
            raw=response_json,
        )

    async def embed(self, *args: Any, **kwargs: Any) -> LLMResponse:  # pragma: no cover
        raise RuntimeError("Embedding is handled by sakhi.libs.embeddings.embed_text().")

    async def _post(self, path: str, payload: Mapping[str, Any]) -> tuple[dict[str, Any], Mapping[str, str]]:
        url = f"{self._base_url.rstrip('/')}{path}"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": self._tenant or "http://localhost:3000",
            "X-Title": "Sakhi",
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                response = await client.post(url, headers=headers, json=payload)
            except httpx.RequestError as exc:
                raise RuntimeError(
                    f"OpenRouter network error: {exc}. Check API key or connectivity."
                ) from exc
            content_type = response.headers.get("content-type", "")
            if not response.is_success:
                raise RuntimeError(
                    f"OpenRouter {response.status_code} on {url}. Body: {response.text[:400]}"
                )
            if "application/json" not in content_type.lower():
                raise RuntimeError(
                    f"OpenRouter returned non-JSON (CT={content_type}) on {url}. Body: {response.text[:400]}"
                )
            return response.json(), response.headers

    def _prepare_tools(
        self,
        tools: Sequence[Mapping[str, Any]] | None,
    ) -> tuple[list[dict[str, Any]] | None, dict[str, Draft7Validator]]:
        if not tools:
            return None, {}

        normalized: list[dict[str, Any]] = []
        validators: dict[str, Draft7Validator] = {}

        for tool in tools:
            if not isinstance(tool, Mapping):
                raise TypeError("Each tool definition must be a mapping")

            name = tool.get("name")
            description = tool.get("description", "")
            parameters = tool.get("parameters")

            if not name or not isinstance(name, str):
                raise ValueError("Tool definitions require a string 'name'")
            if not isinstance(description, str):
                raise ValueError("Tool definitions require a string 'description'")
            if not isinstance(parameters, Mapping):
                raise ValueError("Tool definitions require a JSON Schema 'parameters' mapping")

            try:
                validator = Draft7Validator(parameters)
            except SchemaError as exc:  # pragma: no cover - defensive
                raise ValueError(f"Invalid JSON Schema for tool '{name}'") from exc

            normalized.append(
                {
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": description,
                        "parameters": parameters,
                    },
                }
            )
            validators[name] = validator

        return normalized, validators

    def _normalise_tool_calls(
        self,
        message: Mapping[str, Any],
        validators: Mapping[str, Draft7Validator],
    ) -> dict[str, list[dict[str, Any]]] | None:
        raw_calls = message.get("tool_calls")
        if not raw_calls and "function_call" in message:
            raw_calls = [{"function": message["function_call"]}]

        if not raw_calls:
            return None

        normalized: list[dict[str, Any]] = []
        for call in raw_calls:
            function = call.get("function") or {}
            name = function.get("name") or call.get("name")
            if not name:
                raise ValueError("Tool call is missing a function name")

            arguments = function.get("arguments", call.get("arguments"))
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments or "{}")
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Tool call for '{name}' contains invalid JSON") from exc
            if arguments is None:
                arguments = {}
            if not isinstance(arguments, Mapping):
                raise ValueError(f"Tool call for '{name}' must resolve to a mapping of arguments")

            validator = validators.get(name)
            if validator:
                try:
                    validator.validate(arguments)
                except ValidationError as exc:
                    raise ValueError(f"Tool call arguments for '{name}' failed validation: {exc.message}") from exc

            normalized.append({"name": name, "arguments": dict(arguments)})

        return {"tool_calls": normalized}

    def _serialise_message(self, message: Mapping[str, Any]) -> dict[str, Any]:
        if hasattr(message, "model_dump"):
            data = message.model_dump()
        else:
            data = dict(message)

        role = data.get("role")
        content = data.get("content")
        if role is None or content is None:
            raise ValueError("Chat messages must include 'role' and 'content'")

        serialized = {"role": role, "content": content}
        if "name" in data:
            serialized["name"] = data["name"]
        if "tool_call_id" in data:
            serialized["tool_call_id"] = data["tool_call_id"]
        return serialized

    def _extract_cost(self, payload: Mapping[str, Any], headers: Mapping[str, str]) -> float:
        usage = payload.get("usage") or {}
        for key in ("total_cost", "cost", "estimated_cost"):
            value = usage.get(key)
            if value is not None:
                try:
                    return float(value)
                except (TypeError, ValueError):
                    continue

        header_cost = headers.get("x-usage-cost")
        if header_cost:
            try:
                return float(header_cost)
            except ValueError:  # pragma: no cover - defensive
                pass
        return 0.0


__all__ = ["OpenRouterProvider", "OPENROUTER_DEFAULT_BASE_URL"]
