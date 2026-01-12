# Sakhi Alpha Release Plan

**Target Date:** February 13, 2025
**Status:** Foundation Phase (Jan 6-13) → Feature Development (Jan 13 - Feb 13)
**Audience:** 10-20 alpha users (friends, early adopters, invited testers)

---

## Executive Summary

Sakhi is a personal intelligence system that shows you patterns you can't see, schedules your life around your natural rhythm, and only speaks when you're ready.

**Core Differentiators:**
1. **Contradiction Detection** - Shows when your actions don't match your intentions
2. **Intelligent Scheduling** - Suggests optimal times based on your rhythm data
3. **Context-Aware Reminders** - Only interrupts when you're in the right state
4. **Suppression First** - Respects vulnerable moments (crisis, exhaustion, conflict)

**By Feb 13, we will have:**
- ✅ Defensive foundation (memory, intelligence, suppression)
- ✅ 3 user-facing features with clear value
- ✅ Demo-able product (5-minute wow factor)
- ✅ Alpha pricing model
- ✅ 10+ alpha users providing feedback

---

## Timeline & Milestones

### Phase 1: Foundation Lock (Jan 6-13)
**Goal:** Infrastructure complete and stable

**Deliverables:**
- [x] All 11 proactive scaffold workers protected with suppression
- [x] Lab UI complete (suppression testing, reflection renderer)
- [x] Reflection renderer v1 operational
- [x] Episodic memory v2.1 stable
- [ ] End-to-end internal demo working
- [ ] Performance testing with demo user data

**Success Criteria:**
- All workers pass suppression tests
- Lab UI shows suppression decisions clearly
- Reflection renderer produces coherent output
- No critical bugs in core infrastructure

---

### Phase 2: Feature 1 - Contradictions (Jan 13-20)
**Goal:** Ship the "holy shit" moment

**What It Does:**
Shows users when their stated intentions don't match their actual behavior.

**Examples:**
```
"I need to prioritize rest"
→ Said 6 times over 4 weeks
→ Rested: 0 days
→ Worked late: 18 of 20 days
→ Contradiction detected
```

```
"This week I'll exercise"
→ Planned 6 times
→ Actually exercised: 2 times
→ Pattern: You plan Monday, skip by Wednesday
```

**Technical Approach:**

1. **Simple Pattern Matching (Week 1)**
   - Query episodic memory for intention statements ("I will", "I need to", "I should")
   - Check follow-through in subsequent 7 days
   - Flag contradictions when action doesn't happen

2. **Lab Testing (Week 1)**
   - `/lab/contradictions` endpoint
   - Test with demo user data
   - Validate accuracy (target: 70%+ true positives)

3. **User-Facing UI (Week 1)**
   - Simple card-based view
   - Show top 3-5 contradictions
   - Expandable evidence (journal excerpts)
   - No advice, just observation

**Implementation Files:**
```
sakhi/libs/intelligence/contradiction_detector.py  (new)
sakhi/apps/api/routes/lab.py                       (extend /lab/contradictions)
apps/web/app/lab/contradictions/page.tsx           (new Lab UI)
```

**Success Criteria:**
- 1 alpha user says "holy shit, this is accurate"
- Can demo in 2 minutes
- No false positives that break trust

---

### Phase 3: Feature 2 - Intelligent Scheduling (Jan 20 - Feb 3)
**Goal:** Daily utility that drives retention

**What It Does:**
Suggests optimal times for focus work, meetings, and rest based on longitudinal rhythm data.

**Examples:**
```
Morning Preview (8am):
"Your best focus window today: 9:30am - 11:30am
Based on 12 weeks of data, Tuesday mornings are your peak capacity.
Avoid scheduling meetings before noon."
```

```
Evening Summary (6pm):
"Tomorrow's rhythm forecast:
Morning: High capacity (plan deep work)
Afternoon: Meeting-friendly (2-4pm ideal)
Evening: Low energy (plan admin/rest)"
```

**Technical Approach:**

1. **Rhythm Analysis (Week 1)**
   - Use existing `rhythm_state` and `rhythm_daily_curve`
   - Calculate historical capacity patterns (day/time)
   - Identify best focus windows

2. **Scheduling Suggestions (Week 1)**
   - Morning preview (8am): Today's optimal windows
   - Evening summary (6pm): Tomorrow's forecast
   - Delivered via scaffolding layer (suppression-protected)

3. **UI Integration (Week 2)**
   - Morning dashboard view
   - Calendar integration (optional, stretch goal)
   - Weekly rhythm summary

**Implementation Files:**
```
sakhi/apps/engine/scheduling/optimizer.py          (new)
sakhi/apps/worker/tasks/morning_preview_worker.py  (extend)
apps/web/app/dashboard/rhythm-schedule/page.tsx    (new)
```

**Success Criteria:**
- 3 alpha users check it daily
- Scheduling suggestions feel accurate (subjective validation)
- Users say "this is actually useful"

---

### Phase 4: Feature 3 - Context-Aware Reminders (Feb 3-10)
**Goal:** Demonstrate suppression-first in practice

**What It Does:**
Reminds users about tasks/goals, but only when they're in the right state.

**Examples:**
```
User sets reminder: "Remind me to finish the pitch deck"
System: "I'll remind you when you have focus capacity and are not in crisis/conflict."

Tuesday 10am:
✅ User is in flow state
✅ No suppression flags
✅ Focus window active
→ Gentle reminder appears
```

```
User sets reminder: "Ask me about family time on weekends"
System: "I'll ask when rhythm is restorative and you're not depleted."

Saturday 3pm:
❌ User showing exhaustion signals
❌ Suppression: emotion volatility
→ Reminder deferred to Sunday morning
```

**Technical Approach:**

1. **Reminder Engine (Week 1)**
   - Store user-created reminders with context hints
   - Check suppression before delivery
   - Defer if user is in vulnerable state

2. **Smart Delivery Logic**
   - Use `emotion_state`, `rhythm_state`, suppression checks
   - Only deliver during "green light" windows
   - Log suppression decisions for transparency

3. **UI (Week 1)**
   - Simple reminder creation form
   - "When to remind me" context options
   - Suppression transparency ("I didn't remind you because...")

**Implementation Files:**
```
sakhi/apps/engine/reminders/smart_delivery.py      (new)
sakhi/apps/worker/tasks/reminder_worker.py          (new)
apps/web/app/reminders/page.tsx                     (new)
```

**Success Criteria:**
- Users trust the system to defer appropriately
- No reminders during suppressed states
- Users say "this feels respectful, not intrusive"

---

### Phase 5: Polish & Launch Prep (Feb 10-13)
**Goal:** Ready for public alpha

**Tasks:**

**Day 1 (Feb 10): Bug Bash**
- Fix top 5 bugs from alpha testing
- Performance optimization (if needed)
- Mobile responsiveness check

**Day 2 (Feb 11): Content & Positioning**
- Landing page copy
- Demo video (5 minutes)
- Alpha invite email template
- ProductHunt draft post

**Day 3 (Feb 12): Final Testing**
- End-to-end user flow walkthrough
- Test with fresh user account
- Verify all 3 features work together

**Day 4 (Feb 13): Launch**
- Email 10-20 alpha users
- Post on Twitter/LinkedIn
- (Optional) Soft launch on ProductHunt

---

## Alpha Feature Specs

### Feature 1: Contradictions

**User Story:**
"As a user, I want to see when my actions don't match my stated intentions, so I can become aware of blind spots."

**Acceptance Criteria:**
- [ ] Detects "I will/need to/should" statements in journals
- [ ] Checks for follow-through in next 7-14 days
- [ ] Shows top 3-5 contradictions with evidence
- [ ] Evidence links to original journal entries
- [ ] No false positives (manually validated with demo user)
- [ ] Reflection-compliant (no advice, just observation)

**UI Mockup:**
```
┌─────────────────────────────────────┐
│  Your Contradictions (Last 30 Days) │
├─────────────────────────────────────┤
│                                      │
│  🎭 Intention vs. Action             │
│                                      │
│  "I need better boundaries"          │
│  → Said 8 times                      │
│  → Set boundaries: 0 times           │
│  → Said yes to requests: 12 times    │
│                                      │
│  [Show Evidence]                     │
│                                      │
├─────────────────────────────────────┤
│  More contradictions...              │
└─────────────────────────────────────┘
```

---

### Feature 2: Intelligent Scheduling

**User Story:**
"As a user, I want to know my optimal focus times based on my rhythm, so I can plan important work accordingly."

**Acceptance Criteria:**
- [ ] Morning preview delivered by 8am (if not suppressed)
- [ ] Shows best focus window for today
- [ ] Based on minimum 4 weeks of rhythm data
- [ ] Evening summary delivered by 6pm (if not suppressed)
- [ ] Shows tomorrow's capacity forecast
- [ ] Accuracy validated by user feedback ("was this right?")

**UI Mockup:**
```
┌─────────────────────────────────────┐
│  Good Morning                        │
├─────────────────────────────────────┤
│  Your Best Focus Window Today:       │
│  9:30am - 11:30am                    │
│                                      │
│  Based on 12 weeks of data:          │
│  • Tuesday mornings = peak capacity  │
│  • Avoid meetings before noon        │
│                                      │
│  Rhythm: ████████░░ (80% capacity)   │
└─────────────────────────────────────┘
```

---

### Feature 3: Context-Aware Reminders

**User Story:**
"As a user, I want reminders to respect my state, so I'm not interrupted during vulnerable moments."

**Acceptance Criteria:**
- [ ] User can create reminders with context hints
- [ ] System checks suppression before delivery
- [ ] Defers reminder if user is in crisis/exhaustion/conflict
- [ ] Shows transparency ("I didn't remind you because...")
- [ ] User can manually trigger deferred reminders
- [ ] Logs all suppression decisions

**UI Mockup:**
```
┌─────────────────────────────────────┐
│  Create Reminder                     │
├─────────────────────────────────────┤
│  What: Finish pitch deck             │
│  When: When I have focus capacity    │
│                                      │
│  [✓] Only during flow state          │
│  [✓] Not if exhausted                │
│  [✓] Not during crisis               │
│                                      │
│  [Save]                              │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│  Reminder Deferred                   │
├─────────────────────────────────────┤
│  "Finish pitch deck"                 │
│  was scheduled for 3pm today         │
│                                      │
│  Suppression reason:                 │
│  Emotion volatility detected         │
│                                      │
│  Rescheduled: Tomorrow 10am          │
│  [Override & Show Now]               │
└─────────────────────────────────────┘
```

---

## Technical Architecture

### Foundation (Already Built)

**Layer 1: Evidence**
- Journal ingestion (unified_ingest)
- Timestamp tracking
- Raw content preservation

**Layer 2: Memory**
- Episodic memory v2.1 (consolidation, context tagging)
- Short-term memory (recent events)
- Weekly/monthly summaries

**Layer 3: Deterministic Intelligence**
- `rhythm_state` - Energy patterns, chronotype
- `emotion_state` - Emotional signals (ESR)
- `identity_momentum_state` - Identity drift tracking
- `soul_state` - Values alignment
- `decision_graph_deep` - Internal conflicts

**Layer 4: Scaffolding**
- Suppression engine (6 rules: crisis, silence, conflict, exhaustion, volatility, low engagement)
- @require_suppression_check decorator on all proactive scaffolds
- Sensitivity levels (LOW/MEDIUM/HIGH)

**Layer 5: Reflection**
- Reflection renderer v1 (read-only, no advice)
- Observation-only language
- Evidence attribution

---

### New Components (To Build)

**Contradiction Detector**
```python
# sakhi/libs/intelligence/contradiction_detector.py

async def detect_contradictions(
    person_id: str,
    window_days: int = 30
) -> List[Contradiction]:
    """
    Detect contradictions between stated intentions and observed behavior

    Returns:
        List of Contradiction objects with:
        - statement: What they said
        - evidence_against: What they did instead
        - pattern: How often this happens
        - confidence: How certain we are (0-1)
    """
```

**Scheduling Optimizer**
```python
# sakhi/apps/engine/scheduling/optimizer.py

async def get_optimal_focus_windows(
    person_id: str,
    target_date: date
) -> List[FocusWindow]:
    """
    Calculate optimal focus windows based on rhythm data

    Returns:
        List of FocusWindow objects with:
        - start_time: Recommended start
        - end_time: Recommended end
        - capacity: Expected capacity (0-1)
        - confidence: Based on historical data
    """
```

**Smart Reminder Delivery**
```python
# sakhi/apps/engine/reminders/smart_delivery.py

async def should_deliver_reminder(
    person_id: str,
    reminder: Reminder
) -> DeliveryDecision:
    """
    Check if reminder should be delivered now

    Returns:
        DeliveryDecision with:
        - deliver: bool
        - reason: Why/why not
        - defer_until: If deferred, when to retry
    """
```

---

## Alpha Pricing Model

### Free Tier (Validation)
**Purpose:** Let users experience core value before asking for payment

**Includes:**
- 3 contradictions per month
- Basic scheduling suggestions (today only)
- 5 context-aware reminders per month
- 30-day data retention

**Goal:** Convert 20% to premium after 14 days

---

### Premium Tier ($15/month or $150/year)
**Purpose:** Unlock full value for committed users

**Includes:**
- Unlimited contradictions with full history
- Advanced scheduling (multi-week optimization)
- Unlimited reminders with location context (future)
- 2-year data retention
- Longitudinal identity tracking
- Priority support (email, 48hr response)

**Annual Discount:** $150/year (save $30 = 17% off)

---

### Ultra Tier ($50/month) [Future]
**Purpose:** Premium features for power users

**Includes:**
- Everything in Premium
- Multi-year contradiction tracking (3+ years)
- Predictive scheduling with ML
- API access for custom integrations
- White-glove onboarding
- Priority feature requests

---

## Success Metrics

### Alpha Phase (Feb 13 - March 13)

**Engagement Metrics:**
- [ ] 10 alpha users signed up
- [ ] 70% weekly active rate (7 of 10 users)
- [ ] 3+ sessions per week per user
- [ ] Average session: 5-10 minutes

**Feature Validation:**
- [ ] Contradictions: 80% say "accurate and valuable"
- [ ] Scheduling: 60% check daily
- [ ] Reminders: 70% trust suppression decisions

**Conversion Intent:**
- [ ] 5 users say "I would pay $15/month"
- [ ] 2 users actually pay when asked
- [ ] 0 critical bugs or data loss incidents

**Qualitative Feedback:**
- [ ] Record 5 user interviews (15-30 min each)
- [ ] Identify top 3 feature requests
- [ ] Identify top 3 pain points

---

## Go-to-Market Strategy

### Pre-Launch (Jan 20 - Feb 12)

**Build Waitlist:**
- Twitter thread about contradictions concept
- LinkedIn post about "AI that shows patterns, not prescriptions"
- Personal outreach to 20 potential alpha users

**Content Creation:**
- Demo video (5 min, screen recording with voiceover)
- Landing page with value prop + waitlist
- Alpha invite email template

---

### Launch Day (Feb 13)

**Alpha Invite (10-20 users):**
```
Subject: You're invited: Try Sakhi Alpha

Hi [Name],

You're one of 10 people I'm inviting to try Sakhi's alpha.

Sakhi shows you patterns you can't see:
• When your actions don't match your intentions
• Your optimal focus times (based on your rhythm)
• Reminders that respect your state

It's free during alpha. I just need your feedback.

[Sign Up] (5 min setup)

What I need from you:
1. Journal for 2 weeks (import past journals if you have them)
2. Try the 3 core features
3. 15-min feedback call

Interested? Reply to claim your spot.

[Your Name]
```

**Public Announcement:**
- Twitter: "I built an AI that shows you when you're lying to yourself"
- LinkedIn: Professional framing (longitudinal intelligence)
- ProductHunt: Soft launch (if ready)

---

### Post-Launch (Feb 13+)

**Week 1-2: Active Support**
- Daily check-ins with alpha users
- Fix critical bugs within 24 hours
- Collect feedback (async + calls)

**Week 3-4: Iteration**
- Ship top 2 feature requests
- Improve accuracy based on feedback
- Prepare for paid beta (March)

---

## Risk Mitigation

### Risk 1: Foundation Instability
**Symptom:** Workers crash, suppression fails, data loss
**Mitigation:**
- Comprehensive testing Jan 6-13
- Lab UI for internal validation
- Rollback plan for each worker

---

### Risk 2: Features Don't Resonate
**Symptom:** Users don't engage, no "holy shit" moments
**Mitigation:**
- Get 1 alpha user per feature (validate early)
- Ship Feature 1 (contradictions) first
- Iterate based on feedback before building Feature 3

---

### Risk 3: Pricing Too High/Low
**Symptom:** Users love it but won't pay / underpricing value
**Mitigation:**
- Ask willingness-to-pay during alpha
- Offer annual discount to de-risk commitment
- Free tier validates value before asking for money

---

### Risk 4: Data Privacy Concerns
**Symptom:** Users hesitant to share journals
**Mitigation:**
- Clear privacy policy (local-first future roadmap)
- No data selling, no ads
- Transparency: show what we store, offer export

---

### Risk 5: Comparison to Competitors
**Symptom:** "This is just like [Reflect/Day One/Notion AI]"
**Mitigation:**
- Lead with contradictions (unique)
- Emphasize suppression-first (no competitor does this)
- Show longitudinal data advantage (moat)

---

## Resources & Dependencies

### Team (Assumption: Solo Founder + AI Assistant)
- **Engineering:** Full-time (you)
- **Design:** DIY (Lab UI patterns reused)
- **Marketing:** Personal network + organic
- **Support:** You (alpha phase)

### External Dependencies
- **LLM API:** OpenAI/Anthropic (cost: ~$50-200/month during alpha)
- **Database:** PostgreSQL (existing)
- **Hosting:** Current infrastructure
- **Email:** Existing provider

### Time Allocation (Feb 13 Deadline)
- **Foundation (Jan 6-13):** 40 hours
- **Feature 1 (Jan 13-20):** 30 hours
- **Feature 2 (Jan 20-Feb 3):** 50 hours
- **Feature 3 (Feb 3-10):** 30 hours
- **Polish (Feb 10-13):** 20 hours
- **Total:** ~170 hours over 5 weeks = 34 hours/week

---

## Post-Alpha Roadmap (March+)

### Immediate Next (March)
1. **Paid Beta:** Convert alpha users to Premium
2. **Feature Refinement:** Based on alpha feedback
3. **Mobile App:** iOS/Android (stretch goal)

### Q2 2025
1. **Calendar Integration:** Sync with Google/Apple Calendar
2. **Location Context:** Reminders based on location
3. **Export/Import:** Data portability

### Q3 2025
1. **Multi-Year Analysis:** Decade-scale identity tracking
2. **Collaboration:** Share patterns with therapist/coach (B2B pivot?)
3. **API:** Let developers build on Sakhi

---

## Decision Points

### Go/No-Go Criteria (Feb 13)

**Go → Continue Building:**
- 5+ alpha users actively engaged
- 2+ users express willingness to pay
- Core features work without critical bugs
- Positive qualitative feedback

**No-Go → Pivot:**
- <3 alpha users engaged
- 0 users willing to pay
- Frequent crashes or data loss
- Feedback: "not useful" or "too complex"

---

## Appendix A: Competitor Analysis

### Day One (Journaling App)
**What they do:** Private journaling, search, photos
**What they don't do:** Pattern detection, contradictions, intelligent scheduling
**Our advantage:** Intelligence layer, longitudinal analysis

### Reflect (AI Journaling)
**What they do:** AI-powered prompts, weekly reviews, tagging
**What they don't do:** Suppression logic, rhythm-based scheduling, contradiction detection
**Our advantage:** Suppression-first, behavioral signals

### Notion AI (Workspace AI)
**What they do:** Summarization, writing assistance
**What they don't do:** Personal intelligence, longitudinal tracking
**Our advantage:** Purpose-built for self-awareness, not productivity

---

## Appendix B: Key Design Principles

### 1. Suppression First
Every proactive scaffold checks user state before running. Silence is sometimes the most respectful response.

### 2. Evidence-Grounded
All insights must be traceable to journal entries or deterministic intelligence. No LLM hallucinations.

### 3. Reflection, Not Prescription
Show patterns, don't give advice. The user decides what to do with the information.

### 4. User Agency > System Initiative
The user can always override, defer, or ignore. The system suggests, never demands.

### 5. Transparency as Feature
Show your work. Let users see suppression decisions, data sources, confidence levels.

---

## Appendix C: Alpha User Interview Guide

### Pre-Interview (Setup)
- Send invite with 2-week lead time
- Ensure they've journaled for at least 7 days
- Ask them to try all 3 features before call

### Interview Questions (15-30 min)

**Opening (5 min):**
1. Tell me about your current journaling practice
2. What made you interested in trying Sakhi?

**Feature Validation (15 min):**
3. Did the contradictions feature resonate? Any examples?
4. Was the scheduling advice accurate? Did you use it?
5. Did you trust the reminder deferrals? Any false positives?

**Willingness to Pay (5 min):**
6. Would you pay for this? How much?
7. What would make it worth $15/month to you?

**Improvement (5 min):**
8. What's missing? What frustrated you?
9. If you could add one feature, what would it be?

**Closing:**
10. Would you recommend this to a friend? Why/why not?

---

## Document Control

**Version:** 1.0
**Created:** January 9, 2025
**Owner:** Sakhi Product Team
**Review Date:** February 13, 2025 (Post-Alpha Retrospective)

**Change Log:**
- v1.0 (Jan 9): Initial alpha release plan created

---

**End of Alpha Release Plan**
