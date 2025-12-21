from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

from sakhi.apps.api.core.db import get_db
from sakhi.apps.api.core.llm import call_llm
from sakhi.libs.llm_router.context_builder import build_calibration_context
from sakhi.libs.json_utils import extract_json_block

LOGGER = logging.getLogger(__name__)


def _clamp_float(value: Any, default: float = 0.5) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return default


async def tune_persona(person_id: str) -> Dict[str, Any] | None:
    """
    Adjust persona traits based on recent conversation turns and calibration context.
    """

    db = await get_db()
    try:
        turns: List[Dict[str, Any]] = await db.fetch(
            """
            SELECT text, tone, archetype, created_at
            FROM conversation_turns
            WHERE user_id = $1
            ORDER BY created_at DESC
            LIMIT 20
            """,
            person_id,
        )

        persona_row = await db.fetchrow(
            "SELECT warmth, expressiveness, humor, reflectiveness, tone_bias FROM persona_traits WHERE person_id = $1",
            person_id,
        )

        context_blob = await build_calibration_context(person_id)
        turn_lines = "\n".join(
            f"- [{row.get('tone') or 'neutral'}] {(row.get('text') or '').strip()}"
            for row in turns
            if row.get("text")
        ) or "No recent turns available."

        prompt = f"""
Evaluate how Sakhi should tune its persona traits.

Return JSON ONLY with:
{{
  "warmth": 0.0-1.0,
  "expressiveness": 0.0-1.0,
  "humor": 0.0-1.0,
  "reflectiveness": 0.0-1.0,
  "tone_bias": "soft|direct|warm|neutral",
  "summary": "short reasoning"
}}

Context:
{context_blob or 'None'}

Recent turns:
{turn_lines}

Current persona traits:
{json.dumps(persona_row or {}, default=str, ensure_ascii=False)}
""".strip()

        messages = [
            {"role": "system", "content": "You are Sakhi — tune persona to improve user connection."},
            {"role": "user", "content": prompt},
        ]

        llm_model = "gpt-4o-mini"
        response = await call_llm(messages=messages, person_id=person_id, model=llm_model)
        payload = response if isinstance(response, str) else json.dumps(response, ensure_ascii=False)
        payload = extract_json_block(payload)

        try:
            data: Dict[str, Any] = json.loads(payload)
        except Exception as exc:
            LOGGER.error("[Persona Tuning] JSON parse failed for %s: %s", person_id, exc)
            return None

        warmth = _clamp_float(data.get("warmth"), default=0.8)
        expressiveness = _clamp_float(data.get("expressiveness"), default=0.5)
        humor = _clamp_float(data.get("humor"), default=0.3)
        reflectiveness = _clamp_float(data.get("reflectiveness"), default=0.7)
        tone_bias = (data.get("tone_bias") or "warm").strip() or "warm"

        await db.execute(
            """
            INSERT INTO persona_traits (person_id, warmth, expressiveness, humor, reflectiveness, tone_bias, last_updated)
            VALUES ($1, $2, $3, $4, $5, $6, NOW())
            ON CONFLICT (person_id)
            DO UPDATE SET
                warmth = EXCLUDED.warmth,
                expressiveness = EXCLUDED.expressiveness,
                humor = EXCLUDED.humor,
                reflectiveness = EXCLUDED.reflectiveness,
                tone_bias = EXCLUDED.tone_bias,
                last_updated = NOW()
            """,
            person_id,
            warmth,
            expressiveness,
            humor,
            reflectiveness,
            tone_bias,
        )

        LOGGER.info("[Persona Tuning] Updated persona traits for %s", person_id)
        return data
    finally:
        await db.close()


__all__ = ["tune_persona"]
