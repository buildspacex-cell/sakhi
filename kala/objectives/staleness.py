"""Staleness detection — bridge between objectives and constraints.

Convention: a constraint's ``source`` field encodes which objective version
created it, using the pattern ``"objective:{objective_id}:v{version}"``.

This module parses that convention and detects when constraints reference
outdated objective versions.
"""

from __future__ import annotations

import re

from kala.constraints.core import Constraint, ConstraintSet
from kala.objectives.core import ObjectiveStore, ObjectiveVersion

# ---------------------------------------------------------------------------
# Source convention
# ---------------------------------------------------------------------------

SOURCE_PREFIX = "objective:"
_SOURCE_PATTERN = re.compile(r"^objective:(.+):v(\d+)$")


def format_source(objective_id: str, version: int) -> str:
    """Build a constraint source string from objective id and version.

    >>> format_source("sleep-goal", 2)
    'objective:sleep-goal:v2'
    """
    return f"objective:{objective_id}:v{version}"


def parse_objective_source(source: str) -> tuple[str, int] | None:
    """Parse a constraint source string into ``(objective_id, version)``.

    Returns ``None`` if *source* doesn't match the objective convention.

    >>> parse_objective_source("objective:sleep-goal:v2")
    ('sleep-goal', 2)
    >>> parse_objective_source("onboarding") is None
    True
    """
    match = _SOURCE_PATTERN.match(source)
    if match is None:
        return None
    return match.group(1), int(match.group(2))


# ---------------------------------------------------------------------------
# Staleness queries
# ---------------------------------------------------------------------------


def find_stale_constraints(
    constraints: ConstraintSet,
    store: ObjectiveStore,
) -> list[tuple[Constraint, ObjectiveVersion]]:
    """Find constraints whose source references an outdated objective version.

    Returns pairs of ``(stale_constraint, current_objective_version)``.
    Constraints whose source doesn't reference an objective are skipped.
    """
    stale: list[tuple[Constraint, ObjectiveVersion]] = []

    for constraint in constraints.active():
        parsed = parse_objective_source(constraint.source)
        if parsed is None:
            continue
        obj_id, ref_ver = parsed
        if store.is_stale(obj_id, ref_ver):
            current = store.current(obj_id)
            if current is not None:
                stale.append((constraint, current))

    return stale


def invalidated_by(
    version: ObjectiveVersion,
    constraints: ConstraintSet,
) -> list[Constraint]:
    """Find constraints created for an older version of the given objective.

    Useful when a new version arrives and you need to know what's now stale.
    """
    result: list[Constraint] = []
    for constraint in constraints.active():
        parsed = parse_objective_source(constraint.source)
        if parsed is None:
            continue
        obj_id, ref_ver = parsed
        if obj_id == version.objective_id and ref_ver < version.version:
            result.append(constraint)
    return result
