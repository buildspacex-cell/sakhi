from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field, confloat


class SelfObservation(BaseModel):
    kind: str
    score: Optional[confloat(ge=-1.0, le=1.0)] = None
    labels: List[str] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)
    confidence: confloat(ge=0.0, le=1.0)


class ObjectObservation(BaseModel):
    type: str
    domain: Optional[str] = None
    status: Optional[str] = None
    actors: List[str] = Field(default_factory=list)
    timescale: Optional[str] = None
    polarity: Optional[str] = None
    needs: List[str] = Field(default_factory=list)
    values: List[str] = Field(default_factory=list)
    signature: Optional[Dict[str, float]] = None
    notes: List[str] = Field(default_factory=list)
    confidence: confloat(ge=0.0, le=1.0) = 0.6
    object_id: Optional[str] = None


class ExtractionOutput(BaseModel):
    self: List[SelfObservation] = Field(default_factory=list)
    objects: List[ObjectObservation] = Field(default_factory=list)
    meta: Dict[str, str] | None = None


class StateVectorOutput(BaseModel):
    dosha: Dict[str, confloat(ge=-2.0, le=2.0)]
    guna: Dict[str, confloat(ge=0.0, le=1.0)]
    elements: Dict[str, confloat(ge=0.0, le=1.0)]
    notes: List[str] = Field(default_factory=list)
    confidence: confloat(ge=0.0, le=1.0)


class PhraseOutput(BaseModel):
    lines: List[str] = Field(default_factory=list)
    style: str
    confidence: confloat(ge=0.0, le=1.0)
    safety: str = "ok"
