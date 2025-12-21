from __future__ import annotations

from fastapi import APIRouter

from sakhi.apps.api.core.db import q
from sakhi.core.soul.identity_momentum_engine import compute_fast_identity_momentum

router = APIRouter(prefix="/identity_momentum", tags=["identity_momentum"])


@router.get("/{person_id}")
async def get_identity_momentum(person_id: str):
    pm = await q(
        "SELECT soul_state, emotion_state, rhythm_state, identity_momentum_state FROM personal_model WHERE person_id = $1",
        person_id,
        one=True,
    )
    soul = (pm or {}).get("soul_state") or {}
    emotion = (pm or {}).get("emotion_state") or {}
    rhythm = (pm or {}).get("rhythm_state") or {}
    fast = compute_fast_identity_momentum([], soul, emotion, rhythm)
    deep = (pm or {}).get("identity_momentum_state") or {}
    return {"fast": fast, "deep": deep}

