from __future__ import annotations

import uuid
from typing import Any, Dict, List

from fastapi import APIRouter, Depends

from sakhi.apps.api.core.db import get_db, DBSession

router = APIRouter(prefix="/adjustments", tags=["adjustments"])


@router.get("/{person_id}")
async def get_adjustments(person_id: uuid.UUID, db: DBSession = Depends(get_db)) -> List[Dict[str, Any]]:
    rows = await db.fetch(
        """
        SELECT pattern_type,
               learning_rate,
               applied_at,
               array_length(delta, 1) AS dimensions
        FROM model_adjustments
        WHERE person_id = $1
        ORDER BY applied_at DESC
        LIMIT 20
        """,
        str(person_id),
    )
    await db.close()
    return rows


__all__ = ["router"]
