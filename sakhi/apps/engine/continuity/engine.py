from __future__ import annotations

import datetime as dt
import uuid
from typing import Any, Dict, List, Sequence

from sakhi.apps.api.core.db import q, exec as dbexec
from sakhi.apps.api.core.person_utils import resolve_person_id


DEFAULT_STATE = {
    "last_text_turns": [],
    "last_voice_inputs": [],
    "last_reflections": [],
    "last_nudges": [],
    "last_tasks": [],
    "last_emotion_snapshots": [],
    "last_tone_snapshots": [],
    "last_forecast_snapshots": [],
    "threads": {"current": "general", "confidence": 0.5},
}

WINDOW_HOURS = 12


async def load_continuity(person_id: str) -> Dict[str, Any]:
    person_id = await resolve_person_id(person_id) or person_id
    row = await q("SELECT continuity_state FROM session_continuity WHERE person_id = $1", person_id, one=True) or {}
    state = row.get("continuity_state") or {}
    merged = {**DEFAULT_STATE, **state}
    return merged


def compute_continuity_markers(event: Dict[str, Any], memory_short_term: Sequence[Dict[str, Any]] | None = None, pattern_sense: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Derive continuity anchor/thread based on recent themes or patterns."""
    anchor_id = str(uuid.uuid4())
    thread = "general"
    confidence = 0.5
    memory_short_term = memory_short_term or []
    theme_counts: Dict[str, int] = {}
    for item in memory_short_term:
        theme = (item or {}).get("theme")
        if theme:
            theme_counts[theme] = theme_counts.get(theme, 0) + 1
    if theme_counts:
        top_theme = max(theme_counts.items(), key=lambda kv: kv[1])
        if top_theme[1] >= 2:
            thread = top_theme[0]
            confidence = min(0.9, 0.4 + 0.1 * top_theme[1])
    elif pattern_sense and isinstance(pattern_sense, dict):
        patterns = pattern_sense.get("patterns") or pattern_sense
        if isinstance(patterns, dict):
            for name, val in patterns.items():
                try:
                    strength = float(val.get("strength") or val.get("score") or 0.5)
                except Exception:
                    strength = 0.5
                if strength > confidence:
                    thread = name
                    confidence = strength
    return {"continuity_anchor_id": anchor_id, "continuity_thread": thread, "continuity_mode": event.get("type") or "text_message", "confidence": confidence}


def _prune(entries: List[Dict[str, Any]], max_len: int) -> List[Dict[str, Any]]:
    now = dt.datetime.utcnow()
    pruned: List[Dict[str, Any]] = []
    for item in entries:
        ts_raw = item.get("ts")
        try:
            ts = dt.datetime.fromisoformat(ts_raw.replace("Z", "+00:00")) if ts_raw else None
        except Exception:
            ts = None
        if ts and (now - ts).total_seconds() > WINDOW_HOURS * 3600:
            continue
        pruned.append(item)
    if len(pruned) > max_len:
        pruned = pruned[-max_len:]
    return pruned


async def update_continuity(person_id: str, event: Dict[str, Any], memory_short_term: Sequence[Dict[str, Any]] | None = None, pattern_sense: Dict[str, Any] | None = None) -> Dict[str, Any]:
    person_id = await resolve_person_id(person_id) or person_id
    state = await load_continuity(person_id)
    markers = compute_continuity_markers(event, memory_short_term, pattern_sense)
    ev = dict(event)
    ev.setdefault("ts", dt.datetime.utcnow().isoformat())

    event_type = ev.get("type") or "text_message"
    buckets = {
        "text_message": ("last_text_turns", 20),
        "voice_transcript": ("last_voice_inputs", 10),
        "reflection": ("last_reflections", 10),
        "task_created": ("last_tasks", 5),
        "task_edited": ("last_tasks", 5),
        "nudge_ack": ("last_nudges", 5),
        "planner_followup": ("last_tasks", 5),
    }
    bucket_name, max_len = buckets.get(event_type, ("last_text_turns", 20))
    entries = state.get(bucket_name) or []
    entries.append(ev)
    state[bucket_name] = _prune(entries, max_len)

    if ev.get("emotion"):
        emo_entries = state.get("last_emotion_snapshots") or []
        emo_entries.append({"ts": ev.get("ts"), "emotion": ev.get("emotion")})
        state["last_emotion_snapshots"] = _prune(emo_entries, 10)
    if ev.get("tone_state"):
        tone_entries = state.get("last_tone_snapshots") or []
        tone_entries.append({"ts": ev.get("ts"), "tone": ev.get("tone_state")})
        state["last_tone_snapshots"] = _prune(tone_entries, 10)
    if ev.get("forecast_state"):
        fc_entries = state.get("last_forecast_snapshots") or []
        fc_entries.append({"ts": ev.get("ts"), "forecast": ev.get("forecast_state")})
        state["last_forecast_snapshots"] = _prune(fc_entries, 5)

    state["threads"] = {"current": markers.get("continuity_thread") or "general", "confidence": markers.get("confidence", 0.5)}
    try:
        await dbexec(
            """
            INSERT INTO session_continuity (person_id, continuity_state, updated_at)
            VALUES ($1, $2, NOW())
            ON CONFLICT (person_id) DO UPDATE
            SET continuity_state = EXCLUDED.continuity_state,
                updated_at = NOW()
            """,
            person_id,
            state,
        )
    except Exception:
        pass
    return state


__all__ = ["load_continuity", "update_continuity", "compute_continuity_markers"]
