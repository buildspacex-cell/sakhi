from fastapi import APIRouter, HTTPException

from sakhi.apps.logic.journey import renderer

router = APIRouter(prefix="/journey", tags=["journey"])


@router.get("/today")
async def journey_today(person_id: str, force_refresh: bool = False):
    try:
        data = await renderer.get_today(person_id, force_refresh=force_refresh)
        return {"status": "ok", "data": data}
    except Exception as exc:  # pragma: no cover - passthrough to API
        raise HTTPException(status_code=500, detail="Failed to build journey snapshot") from exc


@router.get("/week")
async def journey_week(person_id: str, force_refresh: bool = False):
    try:
        data = await renderer.get_week(person_id, force_refresh=force_refresh)
        return {"status": "ok", "data": data}
    except Exception as exc:  # pragma: no cover - passthrough to API
        raise HTTPException(status_code=500, detail="Failed to build journey snapshot") from exc


@router.get("/month")
async def journey_month(person_id: str, force_refresh: bool = False):
    try:
        data = await renderer.get_month(person_id, force_refresh=force_refresh)
        return {"status": "ok", "data": data}
    except Exception as exc:  # pragma: no cover - passthrough to API
        raise HTTPException(status_code=500, detail="Failed to build journey snapshot") from exc


@router.get("/life-chapters")
async def journey_life(person_id: str, force_refresh: bool = False):
    try:
        data = await renderer.get_life_chapters(person_id, force_refresh=force_refresh)
        return {"status": "ok", "data": data}
    except Exception as exc:  # pragma: no cover - passthrough to API
        raise HTTPException(status_code=500, detail="Failed to build journey snapshot") from exc
