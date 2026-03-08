"""Versioned continuity taxonomy for deterministic simulation inference.

This module centralizes the lexical taxonomy used by the simulation continuity
compiler so changes can be reviewed, versioned, and regression-tested as a
single unit instead of being patched ad hoc inside the compiler.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping


@dataclass(frozen=True)
class ContinuityTaxonomy:
    version: str
    anchor_rules: Mapping[str, Mapping[str, float]]
    anchor_labels: Mapping[str, str]
    anchor_priority: Mapping[str, int]
    anchor_aliases: Mapping[str, str]
    facet_rules: Mapping[str, Mapping[str, Mapping[str, float]]]
    facet_aliases: Mapping[str, Mapping[str, str]]
    anchor_negative_rules: Mapping[str, Mapping[str, float]]
    facet_negative_rules: Mapping[str, Mapping[str, Mapping[str, float]]]
    positive_cues: Mapping[str, float]
    negative_cues: Mapping[str, float]
    defer_cues: tuple[str, ...]
    reversal_cues: tuple[str, ...]
    default_anchor_min_score: float = 1.0
    anchor_min_score_overrides: Mapping[str, float] = field(default_factory=dict)
    default_facet_min_score: float = 0.0
    facet_min_score_overrides: Mapping[str, float] = field(default_factory=dict)

    def anchor_min_score(self, anchor: str | None = None) -> float:
        if anchor and anchor in self.anchor_min_score_overrides:
            return float(self.anchor_min_score_overrides[anchor])
        return float(self.default_anchor_min_score)

    def facet_min_score(self, anchor: str | None = None) -> float:
        if anchor and anchor in self.facet_min_score_overrides:
            return float(self.facet_min_score_overrides[anchor])
        return float(self.default_facet_min_score)

    def label_for(self, anchor: str) -> str:
        return self.anchor_labels.get(anchor, anchor.replace("_", " ").title())

    def priority_for(self, anchor: str) -> int:
        return int(self.anchor_priority.get(anchor, 0))


SIMULATION_CONTINUITY_TAXONOMY = ContinuityTaxonomy(
    version="2026.03.03",
    anchor_rules={
        "caregiving": {
            "care": 1.1,
            "caregiving": 1.3,
            "grief": 1.4,
            "pre-accident": 1.6,
            "accident": 1.2,
            "confused": 1.1,
            "doctor": 1.0,
            "hospital": 1.0,
            "dad": 0.6,
            "mom": 0.6,
            "father": 0.6,
            "mother": 0.6,
        },
        "family": {
            "dad": 1.0,
            "mom": 1.0,
            "father": 1.0,
            "mother": 1.0,
            "daughter": 1.1,
            "son": 1.1,
            "kids": 1.1,
            "family": 1.2,
            "parents": 1.0,
            "dinner": 0.5,
            "home": 0.4,
        },
        "basketball": {
            "basketball": 1.5,
            "practice": 1.4,
            "coach": 1.3,
            "game": 1.2,
            "gym": 1.0,
            "drill": 1.0,
            "footwork": 1.3,
            "minutes": 0.8,
            "shooting": 1.0,
            "scrimmage": 1.0,
            "conditioning": 1.1,
            "court": 1.0,
        },
        "school": {
            "school": 1.4,
            "class": 1.2,
            "teacher": 1.0,
            "homework": 1.0,
            "exam": 1.0,
            "assignment": 1.0,
            "study": 1.0,
            "grade": 1.0,
            "period": 0.6,
        },
        "recovery": {
            "recovery": 1.4,
            "recover": 1.3,
            "injury": 1.2,
            "healing": 1.2,
            "pain": 0.9,
            "sore": 0.8,
            "rehab": 1.2,
            "physio": 1.2,
            "body": 0.6,
            "rest": 0.5,
        },
        "belonging": {
            "belong": 1.4,
            "belonging": 1.4,
            "fit in": 1.4,
            "left out": 1.3,
            "validation": 1.2,
            "reassurance": 1.1,
            "respect": 0.9,
            "special": 0.8,
            "accepted": 1.2,
            "seen": 1.0,
            "noticed": 0.9,
            "friends": 0.9,
            "alone": 1.0,
            "lonely": 1.0,
            "doubt": 0.7,
        },
        "leadership": {
            "leadership": 1.5,
            "manager": 1.0,
            "team": 0.8,
            "people": 0.6,
            "mentor": 1.0,
            "mentoring": 1.1,
            "coach": 0.5,
            "review": 0.5,
        },
        "career": {
            "boss": 1.2,
            "meeting": 1.0,
            "meetings": 1.0,
            "calendar": 0.8,
            "review": 1.0,
            "deadline": 1.0,
            "promotion": 1.3,
            "work": 0.8,
            "role": 0.9,
            "team": 0.4,
            "client": 0.8,
            "sales": 1.0,
            "call": 0.7,
            "channel": 1.0,
            "office": 0.8,
            "presentation": 0.8,
            "career": 1.3,
            "job": 0.9,
            "leadership": 0.6,
        },
        "generosity": {
            "advice": 1.2,
            "helped": 1.0,
            "help": 0.8,
            "support": 0.8,
            "mentor": 0.8,
            "mentoring": 0.9,
            "give": 0.7,
            "giving": 0.7,
            "reached out": 1.0,
            "asked for advice": 1.1,
        },
        "self_care": {
            "yoga": 1.4,
            "sleep": 1.0,
            "slept": 1.0,
            "rest": 0.9,
            "restless": 1.0,
            "walk": 1.0,
            "breath": 1.0,
            "breathed": 1.0,
            "tea": 0.7,
            "body": 0.8,
            "morning": 0.5,
            "quiet": 0.6,
        },
        "sakhi": {
            "sakhi": 1.8,
            "ayurveda": 1.4,
            "ayurvedic": 1.4,
            "ravi": 1.2,
            "knowledge graph": 1.5,
            "rag": 1.2,
            "mvp": 1.3,
            "prototype": 1.1,
            "vc": 1.1,
            "pitch": 1.0,
            "consumer ai": 1.2,
            "ai companion": 1.3,
            "gemini": 1.1,
            "deterministic intelligence": 1.5,
            "continuity": 1.3,
            "gtm": 1.0,
            "founder": 1.0,
            "equity": 0.9,
            "advisor role": 1.0,
            "personal intelligence": 1.2,
        },
    },
    anchor_labels={
        "caregiving": "Caregiving",
        "family": "Family",
        "basketball": "Basketball",
        "school": "School",
        "recovery": "Recovery",
        "belonging": "Belonging",
        "leadership": "Leadership",
        "career": "Career",
        "generosity": "Generosity",
        "self_care": "Self Care",
        "sakhi": "Sakhi",
        "life": "Life",
    },
    anchor_priority={
        "caregiving": 10,
        "basketball": 9,
        "school": 8,
        "recovery": 7,
        "belonging": 6,
        "leadership": 5,
        "career": 4,
        "family": 3,
        "generosity": 2,
        "self_care": 1,
        "sakhi": 11,
        "life": 0,
    },
    anchor_aliases={
        "founder journey": "sakhi",
        "startup": "sakhi",
        "startup idea": "sakhi",
        "startup pull": "sakhi",
        "company": "sakhi",
        "work life": "career",
        "job path": "career",
        "care for dad": "caregiving",
        "dad recovery": "caregiving",
        "healing arc": "recovery",
    },
    facet_rules={
        "caregiving": {
            "grief": {"grief": 1.2, "pre-accident": 1.2, "photos": 0.8},
            "caregiving": {"care": 1.0, "caregiving": 1.1, "doctor": 0.8, "confused": 0.7},
            "boundary": {"guilty": 0.7, "tired": 0.6, "heavy": 0.6, "boundary": 1.0},
        },
        "family": {
            "family_pull": {"family": 1.0, "dad": 0.8, "mom": 0.8, "home": 0.4},
            "parenting": {"daughter": 1.0, "son": 1.0, "kids": 1.0, "practice": 0.5},
            "grief": {"grief": 1.1, "miss": 0.6, "photos": 0.6},
        },
        "basketball": {
            "discipline": {"practice": 1.0, "conditioning": 1.0, "drill": 0.9, "footwork": 0.9},
            "confidence": {"confidence": 1.1, "proud": 0.7, "validation": 0.8, "nodded": 0.8},
            "team": {"team": 1.1, "coach": 0.6, "minutes": 0.5, "game": 0.5},
        },
        "school": {
            "school_load": {"school": 1.0, "class": 0.9, "teacher": 0.7, "assignment": 0.7},
            "confidence": {"confidence": 0.8, "good enough": 1.0, "validation": 0.7},
            "discipline": {"study": 0.8, "homework": 0.8, "practice": 0.4},
        },
        "recovery": {
            "recovery": {"recovery": 1.1, "recover": 1.0, "healing": 1.0, "rest": 0.6},
            "confidence": {"confidence": 0.8, "ready": 0.6, "strong": 0.5},
            "patience": {"slow": 0.7, "again": 0.5, "still": 0.4},
        },
        "belonging": {
            "belonging": {"belong": 1.1, "belonging": 1.1, "fit in": 1.0, "accepted": 0.8},
            "confidence": {"validation": 1.0, "noticed": 0.7, "seen": 0.7, "doubt": 0.6},
            "team": {"friends": 0.8, "team": 0.8, "coach": 0.3},
        },
        "leadership": {
            "leadership": {"leadership": 1.2, "manager": 0.8, "team": 0.6},
            "identity": {"identity": 1.0, "storytelling": 0.8, "persuasion": 0.8, "role": 0.5},
            "boundary": {"tone": 0.7, "pushed": 0.6, "heavy": 0.5, "boundary": 1.0},
        },
        "career": {
            "promotion": {"promotion": 1.2, "boss": 0.8, "review": 0.7},
            "workload": {"meeting": 0.8, "meetings": 0.8, "calendar": 0.8, "deadline": 0.9},
            "leadership": {"leadership": 1.0, "team": 0.4, "manager": 0.5},
            "boundary": {"tense": 0.7, "restless": 0.5, "heavy": 0.5, "pushing": 0.6},
        },
        "generosity": {
            "generosity": {"advice": 1.1, "helped": 0.9, "support": 0.8, "mentor": 0.7},
            "leadership": {"team": 0.5, "people": 0.5, "advice": 0.5},
            "boundary": {"too much": 0.8, "tired": 0.5, "heavy": 0.5},
        },
        "self_care": {
            "rest": {"sleep": 1.0, "slept": 1.0, "rest": 0.9, "walk": 0.7},
            "boundary": {"restless": 0.8, "heavy": 0.5, "tense": 0.6, "boundary": 1.0},
            "self_trust": {"strong": 0.7, "clear": 0.7, "daily": 0.5, "yoga": 0.6},
        },
        "sakhi": {
            "ayurveda_engine": {
                "ayurveda": 1.1,
                "ayurvedic": 1.1,
                "wisdom": 0.7,
                "oil": 0.5,
                "remedies": 0.6,
            },
            "product_shape": {
                "product": 0.9,
                "prototype": 0.9,
                "mvp": 1.0,
                "build": 0.6,
                "experience": 0.6,
                "clarity": 0.7,
            },
            "founder_alignment": {
                "ravi": 1.0,
                "equity": 0.9,
                "alignment": 0.9,
                "founder": 0.8,
            },
            "validation": {
                "pitch": 0.8,
                "vc": 1.0,
                "google": 0.8,
                "gemini": 0.9,
                "validation": 0.9,
                "mentor": 0.5,
            },
            "deterministic_core": {
                "knowledge graph": 1.2,
                "rag": 1.0,
                "deterministic intelligence": 1.3,
                "continuity": 1.1,
                "logic": 0.7,
            },
        },
    },
    facet_aliases={
        "career": {
            "career move": "promotion",
            "next role": "promotion",
            "promotion path": "promotion",
            "calendar crush": "workload",
        },
        "caregiving": {
            "dad recovery": "caregiving",
            "waves of grief": "grief",
        },
        "sakhi": {
            "ayurvedic wisdom": "ayurveda_engine",
            "ayurveda personalization": "ayurveda_engine",
            "product feel": "product_shape",
            "personal ai companion": "validation",
            "deterministic continuity": "deterministic_core",
        },
    },
    anchor_negative_rules={
        "career": {
            "dad": 0.8,
            "mom": 0.8,
            "hospital": 0.9,
            "grief": 0.9,
            "caregiving": 1.0,
        },
        "family": {
            "promotion": 0.6,
            "deadline": 0.5,
            "vc": 0.7,
            "mvp": 0.7,
        },
        "caregiving": {
            "promotion": 0.4,
            "vc": 0.4,
        },
        "sakhi": {
            "daughter": 0.7,
            "hospital": 0.7,
        },
    },
    facet_negative_rules={
        "career": {
            "promotion": {"calendar": 0.2, "meetings": 0.2},
            "workload": {"promotion": 0.35, "boss": 0.2},
            "leadership": {"deadline": 0.2},
        },
        "caregiving": {
            "grief": {"doctor": 0.2},
            "caregiving": {"grief": 0.2, "photos": 0.2},
        },
        "sakhi": {
            "ayurveda_engine": {"vc": 0.25, "pitch": 0.2, "google": 0.2},
            "product_shape": {"knowledge graph": 0.25, "deterministic intelligence": 0.25},
            "founder_alignment": {"prototype": 0.2, "mvp": 0.2},
            "validation": {"knowledge graph": 0.25, "continuity": 0.2},
            "deterministic_core": {"prototype": 0.2, "pitch": 0.2},
        },
    },
    positive_cues={
        "clear": 0.4,
        "calm": 0.3,
        "strong": 0.35,
        "ready": 0.35,
        "proud": 0.35,
        "enjoy": 0.35,
        "settled": 0.45,
        "decided": 0.5,
        "committed": 0.55,
        "relief": 0.35,
        "confident": 0.4,
        "finally": 0.35,
    },
    negative_cues={
        "guilty": 0.45,
        "tired": 0.3,
        "heavy": 0.35,
        "restless": 0.4,
        "doubt": 0.45,
        "confused": 0.4,
        "stuck": 0.45,
        "avoid": 0.45,
        "hard": 0.2,
        "tense": 0.35,
        "overthink": 0.35,
        "question": 0.25,
    },
    defer_cues=(
        "for now",
        "not today",
        "later",
        "tomorrow",
        "wait",
        "pushed it",
        "put it off",
        "defer",
    ),
    reversal_cues=(
        "changed my mind",
        "not anymore",
        "pulled back",
        "stepped back",
        "instead",
        "but now",
    ),
)
