"""
Personal Pattern Learning Service
---------------------------------
Learns user-specific cause-effect patterns from journal entries.

This service:
1. Extracts behaviors and symptoms from text
2. Logs them for correlation analysis
3. Detects and strengthens patterns over time
4. Provides the data for causal reasoning

The goal: Over time, Sakhi learns YOUR patterns, not just general Ayurvedic knowledge.
"""

from __future__ import annotations

import math
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from sakhi.apps.api.core.db import q as dbfetch, exec as execute
from sakhi.apps.api.core.llm import call_llm

logger = logging.getLogger(__name__)


# =============================================================================
# Pydantic Schemas for LLM Extraction
# =============================================================================

class ExtractedBehavior(BaseModel):
    """A behavior extracted from text."""
    behavior_type: str = Field(
        description="Type: food, sleep, exercise, work, social, substance, routine"
    )
    behavior_name: str = Field(
        description="Normalized name (e.g., 'late_dinner', 'skipped_exercise', 'caffeine_evening')"
    )
    intensity: float = Field(default=0.5, ge=0.0, le=1.0)
    time_indication: Optional[str] = Field(
        default=None,
        description="When this occurred (morning, evening, late_night, etc.)"
    )
    dosha_effect: Optional[str] = Field(
        default=None,
        description="Which dosha this likely affects (vata, pitta, kapha)"
    )
    effect_direction: Optional[str] = Field(
        default=None,
        description="'aggravates' or 'pacifies'"
    )


class ExtractedSymptom(BaseModel):
    """A symptom/state extracted from text."""
    symptom_type: str = Field(
        description="Type: physical, mental, emotional, energy"
    )
    symptom_name: str = Field(
        description="Normalized name (e.g., 'anxiety', 'fatigue', 'scattered')"
    )
    severity: float = Field(default=0.5, ge=0.0, le=1.0)
    time_indication: Optional[str] = Field(
        default=None,
        description="When this was experienced"
    )
    likely_dosha: Optional[str] = Field(
        default=None,
        description="Mapped dosha (vata, pitta, kapha)"
    )


class ExtractionResult(BaseModel):
    """Result of behavior/symptom extraction."""
    behaviors: List[ExtractedBehavior] = Field(default_factory=list)
    symptoms: List[ExtractedSymptom] = Field(default_factory=list)


# =============================================================================
# Behavior-Dosha Mapping
# =============================================================================

BEHAVIOR_DOSHA_MAP = {
    # Vata-aggravating behaviors
    "irregular_schedule": ("vata", "aggravates"),
    "skipped_meals": ("vata", "aggravates"),
    "late_night": ("vata", "aggravates"),
    "excessive_travel": ("vata", "aggravates"),
    "cold_food": ("vata", "aggravates"),
    "raw_food": ("vata", "aggravates"),
    "excessive_talking": ("vata", "aggravates"),
    "overstimulation": ("vata", "aggravates"),
    "caffeine": ("vata", "aggravates"),

    # Pitta-aggravating behaviors
    "spicy_food": ("pitta", "aggravates"),
    "skipped_lunch": ("pitta", "aggravates"),
    "overwork": ("pitta", "aggravates"),
    "competitive_activity": ("pitta", "aggravates"),
    "alcohol": ("pitta", "aggravates"),
    "sun_exposure": ("pitta", "aggravates"),
    "heated_argument": ("pitta", "aggravates"),
    "perfectionism": ("pitta", "aggravates"),

    # Kapha-aggravating behaviors
    "overeating": ("kapha", "aggravates"),
    "excessive_sleep": ("kapha", "aggravates"),
    "sedentary": ("kapha", "aggravates"),
    "heavy_food": ("kapha", "aggravates"),
    "sweet_food": ("kapha", "aggravates"),
    "daytime_nap": ("kapha", "aggravates"),
    "dairy_excess": ("kapha", "aggravates"),
    "attachment_behavior": ("kapha", "aggravates"),

    # Balancing behaviors
    "morning_routine": ("vata", "pacifies"),
    "warm_meal": ("vata", "pacifies"),
    "early_sleep": ("vata", "pacifies"),
    "meditation": ("vata", "pacifies"),
    "cooling_food": ("pitta", "pacifies"),
    "relaxation": ("pitta", "pacifies"),
    "exercise": ("kapha", "pacifies"),
    "fasting": ("kapha", "pacifies"),
}


def get_dosha_effect(behavior_name: str) -> Tuple[Optional[str], Optional[str]]:
    """Get dosha effect for a behavior."""
    return BEHAVIOR_DOSHA_MAP.get(behavior_name.lower(), (None, None))


# =============================================================================
# Extraction Functions
# =============================================================================

EXTRACTION_PROMPT = """Extract only the most relevant wellbeing signals from this journal entry.

Return exactly one JSON object with this shape:
{{
  "behaviors": [...],
  "symptoms": [...]
}}

Rules:
- Include at most 3 behaviors and at most 3 symptoms.
- Use short normalized snake_case names.
- Only include behaviors that plausibly affect wellbeing.
- Only include symptoms or states the person is actually experiencing.
- If a field is unclear, omit that item instead of guessing.
- If nothing relevant is present, return empty arrays.

Behavior fields:
- behavior_type: food, sleep, exercise, work, social, substance, routine
- behavior_name: normalized name like late_dinner, skipped_exercise, overwork
- intensity: 0.0-1.0
- time_indication: morning, afternoon, evening, late_night, or null
- dosha_effect: vata, pitta, kapha, or null
- effect_direction: aggravates, pacifies, or null

Symptom fields:
- symptom_type: physical, mental, emotional, energy
- symptom_name: normalized name like anxiety, fatigue, scattered
- severity: 0.0-1.0
- time_indication: morning, afternoon, evening, late_night, or null
- likely_dosha: vata, pitta, kapha, or null

Journal entry:
---
{text}
---"""


async def extract_behaviors_and_symptoms(
    text: str,
    person_id: Optional[str] = None,
) -> ExtractionResult:
    """
    Extract behaviors and symptoms from journal text.

    Args:
        text: Journal entry or conversation text
        person_id: Optional user ID for context

    Returns:
        ExtractionResult with behaviors and symptoms
    """
    if not text or len(text.strip()) < 20:
        return ExtractionResult()

    try:
        result = await call_llm(
            prompt=EXTRACTION_PROMPT.format(text=text),
            schema=ExtractionResult,
            max_repair_attempts=3,
            person_id=person_id,
        )

        if isinstance(result, ExtractionResult):
            # Enrich with dosha mappings where not provided
            for behavior in result.behaviors:
                if not behavior.dosha_effect:
                    dosha, direction = get_dosha_effect(behavior.behavior_name)
                    behavior.dosha_effect = dosha
                    behavior.effect_direction = direction

            return result

        return ExtractionResult()

    except Exception as e:
        logger.warning(f"Failed to extract behaviors/symptoms: {e}")
        return ExtractionResult()


# =============================================================================
# Logging Functions
# =============================================================================

async def log_behavior(
    person_id: str,
    behavior: ExtractedBehavior,
    occurred_at: Optional[datetime] = None,
    entry_id: Optional[str] = None,
    source_text: Optional[str] = None,
) -> Optional[str]:
    """Log a behavior for pattern analysis."""
    occurred_at = occurred_at or datetime.utcnow()

    try:
        result = await dbfetch(
            """
            INSERT INTO behavior_log (
                person_id, behavior_type, behavior_name,
                intensity, time_of_day, occurred_at,
                dosha_effect, effect_direction,
                source, related_entry_id, source_text
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            RETURNING id
            """,
            person_id,
            behavior.behavior_type,
            behavior.behavior_name,
            behavior.intensity,
            behavior.time_indication,
            occurred_at,
            behavior.dosha_effect,
            behavior.effect_direction,
            "inferred" if source_text else "explicit",
            entry_id,
            source_text,
            one=True,
        )
        return str(result["id"]) if result else None

    except Exception as e:
        logger.warning(f"Failed to log behavior: {e}")
        return None


async def log_symptom(
    person_id: str,
    symptom: ExtractedSymptom,
    occurred_at: Optional[datetime] = None,
    entry_id: Optional[str] = None,
    source_text: Optional[str] = None,
) -> Optional[str]:
    """Log a symptom for pattern analysis."""
    occurred_at = occurred_at or datetime.utcnow()

    try:
        result = await dbfetch(
            """
            INSERT INTO symptom_log (
                person_id, symptom_type, symptom_name,
                severity, time_of_day, occurred_at,
                likely_dosha, source, related_entry_id, source_text
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            RETURNING id
            """,
            person_id,
            symptom.symptom_type,
            symptom.symptom_name,
            symptom.severity,
            symptom.time_indication,
            occurred_at,
            symptom.likely_dosha,
            "inferred" if source_text else "explicit",
            entry_id,
            source_text,
            one=True,
        )
        return str(result["id"]) if result else None

    except Exception as e:
        logger.warning(f"Failed to log symptom: {e}")
        return None


# =============================================================================
# Pattern Detection
# =============================================================================

async def detect_patterns(
    person_id: str,
    lookback_days: int = 14,
) -> List[Dict[str, Any]]:
    """
    Analyze recent behaviors and symptoms to detect patterns.

    This is the core pattern learning function. It:
    1. Gets recent symptoms
    2. For each symptom, looks for preceding behaviors
    3. Records correlations that appear frequently

    Args:
        person_id: User ID
        lookback_days: How many days to analyze

    Returns:
        List of detected patterns
    """
    lookback = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    raw_matches = await _find_new_behavior_symptom_matches(person_id, lookback)
    if not raw_matches:
        return []

    recorded_matches = await _record_behavior_symptom_matches(person_id, raw_matches)
    if not recorded_matches:
        return []

    aggregated: Dict[
        Tuple[str, str, str, str, Optional[str]],
        Dict[str, Any],
    ] = {}
    for match in recorded_matches:
        key = (
            match["cause_type"],
            match["cause_value"],
            match["effect_type"],
            match["effect_value"],
            match.get("related_dosha"),
        )
        observed_at = match.get("observed_at") or datetime.now(timezone.utc)
        bucket = aggregated.get(key)
        if not bucket:
            aggregated[key] = {
                "cause_type": match["cause_type"],
                "cause_value": match["cause_value"],
                "effect_type": match["effect_type"],
                "effect_value": match["effect_value"],
                "related_dosha": match.get("related_dosha"),
                "increment": 1,
                "first_observed_at": observed_at,
                "last_observed_at": observed_at,
            }
            continue

        bucket["increment"] += 1
        if observed_at < bucket["first_observed_at"]:
            bucket["first_observed_at"] = observed_at
        if observed_at > bucket["last_observed_at"]:
            bucket["last_observed_at"] = observed_at

    detected_patterns: List[Dict[str, Any]] = []
    for pattern in aggregated.values():
        pattern_data = await _upsert_pattern(
            person_id=person_id,
            cause_type=pattern["cause_type"],
            cause_value=pattern["cause_value"],
            effect_type=pattern["effect_type"],
            effect_value=pattern["effect_value"],
            related_dosha=pattern.get("related_dosha"),
            increment=pattern["increment"],
            first_observed_at=pattern["first_observed_at"],
            last_observed_at=pattern["last_observed_at"],
        )
        if pattern_data:
            detected_patterns.append(pattern_data)

    return detected_patterns


async def _find_new_behavior_symptom_matches(
    person_id: str,
    lookback: datetime,
) -> List[Dict[str, Any]]:
    """Find behavior->symptom correlations that have not been recorded yet."""
    return await dbfetch(
        """
        SELECT
            b.id AS behavior_log_id,
            s.id AS symptom_log_id,
            b.behavior_type AS cause_type,
            b.behavior_name AS cause_value,
            s.symptom_type AS effect_type,
            s.symptom_name AS effect_value,
            b.dosha_effect AS related_dosha,
            s.occurred_at AS observed_at
        FROM symptom_log s
        JOIN behavior_log b
          ON b.person_id = s.person_id
         AND b.occurred_at BETWEEN s.occurred_at - INTERVAL '48 hours' AND s.occurred_at
         AND b.effect_direction = 'aggravates'
         AND b.dosha_effect IS NOT NULL
         AND b.dosha_effect = s.likely_dosha
        LEFT JOIN behavior_symptom_log l
          ON l.person_id = s.person_id
         AND l.behavior_log_id = b.id
         AND l.symptom_log_id = s.id
        WHERE s.person_id = $1
          AND s.occurred_at > $2
          AND s.likely_dosha IS NOT NULL
          AND l.id IS NULL
        ORDER BY s.occurred_at DESC, b.occurred_at DESC
        """,
        person_id,
        lookback,
    )


async def _record_behavior_symptom_matches(
    person_id: str,
    matches: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Persist new correlations so repeated scans remain idempotent."""
    if not matches:
        return []

    behavior_ids = [str(match["behavior_log_id"]) for match in matches]
    symptom_ids = [str(match["symptom_log_id"]) for match in matches]
    cause_types = [match["cause_type"] for match in matches]
    cause_values = [match["cause_value"] for match in matches]
    effect_types = [match["effect_type"] for match in matches]
    effect_values = [match["effect_value"] for match in matches]
    related_doshas = [match.get("related_dosha") for match in matches]
    observed_ats = [match.get("observed_at") or datetime.now(timezone.utc) for match in matches]

    return await dbfetch(
        """
        INSERT INTO behavior_symptom_log (
            person_id,
            behavior_log_id,
            symptom_log_id,
            cause_type,
            cause_value,
            effect_type,
            effect_value,
            related_dosha,
            observed_at
        )
        SELECT
            $1::uuid,
            data.behavior_log_id,
            data.symptom_log_id,
            data.cause_type,
            data.cause_value,
            data.effect_type,
            data.effect_value,
            data.related_dosha,
            data.observed_at
        FROM UNNEST(
            $2::uuid[],
            $3::uuid[],
            $4::text[],
            $5::text[],
            $6::text[],
            $7::text[],
            $8::text[],
            $9::timestamptz[]
        ) AS data(
            behavior_log_id,
            symptom_log_id,
            cause_type,
            cause_value,
            effect_type,
            effect_value,
            related_dosha,
            observed_at
        )
        ON CONFLICT (person_id, behavior_log_id, symptom_log_id) DO NOTHING
        RETURNING cause_type, cause_value, effect_type, effect_value, related_dosha, observed_at
        """,
        person_id,
        behavior_ids,
        symptom_ids,
        cause_types,
        cause_values,
        effect_types,
        effect_values,
        related_doshas,
        observed_ats,
    )


def _calculate_pattern_metrics(observation_count: int) -> Tuple[float, float]:
    """Compute correlation strength and confidence from the number of observations."""
    strength = min(0.95, 0.5 + (0.15 * math.log(observation_count + 1)))
    confidence = min(0.9, 0.3 + (0.1 * math.log(observation_count + 1)))
    return strength, confidence


async def _upsert_pattern(
    person_id: str,
    cause_type: str,
    cause_value: str,
    effect_type: str,
    effect_value: str,
    related_dosha: Optional[str] = None,
    ayurvedic_explanation: Optional[str] = None,
    evidence_snippet: Optional[str] = None,
    increment: int = 1,
    first_observed_at: Optional[datetime] = None,
    last_observed_at: Optional[datetime] = None,
) -> Optional[Dict[str, Any]]:
    """Upsert a pattern and return the updated data."""
    try:
        now = datetime.now(timezone.utc)
        first_seen = first_observed_at or now
        last_seen = last_observed_at or now

        # Check if pattern exists
        existing = await dbfetch(
            """
            SELECT id, observation_count, correlation_strength, confidence,
                   first_observed_at, last_observed_at, related_dosha
            FROM personal_patterns
            WHERE person_id = $1
              AND cause_type = $2 AND cause_value = $3
              AND effect_type = $4 AND effect_value = $5
            """,
            person_id,
            cause_type,
            cause_value,
            effect_type,
            effect_value,
            one=True,
        )

        if existing:
            # Update existing
            new_count = existing["observation_count"] + max(1, increment)
            new_strength, new_confidence = _calculate_pattern_metrics(new_count)
            current_first = existing.get("first_observed_at") or first_seen
            current_last = existing.get("last_observed_at") or last_seen

            await execute(
                """
                UPDATE personal_patterns
                SET observation_count = $1,
                    correlation_strength = $2,
                    confidence = $3,
                    first_observed_at = $4,
                    last_observed_at = $5,
                    related_dosha = COALESCE($6, related_dosha),
                    updated_at = now()
                WHERE id = $7
                """,
                new_count,
                new_strength,
                new_confidence,
                min(current_first, first_seen),
                max(current_last, last_seen),
                related_dosha or existing.get("related_dosha"),
                existing["id"],
            )

            return {
                "id": str(existing["id"]),
                "cause": f"{cause_type}:{cause_value}",
                "effect": f"{effect_type}:{effect_value}",
                "observation_count": new_count,
                "correlation_strength": new_strength,
                "status": "strengthened",
            }

        else:
            # Create new
            observation_count = max(1, increment)
            correlation_strength, confidence = _calculate_pattern_metrics(observation_count)
            result = await dbfetch(
                """
                INSERT INTO personal_patterns (
                    person_id, cause_type, cause_value, effect_type, effect_value,
                    correlation_strength, confidence, observation_count,
                    related_dosha, ayurvedic_explanation,
                    first_observed_at, last_observed_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                RETURNING id
                """,
                person_id,
                cause_type,
                cause_value,
                effect_type,
                effect_value,
                correlation_strength,
                confidence,
                observation_count,
                related_dosha,
                ayurvedic_explanation or _generate_ayurvedic_explanation(
                    cause_value, effect_value, related_dosha
                ),
                first_seen,
                last_seen,
                one=True,
            )

            return {
                "id": str(result["id"]) if result else None,
                "cause": f"{cause_type}:{cause_value}",
                "effect": f"{effect_type}:{effect_value}",
                "observation_count": observation_count,
                "correlation_strength": correlation_strength,
                "status": "new",
            }

    except Exception as e:
        logger.warning(f"Failed to upsert pattern: {e}")
        return None


def _generate_ayurvedic_explanation(
    cause: str,
    effect: str,
    dosha: Optional[str],
) -> str:
    """Generate basic Ayurvedic explanation for a cause-effect pattern."""
    if not dosha:
        return f"{cause.replace('_', ' ').title()} may contribute to {effect.replace('_', ' ')}."

    dosha_qualities = {
        "vata": "light, mobile, cold qualities",
        "pitta": "hot, sharp, intense qualities",
        "kapha": "heavy, slow, stable qualities",
    }

    return (
        f"{cause.replace('_', ' ').title()} increases {dosha}'s {dosha_qualities.get(dosha, 'qualities')}, "
        f"which can manifest as {effect.replace('_', ' ')}."
    )


# =============================================================================
# Main Processing Hook
# =============================================================================

async def process_entry_for_patterns(
    person_id: str,
    entry_text: str,
    entry_id: Optional[str] = None,
    entry_time: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Main entry point for pattern learning from journal entries.

    Call this during memory ingestion to:
    1. Extract behaviors and symptoms
    2. Log them
    3. Run pattern detection

    Args:
        person_id: User ID
        entry_text: Journal entry text
        entry_id: Optional entry ID
        entry_time: When the entry was written

    Returns:
        Processing result
    """
    result = {
        "entry_id": entry_id,
        "behaviors_logged": 0,
        "symptoms_logged": 0,
        "patterns_detected": [],
    }

    # 1. Extract behaviors and symptoms
    extraction = await extract_behaviors_and_symptoms(entry_text, person_id)

    # 2. Log behaviors
    entry_time = entry_time or datetime.utcnow()
    for behavior in extraction.behaviors:
        logged = await log_behavior(
            person_id=person_id,
            behavior=behavior,
            occurred_at=entry_time,
            entry_id=entry_id,
            source_text=entry_text[:200],  # Store snippet for reference
        )
        if logged:
            result["behaviors_logged"] += 1

    # 3. Log symptoms
    for symptom in extraction.symptoms:
        logged = await log_symptom(
            person_id=person_id,
            symptom=symptom,
            occurred_at=entry_time,
            entry_id=entry_id,
            source_text=entry_text[:200],
        )
        if logged:
            result["symptoms_logged"] += 1

    # 4. Run pattern detection (considers historical data)
    if result["behaviors_logged"] > 0 or result["symptoms_logged"] > 0:
        patterns = await detect_patterns(person_id, lookback_days=14)
        result["patterns_detected"] = patterns

    logger.info(
        "[PatternLearning] person=%s behaviors=%d symptoms=%d patterns=%d",
        person_id,
        result["behaviors_logged"],
        result["symptoms_logged"],
        len(result["patterns_detected"]),
    )

    return result


async def get_learned_patterns(
    person_id: str,
    min_confidence: float = 0.4,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """Get all learned patterns for a user."""
    results = await dbfetch(
        """
        SELECT cause_type, cause_value, effect_type, effect_value,
               correlation_strength, confidence, observation_count,
               ayurvedic_explanation, related_dosha,
               first_observed_at, last_observed_at
        FROM personal_patterns
        WHERE person_id = $1 AND confidence >= $2
        ORDER BY correlation_strength DESC, observation_count DESC
        LIMIT $3
        """,
        person_id,
        min_confidence,
        limit,
    )
    return list(results) if results else []


__all__ = [
    "extract_behaviors_and_symptoms",
    "log_behavior",
    "log_symptom",
    "detect_patterns",
    "process_entry_for_patterns",
    "get_learned_patterns",
    "ExtractionResult",
    "ExtractedBehavior",
    "ExtractedSymptom",
]
