from __future__ import annotations

import logging
from typing import Any, Dict

from sakhi.apps.api.core.db import q
from sakhi.apps.api.core.person_utils import resolve_person_id
from sakhi.apps.api.services.persona.features import analyze_persona_features

LOGGER = logging.getLogger(__name__)
ALPHA = 0.12


async def _fetch_persona_row(person_id: str) -> Dict[str, Any]:
    rows = await q(
        """
        SELECT style_profile, warmth, reflectiveness, humor, expressiveness, tone_bias
        FROM persona_traits
        WHERE person_id = $1
        """,
        person_id,
    )
    return rows[0] if rows else {}


def _blend(old: float | None, new: float | None) -> float:
    base = float(old) if old is not None else 0.5
    if new is None:
        return base
    return round((1 - ALPHA) * base + ALPHA * float(new), 3)


async def update_session_persona(person_id: str, text: str) -> Dict[str, Any]:
    person_id = await resolve_person_id(person_id) or person_id
    signals = await analyze_persona_features(text)
    row = await _fetch_persona_row(person_id)

    if not row:
        await q(
            """
            INSERT INTO persona_traits (person_id, style_profile)
            VALUES ($1, '{}'::jsonb)
            ON CONFLICT (person_id) DO NOTHING
            """,
            person_id,
        )
        row = {}

    updated = {
        "warmth": _blend(row.get("warmth"), signals.get("warmth")),
        "reflectiveness": _blend(row.get("reflectiveness"), signals.get("reflectiveness")),
        "humor": _blend(row.get("humor"), signals.get("humor")),
        "expressiveness": _blend(row.get("expressiveness"), signals.get("expressiveness")),
        "tone_bias": signals.get("tone_bias") or row.get("tone_bias"),
    }

    await q(
        """
        UPDATE persona_traits
        SET warmth = $2,
            reflectiveness = $3,
            humor = $4,
            expressiveness = $5,
            tone_bias = $6,
            last_updated = NOW()
        WHERE person_id = $1
        """,
        person_id,
        updated["warmth"],
        updated["reflectiveness"],
        updated["humor"],
        updated["expressiveness"],
        updated["tone_bias"],
    )

    return updated


__all__ = ["update_session_persona"]
