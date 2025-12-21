from __future__ import annotations

from sakhi.apps.api.core.db import exec as dbexec
from sakhi.apps.api.services.clarity.clarity_engine import compute_clarity_features


async def apply_reflection_to_clarity(person_id: str, reflection_text: str) -> dict:
    """
    Update clarity indicators based on a newly stored reflection.
    """

    features = await compute_clarity_features(reflection_text or "")
    clarity = features["clarity"]
    themes = features.get("themes") or []

    for theme in themes:
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
            INSERT INTO theme_states (id, person_id, theme, clarity_score, updated_at)
            SELECT gen_random_uuid(), $1, $2, $3, NOW()
            WHERE NOT EXISTS (SELECT 1 FROM updated)
            """,
            person_id,
            theme,
            clarity,
        )

    await dbexec(
        """
        UPDATE session_continuity
        SET clarity_level = $2,
            last_interaction_ts = NOW()
        WHERE person_id = $1
        """,
        person_id,
        clarity,
    )

    return {"clarity": clarity, "themes": themes}


__all__ = ["apply_reflection_to_clarity"]
