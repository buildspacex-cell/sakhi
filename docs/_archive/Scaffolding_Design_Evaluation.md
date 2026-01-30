# Scaffolding Design Evaluation: Principles & Contract v1

**Evaluation Date**: January 8, 2026
**Evaluator**: Claude Sonnet 4.5
**Scope**: Assessment of Scaffolding Layer design principles and contract against implementation
**Status**: Design principles are correct; implementation needs alignment

---

## Document Purpose

This document evaluates two foundational Scaffolding design documents:
1. **Scaffolding Design Principles v1** (10 principles)
2. **Scaffolding Contract v1** (situational intelligence-aligned)

Against:
- Current implementation (from [Scaffolding_Layer_Audit.md](Scaffolding_Layer_Audit.md))
- Sakhi's architectural philosophy
- Layer 3 (Sensemaking) boundaries
- Layer 5 (Reflection) boundaries

---

## Executive Summary

### Overall Verdict: ✅ **Design is Correct; Implementation Must Follow**

**The principles and contract represent the architecturally correct way to design scaffolding for a non-coercive personal intelligence system.**

However:
- Current implementation **violates 5 of 10 core principles**
- Fixed-time scheduling contradicts adaptive design
- Language generation happens in Layer 4 (should be Layer 5)
- Suppression integration is incomplete
- Evaluative language persists in several components

**Recommendation**: Principles are the north star. Code must be brought into alignment, not vice versa.

---

## Part 1: Scaffolding Design Principles v1

### Principle 0: Purpose - **STRONG** ✅

**Statement**: "If a scaffolding component violates these principles, the component is wrong, not the principle."

**Assessment**: Clear, non-negotiable hierarchy. Establishes principles as authoritative.

**Alignment with Sakhi Philosophy**: Matches vision in [00_Canonical_Index.md](../00_Canonical_Index.md) - personal intelligence without authority.

**Status**: ✅ Foundational and correct

---

### Principle 1: Silence Is the Default - **CORRECT BUT VIOLATED** ⚠️

**Statement**: "Scaffolding must assume no action unless explicitly justified."

**Implications**:
- Presence must be earned, not assumed
- Time-based triggers alone are insufficient
- "Helpful" is not valid justification

**Current Violations** (from [Scaffolding_Layer_Audit.md](Scaffolding_Layer_Audit.md)):
- Morning scaffolds (preview, ask, momentum) - 6:00-6:15 AM fixed daily
- Micro scaffolds (momentum, recovery) - 9 AM / 2 PM fixed
- Evening scaffolds (closure, reflection) - 8-9 PM fixed
- All auto-generated without suppression checks

**What Must Change**:
- Default: silence
- Trigger: `suppression_check.allow == true && context_justifies == true`
- Clock time alone is never sufficient

**Audit Finding**: 15 of 27 scaffolding components run on fixed schedules without adaptive gating.

**Status**: ✅ Principle correct | ❌ Implementation violates

---

### Principle 2: Signals Before Language - **ARCHITECTURALLY CORRECT** ✅

**Statement**: "Scaffolding produces signals and permissions, not words."

**Implications**:
- Decisions made in structured form first
- Language is downstream, optional, replaceable
- LLMs never part of decision, only expression

**Current Violations** (from audit):
- `focus_path/engine.py` - Generates `focus_hint` via LLM in Layer 4
- `mini_flow/engine.py` - Generates `session_hint`, `prep_message` via LLM
- `morning_momentum/engine.py` - Generates motivational language via LLM
- `micro_recovery/engine.py` - Generates recovery prompt language via LLM
- `nudge/engine.py` - Generates `nudge_text` via LLM
- `evening_closure_worker.py` - Generates closure message via LLM

**Correct Architecture**:
```
Layer 4 (Scaffolding):
  → Emits structured signal: {
      "should_focus": true,
      "suggested_task_id": "abc123",
      "confidence": 0.8,
      "reason_code": "high_rhythm_aligned_goal"
    }

Layer 5 (Reflection):
  → Converts signal to language when user requests
```

**What Must Change**:
- Move all LLM calls out of Layer 4 workers
- Layer 4 emits JSON signals only
- Layer 5 reads signals and generates language on user request

**Audit Finding**: 10 of 27 components generate language directly in Layer 4.

**Status**: ✅ Principle correct | ❌ Layer boundary violated

---

### Principle 3: User Agency Overrides System Initiative - **CORRECT** ✅

**Statement**: "User-initiated scaffolding always has priority over system-initiated."

**Implications**:
- On-demand requests are safe by default
- Proactive scaffolds require higher justification
- Ignoring is meaningful signal

**Current Alignment**:
- ✅ `micro_journey/engine.py` - On-demand only (user requests task breakdown)
- ⚠️ Most scaffolds are system-initiated (morning, micro, evening, nudges)

**Implementation Gap**:
- Pacing controller exists but unclear if it demotes based on ignoring
- No visible user control: "No proactive scaffolds" toggle

**What Must Exist**:
- User preference: Silence mode (suppress all proactive)
- Behavioral signal: Repeated ignoring → reduce initiative
- Gate logic: `system_initiated → requires rhythm > 0.5 && conflict == none && last_interaction > 4hr`

**Status**: ✅ Principle correct | ⚠️ Enforcement needs strengthening

---

### Principle 4: Time Is Adaptive, Never Assumed - **CRITICAL & VIOLATED** ⚠️

**Statement**: "Time-of-day is context, not instruction."

**Implications**:
- "Morning", "afternoon", "evening" are labels, not mandates
- Fixed schedules must yield to rhythm, suppression, behavior history
- No scaffold may rely solely on clock time

**Current Violations** (from audit):
- Morning preview: 6:00 AM fixed
- Morning ask: 6:10 AM fixed
- Morning momentum: 6:15 AM fixed
- Micro momentum: 9:00 AM fixed
- Micro recovery: 2:00 PM fixed
- Evening closure: 8:00 PM fixed
- Daily reflection: 9:00 PM fixed

**Existing Infrastructure** (from audit):
- ✅ `cadence_calculator.py` - Calculates optimal timing from rhythm slots
- ✅ `pacing_controller.py` - Adjusts timing every 6 hours
- ❌ Not wired as gates to schedulers

**What Principle Demands**:
- Actual trigger: `rhythm_state.time_slots["morning"].energy > 0.6 && suppression.allow == true`
- Night-shift user gets "morning" scaffold at 2 PM
- Exhausted user gets no scaffold even if clock says 6 AM

**What Must Change**:
```python
# WRONG (current)
schedule_job(morning_preview, cron="0 6 * * *")

# RIGHT (required)
schedule_job(check_should_morning_scaffold_run, cron="0 * * * *")
  → If conditions met: run morning_preview
  → If not met: defer 1 hour, retry
  → If deferred 3x: cancel for day
```

**Status**: ✅ Principle correct | ❌ Severely violated by fixed schedules

---

### Principle 5: Scaffolding Never Evaluates the Person - **CORRECT & CRITICAL** ✅

**Statement**: "Scaffolding may describe conditions, never judge progress or character."

**Implications**:
- No "you did well", "you made progress", "you should feel..."
- No implicit scoring of person
- No identity reinforcement

**Current Violations** (from audit):
- `evening_closure_worker.py`: "you made progress on..." (evaluative)
- `morning_preview/engine.py`: "your day looks..." (characterization)
- `morning_momentum/engine.py`: "today's energy suggests..." (implicit evaluation)

**Why This Matters**:
- Evaluation implies judgment
- Judgment implies authority
- Authority violates "Inner Human Mirror" philosophy

**What's Allowed vs Not Allowed**:

| ✅ Allowed (Factual) | ❌ Not Allowed (Evaluative) |
|---------------------|----------------------------|
| "Rhythm state shows energy at 0.7 in morning slot" | "You have good energy this morning" |
| "3 of 5 tasks completed" | "You made good progress" |
| "Load increased from 5 to 8 this week" | "You're overworking yourself" |

**What Must Change**:
- LLM prompts must include: "State observations only. No evaluation. No praise. No judgment."
- Remove: "you made progress", "you're doing well", "today looks good"
- Test: If language could feel like performance review → wrong

**Status**: ✅ Principle correct | ⚠️ Language audit required

---

### Principle 6: Suppression Is Global and Mandatory - **CRITICAL FINDING** ⚠️

**Statement**: "If suppression logic exists, it must apply everywhere."

**Implications**:
- No engine bypasses suppression
- Crisis, exhaustion, volatility always win
- Silence beats cleverness

**Current State** (from audit):
- ✅ `suppression_engine.py` exists - central logic
- ✅ `guardrail.py` exists - rule-based gates
- ⚠️ **Unclear which scaffolds actually call it**
- ❌ No evidence morning/micro/evening scaffolds check suppression

**What Principle Demands**:
- Every system-initiated scaffold must call `suppression_engine.check()` FIRST
- Rules: rhythm < 0.3, emotion volatility > 0.7, conflict present, crisis language, silence mode
- Return: `allow` / `suppress` / `defer`
- If suppress/defer → scaffold does not run

**Required Implementation Pattern**:
```python
# WRONG (current pattern)
def morning_preview_worker(person_id):
    preview = generate_morning_preview(person_id)
    save(preview)

# RIGHT (required pattern)
def morning_preview_worker(person_id):
    suppression = suppression_engine.check(person_id, "morning_preview")

    if suppression == "suppress":
        log_suppressed("morning_preview", person_id)
        return None

    if suppression == "defer":
        schedule_retry_in_1_hour("morning_preview", person_id)
        return None

    preview = generate_morning_preview(person_id)
    save(preview)
```

**Audit Finding**: Suppression architecture exists but integration coverage incomplete.

**Status**: ✅ Principle correct | ❌ Integration incomplete

---

### Principle 7: Scaffolding Must Be Reversible and Forgettable - **SOUND** ✅

**Statement**: "Nothing scaffolding does should harden into identity, memory, or truth."

**Implications**:
- Scaffolding outputs are ephemeral
- No permanent writes to personal_model unless explicitly allowed
- No learning loops that entrench behavior prematurely

**Current State** (from audit):
- Daily scaffold states written to `personal_model`:
  - `morning_preview_state`, `morning_ask_state`, `morning_momentum_state`
  - `micro_momentum_state`, `micro_recovery_state`
  - `focus_path_state`, `mini_flow_state`
  - `daily_reflection_state`, `closure_state`

**Risk**:
- If these states persist and feed Sensemaking (Layer 3), they create feedback loops
- Scaffold suggestions could accidentally influence "what person values"

**What Principle Demands**:
- Scaffold states should live in **separate cache tables**, not `personal_model`
- TTL: 48 hours maximum
- Never read by Sensemaking workers (Layer 3)
- Only read by Layer 4 (pacing) and Layer 5 (language generation)

**Storage Architecture Review Needed**:
```sql
-- WRONG (current)
personal_model:
  soul_state (Layer 3)
  rhythm_state (Layer 3)
  morning_preview_state (Layer 4) ← Risk of cross-contamination

-- RIGHT (required)
personal_model:
  soul_state (Layer 3)
  rhythm_state (Layer 3)

scaffold_cache:
  morning_preview_state (Layer 4, TTL 48hr)
```

**Status**: ✅ Principle correct | ⚠️ Storage architecture needs review

---

### Principle 8: Protective Gates Allowed; Direction Is Not - **CLEAR BOUNDARY** ✅

**Statement**: "Scaffolding may prevent harm, but may not prescribe direction."

**Implications**:
- Blocking overload is valid
- Slowing commitments is valid
- Choosing goals for user is not valid

**Current Alignment** (from audit):
- ✅ `planner_commit_gate.py` - Warns/blocks overload (protective) ✓
- ⚠️ `focus_path/engine.py` - Suggests which task to do (directive) ✗
- ⚠️ `mini_flow/engine.py` - Suggests flow session structure (directive) ✗

**What's Allowed**:

| ✅ Protective (Allowed) | ❌ Directive (Not Allowed) |
|------------------------|---------------------------|
| "Current load is high (8/10). Adding this goal would increase fragmentation." | "You should focus on Goal A instead of Goal B" |
| "Rhythm exhausted. Block new commitments until recovery." | "Now is a good time to work on this task" |

**Gray Area - Acceptable If**:
- "Here are 3 tasks that align with current rhythm" (filtered list, not command)
- Acceptable if: User requested suggestions, list is unranked or confidence-scored, user chooses

**What Must Change**:
- `focus_path` should emit: "Tasks ABC have alignment > 0.7 with rhythm" (factual)
- Not: "You should do Task A" (directive)

**Status**: ✅ Principle correct | ⚠️ Requires suggestion vs gate clarification

---

### Principle 9: Consent Can Be Implicit, But Must Be Detectable - **SOPHISTICATED** ✅

**Statement**: "Scaffolding may infer consent — but must be able to detect its absence."

**Implications**:
- Ignoring, dismissing, resisting = consent withdrawal
- Silence patterns matter
- Consent is dynamic, not binary

**Current State** (from audit):
- ✅ `pacing_controller.py` exists - adjusts timing based on response patterns
- ⚠️ Implementation unclear - does it detect ignoring/dismissing?

**What Principle Demands**:
- Track scaffold interaction rates:
  - `morning_preview` shown 30x, opened 3x → 10% engagement → consent withdrawn
- Track suppression frequency:
  - User manually dismisses 5 days in row → reduce initiative
- Track timing patterns:
  - User never interacts before 9 AM → shift timing

**Required Implementation**:
```sql
CREATE TABLE scaffold_interactions (
  scaffold_type TEXT,
  shown_at TIMESTAMP,
  interacted BOOLEAN,
  dismissed BOOLEAN,
  ignored BOOLEAN,
  person_id TEXT
);
```

**Pacing Logic**:
- Weekly: Calculate engagement rate per scaffold type
- If engagement < 20% for 2 weeks → reduce frequency or stop
- If timing misalignment → shift schedule

**Status**: ✅ Principle correct | ⚠️ Engagement tracking verification needed

---

### Principle 10: Scaffolding Exists to Reduce Intrusion - **PROFOUND** ✅

**Statement**: "The success of scaffolding is measured by how little it needs to act."

**Implications**:
- Fewer interventions over time = success
- Calm systems intervene less, not more
- Presence is earned, not constant

**Why This Matters**:
- **Typical AI framing**: "How can we help more?" → maximize engagement
- **Sakhi's framing**: "How can we help less?" → minimize intrusion
- Success metric: User **needs** scaffolding less over time

**What This Demands**:

**Metrics Must Include**:
- Scaffold withhold rate (% of potential scaffolds not sent)
- Suppression rate (% of scaffolds suppressed)
- User-initiated vs system-initiated ratio
- Time between scaffolds (goal: increase)

**Anti-Metric**: Total scaffold count (don't maximize this)

**Implementation**:
- Dashboard shows: "Scaffolding withheld 45 times this week (rhythm low, conflict present, recent interaction)"
- This is **good**, not failure

**Status**: ✅ Principle correct | ⚠️ Metrics inversion required

---

### Final Lock Statement Evaluation

> "Sensemaking tells us what's true.
> Scaffolding decides whether to act — and usually chooses not to.
> Reflection speaks only when invited."

**Assessment**: ✅ **Perfect Formulation**

**Breakdown**:
- Layer 3 (Sensemaking): Truth layer, deterministic, always runs
- Layer 4 (Scaffolding): Decision layer, **default = silence**
- Layer 5 (Reflection): Language layer, user-initiated

**"Usually chooses not to"** is the key phrase. This is the design stance.

---

## Part 2: Scaffolding Contract v1 (Situational Intelligence-Aligned)

### Core Contract Statement - **POWERFUL FRAMING** ✅

**Statement**: "Scaffolding exists to surface situational relevance, capacity, and readiness — using maximal contextual intelligence — while strictly gating interpretation, authority, and prescription."

**Key Insight**: **"Understanding is uncapped, intervention is gated"**

**Assessment**: This resolves a potential tension:
- Question: "If Sakhi has rich situational awareness (location, calendar, body rhythms), does restraint mean ignoring it?"
- Answer: **No. Perception is uncapped. Expression is gated.**

**Why This Matters**:
- Sakhi may **perceive** that user is near cake shop with "buy cake" on list
- Sakhi may **infer** that now is contextually relevant moment
- Sakhi is **still gated** by suppression, consent, and non-directive framing

**This is sophisticated design**: Intelligence ≠ interference

**Status**: ✅ Architecturally mature

---

### Section 2: What Is Uncapped (Hard Allow) - **CLEAR** ✅

**Allowed Contextual Signals**:
- Location & proximity
- Time windows & gaps
- Calendar state
- Task/to-do presence
- Environmental affordances (shops, venues, events)
- Body rhythms (energy, cycle phase)
- Emotional signals (activation, volatility)
- Forecast windows (risk/opportunity)
- Social context (waiting, travel, accompaniment)

**Key Phrase**: "There is no cap on perception or correlation."

**Assessment**: This is the correct stance for a personal intelligence system.

**Why It Works**:
- Sakhi may **know** user is exhausted, near coffee shop, has 30 min free
- Knowing this is fine
- **Acting on it** requires gates

**Status**: ✅ Correct framing

---

### Section 3: What Is Gated (Hard Constraint) - **CRITICAL** ✅

**Scaffolding Must NOT**:
- Invent intent
- Assign meaning
- Judge progress
- Moralize time use
- Prescribe optimal behavior
- Harden suggestions into identity/memory

**Assessment**: These are the exact violations to prevent.

**Real Risk Examples**:
- ❌ "You're near gym and haven't exercised this week" (moralizing)
- ❌ "This is a good time to be productive" (prescriptive)
- ❌ "You always procrastinate on Mondays" (identity hardening)

**Correct Alternative**:
- ✅ "Gym is 200m away. 'Go to gym' is on your list." (factual)

**Status**: ✅ Correct boundaries

---

### Section 4: Scaffolding Output Types - **EXCELLENT TAXONOMY** ✅

#### Type A: Contextual Recall (Low Sensitivity) 🟢

**Definition**: Surfacing user-authored intent when situational relevance high.

**Examples**:
- "You're near cake shop — 'buy birthday cake' is on your list."
- "Dry cleaning is open nearby."

**Rules**:
- Intent must already exist (task, note, calendar)
- No confirmation required
- One-shot, dismissible
- No interpretation or framing

**Assessment**: This is the **safest** and most obviously valuable scaffold type.

**Why Safe**:
- User wrote the intent (not Sakhi)
- Context makes it relevant (not arbitrary)
- Surfacing, not creating

**Status**: ✅ Well-defined, low-risk

---

#### Type B: Capacity Surfacing (Neutral) 🟡

**Definition**: Surfacing available space (time, energy, attention) without filling it.

**Examples**:
- "You have about 2 hours free before match starts."
- "Your afternoon looks unscheduled."

**Rules**:
- State facts only
- May include neutral invitation ("Want to use it or just rest?")
- No suggestions unless user engages

**Assessment**: This is sophisticated restraint.

**Why It Works**:
- Sakhi notices the space
- Sakhi doesn't prescribe how to use it
- User decides (or chooses rest)

**Status**: ✅ Exemplifies non-directive support

---

#### Type C: Sensitive State Check (Confirmation Required) 🟠

**Definition**: Surfacing probabilistic bodily/emotional states that require validation.

**Examples**:
- Possible period onset
- Illness/fatigue
- Emotional overload

**Mandatory Flow**:
1. Internal signal only
2. Gentle confirmation question
3. No support action unless user confirms

**Rules**:
- Use uncertainty language ("might", "feels like")
- One question only
- Drop entirely on "no"

**Assessment**: This is the **most sensitive** scaffold type and requires highest care.

**Why Critical**:
- Sakhi is **inferring** bodily/emotional state (not fact)
- User may disagree
- Confirmation required before any support

**Example Flow**:
```
Sakhi (internal): Signal suggests possible period onset (confidence 0.7)
Sakhi (to user): "Feeling like your cycle might be starting?"
User: "No, just tired."
Sakhi: [Drops period support, does not persist in memory]
```

**Status**: ✅ Appropriately gated

---

#### Type D: Prescriptive Optimization (Disallowed) 🔴

**Definition**: Any scaffold that tells user what they should do, why it matters, or what it says about them.

**Examples (Not Allowed)**:
- ❌ "This is a good time to be productive"
- ❌ "You should slow down today"
- ❌ "You've been procrastinating"
- ❌ "Today looks like high-performance day"

**Assessment**: Clear red line.

**Why Disallowed**:
- Implies authority
- Prescribes behavior
- May reinforce identity ("you're a procrastinator")

**Status**: ✅ Correct prohibition

---

### Section 5: Signals Before Language - **ARCHITECTURAL** ✅

**Requirement**: All scaffolding decisions must first emit structured signal.

**Example Signal**:
```json
{
  "scaffold_type": "contextual_recall | capacity_surface | sensitive_check",
  "confidence": 0.0-1.0,
  "basis": ["signal_1", "signal_2"],
  "sensitivity": "low | medium | high"
}
```

**Only after this may language be generated downstream.**

**Assessment**: This enforces Layer 4 / Layer 5 separation.

**Status**: ✅ Matches Principle 2

---

### Section 6: Silence & Suppression Rules - **CRITICAL** ✅

**Rules**:
- Silence is always valid outcome
- Central suppression engine must be consulted for:
  - Exhaustion
  - Emotional volatility
  - Crisis signals
  - Recent interaction overload
- Suppression beats relevance
- Ignored scaffolds reduce future initiative

**Assessment**: Matches Principle 1 & 6.

**Status**: ✅ Consistent with principles

---

### Section 7: Time & Cadence Rules - **CRITICAL** ✅

**Rules**:
- Clock time alone is never sufficient
- Event-based relevance > schedule-based delivery
- Fixed schedules are candidates, not mandates
- Cadence controllers may delay, defer, cancel any scaffold

**Assessment**: Matches Principle 4.

**Status**: ✅ Consistent with principles

---

### Section 8: Consent Model - **EXPLICIT TAXONOMY** ✅

| Scaffold Type | Consent Model |
|--------------|---------------|
| Contextual Recall | Implicit (task exists) |
| Capacity Surfacing | Soft (invitation) |
| Sensitive State | Explicit confirmation required |
| Suggestions | Only after engagement |

**Assessment**: Clear consent gradations.

**Status**: ✅ Well-defined

---

### Section 9: Persistence Rules - **CRITICAL** ✅

**Rules**:
- Scaffolding outputs are ephemeral
- No scaffolding output may:
  - Update identity
  - Harden into personal_model truth
  - Bias sensemaking directly
- All scaffold states must be discardable

**Assessment**: Matches Principle 7.

**Status**: ✅ Consistent with principles

---

### Section 10: Success Metric - **REFRAMED** ✅

**Statement**: "Scaffolding succeeds when it helps user notice the right thing — and then steps back."

**Key Metric**: "Fewer interventions over time = higher intelligence."

**Assessment**: Matches Principle 10.

**Status**: ✅ Consistent with principles

---

### Final Lock (Updated Framing) - **POWERFUL** ✅

> "Sakhi's situational intelligence is uncapped.
> Its authority is deliberately restrained.
> Its support is conditional, contextual, and optional."

**Assessment**: This is the synthesis statement.

**Three-Part Structure**:
1. **Intelligence**: Uncapped perception/correlation
2. **Authority**: Deliberately restrained (design choice, not limitation)
3. **Support**: Conditional (gated), contextual (relevant), optional (user decides)

**Status**: ✅ Perfect formulation

---

## Critical Implementation Gaps

### Summary of Violations

| Principle/Contract Element | Status | Severity |
|---------------------------|--------|----------|
| 1. Silence is default | ❌ Violated | CRITICAL |
| 2. Signals before language | ❌ Violated | HIGH |
| 3. User agency priority | ⚠️ Partial | MEDIUM |
| 4. Time is adaptive | ❌ Violated | CRITICAL |
| 5. No evaluation | ⚠️ Partial | HIGH |
| 6. Suppression mandatory | ❌ Incomplete | CRITICAL |
| 7. Reversible/forgettable | ⚠️ Storage risk | MEDIUM |
| 8. Protective not directive | ⚠️ Gray areas | MEDIUM |
| 9. Consent detectable | ⚠️ Tracking unclear | MEDIUM |
| 10. Reduce intrusion | ⚠️ No metrics | LOW |

**Violations by Severity**:
- **CRITICAL**: 3 (Principles 1, 4, 6)
- **HIGH**: 2 (Principles 2, 5)
- **MEDIUM**: 4 (Principles 3, 7, 8, 9)
- **LOW**: 1 (Principle 10)

---

### Required Changes (Prioritized)

#### Phase 1: Protect (CRITICAL - Immediate)

**1. Wire Suppression to All System-Initiated Scaffolds**
- Every morning/micro/evening worker must call `suppression_engine.check()` first
- Default to silence if suppression check unclear
- Log all suppressions for metrics

**2. Implement Adaptive Time Gates**
- Replace fixed-time triggers with: `should_scaffold_run(person_id, type)`
- Check: rhythm + suppression + engagement history
- Defer or cancel if conditions not met

**3. Emergency Suppression Rules**
- If `rhythm_state.overall < 0.3` → suppress all proactive scaffolds
- If `emotion_state.volatility > 0.7` → suppress all proactive scaffolds
- If `conflict_state.active == true` → suppress all proactive scaffolds
- If crisis language detected in recent journal → suppress all for 24hr

---

#### Phase 2: Separate (HIGH - Short-term)

**4. Refactor Layer 4 to Emit Signals Only**
- Move all LLM calls from Layer 4 workers to Layer 5
- Layer 4 emits structured JSON only
- Example:
  ```python
  # Layer 4
  def focus_path_worker(person_id):
      return {
          "scaffold_type": "capacity_surface",
          "suggested_tasks": ["task_1", "task_2"],
          "confidence": 0.8,
          "basis": ["rhythm_high", "alignment_score"]
      }

  # Layer 5 (called when user opens app)
  def generate_focus_language(signal):
      return llm.generate(signal)  # Language on demand
  ```

**5. Audit and Remove Evaluative Language**
- Review all LLM prompts for:
  - Praise/judgment ("you did well")
  - Characterization ("your day looks good")
  - Moralizing ("you should...")
- Replace with factual state descriptions
- Test: "Would this feel like performance review?" → remove

---

#### Phase 3: Adapt (MEDIUM - Medium-term)

**6. Implement Engagement Tracking**
```sql
CREATE TABLE scaffold_interactions (
  scaffold_type TEXT,
  shown_at TIMESTAMP,
  interacted BOOLEAN,
  dismissed BOOLEAN,
  ignored BOOLEAN,
  person_id TEXT,
  context JSONB
);
```
- Track all scaffold deliveries and responses
- Pacing controller consumes weekly
- Reduce initiative when engagement < 20%

**7. Separate Scaffold State Storage**
- Move scaffold states out of `personal_model`
- Create: `scaffold_cache` table with TTL
- Ensure Layer 3 (Sensemaking) never reads scaffold states

**8. Implement Output Type Taxonomy**
- Tag all scaffolds as Type A/B/C
- Enforce consent model per type
- Type C (sensitive) requires explicit confirmation flow

---

#### Phase 4: Measure (LOW - Long-term)

**9. Implement Metrics Inversion**
- Track withhold rate (% scaffolds not sent due to gates)
- Track suppression rate
- Track user-initiated vs system-initiated ratio
- Track time-between-scaffolds (goal: increase)
- Dashboard: "Scaffolding withheld 45x this week" (positive metric)

**10. Add Consent Detection**
- Weekly: Calculate engagement rates per scaffold type
- If engagement declines → reduce frequency
- If timing misaligned → shift schedule
- If repeatedly ignored → stop scaffold type

---

## Final Assessment

### Is This the Right Way to Design Scaffolding?

**Answer: YES**

These principles and contract are **architecturally correct, philosophically aligned, and operationally sound** for a non-coercive personal intelligence system that respects human agency.

**They are NOT correct for**:
- Productivity optimization systems (which prescribe)
- Behavior change apps (which evaluate)
- Coaching platforms (which direct)
- Engagement-maximizing social apps (which intrude)

**But for Sakhi's vision** ("Inner Human Mirror", not optimizer or coach):
- ✅ Philosophically aligned
- ✅ Architecturally sound
- ✅ Operationally enforceable
- ✅ Ethically grounded

---

### The Implementation Reality

**The principles are correct. The implementation violates them.**

**Current State**:
- 5 of 10 core principles violated
- Fixed-time scheduling contradicts adaptive design
- Language generation in wrong layer
- Suppression integration incomplete
- Evaluative language persists

**Path Forward**:
- Principles are the north star
- Code must follow principles
- Do not weaken principles to match code
- Bring implementation into alignment

**Estimated Effort**:
- Phase 1 (Protect): 1-2 weeks
- Phase 2 (Separate): 2-3 weeks
- Phase 3 (Adapt): 2-3 weeks
- Phase 4 (Measure): 1 week

**Total**: 6-9 weeks to full alignment

---

### Key Architectural Insights

**1. "Understanding is uncapped, intervention is gated"**
- Sakhi may perceive everything
- Sakhi acts rarely
- Intelligence ≠ interference

**2. "Signals before language"**
- Layer 4 decides
- Layer 5 speaks
- Never collapse boundary

**3. "Silence is the default"**
- Not: "Should we act?"
- Instead: "Why should we act?"
- Default answer: We shouldn't

**4. "Fewer interventions = success"**
- Not: Maximize engagement
- Instead: Minimize intrusion
- Success: User needs less over time

---

## Conclusion

**The Scaffolding Design Principles v1 and Scaffolding Contract v1 represent the correct architectural approach for Sakhi.**

They should be:
- ✅ Locked as authoritative
- ✅ Used as implementation north star
- ✅ Enforced via code review and audit
- ✅ Never weakened to accommodate implementation shortcuts

**The implementation must be brought into alignment with these principles, not vice versa.**

**The component is wrong, not the principle.**

---

**Document Status**: LOCKED
**Next Action**: Implement Phase 1 (Protect) - Wire suppression to all system-initiated scaffolds
**Success Criteria**: Zero proactive scaffolds bypass suppression checks
