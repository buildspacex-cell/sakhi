"""
Extensible Preference Framework

A domain-agnostic system for tracking any type of preference:
- Food, fragrance, travel, fashion, products, experiences, etc.
- Dynamic dimensions within each domain
- Cross-domain traits that span multiple domains
- Evidence-based learning with confidence tracking

Schema Design:
- Domain: A category of preferences (food, fragrance, travel, etc.)
- Dimension: A specific axis within a domain (spiciness, woodiness, etc.)
- Trait: A cross-domain preference (minimalist, adventurous, etc.)
- Evidence: Source of the preference (explicit, inferred, derived)
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field
import json

from sakhi.libs.schemas.db import get_async_pool


# ============================================================================
# Core Types
# ============================================================================

class PreferenceDomain(str, Enum):
    """Built-in domains. Custom domains can be added dynamically."""
    FOOD = "food"
    FRAGRANCE = "fragrance"
    TRAVEL = "travel"
    FASHION = "fashion"
    WELLNESS = "wellness"
    ENVIRONMENT = "environment"  # room temp, lighting, noise
    SOCIAL = "social"  # group size, interaction style
    MEDIA = "media"  # music, movies, books
    CUSTOM = "custom"  # user-defined


class EvidenceType(str, Enum):
    """How was this preference learned?"""
    EXPLICIT = "explicit"  # User directly stated it
    INFERRED = "inferred"  # Derived from behavior/choices
    DERIVED = "derived"  # Computed from other preferences
    ONBOARDING = "onboarding"  # From initial questionnaire
    FEEDBACK = "feedback"  # From explicit feedback on recommendations


class PreferenceStrength(str, Enum):
    """How strong is this preference?"""
    STRONG_DISLIKE = "strong_dislike"
    DISLIKE = "dislike"
    NEUTRAL = "neutral"
    LIKE = "like"
    STRONG_LIKE = "strong_like"


# ============================================================================
# Data Models
# ============================================================================

class PreferenceValue(BaseModel):
    """A single preference value with metadata."""
    value: float = Field(..., ge=-1.0, le=1.0)  # -1 = hate, 0 = neutral, 1 = love
    strength: PreferenceStrength = PreferenceStrength.NEUTRAL
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    evidence_type: EvidenceType = EvidenceType.INFERRED
    source_text: Optional[str] = None  # Original text that led to this
    learned_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def from_strength(cls, strength: PreferenceStrength, **kwargs) -> "PreferenceValue":
        """Create a PreferenceValue from a strength enum."""
        value_map = {
            PreferenceStrength.STRONG_DISLIKE: -1.0,
            PreferenceStrength.DISLIKE: -0.5,
            PreferenceStrength.NEUTRAL: 0.0,
            PreferenceStrength.LIKE: 0.5,
            PreferenceStrength.STRONG_LIKE: 1.0,
        }
        return cls(value=value_map[strength], strength=strength, **kwargs)


class DomainPreference(BaseModel):
    """Preferences within a specific domain."""
    domain: str
    dimensions: Dict[str, PreferenceValue] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)  # Free-form tags
    notes: Optional[str] = None

    def get_top_preferences(self, n: int = 5) -> List[Tuple[str, PreferenceValue]]:
        """Get the strongest positive preferences."""
        sorted_dims = sorted(
            self.dimensions.items(),
            key=lambda x: (x[1].value * x[1].confidence),
            reverse=True
        )
        return sorted_dims[:n]

    def get_top_dislikes(self, n: int = 5) -> List[Tuple[str, PreferenceValue]]:
        """Get the strongest negative preferences."""
        sorted_dims = sorted(
            self.dimensions.items(),
            key=lambda x: (x[1].value * x[1].confidence),
        )
        return [(k, v) for k, v in sorted_dims[:n] if v.value < 0]


class CrossDomainTrait(BaseModel):
    """A trait that applies across multiple domains."""
    trait_name: str  # e.g., "minimalist", "adventurous", "traditional"
    applies_to: List[str] = Field(default_factory=list)  # domains it affects
    value: float = Field(..., ge=-1.0, le=1.0)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    evidence_type: EvidenceType = EvidenceType.INFERRED
    learned_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PersonPreferences(BaseModel):
    """Complete preference profile for a person."""
    person_id: str
    domains: Dict[str, DomainPreference] = Field(default_factory=dict)
    traits: List[CrossDomainTrait] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def get_domain(self, domain: str) -> DomainPreference:
        """Get or create a domain preference."""
        if domain not in self.domains:
            self.domains[domain] = DomainPreference(domain=domain)
        return self.domains[domain]

    def set_preference(
        self,
        domain: str,
        dimension: str,
        value: PreferenceValue,
    ) -> None:
        """Set a preference value."""
        domain_pref = self.get_domain(domain)
        domain_pref.dimensions[dimension] = value
        self.updated_at = datetime.now(timezone.utc)

    def get_preference(
        self,
        domain: str,
        dimension: str,
    ) -> Optional[PreferenceValue]:
        """Get a specific preference."""
        if domain not in self.domains:
            return None
        return self.domains[domain].dimensions.get(dimension)

    def add_trait(self, trait: CrossDomainTrait) -> None:
        """Add or update a cross-domain trait."""
        # Update existing trait if found
        for i, existing in enumerate(self.traits):
            if existing.trait_name == trait.trait_name:
                self.traits[i] = trait
                return
        self.traits.append(trait)
        self.updated_at = datetime.now(timezone.utc)


# ============================================================================
# Standard Dimension Definitions (extensible, not enforced)
# ============================================================================

STANDARD_DIMENSIONS = {
    "food": [
        "spiciness", "sweetness", "saltiness", "sourness", "bitterness", "umami",
        "temperature", "texture_crunchiness", "texture_creaminess", "portion_size",
        "presentation", "authenticity", "health_focus", "indulgence",
    ],
    "fragrance": [
        "woodiness", "florals", "citrus", "musk", "spice", "freshness",
        "sweetness", "smokiness", "longevity_preference", "projection_preference",
    ],
    "travel": [
        "adventure_level", "comfort_level", "cultural_immersion", "nature_focus",
        "urban_preference", "luxury_level", "spontaneity", "planning_detail",
    ],
    "fashion": [
        "formality", "color_boldness", "pattern_complexity", "fit_preference",
        "comfort_vs_style", "brand_consciousness", "sustainability_focus",
    ],
    "wellness": [
        "exercise_intensity", "meditation_interest", "sleep_priority",
        "nutrition_focus", "supplement_openness", "alternative_medicine_openness",
    ],
    "environment": [
        "temperature_warm", "lighting_bright", "noise_tolerance",
        "clutter_tolerance", "nature_elements", "minimalism",
    ],
    "social": [
        "group_size_preference", "introversion_extroversion", "formality",
        "conversation_depth", "activity_vs_talk", "new_people_openness",
    ],
    "media": [
        "complexity", "emotional_intensity", "violence_tolerance",
        "humor_preference", "length_tolerance", "foreign_content_openness",
    ],
}


# ============================================================================
# Database Operations
# ============================================================================

async def store_preferences(preferences: PersonPreferences) -> bool:
    """Store the complete preference profile."""
    pool = await get_async_pool()

    # Serialize to JSON
    data = preferences.model_dump(mode="json")

    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO preference_profiles (person_id, profile_data, updated_at)
            VALUES ($1, $2, $3)
            ON CONFLICT (person_id)
            DO UPDATE SET
                profile_data = EXCLUDED.profile_data,
                updated_at = EXCLUDED.updated_at
            """,
            preferences.person_id,
            json.dumps(data),
            preferences.updated_at,
        )

    return True


async def load_preferences(person_id: str) -> Optional[PersonPreferences]:
    """Load the complete preference profile."""
    pool = await get_async_pool()

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT profile_data FROM preference_profiles
            WHERE person_id = $1
            """,
            person_id,
        )

    if not row:
        return None

    data = json.loads(row["profile_data"])
    return PersonPreferences(**data)


async def get_or_create_preferences(person_id: str) -> PersonPreferences:
    """Load existing or create new preference profile."""
    existing = await load_preferences(person_id)
    if existing:
        return existing
    return PersonPreferences(person_id=person_id)


async def update_single_preference(
    person_id: str,
    domain: str,
    dimension: str,
    value: float,
    evidence_type: EvidenceType = EvidenceType.INFERRED,
    confidence: float = 0.5,
    source_text: Optional[str] = None,
) -> PersonPreferences:
    """Update a single preference dimension."""
    prefs = await get_or_create_preferences(person_id)

    # Determine strength from value
    if value <= -0.75:
        strength = PreferenceStrength.STRONG_DISLIKE
    elif value <= -0.25:
        strength = PreferenceStrength.DISLIKE
    elif value >= 0.75:
        strength = PreferenceStrength.STRONG_LIKE
    elif value >= 0.25:
        strength = PreferenceStrength.LIKE
    else:
        strength = PreferenceStrength.NEUTRAL

    pref_value = PreferenceValue(
        value=value,
        strength=strength,
        confidence=confidence,
        evidence_type=evidence_type,
        source_text=source_text,
    )

    prefs.set_preference(domain, dimension, pref_value)
    await store_preferences(prefs)

    return prefs


async def add_preference_from_text(
    person_id: str,
    domain: str,
    dimension: str,
    text: str,
    sentiment: float,  # -1 to 1
    confidence: float = 0.5,
) -> PersonPreferences:
    """Add a preference learned from natural language."""
    return await update_single_preference(
        person_id=person_id,
        domain=domain,
        dimension=dimension,
        value=sentiment,
        evidence_type=EvidenceType.INFERRED,
        confidence=confidence,
        source_text=text,
    )


async def log_preference_event(
    person_id: str,
    domain: str,
    dimension: str,
    value: float,
    evidence_type: EvidenceType,
    source_text: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
) -> None:
    """Log a preference learning event for audit/debugging."""
    pool = await get_async_pool()

    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO preference_events (
                person_id, domain, dimension, value,
                evidence_type, source_text, context, created_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
            """,
            person_id,
            domain,
            dimension,
            value,
            evidence_type.value,
            source_text,
            json.dumps(context or {}),
        )


# ============================================================================
# Query Helpers
# ============================================================================

async def get_domain_summary(
    person_id: str,
    domain: str,
) -> Optional[Dict[str, Any]]:
    """Get a summary of preferences for a domain."""
    prefs = await load_preferences(person_id)
    if not prefs or domain not in prefs.domains:
        return None

    domain_pref = prefs.domains[domain]
    top_likes = domain_pref.get_top_preferences(5)
    top_dislikes = domain_pref.get_top_dislikes(5)

    return {
        "domain": domain,
        "dimension_count": len(domain_pref.dimensions),
        "top_likes": [
            {"dimension": k, "value": v.value, "confidence": v.confidence}
            for k, v in top_likes
        ],
        "top_dislikes": [
            {"dimension": k, "value": v.value, "confidence": v.confidence}
            for k, v in top_dislikes
        ],
        "tags": domain_pref.tags,
    }


async def get_all_domains(person_id: str) -> List[str]:
    """Get all domains with stored preferences."""
    prefs = await load_preferences(person_id)
    if not prefs:
        return []
    return list(prefs.domains.keys())


async def match_item_to_preferences(
    person_id: str,
    domain: str,
    item_attributes: Dict[str, float],  # dimension -> value (-1 to 1)
) -> Dict[str, Any]:
    """
    Score how well an item matches user preferences.

    Args:
        person_id: The person's ID
        domain: The preference domain
        item_attributes: Mapping of dimension to value for the item

    Returns:
        Match score and breakdown
    """
    prefs = await load_preferences(person_id)
    if not prefs or domain not in prefs.domains:
        return {
            "match_score": 0.5,  # Neutral if no preferences
            "confidence": 0.0,
            "breakdown": [],
            "message": "No preferences found for this domain",
        }

    domain_pref = prefs.domains[domain]

    matches = []
    total_score = 0.0
    total_weight = 0.0

    for dim, item_value in item_attributes.items():
        if dim in domain_pref.dimensions:
            pref = domain_pref.dimensions[dim]

            # Alignment: how well does item match preference?
            # pref.value > 0 means they like high values
            # item_value > 0 means item has high value
            # Alignment is positive if both agree
            alignment = pref.value * item_value

            # Weight by confidence
            weight = pref.confidence
            total_score += alignment * weight
            total_weight += weight

            matches.append({
                "dimension": dim,
                "preference": pref.value,
                "item_value": item_value,
                "alignment": alignment,
                "weighted_score": alignment * weight,
            })

    if total_weight == 0:
        final_score = 0.5
        confidence = 0.0
    else:
        # Normalize to 0-1 range
        final_score = (total_score / total_weight + 1) / 2
        confidence = min(total_weight / len(item_attributes), 1.0) if item_attributes else 0.0

    return {
        "match_score": final_score,
        "confidence": confidence,
        "breakdown": sorted(matches, key=lambda x: abs(x["alignment"]), reverse=True),
        "dimensions_matched": len(matches),
        "dimensions_total": len(item_attributes),
    }


# ============================================================================
# Migration Helper
# ============================================================================

async def migrate_from_sensory_preferences(person_id: str) -> bool:
    """
    Migrate old sensory_preferences format to new framework.
    Call this to upgrade existing preference data.
    """
    pool = await get_async_pool()

    async with pool.acquire() as conn:
        # Load old format
        row = await conn.fetchrow(
            """
            SELECT preferences FROM sensory_preferences
            WHERE person_id = $1
            """,
            person_id,
        )

    if not row:
        return False

    old_prefs = json.loads(row["preferences"])
    new_prefs = await get_or_create_preferences(person_id)

    # Map old categories to new framework
    # Old: temperature, texture, spice, flavor, visual, ambiance, portion, service
    mapping = {
        "temperature": ("food", "temperature"),
        "texture": ("food", "texture_creaminess"),  # Approximate
        "spice": ("food", "spiciness"),
        "flavor": ("food", "umami"),  # Approximate
        "visual": ("food", "presentation"),
        "ambiance": ("environment", "noise_tolerance"),
        "portion": ("food", "portion_size"),
        "service": ("social", "formality"),
    }

    for old_key, (domain, dimension) in mapping.items():
        if old_key in old_prefs:
            old_value = old_prefs[old_key]
            # Old format was 0-1, convert to -1 to 1
            new_value = (old_value - 0.5) * 2

            new_prefs.set_preference(
                domain,
                dimension,
                PreferenceValue(
                    value=new_value,
                    confidence=0.5,
                    evidence_type=EvidenceType.DERIVED,
                    source_text="Migrated from legacy sensory_preferences",
                ),
            )

    await store_preferences(new_prefs)
    return True


__all__ = [
    # Types
    "PreferenceDomain",
    "EvidenceType",
    "PreferenceStrength",
    # Models
    "PreferenceValue",
    "DomainPreference",
    "CrossDomainTrait",
    "PersonPreferences",
    # Constants
    "STANDARD_DIMENSIONS",
    # Functions
    "store_preferences",
    "load_preferences",
    "get_or_create_preferences",
    "update_single_preference",
    "add_preference_from_text",
    "log_preference_event",
    "get_domain_summary",
    "get_all_domains",
    "match_item_to_preferences",
    "migrate_from_sensory_preferences",
]
