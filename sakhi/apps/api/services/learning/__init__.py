"""
Learning Pipeline Services (A.7 & A.8)
--------------------------------------
Real pattern learning and preference feedback loop.

A.7 Learning Pipeline:
- outcomes.py: Track intervention effectiveness
- trigger.py: Run correlation updates

A.8 Preference Feedback Loop:
- choices.py: Track user selections
- feedback.py: Capture feedback signals
- preference_updater.py: Adjust weights from feedback
"""

from .outcomes import (
    log_intervention_outcome,
    get_effective_interventions,
    update_symptom_resolution,
)

from .trigger import (
    run_learning_cycle,
    should_trigger_learning,
    LearningRunResult,
)

from .choices import (
    log_user_choice,
    get_choice_patterns,
)

from .feedback import (
    log_recommendation_feedback,
    extract_feedback_from_text,
    FeedbackType,
)

from .preference_updater import (
    apply_feedback_to_preferences,
    apply_choice_to_preferences,
    decay_stale_preferences,
)

__all__ = [
    # Outcomes
    "log_intervention_outcome",
    "get_effective_interventions",
    "update_symptom_resolution",
    # Trigger
    "run_learning_cycle",
    "should_trigger_learning",
    "LearningRunResult",
    # Choices
    "log_user_choice",
    "get_choice_patterns",
    # Feedback
    "log_recommendation_feedback",
    "extract_feedback_from_text",
    "FeedbackType",
    # Preference Updater
    "apply_feedback_to_preferences",
    "apply_choice_to_preferences",
    "decay_stale_preferences",
]
