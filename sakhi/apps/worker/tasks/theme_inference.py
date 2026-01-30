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
    # Handle case where LLM prefixes text before markdown code block
    if "```json" in text:
        start_idx = text.find("```json")
        text = text[start_idx + 7:]  # Skip ```json
        if "```" in text:
            end_idx = text.find("```")
            text = text[:end_idx]
    elif "```" in text:
        start_idx = text.find("```")
        text = text[start_idx + 3:]
        # Skip language identifier if present
        if text.startswith("\n") or text[0:1].isalpha():
            end_lang = text.find("\n")
            if end_lang != -1:
                text = text[end_lang + 1:]
        if "```" in text:
            end_idx = text.find("```")
            text = text[:end_idx]
    elif text.startswith("```"):
        end_lang = text.find("\n")
        if end_lang != -1:
            text = text[end_lang + 1 :]
        if text.endswith("```"):
            text = text[:-3]
    text = text.strip()
    # Find JSON array or object boundaries
    if text:
        # Find the first [ or { to start JSON
        array_start = text.find("[")
        obj_start = text.find("{")
        if array_start >= 0 and (obj_start < 0 or array_start < obj_start):
            text = text[array_start:]
        elif obj_start >= 0:
            text = text[obj_start:]
        # Find closing bracket
        closing_idx = max(text.rfind("]"), text.rfind("}"))
        if closing_idx != -1:
            text = text[: closing_idx + 1]
    text = _strip_trailing_commas(text)
    return text.strip()


def _strip_trailing_commas(text: str) -> str:
    return re.sub(r",(\s*[}\]])", r"\1", text)


async def run_theme_inference_incremental(person_id: str) -> Dict[str, Any]:
    """
    Incremental theme inference with upranking and decay.

    - Boost clarity for recurring themes (+10% per occurrence)
    - Decay unused themes (-15% per week)
    - Never delete, just deprioritize

    This complements the full run_theme_inference by maintaining
    theme momentum based on crystallized patterns.
    """
    db = await get_db()
    try:
        # Get crystallized theme patterns
        crystallized_themes = await db.fetch(
            """
            SELECT pattern_value, confidence, mention_count, last_seen
            FROM crystallized_patterns
            WHERE person_id = $1
              AND pattern_type = 'theme'
              AND status = 'active'
            """,
            person_id,
        )

        # Get existing theme states
        existing_themes = await db.fetch(
            """
            SELECT theme, clarity_score, updated_at
            FROM theme_states
            WHERE person_id = $1
            """,
            person_id,
        )

        existing_map = {
            row["theme"]: {
                "clarity": row.get("clarity_score", 0.5),
                "updated_at": row.get("updated_at"),
            }
            for row in existing_themes
        }

        boosted = 0
        decayed = 0

        # Boost themes that appear in crystallized patterns
        for crystal in crystallized_themes:
            theme_name = crystal.get("pattern_value")
            if not theme_name:
                continue

            crystal_confidence = float(crystal.get("confidence", 0.5))
            mention_count = crystal.get("mention_count", 1)

            # Calculate boost: base +10% per occurrence beyond threshold
            boost = min(0.25, 0.10 * max(0, mention_count - 3))

            if theme_name in existing_map:
                # Update existing theme
                current_clarity = existing_map[theme_name]["clarity"]
                new_clarity = min(0.95, current_clarity + boost)

                await db.execute(
                    """
                    UPDATE theme_states
                    SET clarity_score = $3, updated_at = NOW()
                    WHERE person_id = $1 AND theme = $2
                    """,
                    person_id,
                    theme_name,
                    new_clarity,
                )
                boosted += 1
            else:
                # Create new theme from crystallized pattern
                await db.execute(
                    """
                    INSERT INTO theme_states (
                        person_id, theme, rhythm_state, emotional_state,
                        clarity_score, updated_at
                    )
                    VALUES ($1, $2, '{}'::jsonb, '{}'::jsonb, $3, NOW())
                    ON CONFLICT (person_id, theme) DO UPDATE
                    SET clarity_score = EXCLUDED.clarity_score, updated_at = NOW()
                    """,
                    person_id,
                    theme_name,
                    crystal_confidence,
                )
                boosted += 1

        # Decay themes not in crystallized patterns
        crystallized_names = {c.get("pattern_value") for c in crystallized_themes}

        for theme_name, theme_data in existing_map.items():
            if theme_name in crystallized_names:
                continue  # Already boosted

            updated_at = theme_data.get("updated_at")
            if not updated_at:
                continue

            # Calculate weeks since last update
            from datetime import datetime, timezone

            now = datetime.now(timezone.utc)
            if hasattr(updated_at, "tzinfo") and updated_at.tzinfo is None:
                updated_at = updated_at.replace(tzinfo=timezone.utc)

            weeks_since = (now - updated_at).days / 7

            if weeks_since < 1:
                continue  # Only decay after a week

            # Apply decay: -15% per week
            current_clarity = theme_data["clarity"]
            decay = 0.15 * weeks_since
            new_clarity = max(0.1, current_clarity - decay)

            await db.execute(
                """
                UPDATE theme_states
                SET clarity_score = $3, updated_at = NOW()
                WHERE person_id = $1 AND theme = $2
                """,
                person_id,
                theme_name,
                new_clarity,
            )
            decayed += 1

        LOGGER.info(
            "[Theme Inference] Incremental update for %s: boosted=%d, decayed=%d",
            person_id,
            boosted,
            decayed,
        )

        return {
            "boosted": boosted,
            "decayed": decayed,
            "crystallized_themes": len(crystallized_themes),
        }

    finally:
        await db.close()


__all__ = ["run_theme_inference", "run_theme_inference_incremental"]
