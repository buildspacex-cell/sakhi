from fastapi import APIRouter, HTTPException

from sakhi.apps.logic.insight import insight_engine

router = APIRouter(prefix="/insight", tags=["insight"])


@router.get("/generate")
async def generate_insight(person_id: str, mode: str = "today"):
    try:
        bundle = await insight_engine.generate_insights(person_id, mode=mode)
        return {"status": "ok", "data": bundle}
    except Exception as exc:  # pragma: no cover - passthrough
        raise HTTPException(status_code=500, detail="Failed to generate insights") from exc


@router.get("/summary")
async def insight_summary(person_id: str, mode: str = "today"):
    try:
        data = await insight_engine.summarize_insights(person_id, mode=mode)
        return {"status": "ok", "data": data}
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail="Failed to summarize insights") from exc
