from __future__ import annotations

from fastapi import APIRouter

from .summary import router as summary_router
from .timeseries import router as timeseries_router
from .themes import router as themes_router
from .patterns import router as patterns_router
from .breath import router as breath_router

router = APIRouter(prefix="/analytics", tags=["analytics"])
router.include_router(summary_router)
router.include_router(timeseries_router)
router.include_router(themes_router)
router.include_router(patterns_router)
router.include_router(breath_router)

__all__ = ["router"]
