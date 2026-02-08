"""Body state engine - computes comprehensive physical state from health data."""

from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from sakhi.apps.api.core.db import dbfetchrow, dbfetchall, exec as dbexec


async def get_body_state(person_id: str) -> Dict[str, Any]:
    """Get current body_state from personal_model."""
    row = await dbfetchrow(
        """
        SELECT body_state
        FROM personal_model
        WHERE person_id = $1
        """,
        person_id,
    )
    if row and row.get("body_state"):
        body_state = row["body_state"]
        # Handle JSONB returned as string by asyncpg
        if isinstance(body_state, str):
            body_state = json.loads(body_state)
        return body_state
    return _default_body_state()


async def compute_body_state(
    person_id: str,
    health_data: Dict[str, Any],
    self_reports: Optional[List[Dict[str, Any]]] = None,
    emotion_state: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Compute comprehensive body_state from health data and self-reports.

    Integrates:
    - Vitals (HR, HRV, SpO2, respiratory rate)
    - Sleep (duration, quality, stages)
    - Activity (steps, exercise, sedentary time)
    - Self-reports (tension, digestion, cravings)
    - Emotion state (for mind-body correlation)

    Returns Ayurvedic body assessment with dosha imbalances.
    """
    from sakhi.apps.api.services.body.dosha_inference import infer_dosha_body_state
    from sakhi.apps.api.services.body.health_aggregator import aggregate_health_data

    # Aggregate raw health data into structured format
    aggregated = await aggregate_health_data(person_id, health_data)

    # Process self-reports if available
    self_report_data = _process_self_reports(self_reports or [])

    # Build body state
    body_state: Dict[str, Any] = {
        # Core vitals
        "vitals": aggregated.get("vitals", {}),

        # Sleep
        "sleep": aggregated.get("sleep", {}),

        # Energy & Activity
        "energy": _compute_energy_state(aggregated, self_report_data),
        "activity": aggregated.get("activity", {}),

        # Ayurvedic body assessment
        "dosha_body": await infer_dosha_body_state(
            aggregated, self_report_data, emotion_state
        ),

        # Agni (digestive fire)
        "agni": _compute_agni_state(self_report_data),

        # Ojas (vital essence)
        "ojas": _compute_ojas_state(aggregated, self_report_data),

        # Tension map (Yogic)
        "tension_map": _compute_tension_map(self_report_data),

        # Prana (breath/life force)
        "prana": _compute_prana_state(aggregated, self_report_data),

        # Hydration & Nutrition
        "hydration": _compute_hydration_state(aggregated, self_report_data),
        "nutrition": aggregated.get("nutrition", {}),

        # Circadian & Seasonal
        "circadian": _compute_circadian_state(),
        "seasonal": _compute_seasonal_state(),

        # Metadata
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "data_sources": _get_data_sources(health_data, self_reports),
    }

    # Compute summary
    body_state["summary"] = _compute_summary(body_state)

    return body_state


async def update_body_state_from_health_data(person_id: str) -> Dict[str, Any]:
    """
    Pull unprocessed health data and update body_state.
    Called by body_refresh worker.
    """
    # Fetch unprocessed health data
    rows = await dbfetchall(
        """
        SELECT id, source, data_type, data, recorded_at
        FROM health_data_sync
        WHERE person_id = $1 AND NOT processed
        ORDER BY recorded_at DESC
        LIMIT 100
        """,
        person_id,
    )

    if not rows:
        return await get_body_state(person_id)

    # Organize by data type
    health_data: Dict[str, List[Dict[str, Any]]] = {}
    record_ids: List[str] = []

    for row in rows:
        data_type = row["data_type"]
        if data_type not in health_data:
            health_data[data_type] = []
        health_data[data_type].append({
            "source": row["source"],
            "data": row["data"],
            "recorded_at": row["recorded_at"],
        })
        record_ids.append(str(row["id"]))

    # Fetch recent self-reports
    self_reports = await dbfetchall(
        """
        SELECT *
        FROM self_report_body
        WHERE person_id = $1
          AND recorded_at > NOW() - INTERVAL '24 hours'
        ORDER BY recorded_at DESC
        LIMIT 10
        """,
        person_id,
    )

    # Fetch emotion state for correlation
    emotion_row = await dbfetchrow(
        """
        SELECT emotion_state
        FROM personal_model
        WHERE person_id = $1
        """,
        person_id,
    )
    emotion_state = emotion_row.get("emotion_state") if emotion_row else None

    # Compute new body state
    body_state = await compute_body_state(
        person_id,
        health_data,
        self_reports or [],
        emotion_state,
    )

    # Update personal_model
    await dbexec(
        """
        UPDATE personal_model
        SET body_state = $2::jsonb,
            updated_at = NOW()
        WHERE person_id = $1
        """,
        person_id,
        json.dumps(body_state, ensure_ascii=False, default=str),
    )

    # Mark records as processed
    if record_ids:
        await dbexec(
            """
            UPDATE health_data_sync
            SET processed = TRUE, processed_at = NOW()
            WHERE id = ANY($1::uuid[])
            """,
            record_ids,
        )

    # Store history snapshot
    await _store_body_state_history(person_id, body_state)

    # Log health signals to symptom_log for pattern learning
    await _log_health_signals(person_id, body_state)

    return body_state


def _default_body_state() -> Dict[str, Any]:
    """Return default body state for new users."""
    return {
        "vitals": {},
        "sleep": {},
        "energy": {"level": 0.5, "trend": "stable"},
        "activity": {},
        "dosha_body": {
            "vata_signs": {"score": 0.0, "signals": []},
            "pitta_signs": {"score": 0.0, "signals": []},
            "kapha_signs": {"score": 0.0, "signals": []},
            "dominant_imbalance": None,
        },
        "agni": {"strength": "moderate"},
        "ojas": {"level": 0.5},
        "tension_map": {},
        "prana": {"breath_quality": "moderate", "capacity_score": 0.5},
        "hydration": {"level": 0.5},
        "summary": {
            "overall_score": 0.5,
            "primary_need": "balance",
            "confidence": 0.0,
        },
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "data_sources": [],
    }


def _process_self_reports(reports: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate self-report data into usable format."""
    if not reports:
        return {}

    # Use most recent report as primary
    latest = reports[0] if reports else {}

    return {
        "energy_level": latest.get("energy_level"),
        "fatigue_level": latest.get("fatigue_level"),
        "tension": {
            "neck_shoulders": latest.get("tension_neck_shoulders"),
            "back": latest.get("tension_back"),
            "jaw": latest.get("tension_jaw"),
        },
        "digestion": {
            "hunger_level": latest.get("hunger_level"),
            "quality": latest.get("digestion_quality"),
            "bloating": latest.get("bloating"),
            "elimination_regular": latest.get("elimination_regular"),
        },
        "temperature": {
            "feeling_cold": latest.get("feeling_cold"),
            "feeling_hot": latest.get("feeling_hot"),
        },
        "hydration_level": latest.get("hydration_level"),
        "breath_quality": latest.get("breath_quality"),
        "cravings": latest.get("cravings", []),
    }


def _compute_energy_state(
    aggregated: Dict[str, Any],
    self_reports: Dict[str, Any],
) -> Dict[str, Any]:
    """Compute energy state from multiple sources."""
    energy_level = 0.5
    sources_used = 0

    # From self-report
    if self_reports.get("energy_level") is not None:
        energy_level = self_reports["energy_level"]
        sources_used += 1

    # Adjust from sleep quality
    sleep = aggregated.get("sleep", {})
    if sleep.get("quality_score"):
        sleep_factor = sleep["quality_score"]
        if sources_used > 0:
            energy_level = (energy_level + sleep_factor) / 2
        else:
            energy_level = sleep_factor
        sources_used += 1

    # Adjust from HRV (higher HRV = more energy/recovery)
    vitals = aggregated.get("vitals", {})
    if vitals.get("heart_rate_variability"):
        hrv = vitals["heart_rate_variability"]
        # HRV 20-60 ms typical range, normalize
        hrv_factor = min(1.0, max(0.0, (hrv - 20) / 40))
        if sources_used > 0:
            energy_level = (energy_level * sources_used + hrv_factor) / (sources_used + 1)
        sources_used += 1

    # Compute trend from activity
    activity = aggregated.get("activity", {})
    trend = "stable"
    if activity.get("active_minutes", 0) > 60:
        trend = "declining"  # After heavy activity
    elif sleep.get("quality_score", 0) > 0.8:
        trend = "rising"

    return {
        "level": round(energy_level, 2),
        "trend": trend,
        "peak_hours": _estimate_peak_hours(),
        "low_hours": _estimate_low_hours(),
    }


def _estimate_peak_hours() -> List[int]:
    """Estimate peak energy hours based on circadian rhythm."""
    # Default circadian peaks
    return [9, 10, 11, 16, 17]


def _estimate_low_hours() -> List[int]:
    """Estimate low energy hours based on circadian rhythm."""
    return [14, 15, 22, 23]


def _compute_agni_state(self_reports: Dict[str, Any]) -> Dict[str, Any]:
    """Compute digestive fire (Agni) state."""
    digestion = self_reports.get("digestion", {})

    # Determine agni strength
    strength = "moderate"
    if digestion.get("quality") == "hyperactive":
        strength = "strong"
    elif digestion.get("quality") == "sluggish":
        strength = "weak"
    elif digestion.get("quality") == "irregular":
        strength = "variable"

    return {
        "strength": strength,
        "hunger_level": digestion.get("hunger_level", 0.5),
        "digestion_quality": digestion.get("quality", "unknown"),
        "bloating": digestion.get("bloating", False),
        "elimination_regular": digestion.get("elimination_regular", True),
    }


def _compute_ojas_state(
    aggregated: Dict[str, Any],
    self_reports: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Compute Ojas (vital essence) - immunity, vitality, glow.
    High ojas = well-rested, nourished, calm, radiant.
    Low ojas = depleted, weak immunity, dull.
    """
    ojas_score = 0.5
    factors = 0

    # Sleep quality is primary ojas builder
    sleep = aggregated.get("sleep", {})
    if sleep.get("quality_score"):
        ojas_score += sleep["quality_score"] * 0.3
        factors += 1

    # Deep sleep is especially important for ojas
    if sleep.get("deep_sleep_percent"):
        deep_factor = min(1.0, sleep["deep_sleep_percent"] / 20)  # 20% is excellent
        ojas_score += deep_factor * 0.2
        factors += 1

    # Consistent sleep builds ojas
    if sleep.get("consistency_score"):
        ojas_score += sleep["consistency_score"] * 0.1
        factors += 1

    # Energy level indicates ojas
    if self_reports.get("energy_level"):
        ojas_score += self_reports["energy_level"] * 0.2
        factors += 1

    # Fatigue depletes ojas
    if self_reports.get("fatigue_level"):
        ojas_score -= self_reports["fatigue_level"] * 0.2

    # Normalize
    ojas_level = max(0.0, min(1.0, ojas_score))

    return {
        "level": round(ojas_level, 2),
        "indicators": {
            "well_rested": sleep.get("quality_score", 0) > 0.7,
            "energy_stable": self_reports.get("energy_level", 0.5) > 0.6,
            "immunity_strong": ojas_level > 0.7,
        },
    }


def _compute_tension_map(self_reports: Dict[str, Any]) -> Dict[str, Any]:
    """Compute body tension map from self-reports."""
    tension = self_reports.get("tension", {})

    neck = tension.get("neck_shoulders", 0.0) or 0.0
    back = tension.get("back", 0.0) or 0.0
    jaw = tension.get("jaw", 0.0) or 0.0

    # Determine primary holding pattern
    primary = None
    max_tension = 0.0
    if neck > max_tension:
        primary = "neck_shoulders"
        max_tension = neck
    if back > max_tension:
        primary = "back"
        max_tension = back
    if jaw > max_tension:
        primary = "jaw"
        max_tension = jaw

    return {
        "neck_shoulders": neck,
        "upper_back": back * 0.6,  # Estimate
        "lower_back": back * 0.4,
        "hips": 0.0,
        "jaw": jaw,
        "primary_holding": primary,
    }


def _compute_prana_state(
    aggregated: Dict[str, Any],
    self_reports: Dict[str, Any],
) -> Dict[str, Any]:
    """Compute Prana (breath/life force) state."""
    breath_quality = self_reports.get("breath_quality", "moderate")

    # Estimate breath location from quality
    location = "chest"
    if breath_quality == "deep":
        location = "belly"
    elif breath_quality == "shallow":
        location = "clavicular"

    # Compute capacity score
    capacity = 0.5
    if breath_quality == "deep":
        capacity = 0.8
    elif breath_quality == "shallow":
        capacity = 0.3
    elif breath_quality == "irregular":
        capacity = 0.4

    # Adjust from SpO2 if available
    vitals = aggregated.get("vitals", {})
    if vitals.get("blood_oxygen"):
        spo2 = vitals["blood_oxygen"]
        if spo2 >= 98:
            capacity = min(1.0, capacity + 0.1)
        elif spo2 < 95:
            capacity = max(0.0, capacity - 0.2)

    return {
        "breath_quality": breath_quality,
        "breath_location": location,
        "capacity_score": round(capacity, 2),
    }


def _compute_hydration_state(
    aggregated: Dict[str, Any],
    self_reports: Dict[str, Any],
) -> Dict[str, Any]:
    """Compute hydration state."""
    level = self_reports.get("hydration_level", 0.5)

    nutrition = aggregated.get("nutrition", {})
    water_intake = nutrition.get("water_intake_ml", 0)
    caffeine = nutrition.get("caffeine_intake_mg", 0)

    # Adjust for caffeine (dehydrating)
    if caffeine > 300:
        level = max(0.0, level - 0.1)

    return {
        "level": round(level, 2),
        "water_intake_ml": water_intake,
        "caffeine_intake_mg": caffeine,
    }


def _compute_circadian_state() -> Dict[str, Any]:
    """Compute circadian phase based on current time."""
    now = datetime.now(timezone.utc)
    hour = now.hour

    # Determine phase
    if 5 <= hour < 9:
        phase = "morning_rise"
    elif 9 <= hour < 12:
        phase = "peak"
    elif 12 <= hour < 15:
        phase = "afternoon_slump"
    elif 15 <= hour < 18:
        phase = "second_wind"
    elif 18 <= hour < 21:
        phase = "evening_wind"
    else:
        phase = "night"

    return {
        "phase": phase,
        "hour": hour,
    }


def _compute_seasonal_state() -> Dict[str, Any]:
    """Compute Ayurvedic seasonal state (Ritu)."""
    now = datetime.now(timezone.utc)
    month = now.month

    # Ayurvedic seasons (Northern hemisphere approximation)
    if month in [11, 12]:
        ritu = "hemanta"  # Early winter
        adjustment = "warming"
        dominant_dosha = "vata"
    elif month in [1, 2]:
        ritu = "shishira"  # Late winter
        adjustment = "warming"
        dominant_dosha = "kapha"
    elif month in [3, 4]:
        ritu = "vasanta"  # Spring
        adjustment = "lightening"
        dominant_dosha = "kapha"
    elif month in [5, 6]:
        ritu = "grishma"  # Summer
        adjustment = "cooling"
        dominant_dosha = "pitta"
    elif month in [7, 8]:
        ritu = "varsha"  # Monsoon
        adjustment = "grounding"
        dominant_dosha = "vata"
    else:  # 9, 10
        ritu = "sharad"  # Autumn
        adjustment = "cooling"
        dominant_dosha = "pitta"

    return {
        "current_ritu": ritu,
        "seasonal_adjustment": adjustment,
        "dominant_dosha": dominant_dosha,
    }


def _get_data_sources(
    health_data: Dict[str, Any],
    self_reports: Optional[List[Dict[str, Any]]],
) -> List[str]:
    """Determine which data sources contributed."""
    sources = set()

    # Check health data sources
    for data_type, records in health_data.items():
        if isinstance(records, list):
            for record in records:
                if record.get("source"):
                    sources.add(record["source"])

    if self_reports:
        sources.add("self_report")

    return list(sources)


def _compute_summary(body_state: Dict[str, Any]) -> Dict[str, Any]:
    """Compute overall summary and recommendations."""
    # Calculate overall score
    scores = []

    energy = body_state.get("energy", {})
    if energy.get("level"):
        scores.append(energy["level"])

    ojas = body_state.get("ojas", {})
    if ojas.get("level"):
        scores.append(ojas["level"])

    sleep = body_state.get("sleep", {})
    if sleep.get("quality_score"):
        scores.append(sleep["quality_score"])

    prana = body_state.get("prana", {})
    if prana.get("capacity_score"):
        scores.append(prana["capacity_score"])

    overall_score = sum(scores) / len(scores) if scores else 0.5

    # Determine primary need
    dosha_body = body_state.get("dosha_body", {})
    primary_need = "balance"

    vata_score = dosha_body.get("vata_signs", {}).get("score", 0)
    pitta_score = dosha_body.get("pitta_signs", {}).get("score", 0)
    kapha_score = dosha_body.get("kapha_signs", {}).get("score", 0)

    if vata_score > 0.5:
        primary_need = "grounding"
    elif pitta_score > 0.5:
        primary_need = "cooling"
    elif kapha_score > 0.5:
        primary_need = "movement"
    elif ojas.get("level", 0.5) < 0.4:
        primary_need = "rest"
    elif energy.get("level", 0.5) < 0.3:
        primary_need = "nourishment"

    # Generate recommendations
    recommendations = _generate_recommendations(body_state, primary_need)

    # Confidence based on data sources
    sources = body_state.get("data_sources", [])
    confidence = min(1.0, len(sources) * 0.25)

    return {
        "overall_score": round(overall_score, 2),
        "primary_need": primary_need,
        "top_recommendations": recommendations[:3],
        "confidence": round(confidence, 2),
    }


def _generate_recommendations(
    body_state: Dict[str, Any],
    primary_need: str,
) -> List[str]:
    """Generate body-specific recommendations."""
    recommendations = []

    if primary_need == "grounding":
        recommendations.extend([
            "warm_oil_massage",
            "warm_cooked_foods",
            "regular_routine",
            "gentle_yoga",
        ])
    elif primary_need == "cooling":
        recommendations.extend([
            "cooling_breath",
            "avoid_overexertion",
            "light_meals",
            "moon_bathing",
        ])
    elif primary_need == "movement":
        recommendations.extend([
            "brisk_walk",
            "dry_brushing",
            "light_fasting",
            "stimulating_spices",
        ])
    elif primary_need == "rest":
        recommendations.extend([
            "earlier_bedtime",
            "warm_milk",
            "reduce_screens",
            "restorative_yoga",
        ])
    elif primary_need == "nourishment":
        recommendations.extend([
            "nourishing_foods",
            "warm_soups",
            "adequate_protein",
            "digestive_tea",
        ])
    else:
        recommendations.extend([
            "balanced_routine",
            "mindful_eating",
            "daily_movement",
        ])

    # Add sleep-specific if needed
    sleep = body_state.get("sleep", {})
    if sleep.get("quality_score", 1) < 0.5:
        recommendations.insert(0, "sleep_hygiene")

    # Add tension-specific if needed
    tension = body_state.get("tension_map", {})
    if tension.get("primary_holding"):
        recommendations.insert(0, f"release_{tension['primary_holding']}")

    return recommendations


async def _store_body_state_history(person_id: str, body_state: Dict[str, Any]) -> None:
    """Store body state snapshot for longitudinal tracking."""
    summary = body_state.get("summary", {})
    dosha = body_state.get("dosha_body", {})
    sleep = body_state.get("sleep", {})
    energy = body_state.get("energy", {})
    ojas = body_state.get("ojas", {})

    await dbexec(
        """
        INSERT INTO body_state_history (
            person_id, body_state, overall_score,
            vata_score, pitta_score, kapha_score,
            ojas_level, sleep_quality, energy_level
        ) VALUES ($1, $2::jsonb, $3, $4, $5, $6, $7, $8, $9)
        """,
        person_id,
        json.dumps(body_state, ensure_ascii=False, default=str),
        summary.get("overall_score"),
        dosha.get("vata_signs", {}).get("score"),
        dosha.get("pitta_signs", {}).get("score"),
        dosha.get("kapha_signs", {}).get("score"),
        ojas.get("level"),
        sleep.get("quality_score"),
        energy.get("level"),
    )


async def _log_health_signals(person_id: str, body_state: Dict[str, Any]) -> None:
    """
    Extract health signals from computed body_state and log them to symptom_log.

    This bridges health data into the pattern learning system. By logging
    health-derived signals as symptoms, detect_patterns() automatically
    correlates journal behaviors with health outcomes:
      - behavior: late_dinner (journal) → symptom: poor_sleep (HealthKit)
      - behavior: meditation (journal) → absence of low_hrv (HealthKit)
    """
    from sakhi.apps.api.services.ayurveda.pattern_learning import (
        ExtractedSymptom,
        log_symptom,
    )

    signals: List[ExtractedSymptom] = []

    # Sleep signals
    sleep = body_state.get("sleep", {})
    duration = sleep.get("duration_hours")
    if isinstance(duration, (int, float)) and duration < 6:
        signals.append(ExtractedSymptom(
            symptom_type="physical",
            symptom_name="poor_sleep",
            severity=max(0.3, round(1.0 - duration / 8.0, 2)),
            likely_dosha="vata",
        ))
    quality = sleep.get("quality_score")
    if isinstance(quality, (int, float)) and quality < 0.4:
        signals.append(ExtractedSymptom(
            symptom_type="physical",
            symptom_name="restless_sleep",
            severity=round(1.0 - quality, 2),
            likely_dosha="vata",
        ))

    # Heart rate signals
    vitals = body_state.get("vitals", {})
    rhr = vitals.get("resting_heart_rate") or vitals.get("resting_hr")
    if isinstance(rhr, (int, float)) and rhr > 80:
        signals.append(ExtractedSymptom(
            symptom_type="physical",
            symptom_name="elevated_heart_rate",
            severity=min(1.0, round((rhr - 60) / 40, 2)),
            likely_dosha="pitta",
        ))

    # HRV signals
    hrv = vitals.get("heart_rate_variability") or vitals.get("hrv_sdnn")
    if isinstance(hrv, (int, float)) and hrv < 30:
        signals.append(ExtractedSymptom(
            symptom_type="physical",
            symptom_name="low_hrv",
            severity=max(0.3, round(1.0 - hrv / 50, 2)),
            likely_dosha="vata",
        ))

    # Energy signals
    energy = body_state.get("energy", {})
    energy_level = energy.get("level")
    if isinstance(energy_level, (int, float)) and energy_level < 0.3:
        signals.append(ExtractedSymptom(
            symptom_type="energy",
            symptom_name="low_energy",
            severity=round(1.0 - energy_level, 2),
            likely_dosha="kapha",
        ))

    # Log each signal
    now = datetime.now(timezone.utc)
    for sig in signals:
        try:
            await log_symptom(
                person_id=person_id,
                symptom=sig,
                occurred_at=now,
                source_text="[HealthKit sync]",
            )
        except Exception as exc:
            # Don't let signal logging failures break the health refresh
            pass


__all__ = [
    "compute_body_state",
    "get_body_state",
    "update_body_state_from_health_data",
]
