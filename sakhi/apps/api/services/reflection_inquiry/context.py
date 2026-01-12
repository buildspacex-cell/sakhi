from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from sakhi.apps.api.core.db import q
from sakhi.apps.api.services.reflection.narration_foundation import generate_foundation_narration
from sakhi.apps.api.services.reflection_inquiry.dao import list_recent_inquiry_turns


def _coerce_json(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return {}
    return {}


async def _load_states(person_id: str) -> Dict[str, Any]:
    try:
        row = await q(
            """
            SELECT soul_state,
                   identity_momentum_state,
                   rhythm_state,
                   emotion_state,
                   emotion_soul_rhythm_state,
                   longitudinal_state
            FROM personal_model
            WHERE person_id = $1
            """,
            person_id,
        )
        if row:
            row = row[0]
            return {
                "soul_state": _coerce_json(row.get("soul_state")),
                "identity_momentum_state": _coerce_json(row.get("identity_momentum_state")),
                "rhythm_state": _coerce_json(row.get("rhythm_state")),
                "emotion_state": _coerce_json(row.get("emotion_state")),
                "emotion_soul_rhythm_state": _coerce_json(row.get("emotion_soul_rhythm_state")),
                "longitudinal_state": _coerce_json(row.get("longitudinal_state")),
            }
    except Exception:
        pass
    return {}


async def _load_journals(person_id: str, window_days: int) -> List[Dict[str, Any]]:
    try:
        rows = await q(
            """
            SELECT id, content, created_at
            FROM journal_entries
            WHERE user_id = $1
              AND created_at >= NOW() - ($2::int || ' days')::interval
            ORDER BY created_at DESC
            LIMIT 20
            """,
            person_id,
            window_days,
        )
        journals: List[Dict[str, Any]] = []
        total_chars = 0
        for row in rows or []:
            content = (row.get("content") or "").strip()
            if not content:
                continue
            if total_chars + len(content) > 2000:
                break
            total_chars += len(content)
            journals.append(
                {
                    "id": row.get("id"),
                    "content": content[:240],
                    "created_at": row.get("created_at"),
                }
            )
        return journals
    except Exception:
        return []


async def _load_episodic(person_id: str, window_days: int) -> List[Dict[str, Any]]:
    try:
        rows = await q(
            """
            SELECT id,
                   COALESCE(record->>'summary', text, '') AS summary,
                   ts
            FROM memory_episodic
            WHERE person_id = $1
              AND ts >= NOW() - ($2::int || ' days')::interval
            ORDER BY ts DESC
            LIMIT 10
            """,
            person_id,
            window_days,
        )
        episodic: List[Dict[str, Any]] = []
        total_chars = 0
        for row in rows or []:
            summary = (row.get("summary") or "").strip()
            if not summary:
                continue
            if total_chars + len(summary) > 1000:
                break
            total_chars += len(summary)
            episodic.append(
                {
                    "id": row.get("id"),
                    "summary": summary,
                    "ts": row.get("ts"),
                }
            )
        return episodic
    except Exception:
        return []


async def assemble_inquiry_context(
    *,
    person_id: str,
    reflection_id: str,
    window_days: int = 7,
    question_text: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build a compact context for reflection inquiry.
    """
    # Anchor to current reflection output (foundation narration).
    reflection = await generate_foundation_narration(person_id=person_id, window_days=window_days, include_debug=False)
    if not reflection:
        raise ValueError("Reflection not available for this person.")

    states = await _load_states(person_id)
    journals = await _load_journals(person_id, window_days)
    episodic = await _load_episodic(person_id, window_days)
    recent_questions = await list_recent_inquiry_turns(person_id=person_id, reflection_id=reflection_id, limit=5)

    return {
        "reflection": {
            "id": reflection_id,
            "text": reflection.get("reflection_text") or "",
            "support": reflection.get("reflection_support") or {},
            "timeframe": reflection.get("timeframe")
            or {"mode": "rolling", "anchor_days": window_days, "context": "longitudinal"},
        },
        "states": states,
        "evidence": {
            "journals": journals,
            "episodic": episodic[:3] if len(journals or []) >= 3 else episodic,
        },
        "recent_questions": [{"id": r.get("id"), "question": r.get("question_text"), "asked_at": r.get("created_at")} for r in recent_questions],
        "question_text": question_text or "",
    }
