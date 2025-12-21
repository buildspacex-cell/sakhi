from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Tuple

from sakhi.apps.api.core.db import q


def _safe_get_layers(long_term: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(long_term, dict):
        return {}
    return long_term.get("layers") or {}


async def _fetch_context(person_id: str) -> Dict[str, Any]:
    row = await q(
        "SELECT long_term FROM personal_model WHERE person_id = $1",
        person_id,
        one=True,
    )
    long_term = row.get("long_term") if row else {}
    layers = _safe_get_layers(long_term)

    # recent topics from memory_short_term
    recent_rows = await q(
        """
        SELECT text
        FROM memory_short_term
        WHERE person_id = $1
        ORDER BY updated_at DESC
        LIMIT 20
        """,
        person_id,
    )
    topics = []
    for r in recent_rows:
        text = (r.get("text") or "").lower()
        if not text:
            continue
        for token in ("guitar", "music", "health", "work", "relationship", "plan", "discipline", "balance"):
            if token in text:
                topics.append(token)
    return {"long_term": long_term, "layers": layers, "topics": topics}


def _add_edge(edges: Dict[str, List[Tuple[str, str]]], kind: str, a: str, b: str):
    if not a or not b:
        return
    edges[kind].append((a, b))


def _coherence_edges(nodes: Dict[str, Any], topics: List[str], load: float) -> List[Tuple[str, str]]:
    edges: List[Tuple[str, str]] = []
    values = nodes.get("values") or []
    themes = nodes.get("life_themes") or []
    priorities = nodes.get("priority_topics") or []
    goals = nodes.get("goals") or []
    mind = nodes.get("mind_state")
    emotion = nodes.get("emotion_state")

    for v in values:
        for g in goals:
            g_str = g if isinstance(g, str) else str(g)
            if any(k in g_str.lower() for k in v.split()):
                edges.append((v, g_str))
            if "guitar" in g_str:
                edges.append((v, "guitar"))

    for theme in themes:
        for p in priorities:
            if theme.split("/")[0] in p:
                edges.append((theme, p))
        for topic in topics:
            if theme.split("/")[0] in topic:
                edges.append((theme, topic))
        if "guitar" in theme:
            edges.append((theme, "guitar"))

    if mind and any(word in mind for word in ("focus", "planning", "clear")):
        for v in values:
            edges.append((mind, v))

    if emotion and "positive" in str(emotion):
        for v in values:
            edges.append((emotion, v))

    return edges


def _conflict_edges(nodes: Dict[str, Any], load: float) -> List[Tuple[str, str]]:
    edges: List[Tuple[str, str]] = []
    values = nodes.get("values") or []
    mind = nodes.get("mind_state") or ""
    emotion = nodes.get("emotion_state") or ""
    priorities = nodes.get("priority_topics") or []

    if load and load > 0.7:
        for v in values:
            edges.append((v, "overwhelm"))
    if "uncertain" in mind or "overloaded" in mind:
        for v in values:
            edges.append((v, "confusion"))
    if "negative" in emotion:
        for v in values:
            edges.append((v, "negative_emotion"))
    if priorities and "discipline" in " ".join(values) and load > 0.6:
        edges.append(("discipline", "overwhelm"))
    return edges


def _reinforcement_edges(nodes: Dict[str, Any], topics: List[str]) -> List[Tuple[str, str]]:
    edges: List[Tuple[str, str]] = []
    values = nodes.get("values") or []
    anchors = nodes.get("identity_anchors") or []
    themes = nodes.get("life_themes") or []
    priorities = nodes.get("priority_topics") or []
    emotion = nodes.get("emotion_state") or ""

    for v in values:
        for a in anchors:
            if v.split()[0] in a:
                edges.append((v, a))
    for t in themes:
        for p in priorities:
            if t.split("/")[0] in p:
                edges.append((t, p))
        for topic in topics:
            if t.split("/")[0] in topic:
                edges.append((t, topic))
    if emotion and "positive" in emotion and priorities:
        edges.append(("positive_emotion", priorities[0]))
    for t in themes:
        if "music/guitar" in t:
            edges.append((t, "creativity"))
            for p in priorities:
                if "guitar" in p:
                    edges.append((t, p))
        if "creativity" in values:
            for p in priorities:
                edges.append(("creativity", p))
    return edges


async def build(person_id: str) -> Dict[str, Any]:
    ctx = await _fetch_context(person_id)
    layers = ctx.get("layers") or {}
    topics = ctx.get("topics") or []

    soul = layers.get("soul") or {}
    mind = layers.get("mind") or {}
    emotion = layers.get("emotion") or {}
    goals = layers.get("goals") or {}

    metrics_soul = soul.get("metrics") or {}
    metrics_mind = mind.get("metrics") or {}

    nodes = {
        "values": metrics_soul.get("values") or [],
        "life_themes": metrics_soul.get("life_themes") or [],
        "identity_anchors": metrics_soul.get("identity_anchors") or [],
        "priority_topics": metrics_mind.get("priority_topics") or [],
        "goals": goals.get("summary") or goals.get("metrics") or [],
        "emotion_state": emotion.get("summary"),
        "mind_state": mind.get("summary"),
    }

    load = metrics_mind.get("cognitive_load") or 0.0

    edges = {
        "coherence": _coherence_edges(nodes, topics, load),
        "conflicts": _conflict_edges(nodes, load),
        "reinforcements": _reinforcement_edges(nodes, topics),
    }

    return {
        "nodes": nodes,
        "edges": edges,
        "updated_at": dt.datetime.utcnow().isoformat(),
    }


__all__ = ["build"]
