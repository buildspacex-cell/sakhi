"""
Product Matching Service
------------------------
Score products against stored preferences using the extensible preference framework.

Works with ANY product category by:
1. Detecting the relevant domain(s) from category/description
2. Extracting product attributes as domain dimensions
3. Matching against stored preference values

Example:
    "Find car perfume" → domain=fragrance, match against woodiness, florals, etc.
    "Restaurant recommendation" → domain=food, match against spiciness, texture, etc.
    "Hotel search" → domain=travel, match against comfort_level, luxury_level, etc.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from sakhi.apps.api.services.memory.preference_framework import (
    load_preferences,
    get_or_create_preferences,
    match_item_to_preferences,
    STANDARD_DIMENSIONS,
)

LOGGER = logging.getLogger(__name__)


class MatchLevel(str, Enum):
    """How well a product matches preferences."""
    PERFECT = "perfect"  # 90-100%
    GOOD = "good"  # 70-89%
    FAIR = "fair"  # 50-69%
    POOR = "poor"  # 25-49%
    AVOID = "avoid"  # 0-24% or explicit dislike


@dataclass
class ProductMatch:
    """Result of matching a product against preferences."""
    score: float  # 0.0 - 1.0
    level: MatchLevel
    reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    preference_hits: Dict[str, Any] = field(default_factory=dict)
    domain: str = "custom"


@dataclass
class ProductAttributes:
    """Extracted attributes from a product description."""
    domain: str
    dimensions: Dict[str, float] = field(default_factory=dict)  # dimension -> value (-1 to 1)
    tags: List[str] = field(default_factory=list)
    raw_description: str = ""


# Map product categories to preference domains
CATEGORY_TO_DOMAIN = {
    # Food & Dining
    "food": "food",
    "restaurant": "food",
    "dining": "food",
    "meal": "food",
    "cuisine": "food",
    # Fragrance
    "perfume": "fragrance",
    "cologne": "fragrance",
    "car_perfume": "fragrance",
    "scent": "fragrance",
    "fragrance": "fragrance",
    "candle": "fragrance",
    "diffuser": "fragrance",
    # Travel
    "hotel": "travel",
    "resort": "travel",
    "vacation": "travel",
    "trip": "travel",
    "destination": "travel",
    # Fashion
    "clothing": "fashion",
    "clothes": "fashion",
    "outfit": "fashion",
    "apparel": "fashion",
    "accessories": "fashion",
    # Wellness
    "supplement": "wellness",
    "fitness": "wellness",
    "gym": "wellness",
    "spa": "wellness",
    # Environment
    "furniture": "environment",
    "decor": "environment",
    "home": "environment",
    # Media
    "movie": "media",
    "book": "media",
    "music": "media",
    "podcast": "media",
    "game": "media",
}


def _category_to_domain(category: Optional[str], description: str = "") -> str:
    """Determine domain from category or description."""
    if category:
        category_lower = category.lower().replace(" ", "_")
        if category_lower in CATEGORY_TO_DOMAIN:
            return CATEGORY_TO_DOMAIN[category_lower]

    # Try to detect from description keywords
    desc_lower = description.lower()
    domain_keywords = {
        "fragrance": ["scent", "smell", "aroma", "perfume", "fragrance", "woody", "floral", "notes"],
        "food": ["taste", "flavor", "spicy", "sweet", "meal", "dish", "restaurant", "cuisine"],
        "travel": ["hotel", "resort", "vacation", "trip", "destination", "travel"],
        "fashion": ["wear", "style", "outfit", "clothing", "fit"],
        "wellness": ["health", "fitness", "supplement", "exercise", "meditation"],
        "environment": ["room", "atmosphere", "lighting", "temperature", "decor"],
        "media": ["watch", "read", "listen", "movie", "book", "show"],
    }

    for domain, keywords in domain_keywords.items():
        if any(kw in desc_lower for kw in keywords):
            return domain

    return "custom"


async def score_product(
    person_id: str,
    product_description: str,
    product_name: Optional[str] = None,
    category: Optional[str] = None,
) -> ProductMatch:
    """
    Score a product against user's stored preferences.

    Args:
        person_id: User's ID
        product_description: Full product description text
        product_name: Optional product name
        category: Optional product category (e.g., "car_perfume", "restaurant", "hotel")

    Returns:
        ProductMatch with score 0.0-1.0 and explanations

    Example:
        >>> match = await score_product(
        ...     person_id="user-123",
        ...     product_description="Woody cedar car freshener with hints of sandalwood",
        ...     category="car_perfume"
        ... )
        >>> match.score
        0.85
        >>> match.reasons
        ["Matches your preference for woody scents", "Contains sandalwood (you like this)"]
    """
    # Determine domain
    domain = _category_to_domain(category, product_description)

    # Extract product attributes using LLM
    attributes = await _extract_product_attributes(product_description, domain, category)

    # Use the framework's matching function
    match_result = await match_item_to_preferences(
        person_id=person_id,
        domain=domain,
        item_attributes=attributes.dimensions,
    )

    # Build reasons and warnings from breakdown
    reasons = []
    warnings = []
    hits = {}

    for item in match_result.get("breakdown", []):
        dim = item["dimension"]
        alignment = item["alignment"]
        pref = item["preference"]
        item_val = item["item_value"]

        if alignment > 0.3:
            if pref > 0:
                reasons.append(f"Matches your preference for {dim.replace('_', ' ')}")
            else:
                reasons.append(f"Avoids {dim.replace('_', ' ')} (you dislike this)")
            hits[dim] = {"match": "positive", "alignment": alignment}
        elif alignment < -0.3:
            if pref > 0:
                warnings.append(f"Low on {dim.replace('_', ' ')} (you prefer more)")
            else:
                warnings.append(f"Contains {dim.replace('_', ' ')} (you avoid this)")
            hits[dim] = {"match": "negative", "alignment": alignment}

    # Add tags as reasons
    for tag in attributes.tags[:3]:
        reasons.append(f"Tagged as: {tag}")

    # Determine match level
    score = match_result["match_score"]

    if score >= 0.9:
        level = MatchLevel.PERFECT
    elif score >= 0.7:
        level = MatchLevel.GOOD
    elif score >= 0.5:
        level = MatchLevel.FAIR
    elif score >= 0.25:
        level = MatchLevel.POOR
    else:
        level = MatchLevel.AVOID

    # Add default reason if none matched
    if not reasons and not warnings:
        if match_result.get("confidence", 0) < 0.2:
            reasons.append("Limited preference data - score based on general compatibility")
        else:
            reasons.append("No specific preference matches found")

    LOGGER.info(
        "[product_matching] Scored %s product for %s: %.2f (%s) - %d reasons",
        domain,
        person_id[:8] if person_id else "?",
        score,
        level.value,
        len(reasons),
    )

    return ProductMatch(
        score=score,
        level=level,
        reasons=reasons,
        warnings=warnings,
        preference_hits=hits,
        domain=domain,
    )


async def score_products_batch(
    person_id: str,
    products: List[Dict[str, Any]],
    category: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Score multiple products and return sorted by match.

    Args:
        person_id: User's ID
        products: List of product dicts with 'name', 'description' keys
        category: Optional category for all products

    Returns:
        Products with 'match_score', 'match_level', 'match_reasons' added, sorted by score
    """
    scored = []

    for product in products:
        match = await score_product(
            person_id=person_id,
            product_description=product.get("description", ""),
            product_name=product.get("name"),
            category=category or product.get("category"),
        )

        scored.append({
            **product,
            "match_score": match.score,
            "match_level": match.level.value,
            "match_domain": match.domain,
            "match_reasons": match.reasons,
            "match_warnings": match.warnings,
        })

    # Sort by score descending
    scored.sort(key=lambda x: x["match_score"], reverse=True)

    return scored


async def _extract_product_attributes(
    description: str,
    domain: str,
    category: Optional[str] = None,
) -> ProductAttributes:
    """Extract attributes from product description using LLM."""
    from sakhi.apps.api.core.llm import call_llm, extract_json_from_llm_response

    # Get standard dimensions for this domain
    dimensions = STANDARD_DIMENSIONS.get(domain, [])

    category_hint = f" (Category: {category})" if category else ""

    prompt = f"""Extract attributes from this product description{category_hint}:

"{description}"

Domain: {domain}
Standard dimensions for this domain: {json.dumps(dimensions)}

For each applicable dimension, rate how strongly the product exhibits that quality:
- -1.0 = complete absence / opposite of the quality
- 0.0 = neutral / not applicable
- 1.0 = strongly exhibits the quality

Also identify any relevant tags (e.g., brand names, specific ingredients, style descriptors).

Return JSON:
{{
    "dimensions": {{
        "dimension_name": value,
        ...
    }},
    "tags": ["tag1", "tag2"]
}}

Only include dimensions that are actually relevant to the product.
Return ONLY the JSON."""

    try:
        # Uses MODEL_CHAT from environment (e.g., gpt-4o-mini from .env.local)
        response = await call_llm(
            prompt=prompt,
            max_tokens=400,
        )

        data = extract_json_from_llm_response(response)

        return ProductAttributes(
            domain=domain,
            dimensions=data.get("dimensions", {}),
            tags=data.get("tags", []),
            raw_description=description,
        )

    except Exception as e:
        LOGGER.warning("[product_matching] Failed to extract attributes: %s", e)
        return ProductAttributes(domain=domain, raw_description=description)


async def get_preference_summary_for_domain(
    person_id: str,
    domain: str,
) -> Dict[str, Any]:
    """
    Get a human-readable preference summary for a domain.

    Useful for showing users what Sakhi knows about their preferences.
    """
    prefs = await load_preferences(person_id)

    if not prefs or domain not in prefs.domains:
        return {
            "domain": domain,
            "has_preferences": False,
            "preferences": [],
            "avoids": [],
            "message": f"No {domain} preferences stored yet",
        }

    domain_pref = prefs.domains[domain]
    top_likes = domain_pref.get_top_preferences(5)
    top_dislikes = domain_pref.get_top_dislikes(5)

    return {
        "domain": domain,
        "has_preferences": True,
        "preferences": [
            f"{dim.replace('_', ' ')} ({pref.strength.value})"
            for dim, pref in top_likes if pref.value > 0
        ],
        "avoids": [
            f"{dim.replace('_', ' ')} ({pref.strength.value})"
            for dim, pref in top_dislikes
        ],
        "dimension_count": len(domain_pref.dimensions),
        "tags": domain_pref.tags,
    }


# Backwards compatibility alias
async def get_preference_summary_for_category(
    person_id: str,
    category: str,
) -> Dict[str, Any]:
    """Get preference summary - maps category to domain."""
    domain = _category_to_domain(category, "")
    return await get_preference_summary_for_domain(person_id, domain)


__all__ = [
    "score_product",
    "score_products_batch",
    "ProductMatch",
    "ProductAttributes",
    "MatchLevel",
    "get_preference_summary_for_domain",
    "get_preference_summary_for_category",
]
