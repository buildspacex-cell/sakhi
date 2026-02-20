"""In-memory graph construction and reasoning — no DB, no I/O."""

from __future__ import annotations

import uuid
from typing import Any


def create_node(
    kind: str,
    label: str,
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create an in-memory graph node."""
    return {
        "id": str(uuid.uuid4()),
        "kind": kind,
        "label": label,
        "data": data or {},
    }


def create_edge(
    src: dict[str, Any],
    dst: dict[str, Any],
    relation: str = "relates_to",
) -> dict[str, Any]:
    """Create an in-memory edge between two nodes."""
    return {
        "src": src["id"],
        "dst": dst["id"],
        "relation": relation,
    }


def build_graph_from_enrichment(enrichment: dict[str, Any]) -> dict[str, Any]:
    """Build an in-memory graph from an enrichment payload.

    Expects enrichment with optional keys: facets, themes, meaning.
    """
    facets = enrichment.get("facets") or {}
    themes = enrichment.get("themes") or []
    meaning = enrichment.get("meaning") or ""

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    reflection_node = create_node(
        "reflection", meaning[:40] or "reflection", {"meaning": meaning}
    )
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


def reason_about_graph(graph: dict[str, Any]) -> dict[str, Any]:
    """Extract summary insights from an in-memory graph."""
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
