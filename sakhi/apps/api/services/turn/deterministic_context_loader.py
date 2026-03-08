"""
Deterministic Context Loader

Shared module for loading ALL deterministic intelligence fields used in conversation turns.
This consolidates context loading that was previously scattered across turn_v2.py.

Used by:
- /v2/turn (production conversation endpoint)
- /lab/live-turn (debug/testing endpoint)

Categories of deterministic intelligence loaded:
1. INTERNAL STATE (from personal_model)
   - operating_system, dosha_baseline, life_context, decision_profile
   - long_term.layers (emotion, mind, soul)
   - cognitive_load, priority, priority_topics
   - soul_values, soul_identity, life_themes, identity_graph

2. BRAIN STATES (from orchestration)
   - emotion_state, soul_state, rhythm_state, goals_state, identity_momentum_state
   - forecast_state, coherence_state, alignment_state

3. ENGINE STATES (computed per-turn)
   - inner_dialogue, microreg_state, tone_state, nudge_state, empathy_state

4. SCAFFOLDS (on-demand action guides)
   - focus_path, mini_flow, micro_journey

5. CONTINUITY
   - continuity_state (conversation thread tracking)

6. COMPUTED STATES (built from above)
   - moment_model, evidence_pack, deliberation_scaffold, reflection_trace
"""

from __future__ import annotations

import json
import datetime
import logging
import os
from typing import Any, Dict, Optional
from dataclasses import dataclass, field

from sakhi.apps.api.core.db import q
from sakhi.apps.api.services.emotion_engine import compute as compute_emotion_state
from sakhi.apps.api.services.mind_engine import compute as compute_mind_state
from sakhi.apps.engine.continuity import load_continuity, DEFAULT_STATE as CONTINUITY_DEFAULT

logger = logging.getLogger(__name__)


def _env_enabled(name: str, default: bool = False) -> bool:
    raw = str(os.getenv(name, "1" if default else "0")).strip().lower()
    return raw in {"1", "true", "yes", "on"}


# Deferred for now: this path queries rhythm-planner alignment tables that are
# not guaranteed to exist in all environments.
ENABLE_RHYTHM_PLANNER_ALIGNMENT = _env_enabled("SAKHI_ENABLE_RHYTHM_PLANNER_ALIGNMENT", default=False)


@dataclass
class DeterministicContext:
    """Container for all deterministic intelligence fields."""

    # Internal State (from personal_model)
    internal_state: Dict[str, Any] = field(default_factory=dict)

    # Brain States (from personal_model — orchestration-derived)
    forecast_state: Dict[str, Any] = field(default_factory=dict)
    coherence_state: Dict[str, Any] = field(default_factory=dict)
    alignment_state: Dict[str, Any] = field(default_factory=dict)
    nudge_state: Dict[str, Any] = field(default_factory=dict)
    long_term: Dict[str, Any] = field(default_factory=dict)

    # Brain State Vectors (from personal_model — live state used for narrative/alignment/moment)
    emotion_state: Dict[str, Any] = field(default_factory=dict)
    soul_state: Dict[str, Any] = field(default_factory=dict)
    rhythm_state: Dict[str, Any] = field(default_factory=dict)
    longitudinal_state: Dict[str, Any] = field(default_factory=dict)
    identity_momentum_state: Dict[str, Any] = field(default_factory=dict)

    # Friction Framework
    operating_system: Optional[Dict[str, Any]] = None
    dosha_baseline: Optional[Dict[str, float]] = None
    life_context: Optional[Dict[str, Any]] = None
    decision_profile: Optional[Dict[str, Any]] = None

    # Friction State (computed from Prakruti vs Vikriti)
    friction_state: str = "balanced"  # chaos, intensity, stagnation, balanced
    friction_info: Dict[str, Any] = field(default_factory=dict)  # Full friction details
    drift_percentage: float = 0.0
    drift_direction: Optional[str] = None  # "elevated" or "depleted"
    primary_contributor: Optional[str] = None  # "vata", "pitta", or "kapha"
    energy_mode: str = "sattva"  # sattva, rajas, tamas

    # Body State (physical/somatic intelligence)
    body_state: Optional[Dict[str, Any]] = None  # Lightweight summary from personal_model
    body_state_full: Optional[Dict[str, Any]] = None  # Full body_state from personal_model
    body_state_translated: Optional[Dict[str, Any]] = None  # Friendly language version

    # Scaffolds (generated on-demand in turn_v2)
    focus_path: Optional[Dict[str, Any]] = None
    mini_flow: Optional[Dict[str, Any]] = None
    micro_journey: Optional[Dict[str, Any]] = None

    # Continuity
    continuity_state: Dict[str, Any] = field(default_factory=dict)

    # Rhythm-Planner Alignment
    rhythm_planner_alignment: Optional[Dict[str, Any]] = None

    # Gap hours (hours since last conversation turn)
    gap_hours: Optional[float] = None

    # Guards (surface-level usage hints for LLM)
    guards: Dict[str, str] = field(default_factory=dict)

    def to_metadata(self) -> Dict[str, Any]:
        """Convert to metadata dict for generate_reply()."""
        return {
            "internal_state": self.internal_state,
            "operating_system": self.internal_state.get("operating_system"),
            "dosha_baseline": self.internal_state.get("dosha_baseline"),
            "life_context": self.internal_state.get("life_context"),
            "decision_profile": self.internal_state.get("decision_profile"),
            "cognitive_load": self.internal_state.get("cognitive_load"),
            "priority": self.internal_state.get("priority"),
            "priority_topics": self.internal_state.get("priority_topics"),
            "soul_values": self.internal_state.get("soul_values"),
            "soul_identity": self.internal_state.get("soul_identity"),
            "life_themes": self.internal_state.get("life_themes"),
            "identity_graph": self.internal_state.get("identity_graph"),
            # Friction state (computed per-turn)
            "friction_state": self.friction_state,
            "friction_info": self.friction_info,
            "drift_percentage": self.drift_percentage,
            "energy_mode": self.energy_mode,
            # Body state (physical intelligence)
            "body_state": self.body_state,
            "body_state_translated": self.body_state_translated,
            # Brain states
            "forecast_state": self.forecast_state,
            "coherence_state": self.coherence_state,
            "alignment_state": self.alignment_state,
            "nudge_state": self.nudge_state,
            "continuity": self.continuity_state,
            "focus_path": self.focus_path,
            "focus_path_guard": self.guards.get("focus_path"),
            "mini_flow": self.mini_flow,
            "mini_flow_guard": self.guards.get("mini_flow"),
            "micro_journey": self.micro_journey,
            "micro_journey_guard": self.guards.get("micro_journey"),
            "rhythm_planner_alignment": self.rhythm_planner_alignment,
            "gap_hours": self.gap_hours,
        }


# =============================================================================
# GUARDS (surface-level usage hints to prevent over-interpretation)
# =============================================================================

DEFAULT_GUARDS = {
    "focus_path": (
        "Focus path is a simple 3-step plan. Use only as surface context; "
        "do not infer emotions or causes."
    ),
    "mini_flow": (
        "Mini-flow is a 10-20 minute routine. Use only as surface context; "
        "do not infer emotions or causes."
    ),
    "micro_journey": (
        "Micro-journey is deterministic and read-only. "
        "Do not infer emotions, causes, or modify the flows."
    ),
}


# =============================================================================
# UNIFIED PERSONAL_MODEL LOADER (single query for all fields)
# =============================================================================

_PERSONAL_MODEL_SQL = """
    SELECT
        long_term, operating_system, life_context, decision_profile,
        forecast_state, coherence_state, alignment_state, nudge_state,
        emotion_state, soul_state, rhythm_state,
        longitudinal_state, identity_momentum_state,
        body_state
    FROM personal_model
    WHERE person_id = $1
"""


def _ensure_json(value: Any) -> Any:
    """Parse JSONB strings from asyncpg if needed."""
    if isinstance(value, str):
        return json.loads(value)
    return value


async def _load_personal_model_row(person_id: str) -> Dict[str, Any]:
    """Single query for all personal_model columns used in a turn."""
    try:
        row = await q(_PERSONAL_MODEL_SQL, person_id, one=True)
        return dict(row) if row else {}
    except Exception as e:
        logger.warning("[_load_personal_model_row] Error: %s", e)
        return {}


def _parse_brain_states(row: Dict[str, Any]) -> Dict[str, Any]:
    """Extract brain state fields from the shared personal_model row."""
    return {
        "forecast_state": _ensure_json(row.get("forecast_state")) or {},
        "coherence_state": _ensure_json(row.get("coherence_state")) or {},
        "alignment_state": _ensure_json(row.get("alignment_state")) or {},
        "nudge_state": _ensure_json(row.get("nudge_state")) or {},
        "long_term": _ensure_json(row.get("long_term")) or {},
    }


def _parse_brain_state_vectors(row: Dict[str, Any]) -> Dict[str, Any]:
    """Extract live state vectors used for narrative/alignment/moment."""
    def _dict(val: Any) -> Dict[str, Any]:
        v = _ensure_json(val)
        return v if isinstance(v, dict) else {}

    return {
        "operating_system": _dict(row.get("operating_system")),
        "emotion_state": _dict(row.get("emotion_state")),
        "soul_state": _dict(row.get("soul_state")),
        "rhythm_state": _dict(row.get("rhythm_state")),
        "longitudinal_state": _dict(row.get("longitudinal_state")),
        "identity_momentum_state": _dict(row.get("identity_momentum_state")),
    }


def _parse_body_state(row: Dict[str, Any]) -> Dict[str, Any]:
    """Extract body state from the shared personal_model row."""
    result = {"body_state": None, "body_state_full": None, "body_state_translated": None}
    raw = row.get("body_state")
    if not raw:
        return result

    full_state = _ensure_json(raw)
    if not isinstance(full_state, dict):
        return result

    result["body_state_full"] = full_state

    summary = full_state.get("summary", {})
    energy = full_state.get("energy", {})
    sleep = full_state.get("sleep", {})
    dosha_body = full_state.get("dosha_body", {})

    confidence = summary.get("confidence", 0)
    overall_score = summary.get("overall_score", 0.5)
    has_meaningful_data = (
        confidence > 0.1 or
        overall_score != 0.5 or
        dosha_body.get("dominant_imbalance") is not None
    )

    if has_meaningful_data:
        result["body_state"] = {
            "overall_score": overall_score,
            "primary_need": summary.get("primary_need", "balance"),
            "dominant_imbalance": dosha_body.get("dominant_imbalance"),
            "energy_level": energy.get("level", 0.5),
            "energy_trend": energy.get("trend", "stable"),
            "sleep_quality": sleep.get("quality_score"),
            "sleep_debt": sleep.get("sleep_debt_hours"),
            "confidence": confidence,
        }

        try:
            from sakhi.apps.api.services.response.translation import translate_body_state
            result["body_state_translated"] = translate_body_state(full_state)
        except ImportError:
            logger.debug("[_parse_body_state] translation module not available")

    return result


# =============================================================================
# INTERNAL STATE LOADER (from personal_model)
# =============================================================================

async def load_internal_state(person_id: str, pm_row: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Load internal state from personal_model.

    This includes:
    - Friction Framework fields (operating_system, life_context, decision_profile)
    - Long-term layers (emotion, mind, soul summaries)
    - Cognitive metrics (cognitive_load, priority, etc.)
    - Soul/identity data

    Args:
        person_id: User ID
        pm_row: Pre-fetched personal_model row (avoids redundant query)
    """
    state = {
        "emotion": None,
        "mind": None,
        "context_vector_available": False,
        "cognitive_load": None,
        "priority": None,
        "priority_topics": None,
        "soul_values": None,
        "soul_identity": None,
        "life_themes": None,
        "identity_graph": None,
        # Friction Framework fields
        "operating_system": None,
        "dosha_baseline": None,
        "life_context": None,
        "decision_profile": None,
    }

    try:
        row = pm_row if pm_row is not None else await q(
            "SELECT long_term, operating_system, life_context, decision_profile FROM personal_model WHERE person_id = $1",
            person_id, one=True,
        ) or {}
        if row.get("long_term"):
            long_term = _ensure_json(row["long_term"])
            layers = long_term.get("layers") if isinstance(long_term, dict) else {}
            emotion = layers.get("emotion") if layers else {}
            mind = layers.get("mind") if layers else {}
            state["emotion"] = (emotion or {}).get("summary")
            state["mind"] = (mind or {}).get("summary")
            metrics = (mind or {}).get("metrics") or {}
            state["cognitive_load"] = metrics.get("cognitive_load")
            state["priority"] = metrics.get("top_priority")
            state["priority_topics"] = metrics.get("priority_topics")
            soul = layers.get("soul") if layers else {}
            soul_metrics = (soul or {}).get("metrics") or {}
            state["soul_values"] = soul_metrics.get("values")
            state["soul_identity"] = soul_metrics.get("identity_anchors")
            state["life_themes"] = soul_metrics.get("life_themes")
            if isinstance(long_term, dict) and long_term.get("identity_graph"):
                state["identity_graph"] = long_term.get("identity_graph")

        # Load Friction Framework data
        if row.get("operating_system"):
            os_data = _ensure_json(row["operating_system"])
            if isinstance(os_data, dict):
                state["operating_system"] = os_data.get("type")
                state["dosha_baseline"] = os_data.get("dosha_baseline")
        if row.get("life_context"):
            state["life_context"] = _ensure_json(row["life_context"])
        if row.get("decision_profile"):
            state["decision_profile"] = _ensure_json(row["decision_profile"])
    except Exception as e:
        logger.warning("[load_internal_state] Error loading from personal_model: %s", e)

    # Check context vector availability
    try:
        ctx_row = await q(
            "SELECT merged_context_vector FROM memory_context_cache WHERE person_id = $1",
            person_id,
            one=True,
        )
        if ctx_row and ctx_row.get("merged_context_vector") is not None:
            state["context_vector_available"] = True
    except Exception:
        pass

    # Fallback: compute emotion/mind if missing
    if not state.get("emotion"):
        try:
            summary = await compute_emotion_state(person_id)
            state["emotion"] = summary.get("summary")
        except Exception:
            state["emotion"] = None

    if not state.get("mind"):
        try:
            summary = await compute_mind_state(person_id)
            state["mind"] = summary.get("summary")
            metrics = summary.get("metrics") or {}
            state["cognitive_load"] = metrics.get("cognitive_load")
            state["priority"] = metrics.get("top_priority")
            state["priority_topics"] = metrics.get("priority_topics")
        except Exception:
            state["mind"] = None

    # Fallback: load soul data if missing (uses pm_row if available)
    if not state.get("soul_values"):
        try:
            lt_row = pm_row if pm_row is not None else await q(
                "SELECT long_term FROM personal_model WHERE person_id = $1",
                person_id, one=True,
            )
            if lt_row and lt_row.get("long_term"):
                long_term = _ensure_json(lt_row["long_term"])
                layers = long_term.get("layers") if isinstance(long_term, dict) else {}
                soul = layers.get("soul") if layers else {}
                metrics = (soul or {}).get("metrics") or {}
                state["soul_values"] = metrics.get("values")
                state["soul_identity"] = metrics.get("identity_anchors")
                state["life_themes"] = metrics.get("life_themes")
                if isinstance(long_term, dict) and long_term.get("identity_graph"):
                    state["identity_graph"] = long_term.get("identity_graph")
        except Exception:
            pass

    return state


# =============================================================================
# BRAIN STATES LOADER (from personal_model)
# =============================================================================

async def load_brain_states(person_id: str, pm_row: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Load brain states from personal_model.

    Args:
        person_id: User ID
        pm_row: Pre-fetched personal_model row (avoids redundant query)

    Returns:
        forecast_state, coherence_state, alignment_state, nudge_state, long_term
    """
    if pm_row is not None:
        return _parse_brain_states(pm_row)
    try:
        row = await q(
            """
            SELECT forecast_state, coherence_state, alignment_state, nudge_state, long_term
            FROM personal_model
            WHERE person_id = $1
            """,
            person_id,
            one=True,
        ) or {}
        return _parse_brain_states(row)
    except Exception as e:
        logger.warning("[load_brain_states] Error: %s", e)
        return _parse_brain_states({})


# =============================================================================
# CONTINUITY LOADER
# =============================================================================

async def load_continuity_state(person_id: str) -> Dict[str, Any]:
    """Load continuity state for conversation thread tracking."""
    try:
        return await load_continuity(person_id)
    except Exception as e:
        logger.warning("[load_continuity_state] Error: %s", e)
        return CONTINUITY_DEFAULT


# =============================================================================
# FRICTION STATE LOADER (Prakruti vs Vikriti)
# =============================================================================

async def load_friction_state(person_id: str) -> Dict[str, Any]:
    """
    Load current friction state by computing Vikriti vs Prakruti drift.

    Returns:
        Dict with:
        - friction_state: "chaos", "intensity", "stagnation", or "balanced"
        - drift_percentage: 0-100
        - energy_mode: "sattva", "rajas", or "tamas"
        - friction_info: Full friction details
    """
    try:
        # Import here to avoid circular imports
        from sakhi.apps.api.services.ayurveda.vikriti import (
            get_full_friction_state,
        )

        full_state = await get_full_friction_state(person_id)
        friction = full_state.get("friction", {})
        drift = full_state.get("drift", {})

        # Determine energy mode from guna if available
        energy_mode = "sattva"  # Default to clarity
        try:
            row = await q(
                """
                SELECT state_vector
                FROM memory_episodic
                WHERE user_id = $1 AND state_vector IS NOT NULL
                ORDER BY created_at DESC
                LIMIT 1
                """,
                person_id,
                one=True,
            )
            if row and row.get("state_vector"):
                sv = row["state_vector"]
                if isinstance(sv, str):
                    sv = json.loads(sv)
                guna = sv.get("guna", {})
                if guna:
                    # Find dominant guna
                    max_guna = max(guna.items(), key=lambda x: x[1])
                    energy_mode = max_guna[0]
        except Exception:
            pass

        return {
            "friction_state": friction.get("state", "balanced"),
            "drift_percentage": drift.get("drift_percentage", 0.0),
            "drift_direction": drift.get("direction"),
            "primary_contributor": drift.get("primary_contributor"),
            "energy_mode": energy_mode,
            "friction_info": friction,
        }

    except Exception as e:
        logger.warning("[load_friction_state] Error: %s", e)
        return {
            "friction_state": "balanced",
            "drift_percentage": 0.0,
            "drift_direction": None,
            "primary_contributor": None,
            "energy_mode": "sattva",
            "friction_info": {},
        }


# =============================================================================
# BODY STATE LOADER (Physical/Somatic Intelligence)
# =============================================================================

async def load_body_state(person_id: str, pm_row: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Load body state summary from personal_model.

    Args:
        person_id: User ID
        pm_row: Pre-fetched personal_model row (avoids redundant query)
    """
    if pm_row is not None:
        return _parse_body_state(pm_row)
    try:
        row = await q(
            "SELECT body_state FROM personal_model WHERE person_id = $1",
            person_id, one=True,
        )
        return _parse_body_state(row or {})
    except Exception as e:
        logger.debug("[load_body_state] Error: %s", e)
        return {"body_state": None, "body_state_full": None, "body_state_translated": None}


# =============================================================================
# RHYTHM PLANNER ALIGNMENT LOADER
# =============================================================================

async def load_rhythm_planner_alignment(person_id: str) -> Optional[Dict[str, Any]]:
    """
    Load rhythm-planner alignment for the user.

    This includes:
    - Peak energy windows for task scheduling
    - Current capacity assessment
    - Task-to-window assignments
    """
    try:
        row = await q(
            """
            SELECT recommendations, horizon, generated_at
            FROM rhythm_planner_alignment
            WHERE person_id = $1 AND horizon = 'today'
            ORDER BY generated_at DESC
            LIMIT 1
            """,
            person_id,
            one=True,
        )
        if row:
            recommendations = row.get("recommendations")
            if isinstance(recommendations, str):
                recommendations = json.loads(recommendations)
            return {
                "recommendations": recommendations,
                "horizon": row.get("horizon"),
                "generated_at": str(row.get("generated_at")) if row.get("generated_at") else None,
            }
    except Exception as e:
        logger.debug("[load_rhythm_planner_alignment] Error: %s", e)
    return None


# =============================================================================
# GAP HOURS CALCULATOR
# =============================================================================

async def calculate_gap_hours(person_id: str) -> Optional[float]:
    """Calculate hours since last conversation turn."""
    try:
        row = await q(
            "SELECT created_at FROM conversation_turns WHERE user_id=$1 ORDER BY created_at DESC LIMIT 1",
            person_id,
            one=True,
        )
        if row and row.get("created_at"):
            delta = datetime.datetime.utcnow() - row["created_at"]
            return delta.total_seconds() / 3600.0
    except Exception:
        pass
    return None


# =============================================================================
# MAIN LOADER: load_deterministic_context
# =============================================================================

async def load_deterministic_context(
    person_id: str,
    *,
    user_text: str = "",
) -> DeterministicContext:
    """
    Load ALL deterministic intelligence for a conversation turn.

    This is the main entry point that consolidates:
    - Internal state (personal_model: friction framework, long_term layers)
    - Brain states (forecast, coherence, alignment, nudge)
    - Continuity state
    - Gap hours

    Args:
        person_id: User ID
        user_text: Current user message

    Returns:
        DeterministicContext with all loaded fields
    """
    ctx = DeterministicContext()
    ctx.guards = DEFAULT_GUARDS.copy()

    # Single query for ALL personal_model columns
    pm_row = await _load_personal_model_row(person_id)
    # Load internal state (uses shared row — no redundant query)
    ctx.internal_state = await load_internal_state(person_id, pm_row=pm_row)

    # Brain states from shared row (no redundant query)
    brain = await load_brain_states(person_id, pm_row=pm_row)
    ctx.forecast_state = brain["forecast_state"]
    ctx.coherence_state = brain["coherence_state"]
    ctx.alignment_state = brain["alignment_state"]
    ctx.nudge_state = brain["nudge_state"]
    ctx.long_term = brain["long_term"]

    # Brain state vectors from shared row (replaces _get_brain_state_from_personal_model)
    vectors = _parse_brain_state_vectors(pm_row)
    ctx.emotion_state = vectors["emotion_state"]
    ctx.soul_state = vectors["soul_state"]
    ctx.rhythm_state = vectors["rhythm_state"]
    ctx.longitudinal_state = vectors["longitudinal_state"]
    ctx.identity_momentum_state = vectors["identity_momentum_state"]

    # Extract friction framework fields for convenience
    ctx.operating_system = ctx.internal_state.get("operating_system")
    ctx.dosha_baseline = ctx.internal_state.get("dosha_baseline")
    ctx.life_context = ctx.internal_state.get("life_context")
    ctx.decision_profile = ctx.internal_state.get("decision_profile")

    # Load friction state (Prakruti vs Vikriti — queries vikriti tables, not personal_model)
    friction = await load_friction_state(person_id)
    ctx.friction_state = friction["friction_state"]
    ctx.drift_percentage = friction["drift_percentage"]
    ctx.energy_mode = friction["energy_mode"]
    ctx.friction_info = friction["friction_info"]
    # Extract drift details for route consumption
    ctx.drift_direction = friction.get("drift_direction") or ctx.friction_info.get("direction")
    ctx.primary_contributor = friction.get("primary_contributor") or ctx.friction_info.get("dosha")

    # Body state from shared row (no redundant query)
    body = _parse_body_state(pm_row)
    ctx.body_state = body["body_state"]
    ctx.body_state_full = body["body_state_full"]
    ctx.body_state_translated = body["body_state_translated"]

    # Load continuity
    ctx.continuity_state = await load_continuity_state(person_id)

    # Calculate gap hours
    gap_hours = await calculate_gap_hours(person_id)
    ctx.gap_hours = gap_hours

    # Note: Cache tables (daily_reflection_cache, etc.) and scaffold caches
    # (focus_path_cache, mini_flow_cache, micro_journey_cache) are no longer
    # loaded here. The workers that populated those tables were archived and
    # the tables had 0 rows globally. Scaffolds (focus_path, mini_flow) are
    # generated on-demand in turn_v2.py when triggered by user messages.

    # Load rhythm-planner alignment only when explicitly enabled.
    if ENABLE_RHYTHM_PLANNER_ALIGNMENT:
        ctx.rhythm_planner_alignment = await load_rhythm_planner_alignment(person_id)
    else:
        ctx.rhythm_planner_alignment = None

    return ctx


# =============================================================================
# MEMORY GRAPH CONTEXT LOADER (Cross-Entity Relationships)
# =============================================================================

async def load_memory_graph_context(
    person_id: str,
    topic_labels: list[str],
    max_related: int = 10,
) -> Dict[str, Any]:
    """
    Load memory graph context for intelligent cross-entity relationships.

    This queries the memory graph to find:
    - Nodes matching the topic labels (goals, patterns, activities)
    - Related entities via edges
    - Competing entities (things that block or compete)
    - Supporting entities (things that enable or support)

    Use case: User mentions "morning routine" - find all related goals,
    competing activities, and supporting patterns.

    Args:
        person_id: User ID
        topic_labels: Keywords/topics from the user message
        max_related: Maximum related entities to return

    Returns:
        Dict with matched_nodes, related_nodes, competing_entities, supporting_entities
    """
    result = {
        "matched_nodes": [],
        "related_nodes": [],
        "competing_entities": [],
        "supporting_entities": [],
        "enabled": False,
    }

    if not topic_labels:
        return result

    try:
        from sakhi.apps.api.services.memory_graph.graph import get_context_for_topic
        from sakhi.apps.api.core.db import get_db

        db = await get_db()
        try:
            context = await get_context_for_topic(
                db,
                person_id=person_id,
                topic_labels=[t.lower().strip() for t in topic_labels if t],
                max_related=max_related,
            )
            result["matched_nodes"] = context.get("matched_nodes", [])
            result["related_nodes"] = context.get("related_nodes", [])
            result["competing_entities"] = context.get("competing_entities", [])
            result["supporting_entities"] = context.get("supporting_entities", [])
            result["enabled"] = True

            logger.debug(
                "[load_memory_graph_context] loaded graph context",
                extra={
                    "person_id": person_id,
                    "topics": topic_labels,
                    "matched": len(result["matched_nodes"]),
                    "related": len(result["related_nodes"]),
                    "competing": len(result["competing_entities"]),
                    "supporting": len(result["supporting_entities"]),
                },
            )
        finally:
            await db.close()

    except ImportError:
        logger.debug("[load_memory_graph_context] memory graph not available")
    except Exception as e:
        logger.debug("[load_memory_graph_context] Error: %s", e)

    return result


def extract_topic_labels_from_text(text: str) -> list[str]:
    """
    Extract potential topic labels from user text for memory graph lookup.

    This is a simple keyword extraction - looks for nouns and phrases
    that might match memory graph nodes.

    For more sophisticated extraction, use NLP or LLM-based extraction.
    """
    if not text:
        return []

    # Common topics to look for (can be expanded)
    topic_keywords = [
        # Time-related
        "morning", "afternoon", "evening", "night",
        # Activity-related
        "yoga", "meditation", "exercise", "work", "meeting", "sleep",
        "routine", "practice", "workout", "walk", "run",
        # Goal-related
        "goal", "plan", "habit", "focus", "productivity",
        # Pattern-related
        "stress", "anxiety", "energy", "tired", "busy", "overwhelmed",
        "calm", "peace", "balance",
    ]

    text_lower = text.lower()
    found_topics = []

    for topic in topic_keywords:
        if topic in text_lower:
            found_topics.append(topic)

    # Limit to 5 topics
    return found_topics[:5]


__all__ = [
    "DeterministicContext",
    "load_deterministic_context",
    "load_internal_state",
    "load_brain_states",
    "load_continuity_state",
    "load_friction_state",
    "load_body_state",
    "load_rhythm_planner_alignment",
    "load_memory_graph_context",
    "extract_topic_labels_from_text",
    "calculate_gap_hours",
    "DEFAULT_GUARDS",
]
