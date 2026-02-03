# Deepening the Ayurvedic Engine
## Implementation Plan for Building the Hidden Intelligence Layer

**Purpose:** Strategic implementation plan for building Sakhi's Ayurvedic reasoning engine deeper
**Date:** January 2026
**Status:** PARTIALLY IMPLEMENTED - Updated February 2026

> **Update 2026-02-03:** Several components have been implemented since this document was written. See status markers below.

---

## Table of Contents

1. [Current State Assessment](#current-state-assessment)
2. [Vision: What "Deeper" Means](#vision-what-deeper-means)
3. [The Knowledge Graph: Core Missing Piece](#the-knowledge-graph-core-missing-piece)
4. [Implementation Phases](#implementation-phases)
5. [Data Requirements](#data-requirements)
6. [Validation Strategy](#validation-strategy)
7. [Success Metrics](#success-metrics)
8. [Risk Mitigation](#risk-mitigation)

---

## Current State Assessment

### What We Have (60-65% Built) ✅

**Computation Layer:**
- ✅ Dosha detection from journal text (Vata/Pitta/Kapha keywords)
- ✅ Guna tracking (Sattva/Rajas/Tamas from sentiment + keywords)
- ✅ Five Element Matrix (body/mind/emotion × earth/water/fire/air/ether)
- ✅ Soul state extraction (values, shadow, light, friction, conflicts)
- ✅ Energy primitives (activation_load, grounding, circulation, recovery)
- ✅ Temporal aggregation (STM → Weekly → Monthly → Baseline)

**Storage:**
- ✅ Per-entry state vectors (dosha, guna, elements)
- ✅ Personal baselines (elemental, energy)
- ✅ Soul state tracking over time
- ✅ Graph schema (ay_nodes, ay_edges tables exist)

**What This Means:**
You're capturing the RAW SIGNALS. You're detecting "high Vata" or "Pitta aggravation" from journal entries. This is the sensory layer.

### What's Been Implemented Since (Updated 2026-02-03)

**Reasoning Layer:**
- ✅ Causal Reasoning Engine - `services/ayurveda/causal_reasoning.py` - "Why am I anxious?" queries
- ✅ Pattern Learning - `services/ayurveda/pattern_learning.py` - learns personal cause→effect patterns
- ✅ Graph Reasoning - `services/ayurveda/graph_reasoning.py` - graph traversal for recommendations
- ✅ Prakruti vs Vikriti - `services/ayurveda/prakruti.py` + `vikriti.py` - baseline vs current state
- ✅ Food Recommendations - `services/ayurveda/food_recommendations.py` - dosha-aware food suggestions
- ⬜ Full Knowledge Graph Population (500 nodes, 2000 edges) - schema exists, needs seeding
- ⬜ Seasonal/circadian intelligence - partial (time-of-day in context)
- ⬜ Contraindication logic - not fully implemented

**Personalization Layer:**
- ✅ Prakruti storage - `personal_model.operating_system` stores constitutional type
- ✅ Food/habit preferences - `services/memory/sensory_preferences.py` + `food_memory.py`
- ✅ Preference Learning - `services/memory/preference_learning.py` - auto-learns from conversations
- ⬜ Location-based adjustments - not implemented
- ⬜ Phase-of-life considerations - partial (age/life_context in personal_model)
- ⬜ Ama tracking - not implemented

### Remaining Gap (~20-25%)

**Still Missing:**
- ⬜ Knowledge Graph seed data (500 Ayurvedic nodes, 2000 edges)
- ⬜ Multi-hop graph traversal for complex recommendations
- ⬜ Seasonal intelligence (Ritu adjustments)
- ⬜ Contraindication rules
- ⬜ Ama/toxin accumulation tracking

**What This Means:**
System can now DETECT and EXPLAIN through causal reasoning, but full PRESCRIPTIVE intelligence (graph-driven, multi-factor) awaits Knowledge Graph population.

---

## Vision: What "Deeper" Means

### From Detection → Understanding → Prescription

**Current (Detection):**
```
Journal: "Feeling scattered, can't focus, anxious"
System: Detects Vata = 0.7 (high)
Output: "You seem restless today"
```

**Deeper (Understanding):**
```
Journal: "Feeling scattered, can't focus, anxious"

Multi-Layer Analysis:
1. Constitutional: User is Vata-Pitta (Adaptive-Performance OS)
2. Current State: Vata = 0.9 (significantly above baseline 0.45)
3. Context: Winter (Vata season) + Evening (Vata time) + Low sleep (3 nights)
4. Pattern: 7-day upward Vata trend
5. Root Cause: Seasonal amplification (1.5x) + Time-of-day (1.3x) + Sleep debt (1.4x) = 2.7x Vata load

Reasoning Chain:
"Your natural Adaptive tendency (Vata) is being amplified by:
- Winter's cold/dry qualities (Vata season)
- Evening hours 2-6pm (Vata time of day)
- Sleep debt accumulating Ama
- Result: 2.7x normal Vata load = Chaos Friction state"

Output: "You're experiencing Chaos Friction (scattered energy). Here's why..."
```

**Even Deeper (Prescription):**
```
Intelligent Recommendations (Graph-Driven):

IMMEDIATE (next 2 hours):
- Nadi Shodhana breathing × 10 min (pacifies Vata 0.6 strength)
- Warm herbal tea: ginger + cinnamon (grounding, warming)
- 15-min slow walk (grounding through feet, not intense)
- Close 2-3 open loops (reduce mental scatter)

TODAY (evening protocol):
- Warm oil self-massage before shower (Vata pacification 0.8 strength)
- Heavy, warm dinner: kitchari or soup (avoid raw/cold foods)
- Early bedtime (9:30pm vs usual 11pm)
- No screens after 8pm (reduce stimulation)

NEXT 7 DAYS (seasonal adjustment):
- Maintain consistent wake/sleep times (counter Vata irregularity)
- Daily grounding practice: yoga nidra or restorative yoga
- Increase healthy fats: ghee, olive oil, nuts
- Reduce cold/dry foods: salads, crackers, raw veggies
- Weekly: warm oil massage (professional or self)

WHY THESE WORK:
[Graph reasoning explains each recommendation's mechanism]
```

### The Difference

**Current:** Pattern detection
**Deeper:** Causal understanding + intelligent prescription

**Current:** "You're anxious" (observation)
**Deeper:** "You're anxious because [multi-factor causal chain] → here's the exact protocol to address root cause"

This is the difference between a **symptom tracker** and an **intelligent practitioner**.

---

## The Knowledge Graph: Core Missing Piece

### Why the Knowledge Graph Is Essential

**Without Graph:**
- Hardcoded if-then rules
- Recommendations don't adapt to context
- Can't explain WHY something works
- No multi-hop reasoning
- Breaks when edge cases appear

**With Graph:**
- Dynamic reasoning based on relationships
- Context-aware (season + time + individual + current state)
- Can explain causal chains
- Handles complexity naturally
- Learns/expands over time

### The Graph Architecture

#### Node Types (8 categories, ~500 total nodes)

**1. Constitutional Nodes (15 nodes)**
- 3 Pure doshas: Vata, Pitta, Kapha
- 10 Dual-dosha combinations: Vata-Pitta, Pitta-Kapha, etc.
- 2 Tridoshic: Balanced, Highly Variable
- Properties: Qualities (cold/hot, dry/oily, light/heavy), vulnerabilities, strengths

**2. Imbalance State Nodes (21 nodes)**
- Vata states: Vata Excess, Vata Deficiency, Vata-Pitta Combined, etc.
- Pitta states: Pitta Excess, Pitta Deficiency, etc.
- Kapha states: Kapha Excess, Kapha Deficiency, etc.
- Properties: Symptoms, aggravating factors, severity levels

**3. Food Nodes (~200 nodes)**
- Common foods: Rice, chicken, spinach, coffee, etc.
- Ayurvedic categories: Grains, legumes, vegetables, fruits, spices, etc.
- Properties:
  - Taste (Rasa): Sweet, sour, salty, bitter, pungent, astringent
  - Quality (Guna): Heavy/light, oily/dry, hot/cold
  - Post-digestive effect (Vipaka)
  - Dosha effects: Pacifies/aggravates V/P/K

**4. Habit/Practice Nodes (~80 nodes)**
- Physical: Yoga styles, exercise types, massage, sleep timing
- Breathing: Pranayama techniques (Nadi Shodhana, Bhastrika, etc.)
- Mental: Meditation types, journaling, creative work
- Daily routine: Wake times, meal times, work patterns
- Properties: Time of day suitability, dosha effects, intensity level

**5. Symptom Nodes (~60 nodes)**
- Physical: Dry skin, inflammation, lethargy, pain types
- Mental: Anxiety, depression, brain fog, racing thoughts
- Emotional: Irritability, sadness, apathy
- Energetic: Fatigue, restlessness, heaviness
- Properties: Dosha signature, severity indicators, related symptoms

**6. Environmental Nodes (~40 nodes)**
- Seasons: Winter, Spring, Summer, Fall (+ 6 Ayurvedic seasons)
- Time of Day: Vata time (2-6am, 2-6pm), Pitta time (10am-2pm, 10pm-2am), Kapha time (6-10am, 6-10pm)
- Climate: Hot/cold, humid/dry, windy, stable
- Properties: Dominant dosha, aggravation risk

**7. Quality Nodes (20 nodes)**
- The 10 pairs of opposite qualities (Gurvadi Gunas):
  - Heavy ↔ Light
  - Oily ↔ Dry
  - Hot ↔ Cold
  - Stable ↔ Mobile
  - Dense ↔ Subtle
  - Smooth ↔ Rough
  - Soft ↔ Hard
  - Slow ↔ Sharp
  - Cloudy ↔ Clear
  - Gross ↔ Subtle

**8. Treatment Principle Nodes (10 nodes)**
- Pacification (Shamana)
- Purification (Shodhana)
- Palliation (Shamana)
- Opposite therapy (Viparita)
- Similar therapy (Sadrisha)
- Satiation therapy (Brimhana)
- Reduction therapy (Langhana)

#### Edge Types (12 relationship types, ~2000 edges)

**1. Constitutional Edges**
- `constitution --[HAS_QUALITY]--> quality` (e.g., Vata has Mobile, Light, Cold, Dry)
- `constitution --[VULNERABLE_TO]--> environmental_factor` (e.g., Vata vulnerable to Winter)
- `constitution --[STRENGTH]--> capability` (e.g., Vata strength in Creativity, Adaptability)

**2. Imbalance Edges**
- `symptom --[INDICATES]--> imbalance` (e.g., Anxiety indicates Vata Excess)
- `imbalance --[HAS_SYMPTOM]--> symptom` (reverse)
- Weight: Strength of indication (0.0-1.0)

**3. Food Edges**
- `food --[PACIFIES]--> dosha` (e.g., Warm Oil Massage pacifies Vata)
- `food --[AGGRAVATES]--> dosha` (e.g., Cold Salad aggravates Vata)
- `food --[HAS_QUALITY]--> quality` (e.g., Ghee has Oily, Heavy)
- Weight: Effect strength (0.0-1.0)

**4. Habit/Practice Edges**
- `practice --[BALANCES]--> imbalance` (e.g., Nadi Shodhana balances Vata Excess)
- `practice --[BEST_TIME]--> time_window` (e.g., Meditation best in Kapha time morning)
- `practice --[INTENSITY]--> level` (gentle/moderate/intense)
- Weight: Effectiveness (0.0-1.0)

**5. Environmental Edges**
- `season --[AGGRAVATES]--> dosha` (e.g., Winter aggravates Vata)
- `time_of_day --[FAVORS]--> dosha` (e.g., 2-6pm is Vata time)
- `climate --[AMPLIFIES]--> imbalance`
- Weight: Amplification factor (1.0-2.0)

**6. Treatment Edges**
- `quality --[OPPOSITE_OF]--> quality` (e.g., Hot opposite of Cold)
- `treatment_principle --[USES]--> quality` (e.g., Pacification uses Opposite qualities)
- `imbalance --[TREATED_BY]--> treatment_principle`

**7. Causal Edges**
- `imbalance --[CAUSES]--> symptom`
- `environmental_factor --[CONTRIBUTES_TO]--> imbalance`
- `habit --[MAINTAINS]--> balance_state`
- Weight: Causal strength

**8. Contraindication Edges**
- `food --[CONTRAINDICATED_WITH]--> imbalance` (e.g., Caffeine contraindicated with Vata Excess)
- `practice --[AVOID_IF]--> condition`

**9. Synergy Edges**
- `food --[SYNERGIZES_WITH]--> food` (combinations that amplify effects)
- `practice --[COMPLEMENTS]--> practice`

**10. Personalization Edges**
- `constitution --[PREFERS]--> food_category`
- `constitution --[OPTIMAL_PRACTICE]--> practice_type`

**11. Temporal Edges**
- `practice --[OPTIMAL_SEASON]--> season`
- `food --[SEASONAL_ALIGNMENT]--> season`

**12. Severity/Progression Edges**
- `imbalance_mild --[PROGRESSES_TO]--> imbalance_severe`
- `symptom --[EARLY_SIGN_OF]--> imbalance`

### Example Graph Queries (Multi-Hop Reasoning)

#### Query 1: "Why am I anxious?"

```
User State:
- Symptom: Anxiety (detected from journal)
- Constitution: Vata-Pitta (stored)
- Current Dosha: Vata = 0.9, Pitta = 0.3, Kapha = 0.1
- Season: Winter
- Time: 3pm
- Recent Pattern: Low sleep × 3 nights

Graph Traversal:
1. anxiety --[INDICATES 0.8]--> vata_excess
2. vata_excess --[AMPLIFIED_BY]--> winter (1.5x)
3. vata_excess --[AMPLIFIED_BY]--> vata_time_afternoon (1.3x)
4. low_sleep --[CAUSES 0.7]--> vata_aggravation
5. vata_pitta_constitution --[VULNERABLE_TO]--> vata_excess

Reasoning Output:
"Your anxiety is primarily Vata Excess (80% confidence), amplified by:
- Winter season (1.5x Vata load - cold/dry qualities)
- Afternoon Vata time 2-6pm (1.3x - natural Vata peak)
- Sleep debt (0.7 strength contributor - increases Vata)
- Your Adaptive-Performance constitution makes you naturally prone to Vata imbalance
Total amplification: 2.5x baseline Vata = Chaos Friction state"
```

#### Query 2: "What should I eat right now?"

```
User State:
- Current Imbalance: Vata Excess
- Time: 6pm (entering Kapha time)
- Season: Winter
- Preferences: Vegetarian, no dairy
- Location: Cold climate

Graph Traversal:
1. vata_excess --[PACIFIED_BY]--> foods WHERE quality IN (warm, oily, heavy, grounding)
2. Filter: foods --[NOT contraindicated]--> vata_excess
3. Filter: foods --[vegetarian]--> true
4. Filter: foods --[EXCLUDE]--> dairy
5. Rank by: (pacification_strength × seasonal_appropriateness × time_of_day_match)

Top Recommendations (with reasoning):
1. **Kitchari (mung dal + rice)** [Score: 0.92]
   - Warm (pacifies Vata 0.8)
   - Oily when cooked with ghee alternatives (coconut oil)
   - Easy to digest (low Ama accumulation)
   - Grounding (Kapha time alignment)
   - Seasonal: Perfect for winter

2. **Root vegetable soup** [Score: 0.88]
   - Heavy, warm, grounding (0.85 Vata pacification)
   - Root vegetables have earth element (stability)
   - Winter-appropriate
   - Kapha time aligned

3. **Warm quinoa bowl with roasted vegetables + tahini** [Score: 0.82]
   - Warm, oily (tahini), moderately heavy
   - Avoid: raw vegetables (would aggravate Vata)
   - Add: warming spices (cumin, coriander, ginger)

AVOID (contraindicated):
- Salads (cold, raw, light - aggravates Vata 0.9)
- Crackers/chips (dry, light - aggravates Vata 0.8)
- Smoothies (cold - aggravates Vata in winter 0.95)
```

#### Query 3: "Design my evening routine"

```
User State:
- Constitution: Vata-Pitta (Adaptive-Performance)
- Current: Chaos Friction (Vata Excess)
- Goal: Improve sleep, reduce anxiety
- Time Available: 3 hours (6pm-9pm)
- Season: Winter

Graph Traversal:
1. chaos_friction --[BEST_TREATED_BY]--> practices WHERE quality IN (grounding, calming, warming)
2. vata_pitta_constitution --[OPTIMAL_EVENING_PRACTICE]--> practice_type
3. Filter: practices --[APPROPRIATE_TIME]--> evening_kapha_time
4. Chain: practices --[SEQUENCED_WITH]--> practices (natural flow)
5. Rank by: (effectiveness × constitution_match × time_appropriateness)

Designed Routine:

**6:00-6:30pm: Transition & Ground**
- Practice: Abhyanga (warm oil self-massage)
- Why: Pacifies Vata (0.8), warming, grounding, soothes nervous system
- Graph reasoning: vata_excess --[PACIFIED_BY 0.8]--> abhyanga --[HAS_QUALITY]--> oily, warm
- Sequence: Before shower, allows oil absorption

**6:30-7:00pm: Nourish**
- Activity: Prepare & eat warm dinner (kitchari or soup)
- Why: Grounding, digestive fire still active, builds tissue
- Graph: kapha_evening_time --[FAVORS]--> building_activities
- Note: Eat mindfully, avoid screens

**7:00-7:45pm: Process & Release**
- Practice: Gentle restorative yoga (5-7 poses, long holds)
- Why: Releases physical tension, activates parasympathetic
- Graph: vata_excess --[BALANCED_BY]--> gentle_movement (NOT intense)
- Contraindication: Avoid vinyasa (too activating for evening Vata excess)

**7:45-8:15pm: Reflect & Integrate**
- Practice: Journal in Sakhi (voice or text)
- Why: Process day, close loops, reduce mental scatter
- Graph: mental_scatter --[REDUCED_BY]--> reflection_practice
- Prompt: "What do I need to release from today?"

**8:15-8:45pm: Calm Nervous System**
- Practice: Nadi Shodhana (alternate nostril breathing) × 10 min
- Why: Balances left/right brain, direct Vata pacification (0.75)
- Graph: vata_excess --[PACIFIED_BY 0.75]--> nadi_shodhana
- Sequence: After journaling, before sleep prep

**8:45-9:00pm: Prepare for Sleep**
- Activity: Warm herbal tea (chamomile, ashwagandha)
- Dim lights, no screens
- Cool bedroom (65-68°F optimal)
- Why: Signals wind-down, supports melatonin
- Graph: sleep_quality --[IMPROVED_BY]--> consistent_routine

**9:00-9:30pm: Sleep**
- Early bedtime (vs. usual 11pm)
- Why: Vata excess needs extra rest, Kapha time supports deep sleep
- Graph: vata_excess --[REQUIRES]--> increased_rest

Total Impact Score: 0.89 (high likelihood of Vata reduction + improved sleep)
```

---

## Implementation Phases

### Phase 1: Knowledge Graph Foundation (Weeks 1-4)

**Goal:** Build the graph infrastructure and populate with core Ayurvedic knowledge

#### Week 1-2: Node Population

**Task 1.1: Constitutional Nodes**
- Research: Classical Ayurvedic texts (Charaka Samhita, Ashtanga Hridaya)
- Create: 15 constitutional type nodes with full property sets
- Properties: Qualities, vulnerabilities, strengths, optimal conditions
- Validation: Cross-reference with 3+ classical sources

**Task 1.2: Food Nodes (Phase 1: 100 most common foods)**
- Focus: Foods likely to appear in Western diet
- Properties: Taste (rasa), qualities (guna), dosha effects
- Sources: Ayurvedic food guidelines + modern nutritional science
- Format: JSON schema with standardized property structure

**Task 1.3: Symptom Nodes**
- Map: 60 most common symptoms from Sakhi user data
- Properties: Dosha signature, severity levels, related symptoms
- Connection: Link to existing soul state patterns (anxiety, fatigue, etc.)

**Task 1.4: Environmental Nodes**
- Seasons (6 Ayurvedic + 4 Western)
- Time windows (6 × 4-hour blocks)
- Climate types (5 variations)

**Deliverable:** 250+ nodes populated with validated properties

---

#### Week 3-4: Edge Relationships (Phase 1: Core relationships)

**Task 2.1: Imbalance-Symptom Edges (~300 edges)**
- Map: Which symptoms indicate which imbalances
- Weight: Strength of indication (0.0-1.0)
- Bidirectional: Symptom→Imbalance and Imbalance→Symptom
- Source: Classical texts + clinical observations

**Task 2.2: Food-Dosha Edges (~600 edges)**
- Map: Pacifies/Aggravates relationships
- Weight: Effect strength
- Example: `ghee --[PACIFIES 0.8]--> vata`
- Example: `cold_salad --[AGGRAVATES 0.9]--> vata`

**Task 2.3: Environmental Amplification Edges (~100 edges)**
- Seasonal aggravation
- Time-of-day dominance
- Climate effects
- Amplification factors (1.0-2.0)

**Task 2.4: Practice-Balance Edges (~200 edges)**
- Which practices balance which imbalances
- Time-of-day suitability
- Effectiveness weights

**Deliverable:** 1,200+ validated edges with weights

---

### Phase 2: Reasoning Engine (Weeks 5-8)

**Goal:** Build graph traversal and multi-hop reasoning capabilities

#### Week 5-6: Query Infrastructure

**Task 3.1: Graph Query Functions**
- PostgreSQL WITH RECURSIVE queries for multi-hop traversal
- Alternative: Neo4j or graph library if complexity demands
- Core queries:
  - `find_causes(symptom)` → chain to root imbalance
  - `find_balancing_foods(imbalance, context)` → personalized list
  - `find_practices(state, time, constitution)` → optimal activities
  - `explain_reasoning(recommendation)` → causal chain

**Task 3.2: Context Integration**
- Combine: User baseline + current state + environmental context
- Inputs: Prakruti, Vikriti, season, time, recent patterns, preferences
- Output: Contextualized query parameters

**Task 3.3: Scoring Algorithm**
- Multi-factor ranking: `score = effectiveness × context_match × personalization × timing`
- Contraindication filtering (hard constraints)
- Preference weighting (soft constraints)

**Deliverable:** Reasoning engine that can answer "Why?" and "What should I do?"

---

#### Week 7-8: Recommendation Generation

**Task 4.1: Recommendation Endpoints**
- Food recommendations (real-time, meal-specific)
- Practice recommendations (daily routine generator)
- Explanation engine (causal chain builder)

**Task 4.2: Protocol Builder**
- Daily rhythm protocol generator
- Weekly adjustment protocols
- Seasonal transition protocols
- Crisis intervention protocols (acute imbalance)

**Task 4.3: Natural Language Output**
- Convert graph paths → readable explanations
- User-facing language (Friction Framework terms)
- Practitioner-facing language (Ayurvedic terms, for internal/advanced users)

**Deliverable:** 5 new API endpoints exposing intelligent recommendations

---

### Phase 3: Personalization Layer (Weeks 9-12)

**Goal:** Make reasoning engine deeply personal to each user

#### Week 9-10: Constitutional Intelligence

**Task 5.1: Prakruti Assessment & Storage**
- Initial questionnaire (comprehensive dosha assessment)
- Baseline computation from first 30 days
- Store as: Operating System type + dosha proportions
- Update: Annual reassessment (Prakruti is stable but can refine with data)

**Task 5.2: Vikriti Tracking**
- Real-time current state from last 7 days
- Comparison to baseline (drift calculation)
- Friction State classification
- Trend detection (improving/worsening)

**Task 5.3: Personal Preference Integration**
- Food preferences & restrictions (vegetarian, allergies, cultural)
- Activity preferences (yoga vs. gym, morning vs. evening)
- Lifestyle constraints (work schedule, family)
- Location/climate adaptation

**Deliverable:** Every recommendation personalized to individual constitution + preferences

---

#### Week 11-12: Adaptive Learning

**Task 6.1: Feedback Loop**
- Track: Which recommendations user follows
- Track: Outcome (did Vata reduce after following protocol?)
- Learn: Adjust weights based on individual response
- Personal graph: User-specific edge weights over time

**Task 6.2: Ama (Residue) Tracking**
- Cumulative stress/toxin model
- Builds with: Poor sleep, irregular routine, contradictory practices
- Reduces with: Proper rest, fasting, aligned practices
- Affects: Recommendation intensity (gentle vs. aggressive)

**Task 6.3: Seasonal Memory**
- Remember: How user responded to previous winter/summer
- Predict: Likely imbalances this season based on history
- Proactive: Recommendations BEFORE imbalance manifests

**Deliverable:** System learns individual patterns and anticipates needs

---

### Phase 4: Advanced Intelligence (Weeks 13-16)

**Goal:** Sophisticated reasoning that rivals human practitioner

#### Week 13-14: Multi-Factor Synthesis

**Task 7.1: Amplification Modeling**
- Calculate: Combined effect of multiple factors
- Example: `total_vata_load = baseline_vata × season_factor × time_factor × stress_factor × sleep_factor`
- Non-linear effects: Some combinations multiply, not add
- Threshold detection: When does "elevated" become "crisis"?

**Task 7.2: Contraindication Logic**
- Hard constraints: Never recommend X if Y present
- Soft constraints: Reduce recommendation of A when B is elevated
- Interaction detection: Food/practice combinations to avoid
- Safety layer: Medical contraindications

**Task 7.3: Root Cause Analysis**
- Distinguish: Proximate cause vs. root cause
- Example: Anxiety (symptom) ← Vata excess (proximate) ← Irregular sleep (root)
- Recommendation priority: Address root, not just symptom
- Causal chain visualization for user

**Deliverable:** Sophisticated multi-hop reasoning that explains and prescribes at root level

---

#### Week 15-16: Temporal Intelligence

**Task 8.1: Chronobiology Integration**
- Dosha times: 6 windows per day
- Personal chronotype: Morning lark vs. night owl
- Ultradian rhythms: 90-120 min cycles
- Recommendations: "Best time for X is [when] because [why]"

**Task 8.2: Seasonal Protocols (Ritucharya)**
- 6 seasons: Early winter, late winter, spring, summer, monsoon, fall
- Transition periods: 2 weeks before season change (preventive)
- Regional adaptation: Northern vs. Southern hemisphere
- Protocol shifts: Food, practices, sleep timing

**Task 8.3: Life Cycle Adaptation**
- Age-based: Kapha (0-30), Pitta (30-60), Vata (60+)
- Gender-based: Menstrual cycle, pregnancy, menopause
- Life phase: Student, householder, retirement
- Adjust recommendations for life stage

**Deliverable:** Time-aware, life-stage-aware intelligent system

---

### Phase 5: Content Integration (Weeks 17-20)

**Goal:** Use graph to power educational content and distribution

#### Week 17-18: Graph-Powered Content

**Task 9.1: Insight Generation**
- Weekly: Graph analysis of user patterns → personalized insights
- Monthly: Seasonal readiness report
- Quarterly: Constitution evolution report
- Annual: Year-in-review with pattern analysis

**Task 9.2: Educational Explanations**
- Every recommendation: Graph-powered "Why this works" explanation
- User education: Teach Friction Framework through personalized examples
- Progressive disclosure: Start simple, reveal depth over time

**Task 9.3: Content Ideas from Graph**
- Graph queries reveal: Most common imbalance patterns
- Content topics: "Why everyone is Vata in winter" (seasonal blog post)
- User-generated: "Share your Operating System" feature
- Social proof: Anonymized pattern insights

**Deliverable:** Graph powers both recommendations AND content distribution

---

#### Week 19-20: Practitioner Mode

**Task 10.1: Advanced Graph Interface**
- Expose Ayurvedic terminology for practitioners
- Graph visualization tool (see reasoning chains)
- Manual override: Practitioner can adjust recommendations
- Case study builder: Document user journey with graph evidence

**Task 10.2: B2B Intelligence**
- Corporate dashboards: Team-level patterns
- Anonymized insights: "Your team shows 65% Intensity Friction"
- Intervention suggestions: Org-wide protocols
- ROI measurement: Friction reduction → productivity correlation

**Task 10.3: Integration Readiness**
- API: External practitioners can query graph for their clients
- White-label: Graph engine powers other apps
- Licensing model: Ayurvedic intelligence as a service

**Deliverable:** Graph becomes platform, not just internal tool

---

## Data Requirements

### Ayurvedic Knowledge Sources

**Classical Texts (Primary Sources):**
1. **Charaka Samhita** - Foundation of Ayurvedic medicine
   - Sutra Sthana (principles)
   - Vimana Sthana (specific measurements)
   - Sharira Sthana (body constitution)
   - Chikitsa Sthana (therapeutics)

2. **Sushruta Samhita** - Surgical & anatomical knowledge
   - Dosha imbalance management
   - Seasonal regimens (Ritucharya)

3. **Ashtanga Hridaya** - Condensed practical guide
   - Daily routine (Dinacharya)
   - Seasonal routine (Ritucharya)
   - Food guidelines (Ahara)

4. **Bhavaprakasha** - Material medica
   - Food properties
   - Herb/food combinations

**Modern Ayurvedic Sources:**
1. Dr. Vasant Lad - "The Complete Book of Ayurvedic Home Remedies"
2. Dr. David Frawley - "Ayurvedic Healing"
3. Dr. Robert Svoboda - Constitutional types
4. Academic research: PubMed Ayurvedic studies (validation)

**Founder's Personal Knowledge:**
- Years of study/practice
- Clinical observations
- Teacher lineage knowledge
- Cultural context understanding

### Data Structure Requirements

**Node Schema Example (Food):**
```json
{
  "id": "food_ghee",
  "name": "Ghee (Clarified Butter)",
  "category": "healthy_fats",
  "properties": {
    "rasa": ["sweet"],
    "guna": ["oily", "heavy", "smooth"],
    "virya": "cooling",
    "vipaka": "sweet",
    "prabhava": "rejuvenating",
    "doshaEffect": {
      "vata": {"effect": "pacifies", "strength": 0.8},
      "pitta": {"effect": "pacifies", "strength": 0.6},
      "kapha": {"effect": "aggravates", "strength": 0.3}
    },
    "elements": {"earth": 0.4, "water": 0.4, "fire": 0.2},
    "bestSeason": ["winter", "spring"],
    "bestTime": ["morning", "evening"],
    "quantity": "1-2 tsp per meal (constitution dependent)"
  },
  "contraindications": ["high_ama", "severe_kapha_excess"],
  "synergies": ["warm_milk", "kitchari", "root_vegetables"],
  "source": "Charaka Samhita, Sutrasthana 27",
  "modernScience": "Rich in butyrate (gut health), fat-soluble vitamins",
  "userFacingName": "Healthy clarified butter",
  "frictionFrameworkExplanation": "Grounding, nourishing fat that reduces Chaos Friction"
}
```

**Edge Schema Example:**
```json
{
  "id": "edge_ghee_pacifies_vata",
  "source": "food_ghee",
  "target": "dosha_vata",
  "relationship": "PACIFIES",
  "weight": 0.8,
  "mechanism": "Oily quality opposes dry quality of Vata",
  "context": {
    "amplifiedBy": ["winter", "vata_time"],
    "reducedBy": ["high_ama", "kapha_excess"]
  },
  "evidence": {
    "classical": "Charaka Samhita reference",
    "modern": "Clinical observations",
    "userFeedback": 0.85
  },
  "explanation": {
    "ayurvedic": "Snigdha guna (oily) pacifies Ruksha (dry) in Vata",
    "scientific": "Healthy fats support nervous system, reduce inflammation",
    "userFacing": "Nourishing fats calm scattered energy"
  }
}
```

### Volume Estimates

**Phase 1 (Core Knowledge):**
- Nodes: 300-400
- Edges: 1,200-1,500
- Time to build: 4 weeks (with expert guidance)

**Phase 2 (Expanded):**
- Nodes: 500-600
- Edges: 2,500-3,000
- Time: +4 weeks

**Phase 3 (Comprehensive):**
- Nodes: 800-1,000
- Edges: 5,000-6,000
- Time: +8 weeks

---

## Validation Strategy

### How to Ensure Accuracy

**1. Classical Text Validation**
- Every node/edge: Cite source (Charaka Samhita verse #)
- Cross-reference: Minimum 2-3 classical sources agree
- Document: Where sources diverge, note lineage differences

**2. Expert Review**
- Founder's deep knowledge validates interpretations
- Optional: Consulting Ayurvedic practitioner review
- Community: Other practitioners can flag issues

**3. User Outcome Validation**
- Track: Recommendation → User follows → State improves?
- A/B test: Graph-driven vs. hardcoded recommendations
- Feedback loop: Users report effectiveness
- Adjust weights based on real-world outcomes

**4. Scientific Correlation**
- Map Ayurvedic concepts → modern research where possible
- Example: Vata aggravation → HPA axis dysregulation research
- Not to prove Ayurveda (it's validated), but to strengthen credibility

**5. Edge Case Testing**
- Test: Complex multi-factor scenarios
- Example: "Vata-Pitta constitution + Kapha imbalance + Summer + Night shift worker"
- Ensure: Graph doesn't break, produces sensible recommendations

### Quality Metrics

**Accuracy:**
- Source citation: 100% of nodes/edges have classical reference
- Expert review: 100% of core relationships validated
- User outcome: >70% report recommendations helpful

**Completeness:**
- Coverage: Top 200 foods (80% of Western diet)
- Symptoms: 60+ most common (95% of user complaints)
- Practices: 80+ (comprehensive lifestyle coverage)

**Consistency:**
- No contradictions: If A pacifies Vata, A should not aggravate Vata
- Bidirectional edges: Symptom→Imbalance matches Imbalance→Symptom
- Transitive logic: If A→B and B→C, then A→C should be valid

---

## Success Metrics

### Technical Metrics

**Graph Quality:**
- Node count: 500+ by end of Phase 2
- Edge count: 2,500+ by end of Phase 2
- Average node degree: 8-12 (well-connected graph)
- Source citation: 100%

**Reasoning Performance:**
- Query speed: <500ms for single recommendation
- Multi-hop traversal: <1s for 3-4 hop reasoning
- Explanation generation: <200ms

**Accuracy:**
- Expert validation: >95% accuracy on core relationships
- User outcome: >70% report improvement after following recommendations
- A/B test: Graph-driven outperforms hardcoded by >20%

### Business Metrics

**User Experience:**
- Recommendation relevance: >80% users rate as "very relevant"
- Friction reduction: >50% of users show measurable dosha balance improvement in 30 days
- Retention: >40% at Day 30 (up from baseline)
- Engagement: Daily check-in rate >60%

**Differentiation:**
- Brand perception: "Sakhi's recommendations are uniquely accurate" (survey)
- Competitive moat: Competitors can't replicate without Ayurvedic expertise
- Content virality: Graph-powered insights drive shares

**Monetization:**
- Premium conversion: >15% (justified by recommendation quality)
- B2B interest: 10+ corporate pilots
- Practitioner licensing: 5+ practitioners want API access

### Learning Metrics

**Adaptive Intelligence:**
- Personal edge weights: 50+ edges personalized per user after 90 days
- Prediction accuracy: >70% on "likely imbalance this season"
- Proactive value: >30% of users report "Sakhi warned me before I noticed"

---

## Risk Mitigation

### Technical Risks

**Risk 1: Graph Complexity**
- Problem: Graph becomes too complex to manage
- Mitigation:
  - Start small (300 nodes, 1,200 edges)
  - Expand only validated relationships
  - Use graph visualization tools to spot issues
  - Automated consistency checks

**Risk 2: Query Performance**
- Problem: Multi-hop queries too slow
- Mitigation:
  - Index critical paths
  - Cache common queries
  - Precompute frequent traversals
  - Consider Neo4j if PostgreSQL insufficient

**Risk 3: Data Quality**
- Problem: Incorrect relationships break recommendations
- Mitigation:
  - Source citation required
  - Expert review layer
  - User feedback flags errors
  - Version control (rollback bad edges)

### Business Risks

**Risk 4: Cultural Appropriation Backlash**
- Problem: Accused of exploiting Ayurveda
- Mitigation:
  - Founder's authentic knowledge & credentials
  - Credit Ayurveda in investor/practitioner materials
  - Not "selling Ayurveda" - using as infrastructure
  - Hire Ayurvedic consultants (cultural authenticity)

**Risk 5: Medical Liability**
- Problem: Health recommendations cause harm
- Mitigation:
  - Disclaimer: "Not medical advice, consult doctor"
  - Contraindication layer (safety checks)
  - Focus on preventive wellness, not disease treatment
  - Legal review of all recommendations

**Risk 6: User Complexity**
- Problem: Users confused by recommendation depth
- Mitigation:
  - Progressive disclosure (simple first, depth optional)
  - User-facing language (Friction Framework, not Ayurveda)
  - Visual explanations (causal chains as diagrams)
  - Onboarding: Teach framework gradually

### Execution Risks

**Risk 7: Time/Resource Intensive**
- Problem: 16-20 weeks is long, expensive
- Mitigation:
  - Phase 1-2 delivers 80% of value (8 weeks)
  - Phase 3-5 are enhancements, not blockers
  - Validate with users after Phase 2 before continuing
  - Can hire Ayurvedic researcher to accelerate

**Risk 8: Founder Dependency**
- Problem: Only founder has deep Ayurvedic knowledge
- Mitigation:
  - Document everything (sources, reasoning)
  - Build replicable process (future team can extend)
  - Record founder's decision rationale
  - Consider co-developing with Ayurvedic consultant

---

## Conclusion

### The Opportunity

Building the Ayurvedic reasoning engine deeper transforms Sakhi from:
- **Pattern detector** → **Intelligent practitioner**
- **Symptom tracker** → **Root cause analyzer**
- **Generic recommendations** → **Personalized prescriptions**
- **Feature parity** → **Unfair advantage**

### The Investment

**Time:** 16-20 weeks to full depth (8 weeks for 80% value)
**Expertise:** Founder's Ayurvedic knowledge + development resources
**Cost:** Primarily time (+ optional Ayurvedic consultant)

### The Return

**User Value:**
- Recommendations that actually work (higher retention)
- Understanding WHY (education builds trust)
- Proactive prevention (anticipate imbalances)
- Personalized to individual constitution

**Business Value:**
- Competitive moat competitors can't replicate
- Premium pricing justified ($20-30/month)
- Content distribution (graph insights → articles/videos)
- Platform play (license to other apps, practitioners)
- Category leadership ("The Ayurvedic intelligence platform")

### The Decision

**This is the 9.5/10 strategy implemented at the technical level.**

The Friction Framework is the user-facing story.
The Ayurvedic Knowledge Graph is the hidden engine that makes it accurate.

Without this depth, Sakhi is another journaling app with AI insights.
With this depth, Sakhi is an intelligent practitioner in your pocket.

**That's the difference between a feature and a fundable company.**

---

*Document Version: 1.0*
*Created: January 2026*
*Next Steps: Review with co-founder, validate Phase 1 scope, begin node population*
