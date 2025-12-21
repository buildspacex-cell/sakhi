from __future__ import annotations

import datetime
from typing import Any, Dict, Mapping

from sakhi.apps.api.core.db import q, exec as dbexec
from sakhi.apps.api.core.person_utils import resolve_person_id
from sakhi.libs.schemas.settings import get_settings
import logging

logger = logging.getLogger(__name__)


async def _safe_get(sql: str, *args, one: bool = False) -> Mapping[str, Any]:
    try:
        row = await q(sql, *args, one=one)
        return row or {}
    except Exception:
        return {}


async def generate_daily_reflection(person_id: str) -> Dict[str, Any]:
    """Deterministic daily reflection summary (no LLM)."""
    resolved = await resolve_person_id(person_id) or person_id

    continuity = await _safe_get(
        "SELECT continuity_state FROM session_continuity WHERE person_id = $1",
        resolved,
        one=True,
    )
    continuity_state = continuity.get("continuity_state") or {}

    pm_row = await _safe_get(
        """
        SELECT emotion_state, tone_state, microreg_state, coherence_state, conflict_state, identity_state
        FROM personal_model
        WHERE person_id = $1
        """,
        resolved,
        one=True,
    )

    forecast_row = await _safe_get(
        "SELECT forecast_state FROM forecast_cache WHERE person_id = $1",
        resolved,
        one=True,
    )

    # Simple deterministic aggregations
    text_turns = continuity_state.get("last_text_turns") or []
    voice_inputs = continuity_state.get("last_voice_inputs") or []
    tasks = continuity_state.get("last_tasks") or []
    emotions = continuity_state.get("last_emotion_snapshots") or []
    microreg_snaps = continuity_state.get("last_microreg_snapshots") or []

    emotional_summary = f"Texts:{len(text_turns)} Voices:{len(voice_inputs)} RecentMood:{len(emotions)}"
    clarity_trend = "steady" if len(text_turns) >= len(voice_inputs) else "mixed"
    energy_pattern = "light" if len(tasks) < 2 else "active"
    overwhelm_events = [e for e in emotions if (e.get("risk") == "high" if isinstance(e, dict) else False)]
    task_alignment = "aligned" if len(tasks) <= 5 else "heavy"
    microreg_summary = f"microreg_entries={len(microreg_snaps)}"
    nudges_today = continuity_state.get("last_nudges") or []
    identity_drift_note = "stable" if (pm_row.get("identity_state") or {}).get("drift_score", 0) >= -0.1 else "watch drift"
    coherence_note = "ok" if (pm_row.get("coherence_state") or {}).get("coherence_score", 0.0) >= 0.5 else "low coherence"

    final_reflection = f"Emotions:{emotional_summary}; Clarity:{clarity_trend}; Energy:{energy_pattern}; Tasks:{task_alignment}; Coherence:{coherence_note}"

    summary = {
        "emotional_summary": emotional_summary,
        "clarity_trend": clarity_trend,
        "energy_pattern": energy_pattern,
        "overwhelm_events": overwhelm_events,
        "task_alignment": task_alignment,
        "microreg_summary": microreg_summary,
        "nudges_today": nudges_today,
        "identity_drift_note": identity_drift_note,
        "coherence_note": coherence_note,
        "final_reflection": final_reflection,
        "generated_at": datetime.datetime.utcnow().isoformat(),
    }

    return summary


async def persist_daily_reflection(person_id: str, summary: Dict[str, Any]) -> None:
    settings = get_settings()
    if not settings.enable_reflective_state_writes:
        logger.info("Worker disabled by safety gate: ENABLE_REFLECTIVE_STATE_WRITES=false")
        return

    resolved = await resolve_person_id(person_id) or person_id
    today = datetime.date.today()
    try:
        await dbexec(
            """
            INSERT INTO daily_reflection_cache (person_id, reflection_date, summary)
            VALUES ($1, $2, $3)
            ON CONFLICT (person_id, reflection_date)
            DO UPDATE SET summary = EXCLUDED.summary, generated_at = now()
            """,
            resolved,
            today,
            summary,
        )
    except Exception:
        return
    try:
        await dbexec(
            "UPDATE personal_model SET daily_reflection_state = $2 WHERE person_id = $1",
            resolved,
            summary,
        )
    except Exception:
        return


__all__ = ["generate_daily_reflection", "persist_daily_reflection"]
