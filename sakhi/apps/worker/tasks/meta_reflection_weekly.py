from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from typing import Any, Dict, List

from sakhi.apps.api.core.db import get_db
from sakhi.apps.api.core.llm import call_llm
from sakhi.libs.schemas.settings import get_settings

LOGGER = logging.getLogger(__name__)


async def run_meta_reflection_weekly() -> bool:
    """
    Generate weekly meta-reflection summaries for each person in personal_model.
    Summaries are inserted into meta_reflections with period='weekly'.
    """
    settings = get_settings()
    if not settings.enable_reflective_state_writes:
        LOGGER.info("Worker disabled by safety gate: ENABLE_REFLECTIVE_STATE_WRITES=false")
        return False

    since_ts = datetime.now(timezone.utc) - timedelta(days=7)
    db = await get_db()
    try:
        rows: List[Dict[str, Any]] = await db.fetch(
            """
            SELECT p.person_id,
                   e.id AS entry_id,
                   e.user_id,
                   e.content,
                   e.raw_encrypted,
                   e.layer,
                   e.mood,
                   e.created_at
            FROM personal_model p
            LEFT JOIN journal_entries e
              ON e.user_id = p.person_id
             AND e.created_at >= $1
            ORDER BY p.person_id, e.created_at ASC
            """,
            since_ts,
        )

        if not rows:
            return False

        grouped_entries: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for row in rows:
            person_id = str(row.get("person_id") or "").strip()
            if not person_id:
                continue
            content = str(row.get("content") or "").strip()
            if not content:
                continue
            grouped_entries[person_id].append(
                {
                    "content": content,
                    "layer": row.get("layer"),
                    "mood": row.get("mood"),
                    "ts": (
                        row.get("created_at").isoformat()
                        if getattr(row.get("created_at"), "isoformat", None)
                        else row.get("created_at")
                    ),
                }
            )

        for person_id, entries in grouped_entries.items():
            if not entries:
                continue

            prompt = f"""
You are Sakhi, a gentle clarity companion.
Summarise the user's identity/values evolution this week.
Provide:
- a concise narrative (~120 words)
- key signals you noticed (list)
- two reflective follow-up questions

Entries JSON:
{json.dumps(entries, ensure_ascii=False)}
""".strip()

            try:
                reply = await call_llm(
                    messages=[{"role": "user", "content": prompt}],
                    person_id=str(person_id),
                )
            except Exception as exc:  # pragma: no cover - defensive logging
                LOGGER.error("[Meta Reflection] LLM failed for %s: %s", person_id, exc)
                continue

            summary_text = reply if isinstance(reply, str) else json.dumps(reply)
            summary_text = summary_text[:2000]

            await db.execute(
                """
                INSERT INTO meta_reflections (person_id, period, summary, insights, created_at)
                VALUES ($1, 'weekly', $2, $3::jsonb, NOW())
                """,
                person_id,
                summary_text,
                json.dumps({"entries": entries}, ensure_ascii=False),
            )
            LOGGER.info("[Meta Reflection] Weekly summary generated for %s", person_id)

        return True
    finally:
        await db.close()


__all__ = ["run_meta_reflection_weekly"]
