# Sakhi Vision Gap Analysis

> Analyzing BUILD_PLAN.md and SAKHI_EVOLUTION_PLAN.md against the vision of Sakhi as a Personal Intelligence Companion and Personal OS.
>
> Last Updated: 2026-02-01

---

## The Vision

**"Sakhi: Infrastructure for humans to reclaim their lives."**

- The world comes through YOUR Sakhi
- You see everything, you decide everything
- Sakhi handles the friction
- You live your life — health, joy, connection

### What This Means Concretely

A **Personal OS** that:
1. **Knows you deeply** - preferences, patterns, relationships, energy, values
2. **Handles your friction** - scheduling, coordination, information management
3. **Protects your time** - filters, prioritizes, defends focus
4. **Nurtures your growth** - reflects, guides, celebrates progress
5. **Connects you to what matters** - health, relationships, purpose

---

## Current Documentation Status

### ✅ WELL DOCUMENTED

| Capability | Where | Status |
|------------|-------|--------|
| **Reflection Engine** | Evolution Plan Phase 1 | ✅ COMPLETE |
| → Relationship Model | `services/relationships/` | Built |
| → Scheduling Preferences | `services/scheduling/` | Built |
| → Knowledge Graph | `causal_reasoning.py` | Built |
| → Personalized Recommendations | `services/recommendations/` | Built |
| **Execution Layer** | Evolution Plan Phase 2 | ✅ COMPLETE |
| → Native Calendar | `services/calendar/` | Built |
| → Conversational Scheduling | Intent detection | Built |
| → Confirmation Flow | User-in-control | Built |
| **Mesh Network** | Evolution Plan Phase 3 | ✅ COMPLETE |
| → Sakhi-to-Sakhi | Coordination protocol | Built |
| → Trust Levels | Privacy-respecting | Built |
| **Desktop Automation** | Evolution Plan Phase 4c | ✅ COMPLETE |
| → Vision Loop | Screenshot + LLM | Built |
| → Task Execution | Error handling, retry | Built |
| **Demo Capabilities** | Build Plan Current Focus | 🔨 IN PROGRESS |
| → Hybrid Search | BM25 + Vector | Planned |
| → Personalization Engine | Taste, sensory | Planned |
| → Demo UI | Split-screen | Planned |

### ⚠️ PARTIALLY DOCUMENTED

| Capability | Current State | Gap |
|------------|---------------|-----|
| **Proactive Intelligence** | Phase 4 mentions "Sakhi suggests" | No concrete spec for when/how Sakhi initiates |
| **Daily Rhythm Support** | Chronotype exists, energy curves | No morning briefing, no evening wind-down |
| **Health Integration** | Ayurveda/dosha only | No sleep, exercise, nutrition tracking |
| **Relationship Nurturing** | "Needs attention" query exists | No birthday/anniversary reminders, no proactive nudges |
| **Email** | "Planned" in native ecosystem | No detailed spec for `@user.sakhi.id` |

### ❌ NOT DOCUMENTED (Critical Gaps)

| Capability | Why It Matters | Impact on Vision |
|------------|----------------|------------------|
| **Voice Interface** | "The world comes through Sakhi" needs voice | Can't be ambient companion without voice |
| **Mobile Experience** | Desktop only currently | Users need Sakhi everywhere |
| **Morning Briefing** | Start day with clarity | Missing core "reclaim your life" feature |
| **Information Diet** | "You see everything, you decide" | No curation, filtering, or info protection |
| **Focus Protection** | "Sakhi handles friction" | No do-not-disturb, no focus mode |
| **Financial Awareness** | Core life friction | No money tracking, subscriptions, budgets |
| **Learning/Growth** | "Live your life" includes growth | No skill tracking, learning suggestions |
| **Multi-Device Sync** | Personal OS must be everywhere | Not specified |
| **Offline Capability** | Reliability | No offline mode documented |
| **Data Sovereignty** | Privacy is core to trust | Export, self-host, encryption not detailed |

---

## Gap Analysis by Vision Pillar

### Pillar 1: "The World Comes Through YOUR Sakhi"

**What this means:** Sakhi is the interface to the world - information, communication, services.

| Need | Documented | Gap |
|------|------------|-----|
| Information ingestion | ✅ Journal, voice | ❌ News, articles, feeds |
| Information curation | ❌ | Need: Personalized filtering |
| Communication hub | Partial (Mesh) | Need: Email (spec incomplete), messaging |
| Service access | ✅ Vision Loop | Need: More native integrations |
| Voice interface | ❌ | Need: Always-on voice capability |
| Mobile access | ❌ | Need: Mobile app/PWA |

**Missing Features:**
1. **Morning Briefing** - "Here's your day: 3 meetings, Alex's birthday, Vata is high"
2. **Information Curation** - Filter news/content based on interests, mood, capacity
3. **Message Prioritization** - "These 2 emails need attention today"
4. **Voice Commands** - "Sakhi, what's my day look like?"

### Pillar 2: "You See Everything, You Decide Everything"

**What this means:** User has full visibility and control. Sakhi surfaces, user chooses.

| Need | Documented | Gap |
|------|------------|-----|
| Dashboard/overview | Partial (Calendar UI) | Need: Unified personal dashboard |
| Transparency | ✅ Reasoning shown | Good |
| User confirms actions | ✅ Confirmation flow | Good |
| Privacy controls | ❌ | Need: Granular sharing controls |
| Data export | ❌ | Need: Full data portability |

**Missing Features:**
1. **Personal Dashboard** - One view: calendar, tasks, relationships, energy, money
2. **Notification Control** - User sets what Sakhi can interrupt for
3. **Audit Trail** - "What did Sakhi do on my behalf this week?"
4. **Privacy Center** - What data Sakhi has, who it's shared with

### Pillar 3: "Sakhi Handles the Friction"

**What this means:** Sakhi automates the tedious, coordinates the complex.

| Need | Documented | Gap |
|------|------------|-----|
| Scheduling | ✅ Calendar, Mesh | Good |
| Booking | Partial (Vision Loop) | Need: Native for common services |
| Bill pay | ❌ | Need: Financial automation |
| Renewals/subscriptions | ❌ | Need: Subscription management |
| Travel coordination | ❌ | Need: Travel planning |
| Shopping | Partial (Vision Loop demo) | Need: Shopping list, preferences |

**Missing Features:**
1. **Subscription Manager** - Track, remind, cancel subscriptions
2. **Bill Reminders** - "Electricity bill due in 3 days"
3. **Travel Assistant** - Plan trips considering energy, preferences
4. **Shopping Intelligence** - Remember sizes, preferences, reorder patterns

### Pillar 4: "You Live Your Life — Health, Joy, Connection"

**What this means:** Free from friction, user focuses on what matters.

#### Health

| Need | Documented | Gap |
|------|------------|-----|
| Ayurvedic state | ✅ Dosha, Guna | Good |
| Energy tracking | ✅ Operating System | Good |
| Sleep | Partial (mentioned) | Need: Integration with sleep data |
| Exercise/movement | ❌ | Need: Activity awareness |
| Nutrition | Partial (food_reco planned) | Need: Deeper food intelligence |
| Medication | ❌ | Need: Medication reminders |

**Missing Features:**
1. **Sleep Intelligence** - Connect sleep patterns to energy/dosha
2. **Movement Nudges** - "You've been sitting for 2 hours"
3. **Meal Timing** - Ayurvedic meal timing recommendations
4. **Medication Tracker** - Reminders, refill alerts

#### Joy

| Need | Documented | Gap |
|------|------------|-----|
| Hobbies/interests | Partial (preferences) | Need: Hobby tracking, suggestions |
| Entertainment | ❌ | Need: Music, shows, books preferences |
| Celebrations | ❌ | Need: Birthdays, milestones |
| Gratitude/reflection | ✅ Journal, synthesis | Good |

**Missing Features:**
1. **Hobby Time** - "You haven't played guitar in 2 weeks"
2. **Entertainment Matching** - Recommend based on mood/energy
3. **Milestone Celebration** - "One year since you started meditation!"

#### Connection

| Need | Documented | Gap |
|------|------------|-----|
| Relationship tracking | ✅ Rich model | Good |
| Connection reminders | Partial | Need: Proactive "call Mom" |
| Birthday/anniversary | ❌ | Need: Date tracking |
| Gift suggestions | ❌ | Need: Based on relationship context |
| Shared memories | Partial (memory graph) | Need: "Remember when" surfacing |

**Missing Features:**
1. **Birthday/Anniversary Alerts** - "Sarah's birthday is Friday"
2. **Connection Nudges** - "You haven't talked to Alex in 6 weeks"
3. **Gift Intelligence** - "Based on Alex's interests: [suggestions]"
4. **Memory Surfacing** - "This day last year, you [memory]"

---

## Recommended Documentation Additions

### HIGH PRIORITY (Core to Vision)

#### 1. Voice Interface Spec
```
Location: SAKHI_EVOLUTION_PLAN.md Phase 4 or new section

Contents:
- Wake word or push-to-talk
- Voice input processing
- Voice output (TTS)
- Always-on vs on-demand
- Privacy considerations (local vs cloud)
- Mobile integration
```

#### 2. Morning Briefing Feature
```
Location: BUILD_PLAN.md new section or SAKHI_EVOLUTION_PLAN.md Phase 4

Contents:
- What's included: calendar, tasks, energy prediction, relationship nudges
- Delivery: voice, notification, or dashboard
- Timing: user preference, circadian-aware
- Personalization: adapt based on engagement
```

#### 3. Mobile Experience
```
Location: BUILD_PLAN.md Platform section

Contents:
- PWA vs native app
- Core features on mobile
- Sync with desktop
- Offline capability
- Push notifications
```

#### 4. Personal Dashboard
```
Location: BUILD_PLAN.md or new UI spec

Contents:
- Unified view: calendar, tasks, energy, relationships, finances
- Customizable widgets
- Glanceable design
- Mobile-first
```

### MEDIUM PRIORITY (Enhances Vision)

#### 5. Financial Awareness
```
Location: BUILD_PLAN.md Native Ecosystem section

Contents:
- Subscription tracking
- Bill reminders
- Budget awareness (optional)
- Not full banking - just awareness
```

#### 6. Information Diet
```
Location: New section in Evolution Plan

Contents:
- Content sources (RSS, newsletters, etc.)
- Personalized filtering
- "Save for later" queue
- Reading time estimation
- Mood-appropriate surfacing
```

#### 7. Focus Protection
```
Location: BUILD_PLAN.md or Evolution Plan

Contents:
- Do-not-disturb modes
- Focus time blocking
- Interruption filtering
- Context-aware notifications
```

### LOWER PRIORITY (Nice to Have)

#### 8. Entertainment/Joy Features
```
- Music preferences and mood matching
- Book/show recommendations
- Hobby tracking
- Milestone celebrations
```

#### 9. Health Integrations
```
- Sleep data import (Apple Health, Oura, etc.)
- Exercise tracking
- Medication reminders
```

---

## Updated Vision Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              SAKHI PERSONAL OS                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                         INTERFACE LAYER                              │    │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐   │    │
│  │  │ Voice   │  │ Mobile  │  │ Desktop │  │Dashboard│  │  API    │   │    │
│  │  │   ❌    │  │   ❌    │  │   ✅    │  │   ⚠️    │  │   ✅    │   │    │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘   │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                      INTELLIGENCE LAYER                              │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                  │    │
│  │  │ Reflection  │  │ Proactive   │  │ Automation  │                  │    │
│  │  │   Engine    │  │Intelligence │  │   Engine    │                  │    │
│  │  │     ✅      │  │     ⚠️      │  │     ✅      │                  │    │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                  │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                  │    │
│  │  │  Ayurveda   │  │ Personalize │  │   Memory    │                  │    │
│  │  │  + Patterns │  │   Engine    │  │    Graph    │                  │    │
│  │  │     ✅      │  │     ⚠️      │  │     ✅      │                  │    │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        EXECUTION LAYER                               │    │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐   │    │
│  │  │Calendar │  │  Tasks  │  │  Notes  │  │  Mesh   │  │ Vision  │   │    │
│  │  │   ✅    │  │   ✅    │  │   ✅    │  │   ✅    │  │  Loop   │   │    │
│  │  │         │  │         │  │         │  │         │  │   ✅    │   │    │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘   │    │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐   │    │
│  │  │ Email   │  │ Finance │  │ Health  │  │ Focus   │  │ Info    │   │    │
│  │  │   ⚠️    │  │   ❌    │  │   ⚠️    │  │  Prot.  │  │  Diet   │   │    │
│  │  │         │  │         │  │         │  │   ❌    │  │   ❌    │   │    │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘   │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        PLATFORM LAYER                                │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                  │    │
│  │  │   Privacy   │  │ Multi-Device│  │   Offline   │                  │    │
│  │  │  + Export   │  │    Sync     │  │    Mode     │                  │    │
│  │  │     ❌      │  │     ❌      │  │     ❌      │                  │    │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  Legend: ✅ Built  ⚠️ Partial/Planned  ❌ Not Documented                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Action Items

### Immediate (Add to BUILD_PLAN.md)

1. [ ] **Voice Interface** - Add to Platform section with phases:
   - Phase 1: Voice input (speech-to-text)
   - Phase 2: Voice output (TTS for briefings)
   - Phase 3: Always-on assistant mode

2. [ ] **Mobile Experience** - Add to Platform section:
   - PWA for immediate cross-platform
   - Native apps later if needed

3. [ ] **Morning Briefing** - Add to Proactive Intelligence section:
   - Calendar + tasks + energy + relationships
   - Voice delivery option

4. [ ] **Personal Dashboard** - Add to UI section:
   - Unified glanceable view
   - Widget-based customization

### Short Term (Add to SAKHI_EVOLUTION_PLAN.md Phase 4)

5. [ ] **Proactive Intelligence Spec** - Detail when/how Sakhi initiates:
   - Morning briefing timing
   - Relationship nudge triggers
   - Health intervention triggers

6. [ ] **Birthday/Anniversary Tracking** - Add to Relationship Model:
   - Store important dates
   - Reminder logic

7. [ ] **Focus Protection** - Add as new capability:
   - Do-not-disturb modes
   - Interruption filtering

### Medium Term (New Documentation)

8. [ ] **Privacy & Data Sovereignty Doc** - Create `PRIVACY_ARCHITECTURE.md`:
   - Data storage model
   - Export capabilities
   - Self-hosting option
   - Encryption at rest

9. [ ] **Financial Awareness Spec** - Add to Native Ecosystem:
   - Subscription tracking
   - Bill reminders (not full banking)

---

## Conclusion

### What's Strong

The current documentation does well on:
- **Reflection/Intelligence** - Ayurveda, patterns, recommendations are solid
- **Execution** - Calendar, scheduling, mesh are complete
- **Automation** - Vision loop with proper error handling
- **Demo Path** - Clear 10-day demo build plan

### Critical Gaps for Vision

To be a true **Personal OS** that helps people **reclaim their lives**, we need to document:

1. **Voice Interface** - Can't be a companion without voice
2. **Mobile Experience** - Must be everywhere
3. **Morning Briefing** - Daily engagement hook
4. **Proactive Intelligence** - Sakhi initiates, not just responds
5. **Focus Protection** - Defend user's attention
6. **Data Sovereignty** - Trust requires control

### Recommended Next Steps

1. Update BUILD_PLAN.md with Voice + Mobile + Dashboard sections
2. Expand SAKHI_EVOLUTION_PLAN.md Phase 4 with Proactive Intelligence spec
3. Create PRIVACY_ARCHITECTURE.md for data sovereignty
4. Add Success Metrics for "reclaim your life" outcomes

---

## References

- [BUILD_PLAN.md](./BUILD_PLAN.md)
- [SAKHI_EVOLUTION_PLAN.md](../SAKHI_EVOLUTION_PLAN.md)
- [sakhi-vs-openclaw-comparison.md](./sakhi-vs-openclaw-comparison.md)
