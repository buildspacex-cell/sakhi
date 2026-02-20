"""Versioned objectives — identity, lineage, and registry.

An **Objective** is a declared goal or intention that can evolve over time.
Each mutation creates a new :class:`ObjectiveVersion` — an immutable snapshot.
The :class:`ObjectiveStore` holds the full version chain for all objectives.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterator


@dataclass(frozen=True)
class ObjectiveVersion:
    """Immutable snapshot of an objective at a specific version.

    Attributes:
        objective_id: Stable identity across versions.
        version: Monotonic version number (1, 2, 3, ...).
        timestamp: When this version was created.
        title: Human-readable label (e.g., "Sleep by 10pm").
        description: Optional longer description.
        data: Structured payload (targets, thresholds, etc.).
        source: What triggered this version ("user_input", "feedback", "crystallization").
        reason: Why it changed ("User refined after 2-week check-in").
        parent_version: Which version this evolved from (``None`` for v1).
    """

    objective_id: str
    version: int
    timestamp: datetime
    title: str
    description: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    source: str = ""
    reason: str = ""
    parent_version: int | None = None


class ObjectiveStore:
    """Registry of objectives with version lineage.

    Each ``objective_id`` maps to an ordered chain of
    :class:`ObjectiveVersion` snapshots.  Versions must be added
    sequentially (v1, v2, v3, ...).
    """

    def __init__(self) -> None:
        self._versions: dict[str, list[ObjectiveVersion]] = {}

    # -- mutators ----------------------------------------------------------

    def add(self, version: ObjectiveVersion) -> None:
        """Append a new version to the objective's chain.

        Raises ``ValueError`` if the version number is not sequential.
        """
        chain = self._versions.get(version.objective_id, [])
        expected = len(chain) + 1
        if version.version != expected:
            raise ValueError(
                f"Expected version {expected} for objective "
                f"'{version.objective_id}', got {version.version}"
            )
        chain.append(version)
        self._versions[version.objective_id] = chain

    # -- queries -----------------------------------------------------------

    def current(self, objective_id: str) -> ObjectiveVersion | None:
        """Return the latest version, or ``None``."""
        chain = self._versions.get(objective_id)
        return chain[-1] if chain else None

    def get_version(self, objective_id: str, version: int) -> ObjectiveVersion | None:
        """Return a specific version, or ``None``."""
        chain = self._versions.get(objective_id, [])
        if 1 <= version <= len(chain):
            return chain[version - 1]
        return None

    def history(self, objective_id: str) -> list[ObjectiveVersion]:
        """Return all versions in chronological order."""
        return list(self._versions.get(objective_id, []))

    def is_stale(self, objective_id: str, referenced_version: int) -> bool:
        """Return ``True`` if *referenced_version* is older than the current version."""
        current = self.current(objective_id)
        if current is None:
            return False
        return referenced_version < current.version

    def objectives(self) -> list[str]:
        """Return all objective IDs."""
        return list(self._versions.keys())

    # -- dunder ------------------------------------------------------------

    def __len__(self) -> int:
        """Total number of objectives (not versions)."""
        return len(self._versions)

    def __bool__(self) -> bool:
        return bool(self._versions)

    def __iter__(self) -> Iterator[str]:
        return iter(self._versions)
