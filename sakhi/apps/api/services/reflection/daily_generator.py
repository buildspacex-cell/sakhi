from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

from sakhi.apps.api.core.db import get_db
from sakhi.apps.api.core.llm import call_llm
from sakhi.libs.llm_router.context_builder import build_calibration_context
from sakhi.libs.json_utils import extract_json_block
from sakhi.libs.schemas.settings import get_settings

LOGGER = logging.getLogger(__name__)


async def generate_daily_reflection(person_id: str) -> Dict[str, Any] | None:
    """
    Produce a daily reflection summary based on the last 24 hours.
    Pulls recent reflections, builds a context blob, and stores a meta_reflections row.
    """
    settings = get_settings()
    if not settings.enable_reflective_state_writes:
        LOGGER.info("Worker disabled by safety gate: ENABLE_REFLECTIVE_STATE_WRITES=false")
        return None

    db = await get_db()
    try:
        rows: List[Dict[str, Any]] = await db.fetch(
            """
            SELECT id, content, theme, created_at
            FROM reflections
            WHERE user_id = $1
              AND created_at >= NOW() - INTERVAL '1 day'
            ORDER BY created_at DESC
            """,
            person_id,
        )

        reflection_snippets = "\n".join(
            f"- [{row.get('theme') or 'general'}] {(row.get('content') or '').strip()}" for row in rows
        )
        if not reflection_snippets:
            reflection_snippets = "No reflections logged in the last 24 hours."

        context_blob = await build_calibration_context(person_id)

        prompt = f"""
Generate a DAILY REFLECTION for the user.
Summarize patterns from the last 24 hours and produce:
- emotional tone
- energy trend
- key insights
- 1–2 suggestions
- one concise narrative paragraph

Return ONLY valid JSON with these fields:
{{
  "tone": "...",
  "insights": ["...", "..."],
  "energy_trend": "...",
  "suggestions": ["...", "..."],
  "narrative": "..."
}}

Context (optional):
{context_blob or 'None'}

User reflection entries (last 24h):
{reflection_snippets}
""".strip()

        messages = [
            {"role": "system", "content": "You are Sakhi. Generate grounded, warm, concise reflections."},
            {"role": "user", "content": prompt},
        ]

        llm_model = "gpt-4o-mini"
        response = await call_llm(messages=messages, person_id=person_id, model=llm_model)
        payload = response if isinstance(response, str) else json.dumps(response, ensure_ascii=False)
        payload = extract_json_block(payload)

        try:
            data: Dict[str, Any] = json.loads(payload)
        except Exception as exc:
            LOGGER.error("[Daily Reflection] Failed to parse JSON for %s: %s", person_id, exc)
            return None

        await db.execute(
            """
            INSERT INTO meta_reflections (person_id, period, summary, insights)
            VALUES ($1, 'daily', $2, $3)
            """,
            person_id,
            data.get("narrative"),
            json.dumps(
                {
                    "tone": data.get("tone"),
                    "insights": data.get("insights"),
                    "energy_trend": data.get("energy_trend"),
                    "suggestions": data.get("suggestions"),
                },
                ensure_ascii=False,
            ),
        )

        LOGGER.info("[Daily Reflection] Generated summary for %s", person_id)
        return data
    finally:
        await db.close()


__all__ = ["generate_daily_reflection"]
