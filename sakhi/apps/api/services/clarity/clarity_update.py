from __future__ import annotations

import json
from typing import Any, Dict, List

import numpy as np

from sakhi.apps.api.core.db import exec as dbexec, q as dbfetch
from sakhi.apps.api.services.clarity.clarity_engine import compute_clarity_features


async def update_clarity_from_short_term(person_id: str) -> None:
    """
    Aggregate short-term memories into clarity metrics and store them in theme_states & personal_model.
    """

    row = await dbfetch(
        """
        SELECT short_term
        FROM personal_model
        WHERE person_id = $1
        """,
        person_id,
    )
    if not row:
        return

    short_term = (row[0] or {}).get("short_term") or {}
    texts: List[str] = [text for text in (short_term.get("texts") or []) if isinstance(text, str) and text.strip()]
    if not texts:
        return

    clarity_scores: List[float] = []
    theme_counts: Dict[str, int] = {}
    vectors: List[List[float]] = []

    for text in texts:
        features = await compute_clarity_features(text)
        clarity_scores.append(features["clarity"])
        vector = features.get("vector") or []
        if isinstance(vector, list) and len(vector) == 1536:
            vectors.append(vector)
        for theme in features.get("themes") or []:
            theme_counts[theme] = theme_counts.get(theme, 0) + 1

    if not clarity_scores:
        return

    avg_clarity = round(float(sum(clarity_scores) / len(clarity_scores)), 4)

    summary_text = _make_summary(theme_counts, avg_clarity)
    await _update_theme_states(person_id, theme_counts, avg_clarity)

    merged_vec = None
    if vectors:
        merged_vec = np.mean(np.array(vectors, dtype=float), axis=0).tolist()

    payload = {
        "clarity": avg_clarity,
        "themes": theme_counts,
        "merged_vector": merged_vec,
    }
    await dbexec(
        """
        UPDATE personal_model
        SET mind_state = jsonb_set(
                COALESCE(mind_state, '{}'::jsonb),
                '{clarity}',
                to_jsonb($2::float8),
                true
            ),
            summary_text = $3,
            data = jsonb_set(
                COALESCE(data, '{}'::jsonb),
                '{clarity_snapshot}',
                $4::jsonb,
                true
            ),
            updated_at = NOW()
        WHERE person_id = $1
        """,
        person_id,
        avg_clarity,
        summary_text,
        json.dumps(payload, ensure_ascii=False),
    )


async def _update_theme_states(person_id: str, theme_counts: Dict[str, int], clarity: float) -> None:
    if not theme_counts:
        return

    for theme, count in theme_counts.items():
        await dbexec(
            """
            WITH updated AS (
                UPDATE theme_states
                SET clarity_score = $3,
                    updated_at = NOW()
                WHERE person_id = $1
                  AND theme = $2
                RETURNING id
            )
            INSERT INTO theme_states (id, person_id, theme, clarity_score, updated_at, rhythm_state)
            SELECT gen_random_uuid(), $1, $2, $3, NOW(), jsonb_build_object('mentions', $4)
            WHERE NOT EXISTS (SELECT 1 FROM updated)
            """,
            person_id,
            theme,
            clarity,
            count,
        )


def _make_summary(theme_counts: Dict[str, int], clarity: float) -> str:
    if not theme_counts:
        return f"Clarity steady at {clarity:.2f}. No dominant themes."
    dominant = sorted(theme_counts.items(), key=lambda item: item[1], reverse=True)[0][0]
    return f"Dominant theme: {dominant}. Clarity score: {clarity:.2f}"


__all__ = ["update_clarity_from_short_term"]
