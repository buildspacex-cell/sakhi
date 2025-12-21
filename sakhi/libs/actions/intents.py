from typing import Any, Dict, Optional

from sakhi.libs.schemas.db import get_async_pool


async def create_intent_from_entry(
    user_id: str,
    entry_id: Optional[str],
    title: str,
    raw: str,
    fx: Dict[str, Any],
) -> int:
    pool = await get_async_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
              INSERT INTO intents(user_id, source_entry_id, title, raw_input, intent_type, domain,
                                  timeline, target_date, status, clarity_score, context_snapshot)
              VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
              RETURNING id
            """,
            user_id,
            entry_id,
            title,
            raw,
            fx.get("intent_type"),
            fx.get("domain"),
            (fx.get("timeline") or {}).get("horizon", "none"),
            (fx.get("timeline") or {}).get("target_date"),
            "clarifying",
            float(fx.get("actionability", 0.0) or 0.0),
            {
                "emotion": fx.get("emotion"),
                "sentiment": fx.get("sentiment"),
            },
        )
    return row["id"]
