"""
Adaptive Response Framework

This module implements Sakhi's constitution-aware, memory-informed response system.
Instead of generic replies, Sakhi responds like a skilled Ayurvedic practitioner:

1. Constitution-aware — Uses the user's Operating System (dosha baseline) to prioritize likely causes
2. Memory-informed — Checks what we already know before asking questions
3. Targeted inquiry — Asks maximum 2 questions per turn, chosen for diagnostic value
4. Domain-adaptive — Adjusts approach based on whether the concern is Body, Mind, or Life

Core Principle: Never ramble with 10 possibilities. Pick the most likely 2-3 based on
their constitution and ask targeted questions.

Pipeline Stages:
1. Sensing Layer - Classify domain, extract symptom, detect tone
2. Knowledge Gap Analysis - Query memory, identify what's known vs unknown
3. Response Strategy - Select mode (RESPOND, CONNECT_AND_INQUIRE, INQUIRE)
4. Context Synthesis - Compress context for LLM
5. Response Formation - Generate adaptive prompt

Usage:
    from sakhi.apps.api.services.response import run_adaptive_pipeline

    result = await run_adaptive_pipeline(person_id, user_text)
    adaptive_prompt = result.adaptive_prompt
"""

from sakhi.apps.api.services.response.diagnostic_kb import (
    ConstitutionGuidance,
    DiagnosticPath,
    get_constitution_guidance,
    get_diagnostic_path,
    get_diagnostic_questions,
)
from sakhi.apps.api.services.response.knowledge_gap import (
    ConstitutionContext,
    DiagnosticQuestion,
    Inference,
    KnowledgeGap,
    KnownFact,
    analyze_knowledge_gap,
)
from sakhi.apps.api.services.response.pipeline import (
    AdaptiveResponseContext,
    get_adaptive_prompt_if_applicable,
    run_adaptive_pipeline,
    should_use_adaptive_pipeline,
)
from sakhi.apps.api.services.response.sensing import (
    SenseFrame,
    sense_message,
)
from sakhi.apps.api.services.response.strategy import (
    ResponseMode,
    ResponseStrategy,
    select_response_strategy,
)
from sakhi.apps.api.services.response.synthesizer import (
    SynthesizedContext,
    build_adaptive_prompt,
    synthesize_context,
)
from sakhi.apps.api.services.response.templates import (
    ResponseTemplate,
    get_template,
)

__all__ = [
    # Pipeline
    "run_adaptive_pipeline",
    "should_use_adaptive_pipeline",
    "get_adaptive_prompt_if_applicable",
    "AdaptiveResponseContext",
    # Sensing
    "SenseFrame",
    "sense_message",
    # Knowledge Gap
    "KnowledgeGap",
    "KnownFact",
    "Inference",
    "DiagnosticQuestion",
    "ConstitutionContext",
    "analyze_knowledge_gap",
    # Diagnostic KB
    "DiagnosticPath",
    "ConstitutionGuidance",
    "get_diagnostic_path",
    "get_diagnostic_questions",
    "get_constitution_guidance",
    # Strategy
    "ResponseMode",
    "ResponseStrategy",
    "select_response_strategy",
    # Synthesizer
    "SynthesizedContext",
    "synthesize_context",
    "build_adaptive_prompt",
    # Templates
    "ResponseTemplate",
    "get_template",
]
