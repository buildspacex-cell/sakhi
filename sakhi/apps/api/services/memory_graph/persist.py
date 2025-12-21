"""
Patch V — Persistence Layer
---------------------------
Persists enrichment payloads into journal_inference (separate from raw evidence).
All operations swallow DB errors to avoid disrupting the request flow.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from sakhi.apps.api.core.db import get_db

LOGGER = logging.getLogger(__name__)


async def persist_enrichment(entry_id: str | None, enrichment: Dict[str, Any]) -> None:
    """
    Persist enrichment data as replaceable inferences tied to a single entry.
    Nothing is written back to journal_entries (raw evidence).
    """

    if not entry_id:
        return

    payload = {
        "facets": enrichment.get("facets") or {},
        "themes": enrichment.get("themes") or [],
        "meaning": enrichment.get("meaning") or "",
    }

    db = await get_db()
    try:
        await db.execute(
            """
            INSERT INTO journal_inference (entry_id, container, payload, inference_type, source)
            VALUES ($1, 'context', $2::jsonb, 'interpretive', 'persist_enrichment')
            """,
            entry_id,
            payload,
        )
    except Exception as exc:  # pragma: no cover - best-effort persistence
        LOGGER.error("[Patch V] Failed to persist enrichment for %s: %s", entry_id, exc)
    finally:
        await db.close()


async def persist_memory_graph(person_id: str, graph: Dict[str, Any]) -> None:
    """
    Persist memory graph nodes/edges into memory_nodes + memory_edges tables.
    """

    if not person_id:
        LOGGER.warning("[Patch V] Cannot persist memory graph without person_id")
        return

    nodes = graph.get("nodes") or []
    edges = graph.get("edges") or []

    db = await get_db()
    try:
        for node in nodes:
            try:
                await db.execute(
                    """
                    INSERT INTO memory_nodes (id, person_id, node_kind, label, data)
                    VALUES ($1, $2, $3, $4, $5::jsonb)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    node["id"],
                    person_id,
                    node.get("kind"),
                    node.get("label"),
                    node.get("data") or {},
                )
            except Exception as exc:  # pragma: no cover - best-effort persistence
                LOGGER.error("[Patch V] Failed to insert node %s: %s", node.get("id"), exc)

        for edge in edges:
            try:
                await db.execute(
                    """
                    INSERT INTO memory_edges (person_id, from_node, to_node, relation)
                    VALUES ($1, $2, $3, $4)
                    """,
                    person_id,
                    edge.get("src"),
                    edge.get("dst"),
                    edge.get("relation"),
                )
            except Exception as exc:  # pragma: no cover
                LOGGER.error(
                    "[Patch V] Failed to insert edge %s→%s: %s",
                    edge.get("src"),
                    edge.get("dst"),
                    exc,
                )
    finally:
        await db.close()


__all__ = ["persist_enrichment", "persist_memory_graph"]
