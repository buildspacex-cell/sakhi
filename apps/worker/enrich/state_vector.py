from __future__ import annotations

import json
import logging
from typing import Dict, List, Tuple

from sakhi.apps.api.core.config_loader import get_policy, get_prompt
from sakhi.apps.api.core.llm import LLMResponseError, call_llm
from sakhi.apps.api.core.llm_schemas import StateVectorOutput

LOGGER = logging.getLogger(__name__)


def _build_messages(observations: List[dict]) -> List[dict]:
    prompt_def = get_prompt("interpret")
    messages: List[dict] = []
    system = prompt_def.get("system")
    if system:
        messages.append({"role": "system", "content": system})
    for shot in prompt_def.get("few_shots", []):
        user = shot.get("input")
        assistant = shot.get("output")
        if user:
            messages.append({"role": "user", "content": json.dumps(user, ensure_ascii=False)})
        if assistant:
            messages.append({"role": "assistant", "content": json.dumps(assistant, ensure_ascii=False)})
    payload = {"observations": observations}
    messages.append({"role": "user", "content": json.dumps(payload, ensure_ascii=False)})
    return messages


def _norm(value: float) -> float:
    """Map [-2, 2] range to [0, 1] for blending heuristics."""
    return max(0.0, min(1.0, 0.5 + value / 4.0))


def _clamp_state(value: float, *, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _extract_signal(observations: List[dict], lens: str, kind: str, key: str) -> float | None:
    for obs in observations:
        if obs.get("lens") != lens or obs.get("kind") != kind:
            continue
        payload = obs.get("payload") or {}
        if isinstance(payload, dict) and key in payload:
            try:
                return float(payload[key])
            except (TypeError, ValueError):
                return None
    return None


def _matched_keywords(text: str, keywords: List[str]) -> List[str]:
    return [kw for kw in keywords if kw and kw in text]


def _fallback_state_vector(observations: List[dict], text: str | None) -> Tuple[StateVectorOutput, Dict[str, List[str]]]:
    rules = get_policy("fallback_rules")
    defaults = rules.get("defaults", {})
    weights = rules.get("weights", {})
    lowered = (text or "").lower()

    matched: Dict[str, List[str]] = {}

    dosha: Dict[str, float] = {}
    for name in ("vata", "pitta", "kapha"):
        hits = _matched_keywords(lowered, rules.get(f"{name}_keywords", []))
        matched[name] = hits
        base = float(defaults.get(name, 0.0))
        if hits:
            base += float(weights.get(name, 0.0))
        dosha[name] = _clamp_state(base, lower=-2.0, upper=2.0)

    valence = _extract_signal(observations, "self", "valence", "valence")
    stress = _extract_signal(observations, "self", "stress", "stress")
    energy = _extract_signal(observations, "self", "energy", "energy")

    guna = {
        "sattva": float(defaults.get("sattva", 0.33)),
        "rajas": float(defaults.get("rajas", 0.34)),
        "tamas": float(defaults.get("tamas", 0.33)),
    }
    if valence is not None:
        if valence < -0.2:
            guna["tamas"] += 0.1
            guna["sattva"] -= 0.05
        elif valence > 0.2:
            guna["sattva"] += 0.1
            guna["tamas"] -= 0.05
    if stress is not None and stress > 0.6:
        guna["rajas"] += 0.12
        guna["sattva"] -= 0.05

    total_guna = sum(guna.values())
    if total_guna > 0:
        for key in guna:
            guna[key] = _clamp_state(guna[key] / total_guna, lower=0.0, upper=1.0)

    vata_norm = _norm(dosha["vata"])
    pitta_norm = _norm(dosha["pitta"])
    kapha_norm = _norm(dosha["kapha"])
    elements = {
        "earth": _clamp_state(0.2 + 0.4 * kapha_norm, lower=0.0, upper=1.0),
        "water": _clamp_state(0.2 + 0.2 * kapha_norm + 0.2 * pitta_norm, lower=0.0, upper=1.0),
        "fire": _clamp_state(0.2 + 0.4 * pitta_norm, lower=0.0, upper=1.0),
        "air": _clamp_state(0.2 + 0.4 * vata_norm, lower=0.0, upper=1.0),
        "ether": _clamp_state(0.2 + 0.3 * vata_norm, lower=0.0, upper=1.0),
    }

    signals_considered = sum(
        1 for value in (valence, stress, energy) if isinstance(value, (int, float))
    )
    confidence = _clamp_state(0.25 + 0.1 * signals_considered, lower=0.25, upper=0.55)

    notes = ["Heuristic fallback used for state vector."]
    for dosha_name, hits in matched.items():
        if hits:
            notes.append(f"{dosha_name.title()} cues: {', '.join(hits)}")
    if valence is not None:
        notes.append(f"Valence heuristic: {valence:.2f}")
    if stress is not None:
        notes.append(f"Stress heuristic: {stress:.2f}")

    return (
        StateVectorOutput(
            dosha=dosha,
            guna=guna,
            elements=elements,
            notes=notes,
            confidence=confidence,
        ),
        matched,
    )


async def compute_state_vector(
    observations: List[dict],
    text: str | None,
) -> tuple[StateVectorOutput | None, str | None, str]:
    try:
        messages = _build_messages(observations)
        parsed: StateVectorOutput = await call_llm(messages=messages, schema=StateVectorOutput)
        min_conf = float(get_policy("response_policy").get("min_state_confidence", 0.0))
        if float(parsed.confidence) < min_conf:
            fallback, _ = _fallback_state_vector(observations, text)
            return fallback, f"llm_low_confidence:{parsed.confidence}", "heuristic"
        return parsed, None, "llm"
    except LLMResponseError as exc:
        LOGGER.warning("State vector LLM failed: %s", exc)
        fallback, _ = _fallback_state_vector(observations, text)
        return fallback, str(exc), "heuristic"
