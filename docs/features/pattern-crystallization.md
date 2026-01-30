# Pattern Crystallization Layer — Design Document

> **Status:** Design Only (Not Implemented)
> **Created:** 2026-01-26
> **Purpose:** Transform raw signals into earned understanding through periodic crystallization

---

## Core Philosophy

**The current architecture has memory. It needs wisdom.**

Memory = storing what happened
Wisdom = knowing what matters, how it's changing, and when to speak about it

The Pattern Crystallization Layer (PCL) is a **periodic intelligence loop** that:
1. Reviews accumulated signals across time windows
2. Identifies patterns that meet threshold evidence
3. Promotes patterns to structured understanding only when earned
4. Creates citable provenance so Sakhi can reference specific moments
5. Tracks trajectories (improving, worsening, stable, emerging)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         TURN LAYER (Real-time)                          │
│  turn_v2.py → orchestrate_turn → workers                                │
│  Writes to: journal_entries, memory_short_term, intents, conversation_turns │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ (Signals accumulate)
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    PATTERN CRYSTALLIZATION LAYER                        │
│                     (Runs periodically, not per-turn)                   │
│                                                                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐         │
│  │  Daily Runner   │  │  Weekly Runner  │  │  Monthly Runner │         │
│  │  (frequency,    │  │  (trajectory,   │  │  (themes,       │         │
│  │   recurrence)   │  │   consistency)  │  │   identity)     │         │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘         │
│           │                    │                    │                   │
│           └──────────────┬─────┴────────────────────┘                   │
│                          ▼                                              │
│              ┌───────────────────────┐                                  │
│              │  Crystallization      │                                  │
│              │  Engine               │                                  │
│              │  - Pattern detection  │                                  │
│              │  - Threshold gating   │                                  │
│              │  - Provenance linking │                                  │
│              │  - Trajectory calc    │                                  │
│              └───────────┬───────────┘                                  │
│                          │                                              │
│                          ▼                                              │
│              ┌───────────────────────┐                                  │
│              │  crystallized_patterns│ (new table)                      │
│              │  - pattern_type       │                                  │
│              │  - evidence_entries   │                                  │
│              │  - confidence         │                                  │
│              │  - trajectory         │                                  │
│              │  - first_seen         │                                  │
│              │  - last_seen          │                                  │
│              │  - mention_count      │                                  │
│              └───────────────────────┘                                  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ (Only crystallized patterns)
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    ADAPTIVE RESPONSE LAYER                              │
│  knowledge_gap.py can query crystallized_patterns                       │
│  synthesizer.py can include "You've mentioned X 5 times this week"      │
│  LLM receives earned understanding, not opportunistic signals           │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Database Schema

### New Table: `crystallized_patterns`

```sql
CREATE TABLE crystallized_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES persons(id),

    -- Pattern identification
    pattern_type TEXT NOT NULL,  -- 'concern', 'theme', 'trait', 'relationship', 'goal', 'contradiction'
    topic TEXT NOT NULL,         -- e.g., 'sleep', 'mom', 'work_stress', 'exercise'
    sub_topic TEXT,              -- Optional refinement

    -- The crystallized understanding
    summary TEXT NOT NULL,       -- Human-readable pattern description
    constitution_relevance TEXT, -- How this relates to their dosha (if applicable)

    -- Evidence (provenance)
    evidence_entries UUID[] NOT NULL DEFAULT '{}',  -- Array of journal_entry IDs
    evidence_snippets JSONB NOT NULL DEFAULT '[]',  -- [{entry_id, date, snippet}, ...]
    mention_count INTEGER NOT NULL DEFAULT 0,

    -- Confidence and thresholds
    confidence REAL NOT NULL DEFAULT 0.0,  -- 0-1, increases with evidence
    threshold_met_at TIMESTAMPTZ,          -- When pattern crossed threshold

    -- Trajectory tracking
    trajectory TEXT DEFAULT 'stable',  -- 'improving', 'worsening', 'stable', 'emerging', 'fading'
    trajectory_data JSONB DEFAULT '{}', -- Time-series data for trend calculation

    -- Lifecycle
    status TEXT NOT NULL DEFAULT 'emerging',  -- 'emerging', 'active', 'fading', 'archived'
    first_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    crystallized_at TIMESTAMPTZ,  -- When it became 'active' (threshold met)

    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT valid_trajectory CHECK (trajectory IN ('improving', 'worsening', 'stable', 'emerging', 'fading')),
    CONSTRAINT valid_status CHECK (status IN ('emerging', 'active', 'fading', 'archived')),
    CONSTRAINT valid_pattern_type CHECK (pattern_type IN ('concern', 'theme', 'trait', 'relationship', 'goal', 'contradiction'))
);

CREATE INDEX idx_crystallized_person ON crystallized_patterns(person_id);
CREATE INDEX idx_crystallized_status ON crystallized_patterns(person_id, status);
CREATE INDEX idx_crystallized_type ON crystallized_patterns(person_id, pattern_type);
CREATE INDEX idx_crystallized_topic ON crystallized_patterns(person_id, topic);
```

### New Table: `pattern_signals` (Pre-crystallization staging)

```sql
-- Raw signals before they meet threshold
-- Workers write here, crystallization engine reads and promotes
CREATE TABLE pattern_signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL,

    -- Signal source
    entry_id UUID REFERENCES journal_entries(id),
    signal_type TEXT NOT NULL,  -- 'topic_mention', 'emotion', 'intent', 'entity_reference'

    -- Signal content
    topic TEXT NOT NULL,
    value TEXT,  -- The actual content/snippet
    sentiment REAL,  -- -1 to 1 if applicable

    -- Metadata
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '30 days'),

    -- Processing state
    processed BOOLEAN DEFAULT FALSE,
    crystallized_pattern_id UUID REFERENCES crystallized_patterns(id)
);

CREATE INDEX idx_signals_person_topic ON pattern_signals(person_id, topic);
CREATE INDEX idx_signals_unprocessed ON pattern_signals(person_id, processed) WHERE NOT processed;
CREATE INDEX idx_signals_expires ON pattern_signals(expires_at);
```

---

## Crystallization Thresholds

```python
# sakhi/apps/api/services/crystallization/thresholds.py

from dataclasses import dataclass
from typing import Dict

@dataclass
class CrystallizationThreshold:
    """Defines when a pattern becomes 'crystallized' (earned)."""

    # Minimum mentions before pattern is considered
    min_mentions: int

    # Time window for counting mentions
    window_days: int

    # Minimum confidence score (0-1)
    min_confidence: float

    # Whether pattern requires consistency across different contexts
    requires_consistency: bool = False

    # Minimum distinct days the pattern must appear
    min_distinct_days: int = 1


# Different thresholds for different pattern types
CRYSTALLIZATION_THRESHOLDS: Dict[str, CrystallizationThreshold] = {
    # Concerns: Things they're worried about
    # Threshold: 3+ mentions in 14 days
    "concern": CrystallizationThreshold(
        min_mentions=3,
        window_days=14,
        min_confidence=0.5,
        min_distinct_days=2,
    ),

    # Themes: Recurring topics in their life
    # Threshold: 5+ mentions in 30 days
    "theme": CrystallizationThreshold(
        min_mentions=5,
        window_days=30,
        min_confidence=0.6,
        requires_consistency=True,
        min_distinct_days=3,
    ),

    # Traits: Stable characteristics
    # Threshold: 7+ consistent mentions in 60 days
    "trait": CrystallizationThreshold(
        min_mentions=7,
        window_days=60,
        min_confidence=0.75,
        requires_consistency=True,
        min_distinct_days=5,
    ),

    # Relationships: People in their life
    # Threshold: 4+ mentions in 30 days
    "relationship": CrystallizationThreshold(
        min_mentions=4,
        window_days=30,
        min_confidence=0.6,
        min_distinct_days=2,
    ),

    # Goals: Things they want to achieve
    # Threshold: 3+ mentions in 21 days (goals can be shorter-lived)
    "goal": CrystallizationThreshold(
        min_mentions=3,
        window_days=21,
        min_confidence=0.5,
        min_distinct_days=2,
    ),

    # Contradictions: Conflicting statements
    # Threshold: 2 contradictory statements (special case)
    "contradiction": CrystallizationThreshold(
        min_mentions=2,
        window_days=30,
        min_confidence=0.7,
        min_distinct_days=2,
    ),
}
```

---

## Service Structure

```
sakhi/apps/api/services/crystallization/
├── __init__.py
├── thresholds.py      # Threshold configuration (above)
├── engine.py          # Core crystallization logic
├── signal_writer.py   # Write signals from workers
├── query.py           # Query interface for adaptive pipeline
```

---

## Core Crystallization Engine

See full implementation in the design discussion. Key functions:

### Signal Aggregation
```python
async def aggregate_signals(person_id: str, window_days: int) -> Dict[str, List[Dict]]
```

### Pattern Detection
```python
def detect_pattern_type(topic: str, signals: List[Dict]) -> str
def calculate_distinct_days(signals: List[Dict]) -> int
def calculate_trajectory(signals: List[Dict], existing_data: Dict) -> Tuple[str, Dict]
```

### Threshold Checking
```python
def check_threshold(candidate: PatternCandidate, threshold: CrystallizationThreshold) -> Tuple[bool, float]
```

### Main Crystallization
```python
async def crystallize_patterns(person_id: str, window_days: int, run_type: str) -> CrystallizationResult
async def create_crystallized_pattern(...) -> UUID
async def update_existing_pattern(...)
async def store_emerging_pattern(...)
```

---

## Signal Writer (For Workers)

Workers should write signals to `pattern_signals` instead of directly updating `personal_model`:

```python
# sakhi/apps/api/services/crystallization/signal_writer.py

async def write_topic_signal(person_id, entry_id, topic, snippet, sentiment=None)
async def write_emotion_signal(person_id, entry_id, emotion, snippet, intensity)
async def write_intent_signal(person_id, entry_id, intent_title, intent_domain, snippet)
async def write_entity_signal(person_id, entry_id, entity_name, entity_type, snippet, sentiment=None)
async def write_batch_signals(person_id, entry_id, topics, snippet, sentiment=None)
```

---

## Query Interface for Adaptive Pipeline

```python
# sakhi/apps/api/services/crystallization/query.py

async def get_active_patterns(person_id, pattern_types=None, limit=10) -> List[Dict]
async def get_concerns(person_id, limit=5) -> List[Dict]
async def get_relationships(person_id, limit=10) -> List[Dict]
async def get_themes(person_id, limit=5) -> List[Dict]
async def get_goals(person_id, limit=5) -> List[Dict]
async def get_pattern_for_topic(person_id, topic) -> Optional[Dict]
async def get_trajectory_summary(person_id) -> Dict[str, List[str]]
def format_pattern_for_prompt(pattern: Dict) -> str
async def get_patterns_for_prompt(person_id, current_topic=None) -> Dict
```

---

## Scheduler Configuration

```python
CRYSTALLIZATION_SCHEDULES = {
    "daily_crystallization": {
        "task": "run_daily_crystallization_batch",
        "schedule": "0 3 * * *",  # 3 AM daily
        "window_days": 14,
        "focus": "frequency, recurrence"
    },
    "weekly_crystallization": {
        "task": "run_weekly_crystallization_batch",
        "schedule": "0 4 * * 0",  # 4 AM Sunday
        "window_days": 30,
        "focus": "trajectory, consistency"
    },
    "monthly_crystallization": {
        "task": "run_monthly_crystallization_batch",
        "schedule": "0 5 1 * *",  # 5 AM first of month
        "window_days": 60,
        "focus": "themes, traits, identity"
    },
}
```

---

## Integration Points

### 1. Worker Integration
Workers that currently write to `personal_model` directly should be updated to write signals:

| Current Worker | Current Target | New Target |
|----------------|----------------|------------|
| topic_extraction | personal_model.topics | pattern_signals (topic_mention) |
| emotion_detection | personal_model.emotion_state | pattern_signals (emotion) |
| intent_extraction | intents table | pattern_signals (intent) + intents |
| entity_extraction | personal_model.life_context | pattern_signals (entity_reference) |

### 2. Adaptive Pipeline Integration
Update `knowledge_gap.py` and `synthesizer.py` to query crystallized patterns:

```python
# In knowledge_gap.py
from sakhi.apps.api.services.crystallization.query import get_pattern_for_topic

# Check if we have crystallized understanding about the topic
pattern = await get_pattern_for_topic(person_id, sense.symptom)
if pattern:
    # We have earned knowledge - include in known facts
    gap.known[pattern["topic"]] = KnownFact(...)
```

### 3. Prompt Integration
Update `build_adaptive_prompt` to include crystallized patterns section:

```python
# In synthesizer.py
patterns = await get_patterns_for_prompt(person_id, current_topic=synth.symptom)

crystallized_section = """
═══════════════════════════════════════════════════════════════════════════════
EARNED UNDERSTANDING (Crystallized from repeated patterns - you can cite this)
═══════════════════════════════════════════════════════════════════════════════
"""
```

---

## Migration

```sql
-- sakhi/infra/scripts/migrations/0033_pattern_crystallization.sql

-- See full schema above
CREATE TABLE IF NOT EXISTS crystallized_patterns (...);
CREATE TABLE IF NOT EXISTS pattern_signals (...);

-- Cleanup job for expired signals (run via pg_cron)
-- DELETE FROM pattern_signals WHERE expires_at < NOW();
```

---

## What This Design Achieves

| Problem | Solution |
|---------|----------|
| Single turns modify identity | Signals staged → crystallization threshold required |
| No frequency tracking | `mention_count`, `distinct_days` tracked per topic |
| No trajectory awareness | `trajectory` field with improving/worsening/stable/emerging/fading |
| LLM cannot cite evidence | `evidence_snippets` with dates → "Based on your messages from..." |
| Opportunistic memory writes | Workers write to `pattern_signals`, not directly to `personal_model` |
| No earned vs borrowed authority | Patterns have `status`: emerging (sub-threshold) vs active (earned) |
| Intents stored immediately | Goals require 3+ mentions over 21 days to crystallize |
| Relationships not tracked | Entity signals → relationship patterns when mentioned 4+ times |
| Contradictions not detected | Dedicated contradiction detection (to be implemented) |

---

## Implementation Phases

### Phase 1: Foundation
- [ ] Create migration for new tables
- [ ] Create `crystallization/` service directory
- [ ] Implement `thresholds.py`
- [ ] Implement `signal_writer.py`
- [ ] Implement core `engine.py` functions

### Phase 2: Worker Integration
- [ ] Update topic extraction worker to write signals
- [ ] Update emotion detection worker to write signals
- [ ] Update intent extraction worker to write signals
- [ ] Update entity extraction (if exists) to write signals

### Phase 3: Adaptive Pipeline Integration
- [ ] Update `knowledge_gap.py` to query crystallized patterns
- [ ] Update `synthesizer.py` to include crystallized section in prompt
- [ ] Add `crystallized_patterns` to metadata for debugging

### Phase 4: Scheduling
- [ ] Create scheduler jobs for daily/weekly/monthly crystallization
- [ ] Add monitoring/logging for crystallization runs
- [ ] Add cleanup job for expired signals

---

## Related Documents

- [Conversation Turn Audit](./CONVERSATION_TURN_AUDIT.md) — The audit that identified the need for this layer
- [Worker Audit](./WORKER_AUDIT.md) — Full inventory of workers and their purposes (TBD)
