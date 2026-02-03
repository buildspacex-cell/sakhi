"""
Demo Preference Seeder
----------------------
Seeds sensory preferences for demo users.

This creates the rich personalization that makes Sakhi feel like it truly knows you.
"""

from __future__ import annotations

import logging
from typing import Optional

from sakhi.apps.api.services.memory.sensory_preferences import (
    SensoryCategory,
    PreferenceStrength,
    update_sensory_preference,
    set_temperature_preference,
    set_texture_preference,
    set_spice_tolerance,
    set_ambiance_preference,
)
from sakhi.apps.api.services.demo.user_seeder import DEMO_USER_ID

LOGGER = logging.getLogger(__name__)


async def seed_demo_preferences(person_id: Optional[str] = None) -> None:
    """
    Seed all demo preferences for a user.

    Creates a complete sensory profile that demonstrates Sakhi's
    deep personalization capabilities.
    """
    person_id = person_id or DEMO_USER_ID

    await seed_dining_preferences(person_id)
    await seed_product_preferences(person_id)

    LOGGER.info("[demo] Seeded all preferences for %s", person_id[:8])


async def seed_dining_preferences(person_id: Optional[str] = None) -> None:
    """
    Seed dining-related sensory preferences.

    These are used for restaurant recommendations and food ordering.
    """
    person_id = person_id or DEMO_USER_ID

    # Temperature preferences
    await set_temperature_preference(
        person_id=person_id,
        item_type="drinks",
        preference="hot",
        strength=PreferenceStrength.STRONG,
        source="demo_seed",
    )
    await set_temperature_preference(
        person_id=person_id,
        item_type="coffee",
        preference="very_hot",
        strength=PreferenceStrength.MUST_HAVE,
        source="demo_seed",
    )
    await set_temperature_preference(
        person_id=person_id,
        item_type="soup",
        preference="hot",
        strength=PreferenceStrength.MODERATE,
        source="demo_seed",
    )
    await set_temperature_preference(
        person_id=person_id,
        item_type="salad",
        preference="cold",
        strength=PreferenceStrength.SLIGHT,
        source="demo_seed",
    )

    # Texture preferences
    await set_texture_preference(
        person_id=person_id,
        texture="crunchy",
        preference="love",
        strength=PreferenceStrength.STRONG,
        source="demo_seed",
    )
    await set_texture_preference(
        person_id=person_id,
        texture="crispy",
        preference="love",
        strength=PreferenceStrength.STRONG,
        source="demo_seed",
    )
    await set_texture_preference(
        person_id=person_id,
        texture="chewy",
        preference="like",
        strength=PreferenceStrength.MODERATE,
        source="demo_seed",
    )
    await set_texture_preference(
        person_id=person_id,
        texture="mushy",
        preference="avoid",
        strength=PreferenceStrength.STRONG,
        source="demo_seed",
    )

    # Spice tolerance
    await set_spice_tolerance(
        person_id=person_id,
        level="medium",
        strength=PreferenceStrength.MODERATE,
        source="demo_seed",
    )
    await set_spice_tolerance(
        person_id=person_id,
        level="hot",
        cuisine_context="thai",
        strength=PreferenceStrength.MODERATE,
        source="demo_seed",
    )
    await set_spice_tolerance(
        person_id=person_id,
        level="medium",
        cuisine_context="indian",
        strength=PreferenceStrength.MODERATE,
        source="demo_seed",
    )

    # Ambiance preferences
    await set_ambiance_preference(
        person_id=person_id,
        aspect="noise",
        preference="quiet",
        strength=PreferenceStrength.STRONG,
        source="demo_seed",
    )
    await set_ambiance_preference(
        person_id=person_id,
        aspect="lighting",
        preference="dim",
        strength=PreferenceStrength.MODERATE,
        source="demo_seed",
    )
    await set_ambiance_preference(
        person_id=person_id,
        aspect="seating",
        preference="booth",
        strength=PreferenceStrength.STRONG,
        source="demo_seed",
    )
    await set_ambiance_preference(
        person_id=person_id,
        aspect="crowd",
        preference="moderate",
        strength=PreferenceStrength.SLIGHT,
        source="demo_seed",
    )

    # Portion preferences
    await update_sensory_preference(
        person_id=person_id,
        category=SensoryCategory.PORTION,
        preference="size",
        value="regular",
        strength=PreferenceStrength.SLIGHT,
        source="demo_seed",
    )
    await update_sensory_preference(
        person_id=person_id,
        category=SensoryCategory.PORTION,
        preference="shareable",
        value="prefer",
        strength=PreferenceStrength.MODERATE,
        source="demo_seed",
    )

    # Service preferences
    await update_sensory_preference(
        person_id=person_id,
        category=SensoryCategory.SERVICE,
        preference="pace",
        value="relaxed",
        strength=PreferenceStrength.MODERATE,
        source="demo_seed",
    )
    await update_sensory_preference(
        person_id=person_id,
        category=SensoryCategory.SERVICE,
        preference="attentiveness",
        value="present_but_not_hovering",
        strength=PreferenceStrength.STRONG,
        source="demo_seed",
    )

    # Flavor preferences
    await update_sensory_preference(
        person_id=person_id,
        category=SensoryCategory.FLAVOR,
        preference="umami",
        value="love",
        strength=PreferenceStrength.STRONG,
        source="demo_seed",
    )
    await update_sensory_preference(
        person_id=person_id,
        category=SensoryCategory.FLAVOR,
        preference="sweet",
        value="moderate",
        strength=PreferenceStrength.SLIGHT,
        source="demo_seed",
    )
    await update_sensory_preference(
        person_id=person_id,
        category=SensoryCategory.FLAVOR,
        preference="sour",
        value="enjoy",
        strength=PreferenceStrength.MODERATE,
        source="demo_seed",
    )
    await update_sensory_preference(
        person_id=person_id,
        category=SensoryCategory.FLAVOR,
        preference="bitter",
        value="appreciate",
        strength=PreferenceStrength.SLIGHT,
        context="in coffee and dark chocolate",
        source="demo_seed",
    )

    LOGGER.info("[demo] Seeded dining preferences for %s", person_id[:8])


async def seed_product_preferences(person_id: Optional[str] = None) -> None:
    """
    Seed product-related sensory preferences.

    These are used for product recommendations and shopping.
    """
    person_id = person_id or DEMO_USER_ID

    # Scent preferences (for car perfume demo)
    await update_sensory_preference(
        person_id=person_id,
        category=SensoryCategory.FLAVOR,  # Using flavor for scent
        preference="scent_woody",
        value="love",
        strength=PreferenceStrength.STRONG,
        context="car_perfume",
        source="demo_seed",
    )
    await update_sensory_preference(
        person_id=person_id,
        category=SensoryCategory.FLAVOR,
        preference="scent_citrus",
        value="like",
        strength=PreferenceStrength.MODERATE,
        context="car_perfume",
        source="demo_seed",
    )
    await update_sensory_preference(
        person_id=person_id,
        category=SensoryCategory.FLAVOR,
        preference="scent_floral",
        value="avoid",
        strength=PreferenceStrength.STRONG,
        context="car_perfume",
        source="demo_seed",
    )
    await update_sensory_preference(
        person_id=person_id,
        category=SensoryCategory.FLAVOR,
        preference="scent_vanilla",
        value="neutral",
        strength=PreferenceStrength.SLIGHT,
        context="car_perfume",
        source="demo_seed",
    )
    await update_sensory_preference(
        person_id=person_id,
        category=SensoryCategory.FLAVOR,
        preference="scent_musk",
        value="like",
        strength=PreferenceStrength.MODERATE,
        context="car_perfume",
        source="demo_seed",
    )

    # Visual preferences (for product recommendations)
    await update_sensory_preference(
        person_id=person_id,
        category=SensoryCategory.VISUAL,
        preference="color_palette",
        value="earth_tones",
        strength=PreferenceStrength.MODERATE,
        source="demo_seed",
    )
    await update_sensory_preference(
        person_id=person_id,
        category=SensoryCategory.VISUAL,
        preference="style",
        value="minimalist",
        strength=PreferenceStrength.STRONG,
        source="demo_seed",
    )
    await update_sensory_preference(
        person_id=person_id,
        category=SensoryCategory.VISUAL,
        preference="finish",
        value="matte",
        strength=PreferenceStrength.MODERATE,
        source="demo_seed",
    )

    LOGGER.info("[demo] Seeded product preferences for %s", person_id[:8])


__all__ = [
    "seed_demo_preferences",
    "seed_dining_preferences",
    "seed_product_preferences",
]
