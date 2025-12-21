from __future__ import annotations

from typing import Any, Dict, List

from sakhi.apps.api.core.db import get_db
from sakhi.apps.api.services.memory_graph.graph import get_or_create_node, upsert_edge


async def reinforce_recall_graph(person_id: str, query: str, recalled_items: List[Dict[str, Any]]) -> None:
    """
    Patch Y: Strengthen the memory graph using recall results.
    """

    if not recalled_items:
        return

    db = await get_db()
    try:
        query_node_id = await get_or_create_node(
            db,
            person_id=person_id,
            node_kind="reflection",
            label=query[:80],
            data={"query": query},
        )

        for item in recalled_items:
            src_node_id = await get_or_create_node(
                db,
                person_id=person_id,
                node_kind=item.get("type") or "memory",
                label=(item.get("text") or "")[:80],
                data={"raw_text": item.get("text")},
            )

            weight = float(item.get("score") or 0.2)
            weight = max(0.05, min(weight, 1.0))

            await upsert_edge(
                db,
                person_id=person_id,
                from_node=src_node_id,
                to_node=query_node_id,
                relation="supports",
                weight=weight,
            )
    finally:
        await db.close()


__all__ = ["reinforce_recall_graph"]
