"""
Deterministic Intelligence Integration Tests

Comprehensive test suite verifying ALL deterministic intelligence fields from turn-v2:

FRICTION FRAMEWORK (Ayurvedic Pipeline):
- Operating System storage from onboarding
- State vector computation in episodic consolidation
- Internal state loading in turn-v2
- Friction state calculation

BRAIN STATES:
- emotion_state, soul_state, rhythm_state, goals_state, identity_momentum_state
- long_term.layers (emotion, mind, soul)
- forecast_state, coherence_state, alignment_state

ENGINE STATES:
- inner_dialogue, microreg_state, tone_state, nudge_state, empathy_state

CONTINUITY & REFLECTION:
- continuity_state, daily_reflection, evening_closure

MORNING CONTEXT:
- morning_preview, morning_ask, morning_momentum

MICRO CONTEXT:
- micro_momentum, micro_recovery

SCAFFOLDS:
- focus_path, mini_flow, micro_journey

COMPUTED STATES:
- moment_model, evidence_pack, deliberation_scaffold, reflection_trace

Usage:
    pytest sakhi/tests/friction_framework/ -v
    python -m sakhi.tests.friction_framework.test_friction_framework_integration
"""
