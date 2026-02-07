"""
Sakhi Email Intelligence Integration
------------------------------------
Connects email signals to Sakhi's broader intelligence layer.

Key responsibilities:
- Extract and store signals from email events
- Surface insights in conversation
- Map email patterns to friction framework
- Provide context for recommendations

Principle: Email signals are soft evidence, not dictates.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sakhi.apps.api.core.db import exec as dbexec
from sakhi.apps.api.core.db import q as dbfetch
from sakhi.apps.api.services.email.models import (
    AvoidanceSignal,
    BoundarySignal,
    CognitiveLoadSignal,
    SignalType,
    SubscriptionSignal,
)
from sakhi.apps.api.services.email.signals import (
    compute_cognitive_load,
    detect_avoidance,
    detect_boundary_patterns,
    detect_subscriptions,
)
from sakhi.apps.api.services.email.sync import (
    get_stored_events,
    get_sync_state,
)

LOGGER = logging.getLogger(__name__)


# =============================================================================
# Signal Extraction Pipeline
# =============================================================================

async def extract_all_signals(
    person_id: str,
    *,
    force_refresh: bool = False,
) -> Dict[str, Any]:
    """
    Extract all email signals for a user.

    This is typically run after sync completes or periodically.

    Args:
        person_id: User ID
        force_refresh: Re-extract even if recent signals exist

    Returns:
        Dict with all extracted signals
    """
    # Check if we need to extract
    if not force_refresh:
        last_extraction = await _get_last_extraction_time(person_id)
        if last_extraction and (datetime.now(timezone.utc) - last_extraction) < timedelta(hours=6):
            LOGGER.debug("[EmailIntegration] Recent signals exist, skipping extraction")
            return await get_stored_signals(person_id)

    # Get sync state
    state = await get_sync_state(person_id)
    if not state:
        return {"status": "not_connected"}

    # Get stored events
    events = await get_stored_events(person_id, limit=2000)
    if not events:
        return {"status": "no_events"}

    # Get user email from sync state
    user_email = await _get_user_email(person_id)

    # Extract signals
    subscriptions = await detect_subscriptions(events)
    avoidance = await detect_avoidance(events, user_email) if user_email else []
    boundary = await detect_boundary_patterns(events)
    cognitive_load = await compute_cognitive_load(events)

    # Store signals
    await _store_signals(
        person_id,
        subscriptions=subscriptions,
        avoidance=avoidance,
        boundary=boundary,
        cognitive_load=cognitive_load,
    )

    # Log to behavior_log for pattern learning
    await _log_to_behavior_log(person_id, boundary, cognitive_load)

    result = {
        "status": "extracted",
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "subscriptions": [s.dict() for s in subscriptions],
        "avoidance": [a.dict() for a in avoidance],
        "boundary": boundary.dict(),
        "cognitive_load": cognitive_load.dict(),
    }

    LOGGER.info(
        "[EmailIntegration] Extracted signals for %s: %d subscriptions, %d avoidance, erosion=%.2f",
        person_id,
        len(subscriptions),
        len(avoidance),
        boundary.erosion_score,
    )

    return result


async def _get_user_email(person_id: str) -> Optional[str]:
    """Get user's email address from sync state or profile."""
    # Try sync state first
    row = await dbfetch(
        """
        SELECT u.email
        FROM users u
        WHERE u.id = $1
        """,
        person_id,
        one=True,
    )
    return row["email"] if row else None


async def _get_last_extraction_time(person_id: str) -> Optional[datetime]:
    """Get timestamp of last signal extraction."""
    row = await dbfetch(
        """
        SELECT MAX(extracted_at) as last_extraction
        FROM email_signals
        WHERE person_id = $1
        """,
        person_id,
        one=True,
    )
    return row["last_extraction"] if row else None


async def _store_signals(
    person_id: str,
    subscriptions: List[SubscriptionSignal],
    avoidance: List[AvoidanceSignal],
    boundary: BoundarySignal,
    cognitive_load: CognitiveLoadSignal,
) -> None:
    """Store extracted signals in database."""
    now = datetime.now(timezone.utc)

    # Clear old signals
    await dbexec(
        "DELETE FROM email_signals WHERE person_id = $1",
        person_id,
    )

    # Store subscription signals
    for sub in subscriptions:
        await dbexec(
            """
            INSERT INTO email_signals (
                person_id, signal_type, signal_data, confidence, extracted_at
            ) VALUES ($1, $2, $3::jsonb, $4, $5)
            """,
            person_id,
            SignalType.SUBSCRIPTION.value,
            sub.json(),
            sub.confidence,
            now,
        )

    # Store avoidance signals
    for avoid in avoidance:
        await dbexec(
            """
            INSERT INTO email_signals (
                person_id, signal_type, signal_data, confidence, extracted_at
            ) VALUES ($1, $2, $3::jsonb, $4, $5)
            """,
            person_id,
            SignalType.AVOIDANCE.value,
            avoid.json(),
            avoid.confidence,
            now,
        )

    # Store boundary signal
    await dbexec(
        """
        INSERT INTO email_signals (
            person_id, signal_type, signal_data, confidence, extracted_at
        ) VALUES ($1, $2, $3::jsonb, $4, $5)
        """,
        person_id,
        SignalType.BOUNDARY_EROSION.value,
        boundary.json(),
        boundary.confidence,
        now,
    )

    # Store cognitive load signal
    await dbexec(
        """
        INSERT INTO email_signals (
            person_id, signal_type, signal_data, confidence, extracted_at
        ) VALUES ($1, $2, $3::jsonb, $4, $5)
        """,
        person_id,
        SignalType.COGNITIVE_LOAD.value,
        cognitive_load.json(),
        cognitive_load.confidence,
        now,
    )


async def _log_to_behavior_log(
    person_id: str,
    boundary: BoundarySignal,
    cognitive_load: CognitiveLoadSignal,
) -> None:
    """
    Log email-derived behaviors to Sakhi's behavior_log.

    This enables pattern learning to correlate email patterns
    with symptoms and states.
    """
    now = datetime.now(timezone.utc)

    # Log boundary erosion if significant
    if boundary.erosion_score > 0.2:
        dosha_effect = None
        if boundary.friction_impact == "chaos_friction":
            dosha_effect = "vata"
        elif boundary.friction_impact == "intensity_friction":
            dosha_effect = "pitta"

        try:
            await dbexec(
                """
                INSERT INTO behavior_log (
                    person_id, behavior_type, behavior_name, occurred_at,
                    dosha_effect, effect_direction, intensity, source_type
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                person_id,
                "email_pattern",
                "boundary_erosion",
                now,
                dosha_effect,
                "aggravates" if dosha_effect else None,
                "moderate" if boundary.erosion_score > 0.3 else "mild",
                "email_signal",
            )
        except Exception as e:
            LOGGER.warning("[EmailIntegration] Failed to log behavior: %s", e)

    # Log cognitive overload if high risk
    if cognitive_load.overwhelm_risk in ("moderate", "high"):
        try:
            await dbexec(
                """
                INSERT INTO behavior_log (
                    person_id, behavior_type, behavior_name, occurred_at,
                    dosha_effect, effect_direction, intensity, source_type
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                person_id,
                "email_pattern",
                "cognitive_overload",
                now,
                "vata",  # Overload tends to scatter attention
                "aggravates",
                cognitive_load.overwhelm_risk,
                "email_signal",
            )
        except Exception as e:
            LOGGER.warning("[EmailIntegration] Failed to log behavior: %s", e)


# =============================================================================
# Signal Retrieval
# =============================================================================

async def get_stored_signals(person_id: str) -> Dict[str, Any]:
    """Retrieve stored signals for a user."""
    rows = await dbfetch(
        """
        SELECT signal_type, signal_data, confidence, extracted_at
        FROM email_signals
        WHERE person_id = $1
        ORDER BY extracted_at DESC
        """,
        person_id,
    )

    if not rows:
        return {"status": "no_signals"}

    # Get extracted_at from the first row
    extracted_at = rows[0].get("extracted_at") if rows else None

    result = {
        "status": "loaded",
        "extracted_at": extracted_at.isoformat() if extracted_at else None,
        "subscriptions": [],
        "avoidance": [],
        "boundary": None,
        "cognitive_load": None,
    }

    import json as _json

    for row in rows:
        signal_type = row["signal_type"]
        data = row["signal_data"]
        # asyncpg returns JSONB as strings; parse if needed
        if isinstance(data, str):
            data = _json.loads(data)

        if signal_type == SignalType.SUBSCRIPTION.value:
            result["subscriptions"].append(data)
        elif signal_type == SignalType.AVOIDANCE.value:
            result["avoidance"].append(data)
        elif signal_type == SignalType.BOUNDARY_EROSION.value:
            result["boundary"] = data
        elif signal_type == SignalType.COGNITIVE_LOAD.value:
            result["cognitive_load"] = data

    return result


# =============================================================================
# Conversation Context
# =============================================================================

async def get_email_context_for_conversation(
    person_id: str,
    *,
    include_details: bool = False,
) -> Optional[str]:
    """
    Get email-derived context for conversation.

    This provides context to the conversation engine about
    email patterns that might be relevant.

    Args:
        person_id: User ID
        include_details: Include specific details vs summary

    Returns:
        Context string or None if no relevant signals
    """
    signals = await get_stored_signals(person_id)

    if signals.get("status") != "loaded":
        return None

    context_parts = []

    # Avoidance patterns (most actionable)
    avoidance = signals.get("avoidance", [])
    if avoidance:
        significant = [a for a in avoidance if a.get("severity") in ("moderate", "significant")]
        if significant:
            if include_details:
                for a in significant[:2]:
                    days = a.get("duration_days", 0)
                    subject = a.get("subject", "")[:50]
                    context_parts.append(
                        f"- Email thread '{subject}...' awaiting reply for {days} days"
                    )
            else:
                context_parts.append(
                    f"- {len(significant)} email thread(s) awaiting reply"
                )

    # Boundary erosion
    boundary = signals.get("boundary")
    if boundary:
        erosion = boundary.get("erosion_score", 0)
        if erosion > 0.3:
            pct = int(boundary.get("after_hours_pct", 0) * 100)
            trend = boundary.get("trend", "stable")
            context_parts.append(
                f"- Email boundary erosion: {pct}% after-hours (trend: {trend})"
            )

    # Cognitive load
    load = signals.get("cognitive_load")
    if load:
        risk = load.get("overwhelm_risk", "low")
        if risk in ("moderate", "high"):
            active = load.get("active_threads", 0)
            context_parts.append(
                f"- Email cognitive load: {risk} ({active} active threads)"
            )

    if not context_parts:
        return None

    return "Email patterns:\n" + "\n".join(context_parts)


# =============================================================================
# Conversational Surfacing
# =============================================================================

async def get_surfaceable_insight(
    person_id: str,
) -> Optional[Dict[str, Any]]:
    """
    Get a single insight worth surfacing in conversation.

    This is called when Sakhi wants to proactively mention
    something email-related.

    Returns:
        Dict with insight type and suggested phrasing, or None
    """
    signals = await get_stored_signals(person_id)

    if signals.get("status") != "loaded":
        return None

    # Priority 1: Significant avoidance
    avoidance = signals.get("avoidance", [])
    significant_avoidance = [
        a for a in avoidance
        if a.get("severity") in ("moderate", "significant") and a.get("follow_up_count", 0) >= 1
    ]
    if significant_avoidance:
        top = significant_avoidance[0]
        return {
            "type": "avoidance",
            "data": top,
            "suggested_phrasing": (
                f"I noticed there's an email thread that's been waiting "
                f"for {top.get('duration_days', 0)} days. "
                f"Sometimes those background things add to mental load. "
                f"Want to look at it?"
            ),
        }

    # Priority 2: Boundary erosion with worsening trend
    boundary = signals.get("boundary")
    if boundary:
        if boundary.get("erosion_score", 0) > 0.4 and boundary.get("trend") == "worsening":
            pct = int(boundary.get("after_hours_pct", 0) * 100)
            return {
                "type": "boundary",
                "data": boundary,
                "suggested_phrasing": (
                    f"I've noticed your after-hours email activity is up this week "
                    f"({pct}% of emails outside work hours). That can affect rest. "
                    f"Would it help to talk about boundaries?"
                ),
            }

    # Priority 3: High cognitive load
    load = signals.get("cognitive_load")
    if load and load.get("overwhelm_risk") == "high":
        heavy = load.get("heavy_threads", 0)
        return {
            "type": "cognitive_load",
            "data": load,
            "suggested_phrasing": (
                f"Your email load looks pretty heavy right now "
                f"({heavy} complex threads). That can be draining. "
                f"Is there anything I can help you process or prioritize?"
            ),
        }

    # Priority 4: Subscription review (less urgent)
    subscriptions = signals.get("subscriptions", [])
    marketing_subs = [s for s in subscriptions if s.get("is_marketing")]
    if len(marketing_subs) > 10:
        return {
            "type": "subscriptions",
            "data": {"count": len(marketing_subs)},
            "suggested_phrasing": (
                f"I've noticed you receive newsletters from about {len(marketing_subs)} sources. "
                f"Would you like to review which ones are still useful?"
            ),
        }

    return None


# =============================================================================
# Friction Framework Integration
# =============================================================================

async def get_email_friction_contribution(
    person_id: str,
) -> Optional[Dict[str, Any]]:
    """
    Get email's contribution to current friction state.

    Used by friction framework to incorporate email signals.

    Returns:
        Dict with friction type and confidence, or None
    """
    signals = await get_stored_signals(person_id)

    if signals.get("status") != "loaded":
        return None

    contributions = []

    # Boundary erosion → Chaos or Intensity friction
    boundary = signals.get("boundary")
    if boundary:
        impact = boundary.get("friction_impact")
        if impact:
            contributions.append({
                "source": "email_boundary",
                "friction_type": impact,
                "confidence": boundary.get("confidence", 0.5) * boundary.get("erosion_score", 0),
                "reason": f"After-hours email activity ({int(boundary.get('after_hours_pct', 0) * 100)}%)",
            })

    # Cognitive overload → Chaos friction
    load = signals.get("cognitive_load")
    if load and load.get("overwhelm_risk") in ("moderate", "high"):
        score = load.get("load_score", 0)
        contributions.append({
            "source": "email_load",
            "friction_type": "chaos_friction",
            "confidence": load.get("confidence", 0.5) * score,
            "reason": f"Email cognitive load ({load.get('overwhelm_risk')} risk)",
        })

    # Avoidance → subtle Kapha (stagnation) or Vata (anxiety about pending)
    avoidance = signals.get("avoidance", [])
    if avoidance:
        total_days = sum(a.get("duration_days", 0) for a in avoidance)
        if total_days > 30:
            contributions.append({
                "source": "email_avoidance",
                "friction_type": "chaos_friction",  # Avoidance creates mental churn
                "confidence": 0.4,
                "reason": f"Email threads awaiting reply ({len(avoidance)} threads, {total_days} total days)",
            })

    if not contributions:
        return None

    # Return strongest contribution
    contributions.sort(key=lambda c: c["confidence"], reverse=True)
    return contributions[0]


__all__ = [
    "extract_all_signals",
    "get_stored_signals",
    "get_email_context_for_conversation",
    "get_surfaceable_insight",
    "get_email_friction_contribution",
]
