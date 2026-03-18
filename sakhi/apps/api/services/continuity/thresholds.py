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
    max_related_anchors_per_entry: int
    related_anchor_min_score_ratio: float
    related_anchor_membership_weight: float
    unknown_if_ambiguous: bool
    coherence_min: float
    surface_mirror_min: float
    surface_detail_min: float


@dataclass(frozen=True)
class CrossTopicContinuityThresholdProfile:
    version: str
    max_candidate_topics: int
    max_topic_keys: int
    correlation_cache_ttl_hours: int
    life_dimensions_cache_ttl_hours: int
    correlation_full_sweep_max_topics: int
    cross_context_min_moments: int
    cross_context_min_combined_score: float
    cross_context_recent_activity_days: int
    whole_story_min_primary_moments: int
    whole_story_min_total_moments: int
    whole_story_min_related_moments: int
    whole_story_primary_dominance_ratio: float
    dimension_time_window_days: int
    dimension_emotion_window_days: int
    dimension_financial_window_days: int
    dimension_surface_min_topics: int
    dimension_surface_min_entries: int
    dimension_surface_level_high: float
    dimension_surface_level_low: float
    financial_surface_min_level: float


SIMULATION_CONTINUITY_THRESHOLD_PROFILE = ContinuityThresholdProfile(
    version="2026.03.18.1",
    anchor_min_score=1.0,
    anchor_margin_min=0.55,
    facet_min_score=0.7,
    facet_margin_min=0.35,
    max_facets_per_entry=1,
    max_related_anchors_per_entry=1,
    related_anchor_min_score_ratio=0.55,
    related_anchor_membership_weight=0.72,
    unknown_if_ambiguous=True,
    coherence_min=0.5,
    surface_mirror_min=0.52,
    surface_detail_min=0.72,
)


CONTINUITY_CROSS_TOPIC_THRESHOLD_PROFILE = CrossTopicContinuityThresholdProfile(
    version="2026.03.18.1",
    max_candidate_topics=3,
    max_topic_keys=3,
    correlation_cache_ttl_hours=6,
    life_dimensions_cache_ttl_hours=6,
    # Cold cache is warmed for all pairwise topic combinations up to this cap.
    correlation_full_sweep_max_topics=12,
    cross_context_min_moments=6,
    cross_context_min_combined_score=0.35,
    cross_context_recent_activity_days=90,
    whole_story_min_primary_moments=8,
    whole_story_min_total_moments=12,
    whole_story_min_related_moments=5,
    whole_story_primary_dominance_ratio=1.5,
    # Time window: capture current load pressure.
    dimension_time_window_days=14,
    # Emotion window: smooth spikes but stay recent.
    dimension_emotion_window_days=30,
    # Financial window: lower-frequency but meaningful signals.
    dimension_financial_window_days=60,
    dimension_surface_min_topics=2,
    dimension_surface_min_entries=4,
    dimension_surface_level_high=0.5,
    dimension_surface_level_low=0.3,
    financial_surface_min_level=0.65,
)
