from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class NarrativeState(BaseModel):
    identity_arc: Optional[str] = None
    soul_archetype: Optional[str] = None
    life_phase: Optional[str] = None
    value_conflicts: List[str] = []
    healing_direction: List[str] = []
    narrative_tension: Optional[str] = None


class AlignmentState(BaseModel):
    alignment_score: float | None = None
    conflict_zones: List[str] = []
    action_suggestions: List[str] = []


__all__ = ["NarrativeState", "AlignmentState"]
