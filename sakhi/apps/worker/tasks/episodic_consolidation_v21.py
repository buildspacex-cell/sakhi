from __future__ import annotations

"""
Soul conflict & soul friction are HIGH-STAKES signals.

Rules:
- NEVER infer from a single episode alone.
- NEVER populate unless confidence >= 0.6.
- EMPTY {} is a valid and preferred state.
- These fields represent longitudinal tension, not daily mood.
"""

import hashlib
import json
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Sequence

from sakhi.apps.api.core.db import exec as dbexec
from sakhi.apps.api.core.db import q as dbfetch
from sakhi.apps.worker.jobs import _get_router
from sakhi.libs.embeddings import embed_text, to_pgvector
from sakhi.libs.schemas import get_settings

# Memory Graph wiring for cross-entity relationships
try:
    from sakhi.apps.api.services.memory_graph.wiring import (
        ensure_time_slots,
        wire_activity_to_time_slot,
        wire_soul_conflict_to_graph,
        wire_soul_friction_to_graph,
        wire_soul_signals_to_graph,
    )
    MEMORY_GRAPH_ENABLED = True
except ImportError:
    MEMORY_GRAPH_ENABLED = False

LOGGER = logging.getLogger(__name__)


def _log(prefix: str, msg: str, **kwargs: Any) -> None:
    if kwargs:
        LOGGER.info("[%s] %s %s", prefix, msg, kwargs)
    else:
        LOGGER.info("[%s] %s", prefix, msg)


def _parse_ts(ts_val: Any) -> datetime | None:
    if isinstance(ts_val, datetime):
        return ts_val.astimezone(timezone.utc)
    if isinstance(ts_val, str):
        try:
            dt = datetime.fromisoformat(ts_val.replace("Z", "+00:00"))
            return dt.astimezone(timezone.utc)
        except Exception:
            return None
    return None


async def _fetch_journals(user_id: str, start: datetime, end: datetime) -> list[dict]:
    rows = await dbfetch(
        """
        SELECT id, content, ts
        FROM journal_entries
        WHERE user_id = $1
          AND ts >= $2
          AND ts < $3
        ORDER BY ts ASC
        """,
        user_id,
        start,
        end,
    )
    return [dict(row) for row in rows]


async def _fetch_health_context_for_window(
    user_id: str,
    window_start: datetime,
    window_end: datetime,
) -> str:
    """Fetch body_state_history for the episode window to include in summary."""
    try:
        rows = await dbfetch(
            """
            SELECT body_state
            FROM body_state_history
            WHERE person_id = $1
              AND computed_at >= $2 AND computed_at < $3
            ORDER BY computed_at DESC
            LIMIT 1
            """,
            user_id,
            window_start,
            window_end,
        )
        if not rows:
            return ""
        bs = rows[0].get("body_state") or {}
        if isinstance(bs, str):
            bs = json.loads(bs)
        parts = []
        sleep = bs.get("sleep", {})
        if sleep.get("duration_hours"):
            parts.append(f"Sleep: {sleep['duration_hours']:.1f}h ({sleep.get('quality', 'unknown')} quality)")
        vitals = bs.get("vitals", {})
        rhr = vitals.get("resting_heart_rate") or vitals.get("resting_hr")
        hrv = vitals.get("heart_rate_variability") or vitals.get("hrv_sdnn")
        if rhr:
            parts.append(f"Resting HR: {rhr} bpm")
        if hrv:
            parts.append(f"HRV: {hrv}ms")
        activity = bs.get("activity", {})
        if activity.get("steps"):
            parts.append(f"Steps: {activity['steps']}")
        if not parts:
            return ""
        return "\n[Health data for this day: " + ", ".join(parts) + "]"
    except Exception:
        return ""


async def _fetch_body_dosha_for_window(
    user_id: str,
    window_start: datetime,
    window_end: datetime,
) -> Dict[str, float]:
    """Fetch body dosha scores from body_state_history for blending into state_vector."""
    try:
        rows = await dbfetch(
            """
            SELECT vata_score, pitta_score, kapha_score
            FROM body_state_history
            WHERE person_id = $1
              AND computed_at >= $2 AND computed_at < $3
              AND vata_score IS NOT NULL
            ORDER BY computed_at DESC
            LIMIT 1
            """,
            user_id,
            window_start,
            window_end,
        )
        if not rows:
            return {}
        row = rows[0]
        vata = row.get("vata_score")
        pitta = row.get("pitta_score")
        kapha = row.get("kapha_score")
        if vata is None or pitta is None or kapha is None:
            return {}
        return {"vata": float(vata), "pitta": float(pitta), "kapha": float(kapha)}
    except Exception:
        return {}


async def _summarize_day(
    journals: Sequence[Dict[str, Any]],
    window_start: datetime,
    health_context: str = "",
) -> str:
    # Concatenate journal texts in chronological order
    corpus_parts: List[str] = []
    for j in journals:
        text = (j.get("content") or "").strip()
        if text:
            corpus_parts.append(text)
    corpus = "\n\n".join(corpus_parts).strip()
    # Append health context if available
    if health_context:
        corpus = corpus + "\n\n" + health_context if corpus else health_context
    fallback = f"Episodic summary (v2.1 stub) for {window_start.date()}"
    if not corpus:
        return fallback

    system_msg = (
        "Summarize the day as a whole in 2-4 sentences using neutral, factual language. "
        "Include any health data (sleep, heart rate, activity) as part of the factual picture. "
        "Do not give advice, interpretation, identity claims, or future predictions. "
        "Plain text only; no bullets, emojis, or headings."
    )
    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": corpus},
    ]
    model = (get_settings().model_reflect or os.getenv("MODEL_REFLECT")) or "gpt-4o-mini"
    try:
        router = _get_router()
        resp = await router.chat(messages=messages, model=model)
        summary = (resp.text or "").strip()
        if summary:
            return summary
    except Exception as exc:  # pragma: no cover - defensive
        _log("episodic_v21", f"llm_summary_failed {exc}")
    return fallback


async def _embed_summary(text: str) -> tuple[Sequence[float], bool]:
    vector = await embed_text(text)
    if isinstance(vector, list) and vector and isinstance(vector[0], list):
        vector = vector[0]
    if not isinstance(vector, list):
        return [], False
    return vector, True


# context_tags — canonical implementation now lives in kala
from kala.signals.context_tags import extract_context_tags  # noqa: E402


async def wire_episode_to_memory_graph(
    person_id: str,
    episode_id: str,
    soul_signals: Dict[str, List[str]],
    soul_conflict: Dict[str, Any],
    soul_friction: Dict[str, Any],
    activities: List[Dict[str, str]] = None,
) -> None:
    """
    Wire episode signals to the memory graph for cross-entity relationships.

    This enables intelligent context loading by creating nodes/edges for:
    - Core values, shadows, lights (soul signals)
    - Value conflicts (soul_conflict)
    - Direction vs block tensions (soul_friction)
    - Activities linked to time slots
    """
    if not MEMORY_GRAPH_ENABLED:
        return

    activities = activities or []

    try:
        # Ensure time slots exist for this person
        await ensure_time_slots(person_id)

        # Wire soul signals (values, patterns)
        if soul_signals:
            counts = await wire_soul_signals_to_graph(
                person_id=person_id,
                soul_signals=soul_signals,
                episode_id=episode_id,
            )
            if counts.get("value", 0) + counts.get("pattern", 0) > 0:
                _log(
                    "memory_graph",
                    "wired soul signals",
                    episode_id=episode_id,
                    values=counts.get("value", 0),
                    patterns=counts.get("pattern", 0),
                    edges=counts.get("edges", 0),
                )

        # Wire value conflicts (opposite_of edges)
        if soul_conflict and soul_conflict.get("themes"):
            edges = await wire_soul_conflict_to_graph(
                person_id=person_id,
                conflict_themes=soul_conflict.get("themes", []),
            )
            if edges > 0:
                _log(
                    "memory_graph",
                    "wired soul conflict",
                    episode_id=episode_id,
                    conflict_edges=edges,
                )

        # Wire soul friction (blocks edges)
        if soul_friction and soul_friction.get("areas"):
            edges = await wire_soul_friction_to_graph(
                person_id=person_id,
                friction_areas=soul_friction.get("areas", []),
            )
            if edges > 0:
                _log(
                    "memory_graph",
                    "wired soul friction",
                    episode_id=episode_id,
                    friction_edges=edges,
                )

        # Wire activities to time slots
        if activities:
            activities_wired = 0
            for act in activities:
                activity_name = act.get("activity", "")
                time_slot = act.get("time_slot", "")
                confidence = float(act.get("confidence", 0.5))
                if activity_name and time_slot:
                    await wire_activity_to_time_slot(
                        person_id=person_id,
                        activity_name=activity_name,
                        time_slot=time_slot,
                        weight=confidence,
                    )
                    activities_wired += 1
            if activities_wired > 0:
                _log(
                    "memory_graph",
                    "wired activities to time slots",
                    episode_id=episode_id,
                    activities_count=activities_wired,
                )

    except Exception as exc:
        _log(
            "memory_graph",
            f"wiring failed (non-fatal): {exc}",
            episode_id=episode_id,
        )


async def log_pattern_occurrences(
    person_id: str,
    episode_id: str,
    entry_id: str | None,
    soul_signals: Dict[str, List[str]],
    summary_snippet: str,
    confidence: float = 0.5,
) -> None:
    """
    Log pattern occurrences to pattern_occurrences table for crystallization.

    Patterns are logged here and only promoted to crystallized_patterns
    when they meet thresholds (handled by crystallization worker).
    """
    pattern_mappings = [
        ("core_value", soul_signals.get("soul") or []),
        ("shadow", soul_signals.get("soul_shadow") or []),
        ("light", soul_signals.get("soul_light") or []),
    ]

    snippet = (summary_snippet or "")[:500]  # Truncate for storage

    for pattern_type, values in pattern_mappings:
        for value in values:
            if not value or not value.strip():
                continue
            try:
                await dbexec(
                    """
                    INSERT INTO pattern_occurrences (
                        person_id, pattern_type, pattern_value,
                        episode_id, entry_id, snippet, confidence
                    )
                    VALUES ($1, $2, $3, $4::uuid, $5::uuid, $6, $7)
                    """,
                    person_id,
                    pattern_type,
                    value.strip()[:200],  # Truncate value
                    episode_id,
                    entry_id,
                    snippet,
                    confidence,
                )
            except Exception as exc:
                _log(
                    "pattern_occurrences",
                    f"failed to log {pattern_type}",
                    person_id=person_id,
                    value=value[:50],
                    error=str(exc),
                )

    count = sum(len(v) for v in [soul_signals.get("soul") or [], soul_signals.get("soul_shadow") or [], soul_signals.get("soul_light") or []])
    if count > 0:
        _log(
            "pattern_occurrences",
            f"logged {count} occurrences",
            person_id=person_id,
            episode_id=episode_id,
            core_values=len(soul_signals.get("soul") or []),
            shadows=len(soul_signals.get("soul_shadow") or []),
            lights=len(soul_signals.get("soul_light") or []),
        )


async def _fetch_existing_pattern_vocab(person_id: str) -> Dict[str, List[str]]:
    """Fetch the most common pattern labels already stored for this person.

    Returns a dict keyed by soul signal type with up to 15 labels each,
    ordered by frequency descending.  These are fed into the extraction
    prompt so the LLM reuses consistent vocabulary.
    """
    type_map = {
        "core_value": "soul",
        "shadow": "soul_shadow",
        "light": "soul_light",
    }
    vocab: Dict[str, List[str]] = {"soul": [], "soul_shadow": [], "soul_light": []}

    try:
        rows = await dbfetch(
            """
            SELECT pattern_type, pattern_value, COUNT(*) as cnt
            FROM pattern_occurrences
            WHERE person_id = $1
              AND pattern_type IN ('core_value', 'shadow', 'light')
            GROUP BY pattern_type, pattern_value
            ORDER BY cnt DESC, pattern_value
            """,
            person_id,
        )
        for row in rows:
            key = type_map.get(row["pattern_type"])
            if key and len(vocab[key]) < 15:
                vocab[key].append(row["pattern_value"])
    except Exception as exc:
        _log("episodic_v21", f"vocab_fetch_failed {exc}", person_id=person_id)

    return vocab


async def extract_episodic_soul(
    summary_text: str,
    existing_vocab: Dict[str, List[str]] | None = None,
) -> Dict[str, List[str]]:
    """
    Extract lightweight soul signals from an episodic summary.
    Must be neutral, non-interpretive, and grounded in the episode only.
    """
    # Build vocabulary hint block if we have prior patterns
    vocab_block = ""
    if existing_vocab and any(existing_vocab.values()):
        parts: list[str] = []
        for key, label in [("soul", "soul"), ("soul_shadow", "soul_shadow"), ("soul_light", "soul_light")]:
            items = existing_vocab.get(key) or []
            if items:
                parts.append(f"  {label}: {', '.join(items)}")
        if parts:
            vocab_block = (
                "\n\nPreviously used labels for this person (REUSE these exact phrases "
                "when the meaning matches — only create a new label if none of these fit):\n"
                + "\n".join(parts)
                + "\n"
            )

    prompt = f"""You are annotating a single day of lived experience.

From the text below, extract:

soul: core themes, values, or tensions present

soul_shadow: inner friction, avoidance, fear, or conflict present

soul_light: moments of alignment, clarity, relief, or growth present

Rules:

Use only what is evident in the text

Do NOT give advice, judgments, or identity claims

Do NOT infer future direction

Use short phrases only

IMPORTANT: When a label from the vocabulary list below matches what you observe, use that EXACT label. Only invent a new label when none of the existing ones fit.

If nothing is evident, return empty arrays{vocab_block}

Return valid JSON only in this exact shape:

{{
"soul": [],
"soul_shadow": [],
"soul_light": []
}}

Text:
\"\"\"{summary_text}\"\"\""""

    model = (get_settings().model_reflect or os.getenv("MODEL_REFLECT")) or "gpt-4o-mini"
    try:
        router = _get_router()
        resp = await router.chat(messages=[{"role": "user", "content": prompt}], model=model)
        raw = (resp.text or "").strip()
        parsed: Dict[str, Any] = json.loads(raw)
    except Exception as exc:  # pragma: no cover - defensive
        _log("episodic_v21", f"soul_extraction_failed {exc}")
        return {"soul": [], "soul_shadow": [], "soul_light": []}

    def _listify(val: Any) -> List[str]:
        if isinstance(val, list):
            return [str(x) for x in val if isinstance(x, (str, int, float))]
        return []

    return {
        "soul": _listify(parsed.get("soul")),
        "soul_shadow": _listify(parsed.get("soul_shadow")),
        "soul_light": _listify(parsed.get("soul_light")),
    }


async def extract_soul_conflict(recent_episode_summaries: list[str]) -> Dict[str, Any]:
    """
    Derives soul_conflict ONLY if repeated tension is evident across multiple episodes.
    """
    if len(recent_episode_summaries) < 3:
        return {}

    prompt = """
You are detecting recurring INNER VALUE CONFLICTS across multiple days.

Rules:
- Only output conflict if it clearly repeats across days.
- Do NOT infer from stress, fatigue, or workload.
- If evidence is weak, output EMPTY JSON {}.
- Output STRICT JSON only.

Definition:
Soul conflict = value vs value tension (e.g. growth vs stability).

Schema:
{
  "themes": [
    {
      "left": string,
      "right": string,
      "strength": number (0-1),
      "confidence": number (0-1)
    }
  ]
}
"""
    try:
        router = _get_router()
        model = (get_settings().model_reflect or os.getenv("MODEL_REFLECT")) or "gpt-4o-mini"
        resp = await router.chat(
            messages=[
                {"role": "system", "content": "You extract conservative, evidence-based inner conflicts."},
                {"role": "user", "content": prompt + "\n\nEPISODES:\n" + "\n---\n".join(recent_episode_summaries)},
            ],
            model=model,
        )
        raw = (resp.text or "").strip()
        parsed = json.loads(raw)
        themes = [t for t in parsed.get("themes", []) if t.get("confidence", 0) >= 0.6]
        return {"themes": themes} if themes else {}
    except Exception as exc:  # pragma: no cover - defensive
        _log("episodic_v21", f"soul_conflict_failed {exc}")
        return {}


async def extract_soul_friction(recent_episode_summaries: list[str]) -> Dict[str, Any]:
    """
    Derives soul_friction ONLY when direction is stable but action/resourcing is blocked.
    """
    if len(recent_episode_summaries) < 3:
        return {}

    prompt = """
You are detecting recurring MISALIGNMENT between inner direction
and lived reality across multiple days.

Rules:
- Only output friction if the same block repeats.
- Do NOT moralize or assign blame.
- If unclear, output EMPTY JSON {}.
- Output STRICT JSON only.

Definition:
Soul friction = value vs reality resistance.

Schema:
{
  "areas": [
    {
      "direction": string,
      "block": string,
      "intensity": number (0-1),
      "confidence": number (0-1)
    }
  ]
}
"""
    try:
        router = _get_router()
        model = (get_settings().model_reflect or os.getenv("MODEL_REFLECT")) or "gpt-4o-mini"
        resp = await router.chat(
            messages=[
                {"role": "system", "content": "You extract conservative resistance patterns."},
                {"role": "user", "content": prompt + "\n\nEPISODES:\n" + "\n---\n".join(recent_episode_summaries)},
            ],
            model=model,
        )
        raw = (resp.text or "").strip()
        parsed = json.loads(raw)
        areas = [a for a in parsed.get("areas", []) if a.get("confidence", 0) >= 0.6]
        return {"areas": areas} if areas else {}
    except Exception as exc:  # pragma: no cover - defensive
        _log("episodic_v21", f"soul_friction_failed {exc}")
        return {}


async def _fetch_recent_episode_summaries(user_id: str, limit: int = 5) -> list[str]:
    rows = await dbfetch(
        """
        SELECT text
        FROM memory_episodic
        WHERE user_id = $1
        ORDER BY created_at DESC
        LIMIT $2
        """,
        user_id,
        limit,
    )
    summaries: list[str] = []
    for row in rows:
        text = (row.get("text") or "").strip()
        if text:
            summaries.append(text)
    return summaries


async def _fetch_recent_episode_summaries_before(user_id: str, limit: int, before_ts: datetime) -> list[str]:
    rows = await dbfetch(
        """
        SELECT text
        FROM memory_episodic
        WHERE user_id = $1
          AND created_at < $2
        ORDER BY created_at DESC
        LIMIT $3
        """,
        user_id,
        before_ts,
        limit,
    )
    summaries: list[str] = []
    for row in rows:
        text = (row.get("text") or "").strip()
        if text:
            summaries.append(text)
    return summaries


async def extract_emotion_loop(recent_summaries: list[str]) -> Dict[str, Any]:
    """
    Extract recurring emotional dynamics across episodes.
    Must be confidence-gated and safe.
    """
    if len(recent_summaries) < 3:
        return {}

    prompt = """
You are analyzing multiple daily summaries of a person.

Identify whether there is a recurring emotional loop across days.
An emotional loop is a repeated emotional pattern, not a mood.

Rules:
- Only output a loop if there is clear repetition across days.
- Do not give advice, diagnosis, or predictions.
- If confidence is low, return {}.

Return JSON only with:
{
  "loop_type": string,
  "pattern": [string],
  "confidence": float,
  "notes": string
}
"""
    try:
        router = _get_router()
        model = (get_settings().model_reflect or os.getenv("MODEL_REFLECT")) or "gpt-4o-mini"
        resp = await router.chat(
            messages=[
                {"role": "system", "content": "You extract recurring emotional dynamics conservatively."},
                {"role": "user", "content": prompt + "\n\nEPISODES:\n" + "\n---\n".join(recent_summaries)},
            ],
            model=model,
        )
        raw = (resp.text or "").strip()
        parsed = json.loads(raw)
        confidence = float(parsed.get("confidence", 0.0))
        if confidence < 0.65:
            return {}
        return {
            "loop_type": parsed.get("loop_type"),
            "pattern": parsed.get("pattern") or [],
            "confidence": confidence,
            "notes": parsed.get("notes"),
        }
    except Exception as exc:  # pragma: no cover - defensive
        _log("episodic_v21", f"emotion_loop_failed {exc}")
        return {}


# Dosha state computation — canonical implementation now lives in kala
from kala.state.dosha import compute_dosha_state as _compute_dosha_state  # noqa: E402


async def extract_state_vector(
    summary_text: str,
    emotional_state: Dict[str, Any],
    rhythm_state: Dict[str, Any],
    body_dosha: Dict[str, float] | None = None,
) -> Dict[str, Any]:
    """Async wrapper for kala.state.dosha.compute_dosha_state."""
    return _compute_dosha_state(summary_text, emotional_state, rhythm_state, body_dosha)


# Guna state computation — canonical implementation now lives in kala
from kala.state.guna import compute_guna_state as _compute_guna_state  # noqa: E402


async def extract_guna_vector(summary_text: str, emotional_state: Dict[str, Any]) -> Dict[str, Any]:
    """Async wrapper for kala.state.guna.compute_guna_state."""
    return _compute_guna_state(summary_text, emotional_state)


async def extract_episodic_emotional_state(summary_text: str) -> Dict[str, Any]:
    """
    Returns a coarse emotional aggregate for the day.
    Must be stable, non-reactive, and trend-oriented.
    """
    prompt = """
You are extracting a coarse emotional state for a single day based on a summary.

Rules:
- Output STRICT JSON only.
- Do NOT include advice, interpretation, identity, or future prediction.
- Use coarse, aggregated signals only.
- If unclear, return neutral defaults.

Schema:
{
  "tone": "positive|neutral|negative|mixed",
  "valence": number between -1.0 and 1.0,
  "activation": number between 0.0 and 1.0,
  "stability": number between 0.0 and 1.0
}

Defaults if unclear:
tone="neutral", valence=0.0, activation=0.5, stability=0.5
"""
    try:
        router = _get_router()
        model = (get_settings().model_reflect or os.getenv("MODEL_REFLECT")) or "gpt-4o-mini"
        resp = await router.chat(
            messages=[{"role": "system", "content": "You extract structured emotional signals."}, {"role": "user", "content": prompt + "\n\nSUMMARY:\n" + summary_text}],
            model=model,
        )
        raw = (resp.text or "").strip()
        parsed = json.loads(raw)
        return {
            "tone": parsed.get("tone", "neutral"),
            "valence": float(parsed.get("valence", 0.0)),
            "activation": float(parsed.get("activation", 0.5)),
            "stability": float(parsed.get("stability", 0.5)),
        }
    except Exception as exc:  # pragma: no cover - defensive
        _log("episodic_v21", f"emotional_state_failed {exc}")
        return {
            "tone": "neutral",
            "valence": 0.0,
            "activation": 0.5,
            "stability": 0.5,
        }


async def extract_episodic_rhythm_state(summary_text: str) -> Dict[str, Any]:
    """
    Returns a macro rhythm assessment for the day.
    Focuses on sustainability, not momentary fatigue.
    """
    prompt = """
You are extracting a macro rhythm state for a single day.

Rules:
- Output STRICT JSON only.
- Do NOT include advice, interpretation, or future planning.
- Focus on trend-level rhythm signals only.
- If unclear, return neutral defaults.

Schema:
{
  "energy_trend": "up|down|flat",
  "load_balance": "underloaded|balanced|overextended",
  "recovery_signal": "adequate|insufficient|unknown"
}

Defaults if unclear:
energy_trend="flat", load_balance="balanced", recovery_signal="unknown"
"""
    try:
        router = _get_router()
        model = (get_settings().model_reflect or os.getenv("MODEL_REFLECT")) or "gpt-4o-mini"
        resp = await router.chat(
            messages=[{"role": "system", "content": "You extract rhythm sustainability signals."}, {"role": "user", "content": prompt + "\n\nSUMMARY:\n" + summary_text}],
            model=model,
        )
        raw = (resp.text or "").strip()
        parsed = json.loads(raw)
        return {
            "energy_trend": parsed.get("energy_trend", "flat"),
            "load_balance": parsed.get("load_balance", "balanced"),
            "recovery_signal": parsed.get("recovery_signal", "unknown"),
        }
    except Exception as exc:  # pragma: no cover - defensive
        _log("episodic_v21", f"rhythm_state_failed {exc}")
        return {
            "energy_trend": "flat",
            "load_balance": "balanced",
            "recovery_signal": "unknown",
        }


async def extract_activities_with_time_slots(summary_text: str) -> List[Dict[str, str]]:
    """
    Extract activities and their associated time slots from conversation text.

    Returns list of {activity, time_slot, confidence} dictionaries.
    Time slots: morning, afternoon, evening, night

    This enables the memory graph to track:
    - What activities the person does/wants to do
    - When they prefer to do them
    - Potential conflicts (two activities competing for morning slot)
    """
    prompt = """Extract activities mentioned in this text along with their time context.

Rules:
- Output STRICT JSON only.
- Focus on concrete activities/habits, not abstract concepts.
- Include activities they DO or WANT TO DO.
- Time slots: morning (6am-12pm), afternoon (12pm-6pm), evening (6pm-10pm), night (10pm-6am)
- If time is not explicitly stated, infer from context (e.g., "first thing" = morning)
- Skip activities with no time context.
- Confidence: 0.0-1.0 based on explicitness.

Schema:
{
  "activities": [
    {"activity": "yoga", "time_slot": "morning", "confidence": 0.9},
    {"activity": "work meeting", "time_slot": "afternoon", "confidence": 0.7}
  ]
}

Return empty activities array [] if none found with time context.
"""
    try:
        router = _get_router()
        model = (get_settings().model_reflect or os.getenv("MODEL_REFLECT")) or "gpt-4o-mini"
        resp = await router.chat(
            messages=[
                {"role": "system", "content": "You extract activities and their time contexts from text."},
                {"role": "user", "content": prompt + "\n\nTEXT:\n" + summary_text[:2000]}
            ],
            model=model,
        )
        raw = (resp.text or "").strip()
        parsed = json.loads(raw)
        activities = parsed.get("activities", [])

        # Validate and filter
        valid_slots = {"morning", "afternoon", "evening", "night"}
        validated = []
        for act in activities[:10]:  # Limit to 10
            if not act.get("activity") or not act.get("time_slot"):
                continue
            if act.get("time_slot", "").lower() not in valid_slots:
                continue
            confidence = float(act.get("confidence", 0.5))
            if confidence < 0.3:
                continue
            validated.append({
                "activity": act["activity"].lower().strip()[:50],
                "time_slot": act["time_slot"].lower().strip(),
                "confidence": confidence,
            })

        return validated

    except Exception as exc:
        _log("episodic_v21", f"activity_extraction_failed {exc}")
        return []


async def run_episodic_consolidation_v21(person_id: str, payload: Dict[str, Any]) -> None:
    """
    Episodic v2.1 skeleton: compute daily window, read journals, log exit path.
    """
    user_id = payload.get("user_id") or payload.get("thread_id") or person_id
    entry_id = payload.get("entry_id")
    ts_raw = payload.get("ts")
    ts = _parse_ts(ts_raw)

    if not user_id:
        _log("episodic_v21", "missing user_id/thread_id; skipping", entry_id=entry_id, ts=ts_raw)
        return
    if ts is None:
        _log("episodic_v21", "invalid ts; skipping", user_id=user_id, entry_id=entry_id, ts=ts_raw)
        return

    # Compute calendar day window in UTC
    # Episodic windowing MUST use journal_entries.ts only.
    # Never use created_at / updated_at / STM timestamps for episodic logic.
    window_start = datetime(ts.year, ts.month, ts.day, tzinfo=timezone.utc)
    window_end = window_start + timedelta(days=1)
    _log(
        "episodic_v21",
        "window",
        user_id=user_id,
        entry_id=entry_id,
        start=window_start.isoformat(),
        end=window_end.isoformat(),
    )

    journals = await _fetch_journals(user_id, window_start, window_end)
    count = len(journals)
    _log(
        "episodic_v21",
        "found journals",
        user_id=user_id,
        entry_id=entry_id,
        start=window_start.isoformat(),
        end=window_end.isoformat(),
        journal_count=count,
    )

    if count == 0:
        _log(
            "episodic_v21",
            "exit: no journals in window",
            user_id=user_id,
            entry_id=entry_id,
            start=window_start.isoformat(),
            end=window_end.isoformat(),
            journal_count=count,
        )
        return
    # Eligible for consolidation: compute source ids and dedup hash
    source_entry_ids = sorted([str(j["id"]) for j in journals])
    joined = "|".join(source_entry_ids)
    content_hash = hashlib.md5(joined.encode("utf-8"), usedforsecurity=False).hexdigest()
    _log(
        "episodic_v21",
        "eligible for consolidation",
        user_id=user_id,
        entry_id=entry_id,
        start=window_start.isoformat(),
        end=window_end.isoformat(),
        journal_count=count,
        source_entry_ids=source_entry_ids,
        content_hash=content_hash,
    )

    dedup_row = await dbfetch(
        """
        SELECT id, content_hash, record->>'source_entry_ids' as source_ids
        FROM memory_episodic
        WHERE user_id = $1
          AND record->>'episode_type' = 'daily'
          AND record->>'window_start' = $2
          AND record->>'window_end' = $3
        LIMIT 1
        """,
        user_id,
        window_start.isoformat(),
        window_end.isoformat(),
        one=True,
    )

    if dedup_row:
        existing_hash = dedup_row.get("content_hash")
        existing_episode_id = dedup_row.get("id")

        # Check if content changed (new journals added)
        if existing_hash == content_hash:
            _log(
                "episodic_v21",
                "exit: daily episode already exists with same content",
                user_id=user_id,
                entry_id=entry_id,
                start=window_start.isoformat(),
                end=window_end.isoformat(),
                journal_count=count,
                content_hash=content_hash,
                episode_id=existing_episode_id,
            )
            return

        # Content changed - update existing episode with new journals
        _log(
            "episodic_v21",
            "updating existing episode with new journals",
            user_id=user_id,
            entry_id=entry_id,
            start=window_start.isoformat(),
            end=window_end.isoformat(),
            journal_count=count,
            old_hash=existing_hash,
            new_hash=content_hash,
            episode_id=existing_episode_id,
        )

        # Fetch health context for the day (longitudinal integration)
        health_context = await _fetch_health_context_for_window(user_id, window_start, window_end)
        body_dosha = await _fetch_body_dosha_for_window(user_id, window_start, window_end)

        # Recalculate everything with all journals + health context
        summary_text = await _summarize_day(journals, window_start, health_context=health_context)
        vector_values, has_vec = await _embed_summary(summary_text)
        vector_literal = to_pgvector(vector_values, length=1536) if has_vec else None
        existing_vocab = await _fetch_existing_pattern_vocab(user_id)
        soul_signals = await extract_episodic_soul(summary_text, existing_vocab=existing_vocab)
        episodic_emotional_state = await extract_episodic_emotional_state(summary_text)
        episodic_rhythm_state = await extract_episodic_rhythm_state(summary_text)
        # Recompute state vectors for Friction Framework (blended with body dosha)
        state_vector = await extract_state_vector(summary_text, episodic_emotional_state, episodic_rhythm_state, body_dosha=body_dosha)
        guna_vector = await extract_guna_vector(summary_text, episodic_emotional_state)
        recent_summaries_prev = await _fetch_recent_episode_summaries_before(user_id, limit=7, before_ts=window_end)
        recent_summaries = [summary_text] + recent_summaries_prev
        soul_conflict = await extract_soul_conflict(recent_summaries)
        soul_friction = await extract_soul_friction(recent_summaries)
        emotion_loop = await extract_emotion_loop(recent_summaries)

        # Extract activities with time slots for memory graph
        activities = await extract_activities_with_time_slots(summary_text)

        # Log pattern occurrences for crystallization layer
        await log_pattern_occurrences(
            person_id=user_id,
            episode_id=str(existing_episode_id),
            entry_id=entry_id,
            soul_signals=soul_signals,
            summary_snippet=summary_text,
            confidence=0.6,  # Higher confidence for multi-journal episodes
        )

        # Wire to memory graph for cross-entity relationships
        await wire_episode_to_memory_graph(
            person_id=user_id,
            episode_id=str(existing_episode_id),
            soul_signals=soul_signals,
            soul_conflict=soul_conflict,
            soul_friction=soul_friction,
            activities=activities,
        )

        record_payload = {
            "source_entry_ids": source_entry_ids,
            "window_start": window_start.isoformat(),
            "window_end": window_end.isoformat(),
            "model_version": "episodic_v2.1",
            "episode_type": "daily",
            "summary": summary_text,
        }

        try:
            await dbexec(
                """
                UPDATE memory_episodic
                SET
                    text = $2,
                    record = $3::jsonb,
                    vector_vec = CASE
                        WHEN $4::text IS NULL THEN NULL::vector
                        ELSE ($4::text)::vector
                    END,
                    content_hash = $5,
                    context_tags = $6::jsonb,
                    soul = $7::jsonb,
                    soul_shadow = $8::jsonb,
                    soul_light = $9::jsonb,
                    emotional_state = $10::jsonb,
                    rhythm_state = $11::jsonb,
                    soul_conflict = $12::jsonb,
                    soul_friction = $13::jsonb,
                    emotion_loop = $14::jsonb,
                    state_vector = $15::jsonb,
                    guna_vector = $16::jsonb
                WHERE id = $1
                """,
                existing_episode_id,
                summary_text,
                json.dumps(record_payload, ensure_ascii=False),
                vector_literal,
                content_hash,
                json.dumps(extract_context_tags(summary_text)),
                json.dumps(soul_signals.get("soul") or []),
                json.dumps(soul_signals.get("soul_shadow") or []),
                json.dumps(soul_signals.get("soul_light") or []),
                json.dumps(episodic_emotional_state),
                json.dumps(episodic_rhythm_state),
                json.dumps(soul_conflict),
                json.dumps(soul_friction),
                json.dumps(emotion_loop),
                json.dumps(state_vector),
                json.dumps(guna_vector),
            )
            _log(
                "episodic_v21",
                "updated episode with new journals",
                user_id=user_id,
                entry_id=entry_id,
                episode_id=existing_episode_id,
                start=window_start.isoformat(),
                end=window_end.isoformat(),
                journal_count=count,
                content_hash=content_hash,
                source_entry_ids=source_entry_ids,
                has_vector=has_vec,
                summary_len=len(summary_text),
            )
            _log(
                "episodic_v21",
                "friction_vectors_updated",
                episode_id=existing_episode_id,
                state_vector_dosha=state_vector.get("dosha"),
                state_vector_conf=state_vector.get("confidence"),
                guna_vector_sattva=guna_vector.get("sattva"),
                guna_vector_rajas=guna_vector.get("rajas"),
                guna_vector_tamas=guna_vector.get("tamas"),
            )
        except Exception as exc:
            _log(
                "episodic_v21",
                f"update failed: {exc}",
                user_id=user_id,
                entry_id=entry_id,
                episode_id=existing_episode_id,
            )
        return

    # Fetch health context for the day (longitudinal integration)
    health_context = await _fetch_health_context_for_window(user_id, window_start, window_end)
    body_dosha = await _fetch_body_dosha_for_window(user_id, window_start, window_end)

    # Create new episode with health context
    summary_text = await _summarize_day(journals, window_start, health_context=health_context)
    vector_values, has_vec = await _embed_summary(summary_text)
    vector_literal = to_pgvector(vector_values, length=1536) if has_vec else None
    existing_vocab = await _fetch_existing_pattern_vocab(user_id)
    soul_signals = await extract_episodic_soul(summary_text, existing_vocab=existing_vocab)
    episodic_emotional_state = await extract_episodic_emotional_state(summary_text)
    episodic_rhythm_state = await extract_episodic_rhythm_state(summary_text)
    # Compute state vectors for Friction Framework (blended with body dosha)
    state_vector = await extract_state_vector(summary_text, episodic_emotional_state, episodic_rhythm_state, body_dosha=body_dosha)
    guna_vector = await extract_guna_vector(summary_text, episodic_emotional_state)
    recent_summaries_prev = await _fetch_recent_episode_summaries_before(user_id, limit=7, before_ts=window_end)
    recent_summaries = [summary_text] + recent_summaries_prev
    soul_conflict = await extract_soul_conflict(recent_summaries)
    soul_friction = await extract_soul_friction(recent_summaries)
    emotion_loop = await extract_emotion_loop(recent_summaries)

    # Extract activities with time slots for memory graph
    activities = await extract_activities_with_time_slots(summary_text)

    episode_id = str(uuid.uuid4())

    # Log pattern occurrences for crystallization layer
    await log_pattern_occurrences(
        person_id=user_id,
        episode_id=episode_id,
        entry_id=entry_id,
        soul_signals=soul_signals,
        summary_snippet=summary_text,
        confidence=0.6,  # Higher confidence for multi-journal episodes
    )

    # Wire to memory graph for cross-entity relationships
    await wire_episode_to_memory_graph(
        person_id=user_id,
        episode_id=episode_id,
        soul_signals=soul_signals,
        soul_conflict=soul_conflict,
        soul_friction=soul_friction,
        activities=activities,
    )

    record_payload = {
        "source_entry_ids": source_entry_ids,
        "window_start": window_start.isoformat(),
        "window_end": window_end.isoformat(),
        "model_version": "episodic_v2.1",
        "episode_type": "daily",
        "summary": summary_text,
    }
    try:
        await dbexec(
            """
            INSERT INTO memory_episodic (
                id,
                user_id,
                person_id,
                text,
                record,
                vector_vec,
                content_hash,
                context_tags,
                ts,
                created_at,
                soul,
                soul_shadow,
                soul_light,
                emotional_state,
                rhythm_state,
                soul_conflict,
                soul_friction,
                emotion_loop,
                state_vector,
                guna_vector
            )
            VALUES (
                $1,
                $2,
                $3::uuid,
                $4,
                $5::jsonb,
                CASE
                    WHEN $6::text IS NULL THEN NULL::vector
                    ELSE ($6::text)::vector
                END,
                $7,
                $8::jsonb,
                $9,
                $10,
                $11::jsonb,
                $12::jsonb,
                $13::jsonb,
                $14::jsonb,
                $15::jsonb,
                $16::jsonb,
                $17::jsonb,
                $18::jsonb,
                $19::jsonb,
                $20::jsonb
            )
            """,
            episode_id,
            user_id,
            person_id,
            summary_text,
            json.dumps(record_payload, ensure_ascii=False),
            vector_literal,
            content_hash,
            json.dumps(extract_context_tags(summary_text)),
            window_start,
            window_start,
            json.dumps(soul_signals.get("soul") or []),
            json.dumps(soul_signals.get("soul_shadow") or []),
            json.dumps(soul_signals.get("soul_light") or []),
            json.dumps(episodic_emotional_state),
            json.dumps(episodic_rhythm_state),
            json.dumps(soul_conflict),
            json.dumps(soul_friction),
            json.dumps(emotion_loop),
            json.dumps(state_vector),
            json.dumps(guna_vector),
        )
        _log(
            "episodic_v21",
            "created episode",
            user_id=user_id,
            entry_id=entry_id,
            episode_id=episode_id,
            start=window_start.isoformat(),
            end=window_end.isoformat(),
            journal_count=count,
            content_hash=content_hash,
            source_entry_ids=source_entry_ids,
            has_vector=has_vec,
            summary_len=len(summary_text),
        )
        _log(
            "episodic_v21",
            "soul_enriched",
            episode_id=episode_id,
            soul=len(soul_signals.get("soul") or []),
            shadow=len(soul_signals.get("soul_shadow") or []),
            light=len(soul_signals.get("soul_light") or []),
        )
        _log(
            "episodic_v21",
            "emotion_rhythm_enriched",
            episode_id=episode_id,
            has_emotion=bool(episodic_emotional_state),
            has_rhythm=bool(episodic_rhythm_state),
        )
        _log(
            "episodic_v21",
            "friction_vectors_enriched",
            episode_id=episode_id,
            state_vector_dosha=state_vector.get("dosha"),
            state_vector_conf=state_vector.get("confidence"),
            guna_vector_sattva=guna_vector.get("sattva"),
            guna_vector_rajas=guna_vector.get("rajas"),
            guna_vector_tamas=guna_vector.get("tamas"),
        )
        _log(
            "episodic_v22",
            "conflict_friction_enriched",
            episode_id=episode_id,
            has_conflict=bool(soul_conflict),
            has_friction=bool(soul_friction),
        )
        _log(
            "episodic_v23",
            "emotion_loop_enriched",
            episode_id=episode_id,
            has_loop=bool(emotion_loop),
            confidence=(emotion_loop or {}).get("confidence"),
        )
    except Exception as exc:  # pragma: no cover - defensive
        _log(
            "episodic_v21",
            f"error creating episode: {exc}",
            user_id=user_id,
            entry_id=entry_id,
            start=window_start.isoformat(),
            end=window_end.isoformat(),
            journal_count=count,
            content_hash=content_hash,
            source_entry_ids=source_entry_ids,
        )
    return None


__all__ = ["run_episodic_consolidation_v21"]
