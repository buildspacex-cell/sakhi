from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from sakhi.apps.api.deps.auth import get_current_user_id
from sakhi.apps.api.services.loop.run_loop import run_loop, build_context, HISTORY_LIMIT
from sakhi.apps.api.services.memory.sessions import ensure_session, get_summary, load_recent_turns
from sakhi.apps.api.services.journaling.ai import generate_journaling_guidance

router = APIRouter(prefix="/journal", tags=["journal"])


class TurnIn(BaseModel):
    text: str
    session: str | None = "journal"


@router.post("/turn")
async def journal_turn_compat(body: TurnIn, user_id: str = Depends(get_current_user_id)):
    if not body.text.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty text")

    v2 = await run_loop(user_id, body.text, session_slug=body.session or "journal")

    return {
        "message": v2.get("reply") or "—",
        "dev": {
            "confirmations": v2.get("confirmations", []),
            "suggestions": v2.get("suggestions", []),
            "frontierTop3": v2.get("frontierTop3", []),
            "objective": v2.get("lastObjective"),
            "tone": v2.get("tone"),
            "mood": v2.get("mood"),
            "archetype": v2.get("archetype"),
            "usedSummary": v2.get("usedSummary"),
            "historyCount": v2.get("historyCount"),
            "session": v2.get("sessionSlug"),
            "sessionTitle": v2.get("sessionTitle"),
            "topicShift": {
                "shiftScore": v2.get("topicShift", {}).get("shift"),
                "semanticSim": v2.get("topicShift", {}).get("semantic_sim"),
                "hint": v2.get("switch", {}).get("hint"),
            },
            "switch": v2.get("switch", {}),
            "titlePrompted": v2.get("titlePrompted", False),
        },
    }


journal_turn_router = router


@router.get("/guide")
async def journal_guide(
    session: str | None = "journal",
    user_id: str = Depends(get_current_user_id),
):
    session_slug = session or "journal"
    session_id = await ensure_session(user_id, session_slug)
    history = await load_recent_turns(session_id, limit=HISTORY_LIMIT)
    summary = await get_summary(session_id)
    last_user_text = next(
        (turn.get("text") for turn in reversed(history) if turn.get("role") == "user"),
        "",
    )
    last_mood = next(
        (turn.get("tone") for turn in reversed(history) if turn.get("role") == "user"),
        None,
    )
    ctx = await build_context(user_id, session_id)
    guidance = generate_journaling_guidance(
        user_id=user_id,
        text=last_user_text or "",
        tone={"mood": (last_mood or "neutral")},
        context=ctx,
        summary=summary,
    )
    return guidance
