# Long-Running Task System Architecture

## Overview

A system for Sakhi to autonomously execute tasks that span days, weeks, or months — like building a personal brand on Twitter, learning a new skill, or managing a home renovation project.

## Core Concepts

### Task Hierarchy

```
┌─────────────────────────────────────────────────────────────────┐
│                        MISSION                                   │
│  "Build a thought leadership brand on Twitter"                   │
│  Duration: 6 months | Goal: 10k followers                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         PHASES                                   │
│  Phase 1: Foundation (Month 1-2)                                 │
│  Phase 2: Growth (Month 3-4)                                     │
│  Phase 3: Monetization (Month 5-6)                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      WEEKLY PLANS                                │
│  Week 5 Plan:                                                    │
│  - Post 3 threads on AI ethics                                   │
│  - Engage with 20 accounts in niche                              │
│  - Analyze what's working                                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    DAILY ACTIONS                                 │
│  Monday:                                                         │
│  - 9am: Draft thread                                             │
│  - 12pm: Post thread                                             │
│  - 6pm: Respond to comments                                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   ATOMIC OPERATIONS                              │
│  "Post thread" breaks down to:                                   │
│  1. Open Twitter                                                 │
│  2. Click compose                                                │
│  3. Paste content                                                │
│  4. Click post                                                   │
│  (This is a single vision loop session)                          │
└─────────────────────────────────────────────────────────────────┘
```

## Data Model

### 1. Mission (Top-Level Goal)

```sql
CREATE TABLE long_running_missions (
    id UUID PRIMARY KEY,
    person_id UUID NOT NULL REFERENCES people(id),

    -- Mission definition
    title TEXT NOT NULL,                    -- "Build Twitter brand"
    description TEXT,                       -- Detailed goal description
    success_criteria JSONB,                 -- Measurable outcomes

    -- Timeline
    created_at TIMESTAMPTZ DEFAULT NOW(),
    target_end_date DATE,                   -- When to achieve by
    actual_end_date DATE,                   -- When actually completed

    -- Status
    status TEXT DEFAULT 'active',           -- active, paused, completed, abandoned
    health TEXT DEFAULT 'on_track',         -- on_track, at_risk, behind, ahead

    -- Learning
    strategy_notes TEXT,                    -- High-level approach
    lessons_learned JSONB,                  -- What we've learned

    -- Metrics
    progress_pct INTEGER DEFAULT 0,         -- 0-100
    metrics JSONB                           -- Domain-specific KPIs
);

-- Example:
-- {
--   "title": "Build Twitter personal brand",
--   "success_criteria": {
--     "followers": 10000,
--     "avg_engagement_rate": 0.05,
--     "monetization": "1 paid consultation"
--   },
--   "metrics": {
--     "current_followers": 847,
--     "posts_this_month": 12,
--     "avg_engagement": 0.032
--   }
-- }
```

### 2. Phase (Multi-Week Chunks)

```sql
CREATE TABLE mission_phases (
    id UUID PRIMARY KEY,
    mission_id UUID REFERENCES long_running_missions(id),

    -- Phase definition
    phase_number INTEGER NOT NULL,          -- 1, 2, 3...
    name TEXT NOT NULL,                     -- "Foundation Phase"
    objective TEXT,                         -- What this phase achieves

    -- Timeline
    start_date DATE NOT NULL,
    target_end_date DATE NOT NULL,
    actual_end_date DATE,

    -- Status
    status TEXT DEFAULT 'pending',          -- pending, active, completed, skipped

    -- Deliverables
    expected_outcomes JSONB,                -- What success looks like
    actual_outcomes JSONB,                  -- What actually happened

    -- Adaptation
    adjustments_made TEXT[]                 -- Changes from original plan
);
```

### 3. Weekly Plan

```sql
CREATE TABLE weekly_plans (
    id UUID PRIMARY KEY,
    phase_id UUID REFERENCES mission_phases(id),
    mission_id UUID REFERENCES long_running_missions(id),

    -- Week identification
    week_number INTEGER NOT NULL,           -- Week 1, 2, 3...
    week_start DATE NOT NULL,
    week_end DATE NOT NULL,

    -- Planning
    objectives TEXT[],                      -- This week's goals
    tasks JSONB,                            -- Structured task list

    -- Status
    status TEXT DEFAULT 'planned',          -- planned, active, completed, adjusted

    -- Review
    review_completed BOOLEAN DEFAULT FALSE,
    review_notes TEXT,                      -- End-of-week reflection
    what_worked TEXT[],
    what_didnt TEXT[],
    adjustments_for_next TEXT[]
);

-- Example tasks JSONB:
-- [
--   {
--     "id": "thread_1",
--     "type": "content_creation",
--     "description": "Write thread on AI ethics",
--     "scheduled_day": "monday",
--     "scheduled_time": "09:00",
--     "status": "completed",
--     "result": {"likes": 45, "retweets": 12}
--   }
-- ]
```

### 4. Scheduled Action (Individual Task)

```sql
CREATE TABLE scheduled_actions (
    id UUID PRIMARY KEY,
    weekly_plan_id UUID REFERENCES weekly_plans(id),
    mission_id UUID REFERENCES long_running_missions(id),
    person_id UUID NOT NULL,

    -- Action definition
    action_type TEXT NOT NULL,              -- post, engage, analyze, research
    description TEXT NOT NULL,
    instructions JSONB,                     -- Detailed execution steps

    -- Scheduling
    scheduled_date DATE NOT NULL,
    scheduled_time TIME,                    -- NULL = anytime that day
    deadline TIMESTAMPTZ,                   -- Must complete by

    -- Execution
    status TEXT DEFAULT 'scheduled',        -- scheduled, triggered, running, completed, failed, skipped
    agent_session_id UUID,                  -- Links to vision loop session
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,

    -- Results
    outcome JSONB,                          -- What happened
    success BOOLEAN,
    error_message TEXT,

    -- Learning
    effectiveness_score DECIMAL(3,2),       -- 0-1, did this help the mission?
    notes TEXT
);
```

### 5. Progress Checkpoint

```sql
CREATE TABLE mission_checkpoints (
    id UUID PRIMARY KEY,
    mission_id UUID REFERENCES long_running_missions(id),

    -- Timing
    checkpoint_date DATE NOT NULL,
    checkpoint_type TEXT NOT NULL,          -- daily, weekly, monthly, milestone

    -- State snapshot
    metrics_snapshot JSONB,                 -- All metrics at this point
    progress_pct INTEGER,
    health TEXT,

    -- Analysis
    analysis TEXT,                          -- AI-generated analysis
    recommendations TEXT[],                 -- Suggested adjustments
    risks TEXT[],                           -- Identified risks

    -- Decisions
    adjustments_approved JSONB,             -- User-approved changes
    user_feedback TEXT
);
```

## Scheduling System

### Trigger Types

```python
class TriggerType(Enum):
    SCHEDULED = "scheduled"         # Specific date/time
    RECURRING = "recurring"         # Daily at 9am, Weekly on Monday
    CONDITION = "condition"         # When followers hit 1000
    EVENT = "event"                 # When user posts manually
    MANUAL = "manual"               # User triggers explicitly

class ScheduledTrigger:
    trigger_type: TriggerType
    cron_expression: str            # "0 9 * * MON" = Monday 9am
    condition_check: Optional[str]  # SQL or Python expression
    event_type: Optional[str]       # "manual_post", "follower_milestone"
```

### Scheduler Bridge

```python
# In sakhi/apps/worker/long_task_scheduler.py

class LongTaskScheduler:
    """
    Bridges between mission plans and RQ job queue.
    Runs every hour to check what needs to be triggered.
    """

    def check_scheduled_actions(self):
        """Find actions due in the next hour and enqueue them."""

        due_actions = db.query("""
            SELECT * FROM scheduled_actions
            WHERE status = 'scheduled'
            AND scheduled_date = CURRENT_DATE
            AND (scheduled_time IS NULL OR scheduled_time <= NOW() + INTERVAL '1 hour')
            AND scheduled_time >= NOW()
        """)

        for action in due_actions:
            self.enqueue_action(action)

    def enqueue_action(self, action):
        """Create a vision loop session for this action."""

        # Create agent session
        session = AgentSession.create(
            person_id=action.person_id,
            task_type="long_running_action",
            task_context={
                "mission_id": action.mission_id,
                "action_id": action.id,
                "instructions": action.instructions,
                "success_criteria": action.instructions.get("success_criteria")
            }
        )

        # Update action status
        action.status = "triggered"
        action.agent_session_id = session.id

        # Queue the vision loop
        rq.enqueue(
            "execute_scheduled_action",
            session_id=session.id,
            queue="agent"
        )

    def check_weekly_reviews(self):
        """Trigger end-of-week reviews on Sunday evenings."""

        if today.weekday() == 6:  # Sunday
            active_plans = db.query("""
                SELECT * FROM weekly_plans
                WHERE status = 'active'
                AND review_completed = FALSE
            """)

            for plan in active_plans:
                self.trigger_weekly_review(plan)

    def check_conditions(self):
        """Check condition-based triggers."""

        # Example: "When followers > 1000, start Phase 2"
        condition_triggers = db.query("""
            SELECT * FROM mission_phases
            WHERE status = 'pending'
            AND start_condition IS NOT NULL
        """)

        for phase in condition_triggers:
            if self.evaluate_condition(phase.start_condition):
                self.activate_phase(phase)
```

## Execution Flow

### 1. Mission Creation

```python
async def create_mission(person_id: str, request: MissionRequest) -> Mission:
    """
    User says: "Help me build a Twitter brand"
    Sakhi creates a multi-month mission with phases.
    """

    # 1. Understand the goal through conversation
    goal_analysis = await sakhi.analyze_goal(request.description)

    # 2. Create mission
    mission = Mission.create(
        person_id=person_id,
        title=goal_analysis.title,
        description=goal_analysis.description,
        success_criteria=goal_analysis.success_criteria,
        target_end_date=goal_analysis.recommended_timeline
    )

    # 3. Generate phases
    phases = await sakhi.generate_phases(mission, goal_analysis)
    for phase in phases:
        MissionPhase.create(mission_id=mission.id, **phase)

    # 4. Generate first week's plan
    first_week = await sakhi.generate_weekly_plan(
        mission=mission,
        phase=phases[0],
        week_number=1
    )
    WeeklyPlan.create(mission_id=mission.id, **first_week)

    # 5. Schedule first week's actions
    for action in first_week.tasks:
        ScheduledAction.create(
            mission_id=mission.id,
            weekly_plan_id=first_week.id,
            **action
        )

    return mission
```

### 2. Daily Execution

```python
async def execute_scheduled_action(session_id: str):
    """
    Vision loop executes a single scheduled action.
    """

    session = AgentSession.get(session_id)
    action = ScheduledAction.get(session.task_context["action_id"])

    try:
        # Run the vision loop for this specific action
        result = await vision_loop.execute(
            session=session,
            instructions=action.instructions,
            max_steps=50
        )

        # Record outcome
        action.status = "completed"
        action.outcome = result.outcome
        action.success = result.success
        action.completed_at = datetime.now()
        action.save()

        # Update mission metrics if applicable
        await update_mission_metrics(action.mission_id, result)

    except Exception as e:
        action.status = "failed"
        action.error_message = str(e)
        action.save()

        # Notify user of failure
        await notify_user(action.person_id, f"Action failed: {action.description}")
```

### 3. Weekly Review & Adaptation

```python
async def weekly_review(plan: WeeklyPlan):
    """
    End of week: analyze what worked, adjust next week.
    """

    mission = Mission.get(plan.mission_id)

    # 1. Gather this week's data
    actions = ScheduledAction.get_by_plan(plan.id)
    outcomes = [a.outcome for a in actions if a.outcome]

    # 2. Analyze performance
    analysis = await sakhi.analyze_week(
        mission=mission,
        planned=plan.tasks,
        actual_outcomes=outcomes,
        current_metrics=mission.metrics
    )

    # 3. Update plan with review
    plan.review_completed = True
    plan.review_notes = analysis.summary
    plan.what_worked = analysis.what_worked
    plan.what_didnt = analysis.what_didnt
    plan.adjustments_for_next = analysis.recommendations
    plan.save()

    # 4. Generate next week's plan (incorporating learnings)
    next_week = await sakhi.generate_weekly_plan(
        mission=mission,
        phase=mission.current_phase,
        week_number=plan.week_number + 1,
        learnings=analysis
    )

    # 5. Notify user for approval (if significant changes)
    if analysis.requires_user_approval:
        await notify_user(
            mission.person_id,
            f"Week {plan.week_number} review ready. New plan needs approval.",
            action_url=f"/missions/{mission.id}/weekly/{next_week.id}"
        )
    else:
        # Auto-approve minor adjustments
        await schedule_weekly_actions(next_week)
```

### 4. Mission Health Monitoring

```python
async def daily_health_check():
    """
    Run daily to assess all active missions.
    """

    active_missions = Mission.get_active()

    for mission in active_missions:
        # Calculate health based on:
        # - Progress vs timeline
        # - Recent action success rate
        # - Metric trends

        health = await assess_mission_health(mission)

        if health.status == "at_risk":
            # Alert user
            await notify_user(
                mission.person_id,
                f"Mission '{mission.title}' needs attention: {health.reason}",
                urgency="medium"
            )

        # Create checkpoint
        MissionCheckpoint.create(
            mission_id=mission.id,
            checkpoint_type="daily",
            metrics_snapshot=mission.metrics,
            progress_pct=mission.progress_pct,
            health=health.status,
            analysis=health.analysis,
            recommendations=health.recommendations
        )
```

## Example: Twitter Personal Brand Mission

### Initial Setup

```
User: "I want to build a personal brand on Twitter focused on AI"

Sakhi: "I'd love to help you build your Twitter presence. Let me understand your goals:

1. What's your target audience? (developers, executives, general public)
2. What's your timeline? (3 months, 6 months, 1 year)
3. Any specific goals? (followers, consulting leads, speaking invites)
4. How much time can you dedicate daily? (15 min, 30 min, 1 hour)"

User: "Developers and tech leads. 6 months. Goal is 10k followers and 1 paid consultation. I can do 30 min/day."

Sakhi: "Great! Here's my proposed plan:

**Mission: AI Thought Leader on Twitter**
Duration: 6 months
Goal: 10k followers + 1 paid consultation

**Phase 1: Foundation (Weeks 1-8)**
- Define your unique angle
- Create consistent posting rhythm
- Build initial content library
- Target: 1,000 followers

**Phase 2: Growth (Weeks 9-16)**
- Increase posting frequency
- Engage with larger accounts
- Start threads on trending topics
- Target: 5,000 followers

**Phase 3: Authority (Weeks 17-24)**
- Guest posts and collaborations
- Launch newsletter or offer
- Convert followers to leads
- Target: 10,000 followers + 1 consultation

**Weekly Commitment:**
- 3 posts (1 thread, 2 single tweets)
- 20 min engagement daily
- 1 weekly review with me

Should I create this mission?"

User: "Yes, let's do it"

Sakhi: "Mission created! Here's your Week 1 plan:

**Week 1: Finding Your Voice**

Monday:
- 9am: Draft your intro thread (who you are, what you'll share)
- I'll post it at 12pm (optimal engagement time)

Wednesday:
- Research 10 accounts in your niche
- Draft 2 single tweets on current AI news

Friday:
- Post the 2 tweets
- Spend 20 min engaging with responses

Sunday:
- We'll review what worked and plan Week 2

I've scheduled these actions. You'll get notifications when it's time. Want me to draft your intro thread now?"
```

### Week 1 Execution

```
MONDAY 9:00 AM - Notification:

"Time to draft your intro thread!

Here's a template based on successful AI Twitter accounts:

Thread idea: 'Why I'm betting my career on AI'
1. Your background (brief)
2. The moment AI clicked for you
3. What you're building/learning
4. What you'll share here
5. Call to action

Want me to help you draft this?"

---

MONDAY 12:00 PM - Auto-execution:

Sakhi opens Twitter, posts the thread you approved.
Logs: "Thread posted. Initial impressions: 45"

---

MONDAY 6:00 PM - Notification:

"Your thread is getting traction!
- 127 impressions
- 8 likes
- 2 replies

I've drafted responses to the replies. Want to review them?"

---

FRIDAY 5:00 PM - Notification:

"Week 1 posts are done!

Results:
- Intro thread: 340 impressions, 23 likes, 5 new followers
- Tweet 1: 89 impressions, 4 likes
- Tweet 2: 112 impressions, 6 likes

Best performer: Your intro thread (personal stories resonate)

Ready for your 20-min engagement session? I found 5 posts to engage with."

---

SUNDAY 7:00 PM - Weekly Review:

"Week 1 Review:

**What Worked:**
- Personal story thread (3x better than news commentary)
- Posting at 12pm (highest impressions)
- Replying within 1 hour (50% more engagement)

**Adjustments for Week 2:**
- Focus on personal experience threads
- Add 1 more post (you have capacity)
- Start engaging before posting (warm up the algorithm)

**Week 2 Plan:**
- Monday: Thread on 'My biggest AI mistake'
- Wednesday: 2 tweets + 30 min pre-engagement
- Friday: Thread on 'Tools I use daily'

Approve Week 2 plan?"
```

### Month 2 Checkpoint

```
MONTH 2 REVIEW:

"Mission Health: ON TRACK

**Progress:**
- Followers: 847 (target: 1,000 by Week 8) ✓
- Engagement rate: 3.2% (industry avg: 1.5%) ✓
- Consistency: 100% of planned posts ✓

**Key Learnings:**
1. Threads outperform single tweets 4:1
2. Tuesday 11am is your best time (not Monday 12pm)
3. Hot takes get shares, tutorials get saves
4. Engaging before posting boosts reach 2x

**Recommendation:**
You're ahead of schedule. Options:
A) Stay the course (safe)
B) Accelerate to Phase 2 early (more effort, faster growth)
C) Maintain pace but add newsletter (diversify)

Which approach?"
```

## Integration Points

### Existing Systems Used

| System | How It's Used |
|--------|---------------|
| `AgentSession` | Each scheduled action runs as a vision loop session |
| `InterventionPlan` | Weekly plans use same tracking pattern |
| `PreferenceEngine` | Learn content preferences (what topics get engagement) |
| `PatternLearning` | Identify what works (time of day, content type) |
| `RQ Queues` | Schedule daily/weekly jobs |
| `Nudges` | Remind user of upcoming actions, celebrate wins |

### New Components Needed

1. **MissionOrchestrator** - Manages mission lifecycle
2. **WeeklyPlanner** - Generates weekly plans from mission strategy
3. **HealthMonitor** - Assesses mission progress daily
4. **AdaptationEngine** - Adjusts plans based on outcomes
5. **MetricsCollector** - Gathers domain-specific KPIs (Twitter API, etc.)

## Privacy & Control

### User Control Points

- **Approve/reject** weekly plans
- **Pause** mission at any time
- **Adjust** timeline or goals mid-flight
- **Review** all scheduled actions before execution
- **Override** any AI decision

### What Sakhi Can Do Autonomously

- Draft content (user approves before posting)
- Suggest engagement targets
- Analyze performance data
- Adjust posting times based on data
- Generate weekly review summaries

### What Requires User Approval

- Posting any content
- Changing mission goals
- Skipping scheduled phases
- Engaging with specific accounts (optional setting)
- Any financial transactions

## Storage Architecture

### Decision: Database-First with Plan Document

All mission data lives in **PostgreSQL (Supabase)**, including the full plan document as a TEXT column:

```sql
-- Add to long_running_missions table
ALTER TABLE long_running_missions ADD COLUMN plan_document TEXT;
```

### Why Database Storage?

| Factor | Database (chosen) | File Storage |
|--------|-------------------|--------------|
| Plan size | ~2-10 KB markdown | Same |
| Querying | Easy ("find missions with 'Twitter'") | Requires file read |
| Transactions | Atomic (update plan + status together) | Two systems to sync |
| Backup | Already in DB backup | Separate system |
| Infrastructure | No extra setup | Need Supabase Storage |

### Data Model

```
long_running_missions
├── id, person_id, title, status, progress    ← Structured (fast queries)
├── plan_document TEXT                         ← Full markdown plan
├── success_criteria JSONB                     ← Structured goals
└── metrics JSONB                              ← Tracked KPIs
```

### Plan Document Format (Markdown)

```markdown
# Mission: Build Personal Brand on Twitter

## Goal
Reach 1,000 engaged followers in 12 weeks

## Success Criteria
- 1,000 followers
- 5% engagement rate
- 3 viral threads (100+ likes)

## Current Status
- Phase: 2 of 4 (Content Engine)
- Progress: 35%
- Health: On Track ✅

## Phase 1: Foundation (Weeks 1-2) ✅ COMPLETE
- [x] Optimize bio
- [x] Pin best thread
- [x] Consistent posting time: 9am

## Phase 2: Content Engine (Weeks 3-6) ← CURRENT
- [ ] Post daily thread (M-F)
- [ ] Engage 30 min/day
- [ ] Track what resonates

### This Week's Actions
- Mon: Thread on coding productivity
- Tue: Engage with 10 accounts
- Wed: Thread on remote work
...

## Learnings
- Threads > single tweets (3x engagement)
- Morning posts perform better
- Polls don't work for my audience
```

### Mission Recognition

When user says "update my Insta campaign":

```python
async def find_mission_by_reference(person_id: str, reference: str) -> Mission:
    """
    Fuzzy match user's reference to existing missions.
    """

    # 1. Try exact title match
    mission = db.query("""
        SELECT * FROM long_running_missions
        WHERE person_id = :person_id
        AND LOWER(title) = LOWER(:reference)
        AND status = 'active'
    """, person_id=person_id, reference=reference)

    if mission:
        return mission

    # 2. Try fuzzy match on title and description
    missions = db.query("""
        SELECT *,
               similarity(LOWER(title), LOWER(:reference)) as title_sim,
               similarity(LOWER(description), LOWER(:reference)) as desc_sim
        FROM long_running_missions
        WHERE person_id = :person_id
        AND status = 'active'
        AND (
            LOWER(title) ILIKE '%' || LOWER(:reference) || '%'
            OR LOWER(description) ILIKE '%' || LOWER(:reference) || '%'
        )
        ORDER BY title_sim DESC, desc_sim DESC
        LIMIT 1
    """, person_id=person_id, reference=reference)

    if missions:
        return missions[0]

    # 3. Ask for clarification
    return None

async def update_mission_plan(mission_id: str, user_request: str) -> Mission:
    """
    User says: "add posting reels to my Insta campaign"
    """

    # 1. Load current plan
    mission = Mission.get(mission_id)
    current_plan = mission.plan_document

    # 2. LLM updates the plan
    updated_plan = await llm.update_plan(
        current_plan=current_plan,
        user_request=user_request,
        mission_context={
            "title": mission.title,
            "phase": mission.current_phase,
            "metrics": mission.metrics
        }
    )

    # 3. Save atomically
    mission.plan_document = updated_plan
    mission.updated_at = datetime.now()
    mission.save()

    # 4. Parse new actions from plan and schedule them
    new_actions = parse_actions_from_plan(updated_plan)
    for action in new_actions:
        if not action_already_scheduled(action):
            ScheduledAction.create(**action)

    return mission
```

### Future: Version History (Optional)

If we need plan versioning later, add a simple history table:

```sql
CREATE TABLE mission_plan_history (
    id UUID PRIMARY KEY,
    mission_id UUID REFERENCES long_running_missions(id),
    plan_document TEXT,
    changed_at TIMESTAMPTZ DEFAULT NOW(),
    change_summary TEXT,
    changed_by TEXT  -- 'user' or 'sakhi'
);
```

This keeps the main table simple while allowing full history when needed

## Generic Mission Data

### Design Philosophy: One Table for Everything

Instead of creating domain-specific tables (`expenses`, `tweets`, `workouts`), we use a single generic table with JSONB for flexibility:

```sql
CREATE TABLE mission_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mission_id UUID REFERENCES long_running_missions(id),
    person_id UUID NOT NULL REFERENCES people(id),

    -- Flexible typing
    record_type TEXT NOT NULL,      -- 'expense', 'tweet', 'workout', 'lesson', anything

    -- The actual data (schema-free)
    data JSONB NOT NULL,            -- {vendor: "Vercel", amount: 49.99, category: "Cloud"}

    -- Common fields
    record_date DATE,               -- When this record is for (not created_at)
    source TEXT,                    -- 'email', 'manual', 'api', 'vision_loop'

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for fast queries
CREATE INDEX idx_mission_data_lookup ON mission_data(mission_id, record_type);
CREATE INDEX idx_mission_data_person ON mission_data(person_id, record_type);
CREATE INDEX idx_mission_data_date ON mission_data(record_date);
```

### Why Generic?

| Approach | Pros | Cons |
|----------|------|------|
| **Specific tables** (`expenses`, `tweets`) | Type safety, clear schema | New table per domain, migration overhead |
| **Generic JSONB** (chosen) | One table handles everything, future-proof | Less type safety, need validation |

The generic approach wins because:
1. Missions can generate **any type of data** - expenses today, workout logs tomorrow
2. JSONB is **queryable** in PostgreSQL (can still filter, aggregate, index)
3. **No migrations** when adding new data types
4. Schema validation moves to application layer (where it belongs)

### Example Data Shapes

```python
# Expense from email invoice
{
    "record_type": "expense",
    "data": {
        "vendor": "Vercel",
        "amount": 49.99,
        "currency": "USD",
        "category": "Cloud Infrastructure",
        "invoice_date": "2024-01-15",
        "description": "Pro plan - January 2024"
    },
    "source": "email"
}

# Tweet performance
{
    "record_type": "tweet",
    "data": {
        "tweet_id": "1234567890",
        "content": "Thread on AI ethics...",
        "impressions": 12450,
        "likes": 234,
        "retweets": 45,
        "replies": 23
    },
    "source": "api"
}

# Workout log
{
    "record_type": "workout",
    "data": {
        "type": "strength",
        "exercises": [
            {"name": "Squat", "sets": 3, "reps": 8, "weight": 185},
            {"name": "Bench", "sets": 3, "reps": 8, "weight": 135}
        ],
        "duration_minutes": 45,
        "notes": "Felt strong today"
    },
    "source": "manual"
}

# Learning progress
{
    "record_type": "lesson",
    "data": {
        "course": "Rust Programming",
        "chapter": 12,
        "topic": "Ownership and Borrowing",
        "completed": true,
        "notes": "Finally clicked - ownership prevents use-after-free"
    },
    "source": "vision_loop"
}
```

### Querying Mission Data

```python
# Get all expenses for a person this month
expenses = db.query("""
    SELECT data FROM mission_data
    WHERE person_id = :person_id
    AND record_type = 'expense'
    AND record_date >= :start_date
""")

# Sum expenses by category
totals = db.query("""
    SELECT
        data->>'category' as category,
        SUM((data->>'amount')::numeric) as total
    FROM mission_data
    WHERE mission_id = :mission_id
    AND record_type = 'expense'
    GROUP BY data->>'category'
    ORDER BY total DESC
""")

# Get tweet performance trends
performance = db.query("""
    SELECT
        record_date,
        AVG((data->>'impressions')::int) as avg_impressions,
        AVG((data->>'likes')::int) as avg_likes
    FROM mission_data
    WHERE mission_id = :mission_id
    AND record_type = 'tweet'
    GROUP BY record_date
    ORDER BY record_date
""")

# Count workouts this week
workout_count = db.query("""
    SELECT COUNT(*) FROM mission_data
    WHERE person_id = :person_id
    AND record_type = 'workout'
    AND record_date >= CURRENT_DATE - INTERVAL '7 days'
""")
```

### Common Record Types

| Type | Mission Example | Data Fields |
|------|-----------------|-------------|
| `expense` | "Track monthly cloud spend" | vendor, amount, category, invoice_date |
| `tweet` | "Build Twitter brand" | tweet_id, content, impressions, likes |
| `workout` | "Get fit for summer" | type, exercises, duration, notes |
| `lesson` | "Learn Rust" | course, chapter, topic, completed |
| `habit` | "Meditate daily" | activity, duration, streak |
| `metric` | Any mission | name, value, unit, target |
| `note` | Any mission | content, tags |

### Recording Data

```python
async def record_mission_data(
    mission_id: str,
    person_id: str,
    record_type: str,
    data: dict,
    record_date: date = None,
    source: str = None
) -> MissionData:
    """
    Generic function to record any mission-related data.
    """

    return MissionData.create(
        mission_id=mission_id,
        person_id=person_id,
        record_type=record_type,
        data=data,
        record_date=record_date or date.today(),
        source=source
    )

# Usage examples:

# Vision loop scans email, finds invoice
await record_mission_data(
    mission_id=expense_mission.id,
    person_id=user.id,
    record_type="expense",
    data={
        "vendor": "AWS",
        "amount": 127.43,
        "category": "Cloud"
    },
    source="email"
)

# After posting a tweet
await record_mission_data(
    mission_id=twitter_mission.id,
    person_id=user.id,
    record_type="tweet",
    data={
        "tweet_id": result.tweet_id,
        "content": thread_content,
        "posted_at": datetime.now().isoformat()
    },
    source="vision_loop"
)

# User logs workout manually
await record_mission_data(
    mission_id=fitness_mission.id,
    person_id=user.id,
    record_type="workout",
    data=workout_form_data,
    source="manual"
)
```

## External Data Integration

Missions often need data from external sources (email invoices, social media metrics, calendar events). We support two integration patterns:

### Pattern 1: DOM Automation (Primary - Ships Now)

Use the existing vision loop + Playwright to access external services through the user's logged-in browser session.

```
┌─────────────────────────────────────────────────────────────────┐
│ User's Browser (logged into Gmail, Twitter, etc.)               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Vision Loop + Playwright                                         │
│ ─────────────────────────                                        │
│ 1. Navigate to Gmail                                             │
│ 2. Search for "invoice from:vercel"                             │
│ 3. Open each email                                               │
│ 4. Extract vendor, amount, date using vision                    │
│ 5. Record to mission_data                                       │
└─────────────────────────────────────────────────────────────────┘
```

**Advantages:**
- Uses existing infrastructure (vision loop already built)
- No API keys or OAuth setup required
- User's existing session = already authenticated
- Works with ANY service the user can access in browser
- Full visibility - user can watch Sakhi work

**Use Cases:**
| Service | Action | How |
|---------|--------|-----|
| Gmail | Scan invoices | Search → open → extract with vision |
| Twitter | Post thread | Navigate → compose → paste → post |
| Twitter | Get metrics | Open Analytics → screenshot → parse |
| LinkedIn | Check messages | Navigate → read → summarize |
| Bank | Download statement | Login → navigate → download PDF |

**Example: Monthly Invoice Scan**

```python
async def scan_email_for_invoices(mission_id: str, person_id: str):
    """
    Vision loop task: Scan Gmail for invoices and extract expenses.
    """

    # 1. Open Gmail (user's logged-in session)
    await browser.goto("https://mail.google.com")

    # 2. Search for invoices
    await browser.fill('input[name="q"]', 'invoice OR receipt from:vercel OR from:aws OR from:stripe')
    await browser.press('input[name="q"]', 'Enter')
    await wait_for_load()

    # 3. Process each email
    emails = await browser.query_selector_all('.zA')  # Email rows

    for email in emails[:20]:  # Limit to recent 20
        await email.click()
        await wait_for_load()

        # 4. Use vision to extract invoice data
        screenshot = await browser.screenshot()
        extraction = await llm.extract_invoice_data(screenshot)

        if extraction.is_invoice:
            # 5. Record to mission_data
            await record_mission_data(
                mission_id=mission_id,
                person_id=person_id,
                record_type="expense",
                data={
                    "vendor": extraction.vendor,
                    "amount": extraction.amount,
                    "currency": extraction.currency,
                    "category": extraction.category,
                    "invoice_date": extraction.date
                },
                source="email"
            )

        # Go back to search results
        await browser.go_back()

    return {"invoices_found": len(expenses), "total": sum(e.amount for e in expenses)}
```

### Pattern 2: Email Forwarding (Future - One Interface Vision)

Users forward content TO Sakhi, inverting the integration model. Sakhi becomes the destination rather than reaching into services.

```
┌─────────────────────────────────────────────────────────────────┐
│ User forwards email to: invoices@sakhi.yourserver.com           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Email Receiver (Postfix/Mailgun webhook)                         │
│ ─────────────────────────                                        │
│ 1. Receive forwarded email                                       │
│ 2. Parse content + attachments                                   │
│ 3. LLM extracts structured data                                  │
│ 4. Match to relevant mission                                     │
│ 5. Record to mission_data                                       │
└─────────────────────────────────────────────────────────────────┘
```

**Advantages:**
- User explicitly controls what flows in
- Works with ANY email provider (Gmail, Outlook, ProtonMail)
- No browser automation needed
- Scales to "forward newsletters for summarization"
- Evolves toward single-interface vision

**Future Use Cases:**
- `invoices@sakhi.me` - Forward receipts for expense tracking
- `read@sakhi.me` - Forward newsletters for summarization
- `remember@sakhi.me` - Forward anything to add to memory
- CC Sakhi on emails to add to relevant missions

### Integration Decision Matrix

| Use Case | Pattern | Why |
|----------|---------|-----|
| Scan Gmail for invoices | DOM | Need to search, user already logged in |
| Post to Twitter | DOM | Need active browser interaction |
| Process forwarded invoice | Email (future) | User explicitly shares |
| Get Twitter analytics | DOM | Scrape from analytics page |
| Summarize newsletter | Email (future) | User forwards what they want |
| Download bank statement | DOM | Need browser for auth |

### Current Implementation (Demo)

For the initial demo, we use **DOM automation only**:

1. **Gmail invoice scanning** - Vision loop navigates Gmail, extracts invoice data
2. **Twitter posting** - Vision loop composes and posts threads
3. **Twitter metrics** - Vision loop captures analytics screenshots

Email forwarding is a future enhancement that aligns with the "one interface" vision but requires additional infrastructure (email receiver, webhook processing).

## Next Steps

1. **Create database migrations** for new tables
2. **Build MissionOrchestrator** service
3. **Extend scheduler** with condition-based triggers
4. **Create weekly planning prompts** for Claude
5. **Build mission dashboard** in web app
6. **Add Twitter API integration** for metrics
7. **Create demo** showing 6-month mission compressed into 2-minute demo
