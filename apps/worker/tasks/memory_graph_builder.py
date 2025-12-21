from __future__ import annotations

import json
from typing import Any, Dict, List

from sakhi.apps.api.core.llm import call_llm
from sakhi.apps.worker.utils.db import db_find, db_insert


async def run_memory_graph_builder(person_id: str) -> None:
    reflections = db_find("reflections", {"user_id": person_id})[:10]
    themes = db_find("journal_themes", {"user_id": person_id})[:10]
    rhythm = db_find("rhythm_insights", {"person_id": person_id})[:5]
    tones = db_find("emotional_tones", {"person_id": person_id})[:10]

    prompt = f"""
Build or update a holistic user memory graph.
Each node = concept (theme, emotion, rhythm, reflection)
Each edge = relationship (influences, correlates, supports, conflicts)
DATA:
THEMES: {themes}
RHYTHM: {rhythm}
REFLECTIONS: {reflections}
TONES: {tones}

Output JSON:
{{
  "nodes": [{{"kind":"theme","label":"career","data":{{}}}}],
  "edges": [{{"from":"career","to":"finance","relation":"depends","weight":0.8}}]
}}
""".strip()

    response = await call_llm(messages=[{"role": "user", "content": prompt}])
    payload = response.get("message") if isinstance(response, dict) else response
    try:
        graph = json.loads(payload or "{}")
    except json.JSONDecodeError:
        return

    label_to_id: Dict[str, Any] = {}
    for node in graph.get("nodes", []):
        inserted = db_insert(
            "memory_nodes",
            {
                "person_id": person_id,
                "node_kind": node.get("kind"),
                "label": node.get("label"),
                "data": node.get("data", {}),
            },
        )
        label_to_id[node.get("label")] = inserted

    for edge in graph.get("edges", []):
        from_id = label_to_id.get(edge.get("from"))
        to_id = label_to_id.get(edge.get("to"))
        if not from_id or not to_id:
            continue
        db_insert(
            "memory_edges",
            {
                "person_id": person_id,
                "from_node": from_id,
                "to_node": to_id,
                "relation": edge.get("relation"),
                "weight": edge.get("weight", 0.5),
            },
        )


__all__ = ["run_memory_graph_builder"]
