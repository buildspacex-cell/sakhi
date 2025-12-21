from __future__ import annotations

import uuid
from typing import Any, Dict, List

from sakhi.apps.api.core.db import exec as dbexec


async def _add_memory_node(person_id: str, kind: str, label: str, data: Dict[str, Any]) -> str:
    node_id = str(uuid.uuid4())
    await dbexec(
        """
        INSERT INTO memory_nodes (id, person_id, node_kind, label, data)
        VALUES ($1, $2, $3, $4, $5::jsonb)
        """,
        node_id,
        person_id,
        kind,
        label,
        data,
    )
    return node_id


async def _add_memory_edge(person_id: str, src: str, dst: str, relation: str) -> None:
    await dbexec(
        """
        INSERT INTO memory_edges (person_id, from_node, to_node, relation, weight)
        VALUES ($1, $2, $3, $4, 0.5)
        """,
        person_id,
        src,
        dst,
        relation,
    )


def _coerce_label(item: Any, fallback: str) -> str:
    if isinstance(item, str):
        return item[:80] or fallback
    if isinstance(item, dict):
        for key in ("summary", "topic", "text", "label"):
            if key in item and item[key]:
                return str(item[key])[:80]
    return fallback


def _coerce_data(item: Any) -> Dict[str, Any]:
    if isinstance(item, dict):
        return item
    if isinstance(item, str):
        return {"text": item}
    try:
        return dict(item)  # type: ignore[arg-type]
    except Exception:
        return {"value": str(item)}


async def ingest_reasoning_to_memory(
    person_id: str,
    reasoning: Dict[str, Any],
    *,
    source_turn_id: str | None = None,
) -> Dict[str, List[str]]:
    """
    Convert reasoning output into memory nodes + edges.
    Safe on missing fields; best-effort inserts.
    """

    results = {
        "insight_nodes": [],
        "opportunity_nodes": [],
        "contradiction_nodes": [],
        "open_loop_nodes": [],
    }

    # Insights
    for item in reasoning.get("insights") or []:
        data = _coerce_data(item)
        label = _coerce_label(item, "insight")
        node_id = await _add_memory_node(person_id, "insight", label, data)
        results["insight_nodes"].append(node_id)
        if source_turn_id:
            await _add_memory_edge(person_id, src=node_id, dst=source_turn_id, relation="reflects")

    # Opportunities
    for item in reasoning.get("opportunities") or []:
        data = _coerce_data(item)
        label = _coerce_label(item, "opportunity")
        node_id = await _add_memory_node(person_id, "opportunity", label, data)
        results["opportunity_nodes"].append(node_id)
        if source_turn_id:
            await _add_memory_edge(person_id, src=node_id, dst=source_turn_id, relation="influences")

    # Contradictions
    for item in reasoning.get("contradictions") or []:
        data = _coerce_data(item)
        label = _coerce_label(item, "contradiction")
        node_id = await _add_memory_node(person_id, "contradiction", label, data)
        results["contradiction_nodes"].append(node_id)
        if source_turn_id:
            await _add_memory_edge(person_id, src=node_id, dst=source_turn_id, relation="contradicts")

    # Open loops
    for item in reasoning.get("open_loops") or []:
        data = _coerce_data(item)
        label = _coerce_label(item, "open_loop")
        node_id = await _add_memory_node(person_id, "open_loop", label, data)
        results["open_loop_nodes"].append(node_id)
        if source_turn_id:
            await _add_memory_edge(person_id, src=node_id, dst=source_turn_id, relation="extends")

    return results


__all__ = ["ingest_reasoning_to_memory"]
