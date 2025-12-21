from __future__ import annotations

import json
import logging
from decimal import Decimal
from typing import Any, Dict, List

from sakhi.apps.api.core.db import q as dbfetch

LOGGER = logging.getLogger(__name__)

def _ensure_mapping(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _first_row(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    return rows[0] if rows else {}


def _to_float(value: Any) -> Any:
    if isinstance(value, Decimal):
        try:
            return float(value)
        except Exception:
            return None
    return value


async def _build_deep_recall(person_id: str, limit: int = 3) -> Dict[str, Any]:
    recalls = await dbfetch(
        """
        SELECT id, turn_id, thread_id, stitched_summary, compact, vectors, signals, confidence, created_at
        FROM context_recalls
        WHERE person_id = $1
        ORDER BY created_at DESC
        LIMIT $2
        """,
        person_id,
        limit,
    )
    events = await dbfetch(
        """
        SELECT recall_id, event_label, weight, evidence, created_at
        FROM life_event_links
        WHERE person_id = $1
        ORDER BY created_at DESC
        LIMIT 2 * $2
        """,
        person_id,
        limit,
    )
    threads = await dbfetch(
        """
        SELECT thread_id, continuity_hint, persona_stability, last_turn_id, updated_at
        FROM thread_continuity_markers
        WHERE person_id = $1
        ORDER BY updated_at DESC
        LIMIT $2
        """,
        person_id,
        limit,
    )

    serialized_recalls = [
        {
            "id": str(r.get("id")),
            "turn_id": r.get("turn_id"),
            "thread_id": r.get("thread_id"),
            "stitched_summary": r.get("stitched_summary"),
            "compact": r.get("compact") or {},
            "vectors": r.get("vectors") or {},
            "signals": r.get("signals") or {},
            "confidence": _to_float(r.get("confidence")),
            "created_at": r.get("created_at"),
        }
        for r in recalls
    ]
    serialized_events = [
        {
            "recall_id": e.get("recall_id"),
            "event_label": e.get("event_label"),
            "weight": _to_float(e.get("weight")),
            "evidence": e.get("evidence") or {},
            "created_at": e.get("created_at"),
        }
        for e in events
    ]
    serialized_threads = [
        {
            "thread_id": t.get("thread_id"),
            "continuity_hint": t.get("continuity_hint"),
            "persona_stability": t.get("persona_stability") or {},
            "last_turn_id": t.get("last_turn_id"),
            "updated_at": t.get("updated_at"),
        }
        for t in threads
    ]

    return {
        "recalls": serialized_recalls,
        "life_events": serialized_events,
        "threads": serialized_threads,
    }


async def build_conversation_context(person_id: str) -> Dict[str, Any]:
    """
    Build a unified conversation context snapshot for the persona pipeline.
    """

    personal_rows = await dbfetch(
        """
        SELECT mind_state, emotion_state, rhythm_state, short_term, goals_state, data
        FROM personal_model
        WHERE person_id = $1
        """,
        person_id,
    )
    personal = _first_row(personal_rows)
    # Schema drift guard: fallback to data blob if explicit columns are empty.
    if personal and isinstance(personal.get("data"), dict):
        data_blob = personal.get("data") or {}
        personal.setdefault("mind_state", data_blob.get("mind_state"))
        personal.setdefault("emotion_state", data_blob.get("emotion_state"))
        personal.setdefault("rhythm_state", data_blob.get("rhythm_state"))
        personal.setdefault("short_term", data_blob.get("short_term"))
        personal.setdefault("goals_state", data_blob.get("goals_state"))

    conversation_rows = await dbfetch(
        """
        SELECT last_emotion, energy_level
        FROM conversation_state
        WHERE person_id = $1
        """,
        person_id,
    )
    conversation = _first_row(conversation_rows)

    try:
        continuity_rows = await dbfetch(
            """
            SELECT clarity_level, last_interaction_ts
            FROM session_continuity
            WHERE person_id = $1
            """,
            person_id,
        )
        continuity = _first_row(continuity_rows)
    except Exception as exc:  # pragma: no cover - schema drift guard
        LOGGER.warning(
            "[ConversationContext] session_continuity missing clarity_level for %s: %s",
            person_id,
            exc,
        )
        fallback_rows = await dbfetch(
            """
            SELECT last_interaction_ts
            FROM session_continuity
            WHERE person_id = $1
            """,
            person_id,
        )
        continuity = _first_row(fallback_rows)
        if continuity:
            continuity["clarity_level"] = None
        else:
            continuity = {"clarity_level": None}

    persona_rows = await dbfetch(
        """
        SELECT mode_name
        FROM persona_modes
        WHERE person_id = $1
        ORDER BY last_activated DESC
        LIMIT 1
        """,
        person_id,
    )
    persona_mode = persona_rows[0]["mode_name"] if persona_rows else "Reflective"

    theme_rows = await dbfetch(
        """
        SELECT theme, clarity_score
        FROM theme_states
        WHERE person_id = $1
        ORDER BY updated_at DESC
        LIMIT 6
        """,
        person_id,
    )
    themes = [
        {"theme": row.get("theme"), "clarity": row.get("clarity_score")}
        for row in theme_rows
        if row.get("theme")
    ]

    planner_rows = await dbfetch(
        """
        SELECT payload
        FROM planner_context_cache
        WHERE person_id = $1
        LIMIT 1
        """,
        person_id,
    )
    planner_payload: Dict[str, Any] = {}
    if planner_rows:
        raw_payload = planner_rows[0].get("payload")
        parsed_payload: Any = raw_payload
        if isinstance(raw_payload, str):
            try:
                parsed_payload = json.loads(raw_payload)
            except json.JSONDecodeError:
                parsed_payload = {}
        if isinstance(parsed_payload, dict):
            planner_payload = parsed_payload
    try:
        deep_recall = await _build_deep_recall(person_id)
    except Exception as exc:  # pragma: no cover - guard for missing schema during rollout
        LOGGER.warning("[ConversationContext] deep recall unavailable for %s: %s", person_id, exc)
        deep_recall = {"recalls": [], "life_events": [], "threads": []}

    return {
        "mind": _ensure_mapping(personal.get("mind_state")),
        "emotion": _ensure_mapping(personal.get("emotion_state")),
        "rhythm": _ensure_mapping(personal.get("rhythm_state")),
        "goals": _ensure_mapping(personal.get("goals_state")),
        "short_term": _ensure_mapping(personal.get("short_term")),
        "conversation": conversation,
        "continuity": continuity,
        "persona_mode": persona_mode or "Reflective",
        "themes": themes,
        "planner": planner_payload,
        "deep_recall": deep_recall,
    }


__all__ = ["build_conversation_context"]
