"""LLM response parsing utilities."""

from __future__ import annotations

import json
import re
from typing import Any, Dict


def extract_json_from_llm_response(text: str) -> Dict[str, Any]:
    """
    Extract JSON from an LLM response that may contain markdown code blocks or extra text.
    Returns empty dict if no valid JSON found.
    """
    if not text:
        return {}

    # Try to find JSON in markdown code blocks first
    code_block_patterns = [
        r'```json\s*([\s\S]*?)\s*```',
        r'```\s*([\s\S]*?)\s*```',
    ]
    for pattern in code_block_patterns:
        match = re.search(pattern, text)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                continue

    # Try to find JSON object directly
    json_patterns = [
        r'\{[\s\S]*\}',  # Match entire JSON object
    ]
    for pattern in json_patterns:
        match = re.search(pattern, text)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                continue

    # Last resort: try parsing the entire text
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        return {}


__all__ = ["extract_json_from_llm_response"]
