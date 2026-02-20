"""Graph schema — valid node kinds and edge relations."""

from __future__ import annotations

# Valid node kinds (expanded for cross-entity relationships)
VALID_KINDS = {
    # Original types
    "reflection",
    "thought",
    "plan",
    "insight",
    "event",
    # Expanded types for memory graph
    "goal",
    "pattern",
    "person",
    "value",
    "theme",
    "time_slot",
    "activity",
    "emotion",
}

# Valid edge relations
VALID_RELATIONS = {
    "supports",
    "blocks",
    "competes_with",
    "enables",
    "relates_to",
    "influences",
    "scheduled_for",
    "mentions",
    "crystallized_from",
    "part_of",
    "opposite_of",
}


def sanitize_kind(kind: str) -> str:
    """Normalize and validate node kind.

    Returns 'reflection' as default for empty or unknown kinds.
    """
    if not kind:
        return "reflection"
    core = kind.split(":", 1)[0].strip().lower()
    return core if core in VALID_KINDS else "reflection"


def sanitize_relation(relation: str) -> str:
    """Normalize and validate edge relation.

    Returns 'relates_to' as default for empty or unknown relations.
    """
    if not relation:
        return "relates_to"
    core = relation.strip().lower().replace(" ", "_")
    return core if core in VALID_RELATIONS else "relates_to"
