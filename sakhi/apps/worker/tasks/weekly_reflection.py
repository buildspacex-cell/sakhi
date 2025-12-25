from __future__ import annotations

import datetime as dt
import json
import os
import logging
import re
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from sakhi.apps.api.core.db import q
from sakhi.apps.api.core.llm import call_llm
from sakhi.libs.schemas.settings import get_settings

# Weekly Reflection Renderer (ephemeral, language-only)
# Guardrails:
# - Reads structured signals only (memory_weekly_signals + longitudinal_state).
# - Does NOT read episodic text, journals, or planner text.
# - Does NOT persist output.
# - No learning or identity; language is tentative and confidence-aware.

ALLOWED_DIMENSIONS = {"body", "mind", "emotion", "energy", "work"}
DIM_CONFIDENCE_MIN = 0.5
MAX_WORDS = 600
# Only block true advice/identity statements; allow natural second-person reflection.
FORBIDDEN_PATTERNS = [
    r"\byou should\b",
    r"\byou need to\b",
    r"\btry to\b",
    r"\bthis means you are\b",
    r"\byou are (a|an)\b",
    r"\bmust\b",
    r"\badvice\b",
]
logger = logging.getLogger(__name__)
settings = get_settings()
TARGET_WEEK_START_ENV = os.getenv("WEEKLY_REFLECTION_TARGET_WEEK_START")

SYSTEM_PROMPT = (
    "You are a reflective companion helping a person gently look back on their week.\n\n"
    "Your role is not to analyze or judge, but to mirror what seems to have happened in a grounded, human way.\n\n"
    "Write as one thoughtful human speaking to another.\n"
    "Natural. Warm. Clear. Not clinical. Not instructional.\n\n"
    "You are working from structured weekly signals — not raw text.\n"
    "You must stay faithful to the signals provided.\n\n"
    "Trend describes long-term direction.\n"
    "Weekly salience and dimension states describe lived experience for this week.\n"
    "For weekly reflections, dimension_states and weekly_contrast describe lived experience for the week and take precedence over delta_stats for tone and wording.\n"
    "Delta stats provide background only.\n\n"
    "Tone guidelines:\n"
    "- Speak plainly and conversationally.\n"
    "- Avoid phrases like “suggesting”, “indicating”, “dimension”, “trajectory”.\n"
    "- Prefer simple human phrasing: “This week felt…”, “What stands out is…”, “Overall, the week was…”.\n"
    "- Be calm and steady, not enthusiastic or dramatic.\n"
    "- Do not hedge excessively (“it may be”, “it appears”) unless confidence is explicitly low.\n\n"
    "Constraints (do not violate):\n"
    "- Do not give advice.\n"
    "- Do not speculate on causes.\n"
    "- Do not use identity or trait language.\n"
    "- Do not invent experiences.\n"
    "- Do not refer to metrics, scores, or dimensions explicitly.\n\n"
    "If a dimension must be reflected but no specific hints exist, use one brief, neutral phrase "
    "such as “felt mixed”, “had ups and downs”, or “carried some pressure”, without adding causes, advice, or examples.\n\n"
    "When anchors are present:\n"
    "- Describe the overall pattern first\n"
    "- Then weave the anchor naturally as an example\n"
    "- Do not quote, list, or reference journals\n"
    "- Do not mention dates or “you wrote”\n"
    "- Keep it flowing as one human reflection\n"
    "- Use at most one anchor per dimension\n\n"
    "Write as one human reflecting to another — grounded, observational, and calm. Avoid analytical framing or statistical language.\n\n"
    "The goal is for the reader to feel:\n"
    "“Yes — that sounds like my week.”"
)

USER_PROMPT_TEMPLATE = """You are given structured, language-free weekly signals.
- Week window: {week_window}
- Weekly signals JSON: {signals_json}
- High-confidence longitudinal trends JSON: {longitudinal_json}
- Dimensions present this week: {present_dimensions}
- Dimensions that are flat or low-confidence: {flat_or_low_conf_dimensions}

Write:
- One short opening reflection on the week as a whole.
- If specific areas stand out (body, mind, emotion, energy, work), reflect on them naturally in separate short paragraphs.
- If nothing stands out for an area, leave it empty.

If a dimension is flat, describe it as steady unless dimension_states indicates "mixed" or weekly_contrast is present, in which case reflect the presence without implying improvement or decline and without explaining causes.
If weekly salience is present, the overview should acknowledge effort, pressure, or contrast even if trends are flat.
If dimension_states[X] is "mixed", do NOT describe X as steady, unchanged, or quiet.
If dimension_states.body is "mixed" and weekly_body_notes.discomfort_hints are present, you may briefly acknowledge physical discomfort using the same neutral wording as the hint, without adding causes, advice, or interpretation.

For recovery and change:
- If recovery signals are present, offer a short human reflection on recovery/energy restoration.
- If something is shifting, capture it in a short “what’s changing” note. If not, leave it empty.

Do not label sections in the text. The structure will be applied outside the language.

Constraints:
- Do NOT add insights beyond the provided signals.
- Do NOT give advice or speculate on causes.
- Do NOT use bullet points.
- Do NOT use identity or trait language.

Return JSON only:
{{
  "period": "weekly",
  "window": "{week_window}",
  "overview": "...",
  "recovery": "...",
  "changes": "...",
  "body": "...",
  "mind": "...",
  "emotion": "...",
  "energy": "...",
  "work": "...",
  "confidence_note": "..."
}}
"""


async def _fetch_weekly_signals(person_id: str) -> Dict[str, Any]:
    target_clause = ""
    params: list[Any] = [person_id]
    if TARGET_WEEK_START_ENV:
        try:
            target_date = dt.date.fromisoformat(TARGET_WEEK_START_ENV)
            target_clause = "AND week_start = $2"
            params.append(target_date)
        except Exception:
            target_clause = ""
            params = [person_id]

    sql = f"""
        SELECT week_start, week_end, episodic_stats, theme_stats, contrast_stats, delta_stats, confidence, weekly_salience, weekly_contrast, dimension_states, weekly_body_notes
        FROM memory_weekly_signals
        WHERE person_id = $1
        {target_clause}
        ORDER BY week_start DESC
        LIMIT 1
    """
    row = await q(sql, *params, one=True)
    if not row:
        return {}

    parsed = dict(row)
    for key in ("episodic_stats", "theme_stats", "contrast_stats", "delta_stats", "weekly_salience", "weekly_contrast", "dimension_states", "weekly_body_notes"):
        val = parsed.get(key)
        if isinstance(val, str):
            try:
                parsed[key] = json.loads(val)
            except Exception:
                parsed[key] = {} if key.endswith("stats") else []
    if "confidence" in parsed:
        try:
            parsed["confidence"] = float(parsed.get("confidence") or 0.0)
        except Exception:
            parsed["confidence"] = 0.0
    return parsed


def _window(week_row: Dict[str, Any]) -> str:
    if week_row.get("week_start") and week_row.get("week_end"):
        try:
            ws = week_row["week_start"]
            we = week_row["week_end"]
            start = ws.isoformat() if hasattr(ws, "isoformat") else str(ws)
            end = we.isoformat() if hasattr(we, "isoformat") else str(we)
            return f"{start} \u2192 {end}"
        except Exception:
            pass
    end = dt.date.today()
    start = end - dt.timedelta(days=6)
    return f"{start.isoformat()} \u2192 {end.isoformat()}"


def _sanitize_theme_stats(themes: Any) -> List[Dict[str, Any]]:
    cleaned: List[Dict[str, Any]] = []
    if not isinstance(themes, list):
        return cleaned
    for item in themes:
        if not isinstance(item, dict):
            continue
        key = item.get("key")
        weight = item.get("weight")
        if key and isinstance(key, str):
            cleaned.append({"key": key, "weight": float(weight or 0)})
    return cleaned


def _trim_words(text: str, max_words: int = MAX_WORDS) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words])


def _contains_forbidden(text: str) -> bool:
    lowered = text.lower()
    return any(re.search(pattern, lowered) for pattern in FORBIDDEN_PATTERNS)


def _lint_reflection(
    reflection: Dict[str, Any],
    weekly_salience: Dict[str, Any],
    dimension_states: Dict[str, Any],
    weekly_contrast: Dict[str, Any],
    weekly_body_notes: Dict[str, Any],
) -> None:
    # Dimension coverage contract (presence only, not wording):
    # - If body is non-flat OR weekly_body_notes.count > 0 -> body section must exist.
    # - If emotion is non-flat OR weekly_contrast.count > 0 -> emotion section must exist.
    # - If energy is non-flat -> energy section must exist.
    # - If work is non-flat OR weekly_salience has work-related items -> work section must exist.
    # - If mind is non-flat -> mind section must exist.
    # Mentioning a dimension in overview does NOT satisfy coverage.
    violations: list[str] = []
    overview = (reflection.get("overview") or "").lower()
    emotion_reflection = (reflection.get("emotion") or "").strip()
    salience_present = bool(weekly_salience.get("present"))
    contrast_count = 0
    try:
        contrast_count = int(weekly_contrast.get("count") or 0)
    except Exception:
        contrast_count = 0

    if salience_present:
        if any(phrase in overview for phrase in ["nothing stood out", "nothing really stood out", "not much happened"]):
            violations.append("overview cannot say nothing stood out when weekly_salience is present")

    for dim, state in (dimension_states or {}).items():
        if state == "mixed":
            dim_text = (reflection.get(dim) or "").lower()
            if "unchanged" in dim_text or "flat" in dim_text or "steady" in dim_text or "quiet" in dim_text:
                violations.append(f"{dim} reflection cannot say steady/unchanged/flat/quiet when state is mixed")
        if state and str(state).lower() != "flat":
            dim_text_present = bool((reflection.get(dim) or "").strip())
            if not dim_text_present:
                violations.append(f"{dim} reflection missing despite non-flat state")

    if contrast_count > 0 and not emotion_reflection:
        violations.append("emotion reflection must not be empty when weekly_contrast.count > 0")

    body_notes = weekly_body_notes or {}
    try:
        body_notes_count = int(body_notes.get("count") or 0)
    except Exception:
        body_notes_count = 0
    if body_notes_count > 0:
        body_text = (reflection.get("body") or "").strip()
        if not body_text:
            violations.append("body reflection missing despite body notes")
        lower_body = body_text.lower()
        if any(term in lower_body for term in ["steady", "unchanged", "quiet"]):
            violations.append("body reflection cannot say steady/unchanged/quiet when weekly_body_notes.count > 0")
        hints = []
        hints_raw = body_notes.get("discomfort_hints") if isinstance(body_notes, dict) else None
        if isinstance(hints_raw, list):
            for item in hints_raw:
                if isinstance(item, dict) and isinstance(item.get("hint"), str):
                    hints.append(item["hint"].lower())
        ack_keywords = ["discomfort", "unease", "physical discomfort", "physical unease"]
        has_ack = any(k in lower_body for k in ack_keywords) or any(h in lower_body for h in hints)
        if not has_ack:
            violations.append("body reflection must acknowledge discomfort when weekly_body_notes are present")

    salience_items = weekly_salience.get("items") if isinstance(weekly_salience, dict) else []
    if isinstance(salience_items, list):
        for item in salience_items:
            if not isinstance(item, dict):
                continue
            key = str(item.get("key") or "").lower()
            if key in {"work_pressure", "overextension"} and not (reflection.get("work") or "").strip():
                violations.append("work reflection missing despite salience signals")

    # Explicit dimension coverage checks beyond state-based rules.
    if str((dimension_states or {}).get("body") or "").lower() != "flat" or body_notes_count > 0:
        if not (reflection.get("body") or "").strip():
            violations.append("body reflection missing per coverage contract")
    if str((dimension_states or {}).get("emotion") or "").lower() != "flat" or contrast_count > 0:
        if not (reflection.get("emotion") or "").strip():
            violations.append("emotion reflection missing per coverage contract")
    if str((dimension_states or {}).get("energy") or "").lower() != "flat":
        if not (reflection.get("energy") or "").strip():
            violations.append("energy reflection missing per coverage contract")
    work_state = str((dimension_states or {}).get("work") or "").lower()
    work_salient = False
    if isinstance(salience_items, list):
        work_salient = any(str((item or {}).get("key") or "").lower() in {"work_pressure", "overextension"} for item in salience_items if isinstance(item, dict))
    if work_state != "flat" or work_salient:
        if not (reflection.get("work") or "").strip():
            violations.append("work reflection missing per coverage contract")
    if str((dimension_states or {}).get("mind") or "").lower() != "flat":
        if not (reflection.get("mind") or "").strip():
            violations.append("mind reflection missing per coverage contract")

    # Anchor lint: if anchors exist, the corresponding dimension must paraphrase the anchor
    # without quoting journals, mentioning dates, or entry mechanics.
    anchor_map: Dict[str, List[Dict[str, Any]]] = {}
    if isinstance(weekly_contrast.get("moment_anchors"), list):
        for anchor in weekly_contrast.get("moment_anchors") or []:
            if isinstance(anchor, dict):
                typ = anchor.get("type")
                if typ:
                    anchor_map.setdefault(str(typ), []).append(anchor)
    if isinstance(weekly_salience.get("anchors"), list):
        if weekly_salience.get("anchors"):
            anchor_map.setdefault("work_overload", []).extend(
                [a for a in weekly_salience.get("anchors") if isinstance(a, dict)]
            )
    if isinstance(weekly_body_notes.get("anchors"), list):
        if weekly_body_notes.get("anchors"):
            anchor_map.setdefault("body_discomfort", []).extend(
                [a for a in weekly_body_notes.get("anchors") if isinstance(a, dict)]
            )

    def _has_forbidden_anchor_refs(text: str) -> bool:
        lower = text.lower()
        if "you wrote" in lower:
            return True
        if re.search(r"\\b\\d{4}-\\d{2}-\\d{2}\\b", text):
            return True
        return False

    def _check_anchor(dim: str, text: str, anchors: List[Dict[str, Any]]) -> None:
        if not anchors:
            return
        if not text.strip():
            violations.append(f"{dim} reflection missing despite anchor present")
            return
        if _has_forbidden_anchor_refs(text):
            violations.append(f"{dim} reflection references journal mechanics/quotes while anchors present")

    # Body anchor
    if anchor_map.get("body_discomfort"):
        _check_anchor("body", reflection.get("body") or "", anchor_map["body_discomfort"])
    # Work anchor
    if anchor_map.get("work_overload"):
        _check_anchor("work", reflection.get("work") or "", anchor_map["work_overload"])
    # Emotion anchors
    if anchor_map.get("positive_emotion") or anchor_map.get("negative_emotion"):
        _check_anchor("emotion", reflection.get("emotion") or "", (anchor_map.get("positive_emotion") or []) + (anchor_map.get("negative_emotion") or []))

    if violations:
        raise ValueError("Reflection lint failed: " + "; ".join(violations))


def _sanitize_mixed_reflection(reflection: Dict[str, Any], dimension_states: Dict[str, Any]) -> None:
    banned = ("steady", "unchanged", "flat", "quiet")
    for dim, state in (dimension_states or {}).items():
        if state != "mixed":
            continue
        text = reflection.get(dim)
        if not isinstance(text, str):
            continue
        cleaned = text
        for word in banned:
            cleaned = re.sub(rf"\\b{word}\\b", "mixed", cleaned, flags=re.IGNORECASE)
        reflection[dim] = cleaned
    if isinstance(reflection.get("overview"), str) and (dimension_states or {}):
        # Avoid calling the week “quiet/unchanged” when mixed signals exist anywhere.
        cleaned = reflection["overview"]
        for word in banned:
            cleaned = re.sub(rf"\\b{word}\\b", "mixed", cleaned, flags=re.IGNORECASE)
        reflection["overview"] = cleaned

async def _llm_render(
    window_str: str,
    signals: Dict[str, Any],
    longitudinal_state: Dict[str, Any],
    *,
    system_prompt_override: Optional[str] = None,
    user_prompt_override: Optional[str] = None,
) -> Tuple[Dict[str, Any], List[str], Dict[str, Any]]:
    def _json_safe(value: Any) -> Any:
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, date):
            return value.isoformat()
        if isinstance(value, (int, float, str)) or value is None:
            return value
        # Handle decimals and other numeric-likes
        try:
            return float(value)
        except Exception:
            pass
        if isinstance(value, dict):
            return {k: _json_safe(v) for k, v in value.items()}
        if isinstance(value, list):
            return [_json_safe(v) for v in value]
        return value

    safe_signals = _json_safe(
        {
            "week_start": signals.get("week_start"),
            "week_end": signals.get("week_end"),
            "episodic_stats": signals.get("episodic_stats"),
            "theme_stats": signals.get("theme_stats"),
            "contrast_stats": signals.get("contrast_stats"),
            "delta_stats": signals.get("delta_stats"),
            "weekly_salience": signals.get("weekly_salience"),
            "weekly_contrast": signals.get("weekly_contrast"),
            "dimension_states": signals.get("dimension_states"),
            "weekly_body_notes": signals.get("weekly_body_notes"),
            "confidence": signals.get("confidence"),
        }
    )
    # Collect longitudinal without dropping low-confidence; tone is handled in the prompt.
    filtered_longitudinal: Dict[str, Any] = {}
    if isinstance(longitudinal_state, str):
        try:
            longitudinal_state = json.loads(longitudinal_state)
        except Exception:
            longitudinal_state = {}
    for dim, payload in (longitudinal_state or {}).items():
        if dim not in ALLOWED_DIMENSIONS or not isinstance(payload, dict):
            continue
        filtered_longitudinal[dim] = payload

    def _present_dimensions() -> List[str]:
        dims: set[str] = set()
        for dim in ALLOWED_DIMENSIONS:
            if dim in signals:
                dims.add(dim)
        delta_stats = signals.get("delta_stats")
        if isinstance(delta_stats, dict):
            for key in delta_stats.keys():
                if isinstance(key, str) and key in ALLOWED_DIMENSIONS:
                    dims.add(key)
        contrast_stats = signals.get("contrast_stats")
        if isinstance(contrast_stats, dict):
            for key, value in contrast_stats.items():
                if isinstance(key, str) and key in ALLOWED_DIMENSIONS and value is not None:
                    dims.add(key)
        for dim in (longitudinal_state or {}).keys():
            if isinstance(dim, str) and dim in ALLOWED_DIMENSIONS:
                dims.add(dim)
        return sorted(dims)

    def _flat_or_low_conf() -> List[str]:
        dims: set[str] = set()
        dimension_states = signals.get("dimension_states") if isinstance(signals, dict) else {}
        delta_stats = signals.get("delta_stats")
        if isinstance(delta_stats, dict):
            for key, value in delta_stats.items():
                if isinstance(key, str) and key in ALLOWED_DIMENSIONS and str(value).lower() == "flat":
                    if not (isinstance(dimension_states, dict) and str(dimension_states.get(key)).lower() == "mixed"):
                        dims.add(key)
        for dim, payload in (longitudinal_state or {}).items():
            if not isinstance(payload, dict):
                continue
            try:
                if float(payload.get("confidence") or 0.0) < DIM_CONFIDENCE_MIN:
                    dims.add(dim)
            except Exception:
                continue
        return sorted(dims)

    payload = {
        "week_window": window_str,
        "signals_json": json.dumps(safe_signals, ensure_ascii=False),
        "longitudinal_json": json.dumps(filtered_longitudinal, ensure_ascii=False),
        "present_dimensions": json.dumps(_present_dimensions(), ensure_ascii=False),
        "flat_or_low_conf_dimensions": json.dumps(_flat_or_low_conf(), ensure_ascii=False),
    }
    debug_info: Dict[str, Any] = {
        "window": window_str,
        "present_dimensions": json.loads(payload["present_dimensions"]),
        "flat_or_low_conf_dimensions": json.loads(payload["flat_or_low_conf_dimensions"]),
        "safe_signals": safe_signals,
        "longitudinal": filtered_longitudinal,
    }

    class _SafeDict(dict):
        def __missing__(self, key):  # type: ignore[override]
            return ""

    template = user_prompt_override or USER_PROMPT_TEMPLATE
    try:
        prompt = template.format_map(_SafeDict(payload))
    except Exception as exc:
        logger.warning("WEEKLY_PROMPT_OVERRIDE_FORMAT_FAILED", extra={"reason": str(exc)})
        prompt = USER_PROMPT_TEMPLATE.format_map(_SafeDict(payload))

    logger.info(
        "WEEKLY_LLM_CALL",
        extra={
            "model": settings.weekly_reflection_model,
            "mode": "chat",
            "system_prompt_override": bool(system_prompt_override),
            "user_prompt_override": bool(user_prompt_override),
        },
    )

    raw = await call_llm(
        messages=[
            {"role": "system", "content": system_prompt_override or SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        model=settings.weekly_reflection_model,
        temperature=0.7,
    )
    raw = (raw or "").strip()
    debug_info["system_prompt"] = system_prompt_override or SYSTEM_PROMPT
    debug_info["user_prompt"] = prompt
    debug_info["raw_output"] = raw

    if raw.startswith("You are given structured"):
        raise RuntimeError("LLM echoed prompt instead of generating output.")

    if not raw or _contains_forbidden(raw):
        logger.error(
            "WEEKLY_LLM_RAW_OUTPUT_REJECTED",
            extra={
                "text": raw,
                "reason": "forbidden_phrase_or_empty",
            },
        )
        raise RuntimeError("LLM returned empty or contained forbidden phrases.")

    try:
        data = json.loads(raw)
    except Exception:
        raise ValueError("LLM response was not valid JSON.")

    if not isinstance(data, dict):
        raise ValueError("LLM response was not a JSON object.")

    # Flatten if the model returned a nested reflection object
    if isinstance(data.get("reflection"), dict):
        for k, v in data["reflection"].items():
            data.setdefault(k, v)

    confidence_note = data.get("confidence_note")
    if isinstance(confidence_note, str) and _contains_forbidden(confidence_note):
        raise ValueError("LLM response contained forbidden phrasing.")

    flat: Dict[str, Any] = {
        "period": "weekly",
        "window": window_str,
        "confidence_note": confidence_note or "",
    }
    for key in ("overview", "recovery", "changes", "body", "mind", "emotion", "energy", "work"):
        value = data.get(key, "")
        if isinstance(value, str):
            if _contains_forbidden(value):
                logger.error(
                    "WEEKLY_LLM_RAW_OUTPUT_REJECTED",
                    extra={"text": value, "reason": "forbidden_phrase_section", "section": key},
                )
                raise ValueError("LLM response contained forbidden phrasing.")
            flat[key] = _trim_words(value)
        else:
            flat[key] = ""

    used_dimensions = [
        key for key in ("body", "mind", "emotion", "energy", "work") if flat.get(key, "").strip()
    ]

    debug_info["used_dimensions"] = used_dimensions

    return flat, used_dimensions, debug_info


async def generate_weekly_reflection(
    person_id: str,
    longitudinal_state: Dict[str, Any],
    *,
    system_prompt_override: Optional[str] = None,
    user_prompt_override: Optional[str] = None,
    include_debug: bool = False,
) -> Dict[str, Any]:
    """
    Produce an ephemeral weekly reflection.
    - Reads structured weekly signals + longitudinal_state.
    - Never reads episodic/raw text or task text.
    - Never persists output.
    - Uses confidence to modulate language; drops low-confidence dimensions.
    """
    if not settings.enable_weekly_reflection_llm:
        raise RuntimeError(
            "Weekly reflection LLM rendering is disabled. "
            "Set ENABLE_WEEKLY_REFLECTION_LLM=true to proceed."
        )

    signals = await _fetch_weekly_signals(person_id)
    overall_conf = float(signals.get("confidence") or 0.0)
    window_str = _window(signals)

    if isinstance(longitudinal_state, str):
        try:
            longitudinal_state = json.loads(longitudinal_state)
        except Exception:
            longitudinal_state = {}

    llm_result, used_dimensions, debug_info = await _llm_render(
        window_str,
        signals,
        longitudinal_state,
        system_prompt_override=system_prompt_override,
        user_prompt_override=user_prompt_override,
    )
    weekly_salience = signals.get("weekly_salience") or {}
    weekly_contrast = signals.get("weekly_contrast") or {}
    dimension_states = signals.get("dimension_states") or {}
    weekly_body_notes = signals.get("weekly_body_notes") or {}
    _sanitize_mixed_reflection(llm_result, dimension_states)
    try:
        anchors = []
        salience = signals.get("weekly_salience") or {}
        body_notes = signals.get("weekly_body_notes") or {}
        if isinstance(salience.get("anchors"), list):
            anchors.extend([("work", a.get("moment_hint")) for a in salience.get("anchors") or []])
        if isinstance(body_notes.get("anchors"), list):
            anchors.extend([("body", a.get("moment_hint")) for a in body_notes.get("anchors") or []])
        logger.error(
            "WEEKLY_REFLECTION_INPUT_DEBUG",
            extra={
                "person_id": person_id,
                "weekly_contrast_count": (signals.get("weekly_contrast") or {}).get("count"),
                "dimension_state_body": (signals.get("dimension_states") or {}).get("body"),
                "anchors": anchors,
            },
        )
    except Exception:
        pass
    try:
        _lint_reflection(llm_result, weekly_salience, dimension_states, weekly_contrast, weekly_body_notes)
    except Exception as exc:
        logger.error(
            "WEEKLY_REFLECTION_LINT_FAILED",
            extra={"person_id": person_id, "reason": str(exc)},
        )
        raise
    if include_debug:
        llm_result["_debug"] = debug_info

    if not llm_result.get("confidence_note"):
        llm_result["confidence_note"] = (
            "This reflection is based on limited signals and may evolve as more weeks accumulate."
            if overall_conf < 0.6
            else "These patterns are becoming clearer, though they remain open to change."
        )

    logger.info(
        "WEEKLY_RENDERER_LLM_SUCCESS",
        extra={
            "person_id": person_id,
            "model": settings.weekly_reflection_model,
            "dimensions_used": used_dimensions,
        },
    )
    return llm_result


__all__ = ["generate_weekly_reflection"]
