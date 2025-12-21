from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List

from sakhi.apps.api.core.db import get_db
from sakhi.apps.api.core.llm import call_llm

LOGGER = logging.getLogger(__name__)


async def run_theme_inference(person_id: str) -> Dict[str, Any] | None:
    """
    Correlate reflections, goals, and rhythm state into unified themes.
    """

    db = await get_db()
    try:
        reflections = await db.fetch(
            """
            SELECT id, content, theme
            FROM reflections
            WHERE user_id = $1
            ORDER BY created_at DESC
            LIMIT 30
            """,
            person_id,
        )

        goals = await db.fetch(
            """
            SELECT title, description
            FROM goals
            WHERE person_id = $1
            """,
            person_id,
        )

        rhythm_row = await db.fetchrow(
            "SELECT rhythm_state FROM personal_model WHERE person_id = $1",
            person_id,
        )

        payload = {
            "reflections": [
                {"id": row["id"], "theme": row.get("theme"), "content": row.get("content")}
                for row in reflections
            ],
            "goals": goals,
            "rhythm_state": rhythm_row.get("rhythm_state") if rhythm_row else {},
        }

        prompt = (
            "Given reflections, goals, and rhythm_state, find 2–3 major cross-themes.\n"
            "Return JSON list: [{\"theme\":\"...\",\"related_themes\":[...],"
            "\"coherence\":0-1,\"energy_alignment\":0-1}].\n"
            f"Data:\n{json.dumps(payload, ensure_ascii=False)}"
        )

        response = await call_llm(
            messages=[{"role": "user", "content": prompt}],
            person_id=person_id,
        )

        raw = response if isinstance(response, str) else json.dumps(response, ensure_ascii=False)
        raw = _extract_json_block(raw)
        try:
            themes: List[Dict[str, Any]] = json.loads(raw)
        except json.JSONDecodeError as exc:
            preview = raw[:400] + "…" if len(raw) > 400 else raw
            LOGGER.warning(
                "[Theme Inference] Failed to parse LLM response for %s (error=%s). Raw: %s",
                person_id,
                exc,
                preview,
            )
            return None

        if not isinstance(themes, list):
            LOGGER.warning("[Theme Inference] Unexpected payload type for %s", person_id)
            return None

        reflection_ids = [row["id"] for row in reflections]
        for entry in themes:
            theme_name = entry.get("theme")
            if not theme_name:
                continue
            clarity = _coerce_score(entry.get("coherence"), default=0.7)
            energy_alignment = _coerce_score(entry.get("energy_alignment"), default=0.6)
            rhythm_state = {
                "energy_alignment": energy_alignment,
                "related_themes": entry.get("related_themes") or [],
                "reflection_ids": reflection_ids,
            }

            await db.execute(
                """
                DELETE FROM theme_states
                WHERE person_id = $1 AND theme = $2
                """,
                person_id,
                theme_name,
            )
            await db.execute(
                """
                INSERT INTO theme_states (
                    person_id,
                    theme,
                    rhythm_state,
                    emotional_state,
                    clarity_score,
                    updated_at
                )
                VALUES ($1, $2, $3::jsonb, $4::jsonb, $5, now())
                """,
                person_id,
                theme_name,
                json.dumps(rhythm_state, ensure_ascii=False),
                json.dumps(entry.get("emotional_state") or {}, ensure_ascii=False),
                clarity,
            )

        LOGGER.info("[Theme Inference] Updated %s themes for %s", len(themes), person_id)
        return {"themes_count": len(themes)}
    finally:
        await db.close()


def _coerce_score(value: Any, *, default: float) -> float:
    try:
        if value is None:
            return default
        score = float(value)
        return max(0.0, min(1.0, score))
    except (TypeError, ValueError):
        return default


def _extract_json_block(blob: str) -> str:
    text = (blob or "").strip()
    if text.startswith("```"):
        end_lang = text.find("\n")
        if end_lang != -1:
            text = text[end_lang + 1 :]
        if text.endswith("```"):
            text = text[:-3]
    text = text.strip()
    if text:
        closing_idx = max(text.rfind("]"), text.rfind("}"))
        if closing_idx != -1:
            text = text[: closing_idx + 1]
    text = _strip_trailing_commas(text)
    return text.strip()


def _strip_trailing_commas(text: str) -> str:
    return re.sub(r",(\s*[}\]])", r"\1", text)


__all__ = ["run_theme_inference"]
