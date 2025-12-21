from __future__ import annotations

import re
import uuid
from typing import Any


def json_safe(obj: Any) -> Any:
    """Recursively convert objects (e.g., UUIDs) into JSON-serializable structures."""

    if isinstance(obj, uuid.UUID):
        return str(obj)
    if isinstance(obj, dict):
        return {k: json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [json_safe(item) for item in obj]
    return obj


def extract_json_block(blob: str) -> str:
    """
    Strip markdown fences and trailing commas from LLM responses,
    returning a best-effort JSON string.
    """

    text = (blob or "").strip()
    if text.startswith("```"):
        newline_idx = text.find("\n")
        if newline_idx != -1:
            text = text[newline_idx + 1 :]
        if text.endswith("```"):
            text = text[:-3]
    text = text.strip()
    if text:
        closing_idx = max(text.rfind("]"), text.rfind("}"))
        if closing_idx != -1:
            text = text[: closing_idx + 1]
    text = _strip_trailing_commas(text)
    return text.strip()


def _strip_trailing_commas(text: str) -> str:
    return re.sub(r",(\s*[}\]])", r"\1", text)


__all__ = ["json_safe", "extract_json_block"]
