# Adaptive Response Framework

## Overview

The Adaptive Response Framework is Sakhi's approach to forming intelligent, personalized responses. Instead of generic replies or overwhelming users with possibilities, Sakhi responds like a skilled Ayurvedic practitioner:

1. **Constitution-aware** — Uses the user's Operating System (dosha baseline) to prioritize likely causes
2. **Memory-informed** — Checks what we already know before asking questions
3. **Targeted inquiry** — Asks maximum 2 questions per turn, chosen for diagnostic value
4. **Domain-adaptive** — Adjusts approach based on whether the concern is Body, Mind, or Life

**Core Principle:** Never ramble with 10 possibilities. Pick the most likely 2-3 based on their constitution and ask targeted questions.

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
│  2. KNOWLEDGE GAP ANALYSIS                                                   │
│     ├── Load user's Operating System (constitution)                          │
│     ├── Determine diagnostic questions for symptom + constitution            │
│     ├── Query memory sources for each question                               │
│     ├── Check state vectors for inferences                                   │
│     └── Compile: KNOWN / INFERRED / UNKNOWN                                  │
│                                                                              │
│     Output: KnowledgeGap { known, inferred, to_ask }                        │
└─────────────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  3. RESPONSE STRATEGY SELECTION                                              │
│     ├── If UNKNOWN is empty → RESPOND mode (enough info)                    │
│     ├── If UNKNOWN has items → INQUIRY mode (need more info)                │
│     ├── Select max 2 questions to ask (prioritized by constitution)         │
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

### Memory Sources

The system queries four layers of knowledge:

#### Layer 1: Foundational (Onboarding)

Always available from `personal_model`:

| Field | Contains | Usage |
|-------|----------|-------|
| `operating_system.dosha_baseline` | {vata, pitta, kapha} percentages | Prioritize likely causes |
| `operating_system.type` | "Adaptive-Performance" etc. | Frame responses |
| `life_context` | age, roles, life_phase | Avoid inappropriate advice |
| `decision_profile` | risk_tendency, energy_tradeoff | Understand preferences |

#### Layer 2: State Vectors (Recent Episodes)

From `memory_episodic`:

| Field | Contains | Usage |
|-------|----------|-------|
| `state_vector.dosha` | Current dosha levels | Detect drift from baseline |
| `guna_vector` | {sattva, rajas, tamas} | Operating mode |
| `emotional_state` | Recent emotional patterns | Emotional context |
| `rhythm_state` | Energy, stress, fatigue | Physical state |

#### Layer 3: Episodic Memory

From `memory_episodic`, `memory_short_term`, `context_recalls`:

- Semantic search using embeddings
- Keyword matching
- Recency-weighted retrieval

#### Layer 4: Derived Intelligence

From deep workers stored in `personal_model`:

| Worker | Provides |
|--------|----------|
| `identity_momentum_deep` | Identity evolution patterns |
| `emotion_soul_rhythm_deep` | Integrated ESR state |
| `longitudinal_update` | Weekly/monthly patterns |
| `rhythm_soul_deep` | Rhythm-soul integration |

### Query Strategy

For each diagnostic question, query memory with:

```python
@dataclass
class KnowledgeQuery:
    question_id: str              # "sleep_quality"
    keywords: List[str]           # ["sleep", "insomnia", "tired", "rest"]
    semantic_query: str           # "how has their sleep been recently"
    recency_days: int             # How far back to search
    min_confidence: float         # Threshold to consider "found"
```

### Knowledge Gap Output

```python
@dataclass
class KnowledgeGap:
    known: Dict[str, KnownFact]        # What we already know
    inferred: Dict[str, Inference]      # What we can deduce
    unknown: List[DiagnosticQuestion]   # What we need to ask
    constitution_context: ConstitutionContext
```

---

## 3. Diagnostic Knowledge Base

### Structure

The system maintains domain-specific diagnostic trees:

```python
@dataclass
class DiagnosticPath:
    domain: str                           # "body"
    sub_domain: str                       # "head_neurological"
    symptom: str                          # "headaches"

    # Dosha-specific questions (ordered by priority)
    dosha_questions: Dict[str, List[DiagnosticQuestion]]

    # Keywords to search in memory
    memory_queries: List[KnowledgeQuery]

    # State vector signals to check
    state_signals: List[str]

    # Follow-up paths based on answers
    follow_ups: Dict[str, "DiagnosticPath"]
```

### Example: Headaches

```yaml
headaches:
  domain: body
  sub_domain: head_neurological

  dosha_questions:
    vata:
      priority_1:
        id: pain_quality
        question: "Is the pain more throbbing or pulsing?"
        why: "Throbbing suggests vata aggravation"
      priority_2:
        id: anxiety_connection
        question: "Does it come on when you're feeling anxious or scattered?"
        why: "Vata headaches often linked to anxiety"

    pitta:
      priority_1:
        id: pain_quality
        question: "Is the pain sharp or burning?"
        why: "Sharp/burning suggests pitta aggravation"
      priority_2:
        id: heat_trigger
        question: "Does it come on after intense focus or heat exposure?"
        why: "Pitta headaches often heat/intensity related"

    kapha:
      priority_1:
        id: pain_quality
        question: "Is the pain more dull, heavy, or pressure-like?"
        why: "Dull/heavy suggests kapha/sinus involvement"
      priority_2:
        id: congestion
        question: "Is there any sinus pressure or congestion with it?"
        why: "Kapha headaches often sinus-related"

  memory_queries:
    - id: sleep_quality
      keywords: [sleep, insomnia, tired, rest, night, woke]
      semantic: "how has their sleep been"
      recency_days: 14

    - id: meals_hydration
      keywords: [lunch, dinner, meal, eat, skip, water, drink, hungry]
      semantic: "eating and hydration patterns"
      recency_days: 7

    - id: stress_work
      keywords: [stress, work, deadline, pressure, busy, overwhelm]
      semantic: "stress and work pressure"
      recency_days: 14

    - id: screen_time
      keywords: [screen, computer, phone, eyes, strain]
      semantic: "screen and eye strain"
      recency_days: 7

  state_signals:
    - dosha_drift_pitta    # Check if pitta elevated
    - dosha_drift_vata     # Check if vata elevated
    - rajas_dominant       # High activation mode
    - fatigue_high         # From rhythm_state
    - stress_rising        # From rhythm_state

  constitution_guidance:
    vata_dominant:
      likely_causes: [anxiety, irregular_routine, cold_dry, overstimulation]
      tone: grounding, calming
      avoid_suggesting: intense_exercise, stimulants

    pitta_dominant:
      likely_causes: [intensity, heat, skipped_meals, overwork]
      tone: cooling, measured
      avoid_suggesting: more_pushing, competition

    kapha_dominant:
      likely_causes: [sinus, sluggishness, oversleep, heavy_food]
      tone: energizing, clear
      avoid_suggesting: more_rest, heavy_foods
```

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

### Phase 1: MVP

1. **Sensing Layer** — Basic domain classification + symptom extraction
2. **Knowledge Gap** — Query episodic memory + state vectors
3. **Response Strategy** — Simple INQUIRE vs RESPOND mode
4. **Templates** — 3 basic templates

### Phase 2: Diagnostic Trees

1. **Build diagnostic paths** for common symptoms (headaches, sleep, anxiety, energy)
2. **Constitution-specific questions** for each symptom
3. **Follow-up paths** based on answers

### Phase 3: Learning

1. **Track question effectiveness** — Did the question lead to useful info?
2. **Refine memory queries** — Improve recall precision
3. **Personalize diagnostic paths** — Learn individual patterns

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
PROCESS:
  1. Load constitution from personal_model.operating_system
  2. Load state vectors from memory_episodic
  3. Search short-term and episodic memory for relevant topics
  4. Generate inferences from dosha drift and guna mode
DECISION: Classify each diagnostic topic as KNOWN/INFERRED/UNKNOWN
OUTPUT: KnowledgeGap with constitution context
```

**Key factors:**
- Dosha baseline (vata/pitta/kapha percentages)
- Current state vs baseline (drift detection)
- Recency of known facts (recent > moderate > old)
- Confidence threshold for "known" (> 0.5)

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
| `sakhi/apps/api/services/response/sensing.py` | Domain classification, SenseFrame |
| `sakhi/apps/api/services/response/knowledge_gap.py` | Memory queries, gap analysis |
| `sakhi/apps/api/services/response/diagnostic_kb.py` | Diagnostic knowledge base |
| `sakhi/apps/api/services/response/strategy.py` | Response mode selection |
| `sakhi/apps/api/services/response/synthesizer.py` | Context synthesis for LLM |
| `sakhi/apps/api/services/response/templates.py` | Response templates |
| `sakhi/apps/api/services/response/pipeline.py` | Main orchestration |
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

### Example 1: First Interaction — Headaches

**User:** "I keep getting headaches recently"

**SenseFrame:**
- Domain: BODY
- Symptom: headaches
- Temporal: recurring
- Specificity: low

**Knowledge Gap:**
- Operating System: Pitta-dominant (45% pitta)
- Known: (nothing — first interaction post-onboarding)
- Unknown: pain_quality, timing, sleep, meals

**Response (INQUIRE mode):**
> "Headaches can tell us a lot. Given your nature, I'd want to understand a bit more. Is the pain more sharp and concentrated, or dull and heavy? And does it tend to come on after intense work or screen time?"

---

### Example 2: Returning User — Headaches

**User:** "I keep getting headaches recently"

**SenseFrame:**
- Domain: BODY
- Symptom: headaches
- Temporal: recurring
- Specificity: low

**Knowledge Gap:**
- Operating System: Pitta-dominant (45% pitta)
- Current State: Pitta elevated (+7%), Rajas dominant
- Known:
  - Sleep: "mentioned poor sleep 3 days ago"
  - Meals: "skipped lunch twice this week"
- Unknown: pain_quality, timing specifics

**Response (CONNECT_AND_INQUIRE mode):**
> "Headaches again... I'm noticing you mentioned sleep has been rough, and you've been skipping meals during busy stretches. For your system, that combination often shows up as head tension. Is the pain more sharp, or more of a dull pressure?"

---

### Example 3: Enough Information

**User:** "I keep getting headaches recently — sharp pain at my temples, usually after long meetings"

**SenseFrame:**
- Domain: BODY
- Symptom: headaches
- Temporal: recurring
- Specificity: HIGH (location, quality, timing given)

**Knowledge Gap:**
- Operating System: Pitta-dominant
- Known:
  - Pain: sharp, temples (from message)
  - Timing: after meetings (from message)
  - Sleep: poor (from memory)
  - Meals: irregular (from memory)
- Unknown: (nothing critical)

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

*Document Version: 1.1*
*Created: January 2026*
*Updated: January 2026 — Added Debug Panel, Decision-Making Flow*
