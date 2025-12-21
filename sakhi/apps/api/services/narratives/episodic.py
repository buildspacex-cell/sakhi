from __future__ import annotations

import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from sakhi.apps.api.core.db import get_db
from sakhi.apps.api.core.llm import call_llm
from sakhi.libs.llm_router.context_builder import build_meta_context

LOGGER = logging.getLogger(__name__)


def _window_bounds(kind: str) -> tuple[datetime, str]:
    now = datetime.now(timezone.utc)
    kind_norm = "weekly" if kind not in {"weekly", "monthly"} else kind
    if kind_norm == "weekly":
        start = now - timedelta(days=7)
    else:
        start = now - timedelta(days=30)
    return start, kind_norm


async def _fetch_episodes(person_id: str, kind: str) -> List[Dict[str, Any]]:
    db = await get_db()
    start_ts, _ = _window_bounds(kind)
    try:
        rows = await db.fetch(
            """
            SELECT id,
                   ts,
                   layer,
                   text,
                   tags,
                   mood,
                   mood_score,
                   salience,
                   vividness,
                   karmic_weight
            FROM episodes
            WHERE person_id = $1
              AND ts >= $2
            ORDER BY ts ASC
            """,
            person_id,
            start_ts,
        )
        return [dict(row) for row in rows]
    finally:
        await db.close()


def _episodes_to_bullets(episodes: List[Dict[str, Any]]) -> str:
    if not episodes:
        return "No explicit episodic records for this window."

    lines: List[str] = []
    for ep in episodes:
        ts = ep.get("ts")
        ts_str = ""
        if isinstance(ts, datetime):
            ts_str = ts.astimezone(timezone.utc).strftime("%Y-%m-%d")
        layer = ep.get("layer") or "general"
        mood = ep.get("mood") or ""
        text = (ep.get("text") or "").strip()
        if len(text) > 160:
            text = text[:157] + "…"
        parts = [p for p in (ts_str, layer, mood, text) if p]
        if not parts:
            continue
        lines.append("- " + " | ".join(parts))
    return "\n".join(lines) if lines else "No explicit episodic records for this window."


async def generate_episodic_narrative(person_id: str, kind: str = "weekly") -> Dict[str, Any]:
    start_ts, kind_norm = _window_bounds(kind)
    episodes = await _fetch_episodes(person_id, kind_norm)

    if not episodes:
        LOGGER.info("[Narrative] No episodes found for %s (%s)", person_id, kind_norm)
        return {"status": "no_episodes", "kind": kind_norm}

    bullets = _episodes_to_bullets(episodes)
    meta_context = await build_meta_context(person_id)

    system_prompt = (
        "You are Sakhi, a clarity and rhythm companion.\n"
        "Given episodic slices of the recent period, weave a short empathetic narrative "
        "capturing emotional rhythm and 2-3 anchors for the next period. 180–260 words."
    )
    user_prompt = (
        f"Meta context:\n{meta_context}\n\n"
        f"Episodic window: {kind_norm} since {start_ts.date().isoformat()}\n\n"
        f"Episodes:\n{bullets}\n\n"
        "Write one or two paragraphs, no bullet lists, speaking directly to the person."
    )

    LOGGER.info("[Narrative] Generating %s narrative for %s", kind_norm, person_id)
    response = await call_llm(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        person_id=person_id,
        model=os.getenv("MODEL_NARRATIVE", os.getenv("MODEL_CHAT", "gpt-4o-mini")),
    )

    if isinstance(response, dict):
        text = response.get("reply") or response.get("text") or response.get("summary") or ""
    else:
        text = str(response or "")
    summary_text = text.strip() or "Narrative not available."

    signals: Dict[str, Any] = {
        "episode_count": len(episodes),
        "kind": kind_norm,
    }

    db = await get_db()
    try:
        await db.execute(
            """
            INSERT INTO narratives (person_id, kind, summary, signals)
            VALUES ($1, $2, $3, $4::jsonb)
            """,
            person_id,
            kind_norm,
            summary_text,
            signals,
        )
    finally:
        await db.close()

    LOGGER.info("[Narrative] Stored %s narrative for %s", kind_norm, person_id)
    return {
        "status": "ok",
        "kind": kind_norm,
        "summary": summary_text,
        "signals": signals,
    }


__all__ = ["generate_episodic_narrative"]
