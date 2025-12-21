from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List
import re
import numpy as np

from sakhi.apps.api.core.db import get_db
from sakhi.apps.api.core.llm import call_llm
from sakhi.apps.api.core.event_logger import log_event
from sakhi.libs.llm_router.context_builder import build_calibration_context
from sakhi.libs.json_utils import extract_json_block
from sakhi.libs.embeddings import embed_text, parse_pgvector, to_pgvector
from sakhi.libs.schemas.settings import get_settings

# IMPORTANT: All embeddings now flow through sakhi.libs.embeddings.embed_text, which
# guarantees deterministic 1536-d vectors. No stub providers or ad-hoc fallbacks remain.

LOGGER = logging.getLogger(__name__)
THEME_BIAS_WEIGHT = float(os.getenv("THEME_BIAS_WEIGHT", "0.2"))


async def run_rhythm_forecast(person_id: str) -> Dict[str, Any] | None:
    """
    Analyze recent reflections and rhythm state to produce a weekly forecast.
    """

    settings = get_settings()
    if not settings.enable_rhythm_forecast_writes:
        LOGGER.info("Rhythm forecast writes disabled by safety gate")
        return None

    await log_event(person_id, "rhythm", "Rhythm forecast started", {})
    db = await get_db()
    try:
        # ================================
        # 1. Strict reflection fetch
        # ================================
        reflections = await db.fetch(
            """
        SELECT id, content, theme, created_at
        FROM reflections
        WHERE user_id = $1
        ORDER BY created_at DESC
        LIMIT 14
        """,
        person_id,
    )
        # ================================
        # 2. Personal model load (safe)
        # ================================
        pm_row = await db.fetchrow(
            "SELECT rhythm_state FROM personal_model WHERE person_id = $1",
            person_id,
        )
        personal_model = pm_row or {}
        existing_state = personal_model.get("rhythm_state") if personal_model else {}

        reflection_snippets = "\n".join(
            f"- ({row.get('theme') or 'general'}) {(row.get('content') or '').strip()}"
            for row in reflections
            if row.get("content")
        ) or "No reflections available."

        context_blob = await build_calibration_context(person_id)
        prompt = (
            "Analyze the user's recent reflections and rhythm_state. "
            "Estimate next-week mood and energy trends. "
            "Return ONLY valid JSON with keys: "
            "energy_score (0-1), focus_score (0-1), emotion_score (0-1), "
            "mood_pattern (string), recommendation (string or list), "
            "forecast_text (string), forecast_vector (array of floats, e.g. [0.12, -0.34, ...]).\n\n"
            f"Existing rhythm_state: {existing_state or {}}\n"
            f"Reflections:\n{reflection_snippets}"
        )

        messages = []
        if context_blob:
            messages.append({"role": "system", "content": context_blob})
        messages.append({"role": "user", "content": prompt})

        llm_model = os.getenv("MODEL_RHYTHM_FORECAST") or "gpt-4o-mini"
        LOGGER.info("[Rhythm Forecast] calling LLM model=%s for %s", llm_model, person_id)

        response = await call_llm(
            messages=messages,
            person_id=person_id,
            model=llm_model,
        )
        payload = response if isinstance(response, str) else json.dumps(response, ensure_ascii=False)
        payload = extract_json_block(payload)
        try:
            result = json.loads(payload)
        except json.JSONDecodeError as exc:
            preview = payload[:400] + "…" if len(payload) > 400 else payload
            LOGGER.warning(
                "[Rhythm Forecast] LLM payload parse failed for %s (error=%s). Raw: %s",
                person_id,
                exc,
                preview,
            )
            return None

        energy_score = _coerce_score(result.get("energy_score"))
        focus_score = _coerce_score(result.get("focus_score"))
        mood_pattern = (result.get("mood_pattern") or "").strip() or None

        # --- Normalize forecast_text & recommendation safely ---
        raw_summary = result.get("summary")
        raw_text = result.get("forecast_text")
        raw_mood = result.get("mood_pattern")

        candidate = raw_summary or raw_text or raw_mood or ""
        if isinstance(candidate, list):
            candidate = " ".join(str(x) for x in candidate)
        forecast_text = str(candidate).strip() or "Weekly rhythm outlook pending."

        raw_reco = result.get("recommendation")
        if isinstance(raw_reco, list):
            raw_reco = " ".join(str(x) for x in raw_reco)
        recommendation_value_str = (raw_reco or "").strip()
        recommendation = recommendation_value_str or None
        emotion_score = _coerce_score(result.get("emotion_score"))
        # ================================
        # 3. Vector handling (strict)
        # ================================
        forecast_vector_raw = result.get("forecast_vector")

        vector_candidate: List[float] | None = None
        if forecast_vector_raw is not None:
            vector_candidate = sanitize_embedding(forecast_vector_raw)

        if not vector_candidate or len(vector_candidate) != 1536:
            vector_candidate = await embed_text(forecast_text)

        vector_clean = _validate_vector(vector_candidate, person_id)
        if len(vector_clean) != 1536:
            LOGGER.error(
                "[Rhythm Forecast] Invalid forecast_vector for %s: repairing to zeros",
                person_id,
            )
            vector_clean = [0.0] * 1536
        coherence = await compute_coherence(db, person_id, vector_clean)

        # ================================
        # 4. Theme rhythm correlation bias
        # ================================
        corr_rows = await db.fetch(
            "SELECT correlation FROM theme_rhythm_links WHERE person_id = $1",
            person_id,
        )
        theme_bias = (
            float(sum(row.get("correlation") or 0.0 for row in corr_rows)) / len(corr_rows)
            if corr_rows
            else 0.0
        )
        energy_score = _apply_bias(energy_score, theme_bias, THEME_BIAS_WEIGHT)
        focus_score = _apply_bias(focus_score, theme_bias, THEME_BIAS_WEIGHT * 0.5)

        energy_value = energy_score if energy_score is not None else 0.0
        focus_value = focus_score if focus_score is not None else 0.0
        emotion_value = emotion_score if emotion_score is not None else 0.0
        recommendation_list = [recommendation] if recommendation else []
        recommendation_value = json.dumps(recommendation_list, ensure_ascii=False)
        coherence_value = coherence if coherence is not None else 0.0
        stored_vector = to_pgvector(vector_clean)
        if not forecast_text:
            forecast_text = ""
        elif not isinstance(forecast_text, str):
            forecast_text = str(forecast_text)

        # ================================
        # 5. Write forecast safely
        # ================================
        await db.execute(
            """
            INSERT INTO rhythm_forecasts (
                person_id,
                predicted_energy,
                predicted_focus,
                predicted_emotion,
                forecast_text,
                forecast_vector,
                coherence,
                forecast_window,
                updated_at
            )
            VALUES ($1, $2, $3, $4, $5, $6::vector, $7, 'weekly', NOW())
            ON CONFLICT (person_id)
            DO UPDATE SET
                predicted_energy = EXCLUDED.predicted_energy,
                predicted_focus = EXCLUDED.predicted_focus,
                predicted_emotion = EXCLUDED.predicted_emotion,
                forecast_text = EXCLUDED.forecast_text,
                forecast_vector = EXCLUDED.forecast_vector,
                coherence = EXCLUDED.coherence,
                forecast_window = EXCLUDED.forecast_window,
                updated_at = NOW()
            """,
            person_id,
            energy_value,
            focus_value,
            emotion_value,
            forecast_text,
            stored_vector,
            coherence_value,
        )
        # ================================
        # 6. Update personal_model safely
        # ================================
        await db.execute(
            """
            UPDATE personal_model
            SET rhythm_state = jsonb_build_object(
                'energy_score', $2,
                'focus_score', $3,
                'emotion_score', $4,
                'forecast_text', $5,
                'coherence', $6,
                'recommendation', $7,
                'context', 'weekly'
            ),
            updated_at = NOW()
            WHERE person_id = $1
            """,
            person_id,
            energy_value,
            focus_value,
            emotion_value,
            forecast_text,
            coherence_value,
            recommendation_value,
        )

        await log_event(
            person_id,
            "rhythm",
            "Updated rhythm_forecast",
            {
                "energy_score": energy_score,
                "focus_score": focus_score,
                "emotion_score": emotion_score,
                "coherence": coherence_value,
            },
        )
        LOGGER.info("[Rhythm Forecast] Updated rhythm_state and forecast for %s", person_id)
        return {
            "person_id": person_id,
            "energy_score": energy_score,
            "focus_score": focus_score,
            "emotion_score": emotion_score,
            "forecast_text": forecast_text,
            "coherence": coherence_value,
            "recommendations": recommendation,
        }
    finally:
        await db.close()


def _coerce_score(value: Any) -> float | None:
    try:
        if value is None:
            return None
        score = float(value)
        return max(0.0, min(1.0, score))
    except (TypeError, ValueError):
        return None


def _apply_bias(base: float | None, bias: float, weight: float) -> float | None:
    if base is None:
        return None
    adjusted = base + (bias * weight)
    return max(0.0, min(1.0, adjusted))


def normalize_recommendation(val: Any) -> str | None:
    if val is None:
        return None
    if isinstance(val, str):
        val = val.strip()
        return val or None
    if isinstance(val, list):
        cleaned = [str(x).strip() for x in val if str(x).strip()]
        return "; ".join(cleaned) if cleaned else None
    val = str(val).strip()
    return val or None


def sanitize_embedding(raw: Any) -> List[float]:
    import re

    if isinstance(raw, list):
        return [float(x) for x in raw]
    if raw is None:
        return []
    cleaned = re.sub(r"[^0-9eE\.\-,]+", " ", str(raw))
    parts = cleaned.replace("\n", " ").split()
    try:
        return [float(p) for p in parts]
    except ValueError:
        return []


def _validate_vector(vec: Any, person_id: str) -> List[float]:
    if not isinstance(vec, list):
        LOGGER.error("[Rhythm] Invalid vector type for %s: %s", person_id, type(vec))
        return [0.0] * 1536
    if len(vec) != 1536:
        LOGGER.warning(
            "[Rhythm] Vector length mismatch for %s: got=%s expected=1536",
            person_id,
            len(vec),
        )
        return [0.0] * 1536
    try:
        return [float(x) for x in vec]
    except Exception:
        LOGGER.error("[Rhythm] Non-float entries in vector for %s", person_id)
        return [0.0] * 1536


async def compute_coherence(db: Any, person_id: str, new_vector: List[float]) -> float:
    if not new_vector or len(new_vector) != 1536:
        return 0.0
    rows = await db.fetch(
        "SELECT forecast_vector FROM rhythm_forecasts WHERE person_id = $1",
        person_id,
    )
    vectors = []
    for row in rows:
        parsed = parse_pgvector(row.get("forecast_vector"))
        if len(parsed) != 1536:
            continue
        vectors.append(np.array(parsed, dtype=float))
    if not vectors:
        return 1.0
    prev = np.mean(vectors, axis=0)
    numerator = float(np.dot(prev, np.array(new_vector, dtype=float)))
    denom = float(np.linalg.norm(prev) * np.linalg.norm(new_vector))
    if denom == 0:
        return 0.0
    return round(numerator / denom, 4)


__all__ = ["run_rhythm_forecast"]
