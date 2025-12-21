from __future__ import annotations

import json
import logging
from typing import List, Tuple

from sakhi.apps.api.core.config_loader import get_prompt
from sakhi.apps.api.core.llm import LLMResponseError, call_llm
from sakhi.apps.api.core.llm_schemas import ExtractionOutput

LOGGER = logging.getLogger(__name__)


def _build_messages(prompt_name: str, payload: dict) -> List[dict]:
    prompt_def = get_prompt(prompt_name)
    messages: List[dict] = []
    system = prompt_def.get("system")
    if system:
        messages.append({"role": "system", "content": system})

    for shot in prompt_def.get("few_shots", []):
        user = shot.get("input")
        assistant = shot.get("output")
        if user:
            messages.append({"role": "user", "content": json.dumps(user, ensure_ascii=False)})
        if assistant:
            messages.append({"role": "assistant", "content": json.dumps(assistant, ensure_ascii=False)})

    messages.append({"role": "user", "content": json.dumps(payload, ensure_ascii=False)})
    return messages


async def run_extraction_llm(text: str, *, tags: List[str] | None = None, layer: str | None = None) -> Tuple[ExtractionOutput | None, str | None]:
    payload = {"text": text, "meta": {"tags": tags or [], "layer": layer}}
    messages = _build_messages("extract", payload)
    try:
        result: ExtractionOutput = await call_llm(messages=messages, schema=ExtractionOutput)
        return result, None
    except LLMResponseError as exc:  # pragma: no cover - defensive
        LOGGER.warning("LLM extraction failed: %s", exc)
        return None, str(exc)
