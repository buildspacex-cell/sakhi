"""Versioned threshold profile for simulation continuity inference.

Prod-ready continuity inference needs an explicit policy surface:
same inputs + same taxonomy + same threshold profile must yield identical
classifications, fallbacks, and surfacing decisions.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ContinuityThresholdProfile:
    version: str
    anchor_min_score: float
    anchor_margin_min: float
    facet_min_score: float
    facet_margin_min: float
    max_facets_per_entry: int
    unknown_if_ambiguous: bool
    coherence_min: float
    surface_mirror_min: float
    surface_detail_min: float


SIMULATION_CONTINUITY_THRESHOLD_PROFILE = ContinuityThresholdProfile(
    version="2026.03.03.1",
    anchor_min_score=1.0,
    anchor_margin_min=0.55,
    facet_min_score=0.7,
    facet_margin_min=0.35,
    max_facets_per_entry=1,
    unknown_if_ambiguous=True,
    coherence_min=0.5,
    surface_mirror_min=0.52,
    surface_detail_min=0.72,
)
