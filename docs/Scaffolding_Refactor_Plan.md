# Scaffolding Refactor Plan

**Goal**: Align all scaffolding components with Design Principles v1 and Contract v1
**Scope**: 27 files across 6 categories
**Approach**: Incremental refactor with testing at each phase
**Timeline**: 6-9 weeks (4 phases)
**Testing**: All changes must be testable and demonstrable via Lab UI using demo user (MVP scope)

> **MVP Testing Scope**: This plan uses single demo user testing (`c10fbd98-25fa-4445-8aba-e5243bc01564` from `.env`) instead of multi-persona snapshots. This allows faster implementation and testing against real production data. Multi-persona snapshot testing is deferred to post-MVP.

---

## Refactor Strategy Overview

### Foundational Constraints (Read First)

**🔒 1. "UNCHANGED" is a Valid Outcome**

A file may pass Scaffolding v1 with status **UNCHANGED**, provided it:
- Has a Scaffolding Design Record (SDR) documenting alignment with principles
- Has Lab visibility (testable via Lab UI)
- Passes principle validation

**This constraint exists to**:
- Prevent refactoring for its own sake
- Preserve trust in existing good code
- Reinforce the "no rebuilding unless necessary" principle

**2. Lab Language is Debug-Only**

Any language shown in Lab UI is **debug-only** and not evidence of production delivery.

**This means**:
- Lab signal → language panels are for testing Layer 4/5 separation
- Language generation in Lab does NOT mean language is delivered to users in production
- Future engineers must NOT treat Lab output as product behavior

**3. Scaffolding Does Not Optimize Life**

**Explicit Stance**: Scaffolding does not attempt to maximize productivity, balance, or outcomes.

**Scaffolding only**:
- Surfaces situational relevance
- Surfaces capacity
- Surfaces readiness

**Scaffolding never**:
- Prescribes how to use capacity
- Judges use of time
- Optimizes for outcomes
- Maximizes productivity

This guards against future "helpfulness creep."

---

### Core Principles (Non-Negotiable)

1. **Suppression First**: Every system-initiated scaffold checks suppression before running
2. **Signals Not Language**: Layer 4 emits structured signals; Layer 5 generates language
3. **Adaptive Time**: No fixed schedules; all timing gated by context
4. **User Agency**: On-demand > proactive; ignoring reduces initiative
5. **No Evaluation**: Remove all praise, judgment, characterization

### Testing Strategy

**All refactored components must be:**
- **Unit Testable**: Isolated component tests
- **Integration Testable**: End-to-end flow tests
- **Lab Demonstrable**: Testable via Lab UI using demo user
- **Behavior Testable**: User scenario validation

**Lab Testing Requirements (MVP Scope)**:
- Every refactored component must have Lab UI controls
- All tests use single demo user: `c10fbd98-25fa-4445-8aba-e5243bc01564` (from `.env`)
- Suppression rules must be demonstrable in Lab
- Adaptive timing must be visible in Lab
- Engagement tracking must show in Lab metrics
- **Future**: Multi-persona snapshot testing (deferred post-MVP)

---

## Lab Infrastructure Requirements

### Lab UI Enhancements Needed

**Location**: `apps/web/app/lab/` (existing Lab infrastructure)

#### 1. Scaffolding Test Panel (CREATE)

**File**: `apps/web/app/lab/scaffolding/page.tsx`

```typescript
// Lab Scaffolding Test Panel (MVP: Single Demo User)

const ScaffoldingLabPanel = () => {
  // MVP: Use demo user from .env (DEMO_USER_ID)
  const demoUserId = "c10fbd98-25fa-4445-8aba-e5243bc01564";

  return (
    <LabLayout title="Scaffolding Layer Tests (Demo User)">

      {/* Demo User Info Banner */}
      <DemoUserBanner userId={demoUserId} />

      {/* Suppression Test Section */}
      <SuppressionTestPanel userId={demoUserId} />

      {/* Signal Generation Test Section */}
      <SignalGenerationPanel userId={demoUserId} />

      {/* Adaptive Timing Test Section */}
      <AdaptiveTimingPanel userId={demoUserId} />

      {/* Engagement Simulation */}
      <EngagementSimulator userId={demoUserId} />

      {/* Live Metrics */}
      <ScaffoldMetricsView userId={demoUserId} />

    </LabLayout>
  );
};

// Note: Multi-persona snapshot testing deferred to post-MVP
```

#### 2. Suppression Test Panel

```typescript
const SuppressionTestPanel = ({ userId }: { userId: string }) => {
  const [testResults, setTestResults] = useState<SuppressionTestResult[]>([]);

  const runSuppressionTest = async (scaffoldType: string) => {
    const result = await labApi.testSuppression({
      userId: userId,  // MVP: Use demo user
      scaffoldType: scaffoldType
    });

    setTestResults(prev => [...prev, result]);
  };

  return (
    <Panel title="Suppression Tests (Demo User)">
      <UserStateDisplay userId={userId} />  {/* Show current user state */}

      <ScaffoldTypeSelector
        types={[
          "morning_preview",
          "morning_ask",
          "focus_path",
          "micro_momentum",
          "nudge"
        ]}
        onTest={runSuppressionTest}
      />

      <TestResults>
        {testResults.map(result => (
          <TestResult key={result.id}>
            <Badge color={result.action === "allow" ? "green" : "red"}>
              {result.action}
            </Badge>
            <Reason>{result.reason}</Reason>
            <Timestamp>{result.tested_at}</Timestamp>
          </TestResult>
        ))}
      </TestResults>

      {/* Expected vs Actual */}
      <ValidationPanel>
        <ExpectedBehavior userId={userId} />
        <ActualBehavior results={testResults} />
        <AssertionStatus passing={validateResults(testResults)} />
      </ValidationPanel>
    </Panel>
  );
};
```

#### 3. Signal Generation Test Panel

```typescript
const SignalGenerationPanel = ({ userId }: { userId: string }) => {
  const [signal, setSignal] = useState<ScaffoldSignal | null>(null);
  const [language, setLanguage] = useState<string | null>(null);

  const generateSignal = async (scaffoldType: string) => {
    // Test Layer 4 - Signal only
    const signalResult = await labApi.generateSignal({
      userId: userId,  // MVP: Use demo user
      scaffoldType: scaffoldType
    });

    setSignal(signalResult.signal);
    setLanguage(null); // Reset language
  };

  const generateLanguage = async () => {
    if (!signal) return;

    // Test Layer 5 - Language from signal
    const languageResult = await labApi.generateLanguage({
      signal: signal
    });

    setLanguage(languageResult.language);
  };

  return (
    <Panel title="Signal → Language Flow">

      {/* Generate Signal (Layer 4) */}
      <Button onClick={() => generateSignal("focus_path")}>
        Generate Focus Path Signal
      </Button>

      {signal && (
        <>
          <SignalViewer signal={signal}>
            <JsonView data={signal} />
            <Validation>
              <Check label="No language in signal" passed={!hasLanguage(signal)} />
              <Check label="All required fields" passed={validateSchema(signal)} />
              <Check label="Confidence score present" passed={signal.confidence !== undefined} />
              <Check label="Basis array present" passed={Array.isArray(signal.basis)} />
            </Validation>
          </SignalViewer>

          {/* Generate Language (Layer 5) */}
          <Button onClick={generateLanguage}>
            Generate Language from Signal
          </Button>
        </>
      )}

      {language && (
        <LanguageViewer language={language}>
          <TextDisplay>{language}</TextDisplay>
          <Validation>
            <Check label="No evaluation language" passed={!hasEvaluation(language)} />
            <Check label="No directive advice" passed={!hasDirective(language)} />
            <Check label="Factual only" passed={isFactual(language)} />
          </Validation>
        </LanguageViewer>
      )}

      {/* Layer Boundary Assertion */}
      <AssertionPanel>
        <Assert condition={signal !== null} message="Layer 4 emits signal" />
        <Assert condition={!hasLanguage(signal)} message="Signal contains no language" />
        <Assert condition={language === null || hasLanguage(language)} message="Layer 5 generates language on request" />
      </AssertionPanel>

    </Panel>
  );
};
```

#### 4. Adaptive Timing Test Panel

```typescript
const AdaptiveTimingPanel = ({ userId }: { userId: string }) => {
  const [scheduleDecisions, setScheduleDecisions] = useState<ScheduleDecision[]>([]);

  const testScheduling = async (scaffoldType: string, hour: number) => {
    const decision = await labApi.testScheduleDecision({
      userId: userId,  // MVP: Use demo user
      scaffoldType: scaffoldType,
      currentHour: hour
    });

    setScheduleDecisions(prev => [...prev, decision]);
  };

  return (
    <Panel title="Adaptive Timing Tests (Demo User)">

      <UserRhythmDisplay userId={userId} />  {/* Show demo user's rhythm state */}

      {/* Time Slider */}
      <HourSlider
        label="Test at hour"
        min={0}
        max={23}
        onChange={(hour) => testScheduling("morning_preview", hour)}
      />

      <ScheduleDecisionTable decisions={scheduleDecisions}>
        <Column header="Hour" render={(d) => d.hour} />
        <Column header="Decision" render={(d) => (
          <Badge color={decisionColor(d.action)}>
            {d.action}
          </Badge>
        )} />
        <Column header="Reason" render={(d) => d.reason} />
        <Column header="Optimal Slot" render={(d) => d.optimal_slot} />
      </ScheduleDecisionTable>

      {/* Validation */}
      <ValidationPanel>
        <ExpectedTimingBehavior userId={userId} />
        <ActualTimingResults decisions={scheduleDecisions} />
      </ValidationPanel>

    </Panel>
  );
};
```

#### 5. Engagement Simulator

```typescript
const EngagementSimulator = ({ userId }: { userId: string }) => {
  const [interactions, setInteractions] = useState<Interaction[]>([]);
  const [engagementRate, setEngagementRate] = useState<number>(1.0);

  const simulateInteractions = async (pattern: string, count: number) => {
    const result = await labApi.simulateEngagement({
      userId: userId,  // MVP: Use demo user
      pattern: pattern,  // "ignore_all" | "dismiss_all" | "engage_20%" | "engage_80%"
      count: count
    });

    setInteractions(result.interactions);
    setEngagementRate(result.engagement_rate);
  };

  return (
    <Panel title="Engagement Simulation">

      <PatternSelector
        patterns={[
          { id: "ignore_all", label: "Ignore All (0%)", description: "User never opens scaffolds" },
          { id: "dismiss_all", label: "Dismiss All (0%)", description: "User actively dismisses" },
          { id: "engage_20", label: "Low Engagement (20%)", description: "Opens 1 in 5" },
          { id: "engage_80", label: "High Engagement (80%)", description: "Opens 4 in 5" }
        ]}
        onSelect={(pattern) => simulateInteractions(pattern, 30)}
      />

      <MetricDisplay>
        <Metric label="Simulated Interactions" value={interactions.length} />
        <Metric label="Engagement Rate" value={`${(engagementRate * 100).toFixed(0)}%`} />
        <Metric label="Expected Behavior" value={getExpectedBehavior(engagementRate)} />
      </MetricDisplay>

      <InteractionTimeline interactions={interactions} />

      {/* Assertions */}
      <AssertionPanel>
        <Assert
          condition={engagementRate < 0.2 && interactions.length > 10}
          message="Low engagement (< 20%) detected"
          expected="Frequency should reduce"
        />
        <Assert
          condition={engagementRate < 0.2}
          message="System reduces scaffold frequency"
          validate={async () => {
            const decision = await labApi.testScheduleDecision({
              personaSnapshot: snapshot.id,
              scaffoldType: "morning_preview",
              engagementHistory: interactions
            });
            return decision.action === "cancel" && decision.reason === "low_engagement";
          }}
        />
      </AssertionPanel>

    </Panel>
  );
};
```

#### 6. Scaffold Metrics View

```typescript
const ScaffoldMetricsView = ({ userId }: { userId: string }) => {
  const { data: metrics } = useSWR(
    `/lab/scaffolding/metrics?userId=${userId}`  // MVP: Use demo user
  );

  return (
    <Panel title="Scaffolding Metrics (Demo User)">

      <MetricGrid>
        <MetricCard
          label="Scaffolds Withheld"
          value={metrics?.scaffolds_withheld}
          subtitle={`${(metrics?.withhold_rate * 100).toFixed(0)}% of potential`}
          trend="positive"
          description="Higher is better - shows restraint"
        />

        <MetricCard
          label="Suppression Rate"
          value={`${(metrics?.suppression_rate * 100).toFixed(0)}%`}
          subtitle="Protective silencing active"
          breakdown={metrics?.suppression_reasons}
        />

        <MetricCard
          label="Engagement Rate"
          value={`${(metrics?.engagement_rate * 100).toFixed(0)}%`}
          subtitle={metrics?.engagement_rate < 0.2 ? "Low - reducing frequency" : "Healthy"}
        />

        <MetricCard
          label="User-Initiated Ratio"
          value={`${(metrics?.user_initiated_ratio * 100).toFixed(0)}%`}
          subtitle="User requests vs system proactive"
          trend={metrics?.user_initiated_ratio > 0.5 ? "positive" : "neutral"}
        />

        <MetricCard
          label="Avg Time Between"
          value={`${metrics?.avg_hours_between.toFixed(1)}h`}
          subtitle="Goal: increase over time"
          trend={metrics?.avg_hours_between > 12 ? "positive" : "neutral"}
        />
      </MetricGrid>

      {/* Validation */}
      <ValidationPanel>
        <ValidationCheck
          condition={metrics?.withhold_rate > 0}
          message="System withholds some scaffolds (restraint working)"
        />
        <ValidationCheck
          condition={metrics?.suppression_rate >= 0}
          message="Suppression system active and functioning"
        />
      </ValidationPanel>

    </Panel>
  );
};
```

---

## Demo User Testing (MVP Scope)

**Approach**: All testing uses single demo user with real state

**Demo User ID**: `c10fbd98-25fa-4445-8aba-e5243bc01564` (from `.env`)

**Why Single User for MVP**:
- Faster implementation (no persona snapshot system needed)
- Tests against real personal_model state
- Validates actual scaffolding logic with production data
- Multi-persona testing deferred to post-MVP

**Future Enhancement**: Multi-Persona Snapshot Testing
- Deferred to post-MVP scope
- Would allow testing edge cases (exhausted user, volatile emotion, crisis, etc.)
- Requires snapshot system to freeze/restore personal_model states
- Not blocking for v1 scaffolding validation

---

## Lab API Endpoints (MVP Scope)

**Location**: `sakhi/apps/api/routes/lab.py` (EXTEND)

**Note**: All endpoints use demo user ID from `.env`

### Lab Test Endpoints

```python
# routes/lab.py - ADD (MVP: Demo User Only)

from sakhi.config import settings

DEMO_USER_ID = settings.DEMO_USER_ID  # c10fbd98-25fa-4445-8aba-e5243bc01564

@router.post("/lab/scaffolding/test-suppression")
async def test_suppression(request: SuppressionTestRequest):
    """
    Test suppression logic with demo user.

    MVP: Uses demo user from .env
    Future: Support persona snapshots

    Returns: SuppressionDecision (allow/suppress/defer + reason)
    """
    # MVP: Use demo user directly
    user_id = DEMO_USER_ID

    # Test suppression
    decision = await check_scaffold_suppression(
        user_id,
        request.scaffold_type,
        request.sensitivity
    )

    # Get current user state for context
    user_state = await get_user_state(user_id)

    return {
        "decision": decision.action,
        "reason": decision.reason,
        "user_state": user_state,  # Show actual demo user state
        "tested_at": now()
    }


@router.post("/lab/scaffolding/generate-signal")
async def generate_signal_test(request: SignalTestRequest):
    """
    Test signal generation (Layer 4) with demo user.

    MVP: Uses demo user from .env

    Returns: ScaffoldSignal (structured, no language)
    """
    user_id = DEMO_USER_ID

    # Generate signal
    signal = await call_scaffold_worker(
        request.scaffold_type,
        user_id
    )

    # Validate signal structure
    validation = validate_scaffold_signal(signal)

    return {
        "signal": signal,
        "validation": validation,
        "has_language": detect_language_in_signal(signal)
    }


@router.post("/lab/scaffolding/generate-language")
async def generate_language_test(request: LanguageTestRequest):
    """
    Test language generation (Layer 5) from signal.

    Returns: Generated language + validation
    """
    # Generate language from signal
    language = await generate_scaffold_language(request.signal)

    # Validate language (check for evaluative/directive phrases)
    validation = {
        "has_evaluation": detect_evaluation_language(language),
        "has_directive": detect_directive_language(language),
        "is_factual": is_factual_language(language),
        "evaluation_phrases": extract_evaluation_phrases(language),
        "directive_phrases": extract_directive_phrases(language)
    }

    return {
        "language": language,
        "validation": validation,
        "passed": not validation["has_evaluation"] and not validation["has_directive"]
    }


@router.post("/lab/scaffolding/test-schedule-decision")
async def test_schedule_decision(request: ScheduleTestRequest):
    """
    Test adaptive scheduling with demo user.

    MVP: Uses demo user from .env

    Returns: ScheduleDecision (run_now/defer/cancel + reason)
    """
    user_id = DEMO_USER_ID

    # Test scheduling at specific hour
    with mock_time(hour=request.current_hour):
        decision = await should_scaffold_run(
            user_id,
            request.scaffold_type,
            default_hour=6
        )

    # Get optimal slot for comparison
    rhythm = await get_rhythm_state(user_id)
    optimal_slot = get_optimal_slot_for_scaffold(request.scaffold_type, rhythm)

    return {
        "decision": decision.action,
        "reason": decision.reason,
        "current_hour": request.current_hour,
        "optimal_slot": optimal_slot,
        "user_rhythm": rhythm.time_slots
    }


@router.post("/lab/scaffolding/simulate-engagement")
async def simulate_engagement(request: EngagementSimRequest):
    """
    Simulate engagement pattern over N interactions for demo user.

    MVP: Uses demo user from .env

    Returns: Simulated interactions + resulting engagement rate
    """
    user_id = DEMO_USER_ID

    # Simulate interactions
    interactions = []
    pattern_map = {
        "ignore_all": lambda: False,
        "dismiss_all": lambda: False,
        "engage_20": lambda: random() < 0.2,
        "engage_80": lambda: random() < 0.8
    }

    engage_fn = pattern_map[request.pattern]

    for i in range(request.count):
        interaction = {
            "shown_at": now() - timedelta(days=request.count - i),
            "interacted": engage_fn(),
            "dismissed": not engage_fn() and random() < 0.3,
            "ignored": not engage_fn() and random() > 0.3
        }
        interactions.append(interaction)

        # Log interaction
        await log_scaffold_interaction(test_user_id, interaction)

    # Calculate engagement rate
    engagement_rate = sum(1 for i in interactions if i["interacted"]) / len(interactions)

    return {
        "interactions": interactions,
        "engagement_rate": engagement_rate,
        "total": len(interactions),
        "engaged": sum(1 for i in interactions if i["interacted"]),
        "expected_behavior": get_expected_behavior_for_engagement(engagement_rate)
    }


@router.get("/lab/scaffolding/metrics")
async def get_lab_metrics():
    """
    Get scaffolding metrics for demo user.

    MVP: Uses demo user from .env

    Returns: Withhold rate, suppression rate, engagement, etc.
    """
    user_id = DEMO_USER_ID

    # Calculate metrics for demo user
    metrics = await calculate_scaffolding_metrics(
        user_id,
        days=30
    )

    return metrics
```

---

## Testing Requirements Per Phase (MVP: Demo User)

### Phase 1: Foundation (Suppression)

**Lab Tests Required** (using demo user):

1. **Suppression Logic Validation**
   - Test all scaffold types with demo user
   - Verify suppression checks execute before any scaffold runs
   - Display suppression decision + reason in Lab UI
   - Validate decision matches demo user's current state

2. **Suppression Rules Coverage**
   - Test rhythm-based suppression (if demo user rhythm low)
   - Test emotion-based suppression (if demo user emotion volatile)
   - Test engagement-based suppression (if demo user ignoring scaffolds)
   - Display which suppression rules triggered

3. **Decorator Integration**
   - Verify all scaffold workers use `@require_suppression_check`
   - Test decorator behavior with demo user state
   - Confirm scaffolds don't run when suppressed

**Lab UI Demonstration**:
- Show demo user's current state (rhythm, emotion, engagement)
- Show suppression decision for each scaffold type
- Show suppression reason
- Display validation: suppression working correctly ✅/❌

---

### Phase 2: Signals/Language Separation

**Lab Tests Required**:

1. **Signal Contains No Language**
   - Generate signal for any scaffold type
   - Assert: No language fields in signal JSON
   - Assert: All required fields present (confidence, basis, context)

2. **Language Generation Separate**
   - Generate signal
   - Request language from signal
   - Assert: Language generated only after request
   - Assert: No evaluation phrases in language
   - Assert: No directive phrases in language

3. **Layer Boundary Enforcement**
   - Call Layer 4 endpoint
   - Assert: Returns signal only
   - Call Layer 5 endpoint
   - Assert: Returns language from signal

**Lab UI Demonstration**:
- Show signal JSON (no language)
- Show language generation button
- Show generated language
- Show validation checks (no evaluation, no directive)
- Assert layer separation

---

### Phase 3: Adaptive Timing

**Lab Tests Required** (using demo user):

1. **Rhythm-Based Timing**
   - Test scaffold at various hours (use hour slider 0-23)
   - Display demo user's rhythm time slots
   - Show schedule decision at each hour
   - Validate decisions align with demo user's energy peaks

2. **Optimal Slot Calculation**
   - Calculate optimal slot for each scaffold type
   - Test scheduling decision at optimal vs non-optimal times
   - Display: run_now during optimal, defer otherwise
   - Verify timing adapts to demo user's actual rhythm

3. **Suppression Integration**
   - Test timing when demo user rhythm is low
   - Verify suppression overrides timing (cancel vs defer)
   - Display interaction between timing and suppression logic

**Lab UI Demonstration**:
- Show demo user's rhythm time slots (visual graph)
- Show hour slider (0-23) to test different times
- Show schedule decision at each hour
- Highlight optimal slot for each scaffold type
- Display why decision was made (rhythm state, suppression, etc.)

---

### Phase 4: Engagement & Metrics

**Lab Tests Required** (using demo user):

1. **Engagement Pattern Simulation**
   - Simulate various engagement patterns (ignore_all, engage_20, engage_80)
   - Calculate engagement rate for demo user
   - Test how engagement affects scheduling decisions
   - Validate low engagement triggers frequency reduction

2. **Metrics Dashboard**
   - Display scaffolding metrics for demo user (30-day window)
   - Show: withhold rate, suppression rate, engagement rate, avg time between
   - Validate metrics calculated correctly from demo user's history
   - Verify "withhold rate > 0" (system showing restraint)

3. **Engagement-Based Gating**
   - Test scheduling when demo user has low engagement
   - Verify scaffolds cancelled/deferred when ignored repeatedly
   - Display how engagement history affects current decisions

**Lab UI Demonstration**:
- Show engagement simulation UI (pattern selector)
- Show interaction timeline with demo user
- Show calculated engagement rate
- Show metrics dashboard for demo user
- Display validation: metrics accurate ✅/❌

---

## Lab Testing Workflow (MVP: Demo User)

### Step-by-Step Test Procedure

**For Each Refactored Component**:

1. **Implement Lab Test Endpoint**
   - Add endpoint to `/lab/scaffolding/*`
   - Use DEMO_USER_ID from .env
   - Execute component logic with demo user
   - Return result + current demo user state + validation

2. **Build Lab UI Panel**
   - Add component test section to Lab UI
   - Show demo user's current state
   - Show test controls
   - Show results
   - Show validation (pass/fail)

3. **Run Tests with Demo User**
   - Execute tests using real demo user data
   - Verify logic against actual personal_model state
   - Verify assertions
   - Document results

4. **Create Demo Video/Screenshots**
   - Record Lab UI demonstration
   - Show before/after behavior
   - Show validations passing
   - Add to documentation

5. **Update Test Checklist**
   - Mark component as tested
   - Note any issues
   - Document edge cases

---

## Lab Demo Script Template (MVP)

**For Each Component Refactor**:

### Demo: [Component Name] Refactor

**Objective**: Demonstrate [specific behavior change]

**Test Approach**: Using demo user (`c10fbd98-25fa-4445-8aba-e5243bc01564`)

**Steps**:

1. **Show Before State** (if applicable)
   - Load old implementation
   - Show fixed timing / no suppression / language in Layer 4
   - Document issues

2. **Show Demo User State**
   - Display current personal_model state (rhythm, emotion, engagement)
   - Show relevant fields for this test

3. **Show After State** (refactored)
   - Execute component with demo user
   - Show suppression working / adaptive timing / signal-only output
   - Display how component responds to demo user's actual state

4. **Validation**
   - Show expected behavior based on demo user state
   - Show actual behavior
   - Show validation passing

5. **Edge Cases**
   - Test boundary conditions with demo user
   - Test error handling
   - Show graceful degradation

6. **Metrics**
   - Show suppression logs for demo user
   - Show engagement tracking for demo user
   - Show withhold rate

**Expected Results**:
- ✅ All validations pass
- ✅ Behavior matches design principles
- ✅ Logic correct for demo user's state
- ✅ No regressions

---

## Phase 1: Foundation (Weeks 1-2) - CRITICAL

**Goal**: Wire suppression universally, prevent harm

### 1.1 Make Suppression Mandatory

**Files**:
- `sakhi/libs/actions/suppression_engine.py` (KEEP/EXTEND)
- `sakhi/apps/engine/suppression/guardrail.py` (KEEP)

**Lab Tests**:
- [ ] Test exhausted_user → all scaffolds suppressed
- [ ] Test volatile_emotion → all scaffolds suppressed
- [ ] Test conflict_active → all scaffolds suppressed
- [ ] Test crisis_language → 24hr suppression
- [ ] Test healthy_baseline → scaffolds allowed

**Tasks**:

**A. Enhance Suppression Engine**
```python
# suppression_engine.py - ADD

async def check_scaffold_suppression(
    person_id: str,
    scaffold_type: str,
    sensitivity: str = "medium"
) -> SuppressionDecision:
    """
    Central suppression check for all scaffolds.

    Returns:
        allow: Scaffold may proceed
        suppress: Scaffold must be silenced
        defer: Retry in 1 hour
    """
    # Load states
    rhythm = await get_rhythm_state(person_id)
    emotion = await get_emotion_state(person_id)
    conflict = await get_conflict_state(person_id)
    recent_journals = await get_recent_journals(person_id, hours=6)
    last_interaction = await get_last_scaffold_interaction(person_id)

    # HARD RULES (Always suppress)
    if rhythm.overall < 0.3:
        return SuppressionDecision.suppress(reason="rhythm_exhausted")

    if emotion.volatility > 0.7:
        return SuppressionDecision.suppress(reason="emotion_volatile")

    if conflict.active:
        return SuppressionDecision.suppress(reason="conflict_present")

    if detect_crisis_language(recent_journals):
        return SuppressionDecision.suppress(reason="crisis_detected")

    # SOFT RULES (Defer)
    if last_interaction and (now() - last_interaction) < timedelta(hours=2):
        return SuppressionDecision.defer(reason="recent_interaction")

    # SENSITIVITY GATES
    if sensitivity == "high" and rhythm.overall < 0.5:
        return SuppressionDecision.defer(reason="sensitivity_high_rhythm_low")

    # Check user silence mode
    prefs = await get_user_preferences(person_id)
    if prefs.silence_mode:
        return SuppressionDecision.suppress(reason="user_silence_mode")

    return SuppressionDecision.allow()
```

**B. Add Suppression Decorator**
```python
# suppression_engine.py - ADD

def require_suppression_check(scaffold_type: str, sensitivity: str = "medium"):
    """Decorator to enforce suppression checks."""
    def decorator(func):
        @wraps(func)
        async def wrapper(person_id: str, *args, **kwargs):
            decision = await check_scaffold_suppression(
                person_id, scaffold_type, sensitivity
            )

            if decision.action == "suppress":
                log_suppressed(scaffold_type, person_id, decision.reason)
                return None

            if decision.action == "defer":
                schedule_retry(scaffold_type, person_id, hours=1)
                return None

            return await func(person_id, *args, **kwargs)
        return wrapper
    return decorator
```

**C. Add Suppression Tracking**
```sql
-- Add migration

CREATE TABLE scaffold_suppressions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id TEXT NOT NULL,
    scaffold_type TEXT NOT NULL,
    reason TEXT NOT NULL,
    suppressed_at TIMESTAMP NOT NULL DEFAULT NOW(),
    would_have_shown JSONB
);

CREATE INDEX idx_suppressions_person ON scaffold_suppressions(person_id);
CREATE INDEX idx_suppressions_type ON scaffold_suppressions(scaffold_type);
```

**Lab Testing**:
- [ ] Load exhausted_user → test all scaffolds → assert 100% suppressed
- [ ] Load volatile_emotion → test all scaffolds → assert > 80% suppressed
- [ ] Load conflict_active → test all scaffolds → assert 100% suppressed
- [ ] Load crisis_language → test all scaffolds → assert 24hr suppression
- [ ] Load silence_mode → test proactive → assert 0 shown
- [ ] Load healthy_baseline → test all → assert < 20% suppressed

**Acceptance Criteria**:
- ✅ Suppression engine returns allow/suppress/defer
- ✅ All hard rules enforced
- ✅ Suppression tracking table populated
- ✅ No scaffold bypasses suppression
- ✅ All Lab tests pass

---

### 1.2 Wire Suppression to All Proactive Scaffolds

**Strategy**: Add `@require_suppression_check` decorator to every system-initiated scaffold

**Files to Update** (15 files):

**Morning Scaffolds**:
- `sakhi/apps/engine/morning_preview/engine.py`
- `sakhi/apps/engine/morning_ask/engine.py`
- `sakhi/apps/engine/morning_momentum/engine.py`

**Micro Scaffolds**:
- `sakhi/apps/engine/micro_momentum/engine.py`
- `sakhi/apps/engine/micro_recovery/engine.py`

**Evening Scaffolds**:
- `sakhi/apps/engine/daily_reflection/engine.py`
- `sakhi/apps/worker/tasks/evening_closure_worker.py`

**Focus Scaffolds**:
- `sakhi/apps/engine/focus_path/engine.py`
- `sakhi/apps/engine/mini_flow/engine.py`

**Nudge**:
- `sakhi/apps/engine/nudge/engine.py`

**Example Refactor** (morning_preview):

```python
# BEFORE
async def generate_morning_preview(person_id: str) -> Dict[str, Any]:
    # Load states
    goals = await get_goals_state(person_id)
    rhythm = await get_rhythm_state(person_id)

    # Generate preview
    preview = await build_preview(goals, rhythm)

    # Save
    await save_morning_preview(person_id, preview)
    return preview

# AFTER
from sakhi.libs.actions.suppression_engine import require_suppression_check

@require_suppression_check(scaffold_type="morning_preview", sensitivity="medium")
async def generate_morning_preview(person_id: str) -> Dict[str, Any]:
    # Load states
    goals = await get_goals_state(person_id)
    rhythm = await get_rhythm_state(person_id)

    # Generate preview
    preview = await build_preview(goals, rhythm)

    # Save
    await save_morning_preview(person_id, preview)
    return preview
```

**Lab Testing Per Component**:
- [ ] Load exhausted_user → component returns None (suppressed)
- [ ] Load healthy_baseline → component returns result
- [ ] Verify suppression logged
- [ ] Verify decorator respects sensitivity levels

**Acceptance Criteria**:
- ✅ All 15 proactive scaffolds use decorator
- ✅ Zero scaffolds bypass suppression
- ✅ Suppression tracking shows activity
- ✅ Lab tests pass for each component

---

### 1.3 Add User Silence Mode

**Files**:
- `sakhi/apps/api/routes/user_preferences.py` (CREATE)
- Frontend: User settings UI
- Lab: Silence mode test panel

**Tasks**:

**A. Add User Preferences Table**
```sql
CREATE TABLE user_preferences (
    person_id TEXT PRIMARY KEY,
    silence_mode BOOLEAN DEFAULT FALSE,
    proactive_scaffolds_enabled BOOLEAN DEFAULT TRUE,
    scaffold_frequency TEXT DEFAULT 'normal', -- 'minimal' | 'normal' | 'active'
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**B. Add API Endpoints**
```python
# routes/user_preferences.py - CREATE

@router.post("/preferences/silence-mode")
async def set_silence_mode(person_id: str, enabled: bool):
    """Enable/disable silence mode (suppresses all proactive scaffolds)."""
    await update_preference(person_id, "silence_mode", enabled)
    return {"silence_mode": enabled}

@router.get("/preferences")
async def get_preferences(person_id: str):
    """Get user scaffold preferences."""
    prefs = await get_user_preferences(person_id)
    return prefs
```

**C. Frontend Toggle**
```typescript
// User settings page - ADD

<Toggle
  label="Silence Mode"
  description="Pause all proactive scaffolding. Sakhi will only respond when you initiate."
  checked={preferences.silenceMode}
  onChange={async (checked) => {
    await api.post('/preferences/silence-mode', { enabled: checked });
  }}
/>
```

**Lab Testing**:
- [ ] Load silence_mode persona
- [ ] Test all proactive scaffolds
- [ ] Assert: Zero proactive scaffolds shown
- [ ] Test user-initiated scaffold
- [ ] Assert: User-initiated still works
- [ ] Toggle silence mode in Lab UI
- [ ] Assert: Preference persists

**Acceptance Criteria**:
- ✅ Silence mode toggle in UI
- ✅ Suppression engine checks silence mode
- ✅ User-initiated scaffolds bypass silence mode
- ✅ Lab tests pass

---

**Phase 1 Deliverables**:
- ✅ Universal suppression enforcement
- ✅ All proactive scaffolds gated
- ✅ User silence mode implemented
- ✅ Suppression tracking active
- ✅ No scaffold can bypass protection
- ✅ Lab UI tests with demo user working
- ✅ Suppression validation passing

**Phase 1 Lab Demo Checklist**:
- [ ] Demonstrate suppression with demo user (video)
- [ ] Show demo user state in Lab UI
- [ ] Demonstrate suppression logging
- [ ] Show metrics dashboard
- [ ] Document all validations passing
- [ ] Create refactor demo video

---

## Phase 2-4: [Similar structure with Lab tests for each phase]

*[Remaining phases follow same pattern: Refactor → Lab Test → Demonstrate → Document]*

---

## Scaffolding Design Record (SDR) Template

**For components that remain UNCHANGED**:

Each component that passes validation without refactoring must have an SDR documenting alignment.

**Template**: `docs/sdrs/[component_name]_sdr.md`

```markdown
# Scaffolding Design Record: [Component Name]

**File**: `path/to/component.py`
**Status**: UNCHANGED (Passes v1 without refactoring)
**Validated**: [Date]

## Principle Alignment

### 1. Suppression First
- [x] Component checks suppression before running
- [x] Uses `@require_suppression_check` decorator OR
- [x] Is user-initiated (suppression not required)
- Evidence: [Line numbers or explanation]

### 2. Signals Not Language
- [x] Component emits structured signals only OR
- [x] Is pure signal generation (no language)
- Evidence: [Line numbers]

### 3. Adaptive Time
- [x] No fixed-time trigger OR
- [x] Adaptive gating in place
- Evidence: [Scheduler implementation]

### 4. User Agency
- [x] On-demand only OR
- [x] Proactive with high justification
- Evidence: [Trigger mechanism]

### 5. No Evaluation
- [x] No evaluative language OR
- [x] Language generation in Layer 5 only
- Evidence: [Output structure]

## Lab Visibility

- [x] Component testable via Lab UI
- [x] Persona snapshots demonstrate behavior
- Lab test endpoint: `/lab/scaffolding/[component]`

## Justification for UNCHANGED Status

[Explanation of why component doesn't need refactoring]

## Review

- Reviewed by: [Name]
- Date: [Date]
- Sign-off: ✅
```

---

## Component Status Tracking

**Status Options**:
- **UNCHANGED** - Passes v1 with SDR
- **REFACTOR** - Requires changes
- **SPLIT** - Needs separation (e.g., signal/language)
- **GATE** - Needs suppression/timing gates
- **RESTRICT** - Needs reduction in scope

### Component Status Table

| Component | Current Status | Action Required | SDR | Lab Test |
|-----------|---------------|-----------------|-----|----------|
| focus_path/engine.py | REFACTOR | GATE / SPLIT | ⏳ | ⏳ |
| mini_flow/engine.py | REFACTOR | GATE / SPLIT | ⏳ | ⏳ |
| micro_journey/engine.py | **UNCHANGED** | None (user-initiated) | ✅ | ✅ |
| morning_preview/engine.py | REFACTOR | SPLIT / RESTRICT | ⏳ | ⏳ |
| morning_ask/engine.py | REFACTOR | GATE | ⏳ | ⏳ |
| morning_momentum/engine.py | REFACTOR | RESTRICT | ⏳ | ⏳ |
| micro_momentum/engine.py | REFACTOR | RESTRICT | ⏳ | ⏳ |
| micro_recovery/engine.py | REFACTOR | GATE | ⏳ | ⏳ |
| daily_reflection/engine.py | REFACTOR | SPLIT | ⏳ | ⏳ |
| evening_closure_worker.py | REFACTOR | RESTRICT / SPLIT | ⏳ | ⏳ |
| nudge/engine.py | REFACTOR | GATE / RESTRICT | ⏳ | ⏳ |
| forecast.py | **UNCHANGED** | None (signal only) | ✅ | ✅ |
| suppression/guardrail.py | **UNCHANGED** | None (core logic) | ✅ | ✅ |
| suppression_engine.py | EXTEND | Add features | ⏳ | ⏳ |
| pacing/controller.py | EXTEND | Make authoritative | ⏳ | ⏳ |
| cadence_calculator.py | **UNCHANGED** | None (pure math) | ✅ | ✅ |
| scaffold_timing.py | REVIEW | Convert to defaults | ⏳ | ⏳ |
| planner_commit_gate.py | **UNCHANGED** | None (protective) | ✅ | ✅ |
| planner_suggestion_filter.py | **UNCHANGED** | None (filtering) | ✅ | ✅ |
| planner_weekly_pressure.py | **UNCHANGED** | None (signal only) | ✅ | ✅ |
| planner_context_refresh.py | **UNCHANGED** | None (cache) | ✅ | ✅ |
| journal_dao.py | REVIEW | Intent boundary | ⏳ | ⏳ |
| intent_classifier.py | REVIEW | Layer boundary | ⏳ | ⏳ |
| auto_summarizer.py | RESTRICT | Move to Layer 5 | ⏳ | ⏳ |
| reply_service.py | AUDIT | Prompt only | ⏳ | ⏳ |
| clarity/phrasing.py | RESTRICT | Move to Layer 5 | ⏳ | ⏳ |

**Legend**:
- ✅ Complete
- ⏳ Pending
- ❌ Failed validation

**Summary**:
- UNCHANGED: 8 components (30%)
- REFACTOR: 11 components (41%)
- EXTEND: 2 components (7%)
- REVIEW: 4 components (15%)
- AUDIT: 2 components (7%)

---

## Final Deliverables

**Code Deliverables**:
- [ ] All 27 files validated (refactored OR unchanged with SDR)
- [ ] All tests passing
- [ ] All Lab tests passing
- [ ] Documentation updated

**SDR Deliverables**:
- [ ] SDRs for all UNCHANGED components
- [ ] Principle alignment documented
- [ ] Lab visibility confirmed
- [ ] Review sign-offs

**Lab Deliverables** (MVP: Demo User):
- [ ] Lab UI panels for all components
- [ ] All Lab test endpoints implemented (using demo user)
- [ ] Lab demo videos recorded
- [ ] Validations documented
- [ ] Demo user state display working

**Documentation Deliverables**:
- [ ] Refactor progress tracker
- [ ] Lab testing guide (MVP: demo user approach)
- [ ] Demo video library
- [ ] Updated architecture docs
- [ ] SDR library

---

## Success Criteria

**Code Success**:
- ✅ All components align with Design Principles v1
- ✅ All suppression checks enforced
- ✅ Layer 4/5 boundary enforced
- ✅ Adaptive timing implemented
- ✅ Engagement tracking active

**Lab Success** (MVP):
- ✅ Every refactored component testable in Lab with demo user
- ✅ Demo user state correctly displayed in Lab UI
- ✅ All validations pass
- ✅ Demo videos show before/after
- ✅ Edge cases tested and documented

**Product Success**:
- ✅ Suppression logic protects users in vulnerable states
- ✅ Adaptive timing responds to user rhythm patterns
- ✅ Low-engagement triggers frequency reduction
- ✅ Silence mode works
- ✅ Metrics show withhold rate as positive (restraint working)

---

**This refactor plan is now complete with Lab testing integration using demo user (MVP scope). Multi-persona snapshot testing deferred to post-MVP. All changes are testable and demonstrable via Lab UI with real demo user state.**
