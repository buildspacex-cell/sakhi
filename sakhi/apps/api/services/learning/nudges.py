"""
Intervention Nudge Service
--------------------------
Generate and manage nudges for intervention tracking.

Nudge types:
1. Reminder - "Time for your morning walk!"
2. Encouragement - "You're on a 5-day streak!"
3. Missed - "You missed yesterday, want to check in?"
4. Milestone - "You've completed 50% of your plan!"
5. Completion - "Great job completing your routine!"
"""

from __future__ import annotations

import logging
from datetime import datetime, date, timedelta
from typing import Any, Dict, List, Optional
from enum import Enum

from pydantic import BaseModel

from sakhi.apps.api.core.db import q as dbfetch, exec as dbexec

LOGGER = logging.getLogger(__name__)


class NudgeType(str, Enum):
    """Types of nudges."""
    REMINDER = "reminder"  # Time to do the intervention
    ENCOURAGEMENT = "encouragement"  # Streak or progress praise
    MISSED = "missed"  # Missed a day
    MILESTONE = "milestone"  # Hit 25%, 50%, 75%, 100%
    COMPLETION = "completion"  # Plan completed
    CHECK_IN = "check_in"  # Did you do it today?


class NudgeChannel(str, Enum):
    """Where to send the nudge."""
    CHAT = "chat"  # Show in chat interface
    PUSH = "push"  # Push notification
    EMAIL = "email"  # Email


class Nudge(BaseModel):
    """A nudge to show to the user."""
    id: Optional[str] = None
    person_id: str
    plan_id: Optional[str] = None
    checkin_id: Optional[str] = None

    nudge_type: NudgeType
    message: str
    channel: NudgeChannel = NudgeChannel.CHAT

    # For chat display
    action_options: Optional[List[Dict[str, str]]] = None

    sent_at: Optional[datetime] = None
    read_at: Optional[datetime] = None


# =============================================================================
# Message Templates
# =============================================================================

REMINDER_TEMPLATES = [
    "Time for your {intervention}! 🎯",
    "Don't forget your {intervention} today!",
    "Your {intervention} is waiting for you! 💪",
    "Ready for your {intervention}?",
]

ENCOURAGEMENT_TEMPLATES = [
    "Amazing! You're on a {streak}-day streak with {intervention}! 🔥",
    "{streak} days in a row! Keep up the great work on {intervention}!",
    "Your consistency with {intervention} is inspiring! {streak} days!",
]

MISSED_TEMPLATES = [
    "Looks like you missed your {intervention} yesterday. Want to get back on track today?",
    "No worries about missing {intervention} yesterday. Ready to try again today?",
    "Life happens! Your {intervention} is still waiting when you're ready.",
]

MILESTONE_TEMPLATES = {
    25: "You're 25% through your {intervention} plan! Keep it up! 🌱",
    50: "Halfway there! 50% of your {intervention} plan complete! 🎯",
    75: "Almost there! 75% done with your {intervention} plan! 💪",
    100: "Congratulations! You've completed your {intervention} plan! 🎉",
}

CHECKIN_TEMPLATES = [
    "Did you do your {intervention} today?",
    "How did your {intervention} go today?",
    "Time to check in on your {intervention}!",
]


def _pick_template(templates: List[str], seed: int = 0) -> str:
    """Pick a template based on seed (for variety)."""
    return templates[seed % len(templates)]


# =============================================================================
# Nudge Generation
# =============================================================================

async def generate_daily_nudges(person_id: str) -> List[Nudge]:
    """
    Generate all nudges for a user for today.

    Call this during morning briefing or when user opens chat.
    """
    nudges = []
    today = date.today()

    # Get active plans with today's check-ins
    rows = await dbfetch(
        """
        SELECT p.id as plan_id, p.intervention_name, p.intervention_type,
               p.current_streak, p.total_scheduled, p.total_completed,
               c.id as checkin_id, c.status, c.nudge_sent
        FROM intervention_plans p
        LEFT JOIN intervention_checkins c
            ON c.plan_id = p.id AND c.scheduled_date = $2
        WHERE p.person_id = $1 AND p.status = 'active'
        """,
        person_id,
        today,
    )

    for row in rows or []:
        plan_id = str(row["plan_id"])
        intervention = row["intervention_name"]
        streak = row.get("current_streak", 0)
        checkin_status = row.get("status")

        # Reminder nudge for pending check-ins
        if checkin_status == "pending" and not row.get("nudge_sent"):
            nudges.append(Nudge(
                person_id=person_id,
                plan_id=plan_id,
                checkin_id=str(row["checkin_id"]) if row.get("checkin_id") else None,
                nudge_type=NudgeType.REMINDER,
                message=_pick_template(REMINDER_TEMPLATES, len(plan_id)).format(
                    intervention=intervention
                ),
                action_options=[
                    {"label": "Done ✅", "action": "checkin_done"},
                    {"label": "Skip", "action": "checkin_skip"},
                    {"label": "Remind later", "action": "remind_later"},
                ],
            ))

        # Encouragement for streaks
        if streak >= 3 and streak % 3 == 0:  # Every 3 days
            nudges.append(Nudge(
                person_id=person_id,
                plan_id=plan_id,
                nudge_type=NudgeType.ENCOURAGEMENT,
                message=_pick_template(ENCOURAGEMENT_TEMPLATES, streak).format(
                    intervention=intervention,
                    streak=streak,
                ),
            ))

        # Milestone nudges
        total = row.get("total_scheduled", 0)
        completed = row.get("total_completed", 0)
        if total > 0:
            progress = (completed / total) * 100
            for milestone, template in MILESTONE_TEMPLATES.items():
                if progress >= milestone and not await _milestone_sent(plan_id, milestone):
                    nudges.append(Nudge(
                        person_id=person_id,
                        plan_id=plan_id,
                        nudge_type=NudgeType.MILESTONE,
                        message=template.format(intervention=intervention),
                    ))
                    await _record_milestone(plan_id, milestone)

    # Check for yesterday's missed
    yesterday_missed = await _get_missed_yesterday(person_id)
    for missed in yesterday_missed:
        nudges.append(Nudge(
            person_id=person_id,
            plan_id=missed["plan_id"],
            nudge_type=NudgeType.MISSED,
            message=_pick_template(MISSED_TEMPLATES, 0).format(
                intervention=missed["intervention_name"]
            ),
            action_options=[
                {"label": "Do it now", "action": "checkin_done"},
                {"label": "Skip", "action": "checkin_skip"},
            ],
        ))

    return nudges


async def _get_missed_yesterday(person_id: str) -> List[Dict[str, Any]]:
    """Get interventions missed yesterday."""
    yesterday = date.today() - timedelta(days=1)

    rows = await dbfetch(
        """
        SELECT p.id as plan_id, p.intervention_name
        FROM intervention_plans p
        JOIN intervention_checkins c ON c.plan_id = p.id
        WHERE p.person_id = $1
          AND p.status = 'active'
          AND c.scheduled_date = $2
          AND c.status = 'missed'
        """,
        person_id,
        yesterday,
    )

    return [{"plan_id": str(r["plan_id"]), "intervention_name": r["intervention_name"]}
            for r in (rows or [])]


async def _milestone_sent(plan_id: str, milestone: int) -> bool:
    """Check if a milestone nudge was already sent."""
    row = await dbfetch(
        """
        SELECT 1 FROM intervention_nudges
        WHERE plan_id = $1 AND nudge_type = 'milestone'
          AND message LIKE $2
        """,
        plan_id,
        f"%{milestone}%",
        one=True,
    )
    return row is not None


async def _record_milestone(plan_id: str, milestone: int) -> None:
    """Record that a milestone was sent (to avoid duplicates)."""
    # This is handled when we save the nudge
    pass


# =============================================================================
# Nudge Persistence
# =============================================================================

async def save_nudge(nudge: Nudge) -> str:
    """Save a nudge to the database."""
    row = await dbfetch(
        """
        INSERT INTO intervention_nudges (
            person_id, plan_id, checkin_id, nudge_type, message, channel, sent_at
        ) VALUES ($1, $2, $3, $4, $5, $6, NOW())
        RETURNING id
        """,
        nudge.person_id,
        nudge.plan_id,
        nudge.checkin_id,
        nudge.nudge_type.value,
        nudge.message,
        nudge.channel.value,
        one=True,
    )

    nudge_id = str(row["id"]) if row else None

    # Mark check-in as nudge sent
    if nudge.checkin_id:
        await dbexec(
            "UPDATE intervention_checkins SET nudge_sent = TRUE, nudge_sent_at = NOW() WHERE id = $1",
            nudge.checkin_id,
        )

    return nudge_id


async def mark_nudge_read(nudge_id: str) -> None:
    """Mark a nudge as read."""
    await dbexec(
        "UPDATE intervention_nudges SET read_at = NOW() WHERE id = $1",
        nudge_id,
    )


async def mark_nudge_acted(nudge_id: str) -> None:
    """Mark a nudge as acted upon."""
    await dbexec(
        "UPDATE intervention_nudges SET acted_on = TRUE, acted_at = NOW() WHERE id = $1",
        nudge_id,
    )


async def get_unread_nudges(person_id: str, limit: int = 10) -> List[Nudge]:
    """Get unread nudges for a user."""
    rows = await dbfetch(
        """
        SELECT id, person_id, plan_id, checkin_id, nudge_type, message, channel, sent_at
        FROM intervention_nudges
        WHERE person_id = $1 AND read_at IS NULL
        ORDER BY sent_at DESC
        LIMIT $2
        """,
        person_id,
        limit,
    )

    return [
        Nudge(
            id=str(row["id"]),
            person_id=row["person_id"],
            plan_id=str(row["plan_id"]) if row.get("plan_id") else None,
            checkin_id=str(row["checkin_id"]) if row.get("checkin_id") else None,
            nudge_type=NudgeType(row["nudge_type"]),
            message=row["message"],
            channel=NudgeChannel(row.get("channel", "chat")),
            sent_at=row.get("sent_at"),
        )
        for row in (rows or [])
    ]


# =============================================================================
# Check-in Prompt for Chat
# =============================================================================

async def get_checkin_prompt(person_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a check-in prompt to show in chat.

    Returns a structured prompt with action buttons for the chat UI.
    """
    today = date.today()

    # Get pending check-ins for today
    rows = await dbfetch(
        """
        SELECT p.id as plan_id, p.intervention_name, p.intervention_type,
               p.target_per_day, c.id as checkin_id
        FROM intervention_plans p
        JOIN intervention_checkins c ON c.plan_id = p.id
        WHERE p.person_id = $1
          AND p.status = 'active'
          AND c.scheduled_date = $2
          AND c.status = 'pending'
        ORDER BY p.created_at
        LIMIT 1
        """,
        person_id,
        today,
    )

    if not rows:
        return None

    row = rows[0]

    return {
        "type": "intervention_checkin",
        "plan_id": str(row["plan_id"]),
        "checkin_id": str(row["checkin_id"]),
        "intervention_name": row["intervention_name"],
        "intervention_type": row["intervention_type"],
        "message": f"Did you do your {row['intervention_name']} today?",
        "actions": [
            {
                "label": "Yes, I did it! ✅",
                "action": "checkin",
                "data": {"plan_id": str(row["plan_id"]), "completed": True},
            },
            {
                "label": "Not yet",
                "action": "remind_later",
                "data": {"plan_id": str(row["plan_id"])},
            },
            {
                "label": "Skip today",
                "action": "checkin",
                "data": {"plan_id": str(row["plan_id"]), "completed": False},
            },
        ],
    }


# =============================================================================
# Recommendation Tracking Prompt for Chat
# =============================================================================

def create_tracking_offer(
    intervention_name: str,
    intervention_type: str = "activity",
    schedule: str = "daily",
    duration_days: int = 14,
    target_symptom: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a "Track this routine" offer to embed in chat response.

    This is what the chat UI renders as an opt-in button.
    """
    schedule_text = {
        "daily": "every day",
        "alternate_days": "every other day",
        "weekly": "3 times a week",
    }.get(schedule, schedule)

    return {
        "type": "tracking_offer",
        "message": f"Would you like me to help you track {intervention_name}?",
        "description": f"I'll remind you {schedule_text} for {duration_days} days and track your progress.",
        "intervention": {
            "name": intervention_name,
            "type": intervention_type,
            "schedule_type": schedule,
            "duration_days": duration_days,
            "target_symptom": target_symptom,
        },
        "actions": [
            {
                "label": f"Track for {duration_days} days",
                "action": "create_plan",
                "primary": True,
            },
            {
                "label": "Just a suggestion",
                "action": "dismiss",
            },
        ],
    }


__all__ = [
    "NudgeType",
    "NudgeChannel",
    "Nudge",
    "generate_daily_nudges",
    "save_nudge",
    "mark_nudge_read",
    "mark_nudge_acted",
    "get_unread_nudges",
    "get_checkin_prompt",
    "create_tracking_offer",
]
