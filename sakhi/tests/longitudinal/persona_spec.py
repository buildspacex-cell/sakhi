"""
Persona Specification Schema for Longitudinal Testing

Defines synthetic personas with:
- Core traits: Personality patterns, energy profiles, life context
- Arcs: Time-phased emotional/life journeys
- Expected outcomes: What Sakhi should learn at various checkpoints

Example persona: "Anxious Achiever"
- High-achieving professional, tendency toward anxiety
- Arc: Burnout → Recognition → Recovery
- Expected: Sakhi detects Intensity Friction, suggests cooling practices
"""

from __future__ import annotations

import json
import yaml
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from enum import Enum
from pydantic import BaseModel, Field, validator


class DoshaProfile(BaseModel):
    """Ayurvedic dosha baseline for the persona."""
    vata: float = Field(0.33, ge=0, le=1)
    pitta: float = Field(0.33, ge=0, le=1)
    kapha: float = Field(0.34, ge=0, le=1)

    @validator("kapha", always=True)
    def normalize_doshas(cls, v, values):
        """Ensure doshas sum to 1.0"""
        vata = values.get("vata", 0.33)
        pitta = values.get("pitta", 0.33)
        total = vata + pitta + v
        if abs(total - 1.0) > 0.01:
            # Auto-normalize
            return round(1.0 - vata - pitta, 3)
        return v


class EnergySlot(str, Enum):
    """Energy level descriptors."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    VARIABLE = "variable"


class RhythmProfile(BaseModel):
    """Natural energy rhythm profile."""
    morning: EnergySlot = EnergySlot.MEDIUM
    afternoon: EnergySlot = EnergySlot.MEDIUM
    evening: EnergySlot = EnergySlot.MEDIUM
    best_work_time: str = "morning"
    sleep_quality: str = "variable"  # good, poor, variable


class PersonaTrait(BaseModel):
    """
    A core personality trait that influences journal entries.

    Examples:
    - "perfectionist": Shows up as self-criticism, high standards
    - "anxious_attachment": Relationship worry, seeking reassurance
    - "growth_oriented": Reflection on learning, self-improvement
    """
    name: str
    description: str
    intensity: float = Field(0.7, ge=0, le=1)  # How strongly this trait shows
    journal_patterns: List[str] = Field(default_factory=list)  # Typical phrases/themes


class LifeContext(BaseModel):
    """Background context about the persona's life situation."""
    occupation: str = "professional"
    relationships: Dict[str, str] = Field(default_factory=dict)  # name -> relation
    current_challenges: List[str] = Field(default_factory=list)
    values: List[str] = Field(default_factory=list)
    hobbies: List[str] = Field(default_factory=list)


class ArcPhase(BaseModel):
    """
    A phase within a life arc.

    The persona goes through phases over time, each with different
    emotional states and journaling themes.
    """
    name: str
    duration_days: int = 14
    emotional_state: str  # e.g., "overwhelmed", "hopeful", "recovering"
    energy_modifier: float = Field(1.0, ge=0.5, le=1.5)  # Multiplier on base energy
    dosha_shift: Optional[DoshaProfile] = None  # Temporary dosha change
    themes: List[str] = Field(default_factory=list)  # What they journal about
    events: List[str] = Field(default_factory=list)  # Life events during this phase
    entry_frequency: float = Field(1.0, ge=0.2, le=3.0)  # Entries per day multiplier


class PersonaArc(BaseModel):
    """
    A multi-phase journey the persona goes through.

    Example: Burnout Arc
    - Phase 1: "Pushing Through" (2 weeks) - overwork, denial
    - Phase 2: "Breaking Point" (1 week) - anxiety, exhaustion
    - Phase 3: "Recognition" (2 weeks) - acceptance, seeking help
    - Phase 4: "Recovery" (3 weeks) - gradual improvement
    """
    name: str
    description: str
    phases: List[ArcPhase]

    @property
    def total_days(self) -> int:
        return sum(p.duration_days for p in self.phases)

    def get_phase_at_day(self, day: int) -> Optional[ArcPhase]:
        """Get the active phase for a given simulation day."""
        cumulative = 0
        for phase in self.phases:
            cumulative += phase.duration_days
            if day <= cumulative:
                return phase
        return self.phases[-1] if self.phases else None


class Checkpoint(BaseModel):
    """
    An assertion checkpoint at a specific point in the simulation.

    Defines what Sakhi should have learned by this point.
    """
    day: int
    name: str
    assertions: Dict[str, Any] = Field(default_factory=dict)
    # Supported assertion types:
    # - friction_state: {"expected": "chaos|intensity|stagnation|balanced"}
    # - pattern_crystallized: {"type": "emotion", "value": "anxiety", "min_confidence": 0.7}
    # - theme_emerged: {"keywords": ["work", "stress"], "min_occurrences": 3}
    # - rhythm_learned: {"slot": "morning", "expected": "low|high"}
    # - dosha_drift: {"dosha": "pitta", "direction": "elevated", "min_percentage": 20}


class PersonaSpec(BaseModel):
    """
    Complete specification for a synthetic test persona.

    This defines everything needed to simulate months of journaling
    and verify that Sakhi's understanding evolves correctly.
    """
    id: str  # Unique identifier (e.g., "anxious_achiever")
    name: str  # Display name
    description: str

    # Core profile
    dosha_baseline: DoshaProfile = Field(default_factory=DoshaProfile)
    rhythm: RhythmProfile = Field(default_factory=RhythmProfile)
    traits: List[PersonaTrait] = Field(default_factory=list)
    life_context: LifeContext = Field(default_factory=LifeContext)

    # Journey
    arc: PersonaArc

    # Entry generation hints
    writing_style: str = "conversational"  # conversational, reflective, brief, detailed
    typical_entry_length: str = "medium"  # short (1-2 sentences), medium (paragraph), long (multiple paragraphs)
    entry_times: List[str] = Field(default_factory=lambda: ["morning", "evening"])

    # Verification checkpoints
    checkpoints: List[Checkpoint] = Field(default_factory=list)

    # Metadata
    version: str = "1.0"
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @classmethod
    def from_yaml(cls, path: Union[str, Path]) -> "PersonaSpec":
        """Load persona spec from YAML file."""
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        return cls(**data)

    @classmethod
    def from_json(cls, path: Union[str, Path]) -> "PersonaSpec":
        """Load persona spec from JSON file."""
        with open(path, "r") as f:
            data = json.load(f)
        return cls(**data)

    def to_yaml(self, path: Union[str, Path]) -> None:
        """Save persona spec to YAML file."""
        with open(path, "w") as f:
            yaml.dump(self.model_dump(mode="json"), f, default_flow_style=False)

    def to_json(self, path: Union[str, Path]) -> None:
        """Save persona spec to JSON file."""
        with open(path, "w") as f:
            json.dump(self.model_dump(mode="json"), f, indent=2)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to serializable dict for demo export."""
        data = self.model_dump(mode="json")
        # Remove internal fields
        data.pop("version", None)
        data.pop("created_at", None)
        return data

    def get_checkpoint_at_day(self, day: int) -> Optional[Checkpoint]:
        """Get checkpoint if one exists at this day."""
        for cp in self.checkpoints:
            if cp.day == day:
                return cp
        return None

    def get_generation_context(self, day: int) -> Dict[str, Any]:
        """
        Get context for generating entries on a specific day.

        Returns all relevant info for the LLM entry generator.
        """
        phase = self.arc.get_phase_at_day(day)

        return {
            "persona_id": self.id,
            "persona_name": self.name,
            "day": day,
            "phase": phase.model_dump() if phase else None,
            "dosha_baseline": self.dosha_baseline.model_dump(),
            "current_dosha": (phase.dosha_shift.model_dump() if phase and phase.dosha_shift
                             else self.dosha_baseline.model_dump()),
            "rhythm": self.rhythm.model_dump(),
            "traits": [t.model_dump() for t in self.traits],
            "life_context": self.life_context.model_dump(),
            "writing_style": self.writing_style,
            "entry_length": self.typical_entry_length,
            "entry_times": self.entry_times,
        }


def load_persona(persona_id: str) -> PersonaSpec:
    """
    Load a persona spec by ID.

    Looks in the standard personas directory for YAML/JSON files.
    """
    personas_dir = Path(__file__).parent / "personas"

    # Try YAML first, then JSON
    yaml_path = personas_dir / f"{persona_id}.yaml"
    json_path = personas_dir / f"{persona_id}.json"

    if yaml_path.exists():
        return PersonaSpec.from_yaml(yaml_path)
    elif json_path.exists():
        return PersonaSpec.from_json(json_path)
    else:
        raise FileNotFoundError(
            f"Persona '{persona_id}' not found. "
            f"Looked in: {yaml_path}, {json_path}"
        )


def list_available_personas() -> List[str]:
    """List all available persona IDs."""
    personas_dir = Path(__file__).parent / "personas"
    if not personas_dir.exists():
        return []

    personas = set()
    for f in personas_dir.glob("*.yaml"):
        personas.add(f.stem)
    for f in personas_dir.glob("*.json"):
        personas.add(f.stem)

    return sorted(personas)


__all__ = [
    "PersonaSpec",
    "PersonaTrait",
    "PersonaArc",
    "ArcPhase",
    "Checkpoint",
    "DoshaProfile",
    "RhythmProfile",
    "LifeContext",
    "EnergySlot",
    "load_persona",
    "list_available_personas",
]
