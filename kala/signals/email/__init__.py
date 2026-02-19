"""
Email Signal Detectors
----------------------
Deterministic-first pattern extractors that analyze email metadata
to generate signals. Provider-agnostic — operates on normalized EmailEvents.
"""

from kala.signals.email.avoidance import (
    AvoidanceDetector,
    detect_avoidance,
)
from kala.signals.email.boundary import (
    BoundaryDetector,
    detect_boundary_patterns,
)
from kala.signals.email.cognitive_load import (
    CognitiveLoadAnalyzer,
    compute_cognitive_load,
)
from kala.signals.email.subscription import (
    SubscriptionDetector,
    detect_subscriptions,
)

__all__ = [
    "detect_subscriptions",
    "detect_avoidance",
    "detect_boundary_patterns",
    "compute_cognitive_load",
    "SubscriptionDetector",
    "AvoidanceDetector",
    "BoundaryDetector",
    "CognitiveLoadAnalyzer",
]
