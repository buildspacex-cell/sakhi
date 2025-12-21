from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends

from sakhi.apps.api.core.db import DBSession, get_db

router = APIRouter()


def _generate_narrative(summary: Dict[str, Any], themes: List[Dict[str, Any]]) -> str:
    if not themes:
        return "This week stayed balanced with steady clarity and energy."
    top = max(themes, key=lambda t: t.get("change", 0.0), default=None)
    low = min(themes, key=lambda t: t.get("change", 0.0), default=None)
    if not top or not low:
        return "This week stayed balanced with steady clarity and energy."
    mood = summary.get("dominant_tone", "neutral")
    narrative = (
        f"Your {top['name'].lower()} theme grew strongest, while "
        f"{low['name'].lower()} dipped slightly. Tone stayed {mood}, "
        "showing balanced momentum with room for rest."
    )
    if summary.get("breath") is not None:
        narrative += " Your breathing rhythm stabilized this week, improving overall coherence."
    return narrative


@router.get("/theme_trends/{person_id}")
async def theme_trends(person_id: str, db: DBSession = Depends(get_db)) -> Dict[str, List[Dict[str, Any]] | str]:
    try:
        rows = await db.fetch(
            """
            SELECT theme, correlation, clarity_trend, energy_trend
            FROM theme_rhythm_links
            WHERE person_id = $1
            """,
            person_id,
        )
        themes = [
            {
                "name": (row.get("theme") or "general").title(),
                "change": round(float(row.get("correlation") or 0.0) * 100, 1),
                "clarity": float(row.get("clarity_trend") or 0.0),
                "energy": float(row.get("energy_trend") or 0.0),
            }
            for row in rows
        ]
        summary = await db.fetchrow(
            """
            SELECT AVG(clarity_score) AS clarity_index,
                   (
                     SELECT AVG(energy_score)
                     FROM rhythm_forecasts
                     WHERE person_id = $1
                   ) AS energy_index,
                   mode() WITHIN GROUP (ORDER BY emotion) AS dominant_tone
            FROM reflections
            WHERE person_id = $1
            """,
            person_id,
        ) or {}
        breath_row = await db.fetchrow(
            """
            SELECT AVG(calm_score) AS breath_coherence
            FROM breath_sessions
            WHERE person_id = $1
              AND start_time > now() - interval '7 days'
            """,
            person_id,
        )
        if breath_row and breath_row.get("breath_coherence") is not None:
            summary["breath"] = float(breath_row["breath_coherence"])
        narrative = _generate_narrative(summary, themes)
        return {"themes": themes, "narrative": narrative}
    finally:
        await db.close()


__all__ = ["router"]
