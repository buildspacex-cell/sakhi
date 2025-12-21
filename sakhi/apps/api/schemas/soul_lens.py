from __future__ import annotations

from typing import List, Dict, Any

from pydantic import BaseModel


class SoulState(BaseModel):
    core_values: List[str] = []
    longing: List[str] = []
    aversions: List[str] = []
    identity_themes: List[str] = []
    commitments: List[str] = []
    shadow: List[str] = []
    light: List[str] = []
    conflicts: List[str] = []
    friction: List[str] = []
    confidence: float | None = None
    updated_at: str | None = None


class SoulTimelinePoint(BaseModel):
    ts: str | None = None
    shadow: List[Any] = []
    light: List[Any] = []
    conflict: List[Any] = []
    friction: List[Any] = []


class SoulSummary(BaseModel):
    top_shadow: List[str] = []
    top_light: List[str] = []
    dominant_friction: str | None = None
    identity_instability_index: float | None = None
    coherence_score: float | None = None


__all__ = ["SoulState", "SoulTimelinePoint", "SoulSummary"]
