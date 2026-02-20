from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, List

import numpy as np

from kala.memory.vector_math import normalize_vector as _normalize_vector_raw
from kala.memory.vector_math import parse_vector as _coerce_vector

from sakhi.apps.api.core.db import dbfetchrow, exec as dbexec

logger = logging.getLogger(__name__)
EXPECTED_DIM = 1024  # canonical dimension for text-embedding-3-small


def _normalize_vector(vec: Any) -> List[float]:
    return _normalize_vector_raw(vec, dim=EXPECTED_DIM)


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
