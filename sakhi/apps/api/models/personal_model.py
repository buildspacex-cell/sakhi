from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class LayerState(BaseModel):
    summary: Optional[str] = None
    confidence: float = 0.0
    metrics: Dict[str, Any] = Field(default_factory=dict)


class PersonalModelData(BaseModel):
    body: LayerState = LayerState()
    mind: LayerState = LayerState()
    emotion: LayerState = LayerState()
    goals: LayerState = LayerState()
    soul: LayerState = LayerState()
    rhythm: LayerState = LayerState()
    daily_reflection_state: Dict[str, Any] = Field(default_factory=dict)
    closure_state: Dict[str, Any] = Field(default_factory=dict)
    morning_preview_state: Dict[str, Any] = Field(default_factory=dict)
    morning_ask_state: Dict[str, Any] = Field(default_factory=dict)
    morning_momentum_state: Dict[str, Any] = Field(default_factory=dict)
    micro_momentum_state: Dict[str, Any] = Field(default_factory=dict)
    micro_recovery_state: Dict[str, Any] = Field(default_factory=dict)
    focus_path_state: Dict[str, Any] = Field(default_factory=dict)
    mini_flow_state: Dict[str, Any] = Field(default_factory=dict)
    micro_journey_state: Dict[str, Any] = Field(default_factory=dict)
