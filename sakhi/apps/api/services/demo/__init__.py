"""
Sakhi Demo Infrastructure
--------------------------
Seeders and mock runners for real demo functionality.

This module provides:
- User seeder: Create demo users with rich profiles
- Preference seeder: Populate sensory preferences
- Pattern seeder: Create patterns for causal reasoning
- Vision demo: Run vision loop with mock/pre-recorded screenshots
- Coordination demo: Orchestrate mesh coordination between two Sakhis

Usage:
    from sakhi.apps.api.services.demo import (
        seed_demo_user,
        seed_demo_preferences,
        seed_demo_patterns,
        run_vision_demo,
        run_coordination_demo,
        seed_all_demo_data,
    )
"""

import logging
from typing import Any, Dict

LOGGER = logging.getLogger(__name__)

# Re-export from submodules
from sakhi.apps.api.services.demo.user_seeder import (
    seed_demo_user,
    seed_demo_mom,
    seed_demo_restaurant,
    get_demo_user_id,
    seed_all_demo_entities,
    DEMO_USER_ID,
    DEMO_ENTITY_ID,
    DEMO_MOM_USER_ID,
    DEMO_MOM_ENTITY_ID,
    DEMO_RESTAURANT_ENTITY_ID,
)
from sakhi.apps.api.services.demo.preference_seeder import (
    seed_demo_preferences,
    seed_dining_preferences,
    seed_product_preferences,
)
from sakhi.apps.api.services.demo.pattern_seeder import (
    seed_demo_patterns,
    seed_demo_behaviors,
    seed_demo_episodes,
    seed_all_causal_data,
)
from sakhi.apps.api.services.demo.vision_demo import (
    run_vision_demo,
    VisionDemoConfig,
    VisionDemoRunner,
    DemoMode,
)
from sakhi.apps.api.services.demo.coordination_demo import (
    run_coordination_demo,
    CoordinationDemoConfig,
    CoordinationDemoRunner,
    CoordinationScenario,
)


async def seed_all_demo_data(person_id: str = DEMO_USER_ID) -> Dict[str, Any]:
    """
    Seed ALL demo data for a complete working demo.

    This is the master function to prepare the database for demos.
    Call this once before running any demos.

    Returns:
        Summary of what was seeded
    """
    LOGGER.info("[demo] Seeding all demo data...")

    # 1. Seed entities (user, mom, restaurant)
    entities = await seed_all_demo_entities()

    # 2. Seed preferences for demo user
    await seed_demo_preferences(person_id)

    # 3. Seed patterns and behaviors for causal reasoning
    await seed_all_causal_data(person_id)

    LOGGER.info("[demo] All demo data seeded successfully!")

    return {
        "status": "seeded",
        "entities": entities,
        "preferences": "seeded",
        "patterns": "seeded",
        "behaviors": "seeded",
        "episodes": "seeded",
    }


async def run_full_demo(
    demo_type: str = "all",  # "vision", "coordination_personal", "coordination_business", "reflection", "all"
) -> Dict[str, Any]:
    """
    Run a complete demo sequence.

    Args:
        demo_type: Which demo to run

    Returns:
        Results from the demo(s)
    """
    results = {}

    if demo_type in ("vision", "all"):
        LOGGER.info("[demo] Running vision demo...")
        results["vision"] = await run_vision_demo(
            task="Find a car perfume on Amazon",
            mode=DemoMode.SIMULATED,
            person_id=DEMO_USER_ID,
        )

    if demo_type in ("coordination_personal", "all"):
        LOGGER.info("[demo] Running personal coordination demo...")
        results["coordination_personal"] = await run_coordination_demo(
            scenario=CoordinationScenario.PERSONAL_DINNER,
        )

    if demo_type in ("coordination_business", "all"):
        LOGGER.info("[demo] Running business coordination demo...")
        results["coordination_business"] = await run_coordination_demo(
            scenario=CoordinationScenario.BUSINESS_RESERVATION,
        )

    if demo_type in ("reflection", "all"):
        LOGGER.info("[demo] Running reflection demo...")
        from sakhi.apps.api.services.ayurveda.causal_reasoning import explain_symptom
        explanation = await explain_symptom(
            person_id=DEMO_USER_ID,
            symptom="scattered",
        )
        results["reflection"] = {
            "symptom": explanation.symptom,
            "dosha_context": explanation.dosha_context,
            "primary_causes": [c.dict() for c in explanation.primary_causes],
            "contributing_factors": [c.dict() for c in explanation.contributing_factors],
            "explanation": explanation.explanation_text,
        }

    return results


__all__ = [
    # User seeding
    "seed_demo_user",
    "seed_demo_mom",
    "seed_demo_restaurant",
    "get_demo_user_id",
    "seed_all_demo_entities",
    "DEMO_USER_ID",
    "DEMO_ENTITY_ID",
    "DEMO_MOM_USER_ID",
    "DEMO_MOM_ENTITY_ID",
    "DEMO_RESTAURANT_ENTITY_ID",
    # Preference seeding
    "seed_demo_preferences",
    "seed_dining_preferences",
    "seed_product_preferences",
    # Pattern seeding
    "seed_demo_patterns",
    "seed_demo_behaviors",
    "seed_demo_episodes",
    "seed_all_causal_data",
    # Vision demo
    "run_vision_demo",
    "VisionDemoConfig",
    "VisionDemoRunner",
    "DemoMode",
    # Coordination demo
    "run_coordination_demo",
    "CoordinationDemoConfig",
    "CoordinationDemoRunner",
    "CoordinationScenario",
    # Master functions
    "seed_all_demo_data",
    "run_full_demo",
]
