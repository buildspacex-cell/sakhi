"""
Scaffolding Suppression Engine

Core protective logic that prevents scaffolds from running when user is in vulnerable state.

Design Principles:
1. Suppression First - Every proactive scaffold must check suppression
2. User Agency - Ignoring/dismissing scaffolds increases suppression
3. No Evaluation - Pure signal-based decisions, no judgment
4. Protective - Errs on side of silence over noise

MVP Scope: Implements core suppression rules for demo user testing
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from sakhi.apps.api.core.db import q


class SuppressionAction(str, Enum):
    """Suppression decision actions"""
    ALLOW = "allow"          # Scaffold can run
    SUPPRESS = "suppress"    # Scaffold should not run
    DEFER = "defer"          # Scaffold should wait


class SuppressionSensitivity(str, Enum):
    """Scaffold sensitivity levels"""
    LOW = "low"        # Can run in most conditions
    MEDIUM = "medium"  # Requires normal state
    HIGH = "high"      # Requires very stable state


@dataclass
class SuppressionDecision:
    """Result of suppression check"""
    action: SuppressionAction
    reason: str
    sensitivity: SuppressionSensitivity
    user_state: Dict[str, Any]
    checked_at: datetime.datetime


class SuppressionEngine:
    """
    Core suppression engine for scaffolding layer

    Checks multiple signals to determine if scaffolds should be suppressed:
    - Rhythm state (energy, focus, volatility)
    - Emotion state (valence, volatility)
    - Conflict state (active conflicts)
    - Engagement history (ignoring patterns)
    - User preferences (silence mode)
    - Crisis indicators (recent crisis language)
    """

    # Suppression thresholds
    RHYTHM_EXHAUSTED_THRESHOLD = 0.3
    EMOTION_VOLATILE_THRESHOLD = 0.7
    LOW_ENGAGEMENT_THRESHOLD = 0.2
    CRISIS_SUPPRESSION_HOURS = 24

    async def check_suppression(
        self,
        user_id: str,
        scaffold_type: str,
        sensitivity: SuppressionSensitivity = SuppressionSensitivity.MEDIUM
    ) -> SuppressionDecision:
        """
        Check if scaffold should be suppressed for user

        Args:
            user_id: User ID to check
            scaffold_type: Type of scaffold (e.g., "morning_preview", "focus_path")
            sensitivity: Sensitivity level of scaffold

        Returns:
            SuppressionDecision with action and reason
        """
        # Get user state
        user_state = await self._get_user_state(user_id)

        # Check suppression rules in order of severity
        # 1. Crisis language - immediate 24h suppression
        if await self._check_crisis_suppression(user_id):
            return SuppressionDecision(
                action=SuppressionAction.SUPPRESS,
                reason="crisis_detected",
                sensitivity=sensitivity,
                user_state=user_state,
                checked_at=datetime.datetime.utcnow()
            )

        # 2. User silence mode - explicit preference
        if await self._check_silence_mode(user_id):
            return SuppressionDecision(
                action=SuppressionAction.SUPPRESS,
                reason="user_silence_mode",
                sensitivity=sensitivity,
                user_state=user_state,
                checked_at=datetime.datetime.utcnow()
            )

        # 3. Active conflict - suppress during internal tension
        if await self._check_conflict_suppression(user_id):
            return SuppressionDecision(
                action=SuppressionAction.SUPPRESS,
                reason="conflict_present",
                sensitivity=sensitivity,
                user_state=user_state,
                checked_at=datetime.datetime.utcnow()
            )

        # 4. Rhythm exhaustion - low energy/focus
        if await self._check_rhythm_exhaustion(user_id):
            return SuppressionDecision(
                action=SuppressionAction.SUPPRESS,
                reason="rhythm_exhausted",
                sensitivity=sensitivity,
                user_state=user_state,
                checked_at=datetime.datetime.utcnow()
            )

        # 5. Emotion volatility - high emotional instability
        if await self._check_emotion_volatility(user_id, sensitivity):
            return SuppressionDecision(
                action=SuppressionAction.SUPPRESS,
                reason="emotion_volatile",
                sensitivity=sensitivity,
                user_state=user_state,
                checked_at=datetime.datetime.utcnow()
            )

        # 6. Low engagement - user ignoring scaffolds
        if await self._check_low_engagement(user_id, scaffold_type):
            return SuppressionDecision(
                action=SuppressionAction.SUPPRESS,
                reason="low_engagement",
                sensitivity=sensitivity,
                user_state=user_state,
                checked_at=datetime.datetime.utcnow()
            )

        # All checks passed - allow scaffold
        return SuppressionDecision(
            action=SuppressionAction.ALLOW,
            reason="all_checks_passed",
            sensitivity=sensitivity,
            user_state=user_state,
            checked_at=datetime.datetime.utcnow()
        )

    async def _get_user_state(self, user_id: str) -> Dict[str, Any]:
        """Get current user state from personal_model"""
        try:
            row = await q(
                """
                SELECT
                    rhythm_state,
                    emotion_state,
                    conflict_state,
                    user_preferences
                FROM personal_model
                WHERE person_id = $1
                """,
                user_id,
                one=True
            )

            if not row:
                return {}

            return {
                "rhythm_state": row.get("rhythm_state") or {},
                "emotion_state": row.get("emotion_state") or {},
                "conflict_state": row.get("conflict_state") or {},
                "user_preferences": row.get("user_preferences") or {}
            }
        except Exception:
            return {}

    async def _check_crisis_suppression(self, user_id: str) -> bool:
        """Check for recent crisis language in journals"""
        try:
            cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=self.CRISIS_SUPPRESSION_HOURS)

            row = await q(
                """
                SELECT EXISTS(
                    SELECT 1 FROM journals
                    WHERE person_id = $1
                    AND written_at > $2
                    AND (
                        text ILIKE '%can''t handle%'
                        OR text ILIKE '%overwhelmed%'
                        OR text ILIKE '%too much%'
                        OR text ILIKE '%breaking%'
                        OR text ILIKE '%crisis%'
                    )
                ) as has_crisis
                """,
                user_id,
                cutoff,
                one=True
            )

            return row.get("has_crisis", False) if row else False
        except Exception:
            return False

    async def _check_silence_mode(self, user_id: str) -> bool:
        """Check if user has enabled silence mode"""
        try:
            row = await q(
                """
                SELECT user_preferences
                FROM personal_model
                WHERE person_id = $1
                """,
                user_id,
                one=True
            )

            if not row:
                return False

            prefs = row.get("user_preferences") or {}
            return prefs.get("silence_mode", False) or prefs.get("proactive_scaffolds_enabled", True) is False
        except Exception:
            return False

    async def _check_conflict_suppression(self, user_id: str) -> bool:
        """Check for active internal conflict"""
        try:
            row = await q(
                """
                SELECT conflict_state
                FROM personal_model
                WHERE person_id = $1
                """,
                user_id,
                one=True
            )

            if not row:
                return False

            conflict_state = row.get("conflict_state") or {}
            return conflict_state.get("active", False) and conflict_state.get("tension_level", 0) > 0.5
        except Exception:
            return False

    async def _check_rhythm_exhaustion(self, user_id: str) -> bool:
        """Check if rhythm indicates exhaustion"""
        try:
            row = await q(
                """
                SELECT rhythm_state
                FROM personal_model
                WHERE person_id = $1
                """,
                user_id,
                one=True
            )

            if not row:
                return False

            rhythm_state = row.get("rhythm_state") or {}
            overall = rhythm_state.get("overall", 1.0)
            energy = rhythm_state.get("energy", 1.0)

            # Suppress if overall rhythm or energy critically low
            return overall < self.RHYTHM_EXHAUSTED_THRESHOLD or energy < self.RHYTHM_EXHAUSTED_THRESHOLD
        except Exception:
            return False

    async def _check_emotion_volatility(self, user_id: str, sensitivity: SuppressionSensitivity) -> bool:
        """Check if emotions are too volatile"""
        try:
            row = await q(
                """
                SELECT emotion_state
                FROM personal_model
                WHERE person_id = $1
                """,
                user_id,
                one=True
            )

            if not row:
                return False

            emotion_state = row.get("emotion_state") or {}
            volatility = emotion_state.get("volatility", 0.0)

            # Adjust threshold based on sensitivity
            threshold = self.EMOTION_VOLATILE_THRESHOLD
            if sensitivity == SuppressionSensitivity.HIGH:
                threshold = 0.5  # More strict for high sensitivity
            elif sensitivity == SuppressionSensitivity.LOW:
                threshold = 0.9  # Less strict for low sensitivity

            return volatility > threshold
        except Exception:
            return False

    async def _check_low_engagement(self, user_id: str, scaffold_type: str) -> bool:
        """Check if user has low engagement with scaffolds"""
        try:
            # Calculate engagement over last 14 days
            cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=14)

            row = await q(
                """
                SELECT
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE interacted = true) as engaged
                FROM scaffold_interactions
                WHERE person_id = $1
                AND scaffold_type = $2
                AND shown_at > $3
                """,
                user_id,
                scaffold_type,
                cutoff,
                one=True
            )

            if not row or row.get("total", 0) < 5:
                # Not enough data, don't suppress
                return False

            total = row.get("total", 0)
            engaged = row.get("engaged", 0)
            engagement_rate = engaged / total if total > 0 else 1.0

            return engagement_rate < self.LOW_ENGAGEMENT_THRESHOLD
        except Exception:
            return False


# Global instance
_engine = SuppressionEngine()


async def check_scaffold_suppression(
    user_id: str,
    scaffold_type: str,
    sensitivity: SuppressionSensitivity = SuppressionSensitivity.MEDIUM
) -> SuppressionDecision:
    """
    Convenience function to check scaffold suppression

    Args:
        user_id: User ID to check
        scaffold_type: Type of scaffold
        sensitivity: Scaffold sensitivity level

    Returns:
        SuppressionDecision
    """
    return await _engine.check_suppression(user_id, scaffold_type, sensitivity)


__all__ = [
    "SuppressionEngine",
    "SuppressionAction",
    "SuppressionSensitivity",
    "SuppressionDecision",
    "check_scaffold_suppression",
]
