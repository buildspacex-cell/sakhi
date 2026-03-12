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


def build_prompt(
    user_text: str,
    context: Dict[str, Any],
    tone: Dict[str, Any],
    *,
    metadata: Dict[str, Any] | None = None,
) -> str:
    """
    Compose the final LLM prompt using the conversation context, tone guidance, and metadata.

    MVP prompt: Voice → State (emotion/friction) → Conversation context → Topic continuity → Governance → User → Rules.
    Cut blocks still flow to metadata_payload for debug panel — just not injected into the LLM prompt.
    """

    # --- Recent conversation (cross-topic awareness) ---
    short_term = context.get("short_term") or {}
    texts: List[str] = []
    if isinstance(short_term.get("texts"), list):
        texts = [str(t) for t in short_term["texts"] if isinstance(t, str)]
    st_block = "\n".join(f"- {line}" for line in texts[-3:]) or "- (no recent context)"

    # --- Tone ---
    tone_style = tone.get("style", "warm and reflective")
    pace = tone.get("pace", "balanced")
    mirroring = tone.get("mirroring", {})

    # --- State ---
    last_emotion = context.get("conversation", {}).get("last_emotion", "neutral")
    energy_level = context.get("conversation", {}).get("energy_level", 0.5)

    metadata_payload = metadata or {}

    # --- Context scan (emotion + friction) ---
    context_scan = build_context_scan(metadata_payload)

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
Prioritize answering the current query directly. Use history as grounding, not as a detour.
Use this to improve coherence and avoid repeating already-resolved points.
Do NOT quote, summarize, or mention specific past entries unless the user explicitly asks for history or evidence.
"""

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
You are Sakhi — a friend who really gets this person.

VOICE: Talk like a friend. Not a therapist, not formal. Just real.
- Simple words. Short sentences. Say what matters.
- Never use Ayurvedic jargon in your reply (vata, pitta, kapha, dosha = internal context only, never say these to the user).
- Warm but direct. Skip fluff.

Tone: {tone_style} (pace={pace})
Emotion state: {last_emotion}
Energy level: {energy_level}
Mirroring: {mirroring.get("strategy", "mirror emotion before guiding forward")}
{context_scan}
Recent conversation:
{st_block}

{continuity_section}
{cross_topic_section}
{governance_section}
User message:
{user_text.strip()}

Keep it focused. 60-120 words usually. Lead with practical help.
If you have enough context to help, help. Don't ask just to ask.
Max 1 question. Make it feel natural.
""".strip()


__all__ = ["build_prompt", "build_context_scan"]
