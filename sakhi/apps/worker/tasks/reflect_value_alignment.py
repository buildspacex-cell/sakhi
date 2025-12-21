from __future__ import annotations

import os
from typing import Any, Dict, List

import numpy as np
try:
    from supabase import create_client
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    create_client = None  # type: ignore[assignment]

from sakhi.apps.worker.utils.db import db_fetch, db_upsert
from sakhi.apps.worker.utils.llm import llm_reflect
from sakhi.libs.embeddings import embed_text


def cosine(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity guarding against zero vectors."""
    vec_a = np.array(a, dtype=float)
    vec_b = np.array(b, dtype=float)
    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(vec_a, vec_b) / (norm_a * norm_b))


def _get_supabase_client() -> Any | None:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_API_KEY")
    if not url or not key:
        return None
    if create_client is None:
        return None
    try:
        return create_client(url, key)
    except Exception:
        return None


async def reflect_value_alignment(person_id: str) -> None:
    """
    Weekly job aligning declared values vs derived themes.
    """
    _get_supabase_client()  # placeholder – ensures env configuration checked
    row = db_fetch("value_alignment", {"person_id": person_id})
    declared = row.get("declared_values", [])
    if not isinstance(declared, list) or not declared:
        return

    themes_payload = db_fetch("themes", {"person_id": person_id})
    themes: List[Dict[str, Any]] = themes_payload.get("themes", []) if themes_payload else []
    if not themes:
        return

    val_vec = await embed_text(" ".join(map(str, declared)))
    theme_names = [str(item.get("name", "")) for item in themes if item.get("name")]
    if not theme_names:
        return
    theme_vec = await embed_text(" ".join(theme_names))
    score = cosine(val_vec, theme_vec)

    comment = await llm_reflect(
        (
            f"Compare user's declared values {declared} with active themes {theme_names}. "
            "Provide a concise reflection on where they align or diverge."
        ),
        mode="value_alignment",
    )

    db_upsert(
        "value_alignment",
        {
            "person_id": person_id,
            "declared_values": declared,
            "derived_themes": theme_names,
            "alignment_score": score,
            "alignment_comment": comment,
        },
    )

    if score < 0.6:
        enqueue_alignment_insight(person_id, comment, score)


def enqueue_alignment_insight(person_id: str, summary: str, score: float) -> None:
    """Placeholder dispatcher for routing alignment nudges to the presence system."""
    db_upsert(
        "alignment_insights",
        {
            "person_id": person_id,
            "latest_comment": summary,
            "last_score": score,
        },
    )


__all__ = ["reflect_value_alignment"]
