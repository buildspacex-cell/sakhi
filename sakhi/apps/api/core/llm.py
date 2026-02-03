from __future__ import annotations

import json
import os
from typing import Any, Mapping, Optional, Sequence, Type
from decimal import Decimal

import logging
from pydantic import BaseModel, ValidationError

from sakhi.apps.api.middleware.auth_pilot import _mask_pii
from sakhi.libs.llm_router.router import LLMRouter
from sakhi.libs.llm_router.context_builder import build_meta_context
_ROUTER: LLMRouter | None = None


def set_router(router: LLMRouter) -> None:
    global _ROUTER
    _ROUTER = router


def get_router() -> LLMRouter:
    """Get the global LLM router instance."""
    if _ROUTER is None:
        raise RuntimeError("LLM router has not been initialised")
    return _ROUTER


class LLMResponseError(RuntimeError):
    """Raised when the LLM output cannot be repaired."""


async def call_llm(
    prompt: str | None = None,
    *,
    messages: Sequence[Mapping[str, Any]] | None = None,
    schema: Type[BaseModel] | None = None,
    model: str | None = None,
    max_repair_attempts: int = 1,
    person_id: str | None = None,
    context: Mapping[str, Any] | None = None,
    **kwargs: Any,
) -> Any:
    if _ROUTER is None:
        raise RuntimeError("LLM router has not been initialised")

    if messages is None:
        if prompt is None:
            raise ValueError("Either 'prompt' or 'messages' must be provided")
        messages = (
            {"role": "system", "content": "You are Sakhi, a helpful companion."},
            {"role": "user", "content": prompt},
        )

    base_messages: list[Mapping[str, Any]] = list(messages)

    context_payload: dict[str, Any] | None = None
    if person_id:
        try:
            meta_context = await build_meta_context(person_id)
        except Exception as exc:  # pragma: no cover
            logging.getLogger(__name__).warning(
                "[LLM] Context build failed for %s: %s", person_id, exc
            )
            meta_context = {}

        if context:
            context_payload = _coerce_json(dict(meta_context, **context))
        else:
            context_payload = _coerce_json(dict(meta_context))
    elif context:
        context_payload = _coerce_json(dict(context))

    context_message = None
    if context_payload:
        serialized = _mask_pii(json.dumps(context_payload, ensure_ascii=False))
        context_message = {
            "role": "system",
            "content": f"Meta context:\n{serialized}",
        }
        logging.getLogger(__name__).info(
            "[LLM] Injected context for %s (keys=%s)",
            person_id or "anonymous",
            ",".join(context_payload.keys()),
        )

    target_model = model or os.getenv("MODEL_CHAT") or "openrouter/chat"

    if not base_messages or base_messages[0].get("role") != "system":
        base_messages = [{"role": "system", "content": "You are Sakhi, a helpful companion."}] + base_messages

    if context_message:
        base_messages.insert(1 if len(base_messages) > 1 else 0, context_message)

    response_format: Optional[dict[str, str]] = None
    if schema is not None:
        json_only_instruction = {
            "role": "system",
            "content": (
                "Return ONLY a valid JSON object that matches the expected fields. "
                "Do not include any additional commentary or code fences."
            ),
        }
        base_messages = [base_messages[0], json_only_instruction, *base_messages[1:]]
        response_format = {"type": "json_object"}

    request_kwargs = dict(kwargs)
    if response_format is not None:
        request_kwargs["response_format"] = response_format

    last_error: str | None = None
    last_text: str = ""

    for attempt in range(max_repair_attempts + 1):
        attempt_messages = list(base_messages)
        if attempt > 0 and last_error:
            attempt_messages.append(
                {
                    "role": "system",
                    "content": f"Previous response was invalid: {last_error}. Return ONLY valid JSON.",
                }
            )

        current_kwargs = dict(request_kwargs)
        sanitized_messages = [_scrub_message(message) for message in attempt_messages]
        response = await _ROUTER.chat(
            messages=sanitized_messages,
            model=target_model,
            **current_kwargs,
        )
        text = response.text
        if text is None and response.raw:
            choices = (response.raw.get("choices") or [{}])[0]
            message = choices.get("message") or {}
            text = message.get("content")
        last_text = text or ""

        if not schema:
            return last_text

        try:
            payload = json.loads(last_text)
        except json.JSONDecodeError as exc:  # pragma: no cover - defensive
            last_error = str(exc)
            continue

        try:
            return schema.model_validate(payload)
        except ValidationError as exc:  # pragma: no cover - defensive
            last_error = exc.json()
            continue

    preview = (last_text[:400] + "...") if len(last_text) > 400 else last_text
    raise LLMResponseError(f"LLM output invalid after repair attempts: {last_error}. Last response: {preview}")


def _scrub_message(message: Mapping[str, Any]) -> Mapping[str, Any]:
    """Return a sanitized copy of an OpenAI-style chat message."""

    payload = dict(message)
    if "content" in payload:
        payload["content"] = _scrub_value(payload["content"])
    if "name" in payload and isinstance(payload["name"], str):
        payload["name"] = _mask_pii(payload["name"])
    return payload


def _scrub_value(value: Any) -> Any:
    if isinstance(value, str):
        return _mask_pii(value)
    if isinstance(value, list):
        return [_scrub_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _scrub_value(val) for key, val in value.items()}
    return value


def _coerce_json(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {k: _coerce_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_coerce_json(v) for v in value]
    return value


def extract_json_from_llm_response(text: str) -> Any:
    """
    Extract JSON from LLM response that may include markdown code blocks.

    Handles responses like:
    - Raw JSON: {"key": "value"}
    - Markdown wrapped: ```json\n{"key": "value"}\n```
    - Prefixed: "Here's the result:\n```json\n{...}\n```"

    Returns the parsed JSON object/array, or the original text if parsing fails.
    """
    import re

    if not text:
        return {}

    text = text.strip()

    # Try direct JSON parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Handle markdown code blocks with prefix text
    if "```json" in text:
        start_idx = text.find("```json")
        text = text[start_idx + 7:]  # Skip ```json
        if "```" in text:
            end_idx = text.find("```")
            text = text[:end_idx]
    elif "```" in text:
        start_idx = text.find("```")
        text = text[start_idx + 3:]
        # Skip language identifier if present
        if text and text[0] != "\n" and text[0] != "{" and text[0] != "[":
            newline_idx = text.find("\n")
            if newline_idx != -1:
                text = text[newline_idx + 1:]
        if "```" in text:
            end_idx = text.find("```")
            text = text[:end_idx]

    text = text.strip()

    # Find JSON boundaries
    if text:
        array_start = text.find("[")
        obj_start = text.find("{")
        if array_start >= 0 and (obj_start < 0 or array_start < obj_start):
            text = text[array_start:]
        elif obj_start >= 0:
            text = text[obj_start:]

        # Find closing bracket
        closing_idx = max(text.rfind("]"), text.rfind("}"))
        if closing_idx != -1:
            text = text[:closing_idx + 1]

    # Strip trailing commas
    text = re.sub(r",(\s*[}\]])", r"\1", text)

    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        return {"_raw": text}
