"""
Memory Graph Wiring — Worker Integration Helpers

Provides high-level functions for workers to create nodes and edges
in the memory graph when entities are detected.

Workers call these functions to:
1. Create nodes for patterns, themes, activities, goals, values
2. Create edges showing relationships (supports, blocks, competes_with)
3. Link activities to time slots
4. Track competing entities

The memory graph enables intelligent context loading by tracking
cross-entity relationships that might be orthogonal but related
(e.g., two activities competing for the same morning slot).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from sakhi.apps.api.core.db import get_db
from sakhi.apps.api.services.memory_graph.graph import (
    get_or_create_node,
    upsert_edge,
    VALID_KINDS,
    VALID_RELATIONS,
)

LOGGER = logging.getLogger(__name__)


# =============================================================================
# PATTERN WIRING (from crystallization/episodic workers)
# =============================================================================

async def wire_pattern_to_graph(
    person_id: str,
    pattern_type: str,
    pattern_value: str,
    confidence: float = 0.5,
    evidence_snippet: str = "",
) -> Optional[str]:
    """
    Create a pattern node in the memory graph.

    Called by: episodic_consolidation_v21, pattern_crystallization_worker

    Pattern types from Sakhi:
    - core_value → value node
    - shadow → pattern node with negative polarity
    - light → pattern node with positive polarity
    - theme → theme node
    """
    db = await get_db()
    try:
        # Map pattern_type to node_kind
        kind_mapping = {
            "core_value": "value",
            "shadow": "pattern",
            "light": "pattern",
            "theme": "theme",
            "concern": "pattern",
            "goal": "goal",
        }
        node_kind = kind_mapping.get(pattern_type, "pattern")

        # Create node with metadata
        data = {
            "pattern_type": pattern_type,
            "polarity": "negative" if pattern_type == "shadow" else "positive" if pattern_type == "light" else "neutral",
            "evidence_snippet": evidence_snippet[:200] if evidence_snippet else "",
        }

        node_id = await get_or_create_node(
            db,
            person_id=person_id,
            node_kind=node_kind,
            label=pattern_value.lower().strip()[:100],
            data=data,
        )

        LOGGER.debug(
            "[MemoryGraphWiring] created pattern node",
            extra={
                "person_id": person_id,
                "pattern_type": pattern_type,
                "node_kind": node_kind,
                "node_id": node_id,
            },
        )
        return node_id

    except Exception as exc:
        LOGGER.warning(
            "[MemoryGraphWiring] failed to create pattern node: %s",
            exc,
            extra={"person_id": person_id, "pattern_type": pattern_type},
        )
        return None
    finally:
        await db.close()


async def wire_related_patterns(
    person_id: str,
    pattern_labels: List[str],
    relation: str = "relates_to",
    weight: float = 0.5,
) -> int:
    """
    Create edges between related patterns/themes.

    Called by: episodic_consolidation when multiple themes detected in same episode

    Creates edges between all pairs of patterns.
    Returns count of edges created.
    """
    if len(pattern_labels) < 2:
        return 0

    db = await get_db()
    edges_created = 0

    try:
        # Get or create nodes for all patterns
        node_ids = []
        for label in pattern_labels[:5]:  # Limit to 5 to avoid explosion
            node_id = await get_or_create_node(
                db,
                person_id=person_id,
                node_kind="pattern",
                label=label.lower().strip()[:100],
            )
            node_ids.append(node_id)

        # Create edges between pairs
        for i, from_id in enumerate(node_ids):
            for to_id in node_ids[i + 1:]:
                await upsert_edge(
                    db,
                    person_id=person_id,
                    from_node=from_id,
                    to_node=to_id,
                    relation=relation if relation in VALID_RELATIONS else "relates_to",
                    weight=weight,
                )
                edges_created += 1

        return edges_created

    except Exception as exc:
        LOGGER.warning(
            "[MemoryGraphWiring] failed to create pattern edges: %s",
            exc,
            extra={"person_id": person_id},
        )
        return edges_created
    finally:
        await db.close()


# =============================================================================
# ACTIVITY & TIME SLOT WIRING
# =============================================================================

async def wire_activity_to_time_slot(
    person_id: str,
    activity_name: str,
    time_slot: str,  # morning, afternoon, evening, night
    weight: float = 0.5,
) -> Optional[str]:
    """
    Create an activity node and link it to a time slot.

    Called by: rhythm analysis workers, intent extraction

    This enables:
    - "What's scheduled for morning?"
    - "What competes for this time slot?"
    """
    db = await get_db()
    try:
        # Create activity node
        activity_id = await get_or_create_node(
            db,
            person_id=person_id,
            node_kind="activity",
            label=activity_name.lower().strip()[:100],
        )

        # Ensure time slot node exists
        time_slot_label = time_slot.lower().strip()
        if time_slot_label not in ("morning", "afternoon", "evening", "night"):
            time_slot_label = "morning"  # Default

        slot_id = await get_or_create_node(
            db,
            person_id=person_id,
            node_kind="time_slot",
            label=time_slot_label,
            data={"system": True},
        )

        # Create scheduled_for edge
        edge_id = await upsert_edge(
            db,
            person_id=person_id,
            from_node=activity_id,
            to_node=slot_id,
            relation="scheduled_for",
            weight=weight,
        )

        LOGGER.debug(
            "[MemoryGraphWiring] linked activity to time slot",
            extra={
                "person_id": person_id,
                "activity": activity_name,
                "time_slot": time_slot_label,
            },
        )
        return edge_id

    except Exception as exc:
        LOGGER.warning(
            "[MemoryGraphWiring] failed to link activity to time slot: %s",
            exc,
        )
        return None
    finally:
        await db.close()


async def wire_competing_activities(
    person_id: str,
    activity1: str,
    activity2: str,
    shared_time_slot: str = "",
    weight: float = 0.5,
) -> Optional[str]:
    """
    Create a competes_with edge between two activities.

    Called by: rhythm analysis when two activities scheduled for same slot

    This enables:
    - "Morning meeting competes with yoga for morning slot"
    - Surfacing conflicts during context loading
    """
    db = await get_db()
    try:
        # Create both activity nodes
        id1 = await get_or_create_node(
            db,
            person_id=person_id,
            node_kind="activity",
            label=activity1.lower().strip()[:100],
        )
        id2 = await get_or_create_node(
            db,
            person_id=person_id,
            node_kind="activity",
            label=activity2.lower().strip()[:100],
        )

        # Create competes_with edge
        evidence = {"shared_time_slot": shared_time_slot} if shared_time_slot else {}
        edge_id = await upsert_edge(
            db,
            person_id=person_id,
            from_node=id1,
            to_node=id2,
            relation="competes_with",
            weight=weight,
        )

        LOGGER.debug(
            "[MemoryGraphWiring] created competition edge",
            extra={
                "person_id": person_id,
                "activity1": activity1,
                "activity2": activity2,
                "time_slot": shared_time_slot,
            },
        )
        return edge_id

    except Exception as exc:
        LOGGER.warning(
            "[MemoryGraphWiring] failed to create competition edge: %s",
            exc,
        )
        return None
    finally:
        await db.close()


# =============================================================================
# GOAL WIRING (from intent extraction)
# =============================================================================

async def wire_goal_to_graph(
    person_id: str,
    goal_label: str,
    priority: str = "medium",
    supporting_patterns: List[str] = None,
    blocking_patterns: List[str] = None,
) -> Optional[str]:
    """
    Create a goal node and link it to supporting/blocking patterns.

    Called by: intent_extraction_worker, goal_suggester

    This enables:
    - "What patterns support my sleep goal?"
    - "What's blocking my exercise goal?"
    """
    db = await get_db()
    supporting_patterns = supporting_patterns or []
    blocking_patterns = blocking_patterns or []

    try:
        # Create goal node
        goal_id = await get_or_create_node(
            db,
            person_id=person_id,
            node_kind="goal",
            label=goal_label.lower().strip()[:100],
            data={"priority": priority},
        )

        # Link supporting patterns
        for pattern_label in supporting_patterns[:5]:
            pattern_id = await get_or_create_node(
                db,
                person_id=person_id,
                node_kind="pattern",
                label=pattern_label.lower().strip()[:100],
            )
            await upsert_edge(
                db,
                person_id=person_id,
                from_node=pattern_id,
                to_node=goal_id,
                relation="supports",
                weight=0.6,
            )

        # Link blocking patterns
        for pattern_label in blocking_patterns[:5]:
            pattern_id = await get_or_create_node(
                db,
                person_id=person_id,
                node_kind="pattern",
                label=pattern_label.lower().strip()[:100],
            )
            await upsert_edge(
                db,
                person_id=person_id,
                from_node=pattern_id,
                to_node=goal_id,
                relation="blocks",
                weight=0.6,
            )

        LOGGER.debug(
            "[MemoryGraphWiring] created goal with pattern links",
            extra={
                "person_id": person_id,
                "goal": goal_label,
                "supporting": len(supporting_patterns),
                "blocking": len(blocking_patterns),
            },
        )
        return goal_id

    except Exception as exc:
        LOGGER.warning(
            "[MemoryGraphWiring] failed to create goal: %s",
            exc,
        )
        return None
    finally:
        await db.close()


# =============================================================================
# SOUL SIGNAL WIRING (from episodic consolidation)
# =============================================================================

async def wire_soul_signals_to_graph(
    person_id: str,
    soul_signals: Dict[str, List[str]],
    episode_id: str = "",
) -> Dict[str, int]:
    """
    Wire soul signals from episodic consolidation into the memory graph.

    Soul signals include:
    - soul: core themes/values
    - soul_shadow: inner friction/conflict
    - soul_light: alignment/clarity moments

    Returns counts of nodes created per type.
    """
    db = await get_db()
    counts = {"value": 0, "pattern": 0, "edges": 0}

    try:
        created_nodes = []

        # Core values (soul)
        for value in (soul_signals.get("soul") or [])[:5]:
            node_id = await get_or_create_node(
                db,
                person_id=person_id,
                node_kind="value",
                label=value.lower().strip()[:100],
                data={"source": "soul", "episode_id": episode_id},
            )
            created_nodes.append(node_id)
            counts["value"] += 1

        # Shadows (inner friction)
        for shadow in (soul_signals.get("soul_shadow") or [])[:5]:
            node_id = await get_or_create_node(
                db,
                person_id=person_id,
                node_kind="pattern",
                label=shadow.lower().strip()[:100],
                data={"source": "soul_shadow", "polarity": "negative", "episode_id": episode_id},
            )
            created_nodes.append(node_id)
            counts["pattern"] += 1

        # Lights (alignment moments)
        for light in (soul_signals.get("soul_light") or [])[:5]:
            node_id = await get_or_create_node(
                db,
                person_id=person_id,
                node_kind="pattern",
                label=light.lower().strip()[:100],
                data={"source": "soul_light", "polarity": "positive", "episode_id": episode_id},
            )
            created_nodes.append(node_id)
            counts["pattern"] += 1

        # Create edges between all nodes from same episode
        for i, from_id in enumerate(created_nodes):
            for to_id in created_nodes[i + 1:]:
                await upsert_edge(
                    db,
                    person_id=person_id,
                    from_node=from_id,
                    to_node=to_id,
                    relation="relates_to",
                    weight=0.4,
                )
                counts["edges"] += 1

        LOGGER.debug(
            "[MemoryGraphWiring] wired soul signals",
            extra={
                "person_id": person_id,
                "episode_id": episode_id,
                "counts": counts,
            },
        )
        return counts

    except Exception as exc:
        LOGGER.warning(
            "[MemoryGraphWiring] failed to wire soul signals: %s",
            exc,
        )
        return counts
    finally:
        await db.close()


# =============================================================================
# CONFLICT WIRING (from soul_conflict / soul_friction)
# =============================================================================

async def wire_soul_conflict_to_graph(
    person_id: str,
    conflict_themes: List[Dict[str, Any]],
) -> int:
    """
    Wire soul conflict (value vs value tension) into the memory graph.

    Creates nodes for conflicting values and opposite_of edges between them.

    Conflict theme format:
    {"left": "growth", "right": "stability", "strength": 0.7, "confidence": 0.8}

    Returns count of edges created.
    """
    db = await get_db()
    edges_created = 0

    try:
        for conflict in (conflict_themes or [])[:3]:
            left = conflict.get("left", "").lower().strip()
            right = conflict.get("right", "").lower().strip()
            strength = float(conflict.get("strength", 0.5))

            if not left or not right:
                continue

            # Create both value nodes
            left_id = await get_or_create_node(
                db,
                person_id=person_id,
                node_kind="value",
                label=left[:100],
                data={"source": "soul_conflict"},
            )
            right_id = await get_or_create_node(
                db,
                person_id=person_id,
                node_kind="value",
                label=right[:100],
                data={"source": "soul_conflict"},
            )

            # Create opposite_of edge (bidirectional conflict)
            await upsert_edge(
                db,
                person_id=person_id,
                from_node=left_id,
                to_node=right_id,
                relation="opposite_of",
                weight=strength,
            )
            edges_created += 1

        return edges_created

    except Exception as exc:
        LOGGER.warning(
            "[MemoryGraphWiring] failed to wire soul conflict: %s",
            exc,
        )
        return edges_created
    finally:
        await db.close()


async def wire_soul_friction_to_graph(
    person_id: str,
    friction_areas: List[Dict[str, Any]],
) -> int:
    """
    Wire soul friction (direction vs block) into the memory graph.

    Creates nodes for desired direction and blocking patterns,
    with blocks edges between them.

    Friction area format:
    {"direction": "creativity", "block": "workload", "intensity": 0.6}

    Returns count of edges created.
    """
    db = await get_db()
    edges_created = 0

    try:
        for area in (friction_areas or [])[:3]:
            direction = area.get("direction", "").lower().strip()
            block = area.get("block", "").lower().strip()
            intensity = float(area.get("intensity", 0.5))

            if not direction or not block:
                continue

            # Create direction node (what they want)
            direction_id = await get_or_create_node(
                db,
                person_id=person_id,
                node_kind="goal",
                label=direction[:100],
                data={"source": "soul_friction"},
            )

            # Create block node (what's stopping them)
            block_id = await get_or_create_node(
                db,
                person_id=person_id,
                node_kind="pattern",
                label=block[:100],
                data={"source": "soul_friction", "polarity": "negative"},
            )

            # Create blocks edge
            await upsert_edge(
                db,
                person_id=person_id,
                from_node=block_id,
                to_node=direction_id,
                relation="blocks",
                weight=intensity,
            )
            edges_created += 1

        return edges_created

    except Exception as exc:
        LOGGER.warning(
            "[MemoryGraphWiring] failed to wire soul friction: %s",
            exc,
        )
        return edges_created
    finally:
        await db.close()


# =============================================================================
# TIME SLOT INITIALIZATION
# =============================================================================

async def ensure_time_slots(person_id: str) -> Dict[str, str]:
    """
    Ensure the standard time slot nodes exist for a person.

    Returns dict mapping time slot name to node_id.

    Time slots:
    - morning (6am - 12pm): Vata time, creative energy
    - afternoon (12pm - 6pm): Pitta time, productive energy
    - evening (6pm - 10pm): Kapha time, reflective energy
    - night (10pm - 6am): Rest time
    """
    db = await get_db()
    slot_ids = {}

    time_slots = {
        "morning": {
            "start_hour": 6, "end_hour": 12,
            "energy_quality": "creative", "dosha_dominant": "vata"
        },
        "afternoon": {
            "start_hour": 12, "end_hour": 18,
            "energy_quality": "productive", "dosha_dominant": "pitta"
        },
        "evening": {
            "start_hour": 18, "end_hour": 22,
            "energy_quality": "reflective", "dosha_dominant": "kapha"
        },
        "night": {
            "start_hour": 22, "end_hour": 6,
            "energy_quality": "restorative", "dosha_dominant": "kapha"
        },
    }

    try:
        for slot_name, data in time_slots.items():
            node_id = await get_or_create_node(
                db,
                person_id=person_id,
                node_kind="time_slot",
                label=slot_name,
                data={**data, "system": True},
            )
            slot_ids[slot_name] = node_id

        return slot_ids

    except Exception as exc:
        LOGGER.warning(
            "[MemoryGraphWiring] failed to ensure time slots: %s",
            exc,
        )
        return slot_ids
    finally:
        await db.close()


__all__ = [
    "wire_pattern_to_graph",
    "wire_related_patterns",
    "wire_activity_to_time_slot",
    "wire_competing_activities",
    "wire_goal_to_graph",
    "wire_soul_signals_to_graph",
    "wire_soul_conflict_to_graph",
    "wire_soul_friction_to_graph",
    "ensure_time_slots",
]
