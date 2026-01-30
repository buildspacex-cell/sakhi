"""Health data aggregator - processes raw health app data."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from statistics import mean, stdev


async def aggregate_health_data(
    person_id: str,
    health_data: Dict[str, List[Dict[str, Any]]],
) -> Dict[str, Any]:
    """
    Aggregate raw health data into structured format.

    Processes data from Apple Health, Android Health Connect,
    wearables, and other sources into unified body metrics.
    """
    aggregated: Dict[str, Any] = {}

    # Process each data type
    if "sleep" in health_data:
        aggregated["sleep"] = process_sleep_data(health_data["sleep"])

    if "activity" in health_data:
        aggregated["activity"] = process_activity_data(health_data["activity"])

    if "heart" in health_data:
        aggregated["vitals"] = process_heart_data(health_data["heart"])
    else:
        aggregated["vitals"] = {}

    if "respiratory" in health_data:
        resp = process_respiratory_data(health_data["respiratory"])
        aggregated["vitals"].update(resp)

    if "body" in health_data:
        aggregated["body"] = process_body_data(health_data["body"])

    if "nutrition" in health_data:
        aggregated["nutrition"] = process_nutrition_data(health_data["nutrition"])

    if "mindfulness" in health_data:
        aggregated["mindfulness"] = process_mindfulness_data(health_data["mindfulness"])

    return aggregated


def process_sleep_data(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Process sleep data from health apps.

    Apple Health sleep data includes:
    - Sleep analysis (inBed, asleep, awake, asleepCore, asleepDeep, asleepREM)

    Android Health Connect:
    - SleepSessionRecord (stages, duration)
    """
    if not records:
        return {}

    # Get most recent sleep session
    latest = _get_latest_record(records)
    data = latest.get("data", {})

    # Calculate total duration
    duration_hours = _extract_duration_hours(data)

    # Extract sleep stages
    stages = data.get("stages", {})
    deep_percent = stages.get("deep_percent", data.get("deep_sleep_percent"))
    rem_percent = stages.get("rem_percent", data.get("rem_percent"))
    light_percent = stages.get("light_percent", data.get("light_sleep_percent"))

    # Count interruptions
    interruptions = data.get("interruptions", 0)
    if "awake_minutes" in data and data["awake_minutes"] > 30:
        interruptions = max(interruptions, int(data["awake_minutes"] / 15))

    # Calculate quality score
    quality_score = _compute_sleep_quality(
        duration_hours, deep_percent, rem_percent, interruptions
    )

    # Calculate consistency (if we have multiple nights)
    consistency = _compute_sleep_consistency(records)

    # Calculate sleep debt
    sleep_debt = _compute_sleep_debt(records)

    return {
        "duration_hours": duration_hours,
        "quality_score": quality_score,
        "deep_sleep_percent": deep_percent,
        "rem_percent": rem_percent,
        "light_sleep_percent": light_percent,
        "interruptions": interruptions,
        "consistency_score": consistency,
        "sleep_debt_hours": sleep_debt,
        "recorded_at": latest.get("recorded_at"),
    }


def process_activity_data(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Process activity data from health apps.

    Apple Health:
    - stepCount, activeEnergyBurned, appleExerciseTime, appleStandTime

    Android Health Connect:
    - StepsRecord, ActiveCaloriesBurnedRecord, ExerciseSessionRecord
    """
    if not records:
        return {}

    # Aggregate today's activity
    today = datetime.now(timezone.utc).date()
    today_records = [
        r for r in records
        if _get_record_date(r) == today
    ]

    # Sum up steps
    steps_today = sum(
        r.get("data", {}).get("steps", 0) or r.get("data", {}).get("count", 0)
        for r in today_records
        if r.get("data", {}).get("type") in (None, "steps", "stepCount")
    )

    # Sum up active minutes
    active_minutes = sum(
        r.get("data", {}).get("active_minutes", 0) or r.get("data", {}).get("duration_minutes", 0)
        for r in today_records
        if r.get("data", {}).get("type") in (None, "exercise", "activity")
    )

    # Standing hours
    standing_hours = sum(
        1 for r in today_records
        if r.get("data", {}).get("type") == "stand_hour"
    )

    # Exercise details
    exercise_records = [
        r for r in today_records
        if r.get("data", {}).get("type") in ("exercise", "workout")
    ]
    exercise_minutes = sum(
        r.get("data", {}).get("duration_minutes", 0)
        for r in exercise_records
    )
    exercise_type = None
    if exercise_records:
        latest_exercise = _get_latest_record(exercise_records)
        exercise_type = latest_exercise.get("data", {}).get("workout_type", "unknown")

    # Estimate sedentary time (rough calculation)
    awake_hours = 16  # Assume 16 waking hours
    active_hours = (active_minutes + exercise_minutes) / 60
    sedentary_hours = max(0, awake_hours - active_hours - standing_hours)

    return {
        "steps_today": steps_today,
        "active_minutes": active_minutes,
        "standing_hours": standing_hours,
        "exercise_minutes": exercise_minutes,
        "exercise_type": exercise_type,
        "sedentary_hours": round(sedentary_hours, 1),
    }


def process_heart_data(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Process heart data from health apps.

    Apple Health:
    - heartRate, heartRateVariabilitySDNN, restingHeartRate

    Android Health Connect:
    - HeartRateRecord, HeartRateVariabilityRmssdRecord
    """
    if not records:
        return {}

    # Separate by type
    hr_records = [
        r for r in records
        if r.get("data", {}).get("type") in (None, "heart_rate", "heartRate")
    ]
    hrv_records = [
        r for r in records
        if r.get("data", {}).get("type") in ("hrv", "heartRateVariability")
    ]
    rhr_records = [
        r for r in records
        if r.get("data", {}).get("type") in ("resting_heart_rate", "restingHeartRate")
    ]

    result: Dict[str, Any] = {}

    # Get resting heart rate
    if rhr_records:
        latest_rhr = _get_latest_record(rhr_records)
        result["heart_rate_resting"] = latest_rhr.get("data", {}).get("value")
    elif hr_records:
        # Estimate from lowest recent HR values
        hr_values = [
            r.get("data", {}).get("value")
            for r in hr_records
            if r.get("data", {}).get("value")
        ]
        if hr_values:
            result["heart_rate_resting"] = min(hr_values)

    # Get HRV
    if hrv_records:
        latest_hrv = _get_latest_record(hrv_records)
        result["heart_rate_variability"] = latest_hrv.get("data", {}).get("value")

    return result


def process_respiratory_data(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Process respiratory data from health apps.

    Apple Health:
    - respiratoryRate, oxygenSaturation

    Android Health Connect:
    - RespiratoryRateRecord, OxygenSaturationRecord
    """
    if not records:
        return {}

    result: Dict[str, Any] = {}

    # Respiratory rate
    rr_records = [
        r for r in records
        if r.get("data", {}).get("type") in (None, "respiratory_rate", "respiratoryRate")
    ]
    if rr_records:
        latest = _get_latest_record(rr_records)
        result["respiratory_rate"] = latest.get("data", {}).get("value")

    # SpO2
    spo2_records = [
        r for r in records
        if r.get("data", {}).get("type") in ("spo2", "oxygenSaturation", "blood_oxygen")
    ]
    if spo2_records:
        latest = _get_latest_record(spo2_records)
        value = latest.get("data", {}).get("value")
        # Ensure it's a percentage
        if value and value <= 1:
            value = value * 100
        result["blood_oxygen"] = value

    return result


def process_body_data(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Process body measurement data.

    Apple Health:
    - bodyMass, bodyFatPercentage, bodyTemperature

    Android Health Connect:
    - WeightRecord, BodyFatRecord, BodyTemperatureRecord
    """
    if not records:
        return {}

    result: Dict[str, Any] = {}

    # Weight
    weight_records = [
        r for r in records
        if r.get("data", {}).get("type") in (None, "weight", "bodyMass")
    ]
    if weight_records:
        latest = _get_latest_record(weight_records)
        result["weight_kg"] = latest.get("data", {}).get("value")

        # Check trend
        if len(weight_records) >= 3:
            recent = sorted(weight_records, key=lambda x: x.get("recorded_at", ""))[-3:]
            weights = [r.get("data", {}).get("value") for r in recent if r.get("data", {}).get("value")]
            if len(weights) >= 2:
                if weights[-1] > weights[0] * 1.02:
                    result["weight_trend"] = "increasing"
                elif weights[-1] < weights[0] * 0.98:
                    result["weight_trend"] = "decreasing"
                else:
                    result["weight_trend"] = "stable"

    # Body temperature
    temp_records = [
        r for r in records
        if r.get("data", {}).get("type") in ("temperature", "bodyTemperature")
    ]
    if temp_records:
        latest = _get_latest_record(temp_records)
        result["body_temperature"] = latest.get("data", {}).get("value")

    # Body fat
    fat_records = [
        r for r in records
        if r.get("data", {}).get("type") in ("body_fat", "bodyFatPercentage")
    ]
    if fat_records:
        latest = _get_latest_record(fat_records)
        result["body_fat_percent"] = latest.get("data", {}).get("value")

    # Calculate BMI if we have weight and height
    height = None
    height_records = [
        r for r in records
        if r.get("data", {}).get("type") in ("height", "bodyHeight")
    ]
    if height_records:
        latest = _get_latest_record(height_records)
        height = latest.get("data", {}).get("value")

    if result.get("weight_kg") and height:
        # BMI = weight(kg) / height(m)^2
        height_m = height if height < 3 else height / 100  # Handle cm vs m
        result["bmi"] = round(result["weight_kg"] / (height_m ** 2), 1)

    return result


def process_nutrition_data(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Process nutrition data.

    Apple Health:
    - dietaryWater, dietaryCaffeine, dietaryEnergyConsumed

    Android Health Connect:
    - HydrationRecord, NutritionRecord
    """
    if not records:
        return {}

    today = datetime.now(timezone.utc).date()
    today_records = [
        r for r in records
        if _get_record_date(r) == today
    ]

    result: Dict[str, Any] = {}

    # Water intake
    water_records = [
        r for r in today_records
        if r.get("data", {}).get("type") in (None, "water", "hydration", "dietaryWater")
    ]
    if water_records:
        water_ml = sum(
            r.get("data", {}).get("value", 0) or r.get("data", {}).get("volume_ml", 0)
            for r in water_records
        )
        result["water_intake_ml"] = water_ml

    # Caffeine intake
    caffeine_records = [
        r for r in today_records
        if r.get("data", {}).get("type") in ("caffeine", "dietaryCaffeine")
    ]
    if caffeine_records:
        caffeine_mg = sum(
            r.get("data", {}).get("value", 0)
            for r in caffeine_records
        )
        result["caffeine_intake_mg"] = caffeine_mg

    return result


def process_mindfulness_data(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Process mindfulness data.

    Apple Health:
    - mindfulSession

    Android Health Connect:
    - Mindfulness session type
    """
    if not records:
        return {}

    today = datetime.now(timezone.utc).date()
    today_records = [
        r for r in records
        if _get_record_date(r) == today
    ]

    mindful_minutes = sum(
        r.get("data", {}).get("duration_minutes", 0)
        for r in today_records
    )

    return {
        "mindful_minutes_today": mindful_minutes,
        "sessions_today": len(today_records),
    }


# --- Helper Functions ---


def _get_latest_record(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Get the most recent record by recorded_at."""
    if not records:
        return {}
    return max(records, key=lambda x: x.get("recorded_at", ""))


def _get_record_date(record: Dict[str, Any]) -> Optional[datetime.date]:
    """Extract date from record."""
    recorded_at = record.get("recorded_at")
    if not recorded_at:
        return None
    if isinstance(recorded_at, str):
        try:
            dt = datetime.fromisoformat(recorded_at.replace("Z", "+00:00"))
            return dt.date()
        except ValueError:
            return None
    if isinstance(recorded_at, datetime):
        return recorded_at.date()
    return None


def _extract_duration_hours(data: Dict[str, Any]) -> Optional[float]:
    """Extract sleep duration in hours."""
    if "duration_hours" in data:
        return data["duration_hours"]
    if "duration_minutes" in data:
        return data["duration_minutes"] / 60
    if "duration_seconds" in data:
        return data["duration_seconds"] / 3600
    if "start_time" in data and "end_time" in data:
        try:
            start = datetime.fromisoformat(data["start_time"].replace("Z", "+00:00"))
            end = datetime.fromisoformat(data["end_time"].replace("Z", "+00:00"))
            return (end - start).total_seconds() / 3600
        except (ValueError, TypeError):
            pass
    return None


def _compute_sleep_quality(
    duration: Optional[float],
    deep_percent: Optional[float],
    rem_percent: Optional[float],
    interruptions: int,
) -> float:
    """Compute sleep quality score 0-1."""
    score = 0.5
    factors = 0

    # Duration factor (7-9 hours optimal)
    if duration:
        if 7 <= duration <= 9:
            duration_score = 1.0
        elif 6 <= duration < 7 or 9 < duration <= 10:
            duration_score = 0.7
        elif 5 <= duration < 6:
            duration_score = 0.4
        else:
            duration_score = 0.2
        score += duration_score * 0.4
        factors += 1

    # Deep sleep factor (15-20% optimal)
    if deep_percent:
        if 15 <= deep_percent <= 25:
            deep_score = 1.0
        elif 10 <= deep_percent < 15 or 25 < deep_percent <= 30:
            deep_score = 0.7
        else:
            deep_score = 0.4
        score += deep_score * 0.25
        factors += 1

    # REM factor (20-25% optimal)
    if rem_percent:
        if 20 <= rem_percent <= 30:
            rem_score = 1.0
        elif 15 <= rem_percent < 20:
            rem_score = 0.7
        else:
            rem_score = 0.4
        score += rem_score * 0.2
        factors += 1

    # Interruption penalty
    if interruptions > 0:
        interruption_penalty = min(0.3, interruptions * 0.05)
        score -= interruption_penalty

    if factors > 0:
        score = score / (1 + factors * 0.1)  # Normalize

    return round(max(0.0, min(1.0, score)), 2)


def _compute_sleep_consistency(records: List[Dict[str, Any]]) -> float:
    """Compute sleep schedule consistency over past week."""
    if len(records) < 3:
        return 0.5

    # Get sleep start times from past week
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    recent = [
        r for r in records
        if r.get("recorded_at") and (
            datetime.fromisoformat(str(r["recorded_at"]).replace("Z", "+00:00"))
            if isinstance(r.get("recorded_at"), str)
            else r["recorded_at"]
        ) > week_ago
    ]

    if len(recent) < 3:
        return 0.5

    # Extract sleep start hours
    start_hours = []
    for r in recent:
        data = r.get("data", {})
        if "start_time" in data:
            try:
                start = datetime.fromisoformat(data["start_time"].replace("Z", "+00:00"))
                hour = start.hour + start.minute / 60
                # Handle midnight crossing
                if hour < 12:
                    hour += 24
                start_hours.append(hour)
            except (ValueError, TypeError):
                pass

    if len(start_hours) < 2:
        return 0.5

    # Calculate consistency (lower std dev = more consistent)
    try:
        std = stdev(start_hours)
        # 0-0.5 hours std = excellent (1.0)
        # 0.5-1 hours std = good (0.8)
        # 1-2 hours std = fair (0.5)
        # >2 hours std = poor (0.2)
        if std < 0.5:
            return 1.0
        elif std < 1.0:
            return 0.8
        elif std < 2.0:
            return 0.5
        else:
            return 0.2
    except Exception:
        return 0.5


def _compute_sleep_debt(records: List[Dict[str, Any]]) -> float:
    """Compute accumulated sleep debt over past week."""
    ideal_sleep = 7.5  # hours per night
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)

    recent = [
        r for r in records
        if r.get("recorded_at") and (
            datetime.fromisoformat(str(r["recorded_at"]).replace("Z", "+00:00"))
            if isinstance(r.get("recorded_at"), str)
            else r["recorded_at"]
        ) > week_ago
    ]

    if not recent:
        return 0.0

    total_debt = 0.0
    for r in recent:
        data = r.get("data", {})
        duration = _extract_duration_hours(data)
        if duration:
            debt = max(0, ideal_sleep - duration)
            total_debt += debt

    return round(total_debt, 1)


__all__ = [
    "aggregate_health_data",
    "process_sleep_data",
    "process_activity_data",
    "process_heart_data",
    "process_respiratory_data",
    "process_body_data",
    "process_nutrition_data",
    "process_mindfulness_data",
]
