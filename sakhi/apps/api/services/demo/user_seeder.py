"""
Demo User Seeder
----------------
Creates demo users with rich profiles for demonstrations.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, Optional

from sakhi.apps.api.core.db import q as dbfetch, exec as dbexec

LOGGER = logging.getLogger(__name__)

# Stable demo user ID for consistent testing
DEMO_USER_ID = "demo-user-sakhi-001"
DEMO_ENTITY_ID = "demo-entity-sakhi-001"
DEMO_MOM_USER_ID = "demo-mom-sakhi-001"
DEMO_MOM_ENTITY_ID = "demo-mom-entity-001"
DEMO_RESTAURANT_ENTITY_ID = "demo-restaurant-001"


async def seed_demo_user(
    user_id: Optional[str] = None,
    name: str = "Alex",
    profile: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Create or update a demo user with a rich profile.

    Returns the user's person_id.
    """
    user_id = user_id or DEMO_USER_ID

    default_profile = {
        "name": name,
        "dosha": {
            "prakruti": {"vata": 0.4, "pitta": 0.35, "kapha": 0.25},
            "current_vikriti": {"vata": 0.55, "pitta": 0.30, "kapha": 0.15},
        },
        "location": "San Francisco, CA",
        "timezone": "America/Los_Angeles",
        "occupation": "Software Engineer",
        "dietary": {
            "vegetarian": False,
            "allergies": ["shellfish"],
            "preferences": ["healthy", "local"],
        },
    }

    final_profile = {**default_profile, **(profile or {})}

    # Upsert person
    await dbexec(
        """
        INSERT INTO persons (id, profile, created_at, updated_at)
        VALUES ($1, $2::jsonb, NOW(), NOW())
        ON CONFLICT (id) DO UPDATE
        SET profile = $2::jsonb, updated_at = NOW()
        """,
        user_id,
        final_profile,
    )

    # Create Sakhi entity
    await dbexec(
        """
        INSERT INTO sakhi_entities (id, person_id, display_name, entity_type, is_verified, created_at)
        VALUES ($1, $2, $3, 'person', TRUE, NOW())
        ON CONFLICT (id) DO UPDATE
        SET display_name = $3, updated_at = NOW()
        """,
        DEMO_ENTITY_ID if user_id == DEMO_USER_ID else str(uuid.uuid4()),
        user_id,
        name,
    )

    LOGGER.info("[demo] Seeded user: %s (%s)", name, user_id)
    return user_id


async def seed_demo_mom(
    name: str = "Mom",
    profile: Optional[Dict[str, Any]] = None,
) -> str:
    """Create demo mom user for mesh coordination demo."""
    default_profile = {
        "name": name,
        "relationship_to_demo_user": "mother",
        "location": "Los Angeles, CA",
        "timezone": "America/Los_Angeles",
        "dietary": {
            "vegetarian": True,
            "preferences": ["home-cooked", "traditional"],
        },
    }

    final_profile = {**default_profile, **(profile or {})}

    await dbexec(
        """
        INSERT INTO persons (id, profile, created_at, updated_at)
        VALUES ($1, $2::jsonb, NOW(), NOW())
        ON CONFLICT (id) DO UPDATE
        SET profile = $2::jsonb, updated_at = NOW()
        """,
        DEMO_MOM_USER_ID,
        final_profile,
    )

    await dbexec(
        """
        INSERT INTO sakhi_entities (id, person_id, display_name, entity_type, is_verified, created_at)
        VALUES ($1, $2, $3, 'person', TRUE, NOW())
        ON CONFLICT (id) DO UPDATE
        SET display_name = $3, updated_at = NOW()
        """,
        DEMO_MOM_ENTITY_ID,
        DEMO_MOM_USER_ID,
        name,
    )

    # Create connection between demo user and mom
    await dbexec(
        """
        INSERT INTO mesh_connections (
            entity_a_id, entity_b_id, trust_level, connection_type, status, created_at
        )
        VALUES ($1, $2, 'full', 'family', 'active', NOW())
        ON CONFLICT (entity_a_id, entity_b_id) DO NOTHING
        """,
        DEMO_ENTITY_ID,
        DEMO_MOM_ENTITY_ID,
    )

    LOGGER.info("[demo] Seeded mom: %s", name)
    return DEMO_MOM_USER_ID


async def seed_demo_restaurant(
    name: str = "The Golden Gate Bistro",
    cuisine: str = "California Modern",
) -> str:
    """Create demo restaurant entity for business mesh demo."""
    await dbexec(
        """
        INSERT INTO sakhi_entities (
            id, display_name, entity_type, is_verified,
            business_info, created_at
        )
        VALUES ($1, $2, 'business', TRUE, $3::jsonb, NOW())
        ON CONFLICT (id) DO UPDATE
        SET display_name = $2, business_info = $3::jsonb, updated_at = NOW()
        """,
        DEMO_RESTAURANT_ENTITY_ID,
        name,
        {
            "type": "restaurant",
            "cuisine": cuisine,
            "location": "2847 California St, San Francisco",
            "accepts_reservations": True,
            "opening_hours": {"mon-fri": "11:00-22:00", "sat-sun": "10:00-23:00"},
            "capacity": 60,
            "features": ["outdoor_seating", "private_dining", "wine_bar"],
        },
    )

    # Create connection between demo user and restaurant
    await dbexec(
        """
        INSERT INTO mesh_connections (
            entity_a_id, entity_b_id, trust_level, connection_type, status, created_at
        )
        VALUES ($1, $2, 'standard', 'business', 'active', NOW())
        ON CONFLICT (entity_a_id, entity_b_id) DO NOTHING
        """,
        DEMO_ENTITY_ID,
        DEMO_RESTAURANT_ENTITY_ID,
    )

    LOGGER.info("[demo] Seeded restaurant: %s", name)
    return DEMO_RESTAURANT_ENTITY_ID


async def get_demo_user_id() -> str:
    """Get the demo user ID, creating if needed."""
    row = await dbfetch(
        "SELECT id FROM persons WHERE id = $1",
        DEMO_USER_ID,
        one=True,
    )

    if not row:
        await seed_demo_user()

    return DEMO_USER_ID


async def seed_all_demo_entities() -> Dict[str, str]:
    """Seed all demo entities for full demo."""
    user_id = await seed_demo_user()
    mom_id = await seed_demo_mom()
    restaurant_id = await seed_demo_restaurant()

    return {
        "user_id": user_id,
        "user_entity_id": DEMO_ENTITY_ID,
        "mom_id": mom_id,
        "mom_entity_id": DEMO_MOM_ENTITY_ID,
        "restaurant_entity_id": restaurant_id,
    }


__all__ = [
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
]
