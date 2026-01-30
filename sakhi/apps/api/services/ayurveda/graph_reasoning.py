"""
Ayurvedic Knowledge Graph Reasoning Engine

Provides intelligent, personalized recommendations by traversing the
Ayurvedic knowledge graph based on user's current state.

Multi-hop reasoning:
1. Identify imbalanced dosha from friction state
2. Find foods/practices that PACIFY that dosha
3. Filter by season appropriateness
4. Filter by time of day
5. Filter by user dietary preferences
6. Rank by: pacification_strength × context_match
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sakhi.apps.api.core.db import q as dbfetch

LOGGER = logging.getLogger(__name__)

# Season mapping
MONTH_TO_SEASON = {
    1: "winter", 2: "winter", 3: "spring",
    4: "spring", 5: "spring", 6: "summer",
    7: "summer", 8: "summer", 9: "fall",
    10: "fall", 11: "fall", 12: "winter",
}

# Time of day mapping
HOUR_TO_WINDOW = {
    range(4, 6): "early_morning",
    range(6, 10): "morning",
    range(10, 14): "midday",
    range(14, 18): "afternoon",
    range(18, 22): "evening",
}


def get_current_season() -> str:
    """Get current season based on month."""
    return MONTH_TO_SEASON.get(datetime.utcnow().month, "fall")


def get_current_time_window() -> str:
    """Get current time window based on hour."""
    hour = datetime.utcnow().hour
    for hour_range, window in HOUR_TO_WINDOW.items():
        if hour in hour_range:
            return window
    return "night"


async def get_dosha_id(dosha_name: str) -> Optional[int]:
    """Get dosha node ID by name."""
    result = await dbfetch(
        """
        SELECT id FROM ay_nodes
        WHERE kind = 'dosha' AND name = $1
        """,
        dosha_name,
        one=True,
    )
    return result["id"] if result else None


async def query_foods_for_dosha(
    dosha: str,
    relation: str = "PACIFIES",
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """
    Query foods that have a specific relationship with a dosha.

    Args:
        dosha: 'vata', 'pitta', or 'kapha'
        relation: 'PACIFIES' or 'AGGRAVATES'
        limit: Max number of results
    """
    results = await dbfetch(
        """
        SELECT n.name, n.attrs, e.weight
        FROM ay_nodes n
        JOIN ay_edges e ON n.id = e.src
        JOIN ay_nodes d ON e.dst = d.id
        WHERE n.kind = 'food'
          AND d.kind = 'dosha'
          AND d.name = $1
          AND e.rel = $2
        ORDER BY e.weight DESC
        LIMIT $3
        """,
        dosha,
        relation,
        limit,
    )

    foods = []
    for r in results or []:
        attrs = r.get("attrs") or {}
        if isinstance(attrs, str):
            attrs = json.loads(attrs)
        foods.append({
            "name": r["name"],
            "weight": float(r.get("weight") or 0.8),
            "rasa": attrs.get("rasa"),
            "virya": attrs.get("virya"),
            "season": attrs.get("season"),
        })
    return foods


async def query_practices_for_dosha(
    dosha: str,
    limit: int = 15,
) -> List[Dict[str, Any]]:
    """Query practices that pacify a specific dosha."""
    results = await dbfetch(
        """
        SELECT n.name, n.attrs, e.weight
        FROM ay_nodes n
        JOIN ay_edges e ON n.id = e.src
        JOIN ay_nodes d ON e.dst = d.id
        WHERE n.kind = 'practice'
          AND d.kind = 'dosha'
          AND d.name = $1
          AND e.rel = 'PACIFIES'
        ORDER BY e.weight DESC
        LIMIT $2
        """,
        dosha,
        limit,
    )

    practices = []
    for r in results or []:
        attrs = r.get("attrs") or {}
        if isinstance(attrs, str):
            attrs = json.loads(attrs)
        practices.append({
            "name": r["name"],
            "weight": float(r.get("weight") or 0.85),
            "type": attrs.get("type"),
            "intensity": attrs.get("intensity"),
            "duration_min": attrs.get("duration_min"),
            "time": attrs.get("time"),
        })
    return practices


async def query_symptoms_for_dosha(dosha: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Query symptoms that indicate a dosha imbalance."""
    results = await dbfetch(
        """
        SELECT n.name, n.attrs, e.weight
        FROM ay_nodes n
        JOIN ay_edges e ON n.id = e.src
        JOIN ay_nodes d ON e.dst = d.id
        WHERE n.kind = 'symptom'
          AND d.kind = 'dosha'
          AND d.name = $1
          AND e.rel = 'INDICATES'
        ORDER BY e.weight DESC
        LIMIT $2
        """,
        dosha,
        limit,
    )

    symptoms = []
    for r in results or []:
        attrs = r.get("attrs") or {}
        if isinstance(attrs, str):
            attrs = json.loads(attrs)
        symptoms.append({
            "name": r["name"],
            "weight": float(r.get("weight") or 0.8),
            "severity": attrs.get("severity"),
            "category": attrs.get("category"),
        })
    return symptoms


async def get_seasonal_amplification(dosha: str) -> float:
    """Get current seasonal amplification for a dosha."""
    season = get_current_season()
    result = await dbfetch(
        """
        SELECT e.weight
        FROM ay_edges e
        JOIN ay_nodes s ON e.src = s.id
        JOIN ay_nodes d ON e.dst = d.id
        WHERE s.kind = 'season'
          AND s.name = $1
          AND d.kind = 'dosha'
          AND d.name = $2
          AND e.rel = 'AMPLIFIES'
        """,
        season,
        dosha,
        one=True,
    )
    return float(result["weight"]) if result else 1.0


async def query_balancing_recommendations(
    person_id: str,
    friction_state: str,
    season: Optional[str] = None,
    time_of_day: Optional[str] = None,
    dietary_preferences: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Get personalized balancing recommendations based on current state.

    This is the main reasoning function that:
    1. Identifies the imbalanced dosha from friction state
    2. Queries the graph for pacifying foods and practices
    3. Filters by context (season, time, preferences)
    4. Ranks and returns recommendations

    Args:
        person_id: User ID
        friction_state: Current friction state (e.g., "Chaos Friction")
        season: Override season (default: current)
        time_of_day: Override time window (default: current)
        dietary_preferences: User dietary restrictions

    Returns:
        Dict with categorized recommendations
    """
    # Map friction state to dosha
    friction_to_dosha = {
        "chaos_friction": "vata",
        "chaos friction": "vata",
        "intensity_friction": "pitta",
        "intensity friction": "pitta",
        "stagnation_friction": "kapha",
        "stagnation friction": "kapha",
        "balanced": None,
    }

    dosha = friction_to_dosha.get(friction_state.lower())
    if not dosha:
        return {
            "status": "balanced",
            "message": "You're in balance - maintain with seasonal routines",
            "recommendations": {},
        }

    # Get context
    season = season or get_current_season()
    time_window = time_of_day or get_current_time_window()
    preferences = dietary_preferences or {}

    # Get seasonal amplification
    amplification = await get_seasonal_amplification(dosha)

    # Query foods that pacify this dosha
    foods = await query_foods_for_dosha(dosha, "PACIFIES", limit=30)

    # Filter foods by season and preferences
    filtered_foods = _filter_foods(foods, season, preferences)

    # Query practices
    practices = await query_practices_for_dosha(dosha, limit=20)

    # Filter practices by time
    filtered_practices = _filter_practices(practices, time_window)

    # Get symptoms for awareness
    symptoms = await query_symptoms_for_dosha(dosha, limit=10)

    # Score and rank
    scored_foods = _score_recommendations(
        filtered_foods, season, amplification, "food"
    )
    scored_practices = _score_recommendations(
        filtered_practices, time_window, amplification, "practice"
    )

    # Get top recommendations
    top_foods = sorted(scored_foods, key=lambda x: x["score"], reverse=True)[:5]
    top_practices = sorted(scored_practices, key=lambda x: x["score"], reverse=True)[:5]

    # Build immediate actions (quick wins)
    immediate_actions = _build_immediate_actions(top_practices, dosha)

    LOGGER.info(
        "[GraphReasoning] person=%s dosha=%s season=%s foods=%s practices=%s",
        person_id,
        dosha,
        season,
        len(top_foods),
        len(top_practices),
    )

    return {
        "status": "imbalanced",
        "imbalanced_dosha": dosha,
        "friction_state": friction_state,
        "season": season,
        "time_window": time_window,
        "seasonal_amplification": amplification,
        "recommendations": {
            "immediate_actions": immediate_actions,
            "foods_now": top_foods,
            "practices_today": top_practices,
        },
        "watch_for_symptoms": symptoms[:5],
    }


def _filter_foods(
    foods: List[Dict[str, Any]],
    season: str,
    preferences: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Filter foods by season and dietary preferences."""
    filtered = []

    vegetarian = preferences.get("vegetarian", False)
    vegan = preferences.get("vegan", False)
    excluded = set(preferences.get("excluded", []))

    for food in foods:
        name = food.get("name", "")

        # Check exclusions
        if name in excluded:
            continue

        # Check dietary restrictions (simplified - would need more data)
        if vegan and name in ["milk_warm", "ghee", "yogurt", "paneer", "kefir", "cottage_cheese"]:
            continue
        if vegetarian and name in []:  # Add meat items if we had them
            continue

        # Season check (allow "all" season foods)
        food_season = food.get("season", "all")
        if food_season != "all" and food_season != season:
            # Reduce score for out-of-season but don't exclude
            food["season_match"] = 0.7
        else:
            food["season_match"] = 1.0

        filtered.append(food)

    return filtered


def _filter_practices(
    practices: List[Dict[str, Any]],
    time_window: str,
) -> List[Dict[str, Any]]:
    """Filter practices by time of day appropriateness."""
    filtered = []

    for practice in practices:
        practice_time = practice.get("time", "any")

        if practice_time == "any" or practice_time == time_window:
            practice["time_match"] = 1.0
        elif _is_adjacent_time(practice_time, time_window):
            practice["time_match"] = 0.8
        else:
            practice["time_match"] = 0.5

        filtered.append(practice)

    return filtered


def _is_adjacent_time(practice_time: str, current_time: str) -> bool:
    """Check if practice time is adjacent to current time."""
    order = ["early_morning", "morning", "midday", "afternoon", "evening", "night"]
    try:
        practice_idx = order.index(practice_time)
        current_idx = order.index(current_time)
        return abs(practice_idx - current_idx) <= 1
    except ValueError:
        return False


def _score_recommendations(
    items: List[Dict[str, Any]],
    context: str,
    amplification: float,
    item_type: str,
) -> List[Dict[str, Any]]:
    """Score recommendations based on multiple factors."""
    scored = []

    for item in items:
        base_weight = float(item.get("weight", 0.7))
        context_match = float(item.get("season_match", 1.0) if item_type == "food" else item.get("time_match", 1.0))

        # Calculate final score
        score = base_weight * context_match * (1 + (amplification - 1) * 0.3)
        score = min(0.99, score)  # Cap at 0.99

        scored.append({
            **item,
            "score": round(score, 2),
            "why": _generate_why(item, item_type, context_match),
        })

    return scored


def _generate_why(item: Dict[str, Any], item_type: str, context_match: float) -> str:
    """Generate explanation for why this is recommended."""
    name = item.get("name", "").replace("_", " ").title()

    if item_type == "food":
        rasa = item.get("rasa", "balanced")
        virya = item.get("virya", "neutral")
        return f"{rasa.title()} taste, {virya} energy"

    elif item_type == "practice":
        practice_type = item.get("type", "practice")
        intensity = item.get("intensity", "gentle")
        duration = item.get("duration_min", 10)
        return f"{intensity.title()} {practice_type}, {duration} min"

    return "Balancing for your current state"


def _build_immediate_actions(
    practices: List[Dict[str, Any]],
    dosha: str,
) -> List[Dict[str, Any]]:
    """Build list of immediate actions (quick wins under 10 min)."""
    immediate = []

    # Filter to quick practices
    quick_practices = [p for p in practices if (p.get("duration_min") or 15) <= 10]

    for practice in quick_practices[:3]:
        name = practice.get("name", "").replace("_", " ").title()
        duration = practice.get("duration_min", 5)

        immediate.append({
            "action": f"{duration} min {name}",
            "why": _get_dosha_calming_reason(dosha, practice.get("type")),
            "duration_min": duration,
        })

    # Add default breathing if no quick practices
    if not immediate:
        immediate.append({
            "action": "5 min deep breathing",
            "why": f"Calms the nervous system, balances {dosha}",
            "duration_min": 5,
        })

    return immediate


def _get_dosha_calming_reason(dosha: str, practice_type: Optional[str]) -> str:
    """Get explanation for how practice calms dosha."""
    dosha_reasons = {
        "vata": "Grounding, calms nervous system",
        "pitta": "Cooling, reduces intensity",
        "kapha": "Energizing, promotes movement",
    }
    return dosha_reasons.get(dosha, "Balancing for your constitution")


async def get_graph_stats() -> Dict[str, Any]:
    """Get knowledge graph statistics."""
    node_counts = await dbfetch(
        """
        SELECT kind, COUNT(*) as count
        FROM ay_nodes
        GROUP BY kind
        ORDER BY kind
        """
    )

    edge_count = await dbfetch(
        "SELECT COUNT(*) as count FROM ay_edges",
        one=True,
    )

    return {
        "node_counts": {r["kind"]: r["count"] for r in (node_counts or [])},
        "total_nodes": sum(r["count"] for r in (node_counts or [])),
        "total_edges": (edge_count or {}).get("count", 0),
    }


__all__ = [
    "query_balancing_recommendations",
    "query_foods_for_dosha",
    "query_practices_for_dosha",
    "query_symptoms_for_dosha",
    "get_seasonal_amplification",
    "get_graph_stats",
    "get_current_season",
    "get_current_time_window",
]
