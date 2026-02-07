"""
Email Signal Extractors
-----------------------
Deterministic-first pattern extractors that analyze email metadata
to generate signals for Sakhi's intelligence layer.

Signals are provider-agnostic - they operate on normalized EmailEvents.
"""

from sakhi.apps.api.services.email.signals.avoidance import (
    AvoidanceDetector,
    detect_avoidance,
)
from sakhi.apps.api.services.email.signals.boundary import (
    BoundaryDetector,
    detect_boundary_patterns,
)
from sakhi.apps.api.services.email.signals.cognitive_load import (
    CognitiveLoadAnalyzer,
    compute_cognitive_load,
)
from sakhi.apps.api.services.email.signals.subscription import (
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
