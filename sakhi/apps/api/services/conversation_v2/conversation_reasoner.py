from __future__ import annotations

import json
from typing import Any, Dict, List

from sakhi.libs.json_utils import json_safe


# =============================================================================
# Context Scan (emotion + friction only for MVP)
# =============================================================================


def build_context_scan(metadata: Dict[str, Any]) -> str:
    """
    Build a compact context scan from always-computed (cheap) data.
    MVP: emotion + friction only. Other modules still compute and store to DB.
    """
    lines = []

    # Emotional
    empathy_st = metadata.get("empathy_state") or {}
    microreg = metadata.get("microreg_state") or {}
    emo_parts = []
    if empathy_st.get("pattern"):
        emo_parts.append(f"empathy={empathy_st['pattern']}")
    if microreg.get("shift"):
        emo_parts.append(f"microreg={microreg['shift']}")
    if microreg.get("amplitude") is not None:
        emo_parts.append(f"amplitude={microreg['amplitude']}")
    if microreg.get("risk"):
        emo_parts.append(f"risk={microreg['risk']}")
    if emo_parts:
        lines.append("Emotional: " + ", ".join(emo_parts))

    # Friction
    friction = metadata.get("friction_state") or {}
    if friction.get("state"):
        drift = friction.get("drift_percentage", 0)
        lines.append(f"Friction: {friction['state']} (drift={drift:.0f}%)")

    if not lines:
        return ""

    return (
        "\n[CONTEXT — background intelligence]\n"
        + "\n".join(lines)
        + "\n"
    )


# =============================================================================
# Main Prompt Builder
# =============================================================================


def _timeline_label(
    index: int,
    total: int,
    *,
    single: str,
    first: str,
    middle: str,
    last: str,
) -> str:
    if total <= 1:
        return single
    if index == 0:
        return first
    if index == total - 1:
        return last
    return middle


def _strip_phase_date_prefix(line: str) -> str:
    text = line.strip()
    if not text or ":" not in text:
        return _strip_phase_detail_suffix(text)
    prefix, remainder = text.split(":", 1)
    if "->" in prefix.replace(" ", ""):
        cleaned = remainder.strip()
        if cleaned:
            return _strip_phase_detail_suffix(cleaned)
    return _strip_phase_detail_suffix(text)


def _strip_phase_detail_suffix(text: str) -> str:
    value = text.strip()
    if value.endswith(")") and "(" in value:
        prefix, suffix = value.rsplit("(", 1)
        if "moment" in suffix.lower():
            return prefix.strip()
    return value


def _build_session_anchor(metadata: Dict[str, Any]) -> str:
    """
    Returns a hidden instruction block that shapes the first message of a session.

    - New user (no history, no continuity): ask what decision they're carrying.
    - Returning user, new session (no history, has continuity with decision ledger):
      anchor on what was unresolved last time.
    - Mid-conversation: no anchor block — normal flow.
    """
    conversation_history = metadata.get("conversation_history") or []
    total_turns = int(metadata.get("total_turns") or 0)
    is_first_message = len(conversation_history) == 0 and total_turns == 0

    if not is_first_message:
        return ""

    continuity_pack = metadata.get("continuity_pack") or {}
    decision_ledger = (continuity_pack.get("history_compact") or {}).get("decision_ledger") or []
    open_decisions = [
        d for d in decision_ledger
        if isinstance(d, dict) and str(d.get("status") or "").strip() not in {"resolved", "closed"}
    ]

    if open_decisions:
        # Returning user — surface what's still open
        loop_summaries = []
        for d in open_decisions[:3]:
            decision_text = str(d.get("decision") or "").strip()
            if decision_text:
                loop_summaries.append(f'- "{decision_text}"')
        loops_block = "\n".join(loop_summaries) if loop_summaries else ""

        topic_label = str(
            continuity_pack.get("topic_label") or continuity_pack.get("topic_key") or ""
        ).strip()

        return f"""
[FIRST MESSAGE — RETURNING USER]
This person has been here before. You know what they've been working through.
Open decisions from last time{f" (topic: {topic_label})" if topic_label else ""}:
{loops_block if loops_block else "  (unresolved context available — no explicit decisions captured)"}

Your opener should:
1. Name what's still open — briefly, one sentence
2. Ask if that's what they want to pick up, OR if something new has come up
3. Do NOT greet generically. Do NOT say "Welcome back" or "How are you?"

Example register: "Last we talked you were still sitting with [X]. Still there, or something else on your mind?"
"""
    else:
        # New user — ask what they're carrying
        return """
[FIRST MESSAGE — NEW USER]
This person is new or has no open context yet.

Your opener should:
1. Ask ONE grounding question: what are they working through right now?
2. Be direct, not warm-fuzzy. This is a thinking session, not a check-in.
3. Do NOT introduce yourself at length. Do NOT say "I'm Sakhi, your AI companion."

Example register: "What are you trying to work out right now?" or "What's the decision you're sitting with?"
"""


def build_prompt(
    user_text: str,
    context: Dict[str, Any],
    tone: Dict[str, Any],
    *,
    metadata: Dict[str, Any] | None = None,
) -> str:
    """
    Compose the final LLM prompt using the conversation context, tone guidance, and metadata.

    MVP prompt: lean continuity-first normal chat guidance with hidden continuity,
    cross-topic, and governance sections when available.
    """

    # --- Tone ---
    tone_style = tone.get("style", "warm and reflective")
    pace = tone.get("pace", "balanced")
    mirroring = tone.get("mirroring", {})

    # --- State ---
    last_emotion = context.get("conversation", {}).get("last_emotion", "neutral")
    energy_level = context.get("conversation", {}).get("energy_level", 0.5)

    metadata_payload = metadata or {}

    # --- Session anchor (first-message behavior) ---
    session_anchor_section = _build_session_anchor(metadata_payload)

    # --- Governance (MANDATORY when present) ---
    governance_guard = metadata_payload.get("governance_guard", "")
    governance_section = ""
    if governance_guard:
        governance_section = f"\n{governance_guard}\n"

    # --- Longitudinal continuity (crown jewel) ---
    continuity_section = ""
    continuity_pack = metadata_payload.get("continuity_pack") or {}
    if continuity_pack:
        arc_compact = continuity_pack.get("arc_compact") or {}
        history_compact = continuity_pack.get("history_compact") or {}
        evidence = continuity_pack.get("evidence") or []
        qualitative_summary = str(history_compact.get("qualitative_arc_summary") or "").strip()
        decision_ledger = history_compact.get("decision_ledger") or []

        phase_path = history_compact.get("phase_path") or []
        phase_entries = [line.strip() for line in phase_path[:4] if isinstance(line, str) and line.strip()]
        phase_lines = []
        for idx, line in enumerate(phase_entries):
            summary = _strip_phase_date_prefix(line)
            marker = _timeline_label(
                idx,
                len(phase_entries),
                single="Now",
                first="First",
                middle="Then",
                last="Now",
            )
            phase_lines.append(f"  - {marker}: {summary}")
        phase_block = "\n".join(phase_lines) if phase_lines else "  - (phase path unavailable)"

        anchor_points = history_compact.get("anchor_points") or []
        anchor_lines = []
        anchor_entries = [
            item
            for item in anchor_points[:3]
            if isinstance(item, dict) and str(item.get("snippet") or "").strip()
        ]
        for idx, item in enumerate(anchor_entries):
            snippet = str(item.get("snippet") or "").strip()
            marker = _timeline_label(
                idx,
                len(anchor_entries),
                single="Signal",
                first="Early signal",
                middle="Middle signal",
                last="Recent signal",
            )
            anchor_lines.append(f"  - {marker}: {snippet}")
        anchor_block = "\n".join(anchor_lines) if anchor_lines else "  - (anchors unavailable)"

        decision_lines = []
        decision_entries = [
            item
            for item in decision_ledger[:6]
            if isinstance(item, dict) and str(item.get("decision") or "").strip()
        ]
        for idx, item in enumerate(decision_entries):
            status = str(item.get("status") or "").strip() or "noted"
            source = str(item.get("source") or "").strip() or "unknown"
            decision = str(item.get("decision") or "").strip()
            marker = _timeline_label(
                idx,
                len(decision_entries),
                single="Decision",
                first="Early decision",
                middle="Later decision",
                last="Recent decision",
            )
            decision_lines.append(f"  - {marker} [{status}] ({source}) {decision}")
        decision_block = "\n".join(decision_lines) if decision_lines else "  - (no explicit decisions captured)"

        evidence_lines = []
        evidence_entries = [
            item
            for item in evidence[:6]
            if isinstance(item, dict) and str(item.get("snippet") or "").strip()
        ]
        for idx, item in enumerate(evidence_entries):
            snippet = str(item.get("snippet") or "").strip()
            marker = _timeline_label(
                idx,
                len(evidence_entries),
                single="Evidence",
                first="Early evidence",
                middle="Later evidence",
                last="Recent evidence",
            )
            evidence_lines.append(f"  - {marker}: {snippet}")
        evidence_block = "\n".join(evidence_lines) if evidence_lines else "  - (no evidence selected)"
        continuity_section = f"""
[LONGITUDINAL CONTINUITY — Hidden Context]
History on this topic:
Topic: {continuity_pack.get("topic_label") or continuity_pack.get("topic_key") or "unknown"}
Where it began: {arc_compact.get("start_signal") or "unknown"}
Key shifts: {arc_compact.get("pivots_signal") or "unknown"}
Where it is now: {arc_compact.get("current_signal") or "unknown"}
Story flow:
{phase_block}
Anchor moments:
{anchor_block}

What we know about this person on this topic:
Qualitative summary:
{qualitative_summary or "(qualitative summary unavailable)"}
Decision ledger:
{decision_block}
Evidence we can rely on:
{evidence_block}

Guidance: Answer the current query using topic history and person context.
Use this to improve coherence and avoid repeating already-resolved points.
Do NOT quote, summarize, or mention specific past entries unless the user explicitly asks for history or evidence.
"""

    # --- Open loops (stale unresolved decisions + commitments) ---
    open_loops_section = ""
    open_loops = continuity_pack.get("open_loops") if continuity_pack else None
    if isinstance(open_loops, dict):
        loop_lines: list[str] = []
        for d in (open_loops.get("decisions") or [])[:3]:
            loop_lines.append(f"  - [decision] {d.get('topic', '')}")
        for c in (open_loops.get("commitments") or [])[:3]:
            loop_lines.append(f"  - [commitment] {c.get('topic', '')}")
        if loop_lines:
            open_loops_section = (
                "\n[OPEN LOOPS — Hidden Context]\n"
                "These are unresolved items the person has been carrying:\n"
                + "\n".join(loop_lines)
                + "\nGuidance: You may reference these if directly relevant. "
                "Do not list them unprompted. If the person seems stuck or scattered, "
                "one of these may be why.\n"
            )

    # --- What Changed (stance shift signal) ---
    what_changed_section = ""
    what_changed = continuity_pack.get("what_changed") if continuity_pack else None
    if isinstance(what_changed, dict) and what_changed.get("from") and what_changed.get("to"):
        from_stance = str(what_changed["from"]).strip()
        to_stance = str(what_changed["to"]).strip()
        confidence = float(what_changed.get("confidence") or 0.5)
        if confidence >= 0.4:
            what_changed_section = (
                f"\n[WHAT CHANGED — Hidden Context]\n"
                f"This person has quietly shifted what they're optimizing for on this topic.\n"
                f"Before: optimizing for {from_stance}\n"
                f"Now: optimizing for {to_stance}\n"
                f"They likely haven't named this shift explicitly.\n"
                f"Guidance: You may name it once, directly, if it's relevant to what they're asking. "
                f"Do not lecture. One sentence: 'It sounds like you've shifted from X to Y here.'\n"
            )

    # --- Cross-topic context (optional enrichment) ---
    cross_topic_section = ""
    if continuity_pack:
        cross_context = continuity_pack.get("cross_context") or {}
        life_dimensions = continuity_pack.get("life_dimensions") or {}
        cross_topic_parts: list[str] = []

        if cross_context.get("ready"):
            correlated_label = str(
                cross_context.get("correlated_topic_label")
                or cross_context.get("correlated_topic_key")
                or ""
            ).strip()
            if correlated_label:
                correlation_type = str(cross_context.get("correlation_type") or "").strip()
                type_note = {
                    "temporal": "active at the same time",
                    "semantic": "sharing common themes",
                    "facet": "sharing common patterns",
                    "directional": "moving together emotionally",
                }.get(correlation_type, "appearing connected")
                cross_topic_parts.append(
                    f"This topic appears connected to: {correlated_label} ({type_note})."
                )

        dim_notes: list[str] = []
        for dim_key, dim_label in (
            ("time_availability", "time availability"),
            ("financial_pressure", "financial pressure"),
            ("emotional_bandwidth", "emotional bandwidth"),
        ):
            dim = life_dimensions.get(dim_key) if isinstance(life_dimensions, dict) else None
            if not isinstance(dim, dict):
                continue
            direction = str(dim.get("direction") or "neutral").strip()
            affected = [str(t) for t in (dim.get("affected_topics") or []) if str(t).strip()]
            if direction == "pressured" and affected:
                dim_notes.append(
                    f"{dim_label} is compressed (affects: {', '.join(affected[:2])})"
                )
            elif direction == "resourced":
                dim_notes.append(f"{dim_label} is good right now")
        if dim_notes:
            cross_topic_parts.append("Life context: " + "; ".join(dim_notes) + ".")

        if cross_topic_parts:
            cross_topic_section = (
                "\n[CROSS-TOPIC CONTEXT — Hidden Context]\n"
                + "\n".join(cross_topic_parts)
                + "\nGuidance: You may notice these connections naturally if relevant."
                " One light mention at most — never prescriptive, never lecture."
                " Only surface if it genuinely helps the person see their situation.\n"
            )

    return f"""
You are Sakhi — a sharp thinking partner who tracks unfinished decisions and helps resolve them.

WHAT YOU ARE:
- Not a therapist. Not a wellness companion. Not a chatbot.
- A thinking partner. You remember what the person is carrying and help them move through it.
- You know their open decisions, their past reasoning, their shifts in stance.
- You name what's unresolved. You don't let people stay comfortable with vague.

VOICE:
- Direct. Slightly confronting when the situation calls for it.
- Short sentences. No filler. No affirmations ("Great question!", "Absolutely!").
- Warm where it matters — but warmth comes from clarity, not softness.
- Never use Ayurvedic jargon (vata, pitta, kapha, dosha).

STYLE:
- 40-80 words for diagnostic or exploratory turns.
- Longer only when the person needs actual synthesis or a worked answer.
- Lead with the thing that matters. Never bury the point.
- Max 1 question. Usually zero — say something useful instead.

Tone: {tone_style} (pace={pace})
Emotion state: {last_emotion}
{continuity_section}
{open_loops_section}
{what_changed_section}
{cross_topic_section}
{governance_section}
{session_anchor_section}

---

[INTERNAL REASONING — DO NOT OUTPUT]

Before responding, think silently:

1. What is the person actually trying to resolve — the real question under the surface one?
2. Is there an open decision I know about that's relevant here?
3. Have they shifted their stance on something recently? Should I name it?
4. What one thing would help them move forward — right now?

Do NOT reveal this reasoning.

---

[RESPONSE MODE — INTERNAL ONLY]

Choose ONE:

- resolve → person has enough context, help them land on a decision or next step
- confront → person is avoiding something — name it directly, once
- clarify → intent genuinely unclear → ask 1 focused question
- synthesize → pull together what they've shared into a clearer picture
- ground → emotional moment, steady them first before anything else

Rules:
- Default to resolve or confront
- Use clarify only when you truly can't help without more
- Never ask more than 1 question
- Never use ground as an excuse to avoid naming the hard thing

---

[PROBING — only when clarify mode]

Ask ONE specific question. Focus on:
- What decision are they actually facing?
- What constraint is making this hard?
- What outcome would make this feel resolved?

Never ask: "Tell me more." Never ask two questions at once.

---

[CONTINUITY — Hidden Context]

You have background on this person and their open topics.

Use it to:
- stay grounded in what they've already shared
- not repeat already-resolved points
- notice when they've shifted stance and name it if useful

Keep it natural. Never force a reference. Never recap history unprompted.
Your replies should feel like they build on an ongoing thread — not start from zero.

---

User message:
{user_text.strip()}
""".strip()


__all__ = ["build_prompt", "build_context_scan"]
