"""
TurnResponse — Canonical response contract for POST /v2/turn.

Separates product-level fields (what the frontend uses) from debug internals.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


# =============================================================================
# Product fields — the client contract
# =============================================================================


class TurnResponseProduct(BaseModel):
    """Fields the frontend consumes. This is the public API contract."""

    model_config = ConfigDict(populate_by_name=True)

    reply: str = ""
    sessionId: Optional[str] = Field(None, alias="session_id")

    # Tone
    tone_blueprint: Optional[Dict[str, Any]] = None

    # Adaptive response framework output
    adaptive_response: Optional[Dict[str, Any]] = None

    # Friction state + recommendations (from metadata passthrough)
    friction_state: Optional[Dict[str, Any]] = None
    personalized_recommendations: Optional[Dict[str, Any]] = None

    # Journaling guidance
    journaling_ai: Optional[Dict[str, Any]] = None

    # Memory recall (used for "memories" insight pane)
    memory_recall: Optional[List[Dict[str, Any]]] = None

    # Agent task context (for task planning/execution UI)
    agent_task_context: Optional[Dict[str, Any]] = None

    # Entry ID for the stored turn
    entry_id: Optional[str] = None

    # Public continuity summary (non-debug topic signal)
    continuity: Optional[Dict[str, Any]] = None


# =============================================================================
# Debug fields — only included when SAKHI_DEBUG_RESPONSE=1 or ?debug=1
# =============================================================================


class TurnResponseDebug(BaseModel):
    """Internal fields for debugging. Never exposed to production clients."""

    # Core debug from conversation engine
    debug: Optional[Dict[str, Any]] = None

    # Reasoning chain
    reasoning: Optional[Any] = None

    # Context snapshots
    topics_snapshot: Optional[Any] = None
    topic_state: Optional[Any] = None
    emotion: Optional[Any] = None
    intents_detected: Optional[Any] = None
    plans_generated: Optional[Any] = None
    rhythm_triggered: Optional[Any] = None
    meta_reflection_triggered: Optional[Any] = None
    embedding_dim: Optional[int] = None
    orchestration: Optional[Any] = None

    # Memory internals
    memory_write: Optional[Any] = None
    memory_context: Optional[Any] = None
    reflection_hint: Optional[Any] = None

    # Planner / persona
    planner: Optional[Any] = None
    persona_update: Optional[Any] = None

    # Additional internals
    human_insights: Optional[Any] = None
    narrative_trace: Optional[Any] = None
    narrative: Optional[Any] = None
    insight_bundle: Optional[Any] = None
    behavior_profile: Optional[Any] = None
    unified_fast: Optional[Any] = None


# =============================================================================
# Combined response (product + optional debug)
# =============================================================================


class TurnResponse(TurnResponseProduct):
    """Full turn response: product fields + optional debug data."""

    debug_data: Optional[TurnResponseDebug] = None


# Field sets for filtering the raw response dict
PRODUCT_FIELDS = set(TurnResponseProduct.model_fields.keys())
DEBUG_FIELDS = set(TurnResponseDebug.model_fields.keys())


__all__ = [
    "TurnResponseProduct",
    "TurnResponseDebug",
    "TurnResponse",
    "PRODUCT_FIELDS",
    "DEBUG_FIELDS",
]
