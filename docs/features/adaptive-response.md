# Adaptive Response Framework

## Overview

The Adaptive Response Framework is Sakhi's approach to forming intelligent, personalized responses. Instead of generic replies or overwhelming users with possibilities, Sakhi responds like a skilled Ayurvedic practitioner:

1. **Constitution-aware** — Uses the user's Operating System (dosha baseline) to prioritize likely causes
2. **Memory-informed** — Loads what we already know BEFORE forming questions
3. **Personally targeted inquiry** — LLM generates questions specific to THIS person's situation and gaps
4. **Domain-adaptive** — Adjusts approach based on whether the concern is Body, Mind, or Life

**Core Principle:** Never ramble with 10 possibilities. Load everything we know about this person, then ask only about what we genuinely don't know yet.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      ADAPTIVE RESPONSE PIPELINE                              │
└─────────────────────────────────────────────────────────────────────────────┘

User Message: "I keep getting headaches recently"
     │
     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  1. SENSING LAYER                                                            │
│     ├── Domain Classification (Body/Mind/Life)                               │
│     ├── Symptom/Topic Extraction                                             │
│     ├── Temporal Markers (recently, always, sometimes)                       │
│     ├── Tone Detection (seeking help, venting, exploring)                    │
│     └── Specificity Assessment (vague vs detailed)                           │
│                                                                              │
│     Output: SenseFrame                                                       │
└─────────────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  2. KNOWLEDGE GAP ANALYSIS  (context first, then questions)                  │
│     ├── Load constitution + state vectors  ──┐                              │
│     ├── Fetch recent STM entries (10)        ├─ parallel                    │
│     ├── Load deterministic intelligence:     ┘                              │
│     │     ├── personal_patterns (cause→effect chains)                       │
│     │     ├── behavior_log (recent dosha-affecting actions)                 │
│     │     ├── symptom_log (past episodes, what helped)                      │
│     │     └── symptom→dosha mapping                                         │
│     ├── Search episodic memory for older relevant facts                      │
│     ├── Generate inferences from drift + patterns + guna                    │
│     └── LLM generates personalized questions using ALL above context        │
│                                                                              │
│     Output: KnowledgeGap { known, inferred, personalized_questions }        │
└─────────────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  3. RESPONSE STRATEGY SELECTION                                              │
│     ├── If questions empty → RESPOND mode (enough info)                     │
│     ├── If questions exist → INQUIRY or CONNECT_AND_INQUIRE mode            │
│     ├── Select max 2 questions to ask                                       │
│     └── Choose response template                                             │
│                                                                              │
│     Output: ResponseStrategy { mode, questions, template }                   │
└─────────────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  4. CONTEXT SYNTHESIS                                                        │
│     ├── Compress known facts into prompt-ready format                        │
│     ├── Frame inferences with appropriate confidence                         │
│     ├── Symptom protocol from knowledge graph (+ LLM fallback)              │
│     ├── Include constitution-specific guidance                               │
│     └── Add response guardrails                                              │
│                                                                              │
│     Output: SynthesizedContext                                               │
└─────────────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  5. RESPONSE FORMATION                                                       │
│     ├── Apply template: ACKNOWLEDGE → CONNECT → INQUIRE/RESPOND             │
│     ├── Tone calibration based on SenseFrame                                 │
│     └── LLM generation with synthesized context                              │
│                                                                              │
│     Output: Response                                                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 1. Sensing Layer

### Domain Classification

Every user message is classified into a primary domain:

| Domain | Keywords/Patterns | Sub-domains |
|--------|-------------------|-------------|
| **BODY** | headache, pain, sleep, tired, energy, digestion, skin | Head, Digestion, Sleep, Energy, Skin, General |
| **MIND** | anxious, worried, stressed, overwhelmed, focus, clarity | Anxiety, Stress, Focus, Mood, Motivation |
| **LIFE** | goal, plan, career, relationship, purpose, decision | Direction, Work, Relationships, Growth |

### SenseFrame Output

```python
@dataclass
class SenseFrame:
    domain: str                    # "body"
    sub_domain: str                # "head_neurological"
    symptom: str                   # "headaches"
    temporal: str                  # "recurring" | "acute" | "chronic"
    tone: str                      # "seeking_help" | "venting" | "exploring"
    specificity: str               # "low" | "medium" | "high"
    urgency: str                   # "low" | "medium" | "high"
    keywords: List[str]            # ["headaches", "recently", "keep"]
```

---

## 2. Knowledge Gap Analysis

### Core Principle: Context First, Then Questions

The knowledge gap stage **loads everything we know about this person first**, then asks an LLM to generate questions about genuine gaps. This inversion (context → questions, not questions → filter) means:

- Questions are inherently personalized — the LLM sees the full picture
- No keyword whack-a-mole — no need to maintain keyword lists for every possible symptom
- Any symptom gets questions — not limited to pre-built diagnostic paths

### Data Loading (Parallel)

Three groups of queries run concurrently via `asyncio.gather`:

#### Constitution + State Vectors

From `personal_model` and `memory_episodic`:

| Data | Source | Usage |
|------|--------|-------|
| `operating_system.type` | `personal_model` | Frame responses (e.g., "Conservation OS") |
| `operating_system.dosha_baseline` | `personal_model` | {vata, pitta, kapha} percentages |
| `life_context` | `personal_model` | Age, roles, life_phase |
| `state_vector.dosha` | `memory_episodic` (latest) | Detect drift from baseline |
| `guna_vector` | `memory_episodic` (latest) | Operating mode (sattva/rajas/tamas) |

State vectors are compared against the dosha baseline to compute **drift** — e.g., "vata elevated 8% from baseline." Drift feeds into the inference engine.

#### Recent Short-Term Memory (Keyword-Free)

From `memory_short_term` — the 10 most recent entries, **without keyword filtering**:

```python
async def _fetch_recent_stm(person_id: str, limit: int = 10) -> List[str]:
    """Fetch N most recent STM entries — LLM decides relevance."""
    rows = await q(
        "SELECT text FROM memory_short_term WHERE user_id = $1 ORDER BY created_at DESC LIMIT $2",
        person_id, limit,
    )
    # Deduplicate and return
```

**Why no keywords?** Keyword matching is brittle — "hydrate" doesn't match "hydrating", and topic selection can't anticipate every symptom. By fetching recent context and letting the LLM decide relevance, we avoid false negatives.

#### Deterministic Intelligence

Loaded via `_load_deterministic_intelligence()` — queries the Ayurvedic causal reasoning layer for structured, high-confidence data:

| Data | Source | What It Provides |
|------|--------|------------------|
| Personal patterns | `personal_patterns` table | "skipped_exercise → scattered (3x, 71%)" |
| Recent behaviors | `behavior_log` table (7 days) | "caffeine_evening (aggravates vata)" |
| Past symptom episodes | `symptom_log` table | "scattered 3 days ago, severity 0.7, meditation helped" |
| Symptom→dosha mapping | `SYMPTOM_DOSHA_MAP` (causal_reasoning.py) | "scattered = vata" |

Pattern query uses `ILIKE` on `effect_value` across all `effect_type` categories (mental, emotional, physical) so it catches patterns regardless of how they were originally classified.

**Integration:** `_integrate_deterministic_intelligence()` converts raw DB data into structured `KnownFact` and `Inference` objects:

- **Personal patterns** → `Inference` (topic="personal_pattern", basis="personal_patterns") — learned cause→effect correlations with observation count and Ayurvedic explanation
- **Recent behaviors** → `KnownFact` (topic="recent_behavior", source="behavior_log") — concrete dosha-affecting actions
- **Past episodes** → `KnownFact` (topic="past_episode", source="symptom_log") — includes what helped/didn't help (JSONB parsing)
- **Symptom→dosha** → `Inference` (topic="symptom_classification", basis="symptom_dosha_map")

**Graceful degradation:** If any table is empty (new users) or queries fail, the pipeline continues with whatever data is available. Questions just become less targeted.

**Data population:** These tables are populated per conversation turn by the `preference_learning` worker:
```
turn_v2.py → enqueue "preference_learning" job
→ _handle_preference_learning() → Phase 3: process_entry_for_patterns()
  → extract_behaviors_and_symptoms() (LLM)
  → log_behavior() → behavior_log
  → log_symptom() → symptom_log
  → detect_patterns() → personal_patterns
```
Plus daily/weekly/monthly crystallization strengthens recurring patterns.

### Supplementary: Episodic Memory Search

After the primary STM fetch, a keyword-based episodic search runs for **older relevant memories** using `recall_advanced` (embedding-based). This uses `TOPIC_KEYWORDS` to find topic-specific facts from beyond the recent STM window.

### Inference Engine

Generates inferences from dosha drift and guna mode:

| Signal | Inference |
|--------|-----------|
| Vata elevated > 5% | "May indicate irregularity, anxiety, or overstimulation" |
| Pitta elevated > 5% | "May indicate intensity, heat, or frustration" |
| Kapha elevated > 5% | "May indicate sluggishness or stagnation" |
| Rajas dominant | "High activation, may be pushing or stressed" |
| Tamas dominant | "Low energy, may be depleted or withdrawn" |

### LLM Question Generation

All loaded context flows into `generate_personalized_questions()`:

```python
async def generate_personalized_questions(
    sense: SenseFrame,
    constitution: ConstitutionContext,
    known: Dict[str, KnownFact],
    inferred: Dict[str, Inference],
) -> List[DiagnosticQuestion]:
    """LLM generates 2-3 questions about genuine gaps."""
```

The LLM prompt includes structured sections:
- Constitution (OS type, dominant dosha)
- **Recent things they've told us** — recent STM conversation entries
- **Recent behaviors (last 7 days)** — from behavior_log (e.g., "caffeine_evening (aggravates vata)")
- **Past episodes of this symptom** — from symptom_log (what helped/didn't)
- **Known wellness context** — topic-specific memories from episodic search
- **Learned personal patterns** — from personal_patterns (e.g., "caffeine → scattered, 8x, 80%")
- **Symptom classification** — deterministic dosha mapping
- **Current state** — drift/guna inferences from state vectors
- The user's current message and concern
- Explicit instruction: "Do NOT ask about things we already know"

### Knowledge Gap Output

```python
@dataclass
class KnowledgeGap:
    known: Dict[str, KnownFact]        # What we already know
    inferred: Dict[str, Inference]      # What we can deduce
    unknown: List[DiagnosticQuestion]   # Personalized questions from LLM
    constitution: ConstitutionContext
```

---

## 3. Diagnostic Knowledge Base

### Role Change (February 2026)

The Diagnostic Knowledge Base (`diagnostic_kb.py`) previously drove question generation with static `DIAGNOSTIC_PATHS`. As of February 2026, **question generation is handled by the LLM** (see Section 2). The knowledge base now serves two purposes:

1. **Protocol path** (Stage 4) — `get_symptom_from_sense()` → `match_symptom()` → `get_symptom_insight()` provide constitution-specific guidance for response synthesis
2. **Constitution guidance** — `get_constitution_guidance()` provides dosha-specific tone, likely causes, and things to avoid

### Symptom Routing

`get_symptom_from_sense()` routes symptoms through a three-tier fallback:

```
1. DIAGNOSTIC_PATHS match     (8 symptoms: headache, sleep, anxiety, etc.)
2. SYMPTOM_DOSHA_MAP match    (48 symptoms from causal_reasoning.py)
3. Domain default             (body→energy, mind→stress, life→work)
```

This routing is used by the **protocol path** in Stage 4 to find constitution-specific insights, not for question generation.

### Constitution Guidance (Still Active)

The knowledge base provides dosha-specific response guidance:

| Dosha | Likely Causes | Tone | Avoid Suggesting |
|-------|---------------|------|------------------|
| **Vata** | anxiety, irregular routine, cold/dry, overstimulation | Grounding, calming | Intense exercise, stimulants |
| **Pitta** | intensity, heat, skipped meals, overwork | Cooling, measured | More pushing, competition |
| **Kapha** | sinus, sluggishness, oversleep, heavy food | Energizing, clear | More rest, heavy foods |

### DIAGNOSTIC_PATHS (Reference Only)

The 8 pre-built diagnostic paths (headaches, sleep, anxiety, energy, digestion, skin, stress, mood) remain in code for reference and constitution guidance lookups. They are **no longer used for question generation** — that's handled by `generate_personalized_questions()` in `knowledge_gap.py`.

---

## 4. Response Strategy

### Mode Selection

```python
def select_response_mode(knowledge_gap: KnowledgeGap) -> str:
    critical_unknowns = [q for q in knowledge_gap.unknown if q.priority == "high"]

    if len(critical_unknowns) == 0:
        return "RESPOND"  # Enough info to provide guidance
    elif len(knowledge_gap.known) > 0:
        return "CONNECT_AND_INQUIRE"  # Reference what we know, ask targeted questions
    else:
        return "INQUIRE"  # Need more info before responding
```

### Response Templates

#### Template: INQUIRE (First Interaction, Little Data)

```
[ACKNOWLEDGE] {symptom} can tell us a lot.
[FRAME] Given your nature, I'd want to understand a bit more.
[ASK] {question_1}? {question_2}?
```

Example:
> "Headaches can tell us a lot. Given your nature, I'd want to understand a bit more. Is the pain more sharp and concentrated, or dull and heavy? And does it tend to come on after intense focus or when you're feeling scattered?"

#### Template: CONNECT_AND_INQUIRE (Has History)

```
[ACKNOWLEDGE] {symptom} again...
[CONNECT] I notice {known_fact_1} and {known_fact_2} - both can contribute for your system.
[ASK] {question_1}?
```

Example:
> "Headaches again... I notice sleep has been rough lately and you've been skipping meals during busy stretches. For your system, that combination often shows up as head tension. Has the sleep improved at all?"

#### Template: RESPOND (Enough Info)

```
[ACKNOWLEDGE] {symptom} makes sense given what you've shared.
[INSIGHT] For someone with your pattern, this often happens when {constitution_specific_cause}.
[SUGGESTION] {actionable_suggestion}
[CHECK] Does that resonate?
```

---

## 5. Context Synthesis

### Prompt Assembly

The final prompt to the LLM includes:

```python
@dataclass
class SynthesizedContext:
    # User's constitutional frame
    constitution: str                    # "Pitta-dominant (45% pitta, 30% vata)"
    operating_mode: str                  # "Rajas-dominant (activation mode)"

    # What we know
    known_facts: List[str]              # ["sleep has been poor", "skipping meals"]
    inferences: List[str]               # ["pitta elevated +7% from baseline"]

    # Current symptom context
    domain: str                          # "body"
    symptom: str                         # "headaches"
    symptom_characteristics: Dict        # Any details they've shared

    # Response guidance
    likely_causes: List[str]            # ["intensity", "heat", "meals"]
    tone_guidance: str                   # "cooling, measured"
    avoid_suggesting: List[str]         # ["pushing harder"]

    # Questions to ask (if INQUIRY mode)
    questions_to_ask: List[str]         # ["pain quality", "timing"]

    # Guardrails
    guardrails: List[str]               # ["no diagnosis", "max 2 questions"]
```

### LLM Prompt Structure

```
You are Sakhi, an Ayurvedic-informed clarity companion.

USER CONSTITUTION:
- Operating System: {constitution.type} ({constitution.dosha_baseline})
- Current State: {constitution.operating_mode}
- Drift: {constitution.drift_summary}

WHAT WE KNOW:
{formatted_known_facts}

CURRENT CONCERN:
- Domain: {domain}
- Symptom: {symptom}
- Temporal: {temporal}

RESPONSE GUIDANCE:
- Mode: {response_mode}
- For their constitution, likely contributors: {likely_causes}
- Tone: {tone_guidance}
- Avoid suggesting: {avoid_suggesting}

{if INQUIRY mode}
QUESTIONS TO ASK (pick max 2):
{formatted_questions}
{endif}

GUARDRAILS:
- Never list multiple possibilities. Pick most likely based on constitution.
- Maximum 2 questions per response.
- Reference known facts, don't re-ask.
- No diagnosis or medical claims.
- Stay warm, grounded, practical.

USER MESSAGE:
{user_message}

Respond using the template: ACKNOWLEDGE → CONNECT (if data exists) → INQUIRE/RESPOND
```

---

## 6. Domain-Specific Adaptations

### BODY Domain

| Aspect | Approach |
|--------|----------|
| Questions | Physical, sensory (sharp/dull, location, timing) |
| Memory Search | Sleep, meals, exercise, physical symptoms |
| Constitution Role | HIGH — different doshas manifest differently |
| Tone | Practical, embodied, grounded |

### MIND Domain

| Aspect | Approach |
|--------|----------|
| Questions | Emotional, cognitive (when, what triggers, how it feels) |
| Memory Search | Emotional patterns, stress mentions, life events |
| Constitution Role | MEDIUM — patterns vary but less physical |
| Tone | Validating, spacious, reflective |

### LIFE Domain

| Aspect | Approach |
|--------|----------|
| Questions | Values, priorities, constraints |
| Memory Search | Goals, decisions, life context |
| Constitution Role | LOW — more about preferences than constitution |
| Tone | Clarifying, future-oriented, supportive |

---

## 7. Implementation Phases

### Phase 1: MVP (Complete)

1. **Sensing Layer** — LLM-powered domain classification + symptom extraction
2. **Knowledge Gap** — Constitution loading + state vectors + memory search
3. **Response Strategy** — INQUIRE / CONNECT_AND_INQUIRE / RESPOND modes
4. **Templates** — 3 response templates with tone adaptation

### Phase 2: LLM-Powered Questions (Complete — February 2026)

1. **Inverted flow** — Load personal context first, then generate questions via LLM
2. **Keyword-free STM** — Recent memory fetched without keyword filtering
3. **SYMPTOM_DOSHA_MAP routing** — 48-symptom fallback for protocol path
4. **JSONB parsing fixes** — State vectors correctly parsed from asyncpg strings

### Phase 3: Learning (Planned)

1. **Track question effectiveness** — Did the question lead to useful info?
2. **Refine memory recall** — Improve what context gets loaded
3. **Feedback loop** — User responses inform future question quality

---

## 8. Decision-Making Flow

The system makes decisions at each pipeline stage. Here's how each decision is made:

### Stage 1: Domain Classification (Sensing)

```
INPUT: User message text
PROCESS: Keyword matching against domain dictionaries
DECISION: Assign domain (BODY/MIND/LIFE) with highest keyword matches
OUTPUT: SenseFrame with domain, symptom, tone, specificity
```

**Key factors:**
- Body keywords: headache, pain, tired, sleep, energy, digestion
- Mind keywords: anxious, stressed, focus, mood, motivation
- Life keywords: goal, career, relationship, purpose, decision

### Stage 2: Knowledge Gap Analysis

```
INPUT: SenseFrame + User's person_id
PROCESS (parallel):
  1a. Load constitution + state vectors (personal_model + memory_episodic)
  1b. Fetch 10 most recent STM entries (no keyword filtering)
THEN (sequential):
  2. Episodic memory search for older topic-specific facts (embedding-based)
  3. Check for unresolved references (pronouns → semantic search)
  4. Generate inferences from dosha drift + guna mode
  5. LLM generates personalized questions using ALL above context
DECISION: LLM determines what's unknown based on full personal context
OUTPUT: KnowledgeGap { known facts, inferences, personalized questions }
```

**Key factors:**
- Constitution (dosha baseline, OS type, life context)
- Current state vs baseline (drift detection)
- Recent conversation context (keyword-free STM)
- LLM sees everything — generates questions about genuine gaps only

### Stage 3: Response Strategy Selection

```
INPUT: SenseFrame + KnowledgeGap
PROCESS:
  1. Count critical unknowns (high-priority questions)
  2. Count known facts and inferences
  3. Check message specificity
DECISION:
  - If specificity=HIGH and critical_unknowns=0 → RESPOND
  - If known_count > 0 or inferences > 0 → CONNECT_AND_INQUIRE
  - Otherwise → INQUIRE
OUTPUT: ResponseStrategy with mode, questions, facts to reference
```

**Question prioritization:**
1. High-priority questions for dominant dosha (most likely relevant)
2. High-priority questions for any dosha
3. Medium-priority questions
4. Maximum 2 questions selected

### Stage 4: Context Synthesis

```
INPUT: SenseFrame + KnowledgeGap + ResponseStrategy
PROCESS:
  1. Format constitution as human-readable string
  2. Look up constitution-specific guidance from diagnostic_kb
  3. Compile likely causes, tone, things to avoid
  4. Build guardrails list
OUTPUT: SynthesizedContext ready for prompt
```

### Stage 5: Prompt Formation

```
INPUT: User message + SynthesizedContext
PROCESS:
  1. Build decision reasoning explanation
  2. Assemble structured prompt with all context
  3. Include response template for the chosen mode
OUTPUT: Complete LLM prompt
```

---

## 9. Key Files

| File | Purpose |
|------|---------|
| **Backend (Pipeline)** | |
| `sakhi/apps/api/services/response/sensing.py` | LLM-powered domain classification, SenseFrame extraction |
| `sakhi/apps/api/services/response/knowledge_gap.py` | Context loading (constitution, STM, deterministic intelligence, episodic), inference engine, LLM question generation |
| `sakhi/apps/api/services/response/diagnostic_kb.py` | Symptom routing (DIAGNOSTIC_PATHS + SYMPTOM_DOSHA_MAP), constitution guidance for synthesis |
| `sakhi/apps/api/services/response/strategy.py` | Response mode selection (INQUIRE / CONNECT_AND_INQUIRE / RESPOND) |
| `sakhi/apps/api/services/response/synthesizer.py` | Context synthesis — 3-block cognitive architecture prompt for final LLM call |
| `sakhi/apps/api/services/response/templates.py` | Response templates |
| `sakhi/apps/api/services/response/pipeline.py` | Main orchestration — 5-stage pipeline |
| `sakhi/apps/api/services/ayurveda/causal_reasoning.py` | SYMPTOM_DOSHA_MAP (48 symptoms), `get_recent_behaviors()`, `map_symptom_to_dosha()` — feeds knowledge gap + diagnostic_kb |
| **Frontend (Debug)** | |
| `apps/web/app/experience/converse/DebugPanel.tsx` | Debug panel component |
| `apps/web/app/experience/converse/page.tsx` | Converse page with debug integration |

---

## 10. Debug Panel

The Debug Panel provides a "glass pane" view of the entire execution flow. It's accessible from the FAB menu in the converse page.

### What It Shows

| Section | Contents |
|---------|----------|
| **User Input** | The original message sent |
| **Personal OS** | Constitution (dosha %), operating system type, life phase |
| **Adaptive Pipeline** | All 5 stages with status indicators (✓/✗) |
| **Sensing** | Domain, sub-domain, symptom, tone, specificity, confidence |
| **Knowledge Gap** | Known/inferred/unknown counts, dominant dosha, guna mode |
| **Strategy** | Response mode, questions count, reasoning |
| **Memory Recalls** | What was recalled from memory with relevance scores |
| **Context Sent to LLM** | System context (recalls + patterns) |
| **Adaptive Prompt** | Full structured prompt sent to the model |
| **Engine States** | Conversation depth, tone, continuity |
| **Generated Response** | The final reply |
| **Raw Debug JSON** | Complete data dump for debugging |

### How to Access

1. Send a message in the converse page
2. Click the **+** FAB button (bottom right)
3. Click **Debug Panel**
4. View the slide-out panel with all execution details

### Use Cases

- **Development**: Verify the pipeline is working correctly
- **Debugging**: See why a particular response was generated
- **Tuning**: Understand which factors influenced the response mode
- **Testing**: Confirm memory recall and constitution loading

---

## 11. Examples

### Example 1: New User — Joints Hurt (No History)

**User:** "my joints hurt"

**SenseFrame:**
- Domain: BODY
- Symptom: joints
- Temporal: unspecified
- Specificity: low

**Knowledge Gap (context loaded first):**
- Constitution: Vata-dominant (42%), Adaptive OS
- Recent STM: (empty — new user)
- Episodic: (empty)
- Inferences: (none — no state vectors yet)

**LLM generates questions seeing:** empty personal context, vata constitution, joint pain

**Questions generated:**
1. "Is the stiffness worse in the morning, or does it build through the day?" *(high — vata pattern: morning stiffness vs activity-related)*
2. "Has anything changed recently — sleep, activity, weather?" *(medium — vata triggers)*

**Response (INQUIRE mode):**
> "Joint discomfort can tell us a lot. Is the stiffness worse when you first get up, or does it build through the day? And has anything changed recently — sleep, activity level, or even the weather?"

---

### Example 2: Returning User — Headaches (Rich History)

**User:** "I keep getting headaches recently"

**SenseFrame:**
- Domain: BODY
- Symptom: headaches
- Temporal: recurring
- Specificity: low

**Knowledge Gap (context loaded first):**
- Constitution: Kapha-dominant (40%), Conservation OS
- Recent STM (keyword-free, 10 entries):
  - "my skin has been very dry lately"
  - "I've been drinking more water but still feel dehydrated"
  - "some congestion and back stiffness"
  - "I had a headache yesterday afternoon"
  - "I've been sleeping about 7 hours"
- Inferences: (no recent episodic entries with state vectors)

**LLM generates questions seeing:** kapha constitution, dry skin, hydration efforts, congestion, previous headache, sleep data

**Questions generated:**
1. "Is the headache more of a dull pressure, especially around the forehead or sinuses?" *(high — kapha pattern + knows about congestion)*
2. "Does it tend to come on in the afternoon, or is it there when you wake up?" *(medium — timing unknown, previous one was afternoon)*

Note: LLM does NOT ask about sleep (knows: 7 hours), hydration (knows: drinking more water), or skin (not relevant to headaches).

**Response (CONNECT_AND_INQUIRE mode):**
> "Headaches again... I'm noticing you mentioned some congestion earlier, and your system tends toward that kind of buildup. Is the pain more of a dull pressure, especially around the forehead? And does it tend to hit in the afternoon, like the one yesterday?"

---

### Example 3: Enough Information — Detailed Message

**User:** "I keep getting headaches recently — sharp pain at my temples, usually after long meetings"

**SenseFrame:**
- Domain: BODY
- Symptom: headaches
- Temporal: recurring
- Specificity: HIGH (location, quality, timing given)

**Knowledge Gap (context loaded first):**
- Constitution: Pitta-dominant (45%)
- Recent STM: "mentioned poor sleep", "skipped lunch twice", "been in back-to-back meetings"
- Inferences: Pitta elevated +7%, Rajas dominant

**LLM generates questions seeing:** pitta constitution, poor sleep, skipped meals, meetings, AND the message already says sharp/temples/after meetings

**Questions generated:** (empty or only low-priority — user already gave specifics)

**Response (RESPOND mode):**
> "Sharp pain at the temples after long meetings — that's a classic intensity pattern for your system. The combination of mental heat from focused work, plus the sleep and meal gaps you've mentioned, is likely building pressure. A few things that often help: step outside for 2 minutes between meetings for cooler air, and try not to skip lunch even if it's quick. Does that feel doable?"

---

## 12. Guardrails

### Always

- **Max 2 questions per turn** — Never interrogate
- **Reference memory before asking** — Don't re-ask what we know
- **Constitution-first prioritization** — Don't list generic possibilities
- **Warm, practical tone** — Never clinical or diagnostic

### Never

- **Diagnose** — "You have..." or "This is..."
- **Overwhelm with possibilities** — "It could be A, B, C, D, E..."
- **Ignore constitution** — Generic advice that doesn't fit their type
- **Ask redundant questions** — If memory has it, reference it

---

## 13. Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SAKHI_USE_ADAPTIVE_RESPONSE` | `1` | Enable/disable adaptive response pipeline (`1`=on, `0`=off) |

---

*Document Version: 2.1*
*Created: January 2026*
*Updated: February 2026 — Deterministic intelligence wired into knowledge gap pipeline (personal patterns, behavior log, symptom episodes, symptom→dosha mapping). LLM-powered personalized questions, keyword-free STM, inverted knowledge gap flow.*
