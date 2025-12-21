from __future__ import annotations

import logging
import os
from typing import Any, Iterable, List, Sequence

from openai import AsyncOpenAI

LOGGER = logging.getLogger(__name__)
_CLIENT: AsyncOpenAI | None = None
#
# Build 52: normalize to 1536 dims (text-embedding-3-small returns 1536)
_MODEL_NAME = os.getenv("MODEL_EMBED", "text-embedding-3-small")
_EXPECTED_DIM = 1536


def _get_client() -> AsyncOpenAI:
    global _CLIENT
    if _CLIENT is not None:
        return _CLIENT

    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY (or LLM_API_KEY) is required for embeddings.")

    _CLIENT = AsyncOpenAI(api_key=api_key)
    return _CLIENT


def _zero_vector() -> List[float]:
    return [0.0] * _EXPECTED_DIM


def _coerce_vector(vec: Any) -> List[float]:
    # Accept vectors that are close in size (OpenAI sometimes gives slight length differences)
    if isinstance(vec, list) and len(vec) >= _EXPECTED_DIM:
        try:
            return [float(x) for x in vec[:_EXPECTED_DIM]]
        except Exception:
            return _zero_vector()

    # If vector is too short or invalid — pad instead of zeroing out
    if isinstance(vec, list):
        try:
            padded = (vec + [0.0] * _EXPECTED_DIM)[:_EXPECTED_DIM]
            return [float(x) for x in padded]
        except Exception:
            return _zero_vector()

    # Last fallback
    return _zero_vector()


async def _call_openai(texts: Sequence[str]) -> List[List[float]]:
    client = _get_client()
    response = await client.embeddings.create(
        model=_MODEL_NAME,
        input=list(texts),
    )
    return [item.embedding for item in response.data]


async def embed_text(text: str | Sequence[str]) -> List[float] | List[List[float]]:
    """
    Canonical embedding entry point.
    - Accepts a string or a list of strings.
    - Always returns vectors of length 1536.
    - Retries once on OpenAI failure, logging errors.
    - Falls back to zero-vectors when the API cannot be reached.
    """

    # Explicit kill-switch for embeddings (useful for local/dev cost control).
    if os.getenv("SAKHI_DISABLE_EMBEDDINGS") == "1":
        if isinstance(text, str):
            return _zero_vector()
        return [_zero_vector() for _ in (text or [])]

    if isinstance(text, str):
        normalized = (text or "").strip()
        if not normalized:
            return _zero_vector()
        inputs = [normalized]
        expect_single = True
    else:
        expect_single = False
        inputs = [(t or "").strip() for t in text]

    if not inputs:
        return _zero_vector() if expect_single else []

    non_empty_pairs = [(idx, value) for idx, value in enumerate(inputs) if value]
    if not non_empty_pairs:
        zero = _zero_vector()
        return zero if expect_single else [zero for _ in inputs]

    payload = [value for _, value in non_empty_pairs]
    payload_positions = [idx for idx, _ in non_empty_pairs]

    try:
        vectors = await _call_openai(payload)
    except Exception as exc:
        LOGGER.error("embed_text: first attempt failed: %s", exc)
        try:
            vectors = await _call_openai(payload)
        except Exception as retry_exc:
            LOGGER.error("embed_text: retry failed: %s", retry_exc)
            vectors = [_zero_vector() for _ in payload]

    if len(vectors) < len(payload):
        LOGGER.warning(
            "embed_text: missing vectors (%s of %s). Padding with zeros.",
            len(vectors),
            len(payload),
        )
        vectors.extend([_zero_vector() for _ in range(len(payload) - len(vectors))])

    coerced = [_coerce_vector(vec) for vec in vectors]

    mapped: List[List[float]] = []
    vector_iter = iter(coerced)
    position_iter = iter(payload_positions)
    current_position = next(position_iter, None)
    for idx in range(len(inputs)):
        if current_position is not None and idx == current_position:
            mapped.append(next(vector_iter, _zero_vector()))
            current_position = next(position_iter, None)
        else:
            mapped.append(_zero_vector())

    return mapped[0] if expect_single else mapped


def _coerce_float_list(values: Iterable[Any]) -> List[float]:
    try:
        return [float(x) for x in values]
    except Exception:
        return []


async def embed_normalized(text: str) -> List[float]:
    """
    Normalize whitespace + casing then embed using the unified model.
    """
    normalized = " ".join((text or "").lower().strip().split())
    if not normalized:
        return _zero_vector()
    vec = await embed_text(normalized)
    if isinstance(vec, list) and vec and not isinstance(vec[0], list):
        return _coerce_vector(vec)
    if isinstance(vec, list) and vec and isinstance(vec[0], list):
        return _coerce_vector(vec[0])
    return _zero_vector()


def to_pgvector(vec: Sequence[Any] | None, *, length: int | None = None) -> str:
    """
    Render a Python sequence as a pgvector literal.
    """
    floats = _coerce_float_list(vec or [])
    if length is not None:
        if not floats:
            floats = [0.0] * length
        elif len(floats) < length:
            floats = floats + [0.0] * (length - len(floats))
        else:
            floats = floats[:length]
    if not floats:
        return "[]"
    return "[" + ",".join(f"{value:.6f}" for value in floats) + "]"


def parse_pgvector(value: Any) -> List[float]:
    """
    Parse a pgvector column (list, tuple, or string literal) into floats.
    """
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return _coerce_float_list(value)
    if isinstance(value, memoryview):
        value = value.tobytes()
    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8", errors="ignore")
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        if text.startswith("[") and text.endswith("]"):
            text = text[1:-1]
        parts = [part.strip() for part in text.split(",") if part.strip()]
        return _coerce_float_list(parts)
    return []


__all__ = ["embed_text", "embed_normalized", "parse_pgvector", "to_pgvector"]


def compute_direction_vector(vectors: Sequence[Sequence[float]] | None) -> List[float]:
    """
    Compute normalized mean vector for identity direction.
    """
    vecs = vectors or []
    if not vecs:
        return []
    length = min(len(v) for v in vecs if v) or 0
    if length == 0:
        return []
    acc = [0.0] * length
    for v in vecs:
        for i in range(length):
            acc[i] += float(v[i])
    mean = [v / len(vecs) for v in acc]
    norm = sum(x * x for x in mean) ** 0.5
    if norm == 0:
        return mean
    return [x / norm for x in mean]
