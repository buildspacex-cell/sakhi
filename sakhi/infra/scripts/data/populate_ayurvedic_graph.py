"""
Populate Ayurvedic Knowledge Graph with comprehensive data.

Target: 300+ nodes, 1000+ edges for intelligent recommendations.

Node types:
- dosha (3): Vata, Pitta, Kapha
- quality (20): Gunas like light, heavy, oily, dry, hot, cold, etc.
- food (100): With rasa, guna, virya, best_season
- practice (80): Yoga, pranayama, routines, lifestyle
- symptom (60): Mapped to dosha imbalances
- season (6): With dosha effects
- time_window (6): Morning, midday, afternoon, evening, night, early_morning

Edge types:
- PACIFIES: food/practice → dosha
- AGGRAVATES: food/practice → dosha
- INDICATES: symptom → dosha_imbalance
- BALANCES: practice → imbalance
- HAS_QUALITY: food/practice → quality
- OPTIMAL_TIME: practice → time_window
- AMPLIFIES: season → dosha
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List, Tuple

from sakhi.apps.api.core.db import exec as dbexec, q as dbfetch

LOGGER = logging.getLogger(__name__)

# =============================================================================
# NODE DATA
# =============================================================================

DOSHAS = [
    {
        "name": "vata",
        "attrs": {
            "display_name": "Adaptive",
            "elements": ["air", "space"],
            "qualities": ["light", "dry", "cold", "mobile", "subtle", "rough"],
            "body_type": "Thin, light frame",
            "mind_type": "Quick, creative, enthusiastic",
            "imbalance_signs": ["anxiety", "insomnia", "dry_skin", "constipation", "scattered_mind"],
        },
    },
    {
        "name": "pitta",
        "attrs": {
            "display_name": "Performance",
            "elements": ["fire", "water"],
            "qualities": ["hot", "sharp", "light", "oily", "liquid", "spreading"],
            "body_type": "Medium, athletic build",
            "mind_type": "Focused, ambitious, organized",
            "imbalance_signs": ["irritability", "inflammation", "acid_reflux", "skin_rashes", "overheating"],
        },
    },
    {
        "name": "kapha",
        "attrs": {
            "display_name": "Stability",
            "elements": ["earth", "water"],
            "qualities": ["heavy", "slow", "cool", "oily", "smooth", "stable"],
            "body_type": "Solid, strong frame",
            "mind_type": "Calm, loyal, methodical",
            "imbalance_signs": ["lethargy", "weight_gain", "congestion", "attachment", "depression"],
        },
    },
]

QUALITIES = [
    {"name": "light", "attrs": {"opposite": "heavy", "effect": "reduces_kapha"}},
    {"name": "heavy", "attrs": {"opposite": "light", "effect": "reduces_vata"}},
    {"name": "dry", "attrs": {"opposite": "oily", "effect": "aggravates_vata"}},
    {"name": "oily", "attrs": {"opposite": "dry", "effect": "reduces_vata"}},
    {"name": "hot", "attrs": {"opposite": "cold", "effect": "aggravates_pitta"}},
    {"name": "cold", "attrs": {"opposite": "hot", "effect": "reduces_pitta"}},
    {"name": "sharp", "attrs": {"opposite": "dull", "effect": "aggravates_pitta"}},
    {"name": "dull", "attrs": {"opposite": "sharp", "effect": "reduces_pitta"}},
    {"name": "mobile", "attrs": {"opposite": "stable", "effect": "aggravates_vata"}},
    {"name": "stable", "attrs": {"opposite": "mobile", "effect": "reduces_vata"}},
    {"name": "subtle", "attrs": {"opposite": "gross", "effect": "aggravates_vata"}},
    {"name": "gross", "attrs": {"opposite": "subtle", "effect": "reduces_vata"}},
    {"name": "smooth", "attrs": {"opposite": "rough", "effect": "reduces_vata"}},
    {"name": "rough", "attrs": {"opposite": "smooth", "effect": "aggravates_vata"}},
    {"name": "liquid", "attrs": {"opposite": "solid", "effect": "aggravates_pitta"}},
    {"name": "solid", "attrs": {"opposite": "liquid", "effect": "reduces_pitta"}},
    {"name": "soft", "attrs": {"opposite": "hard", "effect": "reduces_vata"}},
    {"name": "hard", "attrs": {"opposite": "soft", "effect": "aggravates_vata"}},
    {"name": "cloudy", "attrs": {"opposite": "clear", "effect": "aggravates_kapha"}},
    {"name": "clear", "attrs": {"opposite": "cloudy", "effect": "reduces_kapha"}},
]

SEASONS = [
    {"name": "winter", "attrs": {"months": [12, 1, 2], "dominant_dosha": "vata", "amplification": 1.5}},
    {"name": "spring", "attrs": {"months": [3, 4, 5], "dominant_dosha": "kapha", "amplification": 1.4}},
    {"name": "summer", "attrs": {"months": [6, 7, 8], "dominant_dosha": "pitta", "amplification": 1.5}},
    {"name": "fall", "attrs": {"months": [9, 10, 11], "dominant_dosha": "vata", "amplification": 1.3}},
    {"name": "monsoon", "attrs": {"months": [7, 8], "dominant_dosha": "vata", "amplification": 1.2}},
    {"name": "late_summer", "attrs": {"months": [8, 9], "dominant_dosha": "pitta", "amplification": 1.2}},
]

TIME_WINDOWS = [
    {"name": "early_morning", "attrs": {"hours": [4, 5, 6], "dominant_dosha": "vata", "best_for": ["meditation", "yoga"]}},
    {"name": "morning", "attrs": {"hours": [6, 7, 8, 9, 10], "dominant_dosha": "kapha", "best_for": ["exercise", "heavy_tasks"]}},
    {"name": "midday", "attrs": {"hours": [10, 11, 12, 13, 14], "dominant_dosha": "pitta", "best_for": ["main_meal", "focused_work"]}},
    {"name": "afternoon", "attrs": {"hours": [14, 15, 16, 17], "dominant_dosha": "vata", "best_for": ["creative_work", "meetings"]}},
    {"name": "evening", "attrs": {"hours": [18, 19, 20, 21], "dominant_dosha": "kapha", "best_for": ["light_dinner", "relaxation"]}},
    {"name": "night", "attrs": {"hours": [22, 23, 0, 1, 2, 3], "dominant_dosha": "pitta", "best_for": ["sleep", "deep_rest"]}},
]

# 100 foods with Ayurvedic properties
FOODS = [
    # Grains (15)
    {"name": "rice_basmati", "attrs": {"rasa": "sweet", "virya": "cooling", "pacifies": ["pitta", "vata"], "aggravates": [], "season": "all"}},
    {"name": "rice_brown", "attrs": {"rasa": "sweet", "virya": "warming", "pacifies": ["kapha"], "aggravates": ["vata"], "season": "all"}},
    {"name": "oats", "attrs": {"rasa": "sweet", "virya": "warming", "pacifies": ["vata"], "aggravates": ["kapha"], "season": "winter"}},
    {"name": "quinoa", "attrs": {"rasa": "astringent", "virya": "warming", "pacifies": ["kapha"], "aggravates": ["vata"], "season": "all"}},
    {"name": "wheat", "attrs": {"rasa": "sweet", "virya": "cooling", "pacifies": ["vata", "pitta"], "aggravates": ["kapha"], "season": "all"}},
    {"name": "barley", "attrs": {"rasa": "sweet", "virya": "cooling", "pacifies": ["pitta", "kapha"], "aggravates": ["vata"], "season": "summer"}},
    {"name": "millet", "attrs": {"rasa": "sweet", "virya": "warming", "pacifies": ["kapha"], "aggravates": ["vata"], "season": "winter"}},
    {"name": "corn", "attrs": {"rasa": "sweet", "virya": "warming", "pacifies": ["kapha"], "aggravates": ["pitta"], "season": "summer"}},
    {"name": "buckwheat", "attrs": {"rasa": "astringent", "virya": "warming", "pacifies": ["kapha"], "aggravates": ["pitta"], "season": "winter"}},
    {"name": "amaranth", "attrs": {"rasa": "astringent", "virya": "warming", "pacifies": ["kapha", "vata"], "aggravates": [], "season": "all"}},
    {"name": "rye", "attrs": {"rasa": "astringent", "virya": "warming", "pacifies": ["kapha"], "aggravates": ["vata"], "season": "winter"}},
    {"name": "spelt", "attrs": {"rasa": "sweet", "virya": "cooling", "pacifies": ["vata", "pitta"], "aggravates": ["kapha"], "season": "all"}},
    {"name": "couscous", "attrs": {"rasa": "sweet", "virya": "cooling", "pacifies": ["pitta"], "aggravates": ["kapha"], "season": "summer"}},
    {"name": "polenta", "attrs": {"rasa": "sweet", "virya": "warming", "pacifies": ["vata"], "aggravates": ["pitta"], "season": "winter"}},
    {"name": "tapioca", "attrs": {"rasa": "sweet", "virya": "cooling", "pacifies": ["pitta", "vata"], "aggravates": ["kapha"], "season": "summer"}},

    # Legumes (10)
    {"name": "mung_beans", "attrs": {"rasa": "sweet", "virya": "cooling", "pacifies": ["pitta", "kapha"], "aggravates": [], "season": "all"}},
    {"name": "lentils_red", "attrs": {"rasa": "astringent", "virya": "warming", "pacifies": ["kapha"], "aggravates": ["vata"], "season": "winter"}},
    {"name": "chickpeas", "attrs": {"rasa": "astringent", "virya": "cooling", "pacifies": ["pitta"], "aggravates": ["vata"], "season": "summer"}},
    {"name": "black_beans", "attrs": {"rasa": "astringent", "virya": "cooling", "pacifies": ["pitta"], "aggravates": ["vata"], "season": "summer"}},
    {"name": "kidney_beans", "attrs": {"rasa": "astringent", "virya": "cooling", "pacifies": ["pitta"], "aggravates": ["vata", "kapha"], "season": "summer"}},
    {"name": "tofu", "attrs": {"rasa": "sweet", "virya": "cooling", "pacifies": ["pitta"], "aggravates": ["vata", "kapha"], "season": "summer"}},
    {"name": "tempeh", "attrs": {"rasa": "astringent", "virya": "warming", "pacifies": ["kapha"], "aggravates": ["pitta"], "season": "winter"}},
    {"name": "split_peas", "attrs": {"rasa": "astringent", "virya": "cooling", "pacifies": ["pitta", "kapha"], "aggravates": ["vata"], "season": "summer"}},
    {"name": "adzuki_beans", "attrs": {"rasa": "sweet", "virya": "cooling", "pacifies": ["pitta", "kapha"], "aggravates": [], "season": "summer"}},
    {"name": "urad_dal", "attrs": {"rasa": "sweet", "virya": "warming", "pacifies": ["vata"], "aggravates": ["pitta", "kapha"], "season": "winter"}},

    # Vegetables (20)
    {"name": "sweet_potato", "attrs": {"rasa": "sweet", "virya": "cooling", "pacifies": ["vata", "pitta"], "aggravates": ["kapha"], "season": "fall"}},
    {"name": "carrots", "attrs": {"rasa": "sweet", "virya": "warming", "pacifies": ["vata"], "aggravates": [], "season": "all"}},
    {"name": "beets", "attrs": {"rasa": "sweet", "virya": "warming", "pacifies": ["vata"], "aggravates": ["pitta"], "season": "fall"}},
    {"name": "spinach", "attrs": {"rasa": "astringent", "virya": "cooling", "pacifies": ["pitta", "kapha"], "aggravates": ["vata"], "season": "spring"}},
    {"name": "kale", "attrs": {"rasa": "bitter", "virya": "cooling", "pacifies": ["pitta", "kapha"], "aggravates": ["vata"], "season": "spring"}},
    {"name": "zucchini", "attrs": {"rasa": "sweet", "virya": "cooling", "pacifies": ["pitta", "vata"], "aggravates": ["kapha"], "season": "summer"}},
    {"name": "cucumber", "attrs": {"rasa": "sweet", "virya": "cooling", "pacifies": ["pitta"], "aggravates": ["vata", "kapha"], "season": "summer"}},
    {"name": "asparagus", "attrs": {"rasa": "sweet", "virya": "cooling", "pacifies": ["pitta", "vata"], "aggravates": [], "season": "spring"}},
    {"name": "broccoli", "attrs": {"rasa": "astringent", "virya": "cooling", "pacifies": ["pitta", "kapha"], "aggravates": ["vata"], "season": "fall"}},
    {"name": "cauliflower", "attrs": {"rasa": "astringent", "virya": "cooling", "pacifies": ["pitta", "kapha"], "aggravates": ["vata"], "season": "fall"}},
    {"name": "pumpkin", "attrs": {"rasa": "sweet", "virya": "warming", "pacifies": ["vata", "pitta"], "aggravates": ["kapha"], "season": "fall"}},
    {"name": "squash", "attrs": {"rasa": "sweet", "virya": "warming", "pacifies": ["vata"], "aggravates": ["kapha"], "season": "fall"}},
    {"name": "green_beans", "attrs": {"rasa": "astringent", "virya": "cooling", "pacifies": ["pitta", "kapha"], "aggravates": ["vata"], "season": "summer"}},
    {"name": "okra", "attrs": {"rasa": "sweet", "virya": "cooling", "pacifies": ["pitta", "vata"], "aggravates": ["kapha"], "season": "summer"}},
    {"name": "celery", "attrs": {"rasa": "astringent", "virya": "cooling", "pacifies": ["pitta", "kapha"], "aggravates": ["vata"], "season": "summer"}},
    {"name": "fennel", "attrs": {"rasa": "sweet", "virya": "cooling", "pacifies": ["pitta", "vata"], "aggravates": [], "season": "all"}},
    {"name": "artichoke", "attrs": {"rasa": "bitter", "virya": "cooling", "pacifies": ["pitta", "kapha"], "aggravates": ["vata"], "season": "spring"}},
    {"name": "cabbage", "attrs": {"rasa": "astringent", "virya": "cooling", "pacifies": ["pitta", "kapha"], "aggravates": ["vata"], "season": "winter"}},
    {"name": "brussels_sprouts", "attrs": {"rasa": "astringent", "virya": "cooling", "pacifies": ["pitta", "kapha"], "aggravates": ["vata"], "season": "winter"}},
    {"name": "radish", "attrs": {"rasa": "pungent", "virya": "warming", "pacifies": ["kapha"], "aggravates": ["pitta", "vata"], "season": "spring"}},

    # Fruits (15)
    {"name": "banana", "attrs": {"rasa": "sweet", "virya": "cooling", "pacifies": ["pitta", "vata"], "aggravates": ["kapha"], "season": "all"}},
    {"name": "apple", "attrs": {"rasa": "sweet", "virya": "cooling", "pacifies": ["pitta"], "aggravates": ["vata"], "season": "fall"}},
    {"name": "mango", "attrs": {"rasa": "sweet", "virya": "warming", "pacifies": ["vata"], "aggravates": ["pitta"], "season": "summer"}},
    {"name": "papaya", "attrs": {"rasa": "sweet", "virya": "warming", "pacifies": ["vata", "kapha"], "aggravates": ["pitta"], "season": "summer"}},
    {"name": "grapes", "attrs": {"rasa": "sweet", "virya": "cooling", "pacifies": ["pitta", "vata"], "aggravates": ["kapha"], "season": "fall"}},
    {"name": "pomegranate", "attrs": {"rasa": "sweet", "virya": "cooling", "pacifies": ["pitta"], "aggravates": [], "season": "fall"}},
    {"name": "dates", "attrs": {"rasa": "sweet", "virya": "warming", "pacifies": ["vata", "pitta"], "aggravates": ["kapha"], "season": "winter"}},
    {"name": "figs", "attrs": {"rasa": "sweet", "virya": "cooling", "pacifies": ["vata", "pitta"], "aggravates": ["kapha"], "season": "summer"}},
    {"name": "coconut", "attrs": {"rasa": "sweet", "virya": "cooling", "pacifies": ["pitta", "vata"], "aggravates": ["kapha"], "season": "summer"}},
    {"name": "avocado", "attrs": {"rasa": "sweet", "virya": "cooling", "pacifies": ["vata", "pitta"], "aggravates": ["kapha"], "season": "all"}},
    {"name": "berries", "attrs": {"rasa": "sweet", "virya": "cooling", "pacifies": ["pitta"], "aggravates": ["kapha"], "season": "summer"}},
    {"name": "melon", "attrs": {"rasa": "sweet", "virya": "cooling", "pacifies": ["pitta"], "aggravates": ["vata", "kapha"], "season": "summer"}},
    {"name": "pear", "attrs": {"rasa": "sweet", "virya": "cooling", "pacifies": ["pitta"], "aggravates": ["vata", "kapha"], "season": "fall"}},
    {"name": "peach", "attrs": {"rasa": "sweet", "virya": "warming", "pacifies": ["vata"], "aggravates": ["pitta"], "season": "summer"}},
    {"name": "cherries", "attrs": {"rasa": "sweet", "virya": "cooling", "pacifies": ["pitta", "vata"], "aggravates": ["kapha"], "season": "summer"}},

    # Dairy & Alternatives (10)
    {"name": "ghee", "attrs": {"rasa": "sweet", "virya": "cooling", "pacifies": ["pitta", "vata"], "aggravates": [], "season": "all"}},
    {"name": "milk_warm", "attrs": {"rasa": "sweet", "virya": "cooling", "pacifies": ["pitta", "vata"], "aggravates": ["kapha"], "season": "all"}},
    {"name": "yogurt", "attrs": {"rasa": "sour", "virya": "warming", "pacifies": ["vata"], "aggravates": ["pitta", "kapha"], "season": "winter"}},
    {"name": "buttermilk", "attrs": {"rasa": "sour", "virya": "cooling", "pacifies": ["vata", "kapha"], "aggravates": ["pitta"], "season": "summer"}},
    {"name": "paneer", "attrs": {"rasa": "sweet", "virya": "cooling", "pacifies": ["pitta", "vata"], "aggravates": ["kapha"], "season": "all"}},
    {"name": "almond_milk", "attrs": {"rasa": "sweet", "virya": "cooling", "pacifies": ["pitta", "vata"], "aggravates": ["kapha"], "season": "all"}},
    {"name": "oat_milk", "attrs": {"rasa": "sweet", "virya": "warming", "pacifies": ["vata"], "aggravates": ["kapha"], "season": "winter"}},
    {"name": "coconut_milk", "attrs": {"rasa": "sweet", "virya": "cooling", "pacifies": ["pitta", "vata"], "aggravates": ["kapha"], "season": "summer"}},
    {"name": "cottage_cheese", "attrs": {"rasa": "sweet", "virya": "cooling", "pacifies": ["pitta"], "aggravates": ["kapha"], "season": "all"}},
    {"name": "kefir", "attrs": {"rasa": "sour", "virya": "cooling", "pacifies": ["vata"], "aggravates": ["pitta", "kapha"], "season": "summer"}},

    # Spices & Herbs (20)
    {"name": "ginger", "attrs": {"rasa": "pungent", "virya": "warming", "pacifies": ["vata", "kapha"], "aggravates": ["pitta"], "season": "winter"}},
    {"name": "turmeric", "attrs": {"rasa": "bitter", "virya": "warming", "pacifies": ["kapha"], "aggravates": [], "season": "all"}},
    {"name": "cumin", "attrs": {"rasa": "pungent", "virya": "cooling", "pacifies": ["vata", "kapha"], "aggravates": [], "season": "all"}},
    {"name": "coriander", "attrs": {"rasa": "astringent", "virya": "cooling", "pacifies": ["pitta", "vata", "kapha"], "aggravates": [], "season": "all"}},
    {"name": "cardamom", "attrs": {"rasa": "sweet", "virya": "cooling", "pacifies": ["vata", "kapha"], "aggravates": [], "season": "all"}},
    {"name": "cinnamon", "attrs": {"rasa": "sweet", "virya": "warming", "pacifies": ["vata", "kapha"], "aggravates": ["pitta"], "season": "winter"}},
    {"name": "black_pepper", "attrs": {"rasa": "pungent", "virya": "warming", "pacifies": ["kapha"], "aggravates": ["pitta"], "season": "winter"}},
    {"name": "fennel_seeds", "attrs": {"rasa": "sweet", "virya": "cooling", "pacifies": ["pitta", "vata", "kapha"], "aggravates": [], "season": "all"}},
    {"name": "fenugreek", "attrs": {"rasa": "bitter", "virya": "warming", "pacifies": ["vata", "kapha"], "aggravates": ["pitta"], "season": "winter"}},
    {"name": "mustard_seeds", "attrs": {"rasa": "pungent", "virya": "warming", "pacifies": ["kapha"], "aggravates": ["pitta"], "season": "winter"}},
    {"name": "cloves", "attrs": {"rasa": "pungent", "virya": "warming", "pacifies": ["vata", "kapha"], "aggravates": ["pitta"], "season": "winter"}},
    {"name": "nutmeg", "attrs": {"rasa": "pungent", "virya": "warming", "pacifies": ["vata", "kapha"], "aggravates": ["pitta"], "season": "winter"}},
    {"name": "saffron", "attrs": {"rasa": "sweet", "virya": "cooling", "pacifies": ["pitta", "vata", "kapha"], "aggravates": [], "season": "all"}},
    {"name": "basil", "attrs": {"rasa": "pungent", "virya": "warming", "pacifies": ["vata", "kapha"], "aggravates": ["pitta"], "season": "summer"}},
    {"name": "mint", "attrs": {"rasa": "pungent", "virya": "cooling", "pacifies": ["pitta", "kapha"], "aggravates": ["vata"], "season": "summer"}},
    {"name": "rosemary", "attrs": {"rasa": "pungent", "virya": "warming", "pacifies": ["kapha"], "aggravates": ["pitta"], "season": "winter"}},
    {"name": "thyme", "attrs": {"rasa": "pungent", "virya": "warming", "pacifies": ["kapha"], "aggravates": ["pitta"], "season": "winter"}},
    {"name": "oregano", "attrs": {"rasa": "pungent", "virya": "warming", "pacifies": ["kapha"], "aggravates": ["pitta"], "season": "winter"}},
    {"name": "asafoetida", "attrs": {"rasa": "pungent", "virya": "warming", "pacifies": ["vata", "kapha"], "aggravates": ["pitta"], "season": "all"}},
    {"name": "bay_leaf", "attrs": {"rasa": "pungent", "virya": "warming", "pacifies": ["vata", "kapha"], "aggravates": ["pitta"], "season": "winter"}},

    # Oils & Fats (5)
    {"name": "sesame_oil", "attrs": {"rasa": "sweet", "virya": "warming", "pacifies": ["vata"], "aggravates": ["pitta", "kapha"], "season": "winter"}},
    {"name": "coconut_oil", "attrs": {"rasa": "sweet", "virya": "cooling", "pacifies": ["pitta", "vata"], "aggravates": ["kapha"], "season": "summer"}},
    {"name": "olive_oil", "attrs": {"rasa": "sweet", "virya": "warming", "pacifies": ["vata"], "aggravates": ["pitta", "kapha"], "season": "all"}},
    {"name": "sunflower_oil", "attrs": {"rasa": "sweet", "virya": "cooling", "pacifies": ["pitta"], "aggravates": ["kapha"], "season": "summer"}},
    {"name": "mustard_oil", "attrs": {"rasa": "pungent", "virya": "warming", "pacifies": ["kapha"], "aggravates": ["pitta"], "season": "winter"}},

    # Nuts & Seeds (5)
    {"name": "almonds", "attrs": {"rasa": "sweet", "virya": "warming", "pacifies": ["vata"], "aggravates": ["pitta", "kapha"], "season": "all"}},
    {"name": "cashews", "attrs": {"rasa": "sweet", "virya": "warming", "pacifies": ["vata"], "aggravates": ["pitta", "kapha"], "season": "all"}},
    {"name": "walnuts", "attrs": {"rasa": "sweet", "virya": "warming", "pacifies": ["vata"], "aggravates": ["pitta", "kapha"], "season": "winter"}},
    {"name": "pumpkin_seeds", "attrs": {"rasa": "sweet", "virya": "cooling", "pacifies": ["pitta", "vata"], "aggravates": ["kapha"], "season": "fall"}},
    {"name": "sunflower_seeds", "attrs": {"rasa": "sweet", "virya": "cooling", "pacifies": ["pitta"], "aggravates": ["kapha"], "season": "summer"}},
]

# 80 practices
PRACTICES = [
    # Yoga Asanas (25)
    {"name": "child_pose", "attrs": {"type": "yoga", "intensity": "gentle", "pacifies": ["vata", "pitta"], "duration_min": 3, "time": "any"}},
    {"name": "corpse_pose", "attrs": {"type": "yoga", "intensity": "restorative", "pacifies": ["vata", "pitta", "kapha"], "duration_min": 10, "time": "evening"}},
    {"name": "forward_fold", "attrs": {"type": "yoga", "intensity": "gentle", "pacifies": ["pitta"], "duration_min": 2, "time": "any"}},
    {"name": "cat_cow", "attrs": {"type": "yoga", "intensity": "gentle", "pacifies": ["vata"], "duration_min": 3, "time": "morning"}},
    {"name": "downward_dog", "attrs": {"type": "yoga", "intensity": "moderate", "pacifies": ["kapha"], "duration_min": 2, "time": "morning"}},
    {"name": "warrior_one", "attrs": {"type": "yoga", "intensity": "active", "pacifies": ["kapha"], "duration_min": 2, "time": "morning"}},
    {"name": "warrior_two", "attrs": {"type": "yoga", "intensity": "active", "pacifies": ["kapha"], "duration_min": 2, "time": "morning"}},
    {"name": "tree_pose", "attrs": {"type": "yoga", "intensity": "moderate", "pacifies": ["vata"], "duration_min": 2, "time": "any"}},
    {"name": "seated_twist", "attrs": {"type": "yoga", "intensity": "gentle", "pacifies": ["pitta", "kapha"], "duration_min": 3, "time": "any"}},
    {"name": "bridge_pose", "attrs": {"type": "yoga", "intensity": "moderate", "pacifies": ["vata"], "duration_min": 3, "time": "evening"}},
    {"name": "legs_up_wall", "attrs": {"type": "yoga", "intensity": "restorative", "pacifies": ["vata", "pitta"], "duration_min": 10, "time": "evening"}},
    {"name": "sun_salutation", "attrs": {"type": "yoga", "intensity": "active", "pacifies": ["kapha"], "duration_min": 15, "time": "morning"}},
    {"name": "moon_salutation", "attrs": {"type": "yoga", "intensity": "gentle", "pacifies": ["pitta"], "duration_min": 15, "time": "evening"}},
    {"name": "cobra_pose", "attrs": {"type": "yoga", "intensity": "moderate", "pacifies": ["kapha"], "duration_min": 2, "time": "morning"}},
    {"name": "shoulder_stand", "attrs": {"type": "yoga", "intensity": "active", "pacifies": ["pitta"], "duration_min": 5, "time": "evening"}},
    {"name": "fish_pose", "attrs": {"type": "yoga", "intensity": "moderate", "pacifies": ["kapha"], "duration_min": 3, "time": "any"}},
    {"name": "pigeon_pose", "attrs": {"type": "yoga", "intensity": "moderate", "pacifies": ["vata"], "duration_min": 5, "time": "evening"}},
    {"name": "reclined_butterfly", "attrs": {"type": "yoga", "intensity": "restorative", "pacifies": ["vata", "pitta"], "duration_min": 5, "time": "evening"}},
    {"name": "standing_forward_bend", "attrs": {"type": "yoga", "intensity": "gentle", "pacifies": ["pitta"], "duration_min": 2, "time": "any"}},
    {"name": "triangle_pose", "attrs": {"type": "yoga", "intensity": "moderate", "pacifies": ["kapha"], "duration_min": 2, "time": "morning"}},
    {"name": "half_moon_pose", "attrs": {"type": "yoga", "intensity": "active", "pacifies": ["kapha"], "duration_min": 2, "time": "morning"}},
    {"name": "camel_pose", "attrs": {"type": "yoga", "intensity": "active", "pacifies": ["kapha"], "duration_min": 2, "time": "morning"}},
    {"name": "bow_pose", "attrs": {"type": "yoga", "intensity": "active", "pacifies": ["kapha"], "duration_min": 3, "time": "morning"}},
    {"name": "headstand", "attrs": {"type": "yoga", "intensity": "advanced", "pacifies": ["vata"], "duration_min": 5, "time": "morning"}},
    {"name": "lotus_pose", "attrs": {"type": "yoga", "intensity": "gentle", "pacifies": ["vata"], "duration_min": 10, "time": "any"}},

    # Pranayama (15)
    {"name": "nadi_shodhana", "attrs": {"type": "pranayama", "intensity": "gentle", "pacifies": ["vata", "pitta", "kapha"], "duration_min": 10, "time": "any"}},
    {"name": "ujjayi_breath", "attrs": {"type": "pranayama", "intensity": "gentle", "pacifies": ["vata"], "duration_min": 5, "time": "any"}},
    {"name": "kapalabhati", "attrs": {"type": "pranayama", "intensity": "active", "pacifies": ["kapha"], "duration_min": 5, "time": "morning"}},
    {"name": "bhramari", "attrs": {"type": "pranayama", "intensity": "gentle", "pacifies": ["vata", "pitta"], "duration_min": 5, "time": "evening"}},
    {"name": "sitali", "attrs": {"type": "pranayama", "intensity": "gentle", "pacifies": ["pitta"], "duration_min": 5, "time": "midday"}},
    {"name": "sitkari", "attrs": {"type": "pranayama", "intensity": "gentle", "pacifies": ["pitta"], "duration_min": 5, "time": "midday"}},
    {"name": "bhastrika", "attrs": {"type": "pranayama", "intensity": "active", "pacifies": ["kapha"], "duration_min": 5, "time": "morning"}},
    {"name": "anulom_vilom", "attrs": {"type": "pranayama", "intensity": "gentle", "pacifies": ["vata", "pitta", "kapha"], "duration_min": 10, "time": "any"}},
    {"name": "box_breathing", "attrs": {"type": "pranayama", "intensity": "gentle", "pacifies": ["vata", "pitta"], "duration_min": 5, "time": "any"}},
    {"name": "478_breathing", "attrs": {"type": "pranayama", "intensity": "gentle", "pacifies": ["vata"], "duration_min": 5, "time": "evening"}},
    {"name": "diaphragmatic_breathing", "attrs": {"type": "pranayama", "intensity": "gentle", "pacifies": ["vata", "pitta"], "duration_min": 5, "time": "any"}},
    {"name": "belly_breathing", "attrs": {"type": "pranayama", "intensity": "gentle", "pacifies": ["vata"], "duration_min": 5, "time": "any"}},
    {"name": "three_part_breath", "attrs": {"type": "pranayama", "intensity": "gentle", "pacifies": ["vata"], "duration_min": 5, "time": "any"}},
    {"name": "lions_breath", "attrs": {"type": "pranayama", "intensity": "moderate", "pacifies": ["kapha"], "duration_min": 3, "time": "morning"}},
    {"name": "cooling_breath", "attrs": {"type": "pranayama", "intensity": "gentle", "pacifies": ["pitta"], "duration_min": 5, "time": "midday"}},

    # Meditation (10)
    {"name": "mindfulness_meditation", "attrs": {"type": "meditation", "intensity": "gentle", "pacifies": ["vata", "pitta", "kapha"], "duration_min": 20, "time": "early_morning"}},
    {"name": "body_scan", "attrs": {"type": "meditation", "intensity": "gentle", "pacifies": ["vata", "pitta"], "duration_min": 15, "time": "evening"}},
    {"name": "loving_kindness", "attrs": {"type": "meditation", "intensity": "gentle", "pacifies": ["pitta"], "duration_min": 15, "time": "any"}},
    {"name": "mantra_meditation", "attrs": {"type": "meditation", "intensity": "gentle", "pacifies": ["vata"], "duration_min": 20, "time": "early_morning"}},
    {"name": "visualization", "attrs": {"type": "meditation", "intensity": "gentle", "pacifies": ["vata", "pitta"], "duration_min": 15, "time": "any"}},
    {"name": "trataka", "attrs": {"type": "meditation", "intensity": "moderate", "pacifies": ["kapha"], "duration_min": 10, "time": "evening"}},
    {"name": "yoga_nidra", "attrs": {"type": "meditation", "intensity": "restorative", "pacifies": ["vata", "pitta"], "duration_min": 30, "time": "evening"}},
    {"name": "walking_meditation", "attrs": {"type": "meditation", "intensity": "gentle", "pacifies": ["kapha"], "duration_min": 20, "time": "morning"}},
    {"name": "breath_awareness", "attrs": {"type": "meditation", "intensity": "gentle", "pacifies": ["vata", "pitta", "kapha"], "duration_min": 10, "time": "any"}},
    {"name": "sound_meditation", "attrs": {"type": "meditation", "intensity": "gentle", "pacifies": ["vata"], "duration_min": 15, "time": "evening"}},

    # Daily Routines (Dinacharya) (15)
    {"name": "oil_pulling", "attrs": {"type": "dinacharya", "intensity": "gentle", "pacifies": ["vata", "kapha"], "duration_min": 15, "time": "early_morning"}},
    {"name": "tongue_scraping", "attrs": {"type": "dinacharya", "intensity": "gentle", "pacifies": ["kapha"], "duration_min": 2, "time": "early_morning"}},
    {"name": "abhyanga", "attrs": {"type": "dinacharya", "intensity": "gentle", "pacifies": ["vata"], "duration_min": 20, "time": "morning"}},
    {"name": "dry_brushing", "attrs": {"type": "dinacharya", "intensity": "moderate", "pacifies": ["kapha"], "duration_min": 5, "time": "morning"}},
    {"name": "nasya", "attrs": {"type": "dinacharya", "intensity": "gentle", "pacifies": ["vata"], "duration_min": 5, "time": "morning"}},
    {"name": "warm_water_morning", "attrs": {"type": "dinacharya", "intensity": "gentle", "pacifies": ["kapha"], "duration_min": 5, "time": "early_morning"}},
    {"name": "early_rising", "attrs": {"type": "dinacharya", "intensity": "gentle", "pacifies": ["kapha"], "duration_min": 0, "time": "early_morning"}},
    {"name": "regular_meals", "attrs": {"type": "dinacharya", "intensity": "gentle", "pacifies": ["vata"], "duration_min": 0, "time": "any"}},
    {"name": "early_dinner", "attrs": {"type": "dinacharya", "intensity": "gentle", "pacifies": ["pitta", "kapha"], "duration_min": 0, "time": "evening"}},
    {"name": "foot_massage", "attrs": {"type": "dinacharya", "intensity": "gentle", "pacifies": ["vata", "pitta"], "duration_min": 10, "time": "evening"}},
    {"name": "warm_bath", "attrs": {"type": "dinacharya", "intensity": "gentle", "pacifies": ["vata"], "duration_min": 20, "time": "evening"}},
    {"name": "cold_shower", "attrs": {"type": "dinacharya", "intensity": "active", "pacifies": ["kapha", "pitta"], "duration_min": 5, "time": "morning"}},
    {"name": "journaling", "attrs": {"type": "dinacharya", "intensity": "gentle", "pacifies": ["vata", "pitta"], "duration_min": 15, "time": "evening"}},
    {"name": "gratitude_practice", "attrs": {"type": "dinacharya", "intensity": "gentle", "pacifies": ["pitta"], "duration_min": 5, "time": "any"}},
    {"name": "digital_detox", "attrs": {"type": "dinacharya", "intensity": "gentle", "pacifies": ["vata", "pitta"], "duration_min": 60, "time": "evening"}},

    # Exercise & Movement (15)
    {"name": "walking", "attrs": {"type": "exercise", "intensity": "gentle", "pacifies": ["vata", "pitta", "kapha"], "duration_min": 30, "time": "any"}},
    {"name": "swimming", "attrs": {"type": "exercise", "intensity": "moderate", "pacifies": ["pitta"], "duration_min": 30, "time": "any"}},
    {"name": "cycling", "attrs": {"type": "exercise", "intensity": "moderate", "pacifies": ["kapha"], "duration_min": 30, "time": "morning"}},
    {"name": "hiking", "attrs": {"type": "exercise", "intensity": "moderate", "pacifies": ["kapha"], "duration_min": 60, "time": "morning"}},
    {"name": "tai_chi", "attrs": {"type": "exercise", "intensity": "gentle", "pacifies": ["vata", "pitta"], "duration_min": 30, "time": "morning"}},
    {"name": "qi_gong", "attrs": {"type": "exercise", "intensity": "gentle", "pacifies": ["vata"], "duration_min": 20, "time": "morning"}},
    {"name": "dancing", "attrs": {"type": "exercise", "intensity": "active", "pacifies": ["kapha"], "duration_min": 30, "time": "any"}},
    {"name": "stretching", "attrs": {"type": "exercise", "intensity": "gentle", "pacifies": ["vata"], "duration_min": 15, "time": "any"}},
    {"name": "strength_training", "attrs": {"type": "exercise", "intensity": "active", "pacifies": ["kapha"], "duration_min": 45, "time": "morning"}},
    {"name": "jogging", "attrs": {"type": "exercise", "intensity": "active", "pacifies": ["kapha"], "duration_min": 30, "time": "morning"}},
    {"name": "running", "attrs": {"type": "exercise", "intensity": "intense", "pacifies": ["kapha"], "duration_min": 30, "time": "morning"}},
    {"name": "pilates", "attrs": {"type": "exercise", "intensity": "moderate", "pacifies": ["vata", "kapha"], "duration_min": 45, "time": "morning"}},
    {"name": "restorative_yoga", "attrs": {"type": "exercise", "intensity": "restorative", "pacifies": ["vata", "pitta"], "duration_min": 45, "time": "evening"}},
    {"name": "gentle_stretching", "attrs": {"type": "exercise", "intensity": "gentle", "pacifies": ["vata"], "duration_min": 15, "time": "evening"}},
    {"name": "nature_walk", "attrs": {"type": "exercise", "intensity": "gentle", "pacifies": ["vata", "pitta", "kapha"], "duration_min": 30, "time": "morning"}},
]

# 60 symptoms
SYMPTOMS = [
    # Vata imbalance symptoms
    {"name": "anxiety", "attrs": {"indicates": "vata", "severity": "moderate", "category": "mental"}},
    {"name": "insomnia", "attrs": {"indicates": "vata", "severity": "moderate", "category": "sleep"}},
    {"name": "dry_skin", "attrs": {"indicates": "vata", "severity": "mild", "category": "skin"}},
    {"name": "constipation", "attrs": {"indicates": "vata", "severity": "moderate", "category": "digestive"}},
    {"name": "bloating", "attrs": {"indicates": "vata", "severity": "mild", "category": "digestive"}},
    {"name": "joint_pain", "attrs": {"indicates": "vata", "severity": "moderate", "category": "physical"}},
    {"name": "cold_hands_feet", "attrs": {"indicates": "vata", "severity": "mild", "category": "circulation"}},
    {"name": "racing_thoughts", "attrs": {"indicates": "vata", "severity": "moderate", "category": "mental"}},
    {"name": "restlessness", "attrs": {"indicates": "vata", "severity": "moderate", "category": "mental"}},
    {"name": "fatigue", "attrs": {"indicates": "vata", "severity": "moderate", "category": "energy"}},
    {"name": "weight_loss", "attrs": {"indicates": "vata", "severity": "mild", "category": "physical"}},
    {"name": "cracking_joints", "attrs": {"indicates": "vata", "severity": "mild", "category": "physical"}},
    {"name": "brittle_nails", "attrs": {"indicates": "vata", "severity": "mild", "category": "physical"}},
    {"name": "forgetfulness", "attrs": {"indicates": "vata", "severity": "mild", "category": "mental"}},
    {"name": "scattered_mind", "attrs": {"indicates": "vata", "severity": "moderate", "category": "mental"}},
    {"name": "light_sleep", "attrs": {"indicates": "vata", "severity": "mild", "category": "sleep"}},
    {"name": "gas", "attrs": {"indicates": "vata", "severity": "mild", "category": "digestive"}},
    {"name": "dry_hair", "attrs": {"indicates": "vata", "severity": "mild", "category": "physical"}},
    {"name": "nervousness", "attrs": {"indicates": "vata", "severity": "moderate", "category": "mental"}},
    {"name": "muscle_twitching", "attrs": {"indicates": "vata", "severity": "mild", "category": "physical"}},

    # Pitta imbalance symptoms
    {"name": "irritability", "attrs": {"indicates": "pitta", "severity": "moderate", "category": "mental"}},
    {"name": "anger", "attrs": {"indicates": "pitta", "severity": "moderate", "category": "mental"}},
    {"name": "acid_reflux", "attrs": {"indicates": "pitta", "severity": "moderate", "category": "digestive"}},
    {"name": "skin_rashes", "attrs": {"indicates": "pitta", "severity": "mild", "category": "skin"}},
    {"name": "overheating", "attrs": {"indicates": "pitta", "severity": "moderate", "category": "physical"}},
    {"name": "excessive_sweating", "attrs": {"indicates": "pitta", "severity": "mild", "category": "physical"}},
    {"name": "inflammation", "attrs": {"indicates": "pitta", "severity": "moderate", "category": "physical"}},
    {"name": "heartburn", "attrs": {"indicates": "pitta", "severity": "moderate", "category": "digestive"}},
    {"name": "diarrhea", "attrs": {"indicates": "pitta", "severity": "moderate", "category": "digestive"}},
    {"name": "impatience", "attrs": {"indicates": "pitta", "severity": "mild", "category": "mental"}},
    {"name": "criticism", "attrs": {"indicates": "pitta", "severity": "mild", "category": "mental"}},
    {"name": "perfectionism", "attrs": {"indicates": "pitta", "severity": "mild", "category": "mental"}},
    {"name": "acne", "attrs": {"indicates": "pitta", "severity": "mild", "category": "skin"}},
    {"name": "burning_eyes", "attrs": {"indicates": "pitta", "severity": "mild", "category": "physical"}},
    {"name": "early_graying", "attrs": {"indicates": "pitta", "severity": "mild", "category": "physical"}},
    {"name": "hot_flashes", "attrs": {"indicates": "pitta", "severity": "moderate", "category": "physical"}},
    {"name": "ulcers", "attrs": {"indicates": "pitta", "severity": "severe", "category": "digestive"}},
    {"name": "jealousy", "attrs": {"indicates": "pitta", "severity": "mild", "category": "mental"}},
    {"name": "competitiveness", "attrs": {"indicates": "pitta", "severity": "mild", "category": "mental"}},
    {"name": "sensitivity_to_heat", "attrs": {"indicates": "pitta", "severity": "mild", "category": "physical"}},

    # Kapha imbalance symptoms
    {"name": "lethargy", "attrs": {"indicates": "kapha", "severity": "moderate", "category": "energy"}},
    {"name": "weight_gain", "attrs": {"indicates": "kapha", "severity": "moderate", "category": "physical"}},
    {"name": "congestion", "attrs": {"indicates": "kapha", "severity": "moderate", "category": "respiratory"}},
    {"name": "depression", "attrs": {"indicates": "kapha", "severity": "moderate", "category": "mental"}},
    {"name": "attachment", "attrs": {"indicates": "kapha", "severity": "mild", "category": "mental"}},
    {"name": "oversleeping", "attrs": {"indicates": "kapha", "severity": "mild", "category": "sleep"}},
    {"name": "slow_digestion", "attrs": {"indicates": "kapha", "severity": "mild", "category": "digestive"}},
    {"name": "water_retention", "attrs": {"indicates": "kapha", "severity": "mild", "category": "physical"}},
    {"name": "excess_mucus", "attrs": {"indicates": "kapha", "severity": "mild", "category": "respiratory"}},
    {"name": "heaviness", "attrs": {"indicates": "kapha", "severity": "moderate", "category": "physical"}},
    {"name": "procrastination", "attrs": {"indicates": "kapha", "severity": "mild", "category": "mental"}},
    {"name": "resistance_to_change", "attrs": {"indicates": "kapha", "severity": "mild", "category": "mental"}},
    {"name": "oily_skin", "attrs": {"indicates": "kapha", "severity": "mild", "category": "skin"}},
    {"name": "sluggishness", "attrs": {"indicates": "kapha", "severity": "moderate", "category": "energy"}},
    {"name": "brain_fog", "attrs": {"indicates": "kapha", "severity": "moderate", "category": "mental"}},
    {"name": "lack_motivation", "attrs": {"indicates": "kapha", "severity": "moderate", "category": "mental"}},
    {"name": "stubbornness", "attrs": {"indicates": "kapha", "severity": "mild", "category": "mental"}},
    {"name": "possessiveness", "attrs": {"indicates": "kapha", "severity": "mild", "category": "mental"}},
    {"name": "allergies", "attrs": {"indicates": "kapha", "severity": "moderate", "category": "respiratory"}},
    {"name": "sinus_issues", "attrs": {"indicates": "kapha", "severity": "moderate", "category": "respiratory"}},
]


# =============================================================================
# POPULATION FUNCTIONS
# =============================================================================

async def clear_graph() -> None:
    """Clear existing graph data."""
    await dbexec("DELETE FROM ay_edges")
    await dbexec("DELETE FROM ay_nodes")
    LOGGER.info("[PopulateGraph] Cleared existing graph data")


async def insert_node(kind: str, name: str, attrs: Dict[str, Any]) -> int:
    """Insert a node and return its ID."""
    result = await dbfetch(
        """
        INSERT INTO ay_nodes (kind, name, attrs)
        VALUES ($1, $2, $3::jsonb)
        ON CONFLICT (kind, name) DO UPDATE SET attrs = EXCLUDED.attrs
        RETURNING id
        """,
        kind,
        name,
        json.dumps(attrs, ensure_ascii=False),
        one=True,
    )
    return result["id"] if result else 0


async def insert_edge(src_id: int, dst_id: int, rel: str, weight: float = 1.0) -> None:
    """Insert an edge."""
    await dbexec(
        """
        INSERT INTO ay_edges (src, dst, rel, weight)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT DO NOTHING
        """,
        src_id,
        dst_id,
        rel,
        weight,
    )


async def populate_nodes() -> Dict[str, Dict[str, int]]:
    """Populate all nodes and return mapping of kind -> name -> id."""
    node_map: Dict[str, Dict[str, int]] = {
        "dosha": {},
        "quality": {},
        "season": {},
        "time_window": {},
        "food": {},
        "practice": {},
        "symptom": {},
    }

    # Doshas
    for d in DOSHAS:
        node_id = await insert_node("dosha", d["name"], d["attrs"])
        node_map["dosha"][d["name"]] = node_id

    # Qualities
    for q in QUALITIES:
        node_id = await insert_node("quality", q["name"], q["attrs"])
        node_map["quality"][q["name"]] = node_id

    # Seasons
    for s in SEASONS:
        node_id = await insert_node("season", s["name"], s["attrs"])
        node_map["season"][s["name"]] = node_id

    # Time windows
    for t in TIME_WINDOWS:
        node_id = await insert_node("time_window", t["name"], t["attrs"])
        node_map["time_window"][t["name"]] = node_id

    # Foods
    for f in FOODS:
        node_id = await insert_node("food", f["name"], f["attrs"])
        node_map["food"][f["name"]] = node_id

    # Practices
    for p in PRACTICES:
        node_id = await insert_node("practice", p["name"], p["attrs"])
        node_map["practice"][p["name"]] = node_id

    # Symptoms
    for s in SYMPTOMS:
        node_id = await insert_node("symptom", s["name"], s["attrs"])
        node_map["symptom"][s["name"]] = node_id

    return node_map


async def populate_edges(node_map: Dict[str, Dict[str, int]]) -> int:
    """Populate all edges. Returns edge count."""
    edge_count = 0

    # Food → Dosha edges (PACIFIES, AGGRAVATES)
    for f in FOODS:
        food_id = node_map["food"].get(f["name"])
        if not food_id:
            continue

        attrs = f["attrs"]
        for dosha in attrs.get("pacifies", []):
            dosha_id = node_map["dosha"].get(dosha)
            if dosha_id:
                await insert_edge(food_id, dosha_id, "PACIFIES", 0.8)
                edge_count += 1

        for dosha in attrs.get("aggravates", []):
            dosha_id = node_map["dosha"].get(dosha)
            if dosha_id:
                await insert_edge(food_id, dosha_id, "AGGRAVATES", 0.7)
                edge_count += 1

    # Practice → Dosha edges
    for p in PRACTICES:
        practice_id = node_map["practice"].get(p["name"])
        if not practice_id:
            continue

        attrs = p["attrs"]
        for dosha in attrs.get("pacifies", []):
            dosha_id = node_map["dosha"].get(dosha)
            if dosha_id:
                await insert_edge(practice_id, dosha_id, "PACIFIES", 0.85)
                edge_count += 1

        # Practice → Time window
        practice_time = attrs.get("time")
        if practice_time and practice_time != "any":
            time_id = node_map["time_window"].get(practice_time)
            if time_id:
                await insert_edge(practice_id, time_id, "OPTIMAL_TIME", 0.9)
                edge_count += 1

    # Symptom → Dosha edges
    for s in SYMPTOMS:
        symptom_id = node_map["symptom"].get(s["name"])
        if not symptom_id:
            continue

        dosha = s["attrs"].get("indicates")
        if dosha:
            dosha_id = node_map["dosha"].get(dosha)
            if dosha_id:
                await insert_edge(symptom_id, dosha_id, "INDICATES", 0.8)
                edge_count += 1

    # Season → Dosha edges (AMPLIFIES)
    for s in SEASONS:
        season_id = node_map["season"].get(s["name"])
        if not season_id:
            continue

        dosha = s["attrs"].get("dominant_dosha")
        if dosha:
            dosha_id = node_map["dosha"].get(dosha)
            if dosha_id:
                amp = s["attrs"].get("amplification", 1.0)
                await insert_edge(season_id, dosha_id, "AMPLIFIES", amp)
                edge_count += 1

    # Time window → Dosha edges
    for t in TIME_WINDOWS:
        time_id = node_map["time_window"].get(t["name"])
        if not time_id:
            continue

        dosha = t["attrs"].get("dominant_dosha")
        if dosha:
            dosha_id = node_map["dosha"].get(dosha)
            if dosha_id:
                await insert_edge(time_id, dosha_id, "DOMINANT_DURING", 0.7)
                edge_count += 1

    # Quality → Dosha edges
    for q in QUALITIES:
        quality_id = node_map["quality"].get(q["name"])
        if not quality_id:
            continue

        effect = q["attrs"].get("effect", "")
        if "aggravates_" in effect:
            dosha = effect.replace("aggravates_", "")
            dosha_id = node_map["dosha"].get(dosha)
            if dosha_id:
                await insert_edge(quality_id, dosha_id, "AGGRAVATES", 0.6)
                edge_count += 1
        elif "reduces_" in effect:
            dosha = effect.replace("reduces_", "")
            dosha_id = node_map["dosha"].get(dosha)
            if dosha_id:
                await insert_edge(quality_id, dosha_id, "REDUCES", 0.6)
                edge_count += 1

    return edge_count


async def run_population(clear_first: bool = True) -> Dict[str, Any]:
    """Main population function."""
    if clear_first:
        await clear_graph()

    node_map = await populate_nodes()

    node_counts = {kind: len(names) for kind, names in node_map.items()}
    total_nodes = sum(node_counts.values())

    edge_count = await populate_edges(node_map)

    LOGGER.info(
        "[PopulateGraph] Complete: %s nodes, %s edges",
        total_nodes,
        edge_count,
    )

    return {
        "status": "success",
        "node_counts": node_counts,
        "total_nodes": total_nodes,
        "edge_count": edge_count,
    }


async def main() -> None:
    """CLI entry point."""
    result = await run_population()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
