from __future__ import annotations

import logging
from typing import Any, Dict, List

import numpy as np

from sakhi.apps.api.core.db import q

LOGGER = logging.getLogger(__name__)

SIM_THRESHOLD = 0.87
MERGE_THRESHOLD = 0.93
MAX_BATCH = 200


def _sim(a: List[float], b: List[float]) -> float:
    if not a or not b:
        return 0.0
    va = np.array(a, dtype=float)
    vb = np.array(b, dtype=float)
    denom = float(np.linalg.norm(va) * np.linalg.norm(vb))
    if denom == 0:
        return 0.0
    return float(np.dot(va, vb) / denom)


def _parse_vec(raw: Any) -> List[float]:
    if not raw:
        return []
    if isinstance(raw, list):
        return [float(x) for x in raw]
    if isinstance(raw, str) and raw.startswith("["):
        body = raw[1:-1].strip()
        if not body:
            return []
        try:
            return [float(val) for val in body.split(",")]
        except Exception:
            return []
    return []


async def fetch_memory_nodes(person_id: str) -> List[Dict[str, Any]]:
    rows = await q(
        """
        SELECT id, node_kind, label, data, embed_vec
        FROM memory_nodes
        WHERE person_id = $1
        ORDER BY created_at DESC
        LIMIT $2
        """,
        person_id,
        MAX_BATCH,
    )
    return [
        {
            "id": row["id"],
            "kind": row["node_kind"],
            "label": row["label"],
            "data": row["data"] or {},
            "vec": _parse_vec(row.get("embed_vec")),
        }
        for row in rows
    ]


async def merge_nodes(person_id: str, src_id: str, dst_id: str) -> None:
    LOGGER.info("[Consolidation] merging %s → %s", src_id, dst_id)
    await q(
        """
        UPDATE memory_edges
        SET from_node = $2
        WHERE person_id = $1 AND from_node = $3
        """,
        person_id,
        dst_id,
        src_id,
    )
    await q(
        """
        UPDATE memory_edges
        SET to_node = $2
        WHERE person_id = $1 AND to_node = $3
        """,
        person_id,
        dst_id,
        src_id,
    )
    await q(
        """
        UPDATE memory_nodes
        SET data = data || (SELECT data FROM memory_nodes WHERE id = $3)
        WHERE id = $2
        """,
        person_id,
        dst_id,
        src_id,
    )
    await q(
        """
        DELETE FROM memory_nodes
        WHERE id = $2 AND person_id = $1
        """,
        person_id,
        src_id,
    )


async def consolidate_memory(person_id: str) -> Dict[str, Any]:
    nodes = await fetch_memory_nodes(person_id)
    if not nodes:
        return {"merged": 0, "candidates": []}

    merged = 0
    candidates: List[Dict[str, Any]] = []

    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            a = nodes[i]
            b = nodes[j]
            sim = _sim(a["vec"], b["vec"])
            if sim < SIM_THRESHOLD:
                continue

            candidates.append(
                {
                    "a": {"id": a["id"], "label": a["label"], "kind": a["kind"]},
                    "b": {"id": b["id"], "label": b["label"], "kind": b["kind"]},
                    "similarity": sim,
                }
            )

            if sim >= MERGE_THRESHOLD:
                dst = a if len(a["label"]) >= len(b["label"]) else b
                src = b if dst is a else a
                await merge_nodes(person_id, src["id"], dst["id"])
                merged += 1

    return {"merged": merged, "candidates": candidates}


__all__ = ["consolidate_memory"]
