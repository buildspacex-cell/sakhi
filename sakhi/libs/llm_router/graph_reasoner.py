from __future__ import annotations

"""
Safe, stable graph summarisation. No embedding calls live here anymore.
"""
import json
from typing import Any

from sakhi.apps.api.core.llm import call_llm


async def reason_over_graph(person_id: str, question: str, db: Any):
    nodes = await db.fetch(
        "SELECT label, node_kind, data FROM memory_nodes WHERE person_id = $1",
        person_id,
    )
    edges = await db.fetch(
        "SELECT relation, weight, from_node, to_node FROM memory_edges WHERE person_id = $1",
        person_id,
    )
    context = {"nodes": nodes, "edges": edges}
    prompt = f"""
You are Sakhi's integrative intelligence.
Answer the user's question using this memory graph context:
{json.dumps(context, indent=2)}
Question: {question}
Respond reflectively, showing understanding of relationships between themes, emotions, and rhythm.
""".strip()
    return await call_llm(messages=[{"role": "user", "content": prompt}])


__all__ = ["reason_over_graph"]
