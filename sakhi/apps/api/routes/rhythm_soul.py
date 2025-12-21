from __future__ import annotations

from fastapi import APIRouter

from sakhi.apps.api.core.db import q
from sakhi.core.rhythm.rhythm_soul_engine import compute_fast_rhythm_soul_frame

router = APIRouter(prefix="/rhythm_soul", tags=["rhythm_soul"])


@router.get("/{person_id}")
async def get_rhythm_soul(person_id: str):
    pm = await q("SELECT rhythm_soul_state, rhythm_state, soul_state FROM personal_model WHERE person_id = $1", person_id, one=True)
    deep = (pm or {}).get("rhythm_soul_state") or {}
    fast = compute_fast_rhythm_soul_frame([], (pm or {}).get("rhythm_state") or {}, (pm or {}).get("soul_state") or {})
    return {"fast": fast, "deep": deep}

