"""Domain-agnostic temporal arc primitives."""

from kala.arc.build import (
    build_arcs,
    extract_arc_features,
    segment_arc,
    summarize_arc_structure,
)
from kala.arc.core import ArcFeatures, ArcPhase, TemporalArc

__all__ = [
    "ArcFeatures",
    "ArcPhase",
    "TemporalArc",
    "build_arcs",
    "segment_arc",
    "extract_arc_features",
    "summarize_arc_structure",
]
