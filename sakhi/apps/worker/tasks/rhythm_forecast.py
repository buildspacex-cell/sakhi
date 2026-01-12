from __future__ import annotations

import datetime as dt
import json
import logging
from typing import Any, Dict, List

from sakhi.apps.api.core.db import get_db
from sakhi.libs.schemas.settings import get_settings

LOGGER = logging.getLogger(__name__)
# TODO(prod): reduce this window back to a bounded horizon (e.g., 14–30 days) once lab validation is done.
RHYTHM_WINDOW_DAYS = 1500
MIN_SIGNALS = 3
MIN_SAMPLES_PER_SLOT = 2
RHYTHM_SLOTS = {
    "early_morning": (5, 8),
    "morning": (8, 12),
    "afternoon": (12, 17),
    "evening": (17, 21),
    "night": (21, 24),
}

# Rhythm slots represent temporal capacity windows, not preferences or recommendations.

# Rhythm Worker Non-Goals:
# - Does not infer identity
# - Does not infer emotion meaning
# - Does not provide advice or recommendations
# - Does not generate narrative or forecasts
# - Does not call LLMs
# - Does not write vectors

# Rhythm Phase-2 Non-Goals:
# - Does not recommend actions
# - Does not decide “best time”
# - Does not infer identity or values
# - Does not use LLMs
# - Does not speak to the user

# Rhythm worker must be deterministic.
# Rhythm computation must be replay-stable.
# Identical inputs must produce identical outputs.

# Reflections are treated as weak temporal signals,
# not as semantic or narrative content.


async def run_rhythm_forecast(person_id: str) -> Dict[str, Any] | None:
    """
    Phase-1 deterministic rhythm lens over recent reflections.
    """
    settings = get_settings()
    if not settings.enable_rhythm_forecast_writes:
        LOGGER.info(
            "Rhythm forecast writes disabled by safety gate",
            extra={"person_id": person_id},
        )
        return None

    db = await get_db()
    try:
        LOGGER.info(
            "[Rhythm] start deterministic rhythm_state",
            extra={
                "person_id": person_id,
                "window_days": RHYTHM_WINDOW_DAYS,
                "min_signals": MIN_SIGNALS,
            },
        )

        # ================================
        # 1. Strict signal fetch (bounded window)
        # ================================
        # Rhythm signals are derived from raw, time-stamped evidence (journals), not from LLM-generated reflections.
        reflections = await db.fetch(
            """
            SELECT
              id,
              content,
              created_at
            FROM journal_entries
            WHERE user_id = $1
              AND created_at >= NOW() - ($2::int || ' days')::interval
            ORDER BY created_at DESC
            LIMIT 100
            """,
            person_id,
            RHYTHM_WINDOW_DAYS,
        )
        LOGGER.info(
            "[Rhythm] fetched rhythm signals",
            extra={
                "person_id": person_id,
                "count": len(reflections),
                "window_days": RHYTHM_WINDOW_DAYS,
            },
        )

        # ================================
        # 2. Guards for insufficient data
        # ================================
        if not reflections or len(reflections) < MIN_SIGNALS:
            LOGGER.info(
                "[Rhythm] skipped: insufficient signals",
                extra={
                    "person_id": person_id,
                    "signals": len(reflections or []),
                    "window_days": RHYTHM_WINDOW_DAYS,
                },
            )
            return None

        # ================================
        # 3. Deterministic scoring (keyword heuristics + slots)
        # ================================
        def _score_reflections(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
            energy_hits = 0.0
            load_hits = 0.0
            recovery_hits = 0.0
            strain_hits = 0.0
            terms_energy_up = ("energized", "focused", "good sleep", "rested")
            terms_energy_down = ("tired", "fatigue", "exhausted", "sleepy", "drained")
            terms_recovery = ("rest", "sleep", "nap", "recovery", "break", "walk", "stretch")
            terms_load = ("meeting", "back-to-back", "deadline", "overloaded", "packed")
            terms_strain = ("stress", "stressed", "anxious", "overwhelmed", "strain")

            for row in rows:
                text = (row.get("content") or "").lower()
                for t in terms_energy_up:
                    if t in text:
                        energy_hits += 1
                for t in terms_energy_down:
                    if t in text:
                        energy_hits -= 1
                        strain_hits += 0.5
                for t in terms_recovery:
                    if t in text:
                        recovery_hits += 1
                for t in terms_load:
                    if t in text:
                        load_hits += 1
                for t in terms_strain:
                    if t in text:
                        strain_hits += 1

            def _clamp(val: float, lo: float = 0.0, hi: float = 1.0) -> float:
                return max(lo, min(hi, val))

            n = max(1, len(rows))
            energy_level = _clamp(0.5 + energy_hits / (2 * n))
            load_level = _clamp(load_hits / (2 * n))
            recovery_level = _clamp(recovery_hits / (2 * n))
            strain_level = _clamp(strain_hits / (2 * n))
            volatility = _clamp(abs(energy_hits) / (3 * n))

            return {
                "energy_level": energy_level,
                "load_level": load_level,
                "recovery_level": recovery_level,
                "strain_level": strain_level,
                "volatility": volatility,
            }

        def slot_for_hour(hour: int) -> str:
            for slot, (start, end) in RHYTHM_SLOTS.items():
                if start <= hour < end:
                    return slot
            return "unknown"

        def _score_slots(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
            slot_metrics = {
                slot: {
                    "energy_level": 0.0,
                    "load_level": 0.0,
                    "recovery_level": 0.0,
                    "strain_level": 0.0,
                    "volatility": 0.0,
                    "samples": 0,
                    "confidence": 0.0,
                }
                for slot in RHYTHM_SLOTS.keys()
            }
            # Collect per-slot hits
            hits = {slot: {"energy": 0.0, "load": 0.0, "recovery": 0.0, "strain": 0.0} for slot in RHYTHM_SLOTS.keys()}

            terms_energy_up = ("energized", "focused", "good sleep", "rested")
            terms_energy_down = ("tired", "fatigue", "exhausted", "sleepy", "drained")
            terms_recovery = ("rest", "sleep", "nap", "recovery", "break", "walk", "stretch")
            terms_load = ("meeting", "back-to-back", "deadline", "overloaded", "packed")
            terms_strain = ("stress", "stressed", "anxious", "overwhelmed", "strain")

            for row in rows:
                created_at = row.get("created_at")
                try:
                    hour = int(created_at.hour) if created_at else None
                except Exception:
                    hour = None
                slot = slot_for_hour(hour) if hour is not None else "unknown"
                if slot not in slot_metrics:
                    continue
                text = (row.get("content") or "").lower()
                metrics = hits[slot]
                for t in terms_energy_up:
                    if t in text:
                        metrics["energy"] += 1
                for t in terms_energy_down:
                    if t in text:
                        metrics["energy"] -= 1
                        metrics["strain"] += 0.5
                for t in terms_recovery:
                    if t in text:
                        metrics["recovery"] += 1
                for t in terms_load:
                    if t in text:
                        metrics["load"] += 1
                for t in terms_strain:
                    if t in text:
                        metrics["strain"] += 1
                slot_metrics[slot]["samples"] += 1

            def _clamp(val: float, lo: float = 0.0, hi: float = 1.0) -> float:
                return max(lo, min(hi, val))

            for slot, m in slot_metrics.items():
                n = max(1, m["samples"])
                h = hits[slot]
                m["energy_level"] = _clamp(0.5 + h["energy"] / (2 * n))
                m["load_level"] = _clamp(h["load"] / (2 * n))
                m["recovery_level"] = _clamp(h["recovery"] / (2 * n))
                m["strain_level"] = _clamp(h["strain"] / (2 * n))
                m["volatility"] = _clamp(abs(h["energy"]) / (3 * n))
                if m["samples"] < MIN_SAMPLES_PER_SLOT:
                    m["confidence"] = 0.0
                else:
                    m["confidence"] = _clamp(m["samples"] / (MIN_SAMPLES_PER_SLOT * 3))

            return slot_metrics

        overall = _score_reflections(reflections)
        slots = _score_slots(reflections)

        # rhythm_state is descriptive, not interpretive.
        # No advice, no forecasts, no identity meaning.
        rhythm_state = {
            "overall": {
                **overall,
                "window_days": RHYTHM_WINDOW_DAYS,
            },
            "slots": slots,
            "window_days": RHYTHM_WINDOW_DAYS,
            "updated_at": dt.datetime.utcnow().isoformat(),
        }
        LOGGER.info(
            "[Rhythm] rhythm_state prepared",
            extra={
                "person_id": person_id,
                "overall": overall,
                "slot_samples": {k: v["samples"] for k, v in slots.items()},
            },
        )

        # ================================
        # 4. Update personal_model safely
        # ================================
        await db.execute(
            """
            UPDATE personal_model
            SET rhythm_state = $2::jsonb,
                updated_at = NOW()
            WHERE person_id = $1
            """,
            person_id,
            json.dumps(rhythm_state, ensure_ascii=False),
        )

        LOGGER.info(
            "[Rhythm] updated rhythm_state",
            extra={
                "person_id": person_id,
                "reflections": len(reflections),
                "window_days": RHYTHM_WINDOW_DAYS,
                "slots": {k: v["samples"] for k, v in slots.items()},
            },
        )

        return {
            "person_id": person_id,
            "rhythm_state": rhythm_state,
        }
    except Exception as exc:
        LOGGER.error("[Rhythm Forecast] failed for %s: %s", person_id, exc, exc_info=True)
        return None
