from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from sakhi.apps.api.core.db import get_db
from sakhi.apps.api.core.llm import call_llm
from sakhi.apps.api.services.memory.recall import build_recall_context

LOGGER = logging.getLogger(__name__)


def _window_start(kind: str) -> datetime:
    now = datetime.now(timezone.utc)
    return now - timedelta(days=30 if kind == "monthly" else 7)


async def _fetch_reflections(person_id: str, kind: str) -> List[Dict[str, Any]]:
    db = await get_db()
    since = _window_start(kind)
    try:
        rows = await db.fetch(
            """
            SELECT id, theme, content, created_at
            FROM reflections
            WHERE user_id = $1
              AND created_at >= $2
            ORDER BY created_at ASC
            """,
            person_id,
            since,
        )
        return [dict(row) for row in rows]
    finally:
        await db.close()


def _reflections_to_bullets(reflections: List[Dict[str, Any]]) -> str:
    if not reflections:
        return "No reflections available."

    lines: List[str] = []
    for item in reflections:
        ts = item.get("created_at")
        ts_str = ts.strftime("%Y-%m-%d") if isinstance(ts, datetime) else ""
        theme = item.get("theme") or "general"
        text = (item.get("content") or "").strip()
        if len(text) > 180:
            text = text[:177] + "…"
        parts = [p for p in (ts_str, theme, text) if p]
        if parts:
            lines.append("- " + " | ".join(parts))
    return "\n".join(lines) if lines else "No reflections available."


async def summarize_reflections(person_id: str, kind: str = "weekly") -> Dict[str, Any]:
    kind_norm = "monthly" if kind == "monthly" else "weekly"
    reflections = await _fetch_reflections(person_id, kind_norm)
    if not reflections:
        LOGGER.info("[ReflectionSummary] No reflections for %s", person_id)
        return {"status": "no_data", "kind": kind_norm}

    bullets = _reflections_to_bullets(reflections)
    recall_context = await build_recall_context(person_id, bullets[:2000])

    system_prompt = (
        "You are Sakhi, a reflective clarity companion.\n"
        "Given the user's reflections and relevant memory context, produce a concise narrative "
        "capturing emotional themes, energy trends, intentions, and 3-4 meaningful insights for next steps. "
        "Length target: 150–230 words."
    )
    user_prompt = (
        f"Reflections ({kind_norm} window):\n{bullets}\n\n"
        f"Relevant memory context:\n{recall_context}\n\n"
        "Write the summary (no bullet lists)."
    )

    model = os.getenv("MODEL_REFLECTION_SUMMARY") or os.getenv("MODEL_CHAT") or "gpt-4o-mini"
    response = await call_llm(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        person_id=person_id,
        model=model,
    )

    if isinstance(response, dict):
        text = response.get("reply") or response.get("text") or response.get("summary") or ""
    else:
        text = str(response or "")
    summary_text = text.strip() or "Reflection summary unavailable."

    db = await get_db()
    try:
        await db.execute(
            """
            INSERT INTO meta_reflections (person_id, period, summary, insights)
            VALUES ($1, $2, $3, '{}'::jsonb)
            """,
            person_id,
            kind_norm,
            summary_text,
        )
    finally:
        await db.close()

    LOGGER.info("[ReflectionSummary] Stored %s summary for %s", kind_norm, person_id)
    return {"status": "ok", "kind": kind_norm, "summary": summary_text}


__all__ = ["summarize_reflections"]

