from __future__ import annotations

from fastapi import APIRouter

from sakhi.apps.api.core.db import q
from sakhi.core.soul.identity_timeline_engine import compute_fast_identity_timeline_frame

router = APIRouter(prefix="/identity_timeline", tags=["identity_timeline"])


@router.get("/{person_id}")
async def get_identity_timeline(person_id: str):
    pm = await q(
        "SELECT soul_state, emotion_state, rhythm_state, identity_momentum_state, identity_timeline, persona_evolution_state FROM personal_model WHERE person_id = $1",
        person_id,
        one=True,
    )
    soul = (pm or {}).get("soul_state") or {}
    emotion = (pm or {}).get("emotion_state") or {}
    rhythm = (pm or {}).get("rhythm_state") or {}
    momentum = (pm or {}).get("identity_momentum_state") or {}
    fast = compute_fast_identity_timeline_frame([], soul, emotion, rhythm, momentum)
    deep_timeline = (pm or {}).get("identity_timeline") or {}
    persona_state = (pm or {}).get("persona_evolution_state") or {}
    return {"fast": fast, "deep": {"timeline": deep_timeline, "persona": persona_state}}

