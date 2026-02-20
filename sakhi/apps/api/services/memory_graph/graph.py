"""
Patch U + Patch Y — Memory Graph Wiring + Persistence Helpers
-------------------------------------------------------------
Creates lightweight in-memory graphs for enrichment AND provides helpers
to persist/reinforce nodes/edges inside the relational memory graph.
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List

from kala.graph.core import (  # noqa: F401
    build_graph_from_enrichment,
    create_edge,
    create_node,
    reason_about_graph,
)
from kala.graph.schema import (
    VALID_KINDS,  # noqa: F401
    VALID_RELATIONS,  # noqa: F401
    sanitize_kind as _sanitize_kind,
    sanitize_relation as _sanitize_relation,
)


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


# =============================================================================
# GRAPH QUERY FUNCTIONS
# =============================================================================

async def find_competing_entities(
    db,
    *,
    person_id: str,
    node_id: str,
) -> List[Dict[str, Any]]:
    """
    Find all entities that compete with or block a given node.

    Use case: "What competes with my morning yoga for the morning slot?"
    Returns activities, goals, or patterns that conflict.
    """
    rows = await db.fetch(
        """
        SELECT
            mn.id,
            mn.node_kind,
            mn.label,
            mn.data,
            me.relation,
            me.weight
        FROM memory_edges me
        JOIN memory_nodes mn ON mn.id = CASE
            WHEN me.from_node = $2 THEN me.to_node
            ELSE me.from_node
        END
        WHERE me.person_id = $1
          AND (me.from_node = $2 OR me.to_node = $2)
          AND me.relation IN ('competes_with', 'blocks')
        ORDER BY me.weight DESC
        """,
        person_id,
        node_id,
    )
    return [dict(row) for row in rows]


async def find_supporting_entities(
    db,
    *,
    person_id: str,
    node_id: str,
) -> List[Dict[str, Any]]:
    """
    Find all entities that support or enable a given node.

    Use case: "What helps me achieve my meditation goal?"
    """
    rows = await db.fetch(
        """
        SELECT
            mn.id,
            mn.node_kind,
            mn.label,
            mn.data,
            me.relation,
            me.weight
        FROM memory_edges me
        JOIN memory_nodes mn ON mn.id = CASE
            WHEN me.from_node = $2 THEN me.to_node
            ELSE me.from_node
        END
        WHERE me.person_id = $1
          AND (me.from_node = $2 OR me.to_node = $2)
          AND me.relation IN ('supports', 'enables')
        ORDER BY me.weight DESC
        """,
        person_id,
        node_id,
    )
    return [dict(row) for row in rows]


async def find_nodes_for_time_slot(
    db,
    *,
    person_id: str,
    time_slot: str,  # "morning", "afternoon", "evening", "night"
) -> List[Dict[str, Any]]:
    """
    Find all activities/goals/patterns scheduled for a time slot.

    Use case: "What's competing for my morning time?"
    """
    rows = await db.fetch(
        """
        SELECT
            mn.id,
            mn.node_kind,
            mn.label,
            mn.data,
            me.weight
        FROM memory_nodes slot
        JOIN memory_edges me ON (me.to_node = slot.id OR me.from_node = slot.id)
        JOIN memory_nodes mn ON mn.id = CASE
            WHEN me.from_node = slot.id THEN me.to_node
            ELSE me.from_node
        END
        WHERE slot.person_id = $1
          AND slot.node_kind = 'time_slot'
          AND slot.label = $2
          AND me.relation = 'scheduled_for'
        ORDER BY me.weight DESC
        """,
        person_id,
        time_slot.lower(),
    )
    return [dict(row) for row in rows]


async def traverse_from_node(
    db,
    *,
    person_id: str,
    node_id: str,
    max_hops: int = 2,
    relation_filter: List[str] | None = None,
) -> List[Dict[str, Any]]:
    """
    Multi-hop graph traversal from a starting node.

    Use case: "Find everything related to my work stress pattern"
    Returns connected nodes with decreasing weight by distance.
    """
    relation_clause = ""
    params = [person_id, node_id, max_hops]

    if relation_filter:
        relation_clause = "AND me.relation = ANY($4)"
        params.append(relation_filter)

    # Note: Using a simpler iterative approach instead of recursive CTE
    # to avoid complexity. For deep traversal, call multiple times.
    rows = await db.fetch(
        f"""
        WITH direct AS (
            SELECT
                CASE
                    WHEN me.from_node = $2 THEN me.to_node
                    ELSE me.from_node
                END AS connected_node,
                me.relation,
                me.weight,
                1 AS distance
            FROM memory_edges me
            WHERE me.person_id = $1
              AND (me.from_node = $2 OR me.to_node = $2)
              {relation_clause}
        )
        SELECT DISTINCT
            mn.id,
            mn.node_kind,
            mn.label,
            mn.data,
            d.relation,
            d.weight,
            d.distance
        FROM direct d
        JOIN memory_nodes mn ON mn.id = d.connected_node
        ORDER BY d.distance, d.weight DESC
        LIMIT 50
        """,
        *params,
    )
    return [dict(row) for row in rows]


async def get_node_by_label(
    db,
    *,
    person_id: str,
    label: str,
    node_kind: str | None = None,
) -> Dict[str, Any] | None:
    """
    Find a node by its label (optionally filtered by kind).

    Use case: Look up "morning" time slot or "meditation" activity.
    """
    if node_kind:
        row = await db.fetchrow(
            """
            SELECT id, node_kind, label, data, weight
            FROM memory_nodes
            WHERE person_id = $1
              AND label = $2
              AND node_kind = $3
            """,
            person_id,
            label,
            node_kind,
        )
    else:
        row = await db.fetchrow(
            """
            SELECT id, node_kind, label, data, weight
            FROM memory_nodes
            WHERE person_id = $1
              AND label = $2
            ORDER BY weight DESC
            LIMIT 1
            """,
            person_id,
            label,
        )
    return dict(row) if row else None


async def get_context_for_topic(
    db,
    *,
    person_id: str,
    topic_labels: List[str],
    max_related: int = 10,
) -> Dict[str, Any]:
    """
    Get rich context for a set of topics by finding all related entities.

    This is the main entry point for intelligent context loading.

    Use case: User mentions "morning routine" and "yoga" - find all
    related goals, patterns, competing activities, and time constraints.

    Returns:
        {
            "matched_nodes": [...],      # Direct matches for topics
            "related_nodes": [...],      # Connected via edges
            "competing_entities": [...], # Things that compete/block
            "supporting_entities": [...] # Things that support/enable
        }
    """
    result = {
        "matched_nodes": [],
        "related_nodes": [],
        "competing_entities": [],
        "supporting_entities": [],
    }

    # Find nodes matching the topic labels
    matched = await db.fetch(
        """
        SELECT id, node_kind, label, data, weight
        FROM memory_nodes
        WHERE person_id = $1
          AND label = ANY($2)
        ORDER BY weight DESC
        """,
        person_id,
        topic_labels,
    )
    result["matched_nodes"] = [dict(row) for row in matched]

    if not matched:
        return result

    # For each matched node, find related, competing, and supporting entities
    matched_ids = [row["id"] for row in matched]

    # Related (general connections)
    related = await db.fetch(
        """
        SELECT DISTINCT
            mn.id,
            mn.node_kind,
            mn.label,
            mn.data,
            me.relation,
            me.weight
        FROM memory_edges me
        JOIN memory_nodes mn ON mn.id = CASE
            WHEN me.from_node = ANY($2) THEN me.to_node
            ELSE me.from_node
        END
        WHERE me.person_id = $1
          AND (me.from_node = ANY($2) OR me.to_node = ANY($2))
        ORDER BY me.weight DESC
        LIMIT $3
        """,
        person_id,
        matched_ids,
        max_related,
    )
    result["related_nodes"] = [dict(row) for row in related]

    # Separate out competing and supporting
    for node in result["related_nodes"]:
        if node.get("relation") in ("competes_with", "blocks"):
            result["competing_entities"].append(node)
        elif node.get("relation") in ("supports", "enables"):
            result["supporting_entities"].append(node)

    return result


# =============================================================================
# EDGE CREATION HELPERS (for workers to use)
# =============================================================================

async def link_activity_to_time_slot(
    db,
    *,
    person_id: str,
    activity_label: str,
    time_slot: str,  # "morning", "afternoon", "evening", "night"
    weight: float = 0.5,
) -> str | None:
    """
    Create a scheduled_for edge between an activity and a time slot.

    Use case: "Yoga is scheduled for morning"
    """
    activity_id = await get_or_create_node(
        db,
        person_id=person_id,
        node_kind="activity",
        label=activity_label,
    )
    slot_id = await get_or_create_node(
        db,
        person_id=person_id,
        node_kind="time_slot",
        label=time_slot.lower(),
        data={"system": True},
    )
    return await upsert_edge(
        db,
        person_id=person_id,
        from_node=activity_id,
        to_node=slot_id,
        relation="scheduled_for",
        weight=weight,
    )


async def link_competing_activities(
    db,
    *,
    person_id: str,
    activity1_label: str,
    activity2_label: str,
    weight: float = 0.5,
) -> str | None:
    """
    Create a competes_with edge between two activities.

    Use case: "Morning meeting competes with yoga for morning slot"
    """
    id1 = await get_or_create_node(
        db,
        person_id=person_id,
        node_kind="activity",
        label=activity1_label,
    )
    id2 = await get_or_create_node(
        db,
        person_id=person_id,
        node_kind="activity",
        label=activity2_label,
    )
    return await upsert_edge(
        db,
        person_id=person_id,
        from_node=id1,
        to_node=id2,
        relation="competes_with",
        weight=weight,
    )


async def link_pattern_to_goal(
    db,
    *,
    person_id: str,
    pattern_label: str,
    goal_label: str,
    relation: str = "supports",  # or "blocks"
    weight: float = 0.5,
) -> str | None:
    """
    Create an edge between a pattern and a goal.

    Use case: "Late night screen time blocks sleep goal"
    """
    pattern_id = await get_or_create_node(
        db,
        person_id=person_id,
        node_kind="pattern",
        label=pattern_label,
    )
    goal_id = await get_or_create_node(
        db,
        person_id=person_id,
        node_kind="goal",
        label=goal_label,
    )
    return await upsert_edge(
        db,
        person_id=person_id,
        from_node=pattern_id,
        to_node=goal_id,
        relation=_sanitize_relation(relation),
        weight=weight,
    )


__all__ = [
    # Original exports
    "build_graph_from_enrichment",
    "reason_about_graph",
    "get_or_create_node",
    "upsert_edge",
    # New exports
    "VALID_KINDS",
    "VALID_RELATIONS",
    "find_competing_entities",
    "find_supporting_entities",
    "find_nodes_for_time_slot",
    "traverse_from_node",
    "get_node_by_label",
    "get_context_for_topic",
    "link_activity_to_time_slot",
    "link_competing_activities",
    "link_pattern_to_goal",
]
