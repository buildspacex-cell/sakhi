# Ayurvedic Knowledge Graph

> **Status**: Production-ready
> **Last Updated**: 2026-02-05
> **Total Nodes**: ~450+ | **Total Edges**: ~1000+
> **Note**: Run `expand_knowledge_graph.py` to populate all nodes

---

## Overview

Sakhi's Ayurvedic Knowledge Graph is a validated, citation-backed database of Ayurvedic knowledge extracted from classical texts. It powers personalized recommendations, causal reasoning, and pattern learning.

**Key Features:**
- LLM-validated data against classical Ayurvedic texts
- Sanskrit names with IAST transliteration
- Citations from Charaka Samhita, Ashtanga Hridaya, Sushruta Samhita, Bhavaprakasha
- Cause-effect relationships (behaviors → symptoms)
- Contraindication edges for safety
- Personal pattern learning integration

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     AYURVEDIC KNOWLEDGE GRAPH                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ┌─────────────┐         ┌─────────────┐         ┌─────────────┐      │
│   │   DOSHAS    │◄───────►│    FOODS    │◄───────►│    HERBS    │      │
│   │  (vata,     │ PACIFIES│  (100 items)│ PACIFIES│  (80 items) │      │
│   │   pitta,    │ AGGRAV. │             │ AGGRAV. │             │      │
│   │   kapha)    │         │             │         │             │      │
│   └──────┬──────┘         └─────────────┘         └─────────────┘      │
│          │                                                              │
│          │ INDICATES / PACIFIES                                         │
│          ▼                                                              │
│   ┌─────────────┐         ┌─────────────┐         ┌─────────────┐      │
│   │  SYMPTOMS   │◄────────│  BEHAVIORS  │         │  RASAYANAS  │      │
│   │  (60 items) │  CAUSES │  (29 items) │         │  (12 items) │      │
│   └─────────────┘         └──────┬──────┘         └─────────────┘      │
│                                  │                                      │
│                                  │ AGGRAVATES                           │
│                                  ▼                                      │
│   ┌─────────────┐         ┌─────────────┐         ┌─────────────┐      │
│   │   ASANAS    │◄───────►│  QUALITIES  │         │  SEASONS    │      │
│   │  (42 items) │ PACIFIES│  (20 items) │         │  (6 items)  │      │
│   └─────────────┘         └─────────────┘         └─────────────┘      │
│                                                                         │
│   ┌─────────────┐                                                       │
│   │  PRACTICES  │ (80 items - yoga, pranayama, routines)               │
│   └─────────────┘                                                       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Database Schema

### Tables

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `ay_nodes` | Knowledge graph nodes | kind, name, name_sanskrit, attrs, citations, confidence |
| `ay_edges` | Relationships between nodes | src, dst, rel, weight, context, citations |
| `ay_sources` | Registry of classical texts | code, title, sections, translation_used |
| `ay_validation_log` | LLM validation audit trail | node_id, status, llm_reasoning, confidence_score |

### Node Types (kinds)

| Kind | Count | Description | Example |
|------|-------|-------------|---------|
| `dosha` | 3 | Constitutional types | vata, pitta, kapha |
| `food` | 100 | Foods with Ayurvedic properties | ginger, milk, rice |
| `herb` | 80 | Medicinal herbs from Dravyaguna | ashwagandha, brahmi, bhringaraj |
| `asana` | 42 | Yoga poses with dosha effects | shavasana, surya_namaskar, trikonasana |
| `rasayana` | 12 | Rejuvenative formulations | chyawanprash, brahma_rasayana |
| `practice` | 80 | Pranayama, routines | nadi_shodhana, ujjayi |
| `symptom` | 60 | Symptoms of imbalance | anxiety, fatigue, bloating |
| `behavior` | 29 | Lifestyle factors | late_night_sleep, overeating |
| `quality` | 20 | Gunas (attributes) | snigdha, ruksha, laghu |
| `season` | 6 | Seasonal contexts | winter, summer, monsoon |
| `time_window` | 6 | Time-of-day periods | morning, evening, night |

### Edge Types (relationships)

| Relationship | Count | Description | Example |
|--------------|-------|-------------|---------|
| `PACIFIES` | 278 | Reduces dosha | ginger → PACIFIES → kapha |
| `AGGRAVATES` | 175 | Increases dosha | late_night → AGGRAVATES → vata |
| `CAUSES` | 92 | Behavior causes symptom | skipping_meals → CAUSES → anxiety |
| `INDICATES` | 60 | Symptom indicates imbalance | scattered → INDICATES → vata |
| `OPTIMAL_TIME` | 55 | Best time for practice | pranayama → OPTIMAL_TIME → morning |
| `REDUCES` | 11 | Reduces symptom | warm_milk → REDUCES → insomnia |
| `AMPLIFIES` | 6 | Season amplifies dosha | winter → AMPLIFIES → vata |
| `DOMINANT_DURING` | 6 | Dosha dominant at time | kapha → DOMINANT_DURING → morning |
| `CONTRAINDICATED_WITH` | 1 | Avoid combining | banana → CONTRAINDICATED_WITH → milk |

---

## Node Attributes

### Food Node (`kind = 'food'`)

```json
{
  "name": "ginger",
  "name_sanskrit": "Shunti",
  "display_name": "Ginger",
  "attrs": {
    "rasa": "katu",           // Taste: sweet, sour, salty, pungent, bitter, astringent
    "virya": "ushna",         // Potency: hot (ushna) or cold (shita)
    "vipaka": "madhura",      // Post-digestive effect
    "guna": ["laghu", "snigdha"],  // Qualities
    "season": "winter"        // Best season
  },
  "citations": [
    {
      "source": "bhavaprakasha",
      "chapter": "madhya_khanda.6",
      "context": "Shunti is pungent, hot, and digestive"
    }
  ],
  "confidence": 0.9
}
```

### Herb Node (`kind = 'herb'`)

```json
{
  "name": "ashwagandha",
  "name_sanskrit": "Ashvagandha",
  "display_name": "Ashwagandha",
  "attrs": {
    "rasa": "tikta",
    "virya": "ushna",
    "vipaka": "madhura",
    "prabhava": "balya",      // Special action
    "part_used": "root",
    "dosage_form": "churna",
    "therapeutic_uses": ["adaptogen", "nervine", "rejuvenative"]
  },
  "citations": [
    {
      "source": "charaka_samhita",
      "chapter": "chikitsasthana",
      "context": "Ashwagandha is one of the foremost rasayanas"
    }
  ]
}
```

### Behavior Node (`kind = 'behavior'`)

```json
{
  "name": "late_night_sleep",
  "display_name": "Late Night Sleep",
  "attrs": {
    "category": "sleep",
    "mechanism": "Disrupts vata's natural rhythm, increases mobile quality",
    "symptoms_caused": ["insomnia", "anxiety", "dry_skin", "restlessness"],
    "nidana": "vihara",       // Etiological category
    "recommendations": "Sleep before 10 PM during vata time"
  },
  "citations": [
    {
      "source": "ashtanga_hridaya",
      "chapter": "sutrasthana.4",
      "context": "Ratrijagarana (staying awake at night) aggravates vata"
    }
  ]
}
```

### Asana Node (`kind = 'asana'`)

```json
{
  "name": "shavasana",
  "name_sanskrit": "Śavāsana",
  "display_name": "Corpse Pose",
  "attrs": {
    "category": "restorative",
    "level": "beginner",
    "hold_time_seconds": "300-600",
    "breath_pattern": "natural, observational",
    "english_name": "Corpse Pose",
    "benefits": ["calms nervous system", "reduces stress", "promotes deep relaxation"],
    "contraindications": ["late pregnancy - modify with props"],
    "chakra_activation": ["anahata", "sahasrara"],
    "mechanism": "Complete stillness pacifies vata's mobile quality",
    "modifications": "Use bolster under knees for lower back support"
  },
  "citations": [
    {
      "source": "hatha_yoga_pradipika",
      "chapter": "1.34",
      "context": "Shavasana removes fatigue and gives rest to the mind"
    }
  ],
  "confidence": 0.9
}
```

---

## How It Was Built

### Phase 1: Schema Design

Created migration `0002_ayurvedic_knowledge_graph.sql` with:
- Nodes table with flexible JSONB attrs
- Edges table with relationship types
- Sources registry for 4 classical texts
- Validation log for audit trail
- Helper functions for graph traversal

```sql
-- Run migration
python sakhi/infra/scripts/run_migration.py \
  sakhi/infra/scripts/migrations/0002_ayurvedic_knowledge_graph.sql
```

### Phase 2: LLM Validation Pipeline

Each item goes through GPT-4o validation:

```python
# From validate_ayurvedic_data.py
FOOD_VALIDATION_PROMPT = """You are an Ayurvedic scholar validating food data
against classical texts (Charaka Samhita, Ashtanga Hridaya, etc.)

Validate this food and provide accurate Ayurvedic properties:
Food: {name}

Provide JSON with:
- validated_properties: rasa, virya, vipaka, guna
- dosha_effects: which doshas it pacifies/aggravates
- citations: source text references
- confidence: 0.0-1.0
"""
```

### Phase 3: Database Population

```bash
# Set environment
export $(grep -E "^(DATABASE_URL|OPENAI_API_KEY)" .env | xargs)

# Run initial validation (foods, practices, symptoms)
python sakhi/infra/scripts/data/validate_ayurvedic_data.py

# Populate database
python sakhi/infra/scripts/data/populate_validated_graph.py

# Run expansion (herbs, rasayanas, behaviors)
python sakhi/infra/scripts/data/expand_knowledge_graph.py
```

### Phase 4: Integration

Connected to:
1. **Recommendation Engine** - Queries graph for personalized suggestions
2. **Causal Reasoning** - Explains "why am I feeling X?"
3. **Pattern Learning** - Learns user-specific cause-effect patterns
4. **Feedback Loop** - Refines preferences from user reactions

---

## Usage Examples

### Query Foods for Dosha

```python
from sakhi.apps.api.services.ayurveda.graph_reasoning import query_foods_for_dosha

# Get foods that pacify vata
foods = await query_foods_for_dosha("vata", "PACIFIES", limit=5)

# Returns:
[
    {
        "name": "warm_milk",
        "name_sanskrit": "Dugdha",
        "rasa": "madhura",
        "virya": "shita",
        "citations": [{"source": "charaka_samhita", "chapter": "sutrasthana.27"}],
        "weight": 0.9
    },
    ...
]
```

### Query Herbs

```python
from sakhi.apps.api.services.recommendations.generator import query_herbs_for_dosha

herbs = await query_herbs_for_dosha("vata", limit=3)

# Returns:
[
    {
        "name": "ashwagandha",
        "name_sanskrit": "Ashvagandha",
        "therapeutic_uses": ["adaptogen", "nervine"],
        "citations": [{"source": "charaka_samhita"}]
    }
]
```

### Query Yoga Asanas

```python
from sakhi.apps.api.services.ayurveda.graph_reasoning import query_asanas_for_dosha

# Get beginner-friendly asanas that pacify vata
asanas = await query_asanas_for_dosha("vata", level="beginner", limit=5)

# Returns:
[
    {
        "name": "shavasana",
        "name_sanskrit": "Śavāsana",
        "display_name": "Corpse Pose",
        "category": "restorative",
        "level": "beginner",
        "benefits": ["calms nervous system", "reduces stress"],
        "contraindications": [],
        "chakra_activation": ["anahata"],
        "citations": [{"source": "hatha_yoga_pradipika", "chapter": "1.34"}]
    },
    {
        "name": "balasana",
        "name_sanskrit": "Bālāsana",
        "display_name": "Child's Pose",
        "category": "restorative",
        "level": "beginner",
        "benefits": ["calms mind", "releases lower back"],
        ...
    }
]
```

### Get Causal Explanation

```python
from sakhi.apps.api.services.ayurveda.causal_reasoning import explain_symptom

explanation = await explain_symptom(
    person_id="user-123",
    symptom="anxiety"
)

# Returns:
CausalExplanation(
    symptom="anxiety",
    dosha_context="Anxiety is a classic sign of elevated Vata...",
    primary_causes=["late_night_sleep", "irregular_meals"],
    seasonal_influence="Winter naturally increases vata energy",
    ayurvedic_source="Charaka Samhita, Sutrasthana"
)
```

### Check Contraindications

```python
from sakhi.apps.api.services.recommendations.generator import check_contraindications

warnings = await check_contraindications("banana")

# Returns:
["Avoid with milk: Heavy combination, clogs channels"]
```

---

## Validation Process

Each node goes through this validation:

```
1. SEED DATA
   ├── Curated list of foods/herbs/practices
   └── Initial properties from secondary sources

2. LLM VALIDATION (GPT-4o)
   ├── Validate against classical texts
   ├── Add Sanskrit names (IAST)
   ├── Provide citations
   └── Assign confidence score

3. DATABASE INSERT
   ├── Store validated properties
   ├── Create dosha relationship edges
   └── Log validation in ay_validation_log

4. ONGOING REFINEMENT
   ├── User feedback improves rankings
   └── Personal patterns override general knowledge
```

### Confidence Levels

| Score | Meaning | Source |
|-------|---------|--------|
| 1.0 | Direct quote from text | Exact shloka reference |
| 0.9 | Clear statement in text | Chapter-level reference |
| 0.8 | Clear inference | Multiple corroborating sources |
| 0.7 | Scholarly consensus | Modern Ayurvedic literature |
| 0.6 | Interpretation | Requires expert review |

---

## Source Texts

| Code | Title | Period | Translation |
|------|-------|--------|-------------|
| `charaka_samhita` | Charaka Samhita | ~200 BCE - 200 CE | P.V. Sharma (Chaukhamba) |
| `ashtanga_hridaya` | Ashtanga Hridaya | ~600 CE | K.R. Srikantha Murthy |
| `sushruta_samhita` | Sushruta Samhita | ~600 BCE | G.D. Singhal |
| `bhavaprakasha` | Bhavaprakasha | ~1550 CE | K.C. Chunekar |
| `hatha_yoga_pradipika` | Hatha Yoga Pradipika | ~15th CE | Swami Muktibodhananda |
| `gheranda_samhita` | Gheranda Samhita | ~17th CE | James Mallinson |

---

## Files

| File | Purpose |
|------|---------|
| `sakhi/infra/scripts/migrations/0002_ayurvedic_knowledge_graph.sql` | Schema migration |
| `sakhi/infra/scripts/data/validate_ayurvedic_data.py` | LLM validation for foods/practices/symptoms |
| `sakhi/infra/scripts/data/expand_knowledge_graph.py` | LLM validation for herbs/rasayanas/behaviors |
| `sakhi/infra/scripts/data/populate_validated_graph.py` | Database population |
| `sakhi/apps/api/services/ayurveda/graph_reasoning.py` | Graph query functions |
| `sakhi/apps/api/services/ayurveda/causal_reasoning.py` | Causal explanation engine |
| `sakhi/apps/api/services/ayurveda/pattern_learning.py` | Personal pattern detection |
| `sakhi/apps/api/services/recommendations/generator.py` | Personalized recommendations |
| `sakhi/tests/unit/services/test_knowledge_graph.py` | Unit tests (14 passing) |

---

## Future Enhancements

- [x] Add more herbs from Dravyaguna texts (80 herbs now)
- [x] Add yoga asana sequences (42 asanas with dosha effects)
- [ ] Add panchakarma protocols
- [ ] Add disease-specific treatment protocols
- [ ] Implement community validation layer
- [ ] Add multi-language support (Hindi, Sanskrit)

---

## Related Documentation

- [DATABASE_SCHEMA.md](../DATABASE_SCHEMA.md) - Full database schema including ay_* tables
- [BUILD_PLAN.md](../BUILD_PLAN.md) - Overall build plan (A.7 Learning Pipeline)
- [SAKHI_EVOLUTION_PLAN.md](../_archive/2026-02-03_consolidation/SAKHI_EVOLUTION_PLAN.md) - System evolution
