"""
Expand the Ayurvedic Knowledge Graph
------------------------------------
Phase A: Add herbs (dravya), rasayanas, and additional foods
Phase B: Add cause-effect relationships (behaviors → symptoms)
Phase C: Add yoga asanas with dosha effects
Phase E: Add contraindications

Uses LLM validation against classical Ayurvedic texts and yoga scriptures.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import asyncpg
from openai import AsyncOpenAI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Output directory for validated data
OUTPUT_DIR = Path(__file__).parent / "validated"
OUTPUT_DIR.mkdir(exist_ok=True)

# OpenAI client
client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


# =============================================================================
# SEED DATA
# =============================================================================

# Common Ayurvedic herbs (dravya) - Extended from Dravyaguna texts
HERBS = [
    # Original 40 herbs
    "ashwagandha", "brahmi", "tulsi", "triphala", "shatavari",
    "guduchi", "neem", "turmeric", "amalaki", "haritaki",
    "bibhitaki", "guggulu", "shilajit", "arjuna", "bala",
    "vidari", "punarnava", "manjistha", "kutki", "pippali",
    "trikatu", "chitrak", "vacha", "jatamansi", "shankhpushpi",
    "gokshura", "kapikacchu", "yashtimadhu", "musta", "haridra",
    "ela", "tvak", "lavanga", "jeeraka", "dhanyaka",
    "methi", "ajwain", "saunf", "hing", "kalaunji",
    # Additional herbs from Dravyaguna Vijnana
    "bhringaraj", "kumari", "eranda", "devadaru", "nagakesara",
    "bakuchi", "apamarga", "katuki", "patha", "kantakari",
    "vasa", "sariva", "ushira", "chandana", "agaru",
    "karpura", "tagara", "priyangu", "lodhra", "dhataki",
    "nagbala", "atibala", "vidarikanda", "ashoka", "daruharidra",
    "chirata", "nishoth", "trivrit", "danti", "jaiphal",
    "javitri", "keshar", "tagar", "pushkarmool", "rasna",
    "nirgundi", "agnimantha", "bilva", "gambhari", "patala",
    "shyonaka", "gmelina", "brihati", "kashmari", "shalaparni",
    "prishnaparni", "mudgaparni", "mashaparni", "jivanti", "kakoli",
]

# Rasayanas (rejuvenatives)
RASAYANAS = [
    "chyawanprash", "brahma_rasayana", "amalaki_rasayana",
    "ashwagandha_lehya", "shatavari_kalpa", "pippali_rasayana",
    "abhaya_amalaki", "agastya_haritaki", "vasant_kusumakar",
    "makaradhwaj", "swarna_bhasma", "loha_bhasma",
]

# Additional foods not in original list
ADDITIONAL_FOODS = [
    "dates", "figs", "pomegranate", "grapes", "coconut_water",
    "buttermilk", "lassi", "jaggery", "raw_honey", "sesame_seeds",
    "flax_seeds", "chia_seeds", "pumpkin_seeds", "sunflower_seeds",
    "almonds", "cashews", "walnuts", "pistachios", "raisins",
    "mung_dal", "toor_dal", "masoor_dal", "chana_dal", "urad_dal",
    "basmati_rice", "red_rice", "amaranth", "ragi", "jowar",
    "bajra", "buckwheat", "quinoa", "barley_water", "rice_water",
]

# Behaviors that affect doshas (for cause-effect edges)
BEHAVIORS = [
    # Vata-aggravating behaviors
    {"name": "late_night_sleep", "aggravates": "vata", "category": "sleep"},
    {"name": "irregular_meals", "aggravates": "vata", "category": "eating"},
    {"name": "excessive_travel", "aggravates": "vata", "category": "lifestyle"},
    {"name": "cold_exposure", "aggravates": "vata", "category": "environment"},
    {"name": "excessive_talking", "aggravates": "vata", "category": "activity"},
    {"name": "skipping_meals", "aggravates": "vata", "category": "eating"},
    {"name": "excessive_fasting", "aggravates": "vata", "category": "eating"},
    {"name": "excessive_exercise", "aggravates": "vata", "category": "activity"},
    {"name": "suppressing_urges", "aggravates": "vata", "category": "habits"},
    {"name": "excessive_screen_time", "aggravates": "vata", "category": "modern"},

    # Pitta-aggravating behaviors
    {"name": "eating_when_angry", "aggravates": "pitta", "category": "eating"},
    {"name": "excessive_sun_exposure", "aggravates": "pitta", "category": "environment"},
    {"name": "competitive_activities", "aggravates": "pitta", "category": "activity"},
    {"name": "spicy_food_excess", "aggravates": "pitta", "category": "eating"},
    {"name": "alcohol_consumption", "aggravates": "pitta", "category": "substance"},
    {"name": "working_through_lunch", "aggravates": "pitta", "category": "work"},
    {"name": "intense_arguments", "aggravates": "pitta", "category": "emotional"},
    {"name": "perfectionism", "aggravates": "pitta", "category": "mental"},
    {"name": "overworking", "aggravates": "pitta", "category": "work"},
    {"name": "hot_environment", "aggravates": "pitta", "category": "environment"},

    # Kapha-aggravating behaviors
    {"name": "daytime_sleeping", "aggravates": "kapha", "category": "sleep"},
    {"name": "overeating", "aggravates": "kapha", "category": "eating"},
    {"name": "sedentary_lifestyle", "aggravates": "kapha", "category": "lifestyle"},
    {"name": "excessive_sweets", "aggravates": "kapha", "category": "eating"},
    {"name": "cold_damp_environment", "aggravates": "kapha", "category": "environment"},
    {"name": "lack_of_exercise", "aggravates": "kapha", "category": "lifestyle"},
    {"name": "emotional_eating", "aggravates": "kapha", "category": "eating"},
    {"name": "excessive_dairy", "aggravates": "kapha", "category": "eating"},
    {"name": "sleeping_after_meals", "aggravates": "kapha", "category": "sleep"},
    {"name": "avoiding_change", "aggravates": "kapha", "category": "mental"},
]

# Contraindications (food/herb combinations to avoid)
CONTRAINDICATIONS = [
    {"item1": "honey", "item2": "ghee_equal", "reason": "Creates ama (toxins) when combined in equal quantities"},
    {"item1": "honey", "item2": "heat", "reason": "Heated honey becomes toxic according to Ayurveda"},
    {"item1": "milk", "item2": "fish", "reason": "Viruddha ahara - incompatible combination"},
    {"item1": "milk", "item2": "sour_fruits", "reason": "Causes curdling and digestive issues"},
    {"item1": "milk", "item2": "salt", "reason": "Incompatible - affects skin health"},
    {"item1": "yogurt", "item2": "night_time", "reason": "Heavy to digest at night, increases kapha"},
    {"item1": "cold_water", "item2": "meals", "reason": "Dampens digestive fire (agni)"},
    {"item1": "fruit", "item2": "meals", "reason": "Fruits should be eaten alone for proper digestion"},
    {"item1": "melon", "item2": "any_food", "reason": "Melons should always be eaten alone"},
    {"item1": "banana", "item2": "milk", "reason": "Heavy combination, clogs channels"},
]

# Yoga Asanas (poses) with their primary dosha effects
YOGA_ASANAS = [
    # Vata-pacifying asanas (grounding, stable, slow)
    {"name": "tadasana", "category": "standing", "pacifies": "vata", "level": "beginner"},
    {"name": "vrikshasana", "category": "standing", "pacifies": "vata", "level": "beginner"},
    {"name": "uttanasana", "category": "forward_bend", "pacifies": "vata", "level": "beginner"},
    {"name": "paschimottanasana", "category": "forward_bend", "pacifies": "vata", "level": "beginner"},
    {"name": "balasana", "category": "restorative", "pacifies": "vata", "level": "beginner"},
    {"name": "supta_baddha_konasana", "category": "restorative", "pacifies": "vata", "level": "beginner"},
    {"name": "viparita_karani", "category": "inversion", "pacifies": "vata", "level": "beginner"},
    {"name": "shavasana", "category": "restorative", "pacifies": "vata", "level": "beginner"},
    {"name": "apanasana", "category": "supine", "pacifies": "vata", "level": "beginner"},
    {"name": "supta_padangusthasana", "category": "supine", "pacifies": "vata", "level": "intermediate"},

    # Pitta-pacifying asanas (cooling, heart-opening, gentle)
    {"name": "ardha_chandrasana", "category": "standing", "pacifies": "pitta", "level": "intermediate"},
    {"name": "trikonasana", "category": "standing", "pacifies": "pitta", "level": "beginner"},
    {"name": "bhujangasana", "category": "backbend", "pacifies": "pitta", "level": "beginner"},
    {"name": "matsyasana", "category": "backbend", "pacifies": "pitta", "level": "intermediate"},
    {"name": "setu_bandhasana", "category": "backbend", "pacifies": "pitta", "level": "beginner"},
    {"name": "janu_sirsasana", "category": "forward_bend", "pacifies": "pitta", "level": "beginner"},
    {"name": "supta_virasana", "category": "restorative", "pacifies": "pitta", "level": "intermediate"},
    {"name": "sitali_pranayama", "category": "pranayama", "pacifies": "pitta", "level": "beginner"},
    {"name": "chandra_bhedana", "category": "pranayama", "pacifies": "pitta", "level": "intermediate"},
    {"name": "supported_shoulderstand", "category": "inversion", "pacifies": "pitta", "level": "intermediate"},

    # Kapha-pacifying asanas (energizing, heating, stimulating)
    {"name": "surya_namaskar", "category": "sequence", "pacifies": "kapha", "level": "beginner"},
    {"name": "virabhadrasana_i", "category": "standing", "pacifies": "kapha", "level": "beginner"},
    {"name": "virabhadrasana_ii", "category": "standing", "pacifies": "kapha", "level": "beginner"},
    {"name": "virabhadrasana_iii", "category": "standing", "pacifies": "kapha", "level": "intermediate"},
    {"name": "utkatasana", "category": "standing", "pacifies": "kapha", "level": "beginner"},
    {"name": "navasana", "category": "core", "pacifies": "kapha", "level": "intermediate"},
    {"name": "ustrasana", "category": "backbend", "pacifies": "kapha", "level": "intermediate"},
    {"name": "dhanurasana", "category": "backbend", "pacifies": "kapha", "level": "intermediate"},
    {"name": "kapalbhati", "category": "pranayama", "pacifies": "kapha", "level": "beginner"},
    {"name": "bhastrika", "category": "pranayama", "pacifies": "kapha", "level": "intermediate"},
    {"name": "simhasana", "category": "seated", "pacifies": "kapha", "level": "beginner"},
    {"name": "mayurasana", "category": "arm_balance", "pacifies": "kapha", "level": "advanced"},

    # Tridosha-balancing asanas (good for all constitutions)
    {"name": "sukhasana", "category": "seated", "pacifies": "tridosha", "level": "beginner"},
    {"name": "padmasana", "category": "seated", "pacifies": "tridosha", "level": "intermediate"},
    {"name": "vajrasana", "category": "seated", "pacifies": "tridosha", "level": "beginner"},
    {"name": "nadi_shodhana", "category": "pranayama", "pacifies": "tridosha", "level": "beginner"},
    {"name": "ujjayi_pranayama", "category": "pranayama", "pacifies": "tridosha", "level": "beginner"},
    {"name": "adho_mukha_svanasana", "category": "standing", "pacifies": "tridosha", "level": "beginner"},
    {"name": "marjaryasana_bitilasana", "category": "kneeling", "pacifies": "tridosha", "level": "beginner"},
    {"name": "ardha_matsyendrasana", "category": "twist", "pacifies": "tridosha", "level": "intermediate"},
    {"name": "marichyasana", "category": "twist", "pacifies": "tridosha", "level": "intermediate"},
    {"name": "gomukhasana", "category": "seated", "pacifies": "tridosha", "level": "intermediate"},
]


# =============================================================================
# LLM VALIDATION PROMPTS
# =============================================================================

HERB_VALIDATION_PROMPT = """You are an Ayurvedic scholar validating herb (dravya) data against classical texts.

Validate this herb and provide accurate Ayurvedic properties:
Herb: {name}

Provide a JSON response with:
{{
    "validated": true/false,
    "name_sanskrit": "Sanskrit name in IAST transliteration",
    "validated_properties": {{
        "rasa": "primary taste (madhura/amla/lavana/katu/tikta/kashaya)",
        "virya": "potency (ushna/shita)",
        "vipaka": "post-digestive effect (madhura/amla/katu)",
        "guna": ["qualities like laghu, guru, snigdha, ruksha"],
        "prabhava": "special action if any",
        "part_used": "root/leaf/whole plant/etc",
        "dosage_form": "churna/kwatha/etc"
    }},
    "dosha_effects": {{
        "pacifies": ["list of doshas it pacifies"],
        "aggravates": ["list of doshas it may aggravate in excess"]
    }},
    "therapeutic_uses": ["list of 3-5 main therapeutic uses"],
    "citations": [
        {{
            "source": "charaka_samhita/ashtanga_hridaya/sushruta_samhita/bhavaprakasha",
            "chapter": "relevant section",
            "context": "brief context of reference"
        }}
    ],
    "confidence": 0.0-1.0,
    "notes": "any important notes or cautions"
}}

Be accurate and cite classical sources. If uncertain, set confidence lower."""


RASAYANA_VALIDATION_PROMPT = """You are an Ayurvedic scholar validating rasayana (rejuvenative) formulations.

Validate this rasayana and provide accurate Ayurvedic properties:
Rasayana: {name}

Provide a JSON response with:
{{
    "validated": true/false,
    "name_sanskrit": "Sanskrit name",
    "validated_properties": {{
        "type": "ajasrika/kamya/naimittika rasayana",
        "primary_action": "main therapeutic action",
        "key_ingredients": ["main ingredients"],
        "anupana": "vehicle/adjuvant to take with"
    }},
    "dosha_effects": {{
        "pacifies": ["doshas it balances"],
        "best_for": "constitution type most suited"
    }},
    "benefits": ["list of 3-5 main benefits"],
    "indications": ["conditions it helps"],
    "contraindications": ["when to avoid"],
    "citations": [
        {{
            "source": "charaka_samhita/ashtanga_hridaya",
            "chapter": "rasayana section reference",
            "context": "brief context"
        }}
    ],
    "confidence": 0.0-1.0,
    "traditional_usage": "traditional way of taking"
}}

Focus on classical references for rasayanas."""


BEHAVIOR_VALIDATION_PROMPT = """You are an Ayurvedic scholar validating lifestyle factors (nidana) and their effects on doshas.

Validate this behavior and its dosha effects:
Behavior: {name}
Claimed effect: Aggravates {dosha}
Category: {category}

Provide a JSON response with:
{{
    "validated": true/false,
    "name_sanskrit": "Sanskrit term if applicable",
    "validated_effects": {{
        "aggravates": ["doshas this behavior aggravates"],
        "pacifies": ["doshas this behavior may pacify, if any"],
        "mechanism": "Ayurvedic explanation of how it affects doshas"
    }},
    "symptoms_caused": ["symptoms this behavior can lead to"],
    "related_concepts": {{
        "nidana": "etiological category",
        "samprapti": "pathogenesis pathway"
    }},
    "citations": [
        {{
            "source": "charaka_samhita/ashtanga_hridaya",
            "chapter": "nidana or sutra sthana reference",
            "context": "relevant teaching"
        }}
    ],
    "confidence": 0.0-1.0,
    "recommendations": "what to do instead"
}}

Ground the validation in classical nidana (etiology) teachings."""


ASANA_VALIDATION_PROMPT = """You are a yoga scholar validating asana (yoga pose) data against classical texts and Ayurvedic principles.

Validate this yoga asana and provide accurate properties:
Asana: {name}
Category: {category}
Claimed dosha effect: Pacifies {pacifies}
Level: {level}

Provide a JSON response with:
{{
    "validated": true/false,
    "name_sanskrit": "Full Sanskrit name with IAST transliteration",
    "english_name": "Common English translation",
    "validated_properties": {{
        "category": "standing/seated/supine/prone/inversion/backbend/forward_bend/twist/arm_balance/core/restorative/pranayama/sequence",
        "level": "beginner/intermediate/advanced",
        "hold_time_seconds": "typical hold time range",
        "breath_pattern": "inhale/exhale synchronization"
    }},
    "dosha_effects": {{
        "pacifies": ["primary doshas this asana balances"],
        "may_aggravate": ["doshas to be cautious about if any"],
        "mechanism": "Ayurvedic explanation of how it affects doshas/prana"
    }},
    "benefits": ["list of 3-5 main physical/mental benefits"],
    "contraindications": ["conditions/situations to avoid this asana"],
    "preparatory_poses": ["asanas to practice before this one"],
    "follow_up_poses": ["asanas that naturally follow"],
    "chakra_activation": ["primary chakras affected"],
    "citations": [
        {{
            "source": "hatha_yoga_pradipika/gheranda_samhita/yoga_sutras/ayurvedic_text",
            "chapter": "relevant section",
            "context": "brief reference"
        }}
    ],
    "confidence": 0.0-1.0,
    "modifications": "common modifications for beginners or limitations"
}}

Ground the validation in classical yoga texts (Hatha Yoga Pradipika, Gheranda Samhita) and Ayurvedic principles."""


# =============================================================================
# VALIDATION FUNCTIONS
# =============================================================================

async def validate_herb(name: str) -> dict[str, Any]:
    """Validate a single herb using LLM."""
    prompt = HERB_VALIDATION_PROMPT.format(name=name)

    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=1000,
    )

    content = response.choices[0].message.content or "{}"

    # Extract JSON from response
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0]
    elif "```" in content:
        content = content.split("```")[1].split("```")[0]

    try:
        result = json.loads(content.strip())
        result["original_name"] = name  # Preserve the original name
        return result
    except json.JSONDecodeError:
        logger.warning(f"Failed to parse herb validation for {name}")
        return {"validated": False, "original_name": name}


async def validate_rasayana(name: str) -> dict[str, Any]:
    """Validate a single rasayana using LLM."""
    prompt = RASAYANA_VALIDATION_PROMPT.format(name=name)

    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=1000,
    )

    content = response.choices[0].message.content or "{}"

    if "```json" in content:
        content = content.split("```json")[1].split("```")[0]
    elif "```" in content:
        content = content.split("```")[1].split("```")[0]

    try:
        result = json.loads(content.strip())
        result["original_name"] = name  # Preserve the original name
        return result
    except json.JSONDecodeError:
        logger.warning(f"Failed to parse rasayana validation for {name}")
        return {"validated": False, "original_name": name}


async def validate_behavior(behavior: dict[str, str]) -> dict[str, Any]:
    """Validate a behavior and its dosha effects using LLM."""
    prompt = BEHAVIOR_VALIDATION_PROMPT.format(
        name=behavior["name"],
        dosha=behavior["aggravates"],
        category=behavior["category"],
    )

    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=800,
    )

    content = response.choices[0].message.content or "{}"

    if "```json" in content:
        content = content.split("```json")[1].split("```")[0]
    elif "```" in content:
        content = content.split("```")[1].split("```")[0]

    try:
        result = json.loads(content.strip())
        result["original"] = behavior
        return result
    except json.JSONDecodeError:
        logger.warning(f"Failed to parse behavior validation for {behavior['name']}")
        return {"validated": False, "original": behavior}


async def validate_asana(asana: dict[str, str]) -> dict[str, Any]:
    """Validate a yoga asana using LLM."""
    prompt = ASANA_VALIDATION_PROMPT.format(
        name=asana["name"],
        category=asana["category"],
        pacifies=asana["pacifies"],
        level=asana["level"],
    )

    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=1200,
    )

    content = response.choices[0].message.content or "{}"

    if "```json" in content:
        content = content.split("```json")[1].split("```")[0]
    elif "```" in content:
        content = content.split("```")[1].split("```")[0]

    try:
        result = json.loads(content.strip())
        result["original"] = asana
        return result
    except json.JSONDecodeError:
        logger.warning(f"Failed to parse asana validation for {asana['name']}")
        return {"validated": False, "original": asana}


async def validate_batch(items: list, validator_func, batch_size: int = 5) -> list:
    """Validate items in batches with rate limiting."""
    results = []

    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        logger.info(f"Processing batch {i // batch_size + 1}/{(len(items) + batch_size - 1) // batch_size}")

        if isinstance(batch[0], dict):
            tasks = [validator_func(item) for item in batch]
        else:
            tasks = [validator_func(item) for item in batch]

        batch_results = await asyncio.gather(*tasks, return_exceptions=True)

        for j, result in enumerate(batch_results):
            if isinstance(result, Exception):
                logger.error(f"Validation failed: {result}")
                if isinstance(batch[j], dict):
                    results.append({"validated": False, "original": batch[j]})
                else:
                    results.append({"validated": False, "name": batch[j]})
            else:
                results.append(result)

        # Rate limiting
        if i + batch_size < len(items):
            await asyncio.sleep(1)

    return results


# =============================================================================
# DATABASE POPULATION
# =============================================================================

async def populate_herbs(conn: asyncpg.Connection, validated_herbs: list) -> tuple[int, int]:
    """Populate herbs into the knowledge graph."""
    nodes_created = 0
    edges_created = 0

    for herb in validated_herbs:
        if not herb.get("validated"):
            continue

        name = herb.get("original_name", "unknown")

        # Build attrs
        props = herb.get("validated_properties", {})
        attrs = {
            "rasa": props.get("rasa"),
            "virya": props.get("virya"),
            "vipaka": props.get("vipaka"),
            "guna": props.get("guna", []),
            "prabhava": props.get("prabhava"),
            "part_used": props.get("part_used"),
            "dosage_form": props.get("dosage_form"),
            "therapeutic_uses": herb.get("therapeutic_uses", []),
            "notes": herb.get("notes"),
        }

        citations = herb.get("citations", [])
        confidence = herb.get("confidence", 0.8)

        # Insert node
        try:
            node_id = await conn.fetchval(
                """
                INSERT INTO ay_nodes (kind, name, name_sanskrit, display_name, attrs, citations, confidence, extraction_method, validated_at, validated_by)
                VALUES ('herb', $1, $2, $3, $4, $5, $6, 'llm_validated', NOW(), 'llm:gpt-4o')
                ON CONFLICT (kind, name) DO UPDATE SET
                    attrs = EXCLUDED.attrs,
                    citations = EXCLUDED.citations,
                    confidence = EXCLUDED.confidence,
                    validated_at = NOW()
                RETURNING id
                """,
                name.lower().replace(" ", "_"),
                herb.get("name_sanskrit"),
                name.replace("_", " ").title(),
                json.dumps(attrs),
                json.dumps(citations),
                confidence,
            )
            nodes_created += 1

            # Create edges for dosha effects
            dosha_effects = herb.get("dosha_effects", {})

            for dosha in dosha_effects.get("pacifies", []):
                dosha_id = await conn.fetchval(
                    "SELECT id FROM ay_nodes WHERE kind = 'dosha' AND name = $1",
                    dosha.lower(),
                )
                if dosha_id:
                    await conn.execute(
                        """
                        INSERT INTO ay_edges (src, dst, rel, weight, citations, confidence)
                        VALUES ($1, $2, 'PACIFIES', 0.85, $3, $4)
                        ON CONFLICT DO NOTHING
                        """,
                        node_id, dosha_id, json.dumps(citations[:1]), confidence,
                    )
                    edges_created += 1

            for dosha in dosha_effects.get("aggravates", []):
                dosha_id = await conn.fetchval(
                    "SELECT id FROM ay_nodes WHERE kind = 'dosha' AND name = $1",
                    dosha.lower(),
                )
                if dosha_id:
                    await conn.execute(
                        """
                        INSERT INTO ay_edges (src, dst, rel, weight, citations, confidence)
                        VALUES ($1, $2, 'AGGRAVATES', 0.7, $3, $4)
                        ON CONFLICT DO NOTHING
                        """,
                        node_id, dosha_id, json.dumps(citations[:1]), confidence,
                    )
                    edges_created += 1

        except Exception as e:
            logger.warning(f"Failed to insert herb {name}: {e}")

    return nodes_created, edges_created


async def populate_rasayanas(conn: asyncpg.Connection, validated_rasayanas: list) -> tuple[int, int]:
    """Populate rasayanas into the knowledge graph."""
    nodes_created = 0
    edges_created = 0

    for rasayana in validated_rasayanas:
        if not rasayana.get("validated"):
            continue

        name = rasayana.get("original_name", "unknown")

        props = rasayana.get("validated_properties", {})
        attrs = {
            "type": props.get("type"),
            "primary_action": props.get("primary_action"),
            "key_ingredients": props.get("key_ingredients", []),
            "anupana": props.get("anupana"),
            "benefits": rasayana.get("benefits", []),
            "indications": rasayana.get("indications", []),
            "contraindications": rasayana.get("contraindications", []),
            "traditional_usage": rasayana.get("traditional_usage"),
        }

        citations = rasayana.get("citations", [])
        confidence = rasayana.get("confidence", 0.8)

        try:
            node_id = await conn.fetchval(
                """
                INSERT INTO ay_nodes (kind, name, name_sanskrit, display_name, attrs, citations, confidence, extraction_method, validated_at, validated_by)
                VALUES ('rasayana', $1, $2, $3, $4, $5, $6, 'llm_validated', NOW(), 'llm:gpt-4o')
                ON CONFLICT (kind, name) DO UPDATE SET
                    attrs = EXCLUDED.attrs,
                    citations = EXCLUDED.citations,
                    confidence = EXCLUDED.confidence,
                    validated_at = NOW()
                RETURNING id
                """,
                name.lower().replace(" ", "_"),
                rasayana.get("name_sanskrit"),
                name.replace("_", " ").title(),
                json.dumps(attrs),
                json.dumps(citations),
                confidence,
            )
            nodes_created += 1

            # Create edges for dosha effects
            dosha_effects = rasayana.get("dosha_effects", {})
            for dosha in dosha_effects.get("pacifies", []):
                dosha_id = await conn.fetchval(
                    "SELECT id FROM ay_nodes WHERE kind = 'dosha' AND name = $1",
                    dosha.lower(),
                )
                if dosha_id:
                    await conn.execute(
                        """
                        INSERT INTO ay_edges (src, dst, rel, weight, citations, confidence)
                        VALUES ($1, $2, 'PACIFIES', 0.9, $3, $4)
                        ON CONFLICT DO NOTHING
                        """,
                        node_id, dosha_id, json.dumps(citations[:1]), confidence,
                    )
                    edges_created += 1

        except Exception as e:
            logger.warning(f"Failed to insert rasayana {name}: {e}")

    return nodes_created, edges_created


async def populate_behaviors(conn: asyncpg.Connection, validated_behaviors: list) -> tuple[int, int]:
    """Populate behaviors and cause-effect edges."""
    nodes_created = 0
    edges_created = 0

    for behavior in validated_behaviors:
        if not behavior.get("validated"):
            continue

        original = behavior.get("original", {})
        name = original.get("name", "unknown")

        effects = behavior.get("validated_effects", {})
        attrs = {
            "category": original.get("category"),
            "mechanism": effects.get("mechanism"),
            "symptoms_caused": behavior.get("symptoms_caused", []),
            "nidana": behavior.get("related_concepts", {}).get("nidana"),
            "recommendations": behavior.get("recommendations"),
        }

        citations = behavior.get("citations", [])
        confidence = behavior.get("confidence", 0.7)

        try:
            node_id = await conn.fetchval(
                """
                INSERT INTO ay_nodes (kind, name, name_sanskrit, display_name, attrs, citations, confidence, extraction_method, validated_at, validated_by)
                VALUES ('behavior', $1, $2, $3, $4, $5, $6, 'llm_validated', NOW(), 'llm:gpt-4o')
                ON CONFLICT (kind, name) DO UPDATE SET
                    attrs = EXCLUDED.attrs,
                    citations = EXCLUDED.citations,
                    confidence = EXCLUDED.confidence,
                    validated_at = NOW()
                RETURNING id
                """,
                name.lower().replace(" ", "_"),
                behavior.get("name_sanskrit"),
                name.replace("_", " ").title(),
                json.dumps(attrs),
                json.dumps(citations),
                confidence,
            )
            nodes_created += 1

            # Create AGGRAVATES edges to doshas
            for dosha in effects.get("aggravates", []):
                dosha_id = await conn.fetchval(
                    "SELECT id FROM ay_nodes WHERE kind = 'dosha' AND name = $1",
                    dosha.lower(),
                )
                if dosha_id:
                    await conn.execute(
                        """
                        INSERT INTO ay_edges (src, dst, rel, weight, citations, confidence)
                        VALUES ($1, $2, 'AGGRAVATES', 0.8, $3, $4)
                        ON CONFLICT DO NOTHING
                        """,
                        node_id, dosha_id, json.dumps(citations[:1]), confidence,
                    )
                    edges_created += 1

            # Create CAUSES edges to symptoms
            for symptom in behavior.get("symptoms_caused", []):
                symptom_name = symptom.lower().replace(" ", "_")
                symptom_id = await conn.fetchval(
                    "SELECT id FROM ay_nodes WHERE kind = 'symptom' AND name ILIKE $1",
                    f"%{symptom_name}%",
                )
                if symptom_id:
                    await conn.execute(
                        """
                        INSERT INTO ay_edges (src, dst, rel, weight, citations, confidence)
                        VALUES ($1, $2, 'CAUSES', 0.75, $3, $4)
                        ON CONFLICT DO NOTHING
                        """,
                        node_id, symptom_id, json.dumps(citations[:1]), confidence,
                    )
                    edges_created += 1

        except Exception as e:
            logger.warning(f"Failed to insert behavior {name}: {e}")

    return nodes_created, edges_created


async def populate_contraindications(conn: asyncpg.Connection) -> int:
    """Populate contraindication edges."""
    edges_created = 0

    for contra in CONTRAINDICATIONS:
        # Find both items
        item1_id = await conn.fetchval(
            """
            SELECT id FROM ay_nodes
            WHERE (kind IN ('food', 'herb', 'rasayana'))
              AND name ILIKE $1
            LIMIT 1
            """,
            f"%{contra['item1']}%",
        )

        item2_id = await conn.fetchval(
            """
            SELECT id FROM ay_nodes
            WHERE (kind IN ('food', 'herb', 'rasayana', 'time_window', 'quality'))
              AND name ILIKE $1
            LIMIT 1
            """,
            f"%{contra['item2']}%",
        )

        if item1_id and item2_id:
            try:
                await conn.execute(
                    """
                    INSERT INTO ay_edges (src, dst, rel, weight, context, confidence)
                    VALUES ($1, $2, 'CONTRAINDICATED_WITH', 0.9, $3, 0.85)
                    ON CONFLICT DO NOTHING
                    """,
                    item1_id,
                    item2_id,
                    json.dumps({"reason": contra["reason"]}),
                )
                edges_created += 1
                logger.info(f"Added contraindication: {contra['item1']} + {contra['item2']}")
            except Exception as e:
                logger.warning(f"Failed to add contraindication: {e}")
        else:
            logger.debug(f"Could not find nodes for contraindication: {contra['item1']} + {contra['item2']}")

    return edges_created


async def populate_asanas(conn: asyncpg.Connection, validated_asanas: list) -> tuple[int, int]:
    """Populate yoga asanas into the knowledge graph."""
    nodes_created = 0
    edges_created = 0

    for asana in validated_asanas:
        if not asana.get("validated"):
            continue

        original = asana.get("original", {})
        name = original.get("name", "unknown")

        props = asana.get("validated_properties", {})
        dosha_effects = asana.get("dosha_effects", {})

        attrs = {
            "category": props.get("category") or original.get("category"),
            "level": props.get("level") or original.get("level"),
            "hold_time_seconds": props.get("hold_time_seconds"),
            "breath_pattern": props.get("breath_pattern"),
            "english_name": asana.get("english_name"),
            "benefits": asana.get("benefits", []),
            "contraindications": asana.get("contraindications", []),
            "preparatory_poses": asana.get("preparatory_poses", []),
            "follow_up_poses": asana.get("follow_up_poses", []),
            "chakra_activation": asana.get("chakra_activation", []),
            "mechanism": dosha_effects.get("mechanism"),
            "modifications": asana.get("modifications"),
        }

        citations = asana.get("citations", [])
        confidence = asana.get("confidence", 0.8)

        try:
            node_id = await conn.fetchval(
                """
                INSERT INTO ay_nodes (kind, name, name_sanskrit, display_name, attrs, citations, confidence, extraction_method, validated_at, validated_by)
                VALUES ('asana', $1, $2, $3, $4, $5, $6, 'llm_validated', NOW(), 'llm:gpt-4o')
                ON CONFLICT (kind, name) DO UPDATE SET
                    attrs = EXCLUDED.attrs,
                    citations = EXCLUDED.citations,
                    confidence = EXCLUDED.confidence,
                    validated_at = NOW()
                RETURNING id
                """,
                name.lower().replace(" ", "_"),
                asana.get("name_sanskrit"),
                asana.get("english_name") or name.replace("_", " ").title(),
                json.dumps(attrs),
                json.dumps(citations),
                confidence,
            )
            nodes_created += 1

            # Create PACIFIES edges to doshas
            pacifies_list = dosha_effects.get("pacifies", [])
            if not pacifies_list and original.get("pacifies"):
                # Fall back to original if LLM didn't return pacifies
                pacifies_list = [original["pacifies"]] if original["pacifies"] != "tridosha" else ["vata", "pitta", "kapha"]

            for dosha in pacifies_list:
                dosha_name = dosha.lower()
                if dosha_name == "tridosha":
                    # Tridosha means all three
                    for d in ["vata", "pitta", "kapha"]:
                        dosha_id = await conn.fetchval(
                            "SELECT id FROM ay_nodes WHERE kind = 'dosha' AND name = $1",
                            d,
                        )
                        if dosha_id:
                            await conn.execute(
                                """
                                INSERT INTO ay_edges (src, dst, rel, weight, citations, confidence)
                                VALUES ($1, $2, 'PACIFIES', 0.75, $3, $4)
                                ON CONFLICT DO NOTHING
                                """,
                                node_id, dosha_id, json.dumps(citations[:1]), confidence,
                            )
                            edges_created += 1
                else:
                    dosha_id = await conn.fetchval(
                        "SELECT id FROM ay_nodes WHERE kind = 'dosha' AND name = $1",
                        dosha_name,
                    )
                    if dosha_id:
                        await conn.execute(
                            """
                            INSERT INTO ay_edges (src, dst, rel, weight, citations, confidence)
                            VALUES ($1, $2, 'PACIFIES', 0.85, $3, $4)
                            ON CONFLICT DO NOTHING
                            """,
                            node_id, dosha_id, json.dumps(citations[:1]), confidence,
                        )
                        edges_created += 1

            # Create AGGRAVATES edges if any
            for dosha in dosha_effects.get("may_aggravate", []):
                dosha_id = await conn.fetchval(
                    "SELECT id FROM ay_nodes WHERE kind = 'dosha' AND name = $1",
                    dosha.lower(),
                )
                if dosha_id:
                    await conn.execute(
                        """
                        INSERT INTO ay_edges (src, dst, rel, weight, citations, confidence)
                        VALUES ($1, $2, 'AGGRAVATES', 0.6, $3, $4)
                        ON CONFLICT DO NOTHING
                        """,
                        node_id, dosha_id, json.dumps(citations[:1]), confidence,
                    )
                    edges_created += 1

        except Exception as e:
            logger.warning(f"Failed to insert asana {name}: {e}")

    return nodes_created, edges_created


# =============================================================================
# MAIN
# =============================================================================

async def main():
    """Run the knowledge graph expansion."""
    import sys

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL not set")
        sys.exit(1)

    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not set")
        sys.exit(1)

    print("=" * 60)
    print("Ayurvedic Knowledge Graph Expansion")
    print("=" * 60)

    # Phase A: Validate and populate herbs
    print("\n[Phase A.1] Validating herbs...")
    validated_herbs = await validate_batch(HERBS, validate_herb, batch_size=5)

    # Save validated herbs
    with open(OUTPUT_DIR / "herbs_validated.json", "w") as f:
        json.dump(validated_herbs, f, indent=2)
    print(f"  Validated {sum(1 for h in validated_herbs if h.get('validated'))} / {len(HERBS)} herbs")

    # Phase A.2: Validate rasayanas
    print("\n[Phase A.2] Validating rasayanas...")
    validated_rasayanas = await validate_batch(RASAYANAS, validate_rasayana, batch_size=3)

    with open(OUTPUT_DIR / "rasayanas_validated.json", "w") as f:
        json.dump(validated_rasayanas, f, indent=2)
    print(f"  Validated {sum(1 for r in validated_rasayanas if r.get('validated'))} / {len(RASAYANAS)} rasayanas")

    # Phase B: Validate behaviors (cause-effect)
    print("\n[Phase B] Validating behaviors (cause-effect)...")
    validated_behaviors = await validate_batch(BEHAVIORS, validate_behavior, batch_size=5)

    with open(OUTPUT_DIR / "behaviors_validated.json", "w") as f:
        json.dump(validated_behaviors, f, indent=2)
    print(f"  Validated {sum(1 for b in validated_behaviors if b.get('validated'))} / {len(BEHAVIORS)} behaviors")

    # Phase C: Validate yoga asanas
    print("\n[Phase C] Validating yoga asanas...")
    validated_asanas = await validate_batch(YOGA_ASANAS, validate_asana, batch_size=5)

    with open(OUTPUT_DIR / "asanas_validated.json", "w") as f:
        json.dump(validated_asanas, f, indent=2)
    print(f"  Validated {sum(1 for a in validated_asanas if a.get('validated'))} / {len(YOGA_ASANAS)} asanas")

    # Connect to database and populate
    print("\n[Database] Connecting and populating...")
    conn = await asyncpg.connect(database_url)

    try:
        # Populate herbs
        herb_nodes, herb_edges = await populate_herbs(conn, validated_herbs)
        print(f"  Herbs: {herb_nodes} nodes, {herb_edges} edges")

        # Populate rasayanas
        rasayana_nodes, rasayana_edges = await populate_rasayanas(conn, validated_rasayanas)
        print(f"  Rasayanas: {rasayana_nodes} nodes, {rasayana_edges} edges")

        # Populate behaviors
        behavior_nodes, behavior_edges = await populate_behaviors(conn, validated_behaviors)
        print(f"  Behaviors: {behavior_nodes} nodes, {behavior_edges} edges")

        # Populate asanas
        asana_nodes, asana_edges = await populate_asanas(conn, validated_asanas)
        print(f"  Asanas: {asana_nodes} nodes, {asana_edges} edges")

        # Phase E: Add contraindications
        print("\n[Phase E] Adding contraindications...")
        contra_edges = await populate_contraindications(conn)
        print(f"  Contraindications: {contra_edges} edges")

        # Get final stats
        stats = await conn.fetchrow(
            """
            SELECT
                (SELECT COUNT(*) FROM ay_nodes) as total_nodes,
                (SELECT COUNT(*) FROM ay_edges) as total_edges,
                (SELECT COUNT(*) FROM ay_nodes WHERE kind = 'herb') as herbs,
                (SELECT COUNT(*) FROM ay_nodes WHERE kind = 'rasayana') as rasayanas,
                (SELECT COUNT(*) FROM ay_nodes WHERE kind = 'behavior') as behaviors,
                (SELECT COUNT(*) FROM ay_nodes WHERE kind = 'asana') as asanas
            """
        )

        print("\n" + "=" * 60)
        print("FINAL KNOWLEDGE GRAPH STATS")
        print("=" * 60)
        print(f"Total nodes: {stats['total_nodes']}")
        print(f"Total edges: {stats['total_edges']}")
        print(f"  - Herbs: {stats['herbs']}")
        print(f"  - Rasayanas: {stats['rasayanas']}")
        print(f"  - Behaviors: {stats['behaviors']}")
        print(f"  - Asanas: {stats['asanas']}")
        print("=" * 60)

    finally:
        await conn.close()

    print("\nExpansion complete!")


if __name__ == "__main__":
    asyncio.run(main())
