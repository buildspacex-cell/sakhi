from __future__ import annotations

from fastapi import APIRouter, Query

from sakhi.apps.api.core.db import q as db_fetch

router = APIRouter(prefix="/memory-graph", tags=["Memory Graph"])


@router.get("/overview")
async def get_graph_overview(person_id: str = Query(...)):
    nodes = await db_fetch(
        "SELECT id, node_kind, label FROM memory_nodes WHERE person_id = $1",
        person_id,
    )
    edges = await db_fetch(
        "SELECT from_node, to_node, relation, weight FROM memory_edges WHERE person_id = $1",
        person_id,
    )
    return {"nodes": nodes, "edges": edges}


__all__ = ["router"]
