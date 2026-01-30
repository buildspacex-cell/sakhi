import logging

from fastapi import APIRouter, HTTPException

from sakhi.apps.logic.brain import brain_engine
from sakhi.apps.worker.tasks.brain_goals_themes_refresh import enqueue_brain_goals_themes_refresh

router = APIRouter(prefix="/brain", tags=["brain"])
logger = logging.getLogger(__name__)


@router.get("/state")
async def brain_state(person_id: str, force_refresh: bool = False):
    try:
        data = await brain_engine.get_brain_state(person_id, force_refresh=force_refresh)
        return {"status": "ok", "data": data}
    except Exception as exc:  # pragma: no cover - passthrough to API
        logger.exception("Failed to load brain state for %s", person_id)
        raise HTTPException(status_code=500, detail="Failed to load brain state") from exc


@router.get("/summary")
async def brain_summary(person_id: str, force_refresh: bool = False):
    try:
        data = await brain_engine.get_brain_summary(person_id, force_refresh=force_refresh)
        return {"status": "ok", "data": data}
    except Exception as exc:  # pragma: no cover - passthrough to API
        logger.exception("Failed to load brain summary for %s", person_id)
        raise HTTPException(status_code=500, detail="Failed to load brain summary") from exc


@router.get("/priorities")
async def brain_priorities(person_id: str, force_refresh: bool = False):
    try:
        data = await brain_engine.get_brain_priorities(person_id, force_refresh=force_refresh)
        return {"status": "ok", "data": data}
    except Exception as exc:  # pragma: no cover - passthrough to API
        logger.exception("Failed to load brain priorities for %s", person_id)
        raise HTTPException(status_code=500, detail="Failed to load brain priorities") from exc


@router.post("/goals_themes/refresh")
async def brain_goals_themes_refresh(person_id: str):
    try:
        enqueue_brain_goals_themes_refresh(person_id)
        return {"status": "queued"}
    except Exception as exc:  # pragma: no cover
        logger.exception("Failed to enqueue goals/themes refresh for %s", person_id)
        raise HTTPException(status_code=500, detail="Failed to enqueue") from exc
