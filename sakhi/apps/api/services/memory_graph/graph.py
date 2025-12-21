"""
Patch U + Patch Y — Memory Graph Wiring + Persistence Helpers
-------------------------------------------------------------
Creates lightweight in-memory graphs for enrichment AND provides helpers
to persist/reinforce nodes/edges inside the relational memory graph.
"""

from __future__ import annotations

import uuid
import json
from typing import Any, Dict, List


def create_node(kind: str, label: str, data: Dict[str, Any] | None = None) -> Dict[str, Any]:
    return {
        "id": str(uuid.uuid4()),
        "kind": kind,
        "label": label,
        "data": data or {},
    }


def create_edge(src: Dict[str, Any], dst: Dict[str, Any], relation: str = "relates_to") -> Dict[str, Any]:
    return {
        "src": src["id"],
        "dst": dst["id"],
        "relation": relation,
    }


def build_graph_from_enrichment(enrichment: Dict[str, Any]) -> Dict[str, Any]:
    facets = enrichment.get("facets") or {}
    themes = enrichment.get("themes") or []
    meaning = enrichment.get("meaning") or ""

    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []

    reflection_node = create_node("reflection", meaning[:40] or "reflection", {"meaning": meaning})
    nodes.append(reflection_node)

    emotion = facets.get("emotion")
    if emotion:
        emotion_node = create_node("emotion", emotion)
        nodes.append(emotion_node)
        edges.append(create_edge(reflection_node, emotion_node, "influences"))

    for theme in themes:
        theme_node = create_node("theme", theme)
        nodes.append(theme_node)
        edges.append(create_edge(reflection_node, theme_node, "relates_to"))

    return {"nodes": nodes, "edges": edges}


def reason_about_graph(graph: Dict[str, Any]) -> Dict[str, Any]:
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])

    themes = [n for n in nodes if n.get("kind") == "theme"]
    emotions = [n for n in nodes if n.get("kind") == "emotion"]

    return {
        "dominant_theme": themes[0]["label"] if themes else None,
        "emotion": emotions[0]["label"] if emotions else None,
        "graph_size": len(nodes),
        "edge_count": len(edges),
    }


async def get_or_create_node(
    db,
    *,
    person_id: str,
    node_kind: str,
    label: str,
    data: Dict[str, Any] | None = None,
) -> str:
    row = await db.fetchrow(
        """
        SELECT id
        FROM memory_nodes
        WHERE person_id = $1
          AND label = $2
        LIMIT 1
        """,
        person_id,
        label,
    )
    if row and row.get("id"):
        return row["id"]

    new_id = str(uuid.uuid4())
    payload = json.dumps(data or {}, ensure_ascii=False)
    await db.execute(
        """
        INSERT INTO memory_nodes (id, person_id, node_kind, label, data)
        VALUES ($1, $2, $3, $4, $5::jsonb)
        """,
        new_id,
        person_id,
        _sanitize_kind(node_kind),
        label,
        payload,
    )
    return new_id


async def upsert_edge(
    db,
    *,
    person_id: str,
    from_node: str,
    to_node: str,
    relation: str,
    weight: float,
) -> str:
    row = await db.fetchrow(
        """
        SELECT id, weight
        FROM memory_edges
        WHERE person_id = $1
          AND from_node = $2
          AND to_node = $3
          AND relation = $4
        """,
        person_id,
        from_node,
        to_node,
        relation,
    )
    if row and row.get("id"):
        prev_weight = float(row.get("weight") or 0.0)
        new_weight = prev_weight * 0.7 + float(weight) * 0.3
        await db.execute(
            """
            UPDATE memory_edges
            SET weight = $2
            WHERE id = $1
            """,
            row["id"],
            new_weight,
        )
        return row["id"]

    new_id = str(uuid.uuid4())
    await db.execute(
        """
        INSERT INTO memory_edges (id, person_id, from_node, to_node, relation, weight)
        VALUES ($1, $2, $3, $4, $5, $6)
        """,
        new_id,
        person_id,
        from_node,
        to_node,
        relation,
        weight,
    )
    return new_id


__all__ = [
    "build_graph_from_enrichment",
    "reason_about_graph",
    "get_or_create_node",
    "upsert_edge",
]
VALID_KINDS = {"reflection", "thought", "plan", "insight", "event"}


def _sanitize_kind(kind: str) -> str:
    if not kind:
        return "reflection"
    core = kind.split(":", 1)[0].strip().lower()
    return core if core in VALID_KINDS else "reflection"
