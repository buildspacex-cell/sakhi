"""Background tasks executed by Redis RQ workers."""

from __future__ import annotations

from typing import Any


def generate_embedding(payload: dict[str, Any]) -> dict[str, Any]:
    """Placeholder embedding task."""

    content = payload.get("content", "")
    return {
        "embedding": [0.0] * min(len(content), 5),
        "metadata": payload.get("metadata", {}),
    }


def compute_salience(payload: dict[str, Any]) -> dict[str, Any]:
    """Placeholder salience task."""

    score = len(payload.get("content", "")) % 10 / 10
    return {"score": score, "metadata": payload.get("metadata", {})}


__all__ = ["compute_salience", "generate_embedding"]
