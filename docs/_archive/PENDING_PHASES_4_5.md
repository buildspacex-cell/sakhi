# Pending Phases: Planning Integration & Knowledge Graph

> **Status:** Deferred post-MVP
> **Estimated effort:** 60-80 hours total
> **Priority:** P1 (after MVP validation)

---

## Phase 4: Planning Integration (18-22 hours)

### Goal
Fix the planning system and connect it to rhythms for intelligent task scheduling.

### 4.1 Fix Goal Evolver

**File:** `sakhi/apps/worker/tasks/goal_evolver.py`

**Current Issue:** Uses placeholder `db_find`/`db_insert` functions instead of real database queries.

**Changes needed:**
```python
# Replace db_find/db_insert with actual asyncpg queries
# Use sakhi.apps.api.core.db import exec, q

async def run_goal_evolver(person_id: str) -> None:
    goals = await dbfetch(
        "SELECT * FROM goals WHERE person_id = $1 AND status = 'active'",
        person_id
    )
    # ... rest of implementation
```

### 4.2 Intent Extraction Worker

**Create:** `sakhi/apps/worker/tasks/intent_extraction_worker.py`

**Purpose:** Extract goals, tasks, concerns from journal entries using LLM.

```python
async def extract_intents_from_entry(person_id: str, entry_id: str):
    """Extract goals, tasks, concerns from journal using LLM."""
    # 1. Fetch journal entry
    # 2. Call LLM to extract intents
    # 3. Store in intent_extractions table
    # 4. Link to goals when user confirms
```

### 4.3 Goal Suggester Service

**Create:** `sakhi/apps/api/services/planner/goal_suggester.py`

**Purpose:** Cluster intents into goal suggestions for user confirmation.

```python
async def suggest_goals_from_intents(person_id: str):
    """
    - Query intent_extractions with status='pending'
    - Cluster related intents
    - Create goal_suggestions (don't auto-create goals)
    - Respect crystallization thresholds (3+ mentions)
    """
```

### 4.4 Rhythm-Aligned Task Scheduling

**Create:** `sakhi/apps/api/services/planner/rhythm_scheduler.py`

**Purpose:** Schedule tasks based on energy forecasts.

```python
async def schedule_tasks_by_rhythm(person_id: str, date: datetime):
    """
    - Get rhythm forecast for the day
    - Get pending tasks from goals
    - Match high-energy tasks to peak windows
    - Block high-load tasks when capacity < 0.4
    - Return schedule for morning preview
    """
```

### 4.5 Surface in Adaptive Response

**Modify:** `sakhi/apps/api/services/turn/deterministic_context_loader.py`

Add `rhythm_planner_alignment` to context loaded for responses.

### Success Criteria
- [ ] Intents extracted from every journal entry
- [ ] Goal suggestions presented (not auto-created)
- [ ] Tasks scheduled by energy forecast
- [ ] Response includes "Your capacity is X — good for Y"

---

## Phase 5: Knowledge Graph & Recommendations (45-60 hours)

### Goal
Populate the Ayurvedic knowledge graph and enable intelligent, personalized recommendations via graph reasoning.

### 5.1 Populate Knowledge Graph (CRITICAL)

**Create:** `sakhi/infra/scripts/data/populate_ayurvedic_graph.py`

**Target:** 300 nodes, 1000 edges

**Node types:**
| Type | Count | Fields |
|------|-------|--------|
| Dosha | 3 | name, user_facing_name, qualities |
| Food | 100 | name, rasa, guna, virya, best_season |
| Practice | 80 | name, type, duration, best_time |
| Symptom | 60 | name, dosha_association, severity |
| Quality | 20 | name (gunas: light, heavy, oily, dry) |
| Season | 6 | name, dosha_aggravation |
| TimeWindow | 12 | name, hour_start, hour_end, dosha_dominance |

**Edge types:**
| Edge | Description |
|------|-------------|
| PACIFIES | food/practice → dosha (with strength) |
| AGGRAVATES | food/practice → dosha (with strength) |
| INDICATES | symptom → dosha_imbalance |
| BALANCES | practice → imbalance |
| OPTIMAL_TIME | practice → time_window |
| HAS_QUALITY | food → quality |

### 5.2 Graph Reasoning Engine

**Create:** `sakhi/apps/api/services/ayurveda/graph_reasoning.py`

```python
async def query_balancing_recommendations(
    person_id: str,
    friction_state: str,
    season: str,
    time_of_day: int,
    dietary_preferences: dict
) -> dict:
    """
    Multi-hop graph traversal:
    1. Find elevated dosha from friction_state
    2. Query foods/practices that PACIFY that dosha
    3. Filter by season appropriateness
    4. Filter by time of day
    5. Filter by dietary restrictions
    6. Rank by: pacification_strength × context_match
    """
```

### 5.3 Recommendations API

**Create:** `sakhi/apps/api/routes/recommendations.py`

```python
@router.get("/recommendations/now/{person_id}")
async def get_current_recommendations(person_id: str):
    """
    Returns:
    - friction_state: current state
    - immediate_actions: quick fixes
    - foods_now: what to eat now
    - practices_today: what to do today
    - avoid: what to avoid
    """
```

### 5.4 Integrate into Conversation

**Modify:** `sakhi/apps/api/services/response/synthesizer.py`

Add "Recommended Actions" section to adaptive prompt with graph-based recommendations.

### Success Criteria
- [ ] Knowledge Graph: 300+ nodes, 1000+ edges
- [ ] Graph queries return personalized recommendations
- [ ] Recommendations filtered by context (season + time + diet)
- [ ] Response includes "Try X (0.85 strength) — perfect for Y"

---

## Database Changes Needed

### Phase 4 Tables (already created in MVP)
- `goals` (extended)
- `goal_history`
- `intent_extractions`
- `goal_suggestions`

### Phase 5 Tables
Need to verify `ay_nodes` and `ay_edges` schema and populate:

```sql
-- Check current state
SELECT COUNT(*) FROM ay_nodes;  -- Currently ~8 sample nodes
SELECT COUNT(*) FROM ay_edges;
```

---

## Implementation Order

1. **Phase 4.1** - Fix goal_evolver.py (2-3 hours)
2. **Phase 4.2** - Intent extraction worker (4-5 hours)
3. **Phase 4.3** - Goal suggester (3-4 hours)
4. **Phase 4.4** - Rhythm scheduler (4-5 hours)
5. **Phase 4.5** - Context loader integration (2-3 hours)
6. **Phase 5.1** - Knowledge graph population (15-20 hours) ← CRITICAL
7. **Phase 5.2** - Graph reasoning engine (10-15 hours)
8. **Phase 5.3** - Recommendations API (5-8 hours)
9. **Phase 5.4** - Synthesizer integration (5-8 hours)

---

## User Experience After These Phases

| What User Sees | Phase |
|----------------|-------|
| "I noticed you mentioned X 3 times — want to make it a goal?" | 4.3 |
| "Your energy peaks at 10am — schedule deep work then?" | 4.4 |
| "Try warm ginger tea (0.85) — perfect for this cold evening" | 5.3 |
| "Avoid cold drinks today — Vata is already elevated" | 5.3 |
| "5-min breathing now would help calm scattered energy" | 5.3 |

---

## Notes

- Phase 5 is blocked on Knowledge Graph population — this is the biggest task
- Phase 4 can be done incrementally
- Consider using existing Ayurvedic databases/APIs to bootstrap knowledge graph
- Graph reasoning could use Neo4j or PostgreSQL with recursive CTEs
