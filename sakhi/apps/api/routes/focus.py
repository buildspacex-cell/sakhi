from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from sakhi.apps.api.services.focus.engine import (
    end_focus_session,
    ping_focus_session,
    start_focus_session,
)

router = APIRouter(prefix="/focus", tags=["focus"])


class FocusStartIn(BaseModel):
    person_id: str
    task_id: Optional[str] = None
    estimated_duration: Optional[int] = Field(default=None, description="minutes")
    mode: str = Field(default="deep")


@router.post("/start")
async def focus_start(body: FocusStartIn) -> Dict[str, Any]:
    return await start_focus_session(body.person_id, body.task_id, body.estimated_duration, body.mode)


class FocusPingIn(BaseModel):
    session_id: str
    biomarkers: Optional[Dict[str, Any]] = None


@router.post("/ping")
async def focus_ping(body: FocusPingIn) -> Dict[str, Any]:
    return await ping_focus_session(body.session_id, body.biomarkers)


class FocusEndIn(BaseModel):
    session_id: str
    completion_score: Optional[float] = None
    session_quality: Optional[Dict[str, Any]] = None
    early_end: bool = False


@router.post("/end")
async def focus_end(body: FocusEndIn) -> Dict[str, Any]:
    return await end_focus_session(
        body.session_id,
        body.completion_score,
        body.session_quality,
        body.early_end,
    )


__all__ = ["router"]
