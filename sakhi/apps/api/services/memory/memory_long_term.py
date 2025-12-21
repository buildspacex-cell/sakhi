from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Sequence, List

import numpy as np

from sakhi.apps.api.core.db import dbfetchrow, exec as dbexec
import logging

logger = logging.getLogger(__name__)
EXPECTED_DIM = 1024  # canonical dimension for text-embedding-3-small


def _normalize_vector(vec: Any) -> List[float]:
    """
    Ensure the vector is a flat list of floats with EXPECTED_DIM elements.
    Pads or trims as needed.
    """
    if not isinstance(vec, (list, tuple)):
        return [0.0] * EXPECTED_DIM

    candidate = vec
    if len(candidate) == 1 and isinstance(candidate[0], (list, tuple)):
        candidate = candidate[0]

    try:
        candidate = [float(x) for x in candidate]
    except Exception:
        return [0.0] * EXPECTED_DIM

    if len(candidate) > EXPECTED_DIM:
        return candidate[:EXPECTED_DIM]
    if len(candidate) < EXPECTED_DIM:
        return candidate + [0.0] * (EXPECTED_DIM - len(candidate))
    return candidate


def _coerce_vector(candidate: Any) -> list[float]:
    if isinstance(candidate, (list, tuple)):
        items: Sequence[Any] = candidate  # type: ignore[assignment]
    else:
        return []

    if items and isinstance(items[0], (list, tuple)):
        items = items[0]  # type: ignore[assignment]

    try:
        return [float(value) for value in items]  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return []


def _coerce_record(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict):
        return payload
    if isinstance(payload, str):
        text = payload.strip()
        if not text:
            return {}
        try:
            decoded = json.loads(text)
        except json.JSONDecodeError:
            return {}
        if isinstance(decoded, dict):
            return decoded
        return {}
    return {}


async def consolidate_long_term(person_id: str) -> None:
    """
    Merge the aggregated short-term vector into the long-term model using
    a simple decay blend to keep traits stable.
    """

    row = await dbfetchrow(
        """
        SELECT short_term_vector, long_term
        FROM personal_model
        WHERE person_id = $1
        """,
        person_id,
    )
    if not row:
        return

    short_term_raw = row.get("short_term_vector")
    short_term = _coerce_record(short_term_raw)
    if not short_term:
        logger.warning(
            "[LongTerm] Missing or invalid short-term payload for %s; skipping consolidation.",
            person_id,
        )
        return
    long_term = _coerce_record(row.get("long_term"))

    raw_st_vec = short_term.get("merged_vector")
    if not raw_st_vec:
        logger.warning(
            "[LongTerm] Short-term vector missing merged_vector for %s; skipping.",
            person_id,
        )
        return
    st_vec = _normalize_vector(raw_st_vec)

    raw_lt_vec = (long_term or {}).get("merged_vector")
    lt_vec = _normalize_vector(raw_lt_vec) if raw_lt_vec else [0.0] * EXPECTED_DIM

    try:
        merged = (
            0.85 * np.array(lt_vec, dtype=float) + 0.15 * np.array(st_vec, dtype=float)
        ).tolist()
    except Exception:
        merged = st_vec

    merged = _normalize_vector(merged)

    new_long_term = dict(long_term)
    new_long_term["merged_vector"] = merged
    new_long_term["last_update"] = datetime.now(timezone.utc).isoformat()

    await dbexec(
        """
        UPDATE personal_model
        SET long_term = $2::jsonb, updated_at = NOW()
        WHERE person_id = $1
        """,
        person_id,
        json.dumps(new_long_term, ensure_ascii=False),
    )
