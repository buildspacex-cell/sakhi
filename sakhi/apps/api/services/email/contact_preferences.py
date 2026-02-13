"""
Contact Preferences & Priority System
--------------------------------------
Lets users define relationships and priorities for their contacts.
The preferences are injected into the LLM triage prompt to personalize
email digest intelligence (and future messaging channels).

Channel-agnostic: works for email, Slack, Teams, WhatsApp, etc.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sakhi.apps.api.core.db import exec as dbexec
from sakhi.apps.api.core.db import q as dbfetch

LOGGER = logging.getLogger(__name__)

# Priority sort order for consistent display
PRIORITY_ORDER = {"critical": 0, "high": 1, "normal": 2, "low": 3, "muted": 4}


# =============================================================================
# CRUD
# =============================================================================


async def get_preferences(person_id: str) -> List[Dict[str, Any]]:
    """Get all contact preferences for a user, sorted by priority then name."""
    rows = await dbfetch(
        """
        SELECT id, person_id, contact_identifier, channel,
               display_name, relationship, organization,
               priority, notes, learned_from, confidence,
               created_at, updated_at
        FROM contact_preferences
        WHERE person_id = $1
        ORDER BY
            CASE priority
                WHEN 'critical' THEN 0
                WHEN 'high' THEN 1
                WHEN 'normal' THEN 2
                WHEN 'low' THEN 3
                WHEN 'muted' THEN 4
                ELSE 2
            END,
            COALESCE(display_name, contact_identifier)
        """,
        person_id,
    )
    result = []
    for row in rows or []:
        d = dict(row)
        # Serialize UUID and timestamps for JSON
        d["id"] = str(d["id"])
        d["person_id"] = str(d["person_id"])
        for ts_field in ("created_at", "updated_at"):
            val = d.get(ts_field)
            if val and hasattr(val, "isoformat"):
                d[ts_field] = val.isoformat()
        result.append(d)
    return result


async def upsert_preference(person_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create or update a contact preference.

    Uses ON CONFLICT on (person_id, contact_identifier, channel) to upsert.
    Returns the upserted row.
    """
    row = await dbfetch(
        """
        INSERT INTO contact_preferences (
            person_id, contact_identifier, channel,
            display_name, relationship, organization,
            priority, notes, learned_from, confidence
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        ON CONFLICT (person_id, contact_identifier, channel)
        DO UPDATE SET
            display_name = EXCLUDED.display_name,
            relationship = EXCLUDED.relationship,
            organization = EXCLUDED.organization,
            priority = EXCLUDED.priority,
            notes = EXCLUDED.notes,
            learned_from = EXCLUDED.learned_from,
            confidence = EXCLUDED.confidence,
            updated_at = NOW()
        RETURNING id, person_id, contact_identifier, channel,
                  display_name, relationship, organization,
                  priority, notes, learned_from, confidence,
                  created_at, updated_at
        """,
        person_id,
        data.get("contact_identifier", ""),
        data.get("channel", "email"),
        data.get("display_name"),
        data.get("relationship"),
        data.get("organization"),
        data.get("priority", "normal"),
        data.get("notes"),
        data.get("learned_from", "user_set"),
        data.get("confidence", 1.0),
        one=True,
    )
    if not row:
        return {}
    d = dict(row)
    d["id"] = str(d["id"])
    d["person_id"] = str(d["person_id"])
    for ts_field in ("created_at", "updated_at"):
        val = d.get(ts_field)
        if val and hasattr(val, "isoformat"):
            d[ts_field] = val.isoformat()
    return d


async def delete_preference(preference_id: str, person_id: str) -> bool:
    """Delete a contact preference. Returns True if deleted, False if not found."""
    result = await dbexec(
        """
        DELETE FROM contact_preferences
        WHERE id = $1 AND person_id = $2
        """,
        preference_id,
        person_id,
    )
    # asyncpg returns "DELETE N" where N is rows affected
    return result.endswith("1")


# =============================================================================
# LLM Prompt Formatting
# =============================================================================


def format_preferences_for_llm(preferences: List[Dict[str, Any]]) -> str:
    """
    Format contact preferences into a text block for LLM prompt injection.

    Only includes non-normal preferences (critical, high, low, muted)
    and any preference with notes, to keep the prompt concise.
    """
    relevant = [
        p for p in preferences
        if p.get("priority") != "normal" or p.get("notes")
    ]

    if not relevant:
        return ""

    lines = ["The user has set these contact preferences:"]
    for p in relevant:
        identifier = p.get("contact_identifier", "")
        priority = (p.get("priority") or "normal").upper()
        relationship = p.get("relationship", "")
        org = p.get("organization", "")
        notes = p.get("notes", "")

        parts = [f"- {identifier}:"]
        if relationship:
            parts.append(relationship.upper())
        if org:
            parts.append(f'at "{org}"')
        parts.append(f"(priority: {priority})")
        if notes:
            parts.append(f'— "{notes}"')

        lines.append(" ".join(parts))

    return "\n".join(lines)


# =============================================================================
# Suggestions (auto-learning from dismiss patterns)
# =============================================================================


async def get_suggestions(person_id: str) -> List[Dict[str, Any]]:
    """
    Generate contact priority suggestions from behavioral patterns.

    Two types of suggestions:
    1. MUTE: senders with 3+ dismissed action items
    2. PROMOTE: senders the user replies to frequently (5+ replies in 30 days)

    Both types exclude senders already in contact_preferences.
    """
    suggestions: List[Dict[str, Any]] = []

    # --- Mute suggestions: dismiss patterns ---
    mute_rows = await dbfetch(
        """
        WITH dismissed_senders AS (
            SELECT
                ee.sender_email,
                COUNT(*) AS dismiss_count
            FROM email_dismissed_actions eda
            JOIN email_events ee
                ON ee.person_id = eda.person_id
                AND ee.message_id = eda.message_id
            WHERE eda.person_id = $1
                AND ee.sender_email IS NOT NULL
                AND ee.sender_email != ''
            GROUP BY ee.sender_email
            HAVING COUNT(*) >= 3
        ),
        already_configured AS (
            SELECT contact_identifier
            FROM contact_preferences
            WHERE person_id = $1 AND channel = 'email'
        )
        SELECT
            ds.sender_email AS contact_identifier,
            ds.dismiss_count
        FROM dismissed_senders ds
        WHERE ds.sender_email NOT IN (SELECT contact_identifier FROM already_configured)
        ORDER BY ds.dismiss_count DESC
        LIMIT 3
        """,
        person_id,
    )
    for row in mute_rows or []:
        row_data = dict(row)
        contact_identifier = row_data.get("contact_identifier")
        dismiss_count = row_data.get("dismiss_count")
        if not contact_identifier or dismiss_count is None:
            continue
        suggestions.append({
            "contact_identifier": contact_identifier,
            "suggested_priority": "muted",
            "reason": f"You dismissed {dismiss_count} emails from this sender",
            "channel": "email",
        })

    # --- Promote suggestions: frequent reply patterns ---
    # Find senders the user replies to most (by count of outgoing emails
    # in threads where this sender has incoming emails)
    promote_rows = await dbfetch(
        """
        WITH reply_targets AS (
            SELECT
                incoming.sender_email,
                COUNT(DISTINCT outgoing.message_id) AS reply_count
            FROM email_events incoming
            JOIN email_events outgoing
                ON outgoing.person_id = incoming.person_id
                AND outgoing.thread_id = incoming.thread_id
                AND outgoing.direction = 'outgoing'
            WHERE incoming.person_id = $1
                AND incoming.direction = 'incoming'
                AND incoming.sender_email IS NOT NULL
                AND incoming.sender_email != ''
                AND incoming.is_newsletter = FALSE
                AND incoming.timestamp > NOW() - INTERVAL '30 days'
            GROUP BY incoming.sender_email
            HAVING COUNT(DISTINCT outgoing.message_id) >= 3
        ),
        already_configured AS (
            SELECT contact_identifier
            FROM contact_preferences
            WHERE person_id = $1 AND channel = 'email'
        )
        SELECT
            rt.sender_email AS contact_identifier,
            rt.reply_count
        FROM reply_targets rt
        WHERE rt.sender_email NOT IN (SELECT contact_identifier FROM already_configured)
        ORDER BY rt.reply_count DESC
        LIMIT 3
        """,
        person_id,
    )
    for row in promote_rows or []:
        row_data = dict(row)
        contact_identifier = row_data.get("contact_identifier")
        count = row_data.get("reply_count")
        if not contact_identifier or count is None:
            continue
        suggestions.append({
            "contact_identifier": contact_identifier,
            "suggested_priority": "high",
            "reason": f"You replied to {count} of their emails in the last 30 days",
            "channel": "email",
        })

    return suggestions


__all__ = [
    "get_preferences",
    "upsert_preference",
    "delete_preference",
    "format_preferences_for_llm",
    "get_suggestions",
]
