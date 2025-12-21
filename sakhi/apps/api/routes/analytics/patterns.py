from __future__ import annotations

import math

from fastapi import APIRouter

from sakhi.apps.api.core.db import q as db_fetch

router = APIRouter()


def _norm(vector):
    if not isinstance(vector, list):
        return 0.0
    total = 0.0
    for value in vector:
        try:
            num = float(value)
        except (TypeError, ValueError):
            num = 0.0
        total += num * num
    return math.sqrt(total)


@router.get("/patterns")
async def get_patterns():
    rows = await db_fetch(
        """
        SELECT pattern_type,
               support_count,
               last_updated,
               mean_vector,
               std_dev_vector
        FROM collective_patterns
        ORDER BY support_count DESC
        LIMIT 20
        """
    )
    enriched = []
    for row in rows:
        stats = {
            "mean_norm": _norm(row.get("mean_vector")),
            "std_norm": _norm(row.get("std_dev_vector")),
        }
        enriched.append(
            {
                "pattern_type": row.get("pattern_type"),
                "support_count": row.get("support_count"),
                "last_updated": row.get("last_updated"),
                "stats": stats,
            }
        )
    return enriched


__all__ = ["router"]
