from __future__ import annotations

from typing import Any, Dict, List

from sakhi.apps.api.core.db import q as dbfetch
from sakhi.apps.api.services.memory.recall import memory_recall


async def _latest_emotion(person_id: str) -> str | None:
    rows = await dbfetch(
        "SELECT last_emotion FROM session_continuity WHERE person_id=$1",
        person_id,
    )
    if rows:
        return rows[0].get("last_emotion")
    return None


async def _active_goals(person_id: str) -> List[str]:
    rows = await dbfetch(
        """
        SELECT title FROM goals
        WHERE person_id=$1 AND status='active'
        ORDER BY updated_at DESC
        LIMIT 3
        """,
        person_id,
    )
    return [str(r.get("title")) for r in rows if r.get("title")]


async def _recent_themes(person_id: str) -> List[str]:
    rows = await dbfetch(
        """
        SELECT theme
        FROM reflections
        WHERE user_id=$1
        ORDER BY created_at DESC
        LIMIT 5
        """,
        person_id,
    )
    seen: set[str] = set()
    themes: List[str] = []
    for row in rows:
        theme = str(row.get("theme") or "").strip()
        if theme and theme not in seen:
            seen.add(theme)
            themes.append(theme)
    return themes


async def _recent_memory_nodes(person_id: str) -> List[Dict[str, Any]]:
    rows = await dbfetch(
        """
        SELECT id, node_kind, label, data
        FROM memory_nodes
        WHERE person_id=$1
        ORDER BY created_at DESC
        LIMIT 5
        """,
        person_id,
    )
    return [dict(r) for r in rows]


def _shorten(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


async def synthesize_memory_context(
    person_id: str,
    user_query: str,
    *,
    limit: int = 300,
) -> str:
    """
    Produce a concise memory context summary for system prompts.
    """

    recall = await memory_recall(person_id, user_query, limit=5)
    recent_nodes = await _recent_memory_nodes(person_id)
    goals = await _active_goals(person_id)
    emotion = await _latest_emotion(person_id) or "neutral"
    themes = await _recent_themes(person_id)

    parts: List[str] = []
    parts.append(f"User emotion={emotion}.")

    if themes:
        parts.append(f"Recent themes: {', '.join(themes)}.")

    if goals:
        parts.append(f"Active goals: {', '.join(goals)}.")

    if recall:
        top: List[str] = []
        for r in recall[:3]:
            snippet = r.get("text") or ""
            if snippet:
                top.append(_shorten(snippet, 120))
        if top:
            parts.append("Memory references: " + "; ".join(top) + ".")

    if recent_nodes:
        node_bits: List[str] = []
        for n in recent_nodes[:3]:
            label = (n.get("label") or "").strip()
            data = n.get("data") or {}
            if isinstance(data, str):
                data = {"summary": data}
            elif not isinstance(data, dict):
                data = {}
            snip = (data.get("summary") or data.get("topic") or data.get("message") or "").strip()
            merged = " ".join(filter(None, [label, snip])).strip()
            if merged:
                node_bits.append(_shorten(merged, 120))
        if node_bits:
            parts.append("Recent notes: " + "; ".join(node_bits) + ".")

    raw = " ".join(parts).strip()
    return _shorten(raw, limit)


__all__ = ["synthesize_memory_context"]
