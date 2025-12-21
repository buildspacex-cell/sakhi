from __future__ import annotations

from fastapi import APIRouter

from sakhi.apps.api.core.db import q
from sakhi.core.emotion.emotion_soul_rhythm_engine import compute_fast_esr_frame

router = APIRouter(prefix="/esr", tags=["esr"])


@router.get("/{person_id}")
async def get_esr(person_id: str):
    pm = await q("SELECT emotion_state, soul_state, rhythm_state, emotion_soul_rhythm_state FROM personal_model WHERE person_id = $1", person_id, one=True)
    emotion = (pm or {}).get("emotion_state") or {}
    soul = (pm or {}).get("soul_state") or {}
    rhythm = (pm or {}).get("rhythm_state") or {}
    fast = compute_fast_esr_frame(emotion, soul, rhythm)
    deep = (pm or {}).get("emotion_soul_rhythm_state") or {}
    return {"fast": fast, "deep": deep}

