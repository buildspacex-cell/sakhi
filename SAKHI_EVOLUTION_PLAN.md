# Sakhi Evolution Plan

## The Vision

**Sakhi: Infrastructure for humans to reclaim their lives.**

- The world comes through YOUR Sakhi
- You see everything, you decide everything
- Sakhi handles the friction
- You live your life — health, joy, connection

---

## Current State: The 70% Reality

Sakhi is a sophisticated signal detection platform. It captures rich, multi-dimensional data about personality, energy, and patterns. But it stops at **detection and reflection** rather than **understanding and action**.

### What Works (70-85%)

| Layer | Status | What's There |
|-------|--------|--------------|
| Signal Capture | 85% | Journal ingestion, voice, embeddings, sentiment |
| Dosha Detection | 75% | Vata/Pitta/Kapha from text |
| Guna Tracking | 70% | Sattva/Rajas/Tamas signals |
| Element Mapping | 65% | 5 elements across body/mind/emotion |
| Short-term Memory | 80% | Recent signals stored, weighted, TTL-based |
| Weekly Synthesis | 70% | Aggregates signals, LLM reflection |
| Operating System | 70% | Adaptive/Performance/Conservation mapping |
| Memory Graph | 60% | Nodes and edges exist, basic relationships |
| Rhythm Tracking | 65% | Energy curves, chronotype, daily state |

### What's Missing (The Gaps)

| Gap | Severity | Current State | Impact |
|-----|----------|---------------|--------|
| **Knowledge Graph Population** | CRITICAL | 20% - Schema exists, data empty | Cannot explain "why" or give reasoned recommendations |
| **Personalized Recommendations** | HIGH | 25% - Generic suggestions only | Friction detected but not addressed personally |
| **Relationship Model** | HIGH | 30% - Entities extracted, no depth | Don't know who matters or relationship context |
| **Action/Feedback Loop** | HIGH | 10% - Intents extracted, no follow-through | Sakhi observes but doesn't guide |
| **Preference Completeness** | MEDIUM | 40% - Basic preferences, no scheduling | Don't know when/where/how you prefer things |
| **Circadian/Seasonal Logic** | MEDIUM | 20% - Time ignored in recommendations | Ayurvedic intelligence not time-aware |

---

## The Path Forward

### Philosophy

**Execution grounded in reflection creates daily engagement that funds deeper reflection over time.**

We don't wait for perfect reflection before users benefit. We build execution (calendar, coordination) that provides daily utility, grounded in the reflection we have. Users stay engaged. Reflection matures.

### The Sequence

```
PHASE 1: Complete Reflection Gaps (3 weeks)
    ↓
PHASE 2: Build Execution Layer (4 weeks)
    ↓
PHASE 3: Sakhi-to-Sakhi Mesh (3 weeks)
    ↓
PHASE 4: Deepen & Expand (Ongoing)
```

---

## PHASE 1: Complete Reflection Gaps

**Duration: 3 weeks**
**Goal: Sakhi truly knows you — preferences, relationships, patterns**

### 1.1 Relationship Model (Week 1)

**Current:** `memory_nodes` has 'person' kind, but no depth. Entities extracted but not enriched.

**Target:** Sakhi knows who matters in your life and context about them.

#### Schema Extension

Extend `memory_nodes.data` for `node_kind = 'person'`:

```json
{
  "relationship": {
    "type": "close_friend | family | colleague | acquaintance",
    "closeness": 0.85,
    "frequency_target": "weekly | monthly | quarterly",
    "last_seen": "2026-01-15",
    "last_contact": "2026-01-28",

    "context": {
      "current_situation": "Job transition, stressed lately",
      "relationship_to_user": "College friend, 10 years",
      "important_to_know": "Wife is Sarah, two kids",
      "shared_interests": ["hiking", "film photography"]
    },

    "patterns": {
      "user_energy_after": "energized | drained | neutral",
      "usual_activities": ["dinner", "hiking"],
      "preferred_times": ["weekend afternoons"],
      "notes": "Always runs 15 min late"
    }
  }
}
```

#### Implementation

| Task | Description |
|------|-------------|
| Schema migration | Extend memory_nodes data structure |
| Relationship extraction service | Extract relationship signals from journal entries |
| Relationship enrichment prompts | LLM extracts context when people mentioned |
| Manual enrichment flow | User can tell Sakhi about relationships |
| Relationship summary endpoint | Get all relationships with context |

#### Files

```
New:
  /sakhi/apps/api/services/relationships/
    ├── extraction.py      # Extract from entries
    ├── enrichment.py      # LLM enrichment
    └── repository.py      # CRUD operations

  /sakhi/apps/api/routes/relationships.py

Modified:
  /sakhi/apps/api/services/memory/memory_ingest.py
    → Call relationship extraction on ingest
```

---

### 1.2 Scheduling Preferences (Week 1-2)

**Current:** `user_profile.preferences` exists but has no scheduling structure.

**Target:** Sakhi knows when, where, and how you prefer to do things.

#### Schema Extension

Extend `user_profile.preferences`:

```json
{
  "scheduling": {
    "preferred_times": {
      "weekday": ["evening"],
      "weekend": ["late_morning", "afternoon"]
    },
    "avoid_times": {
      "always": ["early_morning"],
      "weekday": ["lunch"],
      "sunday": ["evening"]
    },
    "buffer_minutes": 30,
    "max_events_per_day": 3,
    "preferred_duration": {
      "coffee": 45,
      "dinner": 120,
      "call": 30
    }
  },

  "location": {
    "default_area": "downtown",
    "max_travel_minutes": 30,
    "home_base": "...",
    "work_location": "..."
  },

  "dining": {
    "likes": ["italian", "thai", "mediterranean"],
    "dislikes": ["sushi", "very spicy"],
    "dietary": ["vegetarian"],
    "favorites": [
      {"name": "Rosario's", "type": "italian", "location": "..."}
    ]
  }
}
```

#### Implementation

| Task | Description |
|------|-------------|
| Schema definition | Define preference structure in schemas.py |
| Preference capture conversation | "When do you prefer to meet?" flow |
| Preference inference | Learn from past behavior mentioned in journals |
| Preference API | Get/update preferences endpoints |

#### Files

```
New:
  /sakhi/apps/api/services/preferences/
    ├── scheduling.py      # Scheduling preference logic
    ├── capture.py         # Conversation-based capture
    └── inference.py       # Infer from patterns

Modified:
  /sakhi/apps/api/core/schemas.py
    → Add SchedulingPreferences, LocationPreferences, DiningPreferences
```

---

### 1.3 Knowledge Graph Population (Week 2-3)

**Current:** `ay_nodes` and `ay_edges` tables exist but are empty. No causal reasoning.

**Target:** Sakhi can explain "why" and connect patterns to causes.

#### What the Knowledge Graph Enables

```
Without Knowledge Graph:
  User: "Why do I feel scattered?"
  Sakhi: "Your Vata is elevated this week."

With Knowledge Graph:
  User: "Why do I feel scattered?"
  Sakhi: "Your Vata has been high since Tuesday. Looking at your
         patterns: you had three late nights, skipped morning routine,
         and had that stressful conversation with your manager.
         When this happened in October, grounding practices in the
         evening helped within 2-3 days."
```

#### Implementation

| Task | Description |
|------|-------------|
| Define core node types | Causes (sleep, food, weather, events) + Effects (dosha states, moods) |
| Edge relationship types | causes, worsens, improves, correlates_with |
| Populate Ayurvedic base knowledge | Standard relationships (late nights → Vata, etc.) |
| Personal pattern detection | Detect user-specific cause-effect patterns |
| Causal query service | "Why am I feeling X?" → traverse graph |
| Recommendation reasoning | Ground suggestions in personal graph |

#### Schema

```sql
-- ay_nodes (exists, needs population)
node_type: 'cause' | 'effect' | 'practice' | 'symptom' | 'state'
node_category: 'sleep' | 'food' | 'activity' | 'environment' | 'dosha' | 'guna' | 'emotion'
label: "Late nights"
ayurvedic_context: {...}  -- Traditional understanding
personal_weight: 0.0      -- User-specific importance (learned)

-- ay_edges (exists, needs population)
relation: 'increases' | 'decreases' | 'causes' | 'correlates'
base_weight: 0.7          -- General Ayurvedic weight
personal_weight: 0.0      -- User-specific (learned)
evidence_count: 0         -- How often observed for this user
```

#### Files

```
New:
  /sakhi/apps/api/services/knowledge_graph/
    ├── base_population.py    # Populate Ayurvedic base knowledge
    ├── personal_learning.py  # Learn user-specific patterns
    ├── causal_query.py       # "Why am I..." queries
    └── recommendation.py     # Graph-grounded recommendations

  /sakhi/data/ayurvedic_knowledge_base.json  # Base relationships
```

---

### 1.4 Personalized Recommendations (Week 3)

**Current:** Generic suggestions based on detected state.

**Target:** Recommendations grounded in YOUR patterns, YOUR history, YOUR preferences.

#### Implementation

| Task | Description |
|------|-------------|
| Recommendation context builder | Gather: current state + knowledge graph + preferences + history |
| Personal effectiveness tracking | What worked for YOU before |
| Recommendation generation | LLM with full personal context |
| Feedback capture | Did you try it? Did it help? |

#### Example Flow

```
Input: User shows elevated Vata (scattered, anxious)

Context gathered:
- Knowledge graph: User's Vata spikes correlate with sleep < 6hrs
- History: Last month, evening walks helped within 2 days
- Preferences: User likes being outdoors, dislikes meditation apps
- Current: User has free time at 6pm today

Recommendation:
"You've been scattered since Tuesday — looks like those late nights
catching up. Last month when this happened, evening walks helped you
reset. You're free at 6pm — want me to block 30 minutes for a walk?"
```

#### Files

```
New:
  /sakhi/apps/api/services/recommendations/
    ├── context_builder.py     # Gather all relevant context
    ├── effectiveness.py       # Track what works for user
    ├── generator.py           # Generate personalized recs
    └── feedback.py            # Capture and learn from feedback
```

---

## PHASE 2: Build Execution Layer

**Duration: 4 weeks**
**Goal: Sakhi can act — calendar, messaging, coordination**

### 2.1 Sakhi Calendar (Week 4-5)

**Current:** No calendar exists.

**Target:** Native calendar that understands you.

#### Schema

```sql
CREATE TABLE calendar_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  person_id UUID NOT NULL REFERENCES personal_model(person_id),

  -- Basic event info
  title TEXT NOT NULL,
  description TEXT,
  start_time TIMESTAMPTZ NOT NULL,
  end_time TIMESTAMPTZ NOT NULL,
  location TEXT,
  location_data JSONB,

  -- Event classification
  event_type TEXT NOT NULL,        -- 'meeting', 'social', 'personal', 'work', 'blocked'
  category TEXT,                   -- 'dinner', 'coffee', 'call', 'focus_time'

  -- Sakhi-native context
  created_by TEXT NOT NULL,        -- 'user', 'sakhi_coordination', 'external_sync'
  related_person_ids UUID[],       -- Who is this with?
  conversation_context TEXT,       -- What led to this event

  -- Coordination (for Sakhi-to-Sakhi)
  coordination_id UUID,
  coordination_status TEXT,        -- 'proposed', 'confirmed', 'cancelled'

  -- Reflective context
  energy_note TEXT,                -- "You were running high that week"
  relationship_note TEXT,          -- "First time seeing them in a month"

  -- Metadata
  status TEXT DEFAULT 'confirmed',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE availability_cache (
  person_id UUID PRIMARY KEY,
  windows JSONB NOT NULL,          -- [{start, end, quality, reason}]
  high_energy_windows JSONB,
  recovery_windows JSONB,
  computed_at TIMESTAMPTZ DEFAULT NOW(),
  valid_until TIMESTAMPTZ
);
```

#### Implementation

| Task | Description |
|------|-------------|
| Calendar CRUD | Create, read, update, delete events |
| Availability computation | Combine calendar + preferences + rhythm |
| Conversational interface | "What's my week?" / "Block Thursday evening" |
| Context attachment | Link events to relationships, conversations |
| Energy-aware suggestions | "You're usually tired Fridays, sure about this?" |

#### Files

```
New:
  /sakhi/apps/api/services/calendar/
    ├── events.py           # Event CRUD
    ├── availability.py     # Compute availability windows
    └── context.py          # Attach reflective context

  /sakhi/apps/api/routes/calendar.py

  /sakhi/infra/sql/YYYYMMDD_calendar.sql
```

---

### 2.2 Conversational Scheduling (Week 5-6)

**Target:** Natural language scheduling that just works.

#### Capabilities

```
"What does my week look like?"
→ Summary with context (who you're seeing, energy predictions)

"Block Thursday evening for me"
→ Creates blocked time

"Schedule dinner with Alex this week"
→ Checks availability, knows Alex, proposes times

"Move my Friday meeting to next week"
→ Finds the meeting, suggests new times
```

#### Implementation

| Task | Description |
|------|-------------|
| Intent recognition | Detect scheduling intents in conversation |
| Slot filling | Extract: who, when, what, where |
| Availability check | Find suitable times |
| Confirmation flow | Present options, confirm choice |
| Calendar update | Create/modify events |

---

### 2.3 External Calendar Sync (Week 6-7)

**Target:** See external commitments, optionally push out.

#### Implementation

| Task | Description |
|------|-------------|
| Google Calendar OAuth | Connect Google account |
| One-way sync IN | Pull events as "blocked" time |
| One-way sync OUT | Push Sakhi events to external (optional) |
| Conflict detection | Warn about overlaps |

**Note:** Sakhi remains source of truth. External calendars are inputs/outputs.

---

## PHASE 3: Sakhi-to-Sakhi Mesh

**Duration: 3 weeks**
**Goal: Your Sakhi talks to other Sakhis**

### 3.1 Mesh Infrastructure (Week 8)

#### Components

```
┌─────────────────────────────────────────────────────────────────┐
│                     SAKHI MESH SERVER                            │
│                                                                  │
│  Identity Registry                                               │
│  └─ Sakhi ID → Person → Endpoint                                │
│                                                                  │
│  Message Router                                                  │
│  └─ Route messages between Sakhis                               │
│                                                                  │
│  Discovery (Later)                                               │
│  └─ Find Sakhis by criteria                                     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### Schema

```sql
-- Mesh registry (could be separate service)
CREATE TABLE sakhi_registry (
  sakhi_id UUID PRIMARY KEY,
  person_id UUID NOT NULL,
  display_name TEXT,
  endpoint_url TEXT NOT NULL,
  public_key TEXT,                 -- For message verification
  status TEXT DEFAULT 'active',
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

### 3.2 Coordination Protocol (Week 8-9)

#### Message Types

```python
# Scheduling coordination
SchedulingRequest:
  from_sakhi_id: str
  to_person_id: str
  event_type: "dinner" | "coffee" | "call" | "meeting"
  timeframe: "this week" | "next few days" | DateRange
  context: str  # "Alice wants to catch up"
  preferences: {...}  # Relevant preferences to share

AvailabilityResponse:
  from_sakhi_id: str
  windows: [{start, end, quality}]
  preferences: {...}  # Their relevant preferences

Proposal:
  from_sakhi_id: str
  datetime: timestamp
  location: {...}
  reasoning: str  # "Both free, both like Italian"

Confirmation:
  from_sakhi_id: str
  accepted: bool
  event_id: str  # Created event
```

#### Flow

```
Alice: "Dinner with Bob this week"
    │
    ▼
Alice's Sakhi ──────────────────────► Bob's Sakhi
              SchedulingRequest
    │
    │◄────────────────────────────────
              AvailabilityResponse
    │
    │ (Find intersection)
    │
    ▼
Alice's Sakhi ──────────────────────► Bob's Sakhi
              Proposal
    │
    │◄────────────────────────────────
              (Pending Bob's confirmation)
    │
Bob confirms
    │
    │◄────────────────────────────────
              Confirmation
    │
    ▼
Both calendars updated
```

---

### 3.3 Demo Experience (Week 9-10)

#### The Demo

Split screen. Two people. Their Sakhis coordinate.

```
┌─────────────────────────┬─────────────────────────┐
│         ALICE           │           BOB           │
├─────────────────────────┼─────────────────────────┤
│                         │                         │
│ "Sakhi, dinner with     │                         │
│  Bob this week"         │                         │
│                         │                         │
│    [Sakhis coordinate]  │    [Sakhis coordinate]  │
│                         │                         │
│ "Thursday 7pm at        │ "Alice wants dinner     │
│  Rosario's work for     │  Thursday 7pm at        │
│  both. Confirm?"        │  Rosario's. Confirm?"   │
│                         │                         │
│ "Yes"                   │ "Yes"                   │
│                         │                         │
│ "Done. On your          │ "Done. See you          │
│  calendar."             │  Thursday."             │
│                         │                         │
└─────────────────────────┴─────────────────────────┘

Total human effort: Two "yes" responses
```

---

## PHASE 4: Deepen & Expand

**Duration: Ongoing**
**Goal: Sakhi becomes proactive, handles more of life**

### 4.1 Action Loops

- Sakhi suggests based on patterns
- Tracks if you followed through
- Learns what works for YOU
- Feedback improves recommendations

### 4.2 Additional Execution

- Social media posting (draft → approve → post)
- Messaging coordination
- Service booking (restaurants, etc.)
- Buy/sell coordination (Sakhi-to-Sakhi commerce)

### 4.3 Knowledge Graph Deepening

- More personal pattern learning
- Seasonal awareness
- Circadian optimization
- Relationship health tracking

---

## Timeline Summary

| Phase | Weeks | Outcome |
|-------|-------|---------|
| **Phase 1** | 1-3 | Reflection complete — Sakhi truly knows you |
| **Phase 2** | 4-7 | Execution ready — Calendar, scheduling works |
| **Phase 3** | 8-10 | Mesh live — Sakhi-to-Sakhi coordination |
| **Phase 4** | 11+ | Expanding — More of life through Sakhi |

**Investor demo ready: Week 10**

---

## Success Metrics

### Phase 1 (Reflection)
- [ ] Relationship model populated for active users
- [ ] Scheduling preferences captured
- [ ] Knowledge graph has base + personal patterns
- [ ] Recommendations cite personal history

### Phase 2 (Execution)
- [ ] Users can manage calendar through conversation
- [ ] Events have reflective context attached
- [ ] Availability computation includes energy awareness

### Phase 3 (Mesh)
- [ ] Two Sakhis can coordinate scheduling
- [ ] Demo works reliably
- [ ] < 60 seconds from request to confirmation

---

## Open Questions

1. **Mesh hosting**: Central server or federated?
2. **Trust model**: How do Sakhis verify each other?
3. **Privacy boundaries**: What can another Sakhi learn about you?
4. **External calendar**: Sync in Phase 2 or defer?

---

## Progress Log

### January 31, 2026 - Phase 1 Started

#### Completed: Phase 1.1 - Relationship Model

**Files Created:**
- `infra/sql/20260131_phase1_relationships.sql` - Database migration
- `sakhi/apps/api/services/relationships/__init__.py`
- `sakhi/apps/api/services/relationships/repository.py` - CRUD operations
- `sakhi/apps/api/services/relationships/extraction.py` - LLM-based people extraction
- `sakhi/apps/api/services/relationships/enrichment.py` - Relationship enrichment from entries
- `sakhi/apps/api/routes/relationships.py` - API endpoints

**Capabilities Added:**
- Extract people mentioned in journal entries using LLM
- Store rich relationship data (type, closeness, context, patterns)
- Track last contact/seen timestamps
- Get relationships needing attention
- API endpoints for relationship management

#### Completed: Phase 1.2 - Scheduling Preferences

**Files Created:**
- `infra/sql/20260131_phase1_scheduling_preferences.sql` - Database migration
- `sakhi/apps/api/services/scheduling/__init__.py`
- `sakhi/apps/api/services/scheduling/preferences.py` - Preference management
- `sakhi/apps/api/routes/scheduling.py` - API endpoints

**Capabilities Added:**
- Store detailed scheduling preferences (times, locations, dining)
- Check if specific times are preferred
- Get scheduling context for Sakhi-to-Sakhi mesh
- Energy-aware scheduling preferences

#### Completed: Phase 1.3 - Knowledge Graph

**Files Created:**
- `infra/sql/20260131_phase1_personal_patterns.sql` - Personal patterns schema
- `sakhi/apps/api/services/ayurveda/causal_reasoning.py` - "Why am I feeling X?" queries
- `sakhi/apps/api/services/ayurveda/pattern_learning.py` - Personal pattern detection
- `sakhi/apps/api/routes/knowledge_graph.py` - API endpoints

**Capabilities Added:**
- Causal reasoning: Answer "Why am I feeling scattered/anxious/stuck?"
- Personal pattern learning: Detect user-specific cause-effect correlations
- Behavior and symptom extraction from journal entries
- Multi-hop causal chain tracing
- Symptom-to-dosha mapping
- Natural language explanations combining personal patterns + Ayurvedic knowledge

**Key Features:**
- `explain_symptom()` - Full "why" explanation for any symptom
- `explain_friction_state()` - Explain friction states with personal context
- `trace_causal_chain()` - Multi-hop tracing (anxiety → late_dinners → work_stress)
- `process_entry_for_patterns()` - Main hook for pattern learning from journals
- Pattern correlation strengthens with observations (logarithmic growth)

#### Completed: Phase 1.4 - Personalized Recommendations

**Files Created:**
- `infra/sql/20260131_phase1_recommendation_feedback.sql` - Feedback tracking
- `sakhi/apps/api/services/recommendations/__init__.py`
- `sakhi/apps/api/services/recommendations/context_builder.py` - Full context gathering
- `sakhi/apps/api/services/recommendations/generator.py` - Personalized generation

**Capabilities Added:**
- Rich context building: constitution + current state + patterns + history + temporal
- Personal effectiveness tracking: what's worked for YOU
- Recommendation scoring with personal boosts/penalties
- Natural language explanations: "This has worked well for you before"
- Feedback capture loop to improve future recommendations
- Urgency level computation (low → critical based on drift)
- Personalization confidence scoring

**API Endpoints:**
- `GET /recommendations/personalized/{person_id}` - Full personalized recommendations
- `GET /recommendations/personalized/{person_id}/context` - View context used
- `POST /recommendations/personalized/{person_id}/feedback` - Record feedback
- `GET /recommendations/personalized/{person_id}/effectiveness` - What's worked

---

## Phase 1 Complete ✓

All Phase 1 work is complete. Sakhi now:
- **Knows your relationships** - Who matters, context, patterns
- **Knows your preferences** - When, where, how you like to meet
- **Understands causality** - Why you feel the way you do
- **Personalizes recommendations** - Based on YOUR history, not generic advice

---

---

### January 31, 2026 - Phase 2 Started

#### Completed: Phase 2.1 - Sakhi Calendar

**Files Created:**
- `infra/sql/20260131_phase2_calendar.sql` - Database migration with calendar_events, availability_cache, calendar_attendees, scheduling_requests tables + helper functions
- `sakhi/apps/api/services/calendar/__init__.py` - Module exports
- `sakhi/apps/api/services/calendar/events.py` - Full CRUD operations for calendar events
- `sakhi/apps/api/services/calendar/availability.py` - Availability computation combining calendar + preferences + rhythm + operating system
- `sakhi/apps/api/services/calendar/scheduling.py` - Conversational scheduling interface with intent recognition and slot filling
- `sakhi/apps/api/routes/calendar.py` - API endpoints

**Capabilities Added:**
- Calendar event CRUD with Sakhi-native context (relationship context, energy requirements, coordination status)
- Availability windows with quality ratings: preferred, available, suboptimal, emergency_only
- Energy-aware scheduling based on dosha/operating system (Vata prefers morning grounding, Pitta avoids midday, Kapha benefits from early morning)
- Conversational scheduling with natural language intent detection (create, block, query, modify, cancel, find_time)
- Slot filling for event type, participants, timeframe, duration, location
- Week summary with energy predictions and relationship context
- Automatic availability cache invalidation on calendar changes

**API Endpoints:**
- `POST /calendar/events` - Create event
- `GET /calendar/events/{event_id}` - Get event
- `PATCH /calendar/events/{event_id}` - Update event
- `DELETE /calendar/events/{event_id}` - Delete event
- `GET /calendar/today` - Today's events with context
- `GET /calendar/week` - Week's events
- `GET /calendar/availability` - Get availability windows with quality ratings
- `POST /calendar/availability/check` - Check if specific time is available
- `POST /calendar/availability/find-times` - Find best times for an event
- `GET /calendar/summary` - Week summary with energy predictions

#### Completed: Phase 2.2 - Conversational Scheduling in Conversation Flow

**Files Modified:**
- `sakhi/apps/api/routes/turn_v2.py` - Added scheduling integration
- `sakhi/apps/api/services/conversation_v2/conversation_reasoner.py` - Added scheduling context to prompts

**Capabilities Added:**
- **Explicit Scheduling Detection**: Detects intents like "Schedule dinner with Alex this week"
- **Calendar Query Handling**: "What's my week look like?" returns events with relationship context
- **Journal Hint Detection**: Notices "should visit Mom" patterns and offers to help schedule
- **Relationship Nudges**: Surfaces people you haven't connected with recently (natural, not forced)
- **Time Suggestions with Quality**: Presents 2-3 optimal times with energy/quality reasoning
- **User Always Confirms**: Sakhi NEVER creates events without explicit "yes" from user

**User Experience:**
1. **Explicit Request**: User asks to schedule → Sakhi presents time options → User confirms → Event created
2. **Journal Hint**: User mentions wanting to see someone → Sakhi offers "Want me to help schedule that?"
3. **Relationship Nudge**: Sakhi naturally mentions "You haven't seen Alex in 6 weeks - want to reconnect?"
4. **Calendar Query**: User asks about schedule → Sakhi summarizes with relationship/energy context

**Critical Guard**: User is ALWAYS the final decision maker. Sakhi suggests, offers, and waits for confirmation.

#### Completed: Phase 2.3 - Confirmation Flow (End-to-End Scheduling)

**Files Modified:**
- `sakhi/apps/api/services/calendar/scheduling.py` - Added pending request management and confirmation detection
- `sakhi/apps/api/services/calendar/__init__.py` - Exported new functions
- `sakhi/apps/api/routes/turn_v2.py` - Added confirmation detection and execution
- `sakhi/apps/api/services/conversation_v2/conversation_reasoner.py` - Added confirmation acknowledgment

**Capabilities Added:**
- **Pending Request Tracking**: Scheduling requests saved to `scheduling_requests` table
- **Confirmation Detection**: Detects "yes", "confirm", "do it", "sounds good", "option 1/2/3", etc.
- **Automatic Event Creation**: When user confirms, event is created in calendar
- **Success Acknowledgment**: LLM acknowledges the created event with celebration

**End-to-End Flow:**
1. User: "Schedule dinner with Alex this week"
2. Sakhi: "Here are some options: Thursday 7pm (preferred), Friday 6pm (available)..."
3. Sakhi saves pending request to database
4. User: "Thursday works" or "yes" or "option 1"
5. Sakhi detects confirmation, looks up pending request
6. Sakhi creates calendar event
7. Sakhi: "Done! Dinner with Alex is now on your calendar for Thursday 7pm."

#### Completed: Phase 2.4 - Calendar UI in Web App

**Files Created:**
- `apps/web/app/experience/calendar/page.tsx` - Calendar page wrapper
- `apps/web/app/experience/calendar/client.tsx` - Calendar UI components
- `apps/web/app/api/calendar/today/route.ts` - Today's events API
- `apps/web/app/api/calendar/week/route.ts` - Week events API
- `apps/web/app/api/calendar/summary/route.ts` - Week summary API

**UI Components:**
- **Today/Week Toggle**: Switch between today's view and week view
- **Week Summary Card**: Shows event count, energy prediction, busiest day
- **Event Cards**: Display event with time, type badge, location, relationship context, energy notes
- **Week View**: Groups events by day with date headers
- **Empty State**: Friendly prompt to schedule something when no events
- **FAB**: Floating action button to schedule via conversation

**Design:**
- Matches existing Me page dark theme (palette, card styling, icons)
- Event type colors: meeting (indigo), social (green), personal (yellow), work (red), focus_time (teal), recovery (purple)
- Relationship context highlighted in accent color
- Energy notes shown with warning color
- Mobile-first responsive design

---

## Phase 2: COMPLETE

Sakhi Calendar is fully functional:
- Calendar schema with events, availability, attendees, scheduling requests
- Energy-aware availability computation based on dosha/operating system
- Conversational scheduling with natural language intent detection
- End-to-end confirmation flow (suggest → confirm → create)
- Web UI to view today/week events with relationship context

---

## Phase 3: COMPLETE

Sakhi-to-Sakhi Mesh is fully functional:

**Files:**
- `sakhi/apps/api/services/mesh/entities.py` - Entity management (people & businesses)
- `sakhi/apps/api/services/mesh/connections.py` - Connection and trust management
- `sakhi/apps/api/services/mesh/coordination.py` - Full coordination protocol
- `sakhi/apps/api/services/mesh/availability.py` - Privacy-respecting availability sharing
- `sakhi/apps/api/routes/mesh.py` - All mesh API endpoints
- Database: `sakhi_entities`, `coordination_threads`, `coordination_messages`, `sakhi_connections`

**Capabilities:**
- Sakhi Profile Management (create, update, search by handle)
- Connection Requests with Trust Levels (minimal, standard, full)
- Scheduling Coordination Protocol:
  - `initiate_coordination()` - Start scheduling with another Sakhi
  - `respond_to_proposal()` - Accept, counter-propose, or decline
  - Auto-find overlapping availability windows
  - Create calendar events for both parties on acceptance
- Conversation Flow Integration:
  - Detects when scheduling involves someone on Sakhi mesh
  - Shows mesh status and offers direct Sakhi-to-Sakhi coordination
- Multiple Coordination Types: scheduling, inquiry, transaction, booking, feedback

---

#### Completed: Phase 4c - Desktop Agent Protocol

**Files Created:**
- `sakhi/apps/desktop-agent/` - Full Electron application
- `apps/api/routes/agent.py` - Agent registration & heartbeat API
- `apps/api/services/agent/` - Sessions, actions, authentication
- Database: `registered_agents`, `agent_sessions`, `agent_actions`

**Capabilities:**
- Desktop Agent DMG installer for macOS
- Device linking via code (OAuth-style flow)
- macOS permissions handling (Accessibility, Screen Recording)
- Action execution: navigate, click, type, scroll, shortcuts
- Heartbeat polling for task assignment
- End-to-end tested: Agent opens browser on command

---

## Next Phase: DEMO BUILD

**See:** [SAKHI_DEMO_PLAN.md](./SAKHI_DEMO_PLAN.md) for full demo script.

---

## BUILD PLAN: Foundation + Five Capabilities

The demo requires **foundational memory improvements** plus **five technical capabilities**.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        SAKHI DEMO CAPABILITIES                               │
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │ 0. FOUNDATION: Hybrid Search (BM25 + Vector)                        │   │
│   │    Borrowed from OpenClaw — catches exact keyword matches           │   │
│   │    STATUS: BUILD FIRST (1 day)                                      │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐            │
│   │ 1. COMPUTER USE │  │ 2. MESH NETWORK │  │ 3. PERSONAL-    │            │
│   │    (Vision Loop)│  │    (Sakhi↔Sakhi)│  │    IZATION      │            │
│   │                 │  │                 │  │                 │            │
│   │ Browse Amazon   │  │ Personal:       │  │ Taste prefs     │            │
│   │ Read reviews    │  │   Mom's Sakhi   │  │ Sensory memory  │            │
│   │ Check Instagram │  │                 │  │ Food history    │            │
│   │ Make purchases  │  │ Business:       │  │ Memory links    │            │
│   │                 │  │   Restaurant    │  │                 │            │
│   │ STATUS: BUILD   │  │   Sakhi         │  │ STATUS: BUILD   │            │
│   └─────────────────┘  │                 │  └─────────────────┘            │
│                        │ STATUS: UI ONLY │                                  │
│   ┌─────────────────┐  └─────────────────┘  ┌─────────────────┐            │
│   │ 4. REFLECTIVE INTELLIGENCE              │ 5. DEMO UI      │            │
│   │    (Ayurveda + Patterns)                │    (Split Screen)│            │
│   │                                         │                  │            │
│   │ Causal reasoning ✅                     │ Personal coord   │            │
│   │ Pattern matching ✅                     │ Business coord   │            │
│   │ "Last time" lookup ⚠️                   │ Real-time sync   │            │
│   │ Ayurveda-food link ⚠️                   │                  │            │
│   │                                         │ STATUS: BUILD    │            │
│   │ STATUS: POLISH                          │                  │            │
│   └─────────────────┘                       └─────────────────┘            │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### CAPABILITY 0: Foundation — Hybrid Search (Borrowed from OpenClaw)

**What:** Add BM25 keyword search alongside vector similarity for better recall accuracy.

**Why:** Pure vector similarity misses exact matches. If user says "Manali cabin", we want EXACT match plus semantic similarity. OpenClaw uses 0.7 vector + 0.3 keyword weighting.

**Current State:**
- ✅ Vector similarity search via pgvector (cosine distance)
- ❌ No keyword/BM25 search
- ❌ No hybrid score merging

**Files to Modify:**

| File | Change | Priority |
|------|--------|----------|
| `sakhi/apps/api/services/memory/recall.py` | Add BM25 scoring + hybrid merge | P0 |
| `sakhi/apps/api/services/memory/bm25.py` | NEW: BM25 implementation for PostgreSQL | P0 |

**Implementation:**

```python
# bm25.py - NEW FILE
from typing import List, Tuple
from sakhi.apps.api.core.db import q as dbfetch

async def bm25_search(
    person_id: str,
    query: str,
    limit: int = 20,
) -> List[Tuple[str, float]]:
    """
    BM25 keyword search using PostgreSQL ts_rank.

    Returns list of (source_id, bm25_score) tuples.
    """
    # Use PostgreSQL full-text search with ts_rank
    rows = await dbfetch(
        """
        SELECT
            id,
            ts_rank_cd(
                to_tsvector('english', content),
                plainto_tsquery('english', $2)
            ) as rank
        FROM journal_entries
        WHERE person_id = $1
          AND to_tsvector('english', content) @@ plainto_tsquery('english', $2)
        ORDER BY rank DESC
        LIMIT $3
        """,
        person_id,
        query,
        limit,
    )
    return [(str(r["id"]), float(r["rank"])) for r in (rows or [])]


# recall.py - MODIFY recall_advanced()
async def recall_advanced(
    person_id: str,
    query: str,
    k: int = 8,
    vector_weight: float = 0.7,
    keyword_weight: float = 0.3,
) -> List[RecallItem]:
    """
    Hybrid recall: vector similarity + BM25 keyword matching.

    Borrowed from OpenClaw's hybrid search approach.
    """
    from sakhi.apps.api.services.memory.bm25 import bm25_search

    # 1. Vector similarity search (existing)
    query_vec = await embed_text(query)
    vector_results = await _fetch_vector_matches(person_id, query_vec, limit=k*3)

    # 2. BM25 keyword search (NEW)
    keyword_results = await bm25_search(person_id, query, limit=k*3)
    keyword_scores = {id: score for id, score in keyword_results}

    # 3. Merge scores with weighting
    combined = {}
    for item in vector_results:
        vec_score = item.similarity
        kw_score = keyword_scores.get(item.id, 0.0)
        combined[item.id] = (
            vector_weight * vec_score +
            keyword_weight * kw_score,
            item
        )

    # 4. Sort by combined score, apply diversity filter
    sorted_items = sorted(combined.values(), key=lambda x: x[0], reverse=True)

    # 5. Return top k with diversity
    return _apply_diversity_filter([item for _, item in sorted_items], k)
```

**Also Add: Memory Flush Before Context Compaction**

```python
# conversation.py or similar - add before context compaction
async def flush_important_context(
    person_id: str,
    conversation_history: List[Dict],
    threshold_tokens: int = 4000,
):
    """
    Auto-persist important information before context window fills.
    Borrowed from OpenClaw's memory flush pattern.
    """
    if estimate_tokens(conversation_history) > threshold_tokens:
        # Extract key insights from recent turns
        insights = await extract_insights_for_persistence(conversation_history[-10:])

        # Write to memory graph as nodes
        for insight in insights:
            await create_memory_node(
                person_id=person_id,
                kind="insight",
                label=insight.summary[:80],
                data={"full_text": insight.text, "auto_flushed": True},
            )
```

**Effort:** 1 day

**Success Criteria:**
- Query "Manali cabin" returns exact match first (not just semantically similar)
- Query "khichdi Annapurna" finds exact restaurant+dish match
- Recall quality improves for specific names, places, foods

---

### CAPABILITY 1: Computer Use (Vision Loop)

**What:** Sakhi autonomously browses the web, reads content, makes decisions, executes actions.

**Demo Use Cases:**
- Browse Amazon/Flipkart for products
- Read reviews, compare options
- Check Instagram for recommendations
- Make purchases based on preferences

**Current State:**
- ✅ Desktop Agent installed and registered
- ✅ Basic actions work: navigate, click, type, scroll
- ❌ No autonomous reasoning loop
- ❌ No screenshot → decision → action cycle

**Architecture:**
```
User Request → Planner → Vision Loop
                              ↓
                    ┌─────────────────────┐
                    │   VISION LOOP       │
                    │                     │
                    │  1. Capture screen  │
                    │  2. Send to Claude  │
                    │  3. Claude decides: │
                    │     - What to click │
                    │     - What to type  │
                    │     - Task complete?│
                    │  4. Execute action  │
                    │  5. Repeat          │
                    │                     │
                    └─────────────────────┘
```

**Files to Create:**

| File | Purpose | Priority |
|------|---------|----------|
| `sakhi/apps/api/services/agent/vision_loop.py` | Core vision loop orchestrator | P0 |
| `sakhi/apps/api/services/agent/screen_analyzer.py` | Screenshot → Claude analysis | P0 |
| `sakhi/apps/api/services/agent/action_decider.py` | Claude decides next action | P0 |
| `sakhi/apps/api/routes/agent.py` (extend) | New endpoints for loop control | P1 |

**Key Functions:**

```python
# vision_loop.py
async def start_vision_loop(
    person_id: str,
    task: str,
    preferences: Dict[str, Any],  # User's taste, constraints
    max_iterations: int = 20,
) -> VisionLoopResult:
    """
    Autonomous browsing loop.

    1. Capture screenshot from agent
    2. Send to Claude with task + preferences
    3. Claude returns: action OR "task_complete"
    4. Execute action via agent
    5. Repeat until complete or max iterations
    """

# screen_analyzer.py
async def analyze_screen(
    screenshot_base64: str,
    task: str,
    history: List[str],  # Previous actions taken
    preferences: Dict[str, Any],
) -> ScreenAnalysis:
    """
    Claude analyzes screenshot and returns:
    - Current page understanding
    - Relevant items found
    - Recommended next action
    - Task completion status
    """

# action_decider.py
async def decide_action(
    analysis: ScreenAnalysis,
    available_actions: List[str],
) -> AgentAction:
    """
    Convert Claude's recommendation to executable action.
    """
```

**Effort:** 3-4 days

---

### CAPABILITY 2: Mesh Network (Sakhi-to-Sakhi)

**What:** Sakhis coordinate with each other for personal and business relationships.

**Demo Use Cases:**
- Personal: Your Sakhi ↔ Mom's Sakhi (schedule time together)
- Business: Your Sakhi ↔ Restaurant's Sakhi (order food with preferences)

**Current State:**
- ✅ Mesh protocol fully built (coordination, trust levels, availability)
- ✅ Database tables exist
- ❌ No demo UI for split-screen visualization
- ❌ No mock business Sakhi (restaurant dashboard)

**Files to Create:**

| File | Purpose | Priority |
|------|---------|----------|
| `apps/web/app/demo/coordination/page.tsx` | Split-screen personal mesh demo | P0 |
| `apps/web/app/demo/restaurant/page.tsx` | Restaurant Sakhi dashboard | P0 |
| `apps/web/app/demo/components/SakhiChat.tsx` | Reusable Sakhi chat UI | P1 |
| `apps/web/app/demo/components/MeshConnection.tsx` | Visual connection animation | P1 |
| `apps/api/routes/demo.py` | Demo-specific endpoints (mock data) | P1 |

**Demo UI Structure:**

```
┌─────────────────────────────────────────────────────────────────┐
│                 PERSONAL MESH DEMO (Act 2)                       │
│                                                                  │
│  ┌─────────────────────┐    ═══════    ┌─────────────────────┐  │
│  │   YOUR SAKHI        │    ↔ mesh ↔   │   MOM'S SAKHI       │  │
│  │                     │    ═══════    │                     │  │
│  │ "Plan something     │               │ "Your son wants to  │  │
│  │  with Mom"          │               │  spend time..."     │  │
│  │                     │               │                     │  │
│  │ [Chat interface]    │               │ [Chat interface]    │  │
│  │                     │               │                     │  │
│  └─────────────────────┘               └─────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                 BUSINESS MESH DEMO (Act 3)                       │
│                                                                  │
│  ┌─────────────────────┐    ═══════    ┌─────────────────────┐  │
│  │   YOUR SAKHI        │    ↔ mesh ↔   │   ANNAPURNA'S SAKHI │  │
│  │                     │    ═══════    │   (Restaurant)      │  │
│  │ "Order food for     │               │                     │  │
│  │  dinner"            │               │ Guest Profile:      │  │
│  │                     │               │ - Prefers mild      │  │
│  │ [Chat interface]    │               │ - No dairy          │  │
│  │                     │               │ - Loves khichdi     │  │
│  │                     │               │                     │  │
│  └─────────────────────┘               └─────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

**Effort:** 2-3 days

---

### CAPABILITY 3: Personalization Engine

**What:** Sakhi knows user's taste, sensory preferences, food history, and links to memories.

**Demo Use Cases:**
- "Find a car perfume that suits my taste" → knows scent preferences
- "Order food" → knows spice tolerance, dietary restrictions
- Connect products to memories ("like that cabin in Manali")

**Current State:**
- ✅ Memory graph exists (memory_nodes, memory_edges)
- ✅ Relationship context works
- ⚠️ Sensory preferences not structured
- ❌ Food preference memory not built
- ❌ Product → memory association not built

**Files to Create/Extend:**

| File | Purpose | Priority |
|------|---------|----------|
| `sakhi/apps/api/services/memory/preferences.py` | NEW: Structured preference storage | P0 |
| `sakhi/apps/api/services/memory/food.py` | NEW: Food/restaurant memory | P0 |
| `sakhi/apps/api/services/memory/graph.py` (extend) | Add preference node types | P1 |
| `sakhi/apps/api/services/ayurveda/food_reco.py` | NEW: Dosha-aware food recommendations | P1 |

**Data Model:**

```python
# preferences.py
class SensoryPreference(BaseModel):
    """User's sensory preferences."""
    category: str  # scent, taste, texture, sound, visual
    likes: List[str]  # "woody", "sandalwood", "subtle"
    dislikes: List[str]  # "strong florals", "synthetic"
    memories: List[str]  # memory_node IDs this connects to
    notes: str  # "sensitive to overpowering scents"

class TasteProfile(BaseModel):
    """User's taste preferences."""
    spice_tolerance: str  # none, mild, medium, hot, very_hot
    dietary: List[str]  # vegetarian, no_dairy, gluten_free
    cuisines_loved: List[str]
    cuisines_avoided: List[str]
    favorite_dishes: List[Dict]  # {dish, restaurant, last_ordered}

# food.py
class FoodMemory(BaseModel):
    """Memory of food experiences."""
    dish: str
    restaurant: str
    rating: int  # 1-5
    notes: str  # "loved it", "too spicy"
    dosha_state_when_eaten: Optional[str]
    how_felt_after: Optional[str]  # "energized", "heavy", "satisfied"
```

**Key Functions:**

```python
async def get_preferences_for_task(
    person_id: str,
    task_type: str,  # "shopping", "food", "activity"
) -> Dict[str, Any]:
    """
    Get relevant preferences for a task.
    Used by Vision Loop to guide product selection.
    """

async def match_product_to_preferences(
    product_description: str,
    preferences: Dict[str, Any],
    memories: List[MemoryNode],
) -> ProductMatch:
    """
    Score how well a product matches user's taste.
    Include memory associations ("like Manali cabin").
    """

async def recommend_food_for_state(
    person_id: str,
    dosha_state: DoshaState,
    dietary_restrictions: List[str],
) -> List[FoodRecommendation]:
    """
    Ayurveda-aware food recommendations.
    """
```

**Effort:** 2-3 days

---

### CAPABILITY 4: Reflective Intelligence (Polish)

**What:** Sakhi explains patterns, finds "last time this happened", connects dots.

**Demo Use Cases:**
- "Why am I feeling scattered?" → shows Vata pattern, contributing factors
- "Last time this happened" → finds similar episode, what helped
- Seamless multi-action from insights

**Current State:**
- ✅ Causal reasoning engine built
- ✅ Pattern learning works
- ⚠️ "Last time" lookup needs polish
- ⚠️ Multi-action execution needs smoothing
- ❌ Pattern visualization not built

**Files to Extend:**

| File | Purpose | Priority |
|------|---------|----------|
| `sakhi/apps/api/services/ayurveda/causal_reasoning.py` | Enhance "last time" lookup | P0 |
| `sakhi/apps/api/services/agentic/planner.py` | Smooth multi-action execution | P1 |
| `apps/web/app/experience/reflect/page.tsx` | NEW: Pattern visualization UI | P2 |

**Enhancements Needed:**

```python
# causal_reasoning.py - enhance find_similar_episodes
async def find_similar_episodes(
    person_id: str,
    current_state: DoshaState,
    current_symptoms: List[str],
) -> List[SimilarEpisode]:
    """
    Find past episodes where user felt similar.

    Returns:
    - When it happened
    - What the state was
    - What interventions were tried
    - What worked (from feedback)
    - How long until recovery
    """

# Add intervention tracking
async def track_intervention_outcome(
    person_id: str,
    intervention: str,  # "evening walk", "sesame oil", "called sister"
    started_at: datetime,
    outcome: str,  # "helped", "no_effect", "made_worse"
    notes: str,
):
    """Track what actually helps this person."""
```

**Effort:** 1-2 days

---

### CAPABILITY 5: Demo UI Framework

**What:** Unified demo experience with split-screen, real-time updates, smooth transitions.

**Files to Create:**

| File | Purpose | Priority |
|------|---------|----------|
| `apps/web/app/demo/page.tsx` | Demo launcher / home | P0 |
| `apps/web/app/demo/layout.tsx` | Demo-specific layout | P0 |
| `apps/web/app/demo/act1/page.tsx` | Computer use demo | P1 |
| `apps/web/app/demo/act2/page.tsx` | Personal mesh demo | P1 |
| `apps/web/app/demo/act3/page.tsx` | Business mesh demo | P1 |
| `apps/web/app/demo/act4/page.tsx` | Reflective demo | P1 |
| `apps/web/lib/demo-state.ts` | Demo state management | P1 |

**Effort:** 2 days

---

## BUILD SCHEDULE

### Week 1: Foundation + Core Capabilities

| Day | Task | Owner | Deliverable |
|-----|------|-------|-------------|
| **1** | **Hybrid Search (Cap 0)** | - | `bm25.py` + modified `recall.py` |
| 1-2 | Vision Loop core | - | `vision_loop.py` working |
| 2-3 | Screen analyzer + action decider | - | Screenshot → action pipeline |
| 3-4 | Preference engine | - | `preferences.py`, `food.py` |
| 4-5 | Integration testing | - | Vision loop uses preferences |

### Week 2: Demo UI + Polish

| Day | Task | Owner | Deliverable |
|-----|------|-------|-------------|
| 1-2 | Split-screen demo UI | - | Personal mesh demo works |
| 2-3 | Restaurant Sakhi dashboard | - | Business mesh demo works |
| 3 | Reflective intelligence polish | - | "Last time" works well |
| 4-5 | End-to-end demo flow | - | All 4 acts runnable |

---

## DEPENDENCIES

```
┌─────────────────────────────────────────────────────────────────┐
│                    FOUNDATION (Day 1)                            │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Hybrid Search: BM25 + Vector (borrowed from OpenClaw)   │    │
│  │ - Improves recall for exact matches ("Manali cabin")    │    │
│  │ - All capabilities benefit from better memory recall    │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
                    ┌─────────────────┐
                    │ Preference      │
                    │ Engine (Cap 3)  │
                    └────────┬────────┘
                             │
                             ▼
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│ Vision Loop     │───│ Demo UI         │───│ Reflective      │
│ (Cap 1)         │   │ (Cap 5)         │   │ Intel (Cap 4)   │
└─────────────────┘   └────────┬────────┘   └─────────────────┘
                               │
                               ▼
                    ┌─────────────────┐
                    │ Mesh UI         │
                    │ (Cap 2)         │
                    └─────────────────┘
```

**Critical Path:** Hybrid Search → Vision Loop → Preferences → Demo UI

---

## SUCCESS CRITERIA

| Capability | Success Metric |
|------------|----------------|
| Computer Use | Sakhi browses Amazon, finds product matching taste, in < 10 iterations |
| Mesh (Personal) | Split screen shows coordination in real-time |
| Mesh (Business) | Restaurant sees guest preferences, suggests order |
| Personalization | Product recommendations feel "that's so me" |
| Reflective | "Last time" finds relevant episode with what helped |
| Demo Flow | All 4 acts run smoothly in sequence |

---

## RISK MITIGATION

| Risk | Mitigation |
|------|------------|
| Vision loop too slow | Pre-capture screenshots, optimize prompts |
| Claude vision inaccurate | Add retry logic, human-in-loop fallback |
| Mesh demo too complex | Simplify to 2-message exchange |
| Preferences feel generic | Seed with rich demo data |

---

### The Pitch

> **"Sakhi knows you. The world comes to you."**

Not your browsing history. Not your likes. **YOU.**
- Your taste (Computer Use + Personalization)
- Your relationships (Mesh - Personal)
- Your body (Mesh - Business + Ayurveda)
- Your patterns (Reflective Intelligence)

Focus on what matters: health, joy, connection.

---

*Document created: January 2026*
*Last updated: January 31, 2026*
*Phase 1: COMPLETE*
*Phase 2: COMPLETE*
*Phase 3: COMPLETE*
*Phase 4c: COMPLETE (Desktop Agent)*
*Next: Demo Build - Foundation + 5 Capabilities*
*  - Cap 0: Hybrid Search (BM25 + Vector) - FOUNDATION (borrowed from OpenClaw)*
*  - Cap 1: Vision Loop (Computer Use) - BUILD*
*  - Cap 2: Mesh UI (Split Screen) - BUILD*
*  - Cap 3: Personalization Engine - BUILD*
*  - Cap 4: Reflective Intelligence - POLISH*
*  - Cap 5: Demo UI Framework - BUILD*
*Vision: Sakhi knows you. The world comes through Sakhi. Matched to you.*
