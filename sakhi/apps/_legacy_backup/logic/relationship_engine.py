from __future__ import annotations

import asyncio
import math
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from sakhi.apps.api.core.db import exec as dbexec, dbfetchrow, q
from sakhi.apps.api.core.person_utils import resolve_person_id

DEFAULT_STATE = {
    "trust_score": 0.4,
    "attunement_score": 0.4,
    "emotional_safety": 0.5,
    "closeness_stage": "Warm",
    "preference_profile": {},
    "interaction_patterns": {},
}


def _clamp(val: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, val))


async def load_state(person_id: str) -> Dict[str, Any]:
    person_id = await resolve_person_id(person_id) or person_id
    try:
        row = await dbfetchrow(
            """
            SELECT trust_score, attunement_score, emotional_safety, closeness_stage,
                   preference_profile, interaction_patterns, updated_at
            FROM relationship_state
            WHERE person_id = $1
            """,
            person_id,
        )
        if row:
            return dict(row)
    except Exception:
        row = None

    await dbexec(
        """
        INSERT INTO relationship_state (person_id, trust_score, attunement_score, emotional_safety, closeness_stage)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (person_id) DO NOTHING
        """,
        person_id,
        DEFAULT_STATE["trust_score"],
        DEFAULT_STATE["attunement_score"],
        DEFAULT_STATE["emotional_safety"],
        DEFAULT_STATE["closeness_stage"],
    )
    return DEFAULT_STATE.copy()


def _next_stage(stage: str, trust: float, attune: float) -> str:
    score = min(trust, attune)
    if score >= 0.85:
        return "Strong Bond"
    if score >= 0.75:
        return "Deepening"
    if score >= 0.6:
        return "Supportive"
    return "Warm"


async def update_state(person_id: str, *, trust_delta: float = 0.0, attunement_delta: float = 0.0, safety_delta: float = 0.0, interaction_hint: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    person_id = await resolve_person_id(person_id) or person_id
    state = await load_state(person_id)
    trust_base = float(state.get("trust_score", DEFAULT_STATE["trust_score"]) or 0.0)
    attune_base = float(state.get("attunement_score", DEFAULT_STATE["attunement_score"]) or 0.0)
    safety_base = float(state.get("emotional_safety", DEFAULT_STATE["emotional_safety"]) or 0.0)

    trust = _clamp(trust_base + float(trust_delta or 0.0))
    attune = _clamp(attune_base + float(attunement_delta or 0.0))
    safety = _clamp(safety_base + float(safety_delta or 0.0))

    last_updated = state.get("updated_at")
    now = datetime.now(timezone.utc)
    allow_stage_change = True
    if isinstance(last_updated, datetime):
        allow_stage_change = (now - last_updated) >= timedelta(days=3)

    stage = state.get("closeness_stage") or DEFAULT_STATE["closeness_stage"]
    proposed_stage = _next_stage(stage, trust, attune)
    if allow_stage_change and proposed_stage != stage:
        stage = proposed_stage

    prefs = state.get("preference_profile") or {}
    interactions = state.get("interaction_patterns") or {}
    if interaction_hint:
        try:
            interactions.update(interaction_hint)
        except Exception:
            pass

    await dbexec(
        """
        INSERT INTO relationship_state (person_id, trust_score, attunement_score, emotional_safety, closeness_stage, preference_profile, interaction_patterns, updated_at)
        VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7::jsonb, NOW())
        ON CONFLICT (person_id)
        DO UPDATE SET
            trust_score = EXCLUDED.trust_score,
            attunement_score = EXCLUDED.attunement_score,
            emotional_safety = EXCLUDED.emotional_safety,
            closeness_stage = EXCLUDED.closeness_stage,
            preference_profile = EXCLUDED.preference_profile,
            interaction_patterns = EXCLUDED.interaction_patterns,
            updated_at = NOW()
        """,
        person_id,
        trust,
        attune,
        safety,
        stage,
        prefs,
        interactions,
    )

    # Mirror into personal_model if column exists.
    try:
        await dbexec(
            """
            UPDATE personal_model
            SET relationship_state = $2::jsonb,
                updated_at = NOW()
            WHERE person_id = $1
            """,
            person_id,
            {
                "trust_score": trust,
                "attunement_score": attune,
                "emotional_safety": safety,
                "closeness_stage": stage,
            },
        )
    except Exception:
        pass

    return {
        "trust_score": trust,
        "attunement_score": attune,
        "emotional_safety": safety,
        "closeness_stage": stage,
    }


# Heuristic event hooks (small deltas only, guardrails)

async def update_from_turn(person_id: str, sentiment: Optional[str] = None, pushback: bool = False) -> Dict[str, Any]:
    trust_delta = 0.02
    attune_delta = 0.02
    safety_delta = 0.01
    if pushback:
        trust_delta = -0.04
        attune_delta = -0.03
        safety_delta = -0.04
    elif sentiment:
        s = sentiment.lower()
        if "negative" in s or "frustrated" in s or "tired" in s:
            trust_delta = 0.0
            attune_delta = 0.01
            safety_delta = 0.02
        elif "positive" in s or "calm" in s:
            trust_delta = 0.03
            attune_delta = 0.03
            safety_delta = 0.02
    return await update_state(person_id, trust_delta=trust_delta, attunement_delta=attune_delta, safety_delta=safety_delta)


async def update_from_focus(person_id: str, completion_score: Optional[float]) -> Dict[str, Any]:
    score = completion_score if completion_score is not None else 0.5
    trust_delta = 0.03 if score >= 0.6 else -0.02
    attune_delta = 0.02 if score >= 0.6 else -0.01
    safety_delta = 0.01
    return await update_state(person_id, trust_delta=trust_delta, attunement_delta=attune_delta, safety_delta=safety_delta)


__all__ = [
    "load_state",
    "update_state",
    "update_from_turn",
    "update_from_focus",
]
