from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Sequence

from sakhi.apps.api.core.db import exec as dbexec
from sakhi.apps.api.core.db import q, q_row
from sakhi.libs.embeddings import embed_text, to_pgvector

LOGGER = logging.getLogger(__name__)


# -------------------------------------------------------
# Helpers
# -------------------------------------------------------

def _parse_vec(raw: Any) -> List[float]:
    if not raw:
        return []
    if isinstance(raw, list):
        return [float(x) for x in raw]
    if isinstance(raw, str) and raw.startswith("[") and raw.endswith("]"):
        body = raw[1:-1].strip()
        pieces = [piece.strip() for piece in body.split(",") if piece.strip()]
        try:
            return [float(piece) for piece in pieces]
        except Exception:
            return []
    return []


async def _clean_vector(vec: Sequence[float]) -> List[float]:
    """
    Ensure vectors are floats and exactly 1536 elements.
    """
    try:
        arr = [float(v) for v in vec]
    except Exception:
        return [0.0] * 1536

    if len(arr) == 1536:
        return arr
    if len(arr) > 1536:
        return arr[:1536]
    pad_len = 1536 - len(arr)
    return arr + [0.0] * pad_len


# -------------------------------------------------------
# Main integrity check
# -------------------------------------------------------

async def run_memory_integrity(person_id: str, *, fix_missing_embeddings: bool = False) -> Dict[str, Any]:
    """
    Validate memory graph + embeddings for a person.
    The function performs soft fixes (vector repair, embedding regeneration)
    and returns a structured report.
    """

    report: Dict[str, Any] = {
        "nodes_checked": 0,
        "edges_checked": 0,
        "fixed_vectors": 0,
        "invalid_edges": 0,
        "duplicate_nodes": 0,
        "dangling_nodes": 0,
        "journal_embedding_mismatches": 0,
        "warnings": [],
    }

    nodes = await q(
        """
        SELECT id, node_kind, label, embed_vec
        FROM memory_nodes
        WHERE person_id = $1
        """,
        person_id,
    )

    seen = set()
    for row in nodes:
        report["nodes_checked"] += 1
        nid = row["id"]
        label = (row.get("label") or "").strip()
        key = (row.get("node_kind"), label.lower())

        if key in seen:
            report["duplicate_nodes"] += 1
        else:
            seen.add(key)

        raw_vec = row.get("embed_vec")
        vec = _parse_vec(raw_vec)
        clean = await _clean_vector(vec)

        if clean != vec:
            report["fixed_vectors"] += 1
            literal = "[" + ",".join(f"{val:.6f}" for val in clean) + "]"
            await dbexec(
                """
                UPDATE memory_nodes
                SET embed_vec = $2
                WHERE id = $1
                """,
                nid,
                literal,
            )

    edges = await q(
        """
        SELECT id, from_node, to_node
        FROM memory_edges
        WHERE person_id = $1
        """,
        person_id,
    )

    node_ids = {row["id"] for row in nodes}
    linked_ids = set()

    for row in edges:
        report["edges_checked"] += 1
        if row["from_node"] not in node_ids or row["to_node"] not in node_ids:
            report["invalid_edges"] += 1
            report["warnings"].append(
                f"Invalid edge {row['id']}: missing from_node/to_node"
            )
        linked_ids.add(row["from_node"])
        linked_ids.add(row["to_node"])

    missing_emb = await q(
        """
        SELECT je.id
        FROM journal_entries je
        LEFT JOIN journal_embeddings emb ON emb.entry_id = je.id
        WHERE je.user_id = $1
          AND emb.entry_id IS NULL
        """,
        person_id,
    )

    report["journal_embedding_mismatches"] = len(missing_emb)
    if missing_emb and not fix_missing_embeddings:
        report["warnings"].append(
            f"{len(missing_emb)} journal entries missing embeddings (run backfill or set fix_missing_embeddings=true)."
        )

    if fix_missing_embeddings:
        for row in missing_emb:
            jid = row["id"]
            row2 = await q_row(
                "SELECT content FROM journal_entries WHERE id = $1",
                jid,
            )
            text = (row2 or {}).get("content") or ""
            vec = await embed_text(text)
            if isinstance(vec, list) and vec and isinstance(vec[0], list):
                vec = vec[0]
            if not isinstance(vec, list):
                vec = []
            cleaned = await _clean_vector(vec)
            literal = to_pgvector(cleaned, length=1536)

            await dbexec(
                """
                INSERT INTO journal_embeddings (entry_id, embedding_vec)
                VALUES ($1, $2)
                ON CONFLICT (entry_id) DO UPDATE
                  SET embedding_vec = EXCLUDED.embedding_vec
                """,
                jid,
                literal,
            )

    for nid in node_ids:
        if nid not in linked_ids:
            report["dangling_nodes"] += 1

    LOGGER.info("[MemoryIntegrity] report=%s", json.dumps(report))
    return report


__all__ = ["run_memory_integrity"]
