from __future__ import annotations

import datetime as dt
from typing import Any, Dict

from sakhi.apps.api.core.db import q, exec as dbexec
from sakhi.apps.api.core.person_utils import resolve_person_id


def _normalize_intent(intent: str) -> str:
    return " ".join((intent or "").lower().strip().split())


async def evolve(person_id: str, intent: str | None, sentiment: float | int | None = None) -> Dict[str, Any]:
    name = _normalize_intent(intent or "")
    if not name:
        return {"skipped": True}
    person_id = await resolve_person_id(person_id) or person_id
    sent_val = float(sentiment or 0)
    row = await q(
        "SELECT strength, emotional_alignment FROM intent_evolution WHERE person_id = $1 AND intent_name = $2",
        person_id,
        name,
        one=True,
    )
    now = dt.datetime.utcnow()
    if not row:
        strength = 0.2
        emo = sent_val
        trend = "stable"
        await dbexec(
            """
            INSERT INTO intent_evolution (person_id, intent_name, strength, emotional_alignment, trend, last_seen, first_seen)
            VALUES ($1, $2, $3, $4, $5, $6, $6)
            """,
            person_id,
            name,
            strength,
            emo,
            trend,
            now,
        )
        return {"intent": name, "strength": strength, "emotional_alignment": emo, "trend": trend}

    prev_strength = float(row.get("strength") or 0)
    prev_emo = float(row.get("emotional_alignment") or 0)
    strength = min(1.0, prev_strength + 0.1)
    emo = round((prev_emo * 0.7) + (sent_val * 0.3), 3)
    trend = "up" if strength > prev_strength else ("down" if strength < prev_strength else "stable")

    await dbexec(
        """
        UPDATE intent_evolution
        SET strength = $3,
            emotional_alignment = $4,
            trend = $5,
            last_seen = $6
        WHERE person_id = $1 AND intent_name = $2
        """,
        person_id,
        name,
        strength,
        emo,
        trend,
        now,
    )
    return {"intent": name, "strength": strength, "emotional_alignment": emo, "trend": trend}


__all__ = ["evolve"]
