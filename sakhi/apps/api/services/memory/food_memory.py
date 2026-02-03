"""
Food Memory Service
-------------------
Tracks what someone eats, where, and how they felt about it.

This is Sakhi's "food diary" for each person:
- Meals eaten (what, where, when)
- Dish experiences (loved it, hated it, want again)
- Restaurant visits (which ones, how often, favorites)
- Food discoveries (new cuisines tried, surprises)

Combined with sensory preferences, this enables Sakhi to:
- Remember "You loved the pad thai at Thai House last month"
- Notice patterns "You've been eating Italian a lot lately"
- Make informed suggestions "Remember you wanted to try that ramen place?"
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum

from pydantic import BaseModel, Field

from sakhi.apps.api.core.db import q as dbfetch, exec as dbexec

LOGGER = logging.getLogger(__name__)


# =============================================================================
# Food Memory Models
# =============================================================================

class MealType(str, Enum):
    """Type of meal."""
    BREAKFAST = "breakfast"
    BRUNCH = "brunch"
    LUNCH = "lunch"
    DINNER = "dinner"
    SNACK = "snack"
    DESSERT = "dessert"
    DRINKS = "drinks"


class DiningContext(str, Enum):
    """Context of the dining experience."""
    SOLO = "solo"
    DATE = "date"
    FRIENDS = "friends"
    FAMILY = "family"
    BUSINESS = "business"
    CELEBRATION = "celebration"
    CASUAL = "casual"


class Rating(str, Enum):
    """Simple rating scale."""
    LOVED = "loved"  # Want again, would recommend
    LIKED = "liked"  # Good, would have again
    OKAY = "okay"  # Fine but not memorable
    DISLIKED = "disliked"  # Wouldn't order again
    HATED = "hated"  # Never again


class FoodExperience(BaseModel):
    """A single food/dining experience."""
    id: Optional[str] = None
    person_id: str
    dish_name: str
    cuisine: Optional[str] = None
    restaurant_name: Optional[str] = None
    restaurant_location: Optional[str] = None
    meal_type: Optional[MealType] = None
    context: Optional[DiningContext] = None
    rating: Optional[Rating] = None
    notes: Optional[str] = None
    date: Optional[datetime] = None
    companions: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    want_again: bool = False
    price_paid: Optional[float] = None


class RestaurantMemory(BaseModel):
    """Memory of a restaurant."""
    name: str
    location: Optional[str] = None
    cuisine: Optional[str] = None
    visit_count: int = 0
    last_visit: Optional[datetime] = None
    average_rating: Optional[float] = None
    favorite_dishes: List[str] = Field(default_factory=list)
    notes: Optional[str] = None
    want_to_return: bool = True


class CuisineExperience(BaseModel):
    """Summary of experience with a cuisine."""
    cuisine: str
    times_eaten: int = 0
    average_rating: Optional[float] = None
    favorite_dishes: List[str] = Field(default_factory=list)
    last_eaten: Optional[datetime] = None


# =============================================================================
# Food Experience Storage
# =============================================================================

async def record_meal(
    person_id: str,
    dish_name: str,
    *,
    cuisine: Optional[str] = None,
    restaurant_name: Optional[str] = None,
    restaurant_location: Optional[str] = None,
    meal_type: Optional[MealType] = None,
    context: Optional[DiningContext] = None,
    rating: Optional[Rating] = None,
    notes: Optional[str] = None,
    companions: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    want_again: bool = False,
    date: Optional[datetime] = None,
) -> str:
    """
    Record a food experience.

    Returns the experience ID.
    """
    experience_date = date or datetime.utcnow()

    row = await dbfetch(
        """
        INSERT INTO food_experiences (
            person_id, dish_name, cuisine, restaurant_name, restaurant_location,
            meal_type, context, rating, notes, companions, tags, want_again,
            experience_date
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10::jsonb, $11::jsonb, $12, $13)
        RETURNING id
        """,
        person_id,
        dish_name,
        cuisine,
        restaurant_name,
        restaurant_location,
        meal_type.value if meal_type else None,
        context.value if context else None,
        rating.value if rating else None,
        notes,
        json.dumps(companions or []),
        json.dumps(tags or []),
        want_again,
        experience_date,
        one=True,
    )

    exp_id = str(row["id"])

    LOGGER.info(
        "[food] Recorded %s at %s for %s (rating: %s)",
        dish_name,
        restaurant_name or "home",
        person_id[:8],
        rating.value if rating else "unrated",
    )

    # Update restaurant memory if applicable
    if restaurant_name:
        await _update_restaurant_memory(person_id, restaurant_name, restaurant_location, cuisine)

    return exp_id


async def get_recent_meals(
    person_id: str,
    limit: int = 10,
    days: int = 30,
) -> List[FoodExperience]:
    """Get recent meals for a person."""
    since = datetime.utcnow() - timedelta(days=days)

    rows = await dbfetch(
        """
        SELECT * FROM food_experiences
        WHERE person_id = $1 AND experience_date >= $2
        ORDER BY experience_date DESC
        LIMIT $3
        """,
        person_id,
        since,
        limit,
    )

    return [_row_to_experience(row) for row in (rows or [])]


async def get_experiences_at_restaurant(
    person_id: str,
    restaurant_name: str,
    limit: int = 20,
) -> List[FoodExperience]:
    """Get all experiences at a specific restaurant."""
    rows = await dbfetch(
        """
        SELECT * FROM food_experiences
        WHERE person_id = $1 AND LOWER(restaurant_name) = LOWER($2)
        ORDER BY experience_date DESC
        LIMIT $3
        """,
        person_id,
        restaurant_name,
        limit,
    )

    return [_row_to_experience(row) for row in (rows or [])]


async def get_experiences_with_dish(
    person_id: str,
    dish_name: str,
    limit: int = 10,
) -> List[FoodExperience]:
    """Get all experiences with a specific dish."""
    rows = await dbfetch(
        """
        SELECT * FROM food_experiences
        WHERE person_id = $1 AND LOWER(dish_name) LIKE LOWER($2)
        ORDER BY experience_date DESC
        LIMIT $3
        """,
        person_id,
        f"%{dish_name}%",
        limit,
    )

    return [_row_to_experience(row) for row in (rows or [])]


# =============================================================================
# Restaurant Memory
# =============================================================================

async def _update_restaurant_memory(
    person_id: str,
    restaurant_name: str,
    location: Optional[str],
    cuisine: Optional[str],
) -> None:
    """Update restaurant visit statistics."""
    await dbexec(
        """
        INSERT INTO restaurant_memory (person_id, restaurant_name, location, cuisine, visit_count, last_visit)
        VALUES ($1, $2, $3, $4, 1, NOW())
        ON CONFLICT (person_id, restaurant_name) DO UPDATE SET
            visit_count = restaurant_memory.visit_count + 1,
            last_visit = NOW(),
            location = COALESCE($3, restaurant_memory.location),
            cuisine = COALESCE($4, restaurant_memory.cuisine)
        """,
        person_id,
        restaurant_name,
        location,
        cuisine,
    )


async def get_restaurant_memory(
    person_id: str,
    restaurant_name: str,
) -> Optional[RestaurantMemory]:
    """Get memory of a specific restaurant."""
    row = await dbfetch(
        """
        SELECT rm.*,
            (SELECT AVG(CASE rating
                WHEN 'loved' THEN 5
                WHEN 'liked' THEN 4
                WHEN 'okay' THEN 3
                WHEN 'disliked' THEN 2
                WHEN 'hated' THEN 1
            END) FROM food_experiences
            WHERE person_id = rm.person_id
            AND LOWER(restaurant_name) = LOWER(rm.restaurant_name)
            AND rating IS NOT NULL) as avg_rating,
            (SELECT array_agg(DISTINCT dish_name) FROM food_experiences
            WHERE person_id = rm.person_id
            AND LOWER(restaurant_name) = LOWER(rm.restaurant_name)
            AND rating IN ('loved', 'liked')) as favorites
        FROM restaurant_memory rm
        WHERE rm.person_id = $1 AND LOWER(rm.restaurant_name) = LOWER($2)
        """,
        person_id,
        restaurant_name,
        one=True,
    )

    if not row:
        return None

    return RestaurantMemory(
        name=row["restaurant_name"],
        location=row.get("location"),
        cuisine=row.get("cuisine"),
        visit_count=row.get("visit_count", 0),
        last_visit=row.get("last_visit"),
        average_rating=row.get("avg_rating"),
        favorite_dishes=row.get("favorites") or [],
        notes=row.get("notes"),
        want_to_return=row.get("want_to_return", True),
    )


async def get_favorite_restaurants(
    person_id: str,
    cuisine: Optional[str] = None,
    limit: int = 10,
) -> List[RestaurantMemory]:
    """Get favorite restaurants, optionally filtered by cuisine."""
    if cuisine:
        rows = await dbfetch(
            """
            SELECT rm.*,
                (SELECT AVG(CASE rating
                    WHEN 'loved' THEN 5 WHEN 'liked' THEN 4 WHEN 'okay' THEN 3
                    WHEN 'disliked' THEN 2 WHEN 'hated' THEN 1 END)
                FROM food_experiences
                WHERE person_id = rm.person_id
                AND LOWER(restaurant_name) = LOWER(rm.restaurant_name)
                AND rating IS NOT NULL) as avg_rating
            FROM restaurant_memory rm
            WHERE rm.person_id = $1 AND LOWER(rm.cuisine) = LOWER($2)
            ORDER BY avg_rating DESC NULLS LAST, visit_count DESC
            LIMIT $3
            """,
            person_id,
            cuisine,
            limit,
        )
    else:
        rows = await dbfetch(
            """
            SELECT rm.*,
                (SELECT AVG(CASE rating
                    WHEN 'loved' THEN 5 WHEN 'liked' THEN 4 WHEN 'okay' THEN 3
                    WHEN 'disliked' THEN 2 WHEN 'hated' THEN 1 END)
                FROM food_experiences
                WHERE person_id = rm.person_id
                AND LOWER(restaurant_name) = LOWER(rm.restaurant_name)
                AND rating IS NOT NULL) as avg_rating
            FROM restaurant_memory rm
            WHERE rm.person_id = $1
            ORDER BY avg_rating DESC NULLS LAST, visit_count DESC
            LIMIT $2
            """,
            person_id,
            limit,
        )

    return [
        RestaurantMemory(
            name=row["restaurant_name"],
            location=row.get("location"),
            cuisine=row.get("cuisine"),
            visit_count=row.get("visit_count", 0),
            last_visit=row.get("last_visit"),
            average_rating=row.get("avg_rating"),
        )
        for row in (rows or [])
    ]


# =============================================================================
# Cuisine Analysis
# =============================================================================

async def get_cuisine_experience(
    person_id: str,
    cuisine: str,
) -> CuisineExperience:
    """Get experience summary for a specific cuisine."""
    row = await dbfetch(
        """
        SELECT
            COUNT(*) as times,
            AVG(CASE rating
                WHEN 'loved' THEN 5 WHEN 'liked' THEN 4 WHEN 'okay' THEN 3
                WHEN 'disliked' THEN 2 WHEN 'hated' THEN 1 END) as avg_rating,
            MAX(experience_date) as last_eaten,
            array_agg(DISTINCT dish_name) FILTER (WHERE rating IN ('loved', 'liked')) as favorites
        FROM food_experiences
        WHERE person_id = $1 AND LOWER(cuisine) = LOWER($2)
        """,
        person_id,
        cuisine,
        one=True,
    )

    return CuisineExperience(
        cuisine=cuisine,
        times_eaten=row.get("times", 0) if row else 0,
        average_rating=row.get("avg_rating") if row else None,
        favorite_dishes=row.get("favorites") or [] if row else [],
        last_eaten=row.get("last_eaten") if row else None,
    )


async def get_cuisine_breakdown(
    person_id: str,
    days: int = 90,
) -> List[Dict[str, Any]]:
    """
    Get breakdown of cuisines eaten recently.

    Useful for seeing eating patterns.
    """
    since = datetime.utcnow() - timedelta(days=days)

    rows = await dbfetch(
        """
        SELECT
            cuisine,
            COUNT(*) as times,
            MAX(experience_date) as last_eaten
        FROM food_experiences
        WHERE person_id = $1
            AND experience_date >= $2
            AND cuisine IS NOT NULL
        GROUP BY cuisine
        ORDER BY times DESC
        """,
        person_id,
        since,
    )

    return [
        {
            "cuisine": row["cuisine"],
            "times": row["times"],
            "last_eaten": row["last_eaten"],
        }
        for row in (rows or [])
    ]


# =============================================================================
# Food Discovery & Suggestions
# =============================================================================

async def get_dishes_to_try_again(
    person_id: str,
    limit: int = 10,
) -> List[FoodExperience]:
    """Get dishes marked as 'want again'."""
    rows = await dbfetch(
        """
        SELECT * FROM food_experiences
        WHERE person_id = $1 AND want_again = true
        ORDER BY experience_date DESC
        LIMIT $2
        """,
        person_id,
        limit,
    )

    return [_row_to_experience(row) for row in (rows or [])]


async def get_loved_dishes(
    person_id: str,
    cuisine: Optional[str] = None,
    limit: int = 20,
) -> List[FoodExperience]:
    """Get dishes rated as 'loved'."""
    if cuisine:
        rows = await dbfetch(
            """
            SELECT * FROM food_experiences
            WHERE person_id = $1 AND rating = 'loved' AND LOWER(cuisine) = LOWER($2)
            ORDER BY experience_date DESC
            LIMIT $3
            """,
            person_id,
            cuisine,
            limit,
        )
    else:
        rows = await dbfetch(
            """
            SELECT * FROM food_experiences
            WHERE person_id = $1 AND rating = 'loved'
            ORDER BY experience_date DESC
            LIMIT $2
            """,
            person_id,
            limit,
        )

    return [_row_to_experience(row) for row in (rows or [])]


async def search_food_memory(
    person_id: str,
    query: str,
    limit: int = 10,
) -> List[FoodExperience]:
    """Search food memory by dish name, restaurant, or notes."""
    rows = await dbfetch(
        """
        SELECT *,
            ts_rank(
                to_tsvector('english', COALESCE(dish_name, '') || ' ' ||
                    COALESCE(restaurant_name, '') || ' ' ||
                    COALESCE(notes, '')),
                plainto_tsquery('english', $2)
            ) as rank
        FROM food_experiences
        WHERE person_id = $1
            AND to_tsvector('english', COALESCE(dish_name, '') || ' ' ||
                COALESCE(restaurant_name, '') || ' ' ||
                COALESCE(notes, '')) @@ plainto_tsquery('english', $2)
        ORDER BY rank DESC, experience_date DESC
        LIMIT $3
        """,
        person_id,
        query,
        limit,
    )

    return [_row_to_experience(row) for row in (rows or [])]


# =============================================================================
# "Last Time" Queries
# =============================================================================

async def last_time_ate(
    person_id: str,
    item: str,  # dish name, cuisine, or restaurant
) -> Optional[FoodExperience]:
    """
    Find the last time the person ate something.

    Searches dish name, cuisine, and restaurant name.

    Example queries:
        - "pizza" - Last time ate pizza
        - "Italian" - Last time ate Italian food
        - "Thai House" - Last time at Thai House
    """
    # Try exact dish match first
    row = await dbfetch(
        """
        SELECT * FROM food_experiences
        WHERE person_id = $1 AND LOWER(dish_name) LIKE LOWER($2)
        ORDER BY experience_date DESC
        LIMIT 1
        """,
        person_id,
        f"%{item}%",
        one=True,
    )

    if row:
        return _row_to_experience(row)

    # Try restaurant match
    row = await dbfetch(
        """
        SELECT * FROM food_experiences
        WHERE person_id = $1 AND LOWER(restaurant_name) LIKE LOWER($2)
        ORDER BY experience_date DESC
        LIMIT 1
        """,
        person_id,
        f"%{item}%",
        one=True,
    )

    if row:
        return _row_to_experience(row)

    # Try cuisine match
    row = await dbfetch(
        """
        SELECT * FROM food_experiences
        WHERE person_id = $1 AND LOWER(cuisine) LIKE LOWER($2)
        ORDER BY experience_date DESC
        LIMIT 1
        """,
        person_id,
        f"%{item}%",
        one=True,
    )

    if row:
        return _row_to_experience(row)

    return None


async def last_time_at_restaurant(
    person_id: str,
    restaurant_name: str,
) -> Tuple[Optional[datetime], List[FoodExperience]]:
    """
    Get the last time visited a restaurant and what was ordered.

    Returns:
        Tuple of (last_visit_date, list_of_dishes_ordered)
    """
    rows = await dbfetch(
        """
        SELECT * FROM food_experiences
        WHERE person_id = $1 AND LOWER(restaurant_name) LIKE LOWER($2)
        ORDER BY experience_date DESC
        LIMIT 10
        """,
        person_id,
        f"%{restaurant_name}%",
    )

    if not rows:
        return None, []

    experiences = [_row_to_experience(row) for row in rows]

    # Get the most recent visit
    most_recent = max(e.date for e in experiences if e.date)

    # Get dishes from that visit
    visit_dishes = [e for e in experiences if e.date == most_recent]

    return most_recent, visit_dishes


# =============================================================================
# Context for Recommendations
# =============================================================================

async def get_food_context_for_recommendations(
    person_id: str,
) -> Dict[str, Any]:
    """
    Get food memory context for making recommendations.

    Used when Sakhi needs to suggest restaurants or dishes.
    """
    recent = await get_recent_meals(person_id, limit=20, days=30)
    favorites = await get_favorite_restaurants(person_id, limit=5)
    loved = await get_loved_dishes(person_id, limit=10)
    cuisine_breakdown = await get_cuisine_breakdown(person_id, days=60)

    return {
        "recent_meals": [
            {
                "dish": e.dish_name,
                "restaurant": e.restaurant_name,
                "cuisine": e.cuisine,
                "rating": e.rating.value if e.rating else None,
                "date": e.date.isoformat() if e.date else None,
            }
            for e in recent
        ],
        "favorite_restaurants": [
            {
                "name": r.name,
                "cuisine": r.cuisine,
                "visits": r.visit_count,
                "rating": r.average_rating,
            }
            for r in favorites
        ],
        "loved_dishes": [
            {
                "dish": e.dish_name,
                "restaurant": e.restaurant_name,
                "cuisine": e.cuisine,
            }
            for e in loved
        ],
        "cuisine_frequency": cuisine_breakdown,
        "eating_variety": len(set(e.cuisine for e in recent if e.cuisine)),
    }


# =============================================================================
# Helper Functions
# =============================================================================

def _row_to_experience(row: Dict[str, Any]) -> FoodExperience:
    """Convert a database row to a FoodExperience."""
    return FoodExperience(
        id=str(row.get("id")) if row.get("id") else None,
        person_id=row["person_id"],
        dish_name=row["dish_name"],
        cuisine=row.get("cuisine"),
        restaurant_name=row.get("restaurant_name"),
        restaurant_location=row.get("restaurant_location"),
        meal_type=MealType(row["meal_type"]) if row.get("meal_type") else None,
        context=DiningContext(row["context"]) if row.get("context") else None,
        rating=Rating(row["rating"]) if row.get("rating") else None,
        notes=row.get("notes"),
        date=row.get("experience_date"),
        companions=_parse_json_list(row.get("companions")),
        tags=_parse_json_list(row.get("tags")),
        want_again=row.get("want_again", False),
        price_paid=row.get("price_paid"),
    )


def _parse_json_list(value: Any) -> List[str]:
    """Parse a JSON list field."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return []
    return []


__all__ = [
    "MealType",
    "DiningContext",
    "Rating",
    "FoodExperience",
    "RestaurantMemory",
    "CuisineExperience",
    "record_meal",
    "get_recent_meals",
    "get_experiences_at_restaurant",
    "get_experiences_with_dish",
    "get_restaurant_memory",
    "get_favorite_restaurants",
    "get_cuisine_experience",
    "get_cuisine_breakdown",
    "get_dishes_to_try_again",
    "get_loved_dishes",
    "search_food_memory",
    "last_time_ate",
    "last_time_at_restaurant",
    "get_food_context_for_recommendations",
]
