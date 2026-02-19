"""
Vector Math — Shared vector utilities for memory systems.

Pure-Python implementations of cosine similarity, vector parsing,
normalization, recency weighting, and diversity filtering.

All functions are pure computation — zero external dependencies
(no numpy, no DB, no sakhi imports).
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

# =============================================================================
# Cosine Similarity
# =============================================================================


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """
    Cosine similarity between two vectors.

    Returns 0.0 for empty, zero-length, or incompatible inputs.
    """
    if not a or not b:
        return 0.0
    try:
        numerator = sum(x * y for x, y in zip(a, b))
        denom_a = math.sqrt(sum(x * x for x in a))
        denom_b = math.sqrt(sum(y * y for y in b))
        if denom_a == 0 or denom_b == 0:
            return 0.0
        return numerator / (denom_a * denom_b)
    except Exception:
        return 0.0


# =============================================================================
# Vector Parsing
# =============================================================================


def parse_vector(raw: Any) -> list[float]:
    """
    Parse a raw value into a flat list of floats.

    Handles: list, string-encoded JSON arrays (``"[0.1, 0.2, ...]"``), None.
    """
    if not raw:
        return []
    if isinstance(raw, list):
        try:
            return [float(x) for x in raw]
        except (TypeError, ValueError):
            return []
    if isinstance(raw, str) and raw.startswith("[") and raw.endswith("]"):
        body = raw[1:-1].strip()
        if not body:
            return []
        try:
            return [float(piece) for piece in body.split(",")]
        except (TypeError, ValueError):
            return []
    return []


# =============================================================================
# Vector Normalization
# =============================================================================


def normalize_vector(vec: Any, dim: int = 1536) -> list[float]:
    """
    Ensure *vec* is a flat list of floats with exactly *dim* elements.

    Unwraps single-element nested lists, pads with 0.0 or trims as needed.
    Returns a zero-vector if *vec* is not list-like.
    """
    if not isinstance(vec, (list, tuple)):
        return [0.0] * dim

    candidate: list[Any] = list(vec)

    # Unwrap accidental double-nesting: [[0.1, 0.2, ...]]
    if len(candidate) == 1 and isinstance(candidate[0], (list, tuple)):
        candidate = list(candidate[0])

    try:
        candidate = [float(x) for x in candidate]
    except (TypeError, ValueError):
        return [0.0] * dim

    if len(candidate) > dim:
        return candidate[:dim]
    if len(candidate) < dim:
        return candidate + [0.0] * (dim - len(candidate))
    return candidate


# =============================================================================
# Recency Weight
# =============================================================================


def recency_weight(
    ts: Any,
    halflife_days: float = 45.0,
) -> float:
    """
    Exponential-decay recency weight for a timestamp.

    Returns a value in (0, 1] where 1.0 = now.
    *halflife_days* controls how fast old items decay.
    """
    if not ts:
        return 1.0
    if isinstance(ts, str):
        try:
            ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            return 1.0
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    age_days = (now - ts).total_seconds() / 86400.0
    return float(0.5 ** (age_days / halflife_days))


# =============================================================================
# Diversity Filter
# =============================================================================


def diversity_filter(
    scored_items: list[tuple[float, dict[str, Any]]],
    top_k: int,
    threshold: float = 0.92,
) -> list[dict[str, Any]]:
    """
    Select up to *top_k* items, skipping near-duplicates.

    Two items are considered duplicates if their ``vec`` keys have
    cosine similarity > *threshold*.  If not enough diverse items
    exist, non-diverse items fill the remaining slots.
    """
    selected: list[dict[str, Any]] = []
    vecs: list[list[float]] = []

    for score, item in scored_items:
        if len(selected) >= top_k:
            break
        vec = item.get("vec")
        if not vec:
            continue
        diverse = True
        for prev in vecs:
            if cosine_similarity(prev, vec) > threshold:
                diverse = False
                break
        if diverse:
            selected.append({"score": score, **item})
            vecs.append(vec)

    # Fill remaining slots with non-diverse items
    if len(selected) < top_k:
        for score, item in scored_items:
            if len(selected) >= top_k:
                break
            candidate = {"score": score, **item}
            if candidate not in selected:
                selected.append(candidate)

    return selected[:top_k]


__all__ = [
    "cosine_similarity",
    "diversity_filter",
    "normalize_vector",
    "parse_vector",
    "recency_weight",
]
