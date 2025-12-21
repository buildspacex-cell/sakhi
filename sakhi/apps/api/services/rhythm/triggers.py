from __future__ import annotations

from typing import Any, Dict, List

from sakhi.apps.api.core.db import exec as dbexec

_RHYTHM_KEYWORDS = {
    "tired",
    "fatigue",
    "exhausted",
    "burnout",
    "sleep",
    "rest",
    "drained",
    "overwhelmed",
    "fog",
    "low energy",
    "low focus",
    "scattered",
}


def detect_rhythm_related_intents(intents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return intents related to rhythm/energy/fatigue heuristics."""

    hits: List[Dict[str, Any]] = []
    for intent in intents or []:
        title = (intent.get("title") or "").lower()
        raw = (intent.get("raw_input") or "").lower()
        if any(keyword in title for keyword in _RHYTHM_KEYWORDS) or any(
            keyword in raw for keyword in _RHYTHM_KEYWORDS
        ):
            hits.append(intent)
    return hits


async def apply_rhythm_triggers(person_id: str, intents: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Apply lightweight rhythm updates (theme correlation hint + refresh flag)."""

    if not intents:
        return {"applied": False}

    for intent in intents:
        theme = intent.get("domain") or "general"
        await dbexec(
            """
            INSERT INTO theme_rhythm_links (person_id, theme, correlation, samples, updated_at)
            VALUES ($1, $2, 0.05, 1, NOW())
            ON CONFLICT (person_id, theme)
            DO UPDATE SET
                correlation = theme_rhythm_links.correlation + 0.02,
                samples = theme_rhythm_links.samples + 1,
                updated_at = NOW()
            """,
            person_id,
            theme,
        )

    await dbexec(
        """
        UPDATE personal_model
        SET rhythm_state = jsonb_set(
                COALESCE(rhythm_state, '{}'::jsonb),
                '{refresh_hint}',
                '"weekly"'
            ),
            updated_at = NOW()
        WHERE person_id = $1
        """,
        person_id,
    )

    return {
        "applied": True,
        "count": len(intents),
        "themes": sorted({intent.get("domain") or "general" for intent in intents}),
    }


__all__ = ["detect_rhythm_related_intents", "apply_rhythm_triggers"]
