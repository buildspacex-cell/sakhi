from __future__ import annotations

import datetime as dt
import json
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

SYSTEM_PROMPT = (
    "You are a reflective companion helping a person gently look back on their week.\n\n"
    "Your role is not to analyze or judge, but to mirror what seems to have happened in a grounded, human way.\n\n"
    "Write as one thoughtful human speaking to another.\n"
    "Natural. Warm. Clear. Not clinical. Not instructional.\n\n"
    "You are working from structured weekly signals — not raw text.\n"
    "You must stay faithful to the signals provided.\n\n"
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

If a dimension is flat or low-confidence, describe it as steady/quiet/unchanged without implying improvement or decline and without explaining causes.

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
    row = await q(
        """
        SELECT week_start, week_end, episodic_stats, theme_stats, contrast_stats, delta_stats, confidence
        FROM memory_weekly_signals
        WHERE person_id = $1
        ORDER BY week_start DESC
        LIMIT 1
        """,
        person_id,
        one=True,
    )
    if not row:
        return {}

    parsed = dict(row)
    for key in ("episodic_stats", "theme_stats", "contrast_stats", "delta_stats"):
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


async def _llm_render(
    window_str: str,
    signals: Dict[str, Any],
    longitudinal_state: Dict[str, Any],
    *,
    system_prompt_override: Optional[str] = None,
    user_prompt_override: Optional[str] = None,
) -> Tuple[Dict[str, Any], List[str]]:
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
        delta_stats = signals.get("delta_stats")
        if isinstance(delta_stats, dict):
            for key, value in delta_stats.items():
                if isinstance(key, str) and key in ALLOWED_DIMENSIONS and str(value).lower() == "flat":
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

    return flat, used_dimensions


async def generate_weekly_reflection(
    person_id: str,
    longitudinal_state: Dict[str, Any],
    *,
    system_prompt_override: Optional[str] = None,
    user_prompt_override: Optional[str] = None,
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

    llm_result, used_dimensions = await _llm_render(
        window_str,
        signals,
        longitudinal_state,
        system_prompt_override=system_prompt_override,
        user_prompt_override=user_prompt_override,
    )

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
