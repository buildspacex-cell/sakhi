from __future__ import annotations

import json
import logging
from decimal import Decimal
from typing import Any, Dict, List

from sakhi.apps.api.core.db import get_db
from sakhi.apps.api.middleware.auth_pilot import _mask_pii

LOGGER = logging.getLogger(__name__)


async def build_meta_context(person_id: str) -> Dict[str, Any]:
    """
    Aggregate short-term memory, rhythm, tone, themes, and persona data
    into a unified context blob for downstream LLM calls.
    """

    db = await get_db()
    context: Dict[str, Any] = {}
    try:
        model = await db.fetchrow(
            "SELECT * FROM personal_model WHERE person_id = $1",
            person_id,
        )
        if model:
            context["body"] = _ensure_mapping(model.get("body_state"))
            context["mind"] = _ensure_mapping(model.get("mind_state"))
            context["emotion"] = _ensure_mapping(model.get("emotion_state"))
            context["rhythm"] = _ensure_mapping(model.get("rhythm_state"))
            context["soul"] = _ensure_mapping(model.get("soul_state"))
            context["goals"] = _ensure_mapping(model.get("goals_state"))

        tone_pref = await db.fetchrow(
            """
            SELECT value
            FROM preferences
            WHERE person_id = $1 AND scope = 'persona' AND key = 'tone'
            LIMIT 1
            """,
            person_id,
        )
        if tone_pref:
            context["tone"] = _ensure_mapping(tone_pref.get("value"))

        forecast = await db.fetchrow(
            """
            SELECT recommendations
            FROM rhythm_forecasts
            WHERE person_id = $1
            ORDER BY created_at DESC
            LIMIT 1
            """,
            person_id,
        )
        if forecast:
            context["forecast_summary"] = forecast.get("recommendations")

        # Themes may not exist in older schemas; fallback safely
        try:
            themes = await db.fetch(
                """
                SELECT
                    COALESCE(theme, 'general') AS theme,
                    COALESCE(AVG(coherence), 0) AS clarity_score
                FROM reflections
                WHERE user_id = $1
                GROUP BY theme
                ORDER BY clarity_score DESC
                LIMIT 5
                """,
                person_id,
            )
        except Exception as exc:
            LOGGER.warning("[ContextBuilder] theme aggregation failed for %s: %s", person_id, exc)
            themes = []

        context["themes_summary"] = [
            {
                "theme": row.get("theme", "general"),
                "coherence": row.get("clarity_score", 0),
                "alignment": None,
            }
            for row in themes
        ]

        system_tempo = await db.fetchrow(
            """
            SELECT tempo, phase
            FROM system_tempo
            WHERE person_id = $1
            """,
            person_id,
        )
        if system_tempo:
            tempo_hint = (
                f"Sakhi breathes at {system_tempo.get('tempo', 8)} bpm, "
                f"currently in {system_tempo.get('phase', 'inhale')} phase. "
                "Adopt a pacing that reflects this rhythm — slower if exhale, brighter if inhale."
            )
            context["system_tempo"] = system_tempo
            context["tempo_hint"] = tempo_hint

        convo_state = await db.fetchrow(
            """
            SELECT last_emotion, energy_level
            FROM conversation_state
            WHERE person_id = $1
            """,
            person_id,
        )
        if convo_state:
            raw_energy = convo_state.get("energy_level")
            try:
                energy_level = float(raw_energy) if raw_energy is not None else 0.0
            except Exception:
                energy_level = 0.0

            convo_payload = {
                "last_emotion": convo_state.get("last_emotion"),
                "energy_level": energy_level,
            }
            context["conversation_state"] = convo_payload
            tone_hint = (
                f"Sakhi perceives the user as {convo_state.get('last_emotion', 'balanced')} "
                f"with energy {energy_level:.2f}. Respond in a tone that steadies and uplifts."
            )
            context["tone_hint"] = tone_hint

        meta_note = await db.fetchrow(
            """
            SELECT correction_note
            FROM meta_audit
            WHERE person_id = $1
            ORDER BY created_at DESC
            LIMIT 1
            """,
            person_id,
        )
        if meta_note:
            context["correction_note"] = meta_note.get("correction_note")

        emotion_state = context.get("emotion")
        if not isinstance(emotion_state, dict):
            emotion_state = _ensure_mapping(emotion_state)
            context["emotion"] = emotion_state
        mood_state = (emotion_state or {}).get("mood")
        bias_factor = 1.0
        if mood_state == "low":
            bias_factor = 0.8
        elif mood_state == "high":
            bias_factor = 1.2
        context["bias_factor"] = bias_factor

        try:
            from sakhi.apps.api.services.patterns.detector import build_patterns_context
            context["patterns"] = await build_patterns_context(person_id)
        except Exception as exc:  # pragma: no cover - context enrichment best effort
            LOGGER.warning("[ContextBuilder] pattern context failed for %s: %s", person_id, exc)
            context["patterns"] = "patterns unavailable"

        LOGGER.info("[ContextBuilder] built meta-context for %s", person_id)
        return _coerce_json(context)
    finally:
        await db.close()


async def build_calibration_context(person_id: str) -> str:
    """Legacy helper: return the meta-context rendered as a scrubbed string."""

    context = await build_meta_context(person_id)
    return _sanitize_payload(context)


def _ensure_mapping(value: Any) -> Dict[str, Any]:
    if not value:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def _sanitize_payload(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        text = value
    else:
        try:
            text = json.dumps(value, ensure_ascii=False)
        except Exception:
            text = str(value)
    masked = _mask_pii(text)
    return masked if len(masked) <= 6000 else f"{masked[:6000]}…"


def _coerce_json(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {k: _coerce_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_coerce_json(v) for v in value]
    if isinstance(value, tuple):
        return [_coerce_json(v) for v in value]
    return value


__all__ = ["build_meta_context", "build_calibration_context"]
