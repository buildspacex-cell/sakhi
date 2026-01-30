"""Dosha inference for body state - Ayurvedic imbalance detection."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


async def infer_dosha_body_state(
    aggregated: Dict[str, Any],
    self_reports: Dict[str, Any],
    emotion_state: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Infer dosha imbalances from body data.

    Uses health metrics, self-reports, and emotion state to detect
    Vata, Pitta, and Kapha imbalances in the physical body.
    """
    vata = compute_vata_signals(aggregated, self_reports, emotion_state)
    pitta = compute_pitta_signals(aggregated, self_reports, emotion_state)
    kapha = compute_kapha_signals(aggregated, self_reports, emotion_state)

    # Determine dominant imbalance
    dominant = None
    max_score = 0.3  # Threshold for significance

    if vata["score"] > max_score:
        dominant = "vata"
        max_score = vata["score"]
    if pitta["score"] > max_score:
        dominant = "pitta"
        max_score = pitta["score"]
    if kapha["score"] > max_score:
        dominant = "kapha"

    return {
        "vata_signs": vata,
        "pitta_signs": pitta,
        "kapha_signs": kapha,
        "dominant_imbalance": dominant,
    }


def compute_vata_signals(
    aggregated: Dict[str, Any],
    self_reports: Dict[str, Any],
    emotion_state: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Detect Vata imbalance in body.

    Vata (Air + Space) imbalance manifests as:
    - Dryness, coldness, lightness
    - Irregular patterns (sleep, digestion, energy)
    - Nervous system overactivity
    - Anxiety, restlessness
    """
    signals: List[str] = []
    score = 0.0
    weights = []

    vitals = aggregated.get("vitals", {})
    sleep = aggregated.get("sleep", {})
    activity = aggregated.get("activity", {})
    temp = self_reports.get("temperature", {})
    digestion = self_reports.get("digestion", {})

    # --- Health Data Signals ---

    # Low HRV = low adaptability, Vata aggravation
    hrv = vitals.get("heart_rate_variability")
    if hrv is not None and hrv < 30:
        signals.append("low_hrv")
        weights.append(0.15)

    # High heart rate variability (std dev) = irregular
    # This would need beat-to-beat data, approximate from context

    # Irregular sleep
    if sleep.get("consistency_score") is not None and sleep["consistency_score"] < 0.5:
        signals.append("irregular_sleep")
        weights.append(0.15)

    # Short or interrupted sleep
    if sleep.get("interruptions") is not None and sleep["interruptions"] > 3:
        signals.append("restless_sleep")
        weights.append(0.1)

    # Low deep sleep (Vata = light sleep)
    if sleep.get("deep_sleep_percent") is not None and sleep["deep_sleep_percent"] < 15:
        signals.append("light_sleep")
        weights.append(0.1)

    # Underweight (if BMI available)
    body = aggregated.get("body", {})
    if body.get("bmi") is not None and body["bmi"] < 18.5:
        signals.append("underweight")
        weights.append(0.1)

    # --- Self-Report Signals ---

    # Cold extremities
    if temp.get("feeling_cold"):
        signals.append("cold_extremities")
        weights.append(0.12)

    # Irregular digestion
    if digestion.get("quality") == "irregular":
        signals.append("variable_digestion")
        weights.append(0.12)

    # Constipation (Vata dryness in colon)
    if digestion.get("elimination_regular") is False:
        signals.append("constipation")
        weights.append(0.1)

    # Bloating (Vata gas)
    if digestion.get("bloating"):
        signals.append("bloating")
        weights.append(0.08)

    # Dry skin/dehydration indicators
    hydration = self_reports.get("hydration_level")
    if hydration is not None and hydration < 0.4:
        signals.append("dehydration")
        weights.append(0.08)

    # Shallow/irregular breath
    breath = self_reports.get("breath_quality")
    if breath in ("shallow", "irregular"):
        signals.append("shallow_breath")
        weights.append(0.08)

    # --- Emotion State Correlation ---
    if emotion_state:
        anxiety = emotion_state.get("anxiety", 0)
        if anxiety > 0.6:
            signals.append("anxiety")
            weights.append(0.12)

        restlessness = emotion_state.get("restlessness", 0)
        if restlessness > 0.5:
            signals.append("restlessness")
            weights.append(0.08)

    # --- Cravings ---
    cravings = self_reports.get("cravings", [])
    if "warm" in cravings or "heavy" in cravings or "oily" in cravings:
        signals.append("craving_grounding_foods")
        weights.append(0.06)

    # Calculate score
    score = sum(weights)
    score = min(1.0, score)  # Cap at 1.0

    return {
        "score": round(score, 2),
        "signals": signals,
    }


def compute_pitta_signals(
    aggregated: Dict[str, Any],
    self_reports: Dict[str, Any],
    emotion_state: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Detect Pitta imbalance in body.

    Pitta (Fire + Water) imbalance manifests as:
    - Heat, inflammation, intensity
    - Sharp/hyperactive digestion
    - Skin issues, acidity
    - Irritability, anger
    """
    signals: List[str] = []
    score = 0.0
    weights = []

    vitals = aggregated.get("vitals", {})
    sleep = aggregated.get("sleep", {})
    activity = aggregated.get("activity", {})
    temp = self_reports.get("temperature", {})
    digestion = self_reports.get("digestion", {})

    # --- Health Data Signals ---

    # Elevated resting heart rate (heat, inflammation)
    rhr = vitals.get("heart_rate_resting")
    if rhr is not None and rhr > 80:
        signals.append("elevated_heart_rate")
        weights.append(0.12)

    # High body temperature
    body_temp = vitals.get("body_temperature")
    if body_temp is not None and body_temp > 37.2:
        signals.append("elevated_temperature")
        weights.append(0.12)

    # Short sleep (Pitta burns through rest)
    if sleep.get("duration_hours") is not None and sleep["duration_hours"] < 6:
        signals.append("insufficient_sleep")
        weights.append(0.1)

    # Intense exercise (Pitta aggravating)
    exercise = activity.get("exercise_type")
    exercise_mins = activity.get("exercise_minutes", 0)
    if exercise_mins > 60 and exercise in ("running", "hiit", "crossfit", "intense"):
        signals.append("intense_exercise")
        weights.append(0.08)

    # --- Self-Report Signals ---

    # Feeling hot
    if temp.get("feeling_hot"):
        signals.append("overheating")
        weights.append(0.12)

    # Hyperactive digestion / acid reflux
    if digestion.get("quality") == "hyperactive":
        signals.append("hyperactive_digestion")
        weights.append(0.12)

    # Strong hunger (Pitta fire)
    hunger = digestion.get("hunger_level")
    if hunger is not None and hunger > 0.8:
        signals.append("intense_hunger")
        weights.append(0.08)

    # --- Emotion State Correlation ---
    if emotion_state:
        irritability = emotion_state.get("irritability", 0)
        if irritability > 0.6:
            signals.append("irritability")
            weights.append(0.12)

        anger = emotion_state.get("anger", 0)
        if anger > 0.5:
            signals.append("anger")
            weights.append(0.1)

        frustration = emotion_state.get("frustration", 0)
        if frustration > 0.5:
            signals.append("frustration")
            weights.append(0.08)

    # --- Cravings ---
    cravings = self_reports.get("cravings", [])
    if "cold" in cravings or "sweet" in cravings:
        signals.append("craving_cooling_foods")
        weights.append(0.06)

    # Calculate score
    score = sum(weights)
    score = min(1.0, score)

    return {
        "score": round(score, 2),
        "signals": signals,
    }


def compute_kapha_signals(
    aggregated: Dict[str, Any],
    self_reports: Dict[str, Any],
    emotion_state: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Detect Kapha imbalance in body.

    Kapha (Water + Earth) imbalance manifests as:
    - Heaviness, sluggishness, congestion
    - Water retention, weight gain
    - Slow digestion, lethargy
    - Depression, attachment
    """
    signals: List[str] = []
    score = 0.0
    weights = []

    vitals = aggregated.get("vitals", {})
    sleep = aggregated.get("sleep", {})
    activity = aggregated.get("activity", {})
    digestion = self_reports.get("digestion", {})

    # --- Health Data Signals ---

    # Very low resting heart rate (sluggish)
    rhr = vitals.get("heart_rate_resting")
    if rhr is not None and rhr < 55:
        signals.append("low_heart_rate")
        weights.append(0.08)

    # Excess sleep (Kapha loves sleep)
    if sleep.get("duration_hours") is not None and sleep["duration_hours"] > 9:
        signals.append("excess_sleep")
        weights.append(0.12)

    # Low activity / sedentary
    steps = activity.get("steps_today", 0)
    if steps < 3000:
        signals.append("low_activity")
        weights.append(0.12)

    sedentary = activity.get("sedentary_hours", 0)
    if sedentary > 10:
        signals.append("sedentary")
        weights.append(0.1)

    # Weight gain trend
    body = aggregated.get("body", {})
    if body.get("weight_trend") == "increasing":
        signals.append("weight_gain")
        weights.append(0.1)

    # Overweight
    if body.get("bmi") is not None and body["bmi"] > 30:
        signals.append("overweight")
        weights.append(0.08)

    # --- Self-Report Signals ---

    # Sluggish digestion
    if digestion.get("quality") == "sluggish":
        signals.append("sluggish_digestion")
        weights.append(0.12)

    # Low hunger (weak agni)
    hunger = digestion.get("hunger_level")
    if hunger is not None and hunger < 0.3:
        signals.append("low_appetite")
        weights.append(0.08)

    # Low energy
    energy = self_reports.get("energy_level")
    if energy is not None and energy < 0.3:
        signals.append("lethargy")
        weights.append(0.12)

    # High fatigue
    fatigue = self_reports.get("fatigue_level")
    if fatigue is not None and fatigue > 0.7:
        signals.append("fatigue")
        weights.append(0.1)

    # --- Emotion State Correlation ---
    if emotion_state:
        depression = emotion_state.get("depression", 0)
        if depression > 0.5:
            signals.append("depression")
            weights.append(0.1)

        lethargy = emotion_state.get("lethargy", 0)
        if lethargy > 0.5:
            signals.append("mental_sluggishness")
            weights.append(0.08)

        attachment = emotion_state.get("attachment", 0)
        if attachment > 0.6:
            signals.append("attachment")
            weights.append(0.06)

    # --- Cravings ---
    cravings = self_reports.get("cravings", [])
    if "light" in cravings or "spicy" in cravings or "bitter" in cravings:
        signals.append("craving_stimulating_foods")
        weights.append(0.06)

    # Calculate score
    score = sum(weights)
    score = min(1.0, score)

    return {
        "score": round(score, 2),
        "signals": signals,
    }


__all__ = [
    "infer_dosha_body_state",
    "compute_vata_signals",
    "compute_pitta_signals",
    "compute_kapha_signals",
]
