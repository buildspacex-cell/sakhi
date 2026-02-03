"""
Demo Pattern & Behavior Seeder
------------------------------
Seeds personal patterns and recent behaviors for causal reasoning demo.

This enables the "Why am I feeling X?" and "Last time..." features.
"""

from __future__ import annotations

import logging
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from sakhi.apps.api.core.db import exec as dbexec
from sakhi.apps.api.services.demo.user_seeder import DEMO_USER_ID

LOGGER = logging.getLogger(__name__)


async def seed_demo_patterns(person_id: Optional[str] = None) -> None:
    """
    Seed personal patterns for causal reasoning.

    These patterns represent learned correlations:
    - "When you do X, you tend to feel Y"
    - Used by explain_symptom() to answer "Why am I feeling X?"
    """
    person_id = person_id or DEMO_USER_ID

    patterns = [
        # Vata-aggravating patterns (anxiety, scattered, restless)
        {
            "cause_type": "behavior",
            "cause_value": "late_dinner",
            "effect_type": "symptom",
            "effect_value": "scattered",
            "correlation_strength": 0.75,
            "confidence": 0.8,
            "observation_count": 12,
            "ayurvedic_explanation": "Eating late disturbs Vata, disrupting sleep and mental clarity next day",
            "related_dosha": "vata",
        },
        {
            "cause_type": "behavior",
            "cause_value": "excessive_travel",
            "effect_type": "symptom",
            "effect_value": "anxiety",
            "correlation_strength": 0.8,
            "confidence": 0.85,
            "observation_count": 8,
            "ayurvedic_explanation": "Movement and irregular routines increase Vata energy",
            "related_dosha": "vata",
        },
        {
            "cause_type": "behavior",
            "cause_value": "skipped_meals",
            "effect_type": "symptom",
            "effect_value": "restless",
            "correlation_strength": 0.7,
            "confidence": 0.75,
            "observation_count": 15,
            "ayurvedic_explanation": "Irregular eating destabilizes Vata, causing restlessness",
            "related_dosha": "vata",
        },
        {
            "cause_type": "behavior",
            "cause_value": "cold_drinks_morning",
            "effect_type": "symptom",
            "effect_value": "bloating",
            "correlation_strength": 0.65,
            "confidence": 0.7,
            "observation_count": 6,
            "ayurvedic_explanation": "Cold dampens digestive fire, Vata causes gas",
            "related_dosha": "vata",
        },
        # Pitta-aggravating patterns (irritable, intense)
        {
            "cause_type": "behavior",
            "cause_value": "working_through_lunch",
            "effect_type": "symptom",
            "effect_value": "irritable",
            "correlation_strength": 0.85,
            "confidence": 0.9,
            "observation_count": 20,
            "ayurvedic_explanation": "Skipping lunch when Pitta is highest (10am-2pm) causes heat buildup",
            "related_dosha": "pitta",
        },
        {
            "cause_type": "behavior",
            "cause_value": "spicy_dinner",
            "effect_type": "symptom",
            "effect_value": "intense",
            "correlation_strength": 0.6,
            "confidence": 0.65,
            "observation_count": 9,
            "ayurvedic_explanation": "Spicy food increases internal heat and Pitta aggression",
            "related_dosha": "pitta",
        },
        # Kapha-aggravating patterns (sluggish, heavy)
        {
            "cause_type": "behavior",
            "cause_value": "heavy_breakfast",
            "effect_type": "symptom",
            "effect_value": "sluggish",
            "correlation_strength": 0.7,
            "confidence": 0.75,
            "observation_count": 11,
            "ayurvedic_explanation": "Heavy morning meals when Kapha is dominant causes sluggishness",
            "related_dosha": "kapha",
        },
        {
            "cause_type": "behavior",
            "cause_value": "no_exercise",
            "effect_type": "symptom",
            "effect_value": "heavy",
            "correlation_strength": 0.8,
            "confidence": 0.85,
            "observation_count": 18,
            "ayurvedic_explanation": "Lack of movement allows Kapha to accumulate",
            "related_dosha": "kapha",
        },
        # Positive patterns (what helps)
        {
            "cause_type": "behavior",
            "cause_value": "morning_walk",
            "effect_type": "symptom",
            "effect_value": "centered",
            "correlation_strength": 0.85,
            "confidence": 0.9,
            "observation_count": 25,
            "ayurvedic_explanation": "Gentle morning movement balances all doshas",
            "related_dosha": None,
        },
        {
            "cause_type": "behavior",
            "cause_value": "warm_water_morning",
            "effect_type": "symptom",
            "effect_value": "clear_mind",
            "correlation_strength": 0.7,
            "confidence": 0.8,
            "observation_count": 30,
            "ayurvedic_explanation": "Warm water kindles digestive fire and clears Kapha",
            "related_dosha": None,
        },
    ]

    for pattern in patterns:
        await dbexec(
            """
            INSERT INTO personal_patterns (
                person_id, cause_type, cause_value, effect_type, effect_value,
                correlation_strength, confidence, observation_count,
                ayurvedic_explanation, related_dosha, last_observed_at, created_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, NOW(), NOW())
            ON CONFLICT (person_id, cause_type, cause_value, effect_type, effect_value)
            DO UPDATE SET
                correlation_strength = $6,
                confidence = $7,
                observation_count = $8,
                ayurvedic_explanation = $9,
                last_observed_at = NOW()
            """,
            person_id,
            pattern["cause_type"],
            pattern["cause_value"],
            pattern["effect_type"],
            pattern["effect_value"],
            pattern["correlation_strength"],
            pattern["confidence"],
            pattern["observation_count"],
            pattern["ayurvedic_explanation"],
            pattern.get("related_dosha"),
        )

    LOGGER.info("[demo] Seeded %d patterns for %s", len(patterns), person_id[:8])


async def seed_demo_behaviors(
    person_id: Optional[str] = None,
    days_back: int = 3,
) -> None:
    """
    Seed recent behaviors for causal reasoning.

    These behaviors are what happened in the last 48-72 hours
    that might explain current symptoms.
    """
    person_id = person_id or DEMO_USER_ID
    now = datetime.utcnow()

    behaviors = [
        # Yesterday evening
        {
            "behavior_type": "food",
            "behavior_name": "late_dinner",
            "occurred_at": now - timedelta(hours=14),
            "dosha_effect": "vata",
            "effect_direction": "aggravates",
            "intensity": "moderate",
            "source_text": "Had dinner at 10pm after working late",
        },
        {
            "behavior_type": "food",
            "behavior_name": "cold_drinks_evening",
            "occurred_at": now - timedelta(hours=15),
            "dosha_effect": "vata",
            "effect_direction": "aggravates",
            "intensity": "mild",
            "source_text": "Had iced tea with dinner",
        },
        # Two days ago
        {
            "behavior_type": "exercise",
            "behavior_name": "no_exercise",
            "occurred_at": now - timedelta(hours=36),
            "dosha_effect": "kapha",
            "effect_direction": "aggravates",
            "intensity": "moderate",
            "source_text": "Skipped gym due to meetings",
        },
        {
            "behavior_type": "food",
            "behavior_name": "working_through_lunch",
            "occurred_at": now - timedelta(hours=28),
            "dosha_effect": "pitta",
            "effect_direction": "aggravates",
            "intensity": "moderate",
            "source_text": "Had a protein bar at desk instead of proper lunch",
        },
        # Three days ago (positive behaviors for contrast)
        {
            "behavior_type": "exercise",
            "behavior_name": "morning_walk",
            "occurred_at": now - timedelta(hours=60),
            "dosha_effect": None,
            "effect_direction": "balances",
            "intensity": "moderate",
            "source_text": "30 minute walk in the park before work",
        },
        {
            "behavior_type": "food",
            "behavior_name": "warm_breakfast",
            "occurred_at": now - timedelta(hours=59),
            "dosha_effect": None,
            "effect_direction": "balances",
            "intensity": "moderate",
            "source_text": "Had oatmeal with warm spices",
        },
    ]

    for behavior in behaviors:
        await dbexec(
            """
            INSERT INTO behavior_log (
                person_id, behavior_type, behavior_name, occurred_at,
                dosha_effect, effect_direction, intensity, source_text, created_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
            ON CONFLICT DO NOTHING
            """,
            person_id,
            behavior["behavior_type"],
            behavior["behavior_name"],
            behavior["occurred_at"],
            behavior["dosha_effect"],
            behavior["effect_direction"],
            behavior["intensity"],
            behavior["source_text"],
        )

    LOGGER.info("[demo] Seeded %d behaviors for %s", len(behaviors), person_id[:8])


async def seed_demo_episodes(person_id: Optional[str] = None) -> None:
    """
    Seed past episodes for "last time" lookups.

    These are historical instances of symptoms and what helped.
    """
    person_id = person_id or DEMO_USER_ID
    now = datetime.utcnow()

    episodes = [
        # "Last time I felt scattered"
        {
            "symptom": "scattered",
            "occurred_at": now - timedelta(days=14),
            "duration_hours": 48,
            "likely_cause": "travel_and_irregular_schedule",
            "what_helped": ["morning walks", "warm meals", "early bedtime"],
            "recovery_time_hours": 48,
            "notes": "Felt scattered after LA trip. Grounding routine helped within 2 days.",
        },
        # "Last time I felt anxious"
        {
            "symptom": "anxiety",
            "occurred_at": now - timedelta(days=21),
            "duration_hours": 72,
            "likely_cause": "work_deadline_and_poor_sleep",
            "what_helped": ["breathing exercises", "reduced caffeine", "nature walk"],
            "recovery_time_hours": 72,
            "notes": "Anxiety before quarterly review. Breathing and nature helped most.",
        },
        # "Last time I felt sluggish"
        {
            "symptom": "sluggish",
            "occurred_at": now - timedelta(days=7),
            "duration_hours": 24,
            "likely_cause": "heavy_dinner_and_no_exercise",
            "what_helped": ["light breakfast", "morning exercise", "ginger tea"],
            "recovery_time_hours": 24,
            "notes": "Felt heavy after weekend. Light eating and movement cleared it by evening.",
        },
    ]

    for episode in episodes:
        await dbexec(
            """
            INSERT INTO symptom_episodes (
                person_id, symptom, occurred_at, duration_hours,
                likely_cause, what_helped, recovery_time_hours, notes, created_at
            )
            VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7, $8, NOW())
            ON CONFLICT DO NOTHING
            """,
            person_id,
            episode["symptom"],
            episode["occurred_at"],
            episode["duration_hours"],
            episode["likely_cause"],
            json.dumps(episode["what_helped"]),
            episode["recovery_time_hours"],
            episode["notes"],
        )

    LOGGER.info("[demo] Seeded %d episodes for %s", len(episodes), person_id[:8])


async def seed_all_causal_data(person_id: Optional[str] = None) -> None:
    """Seed all data needed for causal reasoning demo."""
    person_id = person_id or DEMO_USER_ID

    await seed_demo_patterns(person_id)
    await seed_demo_behaviors(person_id)
    await seed_demo_episodes(person_id)

    LOGGER.info("[demo] Seeded all causal reasoning data for %s", person_id[:8])


__all__ = [
    "seed_demo_patterns",
    "seed_demo_behaviors",
    "seed_demo_episodes",
    "seed_all_causal_data",
]
