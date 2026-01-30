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

4. CACHE TABLES (time-gated daily caches)
   - daily_reflection, evening_closure
   - morning_preview, morning_ask, morning_momentum
   - micro_momentum, micro_recovery

5. SCAFFOLDS (action guides)
   - focus_path, mini_flow, micro_journey

6. CONTINUITY
   - continuity_state (conversation thread tracking)

7. COMPUTED STATES (built from above)
   - moment_model, evidence_pack, deliberation_scaffold, reflection_trace
"""

from __future__ import annotations

import json
import datetime
import logging
from typing import Any, Dict, Optional
from dataclasses import dataclass, field

from sakhi.apps.api.core.db import q
from sakhi.apps.api.services.emotion_engine import compute as compute_emotion_state
from sakhi.apps.api.services.mind_engine import compute as compute_mind_state
from sakhi.apps.engine.continuity import load_continuity, DEFAULT_STATE as CONTINUITY_DEFAULT

logger = logging.getLogger(__name__)


@dataclass
class DeterministicContext:
    """Container for all deterministic intelligence fields."""

    # Internal State (from personal_model)
    internal_state: Dict[str, Any] = field(default_factory=dict)

    # Brain States (from personal_model)
    forecast_state: Dict[str, Any] = field(default_factory=dict)
    coherence_state: Dict[str, Any] = field(default_factory=dict)
    alignment_state: Dict[str, Any] = field(default_factory=dict)
    nudge_state: Dict[str, Any] = field(default_factory=dict)
    long_term: Dict[str, Any] = field(default_factory=dict)

    # Friction Framework
    operating_system: Optional[Dict[str, Any]] = None
    dosha_baseline: Optional[Dict[str, float]] = None
    life_context: Optional[Dict[str, Any]] = None
    decision_profile: Optional[Dict[str, Any]] = None

    # Friction State (computed from Prakruti vs Vikriti)
    friction_state: str = "balanced"  # chaos, intensity, stagnation, balanced
    friction_info: Dict[str, Any] = field(default_factory=dict)  # Full friction details
    drift_percentage: float = 0.0
    energy_mode: str = "sattva"  # sattva, rajas, tamas

    # Body State (physical/somatic intelligence)
    body_state: Optional[Dict[str, Any]] = None  # Lightweight summary from personal_model
    body_state_translated: Optional[Dict[str, Any]] = None  # Friendly language version

    # Cache Tables
    daily_reflection: Optional[Dict[str, Any]] = None
    evening_closure: Optional[Dict[str, Any]] = None
    morning_preview: Optional[Dict[str, Any]] = None
    morning_ask: Optional[Dict[str, Any]] = None
    morning_momentum: Optional[Dict[str, Any]] = None
    micro_momentum: Optional[Dict[str, Any]] = None
    micro_recovery: Optional[Dict[str, Any]] = None

    # Scaffolds
    focus_path: Optional[Dict[str, Any]] = None
    mini_flow: Optional[Dict[str, Any]] = None
    micro_journey: Optional[Dict[str, Any]] = None

    # Continuity
    continuity_state: Dict[str, Any] = field(default_factory=dict)

    # Rhythm-Planner Alignment
    rhythm_planner_alignment: Optional[Dict[str, Any]] = None

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
            "daily_reflection": self.daily_reflection,
            "daily_reflection_guard": self.guards.get("daily_reflection"),
            "evening_closure": self.evening_closure,
            "evening_closure_guard": self.guards.get("evening_closure"),
            "morning_preview": self.morning_preview,
            "morning_preview_guard": self.guards.get("morning_preview"),
            "morning_ask": self.morning_ask,
            "morning_ask_guard": self.guards.get("morning_ask"),
            "morning_momentum": self.morning_momentum,
            "morning_momentum_guard": self.guards.get("morning_momentum"),
            "micro_momentum": self.micro_momentum,
            "micro_momentum_guard": self.guards.get("micro_momentum"),
            "micro_recovery": self.micro_recovery,
            "micro_recovery_guard": self.guards.get("micro_recovery"),
            "focus_path": self.focus_path,
            "focus_path_guard": self.guards.get("focus_path"),
            "mini_flow": self.mini_flow,
            "mini_flow_guard": self.guards.get("mini_flow"),
            "micro_journey": self.micro_journey,
            "micro_journey_guard": self.guards.get("micro_journey"),
            "rhythm_planner_alignment": self.rhythm_planner_alignment,
        }


# =============================================================================
# GUARDS (surface-level usage hints to prevent over-interpretation)
# =============================================================================

DEFAULT_GUARDS = {
    "daily_reflection": (
        "Use this reflection only as surface context. "
        "Do not infer emotions, causes, diagnoses, or psychological interpretations."
    ),
    "evening_closure": (
        "Evening closure is surface-level only. "
        "Do not infer emotions, causes, diagnoses, or psychological interpretations."
    ),
    "morning_preview": (
        "Use morning preview only as surface-level context. "
        "Do not infer mood, meaning, or causes."
    ),
    "morning_ask": (
        "Use morning ask only as surface-level context. "
        "Do not infer mood, meaning, or causes."
    ),
    "morning_momentum": (
        "Use morning momentum only as surface-level context. "
        "Do not infer mood, meaning, or causes."
    ),
    "micro_momentum": (
        "Use micro momentum only as small optional suggestions. "
        "Do not infer mood, meaning, or causes."
    ),
    "micro_recovery": (
        "Micro-recovery is optional and surface-level. "
        "No emotion inference or meaning attribution."
    ),
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
# INTERNAL STATE LOADER (from personal_model)
# =============================================================================

async def load_internal_state(person_id: str) -> Dict[str, Any]:
    """
    Load internal state from personal_model.

    This includes:
    - Friction Framework fields (operating_system, life_context, decision_profile)
    - Long-term layers (emotion, mind, soul summaries)
    - Cognitive metrics (cognitive_load, priority, etc.)
    - Soul/identity data
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
        row = await q(
            """
            SELECT long_term, operating_system, life_context, decision_profile
            FROM personal_model
            WHERE person_id = $1
            """,
            person_id,
            one=True,
        )
        if row and row.get("long_term"):
            long_term = row["long_term"]
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
        if row and row.get("operating_system"):
            os_data = row["operating_system"]
            if isinstance(os_data, str):
                os_data = json.loads(os_data)
            state["operating_system"] = os_data.get("type")
            state["dosha_baseline"] = os_data.get("dosha_baseline")
        if row and row.get("life_context"):
            life_ctx = row["life_context"]
            if isinstance(life_ctx, str):
                life_ctx = json.loads(life_ctx)
            state["life_context"] = life_ctx
        if row and row.get("decision_profile"):
            dec_profile = row["decision_profile"]
            if isinstance(dec_profile, str):
                dec_profile = json.loads(dec_profile)
            state["decision_profile"] = dec_profile
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

    # Fallback: load soul data if missing
    if not state.get("soul_values"):
        try:
            row = await q(
                "SELECT long_term FROM personal_model WHERE person_id = $1",
                person_id,
                one=True,
            )
            if row and row.get("long_term"):
                long_term = row["long_term"]
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

async def load_brain_states(person_id: str) -> Dict[str, Any]:
    """
    Load brain states from personal_model.

    Returns:
        forecast_state, coherence_state, alignment_state, nudge_state, long_term
    """
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
        return {
            "forecast_state": row.get("forecast_state") or {},
            "coherence_state": row.get("coherence_state") or {},
            "alignment_state": row.get("alignment_state") or {},
            "nudge_state": row.get("nudge_state") or {},
            "long_term": row.get("long_term") or {},
        }
    except Exception as e:
        logger.warning("[load_brain_states] Error: %s", e)
        return {
            "forecast_state": {},
            "coherence_state": {},
            "alignment_state": {},
            "nudge_state": {},
            "long_term": {},
        }


# =============================================================================
# CACHE TABLES LOADER (time-gated daily caches)
# =============================================================================

async def load_cache_tables(
    person_id: str,
    *,
    current_hour: Optional[int] = None,
    gap_hours: Optional[float] = None,
    user_text: str = "",
) -> Dict[str, Any]:
    """
    Load time-gated cache tables.

    Time gates:
    - Morning context (hour <= 11): morning_preview, morning_ask, morning_momentum
    - Micro momentum (hour <= 15): micro_momentum
    - Evening closure (hour >= 20): evening_closure
    - Gap-triggered: micro_recovery (gap > 3 hours or restart phrases)

    Args:
        person_id: User ID
        current_hour: Current hour (0-23), defaults to UTC now
        gap_hours: Hours since last turn (for micro_recovery trigger)
        user_text: Current user message (for restart phrase detection)
    """
    if current_hour is None:
        current_hour = datetime.datetime.utcnow().hour

    today = datetime.date.today()
    result = {
        "daily_reflection": None,
        "evening_closure": None,
        "morning_preview": None,
        "morning_ask": None,
        "morning_momentum": None,
        "micro_momentum": None,
        "micro_recovery": None,
    }

    # Daily reflection (always load)
    try:
        rows = await q(
            """
            SELECT summary, reflection_date, generated_at
            FROM daily_reflection_cache
            WHERE person_id = $1 AND reflection_date = $2
            """,
            person_id,
            today,
        )
        result["daily_reflection"] = rows[0] if rows else None
    except Exception:
        pass

    # Evening closure (hour >= 20)
    if current_hour >= 20:
        try:
            rows = await q(
                """
                SELECT completed, pending, signals, summary, closure_date, generated_at
                FROM daily_closure_cache
                WHERE person_id = $1 AND closure_date = $2
                """,
                person_id,
                today,
            )
            result["evening_closure"] = rows[0] if rows else None
        except Exception:
            pass

    # Morning context (hour <= 11)
    if current_hour <= 11:
        try:
            rows = await q(
                """
                SELECT focus_areas, key_tasks, reminders, rhythm_hint, summary, preview_date, generated_at
                FROM morning_preview_cache
                WHERE person_id = $1 AND preview_date = $2
                """,
                person_id,
                today,
            )
            result["morning_preview"] = rows[0] if rows else None
        except Exception:
            pass

        try:
            rows = await q(
                """
                SELECT question, reason, ask_date, generated_at
                FROM morning_ask_cache
                WHERE person_id = $1 AND ask_date = $2
                """,
                person_id,
                today,
            )
            result["morning_ask"] = rows[0] if rows else None
        except Exception:
            pass

        try:
            rows = await q(
                """
                SELECT momentum_hint, suggested_start, reason, momentum_date, generated_at
                FROM morning_momentum_cache
                WHERE person_id = $1 AND momentum_date = $2
                """,
                person_id,
                today,
            )
            result["morning_momentum"] = rows[0] if rows else None
        except Exception:
            pass

    # Micro momentum (hour <= 15)
    if current_hour <= 15:
        try:
            rows = await q(
                """
                SELECT nudge, reason, nudge_date, generated_at
                FROM micro_momentum_cache
                WHERE person_id = $1 AND nudge_date = $2
                """,
                person_id,
                today,
            )
            result["micro_momentum"] = rows[0] if rows else None
        except Exception:
            pass

    # Micro recovery (gap > 3 hours, restart phrases, or afternoon)
    text_lower = (user_text or "").lower()
    restart_phrases = ["restart", "where were we", "how do i restart", "let's continue", "resume"]
    gap_reason = any(p in text_lower for p in restart_phrases)

    if gap_reason or (gap_hours is not None and gap_hours > 3) or current_hour >= 14:
        try:
            rows = await q(
                """
                SELECT nudge, reason, recovery_date, generated_at
                FROM micro_recovery_cache
                WHERE person_id = $1 AND recovery_date = $2
                """,
                person_id,
                today,
            )
            result["micro_recovery"] = rows[0] if rows else None
        except Exception:
            pass

    return result


# =============================================================================
# SCAFFOLDS LOADER
# =============================================================================

async def load_scaffolds(person_id: str) -> Dict[str, Any]:
    """
    Load scaffold caches: focus_path, mini_flow, micro_journey.
    """
    today = datetime.date.today()
    result = {
        "focus_path": None,
        "mini_flow": None,
        "micro_journey": None,
    }

    # Focus path
    try:
        rows = await q(
            """
            SELECT anchor_step, progress_step, closure_step, intent_source, path_date, generated_at
            FROM focus_path_cache
            WHERE person_id = $1 AND path_date = $2
            """,
            person_id,
            today,
        )
        result["focus_path"] = rows[0] if rows else None
    except Exception:
        pass

    # Mini flow
    try:
        rows = await q(
            """
            SELECT warmup_step, focus_block_step, closure_step, optional_reward, source, flow_date, generated_at, rhythm_slot
            FROM mini_flow_cache
            WHERE person_id = $1 AND flow_date = $2
            """,
            person_id,
            today,
        )
        result["mini_flow"] = rows[0] if rows else None
    except Exception:
        pass

    # Micro journey (not date-scoped)
    try:
        rows = await q(
            """
            SELECT flow_count, rhythm_slot, journey, generated_at
            FROM micro_journey_cache
            WHERE person_id = $1
            """,
            person_id,
        )
        result["micro_journey"] = rows[0] if rows else None

        # Enrich with structure data
        if result["micro_journey"] and result["micro_journey"].get("journey"):
            journey = result["micro_journey"]["journey"]
            if isinstance(journey, dict):
                structure = journey.get("structure") or {}
                result["micro_journey"]["total_estimated_minutes"] = structure.get("total_estimated_minutes")
                result["micro_journey"]["pacing"] = structure.get("pacing") or {}
    except Exception:
        pass

    return result


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
            "energy_mode": energy_mode,
            "friction_info": friction,
        }

    except Exception as e:
        logger.warning("[load_friction_state] Error: %s", e)
        return {
            "friction_state": "balanced",
            "drift_percentage": 0.0,
            "energy_mode": "sattva",
            "friction_info": {},
        }


# =============================================================================
# BODY STATE LOADER (Physical/Somatic Intelligence)
# =============================================================================

async def load_body_state(person_id: str) -> Dict[str, Any]:
    """
    Load body state summary from personal_model.

    Returns lightweight summary for conversation context:
    - overall_score: 0-1 physical wellness
    - primary_need: grounding, cooling, movement, rest, nourishment, balance
    - dominant_imbalance: vata, pitta, kapha, or None
    - energy_level: 0-1 current energy
    - sleep_quality: 0-1 recent sleep quality
    - confidence: 0-1 how reliable the data is

    Also returns translated version for friendly prompts.
    """
    result = {
        "body_state": None,
        "body_state_translated": None,
    }

    try:
        row = await q(
            """
            SELECT body_state
            FROM personal_model
            WHERE person_id = $1
            """,
            person_id,
            one=True,
        )

        if row and row.get("body_state"):
            full_state = row["body_state"]
            if isinstance(full_state, str):
                full_state = json.loads(full_state)

            # Extract lightweight summary
            summary = full_state.get("summary", {})
            energy = full_state.get("energy", {})
            sleep = full_state.get("sleep", {})
            dosha_body = full_state.get("dosha_body", {})

            # Check if we have meaningful data (not just defaults)
            confidence = summary.get("confidence", 0)
            overall_score = summary.get("overall_score", 0.5)
            has_meaningful_data = (
                confidence > 0.1 or
                overall_score != 0.5 or
                dosha_body.get("dominant_imbalance") is not None
            )

            if has_meaningful_data:
                lightweight = {
                    "overall_score": overall_score,
                    "primary_need": summary.get("primary_need", "balance"),
                    "dominant_imbalance": dosha_body.get("dominant_imbalance"),
                    "energy_level": energy.get("level", 0.5),
                    "energy_trend": energy.get("trend", "stable"),
                    "sleep_quality": sleep.get("quality_score"),
                    "sleep_debt": sleep.get("sleep_debt_hours"),
                    "confidence": confidence,
                }
                result["body_state"] = lightweight

                # Translate to friendly language
                try:
                    from sakhi.apps.api.services.response.translation import translate_body_state
                    result["body_state_translated"] = translate_body_state(full_state)
                except ImportError:
                    logger.debug("[load_body_state] translation module not available")

    except Exception as e:
        logger.debug("[load_body_state] Error: %s", e)

    return result


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
    skip_cache_tables: bool = False,
    skip_scaffolds: bool = False,
) -> DeterministicContext:
    """
    Load ALL deterministic intelligence for a conversation turn.

    This is the main entry point that consolidates:
    - Internal state (personal_model: friction framework, long_term layers)
    - Brain states (forecast, coherence, alignment, nudge)
    - Cache tables (daily reflection, morning context, micro context)
    - Scaffolds (focus_path, mini_flow, micro_journey)
    - Continuity state

    Args:
        person_id: User ID
        user_text: Current user message (for time-gate triggers)
        skip_cache_tables: Skip loading cache tables (for minimal mode)
        skip_scaffolds: Skip loading scaffolds (for minimal mode)

    Returns:
        DeterministicContext with all loaded fields
    """
    ctx = DeterministicContext()
    ctx.guards = DEFAULT_GUARDS.copy()

    # Load internal state
    ctx.internal_state = await load_internal_state(person_id)

    # Load brain states
    brain = await load_brain_states(person_id)
    ctx.forecast_state = brain["forecast_state"]
    ctx.coherence_state = brain["coherence_state"]
    ctx.alignment_state = brain["alignment_state"]
    ctx.nudge_state = brain["nudge_state"]
    ctx.long_term = brain["long_term"]

    # Extract friction framework fields for convenience
    ctx.operating_system = ctx.internal_state.get("operating_system")
    ctx.dosha_baseline = ctx.internal_state.get("dosha_baseline")
    ctx.life_context = ctx.internal_state.get("life_context")
    ctx.decision_profile = ctx.internal_state.get("decision_profile")

    # Load friction state (Prakruti vs Vikriti)
    friction = await load_friction_state(person_id)
    ctx.friction_state = friction["friction_state"]
    ctx.drift_percentage = friction["drift_percentage"]
    ctx.energy_mode = friction["energy_mode"]
    ctx.friction_info = friction["friction_info"]

    # Load body state (physical/somatic intelligence)
    body = await load_body_state(person_id)
    ctx.body_state = body["body_state"]
    ctx.body_state_translated = body["body_state_translated"]

    # Load continuity
    ctx.continuity_state = await load_continuity_state(person_id)

    # Calculate gap hours for micro_recovery trigger
    gap_hours = await calculate_gap_hours(person_id)

    # Load cache tables (unless skipped)
    if not skip_cache_tables:
        cache = await load_cache_tables(
            person_id,
            gap_hours=gap_hours,
            user_text=user_text,
        )
        ctx.daily_reflection = cache["daily_reflection"]
        ctx.evening_closure = cache["evening_closure"]
        ctx.morning_preview = cache["morning_preview"]
        ctx.morning_ask = cache["morning_ask"]
        ctx.morning_momentum = cache["morning_momentum"]
        ctx.micro_momentum = cache["micro_momentum"]
        ctx.micro_recovery = cache["micro_recovery"]

    # Load scaffolds (unless skipped)
    if not skip_scaffolds:
        scaffolds = await load_scaffolds(person_id)
        ctx.focus_path = scaffolds["focus_path"]
        ctx.mini_flow = scaffolds["mini_flow"]
        ctx.micro_journey = scaffolds["micro_journey"]

    # Load rhythm-planner alignment
    ctx.rhythm_planner_alignment = await load_rhythm_planner_alignment(person_id)

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
    "load_cache_tables",
    "load_scaffolds",
    "load_continuity_state",
    "load_friction_state",
    "load_body_state",
    "load_rhythm_planner_alignment",
    "load_memory_graph_context",
    "extract_topic_labels_from_text",
    "calculate_gap_hours",
    "DEFAULT_GUARDS",
]
