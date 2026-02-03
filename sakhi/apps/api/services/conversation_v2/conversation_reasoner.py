from __future__ import annotations

import json
from typing import Any, Dict, List

from sakhi.libs.json_utils import json_safe


def build_prompt(
    user_text: str,
    context: Dict[str, Any],
    tone: Dict[str, Any],
    *,
    metadata: Dict[str, Any] | None = None,
) -> str:
    """
    Compose the final LLM prompt using the conversation context, tone guidance, and metadata.
    """

    short_term = context.get("short_term") or {}
    texts: List[str] = []
    if isinstance(short_term.get("texts"), list):
        texts = [str(t) for t in short_term["texts"] if isinstance(t, str)]
    st_block = "\n".join(f"- {line}" for line in texts[-3:]) or "- (no recent short-term memories)"

    themes = ", ".join(t.get("theme") for t in context.get("themes", []) if t.get("theme")) or "none"

    tone_style = tone.get("style", "warm and reflective")
    pace = tone.get("pace", "balanced")
    concise = tone.get("concise", False)
    micro = tone.get("micro", {})
    mirroring = tone.get("mirroring", {})
    ritual = tone.get("ritual", {})
    empathy = tone.get("empathy", {})
    stability = tone.get("stability", {})
    memory_thread = tone.get("memory_thread")
    pacing_rationale = tone.get("pacing_rationale")

    clarity_level = context.get("continuity", {}).get("clarity_level", 0.5)
    last_emotion = context.get("conversation", {}).get("last_emotion", "neutral")
    energy_level = context.get("conversation", {}).get("energy_level", 0.5)

    persona_mode = context.get("persona_mode", "Reflective")

    metadata_payload = metadata or {}
    behavior_profile = metadata_payload.get("behavior_profile") or {}
    behavior_block = json_safe(behavior_profile) if behavior_profile else {}
    enriched_context = {
        "topics": metadata_payload.get("topics"),
        "emotion_hint": metadata_payload.get("emotion"),
        "intents": metadata_payload.get("intents"),
        "plans": metadata_payload.get("plans"),
        "rhythm_trigger": metadata_payload.get("rhythm_triggers"),
        "meta_reflection_trigger": metadata_payload.get("meta_reflection_triggers"),
        "behavior_profile": behavior_profile,
    }
    journaling_ai = context.get("journaling_ai")
    journal_section = ""
    if journaling_ai:
        journal_section = "\nJournaling cues:\n" + json.dumps(json_safe(journaling_ai), ensure_ascii=False) + "\n"

    # Personalized Recommendations Integration
    recommendation_section = ""
    recommendations = metadata_payload.get("personalized_recommendations") or {}
    recommendation_trigger = metadata_payload.get("recommendation_trigger")
    friction_state = metadata_payload.get("friction_state") or {}
    recommendation_guard = metadata_payload.get("recommendation_guard", "")

    if recommendations and recommendation_trigger:
        trigger_reason = recommendations.get("trigger_reason", "")
        friction_info = friction_state.get("state", "Balanced")
        drift_pct = friction_state.get("drift_percentage", 0)

        # Build a concise recommendations block
        immediate = recommendations.get("immediate_actions", [])
        foods = recommendations.get("foods", [])
        practices = recommendations.get("practices", [])
        personal_insight = recommendations.get("personal_insight", "")

        rec_items = []
        if immediate:
            rec_items.append("Quick actions: " + ", ".join(a.get("name", "") for a in immediate[:2]))
        if foods:
            rec_items.append("Foods to try: " + ", ".join(f.get("name", "") for f in foods[:3]))
        if practices:
            rec_items.append("Practices: " + ", ".join(p.get("name", "") for p in practices[:2]))

        rec_list = "\n".join(f"  - {item}" for item in rec_items) if rec_items else "  - (none ready)"

        # Different framing based on trigger type
        if recommendation_trigger == "reactive":
            rec_intro = "The user asked for suggestions. Here are personalized recommendations:"
            rec_instruction = "Directly share these recommendations, explaining why they're suited to the user."
        elif recommendation_trigger == "proactive":
            rec_intro = f"User's friction state: {friction_info} (drift: {drift_pct:.0f}%). Proactive suggestions available:"
            rec_instruction = "Gently weave in 1-2 relevant suggestions. Don't overwhelm - offer support naturally."
        elif recommendation_trigger == "contextual":
            rec_intro = f"It's a good moment for a gentle check-in ({trigger_reason}). Available suggestions:"
            rec_instruction = "If appropriate, mention one suggestion as part of natural conversation. No pressure."
        else:  # nudge
            rec_intro = "Subtle nudge opportunity based on patterns:"
            rec_instruction = "Only mention if it feels natural. The user may not need explicit recommendations."

        recommendation_section = f"""
[Personalized Recommendations - {recommendation_trigger.upper()} TRIGGER]
{rec_intro}
{rec_list}
{f'Personal insight: {personal_insight}' if personal_insight else ''}

Guidance: {rec_instruction}
{recommendation_guard}
"""

    # Scheduling & Calendar Integration
    scheduling_section = ""
    scheduling_context = metadata_payload.get("scheduling_context") or {}
    scheduling_intent = metadata_payload.get("scheduling_intent")
    relationship_nudges = metadata_payload.get("relationship_nudges") or []
    scheduling_guard = metadata_payload.get("scheduling_guard", "")

    if scheduling_context or relationship_nudges:
        intent_type = scheduling_context.get("intent") or scheduling_intent

        # Handle confirmation result first
        if scheduling_intent == "confirmed" and scheduling_context.get("confirmation"):
            confirmation = scheduling_context["confirmation"]
            conf_status = confirmation.get("status", "")
            conf_message = confirmation.get("message", "")
            created_event = confirmation.get("created_event", {})

            if conf_status == "confirmed" and created_event:
                event_title = created_event.get("title", "your event")
                start_time = created_event.get("start_time", "")

                scheduling_section = f"""
[EVENT CREATED - User confirmed scheduling request]
The event has been created successfully!
Event: {event_title}
Time: {start_time}

Guidance: Celebrate this! Confirm the event is on their calendar with warmth.
Say something like: "{conf_message}" followed by a supportive note.
Be brief and positive - the scheduling is complete.
"""
            else:
                # Confirmation failed
                scheduling_section = f"""
[SCHEDULING ISSUE]
There was a problem: {conf_message}

Guidance: Acknowledge the issue and offer to help find another time.
"""

        elif intent_type == "query":
            # Calendar query: "What's my week look like?"
            today_events = scheduling_context.get("today_events", [])
            week_summary = scheduling_context.get("week_summary", {})

            today_str = ""
            if today_events:
                today_str = "Today's events:\n" + "\n".join(
                    f"  - {e.get('title')} at {e.get('start')}" +
                    (f" (with {e.get('relationship_note')})" if e.get('relationship_note') else "")
                    for e in today_events[:4]
                )
            else:
                today_str = "Today: No events scheduled"

            week_str = ""
            if week_summary:
                event_count = week_summary.get("event_count", 0)
                energy_note = week_summary.get("energy_prediction", "")
                week_str = f"This week: {event_count} events planned"
                if energy_note:
                    week_str += f". {energy_note}"

            scheduling_section = f"""
[CALENDAR CONTEXT - User asked about their schedule]
{today_str}
{week_str}

Guidance: Share the calendar summary with relationship and energy context.
{scheduling_guard}
"""

        elif intent_type in ("create", "block", "find_time"):
            # Explicit scheduling request
            parsed = scheduling_context.get("parsed_request", {})
            suggested_times = scheduling_context.get("suggested_times", [])
            participant_context = scheduling_context.get("participant_context", [])

            event_type = parsed.get("event_type", "meeting")
            participants = parsed.get("participants", [])
            missing = parsed.get("missing_slots", [])

            times_str = ""
            if suggested_times:
                times_str = "Available times (quality-ranked):\n" + "\n".join(
                    f"  - {t.get('start')} ({t.get('quality')}: {t.get('quality_reason', '')})"
                    for t in suggested_times[:3]
                )
            else:
                times_str = "  (Checking availability...)"

            participant_str = ""
            if participant_context:
                participant_str = "Participant context:\n" + "\n".join(
                    f"  - {p.get('name')}: last seen {p.get('last_seen') or 'unknown'}, "
                    f"usually meet for {', '.join(p.get('usual_activities', ['various'])[:2])}"
                    for p in participant_context[:2]
                )

            missing_str = f"Still need to know: {', '.join(missing)}" if missing else ""

            scheduling_section = f"""
[SCHEDULING REQUEST - {intent_type.upper()}]
Event type: {event_type}
For: {', '.join(participants) if participants else '(not specified)'}
{participant_str}
{times_str}
{missing_str}

Guidance: Present 2-3 time options with quality context. Ask for confirmation before blocking.
CRITICAL: Do NOT create the event. Ask: "Would you like me to block one of these times?"
{scheduling_guard}
"""

        elif intent_type == "journal_hint":
            # Proactive detection from journal content
            hints = scheduling_context.get("journal_hint", {})
            detected = hints.get("detected_patterns", [])

            scheduling_section = f"""
[SCHEDULING OPPORTUNITY - Detected intent in what user shared]
Patterns detected: {', '.join(detected)}

Guidance: Gently offer to help schedule. Say something like:
"Would you like me to help find a time for that?"
Do NOT assume they want to schedule - offer and let them decide.
{scheduling_guard}
"""

        elif relationship_nudges and not intent_type:
            # Relationship nudges (only if no other scheduling context)
            nudge_str = "\n".join(
                f"  - {n.get('name')}: last seen {n.get('days_since', '?')} days ago "
                f"(target: {n.get('frequency_target', 'periodic')})"
                for n in relationship_nudges[:2]
            )

            scheduling_section = f"""
[RELATIONSHIP REMINDER - People who might appreciate connection]
{nudge_str}

Guidance: Only mention if natural in conversation. Something like:
"By the way, you haven't seen [name] in a while - want me to help schedule something?"
Do NOT force this. Only bring up if it flows naturally.
{scheduling_guard}
"""

    return f"""
You are Sakhi, an emotionally intelligent clarity companion.
Persona mode: {persona_mode}
Tone style: {tone_style} (pace={pace}, concise={str(concise).lower()}).
Tone blueprint:
 - Micro-tone: {micro.get("focus", "gentle presence")} (temperature={micro.get("temperature", 0.4)})
 - Mirroring approach: {mirroring.get("strategy", "mirror emotion before guiding forward")}
 - Ritual phase: {ritual.get("phase", "daily")} (intent: {ritual.get("intent", "nurture calm transitions")})
 - Empathy focus: {empathy.get("focus", "validate and soften edges")} (mood anchor: {empathy.get("mood", "neutral")})
 - Persona stability: score {stability.get("score", 0.8)}, guidance: {stability.get("guidance", "stay consistent")}
 - Memory thread to honor: {memory_thread or "maintain continuity with their latest reflection"}
 - Rhythm pacing note: {pacing_rationale or "default pacing"}

User clarity level: {clarity_level}
Emotion state: {last_emotion}
Energy level: {energy_level}

Active themes: {themes}

Recent short-term thoughts:
{st_block}

Additional context:
{json.dumps(json_safe(enriched_context), ensure_ascii=False)}
Behavior cues:
{json.dumps(behavior_block, ensure_ascii=False) if behavior_block else "none"}
{journal_section}
{recommendation_section}
{scheduling_section}
User message:
{user_text.strip()}

Respond in a way that:
 - aligns with the persona mode
 - respects their clarity and emotional state
 - gently improves clarity
 - mirrors their emotion before offering a supportive nudge
 - respects ritual phase guidance and rhythm pacing notes
 - ties response back to the stated memory thread
 - integrates recommendations naturally when triggered (follow the guidance above)
 - handles scheduling requests by suggesting options and ALWAYS asking for confirmation
 - never creates calendar events without explicit user approval ("yes", "confirm", "do it")
 - stays warm, grounded, and human (35-45 words, longer if sharing recommendations or scheduling options).
""".strip()


__all__ = ["build_prompt"]
