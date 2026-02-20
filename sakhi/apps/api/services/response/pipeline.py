"""
Adaptive Response Pipeline

Main orchestration module that runs the complete Adaptive Response Framework:
1. Sensing Layer - Classify domain, extract symptom
2. Knowledge Gap Analysis - Query memory, identify gaps
3. Response Strategy - Select mode and questions
4. Context Synthesis - Prepare prompt context
5. Response Formation - Generate adaptive response

This module provides the main entry point for the framework.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from sakhi.apps.api.services.response.knowledge_gap import (
    KnowledgeGap,
    analyze_knowledge_gap,
)
from sakhi.apps.api.services.response.sensing import SenseFrame, sense_message
from sakhi.apps.api.services.response.strategy import (
    ResponseStrategy,
    adjust_strategy_for_tone,
    adjust_strategy_for_urgency,
    select_response_strategy,
)
from sakhi.apps.api.services.response.synthesizer import (
    SynthesizedContext,
    build_adaptive_prompt,
    synthesize_context,
)
from sakhi.apps.api.services.memory.sessions import get_summary

logger = logging.getLogger(__name__)


# =============================================================================
# PIPELINE RESULT
# =============================================================================

@dataclass
class AdaptiveResponseContext:
    """Complete result of the adaptive response pipeline."""

    # Stage outputs
    sense: SenseFrame = field(default_factory=SenseFrame)
    knowledge_gap: KnowledgeGap = field(default_factory=KnowledgeGap)
    strategy: ResponseStrategy = field(default_factory=ResponseStrategy)
    synthesized: SynthesizedContext = field(default_factory=SynthesizedContext)

    # Final prompt
    adaptive_prompt: str = ""

    # Debug info
    pipeline_stages: Dict[str, bool] = field(default_factory=dict)

    # Error tracking
    errors: Dict[str, str] = field(default_factory=dict)  # stage -> error message
    warnings: list = field(default_factory=list)  # Non-fatal issues

    def to_metadata(self) -> Dict[str, Any]:
        """Convert to metadata dict for logging/debugging."""
        return {
            "sense": {
                "domain": self.sense.domain,
                "sub_domain": self.sense.sub_domain,
                "symptom": self.sense.symptom,
                "temporal": self.sense.temporal,
                "tone": self.sense.tone,
                "specificity": self.sense.specificity,
                "urgency": self.sense.urgency,
                "confidence": self.sense.confidence,
            },
            "knowledge_gap": {
                "known_count": len(self.knowledge_gap.known),
                "inferred_count": len(self.knowledge_gap.inferred),
                "unknown_count": len(self.knowledge_gap.unknown),
                "dominant_dosha": self.knowledge_gap.constitution.dominant_dosha,
                "guna_mode": self.knowledge_gap.constitution.guna_mode,
            },
            "strategy": {
                "mode": self.strategy.mode,
                "questions_count": len(self.strategy.questions_to_ask),
                "known_referenced": len(self.strategy.known_to_reference),
                "reasoning": self.strategy.reasoning,
            },
            "synthesized": {
                "response_mode": self.synthesized.response_mode,
                "constitution": self.synthesized.constitution,
                "symptom": self.synthesized.symptom,
            },
            "pipeline_stages": self.pipeline_stages,
            "errors": self.errors,
            "warnings": self.warnings,
        }


# =============================================================================
# PIPELINE STAGES
# =============================================================================

def stage_1_sensing(user_text: str) -> SenseFrame:
    """
    Stage 1: Sensing Layer

    Classifies the user message into domain, extracts symptom,
    detects temporal markers, tone, and specificity.
    """
    return sense_message(user_text)


async def stage_2_knowledge_gap(
    person_id: str,
    sense: SenseFrame,
) -> KnowledgeGap:
    """
    Stage 2: Knowledge Gap Analysis

    Loads personal context (constitution, memory, state vectors),
    then generates personalized diagnostic questions via LLM.
    """
    return await analyze_knowledge_gap(person_id, sense)


def stage_3_strategy(
    sense: SenseFrame,
    gap: KnowledgeGap,
) -> ResponseStrategy:
    """
    Stage 3: Response Strategy Selection

    Determines response mode (RESPOND, CONNECT_AND_INQUIRE, INQUIRE),
    selects questions to ask, and identifies facts to reference.
    """
    # Select base strategy
    strategy = select_response_strategy(sense, gap)

    # Adjust for tone
    strategy = adjust_strategy_for_tone(strategy, sense)

    # Adjust for urgency
    strategy = adjust_strategy_for_urgency(strategy, sense)

    return strategy


def stage_4_synthesis(
    sense: SenseFrame,
    gap: KnowledgeGap,
    strategy: ResponseStrategy,
    session_summary: str = "",
    friction_state: str = "balanced",
    drift_percentage: float = 0.0,
    energy_mode: str = "sattva",
    recommendations: Optional[Dict[str, Any]] = None,
    memory_graph_context: Optional[Dict[str, Any]] = None,
    symptom_protocol: Optional[Dict[str, Any]] = None,
) -> SynthesizedContext:
    """
    Stage 4: Context Synthesis

    Compresses all gathered context into a prompt-ready format.
    Includes session_summary for pronoun/reference resolution.
    Includes friction state for jargon-free recommendations.
    Includes memory graph context for cross-entity relationships.
    """
    return synthesize_context(
        sense,
        gap,
        strategy,
        session_summary=session_summary,
        friction_state=friction_state,
        drift_percentage=drift_percentage,
        energy_mode=energy_mode,
        recommendations=recommendations,
        memory_graph_context=memory_graph_context,
        symptom_protocol=symptom_protocol,
    )


def stage_5_prompt(
    user_text: str,
    synthesized: SynthesizedContext,
) -> str:
    """
    Stage 5: Prompt Formation

    Builds the final adaptive prompt for the LLM.
    """
    return build_adaptive_prompt(user_text, synthesized)


# =============================================================================
# MAIN PIPELINE FUNCTION
# =============================================================================

async def run_adaptive_pipeline(
    person_id: str,
    user_text: str,
    session_id: str = "",
) -> AdaptiveResponseContext:
    """
    Run the complete Adaptive Response Pipeline.

    This is the main entry point for the framework. It runs all 5 stages
    and returns a complete AdaptiveResponseContext with the final prompt.

    Args:
        person_id: User ID
        user_text: User's message
        session_id: Optional session ID for loading session_summary

    Returns:
        AdaptiveResponseContext with all stage outputs and final prompt
    """
    result = AdaptiveResponseContext()
    result.pipeline_stages = {
        "sensing": False,
        "knowledge_gap": False,
        "strategy": False,
        "synthesis": False,
        "prompt": False,
    }
    result.errors = {}
    result.warnings = []

    # Load session summary for context continuity (if session_id provided)
    session_summary = ""
    if session_id:
        try:
            session_summary = await get_summary(session_id)
        except Exception as e:
            logger.warning("[AdaptivePipeline] Failed to load session summary: %s", e)

    # Stage 1: Sensing
    try:
        result.sense = stage_1_sensing(user_text)
        result.pipeline_stages["sensing"] = True
        logger.debug(
            "[AdaptivePipeline] Sensing: domain=%s, symptom=%s",
            result.sense.domain,
            result.sense.symptom,
        )
        # Check for low confidence
        if result.sense.confidence < 0.3:
            result.warnings.append(f"Low sensing confidence: {result.sense.confidence:.0%}")
    except Exception as e:
        error_msg = f"Sensing failed: {type(e).__name__}: {str(e)}"
        result.errors["sensing"] = error_msg
        logger.error("[AdaptivePipeline] %s", error_msg, exc_info=True)
        return result  # Can't continue without sensing

    # Stage 2: Knowledge Gap Analysis
    try:
        result.knowledge_gap = await stage_2_knowledge_gap(person_id, result.sense)
        result.pipeline_stages["knowledge_gap"] = True
        logger.debug(
            "[AdaptivePipeline] KnowledgeGap: known=%d, unknown=%d, dosha=%s",
            len(result.knowledge_gap.known),
            len(result.knowledge_gap.unknown),
            result.knowledge_gap.constitution.dominant_dosha,
        )
        # Check for missing constitution
        if not result.knowledge_gap.constitution.dosha_baseline:
            result.warnings.append("No dosha baseline found - using defaults")
    except Exception as e:
        error_msg = f"Knowledge gap analysis failed: {type(e).__name__}: {str(e)}"
        result.errors["knowledge_gap"] = error_msg
        logger.error("[AdaptivePipeline] %s", error_msg, exc_info=True)
        return result

    # Stage 3: Strategy Selection
    try:
        result.strategy = stage_3_strategy(result.sense, result.knowledge_gap)
        result.pipeline_stages["strategy"] = True
        logger.debug(
            "[AdaptivePipeline] Strategy: mode=%s, questions=%d",
            result.strategy.mode,
            len(result.strategy.questions_to_ask),
        )
    except Exception as e:
        error_msg = f"Strategy selection failed: {type(e).__name__}: {str(e)}"
        result.errors["strategy"] = error_msg
        logger.error("[AdaptivePipeline] %s", error_msg, exc_info=True)
        return result

    # Load friction state for jargon-free recommendations
    friction_state = "balanced"
    drift_percentage = 0.0
    energy_mode = "sattva"
    recommendations = None

    try:
        # Import here to avoid circular imports
        from sakhi.apps.api.services.turn.deterministic_context_loader import load_friction_state
        friction_data = await load_friction_state(person_id)
        friction_state = friction_data.get("friction_state", "balanced")
        drift_percentage = friction_data.get("drift_percentage", 0.0)
        energy_mode = friction_data.get("energy_mode", "sattva")

        # NOTE: Knowledge graph disabled — dosha-level KG recommendations are
        # too generic and cause hallucinated responses. Symptom-specific protocol
        # (LLM-generated below) now handles recommendations.
        # if friction_state != "balanced":
        #     try:
        #         from sakhi.apps.api.services.ayurveda.graph_reasoning import (
        #             query_balancing_recommendations,
        #         )
        #         recommendations = await query_balancing_recommendations(
        #             person_id=person_id,
        #             friction_state=friction_state,
        #         )
        #     except Exception as rec_err:
        #         logger.debug("[AdaptivePipeline] Recommendations not loaded: %s", rec_err)
    except Exception as friction_err:
        logger.debug("[AdaptivePipeline] Friction state not loaded: %s", friction_err)

    # NOTE: Memory graph disabled while knowledge graph is disabled.
    memory_graph_context = None
    # try:
    #     from sakhi.apps.api.services.turn.deterministic_context_loader import (
    #         load_memory_graph_context,
    #         extract_topic_labels_from_text,
    #     )
    #     topic_labels = extract_topic_labels_from_text(user_text)
    #     if topic_labels:
    #         memory_graph_context = await load_memory_graph_context(
    #             person_id=person_id,
    #             topic_labels=topic_labels,
    #             max_related=10,
    #         )
    #         if memory_graph_context and memory_graph_context.get("enabled"):
    #             logger.debug(
    #                 "[AdaptivePipeline] Memory graph loaded: %d matched, %d related, %d competing",
    #                 len(memory_graph_context.get("matched_nodes", [])),
    #                 len(memory_graph_context.get("related_nodes", [])),
    #                 len(memory_graph_context.get("competing_entities", [])),
    #             )
    # except Exception as graph_err:
    #     logger.debug("[AdaptivePipeline] Memory graph not loaded: %s", graph_err)

    # Look up symptom-specific recommendations via LLM (symptom-aware)
    # Note: KG queries are dosha-level (not symptom-specific), so they feed the
    # general friction-state recommendations instead. The symptom protocol needs
    # targeted advice for the ACTUAL symptom, which only the LLM can provide.
    symptom_protocol = None
    try:
        from sakhi.apps.api.services.response.diagnostic_kb import (
            get_symptom_from_sense, match_symptom, get_symptom_insight,
            generate_symptom_protocol_via_llm,
        )
        from sakhi.apps.api.services.ayurveda.causal_reasoning import map_symptom_to_dosha

        symptom_key = get_symptom_from_sense(result.sense)
        canonical = match_symptom(symptom_key)
        dosha = map_symptom_to_dosha(canonical) if canonical else None

        # Fall back to user's constitution dosha when symptom→dosha mapping fails
        if not dosha:
            dosha = result.knowledge_gap.constitution.dominant_dosha
            if dosha == "balanced":
                dosha = "vata"  # sensible default for unresolved symptoms

        os_type = result.knowledge_gap.constitution.operating_system or ""
        effective_symptom = canonical or symptom_key or result.sense.symptom or "general"
        insight = get_symptom_insight(effective_symptom, dosha, os_type)

        symptom_protocol = await generate_symptom_protocol_via_llm(
            effective_symptom, dosha, os_type, insight,
        )
        if symptom_protocol:
            logger.debug(
                "[AdaptivePipeline] Symptom protocol generated: symptom=%s, dosha=%s",
                effective_symptom, dosha,
            )
    except Exception as proto_err:
        logger.debug("[AdaptivePipeline] Symptom protocol lookup failed: %s", proto_err)

    # Stage 4: Context Synthesis
    try:
        result.synthesized = stage_4_synthesis(
            result.sense,
            result.knowledge_gap,
            result.strategy,
            session_summary=session_summary,
            friction_state=friction_state,
            drift_percentage=drift_percentage,
            energy_mode=energy_mode,
            recommendations=recommendations,
            memory_graph_context=memory_graph_context,
            symptom_protocol=symptom_protocol,
        )
        result.pipeline_stages["synthesis"] = True
    except Exception as e:
        error_msg = f"Context synthesis failed: {type(e).__name__}: {str(e)}"
        result.errors["synthesis"] = error_msg
        logger.error("[AdaptivePipeline] %s", error_msg, exc_info=True)
        return result

    # Stage 5: Prompt Formation
    try:
        result.adaptive_prompt = stage_5_prompt(user_text, result.synthesized)
        result.pipeline_stages["prompt"] = True
        logger.debug(
            "[AdaptivePipeline] Prompt generated (%d chars)",
            len(result.adaptive_prompt),
        )
    except Exception as e:
        error_msg = f"Prompt formation failed: {type(e).__name__}: {str(e)}"
        result.errors["prompt"] = error_msg
        logger.error("[AdaptivePipeline] %s", error_msg, exc_info=True)

    return result


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def should_use_adaptive_pipeline(user_text: str) -> bool:
    """
    Determine if the adaptive pipeline should be used for this message.

    Sakhi's core value is personalized responses based on the user's constitution.
    The adaptive pipeline provides this personalization for ALL conversations,
    not just health-specific ones.

    The pipeline adapts its response based on:
    - User's dosha baseline (vata/pitta/kapha)
    - Current state vectors and drift from baseline
    - Guna mode (sattva/rajas/tamas)
    - Memory of past conversations
    - Domain-specific guidance (body/mind/life/general)

    Args:
        user_text: User's message

    Returns:
        True - always use adaptive pipeline for personalized responses
    """
    # Always use adaptive pipeline - personalization is Sakhi's core value
    # The sensing layer will classify the domain appropriately
    # (body, mind, life, or general) and the pipeline adapts accordingly
    return True


def get_adaptive_prompt_if_applicable(
    result: AdaptiveResponseContext,
) -> Optional[str]:
    """
    Get the adaptive prompt if the pipeline completed successfully.

    Returns:
        Adaptive prompt string if successful, None otherwise
    """
    if result.pipeline_stages.get("prompt") and result.adaptive_prompt:
        return result.adaptive_prompt
    return None


__all__ = [
    "AdaptiveResponseContext",
    "run_adaptive_pipeline",
    "should_use_adaptive_pipeline",
    "get_adaptive_prompt_if_applicable",
    "stage_1_sensing",
    "stage_2_knowledge_gap",
    "stage_3_strategy",
    "stage_4_synthesis",
    "stage_5_prompt",
]
