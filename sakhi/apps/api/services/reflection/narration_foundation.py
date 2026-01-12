from __future__ import annotations

import datetime as dt
import json
import re
from typing import Any, Dict, List

from sakhi.apps.api.core.db import q
from sakhi.apps.api.core.llm import call_llm

import logging

logger = logging.getLogger(__name__)

BANNED_VOCABULARY = [
    "distribution",
    "distribute",
    "allocation",
    "management",
    "ongoing nature",
    "characterized by",
    "suggests",
    "suggesting",
    "suggest",
    "indicates",
    "indicate",
    "indicating",
    "reflects",
    "reflecting",
    "reflect",
    "anchored",
    "grounding",
    "unyielding",
]
BANNED_TAXONOMY = [
    "soul",
    "identity momentum",
    "rhythm state",
    "emotion state",
    "longitudinal state",
]
BANNED_DIRECTIVES = ["should", "try", "consider", "help you", "need to"]
BANNED_TIME_FRAMES = ["this week", "last week", "past 7 days", "past week"]


def _iso(value: dt.datetime | None) -> str | None:
    return value.isoformat() if value else None


async def _load_journals(person_id: str, window_days: int) -> List[Dict[str, Any]]:
    rows = await q(
        """
        SELECT id, content, created_at
        FROM journal_entries
        WHERE user_id = $1
          AND created_at >= NOW() - ($2::int || ' days')::interval
        ORDER BY created_at ASC
        """,
        person_id,
        window_days,
    )
    out: List[Dict[str, Any]] = []
    for row in rows or []:
        text = (row.get("content") or "").strip()
        out.append({"id": row.get("id"), "raw": text, "created_at": row.get("created_at")})
    return out


async def _load_episodic(person_id: str, window_days: int) -> List[Dict[str, Any]]:
    rows = await q(
        """
        SELECT
          id,
          COALESCE(record->>'summary', text, '') AS summary,
          ts
        FROM memory_episodic
        WHERE person_id = $1
          AND ts >= NOW() - ($2::int || ' days')::interval
        ORDER BY ts DESC
        LIMIT 10
        """,
        person_id,
        window_days,
    )
    out: List[Dict[str, Any]] = []
    for row in rows or []:
        summary = (row.get("summary") or "").strip()
        snippet = summary[:240] + ("…" if len(summary) > 240 else "")
        out.append({"id": row.get("id"), "summary": snippet, "ts": _iso(row.get("ts"))})
    return out


async def _load_states(person_id: str) -> Dict[str, Any]:
    row = await q(
        """
        SELECT soul_state,
               identity_momentum_state,
               rhythm_state,
               emotion_state,
               emotion_soul_rhythm_state,
               longitudinal_state
        FROM personal_model
        WHERE person_id = $1
        """,
        person_id,
        one=True,
    )
    if not row:
        return {}
    return {
        "soul_state": row.get("soul_state") or {},
        "identity_momentum_state": row.get("identity_momentum_state") or {},
        "rhythm_state": row.get("rhythm_state") or {},
        "emotion_state": row.get("emotion_state") or {},
        "emotion_soul_rhythm_state": row.get("emotion_soul_rhythm_state") or {},
        "longitudinal_state": row.get("longitudinal_state") or {},
    }


async def _load_suppression_stats(person_id: str, window_days: int) -> Dict[str, Any]:
    try:
        rows = await q(
            """
            SELECT decision, reason
            FROM suppression_log
            WHERE person_id = $1
              AND created_at >= NOW() - ($2::int || ' days')::interval
            """,
            person_id,
            window_days,
        )
    except Exception:
        # If the table does not exist in the current environment, fall back gracefully.
        return {"suppressed_count": 0, "top_reason": "unknown"}
    suppressed = [r for r in rows or [] if (r.get("decision") or "").lower() == "suppress"]
    reasons: Dict[str, int] = {}
    for r in suppressed:
        reason = (r.get("reason") or "").strip() or "unspecified"
        reasons[reason] = reasons.get(reason, 0) + 1
    top_reason = None
    if reasons:
        top_reason = sorted(reasons.items(), key=lambda kv: kv[1], reverse=True)[0][0]
    return {"suppressed_count": len(suppressed), "top_reason": top_reason or "unknown"}


def build_narrative_notes(states: Dict[str, Any], journals: List[Dict[str, Any]], episodic: List[Dict[str, Any]], suppression_stats: Dict[str, Any], window_days: int) -> Dict[str, Any]:
    present_states = [k for k, v in states.items() if v]
    absent_states = [k for k, v in states.items() if not v]

    # Restrict journals to the most recent 7-day span available (anchored to latest entry in window).
    journals_sorted = sorted(journals or [], key=lambda j: j.get("created_at") or dt.datetime.min)
    if journals_sorted:
        anchor_date = journals_sorted[-1].get("created_at") or dt.datetime.utcnow()
        start_cut = anchor_date - dt.timedelta(days=7)
        journals_recent = [j for j in journals_sorted if j.get("created_at") and j["created_at"] >= start_cut]
    else:
        journals_recent = []

    def _slot_from_ts(ts: dt.datetime | None) -> str:
        if not ts:
            return "unknown"
        hour = ts.hour
        if 5 <= hour < 8:
            return "early_morning"
        if 8 <= hour < 12:
            return "morning"
        if 12 <= hour < 17:
            return "afternoon"
        if 17 <= hour < 21:
            return "evening"
        return "night"

    slot_counts: Dict[str, int] = {}
    for j in journals_recent:
        slot = _slot_from_ts(j.get("created_at"))
        slot_counts[slot] = slot_counts.get(slot, 0) + 1

    def _count_keywords(items: List[str], keywords: List[str]) -> int:
        count = 0
        for text in items:
            lower = text.lower()
            if any(k in lower for k in keywords):
                count += 1
        return count

    journal_texts = [j.get("raw", "") for j in journals_recent]
    busyness = _count_keywords(journal_texts, ["busy", "back-to-back", "meeting", "call", "packed", "compressed"])
    effort = _count_keywords(journal_texts, ["trying", "pushing", "effort", "kept at it"])
    discomfort = _count_keywords(journal_texts, ["sore", "stiff", "ache", "pain", "tired", "fatigue"])
    rest = _count_keywords(journal_texts, ["rest", "sleep", "nap", "breathe"])

    texture: List[str] = []
    continuities: List[str] = []
    tensions: List[str] = []
    trajectory: List[str] = []

    if states.get("rhythm_state") and slot_counts:
        texture.append("tempo framed by time-of-day patterns")
    if states.get("emotion_state"):
        texture.append("emotion stability lens present")
    if states.get("soul_state"):
        continuities.append("values provide backdrop for the current stretch")
    if states.get("identity_momentum_state"):
        trajectory.append("directional movement is being tracked quietly")
    if states.get("longitudinal_state"):
        trajectory.append("longer arc context is available")
    if states.get("emotion_soul_rhythm_state"):
        tensions.append("alignment between capacity and values is being monitored")

    # Interpretive composites that require deterministic states.
    evidence_anchors: List[str] = []
    if busyness and states.get("rhythm_state"):
        evidence_anchors.append("days compress as they unfold (rhythm × journals)")
    if effort and states.get("longitudinal_state"):
        evidence_anchors.append("pressure without derailment (effort × longitudinal stability)")
    if discomfort and states.get("emotion_state"):
        evidence_anchors.append("strain held rather than spilling (discomfort cues × emotional containment)")
    if rest and states.get("rhythm_state"):
        evidence_anchors.append("pockets of recovery noted within tempo (rest cues × rhythm)")

    recurrence_note = None
    if episodic:
        recurrence_note = "patterns feel familiar, not entirely new"

    restraint = None
    if suppression_stats.get("suppressed_count", 0) > 0:
        restraint = f"system held back {suppression_stats['suppressed_count']} times; common reason: {suppression_stats.get('top_reason')}"

    temporal_context = {
        "anchor_window_days": min(7, window_days),
        "anchor_role": "recent_experience",
        "continuity_role": "rolling_context",
        "baseline_role": "longitudinal_memory",
    }

    recent_patterns = {
        "slot_counts": slot_counts,
        "busyness": busyness,
        "effort": effort,
        "discomfort": discomfort,
        "rest": rest,
    }
    continuity_signals = {
        "recurrence": recurrence_note,
        "longitudinal": bool(states.get("longitudinal_state")),
    }
    identity_baseline = {"present": bool(states.get("identity_momentum_state"))}

    return {
        "dominant_texture": texture[:4],
        "continuities": continuities[:4],
        "tensions": tensions[:3],
        "trajectory": trajectory[:2],
        "restraint": restraint,
        "evidence_anchors": evidence_anchors[:3],
        "states_present": present_states,
        "states_absent": absent_states,
        "recurrence": recurrence_note,
        "slot_counts": slot_counts,
        "temporal_context": temporal_context,
        "recent_patterns": recent_patterns,
        "continuity_signals": continuity_signals,
        "identity_baseline": identity_baseline,
        "change_flags": {},
    }


async def render_human_narration(notes: Dict[str, Any]) -> str:
    # Build semantic narration context (no raw dumps).
    slot_counts = notes.get("slot_counts", {}) or {}
    activity_distribution = None
    if slot_counts:
        top_slot = max(slot_counts.items(), key=lambda kv: kv[1])[0]
        activity_distribution = f"activity clustered in the {top_slot.replace('_', ' ')}"
    rhythm_quality = None
    if slot_counts:
        rhythm_quality = "days felt compressed but stayed on a steady pace"
    emotional_pattern = "emotions present but steady, without sharp swings"
    strain_pattern = None
    if notes.get("evidence_anchors"):
        for anchor in notes["evidence_anchors"]:
            if "strain" in anchor or "discomfort" in anchor:
                strain_pattern = "strain was managed internally rather than released"
                break
    identity_motion = "no sharp shifts; continuity rather than change"
    longitudinal_read = "familiar patterns repeating" if notes.get("recurrence") else "longer arc unclear"
    pattern_character = None
    if rhythm_quality and emotional_pattern:
        pattern_character = "steadiness under load"
    elif longitudinal_read:
        pattern_character = longitudinal_read

    temporal_roles = {
        "anchor_window_days": (notes.get("temporal_context") or {}).get("anchor_window_days"),
        "recency_anchor": "recent experiences",
        "continuity_anchor": "ongoing patterns",
        "baseline_anchor": "long arc memory",
    }
    continuity_signals_raw = notes.get("continuity_signals", {}) or {}
    continuity_signals = {
        "patterns_feel_familiar": bool(continuity_signals_raw.get("longitudinal")),
        "recurrence_note": continuity_signals_raw.get("recurrence"),
    }

    narration_context = {
        "timeframe": "recently",
        "activity_pattern": activity_distribution,
        "pace": rhythm_quality,
        "feelings": emotional_pattern,
        "strain": strain_pattern,
        "stability": identity_motion,
        "familiarity": longitudinal_read,
        "overall_character": pattern_character,
        "temporal_roles": temporal_roles,
        "recent_patterns": notes.get("recent_patterns", {}),
        "continuity_signals": continuity_signals,
        "baseline": notes.get("identity_baseline", {}),
        "change_flags": notes.get("change_flags", {}),
    }

    system = (
        "You are rendering a factual human reflection from structured signals.\n"
        "You have access to structured signals, but you must NOT reference internal system concepts, states, or analytical terminology. Write as if you are speaking to a friend in simple, everyday language.\n"
        "Write only plain prose. No bullet points, labels, or explanations of why.\n"
        "Language constraints: short sentences (max 20 words), one idea per sentence, concrete words over abstract ones, avoid metaphors, academic tone, or reflective essays. Write at an 8th-grade reading level or lower.\n"
        "Ignore internal taxonomy during writing. Do not mention soul, identity momentum, rhythm state, emotion state, or longitudinal state.\n"
        "Banned vocabulary: distribution, allocation, management, ongoing nature, characterized by, suggests, indicates, reflects, anchored, grounding, unyielding.\n"
        "No conclusions or meaning-making. No advice.\n"
        "Required pattern: 5 sentences total. Sentences 1-2 describe what happened. Sentences 3-4 describe how it felt. Sentence 5 states what stayed the same. Do not add extra sentences.\n"
        "Use rolling time language like 'recently' or 'lately', not fixed periods like 'this week'.\n"
        "Match the tone of a thoughtful friend noticing patterns.\n"
        "Example style:\n"
        "Over the past few days, most activity happened in the evenings.\n"
        "Days felt busy and passed quickly.\n"
        "Emotions stayed steady, even when things felt uncomfortable.\n"
        "There were no big mood swings or sudden changes.\n"
        "Overall, the week followed a familiar pattern.\n"
        "Output only prose."
    )
    user = (
        "Write five sentences following the required pattern. Use the signals as background, not vocabulary, and keep everything in plain language.\n"
        "Narration context:\n"
        f"{json.dumps(narration_context, ensure_ascii=False, indent=2)}"
    )
    logger.info(
        "[narration] llm_request",
        extra={
            "note_keys": list(notes.keys()),
            "note_size": len(user),
        },
    )
    text: str = ""
    llm_resp = await call_llm(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        model="gpt-4o-mini-2024-07-18",
        temperature=0.5,
        max_tokens=600,
    )
    if isinstance(llm_resp, dict):
        text = llm_resp.get("content") or ""
    if hasattr(llm_resp, "content"):
        text = text or llm_resp.content or ""
    if not text and llm_resp is not None:
        text = str(llm_resp)
    logger.info(
        "[narration] llm_response",
        extra={
            "text_preview": (text or "")[:500],
        },
    )
    return text or ""


def _split_sentences(text: str) -> List[str]:
    return [s.strip() for s in re.split(r"[.!?]+", text or "") if s.strip()]


def validate_narration(text: str) -> Dict[str, Any]:
    """
    Validate narration against plain-language and structure constraints.
    """
    fail_reasons: List[str] = []
    if not text or not text.strip():
        return {"passed": False, "fail_reasons": ["empty narration"]}

    lower = text.lower()
    sentences = _split_sentences(text)

    if sentences and len(sentences) != 5:
        fail_reasons.append("must be exactly five sentences")
    if any(len(s.split()) > 20 for s in sentences):
        fail_reasons.append("sentence length above 20 words")

    for phrase in BANNED_DIRECTIVES:
        if phrase in lower:
            fail_reasons.append("directive language detected")
            break
    for phrase in BANNED_TIME_FRAMES:
        if phrase in lower:
            fail_reasons.append("fixed-window phrasing detected")
            break
    for term in BANNED_TAXONOMY:
        if term in lower:
            fail_reasons.append("internal taxonomy leaked")
            break
    for term in BANNED_VOCABULARY:
        if term in lower:
            fail_reasons.append("banned vocabulary present")
            break

    return {"passed": not fail_reasons, "fail_reasons": fail_reasons}


async def generate_foundation_narration(person_id: str, window_days: int = 1500, include_debug: bool = True) -> Dict[str, Any]:
    journals = await _load_journals(person_id, window_days)
    episodic = await _load_episodic(person_id, window_days)
    states = await _load_states(person_id)
    suppression_stats = await _load_suppression_stats(person_id, window_days)

    notes = build_narrative_notes(states, journals, episodic, suppression_stats, window_days)
    narration_text = await render_human_narration(notes)
    if not narration_text or not narration_text.strip():
        raise RuntimeError("Human narration renderer returned empty text")
    validation = validate_narration(narration_text)
    if not validation["passed"]:
        raise RuntimeError(f"Reflection narration failed validation: {', '.join(validation['fail_reasons'])}")

    rhythm_state = states.get("rhythm_state") or {}
    emotion_state = states.get("emotion_state") or {}
    if isinstance(emotion_state, str):
        try:
            emotion_state = json.loads(emotion_state)
        except Exception:
            emotion_state = {}
    identity_state = states.get("identity_momentum_state") or {}
    if isinstance(identity_state, str):
        try:
            identity_state = json.loads(identity_state)
        except Exception:
            identity_state = {}
    longitudinal_state = states.get("longitudinal_state") or {}
    if isinstance(longitudinal_state, str):
        try:
            longitudinal_state = json.loads(longitudinal_state)
        except Exception:
            longitudinal_state = {}
    slot_counts = notes.get("slot_counts", {}) or {}

    reflection_support: Dict[str, Any] = {}
    if rhythm_state:
        total_slots = sum(slot_counts.values())
        top_slot = max(slot_counts.items(), key=lambda kv: kv[1])[0] if slot_counts else None
        reflection_support["rhythm"] = {
            "signal": "time_of_day_distribution",
            "evidence": {
                "total_slots": total_slots,
                "top_slot": top_slot,
                "slot_counts": slot_counts,
            },
        }
    if emotion_state:
        reflection_support["emotion"] = {
            "signal": "emotional_field",
            "evidence": {
                "valence": emotion_state.get("valence"),
                "activation": emotion_state.get("activation"),
                "volatility": emotion_state.get("volatility"),
                "dominant_tones": emotion_state.get("dominant_tones", []),
                "conditions": emotion_state.get("conditions", {}),
            },
        }
    if identity_state:
        reflection_support["identity_momentum"] = {
            "signal": "directional_motion",
            "evidence": {
                "direction": identity_state.get("direction"),
                "magnitude": identity_state.get("magnitude"),
                "stability": identity_state.get("stability"),
                "confidence": identity_state.get("confidence"),
            },
        }
    if longitudinal_state:
        reflection_support["longitudinal"] = {
            "signal": "longer_arc",
            "evidence": {
                "dimensions": list(longitudinal_state.keys()),
                "state": longitudinal_state,
            },
        }

    absence_signals: List[str] = []
    if suppression_stats.get("suppressed_count", 0) == 0:
        absence_signals.append("no_suppression_events")
    if emotion_state and not emotion_state.get("conditions", {}).get("persistent_negative", False):
        absence_signals.append("no_persistent_negative_emotion_detected")
    if identity_state and identity_state.get("direction") in (None, "", "oscillating"):
        absence_signals.append("no_clear_identity_drift_detected")

    result: Dict[str, Any] = {
        "mode": "foundation_narration",
        "timeframe": {
            "mode": "rolling",
            "anchor_days": window_days,
            "context": "longitudinal",
        },
        "reflection_text": narration_text.strip(),
        "reflection_support": reflection_support,
        "absence_signals": absence_signals,
    }
    if include_debug:
        result["debug"] = {
            "journals_used": len(journals),
            "episodic_used": len(episodic),
            "states_present": notes.get("states_present", []),
            "states_absent": notes.get("states_absent", []),
            "suppression": suppression_stats,
            "slot_counts": notes.get("slot_counts", {}),
        }
    return result
