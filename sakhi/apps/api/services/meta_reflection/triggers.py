from __future__ import annotations

from typing import Any, Dict, List

from sakhi.apps.api.core.db import exec as dbexec

_META_KEYWORDS = {
    "why",
    "meaning",
    "purpose",
    "clarity",
    "identity",
    "values",
    "lost",
    "confused",
    "self",
    "introspect",
    "reflection",
}


def detect_meta_reflection_intents(intents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return intents that look introspective / meta reflection friendly."""

    hits: List[Dict[str, Any]] = []
    for intent in intents or []:
        title = (intent.get("title") or "").lower()
        raw = (intent.get("raw_input") or "").lower()
        if any(keyword in title for keyword in _META_KEYWORDS) or any(
            keyword in raw for keyword in _META_KEYWORDS
        ):
            hits.append(intent)
    return hits


async def apply_meta_reflection_triggers(
    person_id: str,
    intents: List[Dict[str, Any]],
    entry_id: str | None,
) -> Dict[str, Any]:
    """Apply meta-reflection adjustments: queue, helpfulness tuning, reflection flag."""

    if not intents:
        return {"applied": False}

    await dbexec(
        """
        INSERT INTO session_continuity (person_id, reflection_pending)
        VALUES ($1, TRUE)
        ON CONFLICT (person_id)
        DO UPDATE SET reflection_pending = TRUE, last_interaction_ts = NOW()
        """,
        person_id,
    )

    await dbexec(
        """
        INSERT INTO meta_reflection_scores (person_id, helpfulness, clarity, updated_at)
        VALUES ($1, 0.1, 0.1, NOW())
        ON CONFLICT (person_id)
        DO UPDATE SET
            helpfulness = COALESCE(meta_reflection_scores.helpfulness, 0) + 0.05,
            clarity = COALESCE(meta_reflection_scores.clarity, 0) + 0.05,
            updated_at = NOW()
        """,
        person_id,
    )

    await dbexec(
        """
        INSERT INTO insights_queue (person_id, insight, priority, created_at)
        VALUES (
            $1,
            jsonb_build_object('source_entry', $2, 'kind', 'meta_reflection'),
            'medium',
            NOW()
        )
        """,
        person_id,
        entry_id,
    )

    return {
        "applied": True,
        "count": len(intents),
    }


__all__ = ["detect_meta_reflection_intents", "apply_meta_reflection_triggers"]
