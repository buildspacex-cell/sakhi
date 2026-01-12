"""
Scaffolding Layer Library

Core components for the scaffolding layer including:
- Suppression engine (protective gating)
- Decorators for scaffold workers
- Signal schemas
- Timing logic

Design Principles:
1. Suppression First - Every proactive scaffold checks suppression
2. Signals Not Language - Layer 4 emits structured signals only
3. Adaptive Time - No fixed schedules
4. User Agency - Ignoring reduces initiative
5. No Evaluation - Pure signal-based decisions
"""

from sakhi.libs.scaffolding.suppression_engine import (
    SuppressionEngine,
    SuppressionAction,
    SuppressionSensitivity,
    SuppressionDecision,
    check_scaffold_suppression,
)

from sakhi.libs.scaffolding.decorators import (
    require_suppression_check,
)

__all__ = [
    # Suppression
    "SuppressionEngine",
    "SuppressionAction",
    "SuppressionSensitivity",
    "SuppressionDecision",
    "check_scaffold_suppression",
    # Decorators
    "require_suppression_check",
]
