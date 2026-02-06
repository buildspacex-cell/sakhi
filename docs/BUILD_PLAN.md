# Sakhi Build Plan

> Living document tracking all planned work. Update checkboxes as items are completed.
>
> Last Updated: 2026-02-05
>
> **Coverage**: 100% — All demo capabilities have paths to become REAL (not just simulated)
>
> **Latest**: Phase B (Voice) and Phase C (Dashboard) COMPLETE. Mobile apps now TOP PRIORITY.

---

## Overview

Sakhi is a personal AI companion with vision-based desktop automation and a self-contained ecosystem for calendar, tasks, notes, contacts, and email.

**Vision**: "Sakhi: Infrastructure for humans to reclaim their lives."
- The world comes through YOUR Sakhi
- You see everything, you decide everything
- Sakhi handles the friction
- You live your life — health, joy, connection

**Strategy**: Web + API foundation ✅ → **Mobile Apps NOW** → Desktop Agent polish

---

## Completed Phases

> See [SAKHI_EVOLUTION_PLAN.md](../SAKHI_EVOLUTION_PLAN.md) for full details.

### ✅ Phase 1: Reflection Gaps (COMPLETE)

| Status | Item | Description | Files |
|--------|------|-------------|-------|
| ✅ | Relationship Model | Rich relationship data (type, closeness, context, patterns) | `services/relationships/` |
| ✅ | Scheduling Preferences | When/where/how user likes to meet | `services/scheduling/` |
| ✅ | Knowledge Graph | Causal reasoning + pattern learning | `services/ayurveda/causal_reasoning.py` |
| ✅ | Personalized Recommendations | Context-aware, history-grounded suggestions | `services/recommendations/` |

### ✅ Phase 2: Execution Layer (COMPLETE)

| Status | Item | Description | Files |
|--------|------|-------------|-------|
| ✅ | Sakhi Calendar | Events, availability, attendees | `services/calendar/`, `routes/calendar.py` |
| ✅ | Conversational Scheduling | Natural language intent detection | `services/calendar/scheduling.py` |
| ✅ | Confirmation Flow | Suggest → Confirm → Create | `routes/turn_v2.py` |
| ✅ | Calendar UI | Today/week view with context | `apps/web/app/experience/calendar/` |

### ✅ Phase 3: Sakhi-to-Sakhi Mesh (COMPLETE)

| Status | Item | Description | Files |
|--------|------|-------------|-------|
| ✅ | Mesh Entities | People & businesses | `services/mesh/entities.py` |
| ✅ | Connections | Trust levels (minimal, standard, full) | `services/mesh/connections.py` |
| ✅ | Coordination Protocol | Scheduling, inquiry, transaction | `services/mesh/coordination.py` |
| ✅ | Privacy-Respecting Availability | Share what you choose | `services/mesh/availability.py` |

### ✅ Phase 4c: Desktop Agent (COMPLETE)

| Status | Item | Description | Files |
|--------|------|-------------|-------|
| ✅ | Electron App | macOS DMG installer | `sakhi/apps/desktop-agent/` |
| ✅ | Device Linking | OAuth-style code flow | `routes/agent.py` |
| ✅ | Permissions | Accessibility, Screen Recording | `desktop-agent/` |
| ✅ | Action Execution | navigate, click, type, scroll | `services/agent/actions.py` |
| ✅ | Error Classification | `AgentError` with `ErrorReason` enum | `errors.py` |
| ✅ | Retry Logic | 3-layer retry with exponential backoff | `vision_loop.py` |
| ✅ | Timeout Clamping | `clamp_timeout()` with min/max bounds | `timeouts.py` |
| ✅ | Session Locking | PostgreSQL advisory locks | `session_lock.py` |
| ✅ | Command Queue | Thread-safe with `asyncio.Lock` | `actions.py` |
| ✅ | Action History | 50-item compaction (first 5 + last 45) | `vision_loop.py` |

---

## BUILD SEQUENCE

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SAKHI BUILD SEQUENCE                               │
│                                                                              │
│  🎯 PHASE M: MOBILE APPS (NOW)            ← TOP PRIORITY                    │
│  ├── M.1 React Native + Expo setup                                          │
│  ├── M.2 Core screens (Voice, Dashboard, Reflection)                        │
│  ├── M.3 Ayurvedic intelligence UI (dosha state, recommendations)           │
│  ├── M.4 iOS App Store submission                                           │
│  └── M.5 Android Play Store submission                                      │
│                                                                              │
│  PHASE A: Demo Build ✅ MOSTLY COMPLETE                                     │
│  ├── ✅ Simulation Personalization (Maya vs Diya)                           │
│  ├── ✅ Personalization Engine                                              │
│  ├── ✅ Reflective Intelligence                                             │
│  └── ✅ Demo UI Framework                                                   │
│                                                                              │
│  PHASE B: Voice Interface ✅ COMPLETE                                       │
│  ├── ✅ Speech-to-Text input                                                │
│  ├── ✅ Text-to-Speech output                                               │
│  └── ✅ Voice conversation mode                                             │
│                                                                              │
│  PHASE C: Personal Dashboard ✅ COMPLETE                                    │
│  ├── ✅ Unified glanceable view                                             │
│  ├── ✅ Widget system                                                       │
│  └── ✅ Customization (partial)                                             │
│                                                                              │
│  PHASE D: Proactive Intelligence (After Mobile)                             │
│  ├── Morning Briefing                                                       │
│  ├── Relationship Nudges                                                    │
│  └── Focus Protection                                                       │
│                                                                              │
│  PHASE E: Bridge Skills (After Mobile)                                      │
│  ├── Google Calendar Sync                                                   │
│  ├── Apple Calendar Sync                                                    │
│  └── Gmail Bridge                                                           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## PHASE A: Demo Build (Current - Week 1-2)

### 🎯 A.0.1 Simulation Personalization Demo (PRIORITY 1)

> **Why**: Shows how Sakhi gives DIFFERENT advice to different people based on their prakruti (constitutional type). This is the "aha moment" for investors — demonstrates personalization is REAL, not generic.

| Status | Item | Description | Files | Test Criteria |
|--------|------|-------------|-------|---------------|
| ✅ | Maya Persona | Pitta-dominant (50%), burnout & recovery arc | `personas/anxious_achiever.yaml` | 66 days simulated |
| ✅ | Diya Persona | Kapha-Vata (50%/30%), menstrual cycle focus | `personas/hormonal_harmony.yaml` | 68 days, cycle-aware |
| ✅ | Persona Selector | Switch between Maya, Alex, Diya with prakruti badges | `simulation/client.tsx` | Shows prakruti type |
| ✅ | Current Friction State | Shows REAL computed friction state from snapshot | `simulation/client.tsx` | Displays actual drift, focus areas |
| ✅ | Generate Diya Data | Run worker pipeline for Diya's journals | `export_real_simulation.py` | 30 days, 56 entries, 31 snapshots |
| ✅ | LLM Recommendation API | Real LLM-powered recommendations by constitution | `friction_framework.py` + `/api/.../by-constitution` | Calls Python backend with LLM |
| ✅ | Conversation LLM Reasoning | Verified LLM reasoning flows through conversation system | `turn_v2.py` → `synthesizer.py` → `conversation_engine.py` | Same reasoning in chat |

**Demo Flow**:
1. Show Maya - friction state, drift from baseline, recommendations focus areas (real computed data)
2. Click "Get Personalized Advice" - real LLM generates constitution-specific recommendations
3. Switch to Diya - same symptom, different advice because of different constitution
4. Explain: This is REAL personalization, not hardcoded - the LLM generates advice based on Ayurvedic principles

**LLM Reasoning Architecture** (Verified):
```
Simulation Page                    Conversation Flow
      │                                  │
      ▼                                  ▼
/api/.../by-constitution          turn_v2.py (lines 1109-1114)
      │                                  │
      ▼                                  ▼
friction_framework.py             generate_personalized_recommendations()
      │                                  │
      ▼                                  ▼
_generate_constitution_           synthesizer.py → build_adaptive_prompt()
recommendations_llm()                    │
      │                                  ▼
      ▼                            conversation_engine.py → call_llm()
GPT-4o-mini generates                    │
constitution-specific advice             ▼
                                   GPT-4o-mini generates
                                   contextual response with reasoning
```

Both paths use real LLM generation - no hardcoded advice.

**Command to generate Diya's data**:
```bash
python -m sakhi.tests.longitudinal.export_real_simulation --persona hormonal_harmony
```

**Test**: Navigate to `/lab/simulation`, switch between Maya and Diya, see personalization comparison section with different recommendations.

### A.0.2 User Experience Gap: Simulation vs Real User (IDENTIFIED)

> **Why**: The simulation page shows investors everything Sakhi understands (friction state, reasoning, recommendations). But actual users chatting with Sakhi see none of this — the chat is a black box. We need to close this gap so users experience the same "aha moment" investors see.

**Gap Analysis**:

```
┌─────────────────────────────────────────────────────────────────┐
│ SIMULATION (Investor View) - What We Show                        │
│ ✅ Friction state (Chaos/Intensity/Stagnation)                   │
│ ✅ Drift from baseline (%)                                       │
│ ✅ Dosha breakdown (Vata/Pitta/Kapha)                            │
│ ✅ LLM-powered recommendations with "why"                        │
│ ✅ State changes over time                                       │
└─────────────────────────────────────────────────────────────────┘
                              vs
┌─────────────────────────────────────────────────────────────────┐
│ CHAT EXPERIENCE (User View) - What Users See                     │
│ ❌ Just text replies — no context, no state, no reasoning        │
│ ❌ No friction state indicator                                   │
│ ❌ No "why" explanation for advice                               │
│ ❌ No memory/pattern visibility                                  │
│ ❌ User thinks: "Generic chatbot"                                │
└─────────────────────────────────────────────────────────────────┘
                              vs
┌─────────────────────────────────────────────────────────────────┐
│ ME PAGE (Profile View) - What's Built                            │
│ ✅ Friction state + operating mode                               │
│ ✅ Baseline drift percentage + visual bars                       │
│ ✅ Operating system type + strengths                             │
│ ✅ Soul state (coherence, lights, shadows)                       │
│ ✅ Personalized recommendations (Quick Wins, Foods, Practices)   │
│ ✅ Weekly rhythm                                                 │
│ ⚠️  Disconnected from chat — user doesn't know this exists      │
└─────────────────────────────────────────────────────────────────┘
```

**What Backend Calculates vs What User Sees**:

| Dimension | Backend Has | Chat Shows | Me Page Shows |
|-----------|-------------|------------|---------------|
| Friction state | ✅ Full state | ❌ Nothing | ✅ Shows |
| Recommendations | ✅ LLM-powered | ❌ Nothing | ✅ Shows |
| Reasoning ("why") | ✅ Full context | ❌ Nothing | ⚠️ Partial |
| Memory context | ✅ Retrieved | ❌ Nothing | ❌ Nothing |
| State transitions | ✅ Tracked | ❌ Nothing | ❌ Nothing |
| Adaptive response | ✅ Full framework | ❌ Nothing | ❌ Nothing |

**Gaps to Close (TBD - Implementation Approach)**:

| Status | Item | Description | Files | Notes |
|--------|------|-------------|-------|-------|
| ✅ | Chat State Indicator | Show friction state in chat header/sidebar | `converse/page.tsx` | Friction state shown in chat |
| ✅ | Inline Reasoning | Surface "why" when giving advice in chat | `turn_v2.py` response | Expandable "Why this response?" panel |
| ✅ | Memory References | Show which memories Sakhi is using | Chat UI | Shows memories with scores |
| ✅ | State Change Notifications | Alert user when state changes | Chat or notification | Inline notification with explanation |
| ✅ | Chat ↔ Me Page Link | Connect chat to Me page insights | Navigation | "View your wellness profile" button |
| ⬜ | Daily Digest | Summary of state + recommendations | New page or widget | Morning/evening digest |
| ⬜ | Recommendation Tracking | Did user follow advice? Did it help? | Feedback loop | Close the loop |
| ✅ | Reasoning Transparency | Explain personalization to user | Expandable in chat | "Why this advice for you" |

**Key Insight**: The infrastructure is built (backend calculates everything). The gap is surfacing it to users so they experience the same "aha moment" that investors see in the simulation.

**Decision Needed**: How much transparency vs simplicity? Options:
1. **Minimal**: Just add friction state indicator to chat
2. **Moderate**: State indicator + inline reasoning when appropriate
3. **Full**: Complete transparency with debug panel for curious users

---

### ✅ A.0.3 Foundation: Hybrid Search (COMPLETE)

| Status | Item | Description | Files | Test Criteria |
|--------|------|-------------|-------|---------------|
| ✅ | BM25 Search | PostgreSQL ts_rank keyword matching | `services/memory/bm25.py` | Query "Manali cabin" returns exact match first |
| ✅ | Hybrid Merge | 0.7 vector + 0.3 keyword weighting | `services/memory/recall.py` | Combined score beats pure vector for keywords |
| ⬜ | Memory Flush | Auto-persist before context compaction | `services/conversation/` | Important context survives compaction |

**Implementation**:
- `bm25.py`: `bm25_search_journals()`, `bm25_search_reflections()`, `bm25_search_memory_nodes()`, `bm25_search_facts()`, `bm25_search_all()`
- `recall.py`: `recall_advanced()` with hybrid scoring, `recall_with_keyword_boost()` (0.5/0.5), `recall_semantic_only()`

**Test**: ✅ VERIFIED
```bash
curl "http://localhost:8080/memory/recall?person_id=a&q=project%20deadline&k=5"
# Result: keyword_score=1.0 → score=0.610 (exact match boosted 5.5x vs semantic-only)
# "meditation" query → keyword_score=1.0 → score=0.553 (exact match found first)
```

**Bug Fixed**: Added `resolve_person()` to `/memory/recall` endpoint (was passing "a" instead of UUID).

### ✅ A.0.5 Demo Infrastructure (COMPLETE)

| Status | Item | Description | Files | Test Criteria |
|--------|------|-------------|-------|---------------|
| ✅ | Demo User Seeder | Create demo users with profiles | `services/demo/user_seeder.py` | Demo user exists with full profile |
| ✅ | Preference Seeder | Seed sensory preferences | `services/demo/preference_seeder.py` | 8 preference categories seeded |
| ✅ | Pattern Seeder | Seed patterns for causal reasoning | `services/demo/pattern_seeder.py` | 10+ patterns, behaviors, episodes |
| ✅ | Vision Demo Runner | Simulated/recorded/live modes | `services/demo/vision_demo.py` | Runs car perfume demo reliably |
| ✅ | Coordination Demo | Personal + Business mesh demos | `services/demo/coordination_demo.py` | Shows two Sakhis coordinating |
| ✅ | Demo API Routes | Full demo control endpoints | `routes/demo.py` | Seed + run demos via API |
| ✅ | DB Migration | Demo tables (patterns, behaviors, episodes) | `migrations/0047_demo_tables.sql` | Tables created |

**API Endpoints**:
- `POST /demo/seed/all` - Seed all demo data
- `POST /demo/run/vision` - Run vision loop demo
- `POST /demo/run/coordination/personal` - Run Mom's Sakhi demo
- `POST /demo/run/coordination/business` - Run Restaurant Sakhi demo
- `POST /demo/run/reflection` - Run causal reasoning demo
- `GET /demo/status` - Check demo data status

**Test**: `curl -X POST /demo/seed/all && curl -X POST /demo/run/full` returns all demo results.

### ✅ A.1 Vision Loop Polish (COMPLETE)

| Status | Item | Description | Files | Test Criteria |
|--------|------|-------------|-------|---------------|
| ✅ | Error Classification | AgentError with ErrorReason enum | `errors.py` | Done |
| ✅ | Retry Logic | 3-layer retry with exponential backoff | `vision_loop.py` | Done |
| ✅ | Vision Demo Runner | Simulated mode for reliable demos | `services/demo/vision_demo.py` | Done |
| ⬜ | Context Compaction | Compress LLM context on overflow | `vision_loop.py` | Loop survives 50+ steps |
| ✅ | Live Screen Analyzer | Claude 3.5 Sonnet via OpenRouter + image compression | `screen_analyzer.py` | OpenAI-style format, max 1568px |
| ✅ | Live Action Decider | Claude 3 Haiku via OpenRouter for fast decisions | `action_decider.py` | Returns valid action from screen analysis |

**Implementation Details**:
- `screen_analyzer.py`: Uses `MODEL_VISION` env var (default: `anthropic/claude-3-5-sonnet`)
- `action_decider.py`: Uses `MODEL_DECISION` env var (default: `anthropic/claude-3-haiku-20240307`)
- Image format: OpenAI-style `image_url` with data URL (compatible with OpenRouter)
- Screenshot compression: PIL-based, max 1568px dimension, JPEG for non-transparent images

**Test**: Vision loop browses Amazon, finds product in < 10 iterations.

### ✅ A.1.1 Browser Automation (COMPLETE)

> **Why**: Desktop agent requires installation and permissions. Browser automation via Playwright is cost-effective and demo-friendly.

| Status | Item | Description | Files | Test Criteria |
|--------|------|-------------|-------|---------------|
| ✅ | Playwright Wrapper | Server-side browser automation | `browser_automation.py` | Navigate, click, type, scroll work |
| ✅ | DOM-First Strategy | Free CSS/XPath/text selectors | `browser_automation.py` | 90% of tasks succeed without vision |
| ✅ | Vision Fallback | Claude Vision when DOM fails | `browser_automation.py` | Complex UIs handled gracefully |
| ✅ | Session Management | Persistent contexts, cookies | `browser_session.py` | Sessions survive across calls |
| ✅ | Credential Vault | Secure login storage | `browser_session.py` | Auto-fill for saved sites |
| ✅ | API Endpoints | Full browser control | `routes/agent.py` | `/browser/task`, `/browser/session`, etc. |

**Cost Optimization Strategy**:
```
User Task: "Find Italian restaurants"
           │
           ▼
┌─────────────────────────────────────┐
│ 1. DOM-Based (FREE)                 │
│    - CSS selectors, text matching   │
│    - ARIA roles, labels             │
│    - 90% of tasks succeed here      │
└─────────────────────────────────────┘
           │ If fails
           ▼
┌─────────────────────────────────────┐
│ 2. Vision-Assisted (PAID)           │
│    - Screenshot → Claude Vision     │
│    - Find coordinates               │
│    - Only for complex/dynamic UIs   │
└─────────────────────────────────────┘
```

**API Endpoints**:
- `POST /api/v1/agent/browser/task` - Run automated task
- `POST /api/v1/agent/browser/session` - Create manual session
- `POST /api/v1/agent/browser/action` - Execute single action
- `DELETE /api/v1/agent/browser/session/{id}` - Close session
- `POST /api/v1/agent/browser/credentials` - Store login

**Environment Variables**:
- `MODEL_VISION`: Vision model (default: `anthropic/claude-3-5-sonnet`)
- `MODEL_DECISION`: Decision model (default: `anthropic/claude-3-haiku-20240307`)
- `BROWSER_SESSION_DIR`: Session storage (default: `/tmp/sakhi/browser_sessions`)

**Test**: `curl -X POST /api/v1/agent/browser/task -d '{"task_description": "Search Google for weather", "starting_url": "https://google.com"}'`

**Test Results (Car Perfume Multi-Step Search)**:
```
✅ Navigate to Amazon
✅ Search for "car air freshener perfume"
✅ Extract products with prices (auto-detects INR/USD)
✅ Filter by budget ($20) and premium ($20-40)
✅ Click top product → extract reviews
✅ Return with recommendation + premium suggestion

Stats:
- Actions executed: 6
- DOM successes: 6 (100%)
- Vision fallbacks: 0
- Cost: $0 (all DOM-based!)
```

### ✅ A.1.2 Integration Testing (COMPLETE)

> **Why**: Browser automation needs to use user preferences so product searches return personalized results.

| Status | Item | Description | Files | Test Criteria |
|--------|------|-------------|-------|---------------|
| ✅ | Personalized Search Module | Browser + preferences integration | `personalized_search.py` | Products ranked by preference match |
| ✅ | Multi-currency Support | Parse INR, USD, EUR, etc. | `personalized_search.py` | Converts to USD automatically |
| ✅ | Combined Scoring | Preference match + review quality | `personalized_search.py` | 60% preference, 40% reviews |
| ✅ | API Endpoint | `/browser/search/personalized` | `routes/agent.py` | Returns ranked products with explanations |
| ✅ | Preference Summary | `/browser/search/preferences/{domain}` | `routes/agent.py` | Shows user's stored preferences |

**Architecture**:
```
User: "Find car air freshener under $20"
           │
           ▼
┌─────────────────────────────────────┐
│ 1. Browser Automation               │
│    - Search Amazon/Google Shopping  │
│    - Extract products (title, price,│
│      rating, reviews)               │
│    - DOM-first, Vision-fallback     │
└─────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│ 2. Product Attribute Extraction     │
│    - LLM extracts dimensions        │
│      (woodiness, citrus, florals)   │
│    - Maps to preference framework   │
└─────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│ 3. Preference Matching              │
│    - Load user's fragrance prefs    │
│    - Score each product alignment   │
│    - Combine with review quality    │
└─────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│ 4. Ranked Results                   │
│    - Budget options (≤$20)          │
│    - Premium suggestions ($20-40)   │
│    - Match reasons + warnings       │
└─────────────────────────────────────┘
```

**Test**: Run `test_personalized_search.py` → Products ranked by user's woodiness/citrus preferences

### A.2 Mesh UI (Split Screen)

| Status | Item | Description | Files | Test Criteria |
|--------|------|-------------|-------|---------------|
| ✅ | Mesh Protocol | Backend fully built | `services/mesh/` | Done |
| ✅ | Personal Mesh Demo Backend | Demo orchestrator for Your Sakhi ↔ Mom's Sakhi | `services/demo/coordination_demo.py` | Done |
| ✅ | Business Mesh Demo Backend | Demo orchestrator for Your Sakhi ↔ Restaurant Sakhi | `services/demo/coordination_demo.py` | Done |
| ✅ | Personal Mesh Demo UI | Split-screen web UI for personal coordination | `apps/web/app/demo/coordination/page.tsx` | Done |
| ✅ | Business Mesh Demo UI | Restaurant dashboard for business coordination | `apps/web/app/demo/restaurant/page.tsx` | Done |
| ✅ | Connection Animation | Enhanced visual mesh connection | `demo/components/MeshConnection.tsx` | SVG animation with data packets, glow effects |

**Test**: Demo page shows two Sakhis coordinating dinner in real-time.

### A.3 Personalization Engine

| Status | Item | Description | Files | Test Criteria |
|--------|------|-------------|-------|---------------|
| ✅ | Sensory Preferences | 8 categories: temperature, texture, spice, flavor, visual, ambiance, portion, service | `services/memory/sensory_preferences.py` | Done |
| ✅ | Preference Seeder | Demo data for sensory preferences | `services/demo/preference_seeder.py` | Done |
| ✅ | Preference Learning | Extract preferences from conversations | `services/memory/preference_learning.py` | Auto-learn from "I like..." statements |
| ✅ | Food Memory | Restaurant/dish history with ratings | `services/ayurveda/food_recommendations.py` | Comprehensive food knowledge base |
| ✅ | Product Matching | Score products against preferences | `services/memory/product_matching.py` | Score products against user preferences |
| ✅ | Dosha-Aware Food | Ayurveda + food recommendations | `services/ayurveda/food_recommendations.py` | Friction-state aware recommendations |

**Test**: "Find car perfume" → returns products matching stored scent preferences (woody, citrus, not floral).

### ✅ A.4 Reflective Intelligence Polish (COMPLETE)

| Status | Item | Description | Files | Test Criteria |
|--------|------|-------------|-------|---------------|
| ✅ | Causal Reasoning | "Why am I feeling X?" | `causal_reasoning.py` | Done |
| ✅ | Pattern Matching | Personal patterns + Ayurvedic knowledge | `pattern_learning.py` | Done |
| ✅ | Demo Data | Patterns, behaviors, episodes seeded | `services/demo/pattern_seeder.py` | Done |
| ✅ | Demo API | `/demo/run/reflection` endpoint | `routes/demo.py` | Done |
| ✅ | "Last Time" Lookup | Find similar episodes, what helped | `causal_reasoning.py` | Returns relevant past episode |
| ✅ | Intervention Tracking | Track what actually works for user | `services/learning/outcomes.py` | Stores intervention outcomes |

**Test**: "Why am I scattered?" → returns pattern + "last time, walks helped in 2 days."

### ✅ A.4.1 Intervention Plan Tracking (COMPLETE)

> **Why**: Long-term wellness interventions need recurring tracking. "Walk 20 min every alternate day for 2 weeks" requires scheduling, check-ins, nudges, and outcome correlation.

| Status | Item | Description | Files | Test Criteria |
|--------|------|-------------|-------|---------------|
| ✅ | Intervention Plans | Create multi-day routines with schedules | `services/learning/intervention_plans.py` | Plans created with daily/alternate/weekly schedules |
| ✅ | Check-in Tracking | Track daily completion with streaks | `services/learning/intervention_plans.py` | Streaks computed, adherence tracked |
| ✅ | Nudge System | Reminders, encouragements, missed alerts | `services/learning/nudges.py` | Generates appropriate nudges |
| ✅ | Outcome Correlation | Connect adherence to symptom improvement | `services/learning/intervention_plans.py` | Shows effectiveness after plan completion |
| ✅ | API Routes | Full CRUD + check-in endpoints | `routes/learning.py` | POST /learning/plan, /plan/checkin, etc. |

**Architecture**:
```
User: "I've been anxious, what should I do?"

Sakhi: "Try 20-min morning walks every other day"
       ┌─────────────────────────────────────┐
       │ 🎯 Track this routine               │
       │    I'll check in & track progress   │
       └─────────────────────────────────────┘
       [Track for 2 weeks]  [Just a suggestion]

User: clicks [Track for 2 weeks]
       │
       ▼
┌─────────────────────────────────────────────┐
│ intervention_plans                          │
│ ─────────────────                          │
│ schedule: alternate_days, 14 days          │
│ target_symptom: anxiety                     │
└─────────────────────────────────────────────┘
       │
       ▼ (Each scheduled day)
┌─────────────────────────────────────────────┐
│ Check-in Prompt                             │
│ "Did you do your morning walk today?"       │
│ [Yes ✅] [Not yet] [Skip]                   │
└─────────────────────────────────────────────┘
       │
       ▼ (Plan completes)
┌─────────────────────────────────────────────┐
│ Outcome Correlation                         │
│ Adherence: 71% (5/7 days)                  │
│ Anxiety reduced: -40%                       │
│ → "Morning walks work for you!"            │
└─────────────────────────────────────────────┘
```

**Test**: Create plan → Check in daily → See adherence rate → Get "this worked for you" insight

### ✅ A.5 Demo UI Framework (COMPLETE)

| Status | Item | Description | Files | Test Criteria |
|--------|------|-------------|-------|---------------|
| ✅ | Demo API Backend | All demo endpoints ready | `routes/demo.py`, `services/demo/` | Done |
| ✅ | Demo Launcher | Home page with all acts | `apps/web/app/demo/page.tsx` | All 4 acts accessible |
| ✅ | Act 1: Vision Loop UI | Vision loop with step-by-step visualization | `apps/web/app/demo/vision/page.tsx` | Shows vision loop in action |
| ✅ | Act 2: Personal Mesh UI | Split-screen Your Sakhi ↔ Mom's Sakhi | `apps/web/app/demo/coordination/page.tsx` | Coordination demo works |
| ✅ | Act 3: Business Mesh UI | Restaurant dashboard with guest profile | `apps/web/app/demo/restaurant/page.tsx` | Business coordination works |
| ✅ | Act 4: Reflection UI | Causal reasoning with dosha context | `apps/web/app/demo/reveal/page.tsx` | Shows reflective intelligence |

**Demo Access**: Navigate to `/demo` to access all 4 acts.

**Test**: All 4 acts run smoothly in sequence for investor demo.

### ✅ A.6 Mesh Communication (Real Inter-Sakhi) (COMPLETE)

> **Why**: Current mesh is simulated within one system. For REAL mesh, Sakhis must actually communicate across instances.

| Status | Item | Description | Files | Test Criteria |
|--------|------|-------------|-------|---------------|
| ✅ | Mesh Message API | POST /mesh/send - send message to another Sakhi | `services/mesh/inter_sakhi.py` | Message sent to external endpoint |
| ✅ | Mesh Webhook Receiver | POST /mesh/receive - receive from other Sakhi | `services/mesh/inter_sakhi.py` | Processes incoming coordination request |
| ✅ | Sakhi Discovery | Register/lookup Sakhi by entity ID or handle | `services/mesh/discovery.py` | Find Mom's Sakhi endpoint |
| ✅ | Mesh Auth | Verify sender identity via signed JWT tokens | `services/mesh/auth.py` | Only trusted Sakhis accepted |
| ✅ | Async Response Handling | Handle delayed responses (Sakhi offline) | `services/mesh/async_handler.py` | Queues message, delivers when online |

**Architecture**:
```
Your Sakhi                          Mom's Sakhi
    │                                    │
    ├─── POST /mesh/send ────────────────►
    │    {to: "mom-sakhi-id",            │
    │     type: "scheduling_request",    │
    │     payload: {...}}                │
    │                                    │
    ◄─── POST /mesh/receive ─────────────┤
         {from: "mom-sakhi-id",          │
          type: "scheduling_response",   │
          payload: {...}}                │
```

**Test**: Your Sakhi running on :8080 sends scheduling request to Mom's Sakhi on :8081 → response received.

### ✅ A.7 Learning Pipeline (Real Pattern Learning) (COMPLETE)

> **Why**: Current causal reasoning uses seeded demo data. For REAL intelligence, Sakhi must learn from actual user behavior.

| Status | Item | Description | Files | Test Criteria |
|--------|------|-------------|-------|---------------|
| ✅ | Behavior Logger | Auto-extract behaviors from conversations | `services/ayurveda/pattern_learning.py` | "I had coffee late" → behavior logged |
| ✅ | Symptom Logger | Track when user reports symptoms/states | `services/ayurveda/pattern_learning.py` | "Feeling scattered" → symptom logged |
| ✅ | Outcome Collector | Track symptom resolution after interventions | `services/learning/outcomes.py` | "Feeling better" → intervention marked effective |
| ✅ | Correlation Computer | Compute personal patterns from behavior→symptom data | `services/ayurveda/pattern_learning.py` | Updates personal_patterns with correlation scores |
| ✅ | Learning Trigger | Run correlation update after sufficient data | `services/learning/trigger.py` | Recomputes on threshold (10 behaviors / 5 symptoms) |

**Architecture**:
```
Conversation                    Learning Pipeline
    │                                │
    ├─ "I stayed up until 2am" ──────► behavior_log (type: sleep, late_night)
    │                                │
    ├─ "Feeling anxious today" ──────► symptom_log (type: anxiety)
    │                                │
    │         [3 days later]         │
    ├─ "Walks really help" ──────────► outcome_log (intervention: walk, effective: true)
    │                                │
    │         [Weekly job]           │
    │                                ▼
    │                    correlation_computer.run()
    │                                │
    │                    ┌───────────┴───────────┐
    │                    │ late_night → anxiety  │
    │                    │ correlation: 0.73     │
    │                    │ (personal pattern!)   │
    │                    └───────────────────────┘
```

**Test**: Log 10 behaviors + 5 symptoms over 2 weeks → "Why am I anxious?" returns YOUR learned patterns, not just Ayurvedic defaults.

### ✅ A.8 Preference Feedback Loop (COMPLETE)

> **Why**: Preferences should improve from implicit signals, not just explicit statements.

| Status | Item | Description | Files | Test Criteria |
|--------|------|-------------|-------|---------------|
| ✅ | Choice Logger | Track when user picks option A over B | `services/learning/choices.py` | Restaurant selection → logged with inferred reasons |
| ✅ | Recommendation Feedback | "Was this good?" or implicit (re-ordered, complained) | `services/learning/feedback.py` | Thumbs up/down, extract from text ("too spicy") |
| ✅ | Preference Updater | Adjust preference weights from feedback | `services/learning/preference_updater.py` | Preferences shift toward actual behavior |

**Test**: User says "This was too spicy" after recommendation → spice preference auto-adjusts down. ✅ VERIFIED

---

## PHASE B: Voice Interface (Week 3-4) - COMPLETE

### B.1 Speech-to-Text Input

| Status | Item | Description | Files | Test Criteria |
|--------|------|-------------|-------|---------------|
| ✅ | Whisper STT | OpenAI Whisper transcription | `apps/web/app/api/voice/turn/route.ts` | Audio → Whisper → text |
| ✅ | Voice Input UI | useVoice hook with recording | `apps/web/lib/hooks/useVoice.ts` | Visual feedback while recording |
| ✅ | Continuous Listening | Optional always-on mode in voice page | `apps/web/app/experience/voice/page.tsx` | Continuous mode with auto-restart |

**Test**: Say "What's my day look like?" → correctly transcribed and processed. ✅

### B.2 Text-to-Speech Output

| Status | Item | Description | Files | Test Criteria |
|--------|------|-------------|-------|---------------|
| ✅ | OpenAI TTS | High quality voice (nova) | `apps/web/app/api/voice/turn/route.ts` | Reads responses naturally |
| ✅ | TTS API | Standalone TTS endpoint | `apps/web/app/api/voice/tts/route.ts` | Text-to-speech on demand |
| ✅ | Voice Selection | Choose voice persona | `apps/web/components/VoiceSettings.tsx` | User can pick nova/shimmer/alloy voice |
| ⬜ | Streaming TTS | Start speaking before full response | `services/voice/stream.py` | < 1s latency to first audio (deferred) |

**Test**: Sakhi reads responses aloud with user-selected voice. ✅

### B.3 Voice Conversation Mode

| Status | Item | Description | Files | Test Criteria |
|--------|------|-------------|-------|---------------|
| ✅ | Voice Turn Pipeline | Audio → STT → Sakhi → TTS → Audio | `apps/web/app/api/voice/turn/route.ts` | Full pipeline implemented |
| ✅ | useVoice Hook | State machine: idle → recording → processing → speaking | `apps/web/lib/hooks/useVoice.ts` | States managed correctly |
| ✅ | Voice-First UI | Full-screen voice mode | `apps/web/app/experience/voice/page.tsx` | Clean interface for voice |
| ✅ | Interruption Handling | User can interrupt Sakhi | `apps/web/lib/hooks/useVoice.ts` | `interrupt()` stops speaking and starts listening |

**Test**: Voice conversation works end-to-end with voice selection and interruption. ✅

---

## PHASE C: Personal Dashboard (Week 5-6) — ✅ COMPLETE

### C.1 Unified Dashboard

| Status | Item | Description | Files | Test Criteria |
|--------|------|-------------|-------|---------------|
| ✅ | Dashboard Page | Glanceable overview | `apps/web/app/experience/dashboard/page.tsx` | All key info visible at once |
| ✅ | Today Section | Calendar + tasks + energy | Integrated in dashboard page | Shows day at a glance |
| ✅ | Relationships Section | People to connect with | Integrated in dashboard page | Shows who needs attention |
| ✅ | Energy/State Section | Current dosha, operating mode | Integrated in dashboard page | Shows current state |

**Test**: Open dashboard → see today's events, tasks, energy, relationship nudges in < 3s. ✅

### C.2 Widget System

| Status | Item | Description | Files | Test Criteria |
|--------|------|-------------|-------|---------------|
| ✅ | Widget Framework | Pluggable widget architecture | `apps/web/app/experience/dashboard/page.tsx` (WidgetCard) | Easy to add new widgets |
| ✅ | Calendar Widget | Upcoming events | Integrated in dashboard page (CalendarWidget) | Shows next 3-5 events |
| ⬜ | Tasks Widget | Today's tasks | Deferred - requires task system | Shows pending tasks |
| ✅ | Energy Widget | Current state visualization | Integrated in dashboard page (EnergyWidget) | Visual energy indicator |
| ✅ | Relationships Widget | Connection reminders | Integrated in dashboard page (RelationshipsWidget) | Who to reach out to |

**Test**: All widgets load and update independently. ✅

### C.3 Customization

| Status | Item | Description | Files | Test Criteria |
|--------|------|-------------|-------|---------------|
| ⬜ | Widget Arrangement | Drag-and-drop layout | Deferred - using static order for now | User can rearrange |
| ✅ | Widget Toggle | Show/hide widgets | `apps/web/app/experience/dashboard/page.tsx` (SettingsPanel) | User controls what shows |
| ⬜ | Theme Options | Light/dark/custom | Deferred - dark mode only for now | Respects user preference |
| ✅ | Layout Persistence | Save arrangement | localStorage (sakhi_dashboard_config) | Remembers layout |

**Test**: Toggle widgets → refresh → configuration persists. ✅

### API Routes Created
- `apps/web/app/api/calendar/[personId]/today/route.ts` - Today's events
- `apps/web/app/api/calendar/[personId]/events/route.ts` - Upcoming events
- `apps/web/app/api/friction/state/friction/[personId]/route.ts` - Friction state
- `apps/web/app/api/relationships/[personId]/needing-attention/route.ts` - Relationships needing attention

---

## 🎯 PHASE M: MOBILE APPS — TOP PRIORITY

> **Why Now**: Web foundation complete (Voice, Dashboard, Ayurvedic intelligence). Time to put Sakhi in users' pockets. Focus on reflective, ayurvedic intelligence as the core differentiator.

### Development Approach

1. **Design Phase**: Use v0.dev or similar to rapidly prototype UI screens
2. **Build Phase**: Port designs to React Native (Expo) in `apps/mobile/`
3. **Integration**: Connect to existing FastAPI backend (same APIs as web)
4. **Launch**: iOS App Store + Android Play Store

### M.1 Project Setup

| Status | Item | Description | Files | Test Criteria |
|--------|------|-------------|-------|---------------|
| ⬜ | Expo Init | Initialize React Native + Expo project | `apps/mobile/` | `npx expo start` works |
| ⬜ | Navigation | React Navigation setup | `apps/mobile/navigation/` | Tab + stack navigation |
| ⬜ | Theming | Dark mode, brand colors | `apps/mobile/theme/` | Consistent with web |
| ⬜ | API Client | Shared API calls | `apps/mobile/lib/api.ts` | Auth + endpoints work |
| ⬜ | Auth Flow | Login/signup screens | `apps/mobile/screens/auth/` | User can authenticate |

**Test**: App launches, user can log in, sees home screen.

### M.2 Core Screens

| Status | Item | Description | Files | Test Criteria |
|--------|------|-------------|-------|---------------|
| ⬜ | Home/Dashboard | Glanceable today view | `apps/mobile/screens/Home.tsx` | Shows energy, events, nudges |
| ⬜ | Voice Conversation | Voice-first chat with Sakhi | `apps/mobile/screens/Voice.tsx` | Push-to-talk + auto-listen |
| ⬜ | Text Conversation | Text chat fallback | `apps/mobile/screens/Chat.tsx` | Standard messaging UI |
| ⬜ | Reflection/Journal | Daily check-in | `apps/mobile/screens/Reflection.tsx` | Quick mood + energy entry |
| ⬜ | Profile/Settings | User preferences | `apps/mobile/screens/Settings.tsx` | Voice, notifications, etc. |

**Test**: User can navigate all core screens, voice conversation works.

### M.3 Ayurvedic Intelligence UI

| Status | Item | Description | Files | Test Criteria |
|--------|------|-------------|-------|---------------|
| ⬜ | Dosha State Display | Current Vata/Pitta/Kapha state | `apps/mobile/components/DoshaState.tsx` | Visual indicator of imbalance |
| ⬜ | Friction State | Chaos/Intensity/Stagnation view | `apps/mobile/components/FrictionState.tsx` | Shows current state + drift |
| ⬜ | Recommendations | Personalized suggestions | `apps/mobile/components/Recommendations.tsx` | Food, activity, rest suggestions |
| ✅ | Onboarding API | Phased onboarding endpoint | `sakhi/apps/api/routes/friction_framework.py` | `POST /onboarding/submit` with phase1/2a/2b/full |
| ⬜ | Onboarding Flow | Prakruti assessment UI | `apps/mobile/screens/Onboarding.tsx` | 10-15 questions → constitution |
| ⬜ | Energy Timeline | Daily energy pattern | `apps/mobile/components/EnergyTimeline.tsx` | Circadian rhythm awareness |

**Test**: User completes onboarding → sees personalized dosha state → gets relevant recommendations.

### M.4 Voice Features (Mobile-specific)

| Status | Item | Description | Files | Test Criteria |
|--------|------|-------------|-------|---------------|
| ⬜ | Native Recording | expo-av audio recording | `apps/mobile/lib/audio.ts` | High-quality audio capture |
| ⬜ | Push-to-Talk | Hold button to speak | `apps/mobile/components/VoiceButton.tsx` | Intuitive UX |
| ⬜ | Background Audio | TTS plays in background | `apps/mobile/lib/audio.ts` | User can listen while multitasking |
| ⬜ | Wake Word (stretch) | "Hey Sakhi" activation | Future | Hands-free activation |

**Test**: Record voice → get Sakhi response → hear TTS playback.

### M.5 App Store Submission

| Status | Item | Description | Files | Test Criteria |
|--------|------|-------------|-------|---------------|
| ⬜ | iOS Build | EAS Build for iOS | `apps/mobile/eas.json` | IPA builds successfully |
| ⬜ | Android Build | EAS Build for Android | `apps/mobile/eas.json` | APK/AAB builds successfully |
| ⬜ | App Icons | iOS + Android icons | `apps/mobile/assets/` | All sizes generated |
| ⬜ | Screenshots | Store listing screenshots | `docs/mobile/screenshots/` | 5-8 screens per platform |
| ⬜ | App Store Connect | iOS submission | Apple Developer account | App approved |
| ⬜ | Play Console | Android submission | Google Play account | App approved |

**Test**: Apps available in stores, users can download and use.

### Key Screens to Design (v0.dev or Figma)

1. **Voice Conversation Screen**
   - Large voice orb (like web `/experience/voice`)
   - Transcript display
   - State indicators (listening, processing, speaking)

2. **Home Dashboard**
   - Greeting + date
   - Energy/dosha state card
   - Today's events (compact)
   - Quick action buttons

3. **Reflection/Check-in**
   - "How are you feeling?" prompt
   - Energy slider
   - Quick mood tags
   - Optional journal entry

4. **Onboarding/Prakruti Assessment**
   - Question cards (swipe or tap)
   - Progress indicator
   - Results screen with dosha breakdown

5. **Settings**
   - Voice selection
   - Notification preferences
   - Account management

---

## PHASE D: Proactive Intelligence (After Mobile Launch)

### D.1 Morning Briefing

| Status | Item | Description | Files | Test Criteria |
|--------|------|-------------|-------|---------------|
| ⬜ | Briefing Generator | Compile daily briefing | `services/briefing/morning.py` | Includes calendar, tasks, energy, nudges |
| ⬜ | Briefing API | GET /api/briefing/morning | `routes/briefing.py` | Returns structured briefing |
| ⬜ | Briefing UI | Morning briefing view | `apps/web/app/experience/briefing/page.tsx` | Beautiful morning view |
| ⬜ | Voice Delivery | Read briefing aloud | Integrates with Phase B | Sakhi speaks briefing |
| ⬜ | Timing Logic | Deliver at user's preferred time | `services/briefing/scheduler.py` | Respects user schedule |

**Test**: At 7am, Sakhi delivers: "Good morning. You have 3 meetings, Alex's birthday is tomorrow, your Vata is elevated - consider grounding practices."

### D.2 Relationship Nudges

| Status | Item | Description | Files | Test Criteria |
|--------|------|-------------|-------|---------------|
| ⬜ | Nudge Detection | Identify who needs attention | `services/relationships/nudges.py` | Finds neglected connections |
| ⬜ | Nudge Generation | Natural language nudge | `services/relationships/nudges.py` | "You haven't talked to Mom in 2 weeks" |
| ⬜ | Nudge Timing | When to surface nudge | `services/relationships/scheduler.py` | Non-intrusive timing |
| ⬜ | Action Options | "Call", "Message", "Schedule time" | `apps/web/components/nudges/Actions.tsx` | Easy to act on nudge |

**Test**: After 2 weeks without contact, see nudge: "You haven't connected with [person] - want to reach out?"

### D.3 Birthday/Anniversary Tracking

| Status | Item | Description | Files | Test Criteria |
|--------|------|-------------|-------|---------------|
| ⬜ | Important Dates Storage | Store birthdays, anniversaries | `services/relationships/dates.py` | CRUD for important dates |
| ⬜ | Date Extraction | Extract from conversations | `services/relationships/extraction.py` | "My mom's birthday is March 15" → stored |
| ⬜ | Reminders | Remind ahead of time | `services/relationships/reminders.py` | 1 week, 1 day before |
| ⬜ | Gift Suggestions | Based on relationship context | `services/relationships/gifts.py` | Personalized suggestions |

**Test**: Add birthday → get reminder 1 week before with gift suggestions.

### D.4 Focus Protection

| Status | Item | Description | Files | Test Criteria |
|--------|------|-------------|-------|---------------|
| ⬜ | Focus Mode | Do-not-disturb state | `services/focus/mode.py` | Suppress non-urgent notifications |
| ⬜ | Focus Scheduling | Auto-enable during calendar blocks | `services/focus/scheduler.py` | Integrates with calendar |
| ⬜ | Urgency Classification | Filter interruptions by urgency | `services/focus/filter.py` | Only critical gets through |
| ⬜ | Focus UI | Indicator + quick toggle | `apps/web/components/focus/` | Easy to enable/disable |

**Test**: Enable focus mode → only CRITICAL notifications get through.

---

## PHASE E: Bridge Skills (Week 9-10)

### E.1 Google Calendar Sync

| Status | Item | Description | Files | Test Criteria |
|--------|------|-------------|-------|---------------|
| ⬜ | OAuth Flow | Google OAuth consent | `services/integrations/google/oauth.py` | User can authorize |
| ⬜ | Calendar Import | Pull events from Google | `services/integrations/google/calendar.py` | Events sync to Sakhi |
| ⬜ | Calendar Export | Push Sakhi events to Google | `services/integrations/google/calendar.py` | Bidirectional sync |
| ⬜ | Conflict Detection | Handle overlapping events | `services/calendar/conflicts.py` | Warns on conflicts |

**Test**: Connect Google Calendar → see events in Sakhi → create event in Sakhi → appears in Google.

### E.2 Apple Calendar Sync

| Status | Item | Description | Files | Test Criteria |
|--------|------|-------------|-------|---------------|
| ⬜ | iCal Import | Import .ics files | `services/integrations/apple/ical.py` | One-time import works |
| ⬜ | CalDAV Sync | Real-time sync via CalDAV | `services/integrations/apple/caldav.py` | Bidirectional sync |
| ⬜ | Desktop Integration | Shortcuts/AppleScript bridge | `services/integrations/apple/shortcuts.py` | macOS integration |

**Test**: Import iCal file → events appear in Sakhi calendar.

### E.3 Gmail Bridge

| Status | Item | Description | Files | Test Criteria |
|--------|------|-------------|-------|---------------|
| ⬜ | Gmail OAuth | Google OAuth for Gmail | `services/integrations/google/gmail_oauth.py` | User can authorize |
| ⬜ | Email Read | Fetch and display emails | `services/integrations/google/gmail_read.py` | Show inbox in Sakhi |
| ⬜ | Email Send | Send via user's Gmail | `services/integrations/google/gmail_send.py` | Compose and send |
| ⬜ | Email Summarization | AI summary of long emails | `services/integrations/google/gmail_summary.py` | Quick email digests |

**Test**: Connect Gmail → see inbox summary → send reply via Sakhi.

---

## PHASE F: Data Sovereignty (Week 11-12)

### F.1 Data Export

| Status | Item | Description | Files | Test Criteria |
|--------|------|-------------|-------|---------------|
| ⬜ | Full Export | Export all user data | `services/export/full.py` | JSON/ZIP download |
| ⬜ | Selective Export | Export specific data types | `services/export/selective.py` | Choose what to export |
| ⬜ | Export Format | Standard, portable format | `services/export/formats.py` | JSON, CSV, ICS options |
| ⬜ | Export UI | Easy export flow | `apps/web/app/settings/export/page.tsx` | One-click export |

**Test**: Click "Export All" → download ZIP with all data in readable format.

### F.2 Privacy Controls

| Status | Item | Description | Files | Test Criteria |
|--------|------|-------------|-------|---------------|
| ⬜ | Privacy Dashboard | See what data Sakhi has | `apps/web/app/settings/privacy/page.tsx` | Full transparency |
| ⬜ | Data Deletion | Delete specific data | `services/privacy/delete.py` | Permanent deletion |
| ⬜ | Sharing Controls | Control what's shared in Mesh | `services/privacy/sharing.py` | Granular controls |
| ⬜ | Retention Settings | How long data is kept | `services/privacy/retention.py` | User sets retention |

**Test**: View privacy dashboard → delete a memory → confirm it's gone.

### F.3 Self-Hosting Documentation

| Status | Item | Description | Files | Test Criteria |
|--------|------|-------------|-------|---------------|
| ⬜ | Docker Compose | Easy self-host setup | `docker-compose.yml` | `docker-compose up` works |
| ⬜ | Self-Host Guide | Step-by-step documentation | `docs/SELF_HOSTING.md` | Complete instructions |
| ⬜ | Environment Config | All configurable via env | `.env.example` | Clear env documentation |
| ⬜ | Data Migration | Move data between instances | `scripts/migrate.py` | Export → import flow |

**Test**: Follow self-hosting guide → Sakhi running on own server.

---

## PHASE G: Mobile (Week 13+)

> Build web + API first, then convert to mobile.

> **See also**: [LONG_RUNNING_TASKS.md](./LONG_RUNNING_TASKS.md) for detailed architecture of Life Missions system.

### G.1 PWA Conversion

| Status | Item | Description | Files | Test Criteria |
|--------|------|-------------|-------|---------------|
| ⬜ | Service Worker | Offline caching | `apps/web/public/sw.js` | App works offline |
| ⬜ | Web Manifest | Install prompt | `apps/web/public/manifest.json` | "Add to Home Screen" works |
| ⬜ | Responsive Polish | Mobile-optimized layouts | All components | Works on 375px width |
| ⬜ | Touch Optimization | Touch-friendly interactions | All components | No tiny tap targets |

**Test**: Install PWA on iPhone → use full Sakhi experience.

### G.2 Push Notifications

| Status | Item | Description | Files | Test Criteria |
|--------|------|-------------|-------|---------------|
| ⬜ | Push Registration | Register for push | `apps/web/lib/push/register.ts` | Browser asks for permission |
| ⬜ | Push Backend | Send push notifications | `services/notifications/push.py` | Notifications delivered |
| ⬜ | Notification Types | Different notification categories | `services/notifications/types.py` | Briefing, nudges, urgent |
| ⬜ | Notification Settings | User controls what notifies | `apps/web/app/settings/notifications/` | Granular controls |

**Test**: Enable push → receive morning briefing notification.

### G.3 Offline Support

| Status | Item | Description | Files | Test Criteria |
|--------|------|-------------|-------|---------------|
| ⬜ | Offline Data | Cache essential data locally | `apps/web/lib/offline/cache.ts` | Calendar, tasks available offline |
| ⬜ | Offline Actions | Queue actions when offline | `apps/web/lib/offline/queue.ts` | Actions sync when online |
| ⬜ | Sync Indicator | Show sync status | `apps/web/components/SyncStatus.tsx` | User knows when offline |
| ⬜ | Conflict Resolution | Handle sync conflicts | `services/sync/conflicts.py` | Graceful conflict handling |

**Test**: Go offline → view calendar → add event → go online → event syncs.

---

## PHASE H: Long-Running Tasks - Life Missions (Week 14-16)

> **Why**: Sakhi should handle autonomous tasks that span weeks or months — building a personal brand on Twitter, training for a marathon, learning a new skill. These require planning, scheduled execution, progress tracking, adaptation, and human approval gates.

> **Architecture**: See [LONG_RUNNING_TASKS.md](./LONG_RUNNING_TASKS.md) for full technical specification.

### H.1 Mission Orchestrator

| Status | Item | Description | Files | Test Criteria |
|--------|------|-------------|-------|---------------|
| ⬜ | Mission Data Model | 5-table hierarchy: missions → phases → weekly_plans → actions → checkpoints | `migrations/00XX_missions.sql` | Tables created with proper FKs |
| ⬜ | Mission CRUD API | Create, read, update missions with phases | `routes/missions.py` | Full CRUD + phase management |
| ⬜ | Mission Decomposition | LLM breaks mission into phases → weeks → actions | `services/missions/decomposer.py` | "Build Twitter brand" → 12-week plan |
| ⬜ | Human Approval Gates | Require approval before major phase transitions | `services/missions/approvals.py` | User confirms before phase 2 starts |
| ⬜ | Mission Health Tracker | Compute on_track / at_risk / blocked status | `services/missions/health.py` | Shows mission health dashboard |

**Task Hierarchy**:
```
Mission (months)
├── Phase (weeks) ← Human approval gate between phases
│   ├── Weekly Plan (7 days)
│   │   ├── Daily Action (scheduled)
│   │   │   └── Atomic Operation (vision loop)
│   │   └── Daily Action
│   └── Weekly Plan
└── Phase
```

**Test**: Create "Build Personal Brand on Twitter" mission → see 12-week plan with phases, approval gates, and daily actions.

### H.2 Scheduling System

| Status | Item | Description | Files | Test Criteria |
|--------|------|-------------|-------|---------------|
| ⬜ | Action Scheduler | Schedule actions at specific times/days | `services/missions/scheduler.py` | "Post tweet at 9am daily" scheduled |
| ⬜ | RQ Job Bridge | Bridge scheduled_actions → RQ for execution | `services/missions/rq_bridge.py` | Actions enqueue when due |
| ⬜ | Trigger Types | Time-based, condition-based, event-based triggers | `services/missions/triggers.py` | Multiple trigger strategies |
| ⬜ | Cron Worker | Hourly check for due actions | `workers/mission_cron.py` | Runs every hour, enqueues due tasks |
| ⬜ | Missed Action Handler | Detect and handle missed scheduled actions | `services/missions/missed.py` | Alerts user, offers reschedule |

**Scheduling Architecture**:
```
┌─────────────────────────────────────────────────────────────┐
│ scheduled_actions table                                      │
│ ─────────────────────                                        │
│ mission_id, action_type, scheduled_date, scheduled_time     │
│ trigger_type: daily_9am | weekly_monday | condition_based   │
│ status: scheduled | queued | executing | completed | failed │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ Cron Worker (hourly)                                         │
│ ─────────────────────                                        │
│ 1. Query due actions (scheduled_time <= NOW + 1hr)          │
│ 2. Enqueue to RQ with mission context                       │
│ 3. Mark as "queued"                                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ RQ Worker                                                    │
│ ─────────────────────                                        │
│ Execute action (browser automation, API call, notification) │
│ Record outcome → checkpoint                                  │
│ Update mission progress                                      │
└─────────────────────────────────────────────────────────────┘
```

**Test**: Schedule daily tweet → action executes at 9am → outcome recorded.

### H.3 Adaptation Engine

| Status | Item | Description | Files | Test Criteria |
|--------|------|-------------|-------|---------------|
| ⬜ | Weekly Review | Auto-generate weekly progress report | `services/missions/review.py` | Summary of week's actions + outcomes |
| ⬜ | Outcome Correlation | Measure what's working vs not | `services/missions/correlation.py` | "Thread tweets get 3x engagement" |
| ⬜ | Plan Adjustment | LLM suggests plan modifications | `services/missions/adapter.py` | "Shift to more threads, fewer polls" |
| ⬜ | Checkpoint Storage | Store progress snapshots | `services/missions/checkpoints.py` | Weekly state snapshots |
| ⬜ | Human Review Prompt | Surface insights for user approval | `services/missions/human_review.py` | "Week 4: Here's what's working..." |

**Adaptation Loop**:
```
Week N Executes
      │
      ▼
Review Outcomes (auto)
      │
      ├─── What worked? (high engagement)
      ├─── What didn't? (low engagement)
      └─── External changes? (algorithm shift)
      │
      ▼
Learn & Adjust (LLM)
      │
      ├─── Keep: morning posts
      ├─── Drop: poll tweets
      └─── Try: thread format
      │
      ▼
Update Plan for Week N+1
      │
      ▼
Human Review Gate (optional)
      │
      ▼
Continue to Week N+1
```

**Test**: After 4 weeks, adaptation engine recommends "more threads, fewer polls" based on engagement data.

### H.4 Metrics & Progress

| Status | Item | Description | Files | Test Criteria |
|--------|------|-------------|-------|---------------|
| ⬜ | Metrics Collector | Collect mission-specific metrics | `services/missions/metrics.py` | Twitter: followers, engagement, impressions |
| ⬜ | Progress Calculator | Compute % complete toward goal | `services/missions/progress.py` | "Goal: 1000 followers, Current: 450 = 45%" |
| ⬜ | Milestone Detection | Detect and celebrate milestones | `services/missions/milestones.py` | "You hit 500 followers!" notification |
| ⬜ | Trend Analysis | Show progress trajectory | `services/missions/trends.py` | "At this rate, you'll hit goal in 6 weeks" |

**Test**: Mission shows 45% progress toward 1000 followers, predicts completion date.

---

## PHASE I: Life Dashboard - Unified Goals & Missions (Week 17-18)

> **Why**: Users currently have intervention plans (health goals) in one place and would have life missions in another. The Life Dashboard unifies everything into a single coherent experience where users can see their daily focus, track health goals, monitor life missions, and get Sakhi's insights.

### I.1 Unified Data Model

| Status | Item | Description | Files | Test Criteria |
|--------|------|-------------|-------|---------------|
| ⬜ | LifeGoal Model | Unified model for health goals + life missions | `services/life/models.py` | Single model handles both types |
| ⬜ | Goal Categorization | Health, Career, Relationships, Learning, Creative | `services/life/categories.py` | Goals organized by life domain |
| ⬜ | Daily Action Aggregator | Combine today's actions from all goals/missions | `services/life/daily.py` | Single list of today's focus items |
| ⬜ | Progress Unification | Unified progress tracking across goal types | `services/life/progress.py` | Same progress UI for health + missions |

**Unified Goal Model**:
```python
class LifeGoal:
    id: UUID
    person_id: UUID
    type: "health" | "mission"  # Health = intervention plan, Mission = long-running task
    category: "health" | "career" | "relationships" | "learning" | "creative"
    title: str
    description: str
    target_date: Optional[date]
    success_criteria: dict
    current_progress: int  # 0-100
    status: "active" | "paused" | "completed" | "archived"
    health: "thriving" | "on_track" | "needs_attention" | "at_risk"

    # Health-specific (intervention plan)
    schedule: Optional[str]  # "daily", "alternate_days", "weekly"
    target_symptom: Optional[str]

    # Mission-specific (long-running task)
    phases: Optional[List[Phase]]
    current_phase: Optional[int]
```

### I.2 Life Dashboard UI

| Status | Item | Description | Files | Test Criteria |
|--------|------|-------------|-------|---------------|
| ⬜ | Dashboard Page | Main Life Dashboard at `/experience/life` | `apps/web/app/experience/life/page.tsx` | Unified view loads |
| ⬜ | Today's Focus Section | What to focus on today across all goals | `apps/web/components/life/TodayFocus.tsx` | Shows prioritized daily actions |
| ⬜ | Health Goals Section | Active health interventions with check-ins | `apps/web/components/life/HealthGoals.tsx` | Progress, streaks, next check-in |
| ⬜ | Life Missions Section | Active missions with phase progress | `apps/web/components/life/LifeMissions.tsx` | Phase indicator, health status |
| ⬜ | Sakhi Insights Section | AI-generated observations and suggestions | `apps/web/components/life/SakhiInsights.tsx` | Patterns, correlations, nudges |

**Dashboard Layout**:
```
┌─────────────────────────────────────────────────────────────────┐
│ Life Dashboard                                      [+ New Goal] │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│ 📍 TODAY'S FOCUS                                                │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ □ Morning walk (20 min) ← from Health: Reduce Anxiety       │ │
│ │ □ Post Twitter thread ← from Mission: Personal Brand        │ │
│ │ □ Evening journal ← from Health: Sleep Quality              │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
│ 💚 HEALTH GOALS                                    [View All →] │
│ ┌──────────────────────┐ ┌──────────────────────┐               │
│ │ Reduce Anxiety       │ │ Better Sleep         │               │
│ │ ████████░░ 78%       │ │ █████░░░░░ 45%       │               │
│ │ 🔥 12-day streak     │ │ ⚠️ Missed yesterday   │               │
│ │ Next: Evening walk   │ │ Next: Journal tonight│               │
│ └──────────────────────┘ └──────────────────────┘               │
│                                                                  │
│ 🚀 LIFE MISSIONS                                   [View All →] │
│ ┌──────────────────────┐ ┌──────────────────────┐               │
│ │ Personal Brand       │ │ Learn Piano          │               │
│ │ Phase 2 of 4         │ │ Phase 1 of 3         │               │
│ │ ████░░░░░░ 35%       │ │ ██░░░░░░░░ 15%       │               │
│ │ 📈 On Track          │ │ ⚠️ Needs Attention    │               │
│ │ 450/1000 followers   │ │ 3/20 lessons done    │               │
│ └──────────────────────┘ └──────────────────────┘               │
│                                                                  │
│ 💡 SAKHI INSIGHTS                                               │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ "Your anxiety levels drop 40% on days you complete your     │ │
│ │  morning walk. You've been consistent for 12 days — this    │ │
│ │  is becoming a real habit!"                                 │ │
│ │                                                             │ │
│ │ "Your Twitter threads get 3x more engagement than single    │ │
│ │  tweets. Consider shifting more content to thread format."  │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### I.3 Sub-Pages

| Status | Item | Description | Files | Test Criteria |
|--------|------|-------------|-------|---------------|
| ⬜ | Today Page | Full daily view at `/experience/life/today` | `apps/web/app/experience/life/today/page.tsx` | Expanded today view |
| ⬜ | Goals Page | All health goals at `/experience/life/goals` | `apps/web/app/experience/life/goals/page.tsx` | Full goals management |
| ⬜ | Missions Page | All missions at `/experience/life/missions` | `apps/web/app/experience/life/missions/page.tsx` | Full missions management |
| ⬜ | Insights Page | Historical insights at `/experience/life/insights` | `apps/web/app/experience/life/insights/page.tsx` | Patterns, trends, correlations |
| ⬜ | Goal Detail Page | Single goal detail at `/experience/life/goal/[id]` | `apps/web/app/experience/life/goal/[id]/page.tsx` | Full goal detail + history |
| ⬜ | Mission Detail Page | Single mission detail at `/experience/life/mission/[id]` | `apps/web/app/experience/life/mission/[id]/page.tsx` | Phases, actions, metrics |

**Information Architecture**:
```
/experience/life
├── /today          ← Today's Focus (expanded)
├── /goals          ← Health Goals (intervention plans)
├── /missions       ← Life Missions (long-running tasks)
├── /insights       ← Sakhi's observations & patterns
├── /goal/[id]      ← Single goal detail
└── /mission/[id]   ← Single mission detail with phases
```

### I.4 Check-in & Tracking UI

| Status | Item | Description | Files | Test Criteria |
|--------|------|-------------|-------|---------------|
| ⬜ | Daily Check-in Modal | Quick check-in for all today's items | `apps/web/components/life/DailyCheckin.tsx` | Batch complete daily actions |
| ⬜ | Quick Action Buttons | One-tap complete/skip/reschedule | `apps/web/components/life/QuickActions.tsx` | Fast interaction |
| ⬜ | Streak Visualization | Show streaks with celebration | `apps/web/components/life/Streaks.tsx` | Gamification elements |
| ⬜ | Progress Charts | Visual progress over time | `apps/web/components/life/ProgressChart.tsx` | Line/bar charts for goals |

**Test**: Open Life Dashboard → see today's focus → check off items → see streaks update → view insights.

---

## Priority Summary Update (Phases H-I)

### Week 14-16: Long-Running Tasks (Life Missions)
| Task | Test |
|------|------|
| Mission data model | 5 tables created with proper relationships |
| Mission decomposition | "Build Twitter brand" → phases + weeks + actions |
| Action scheduler | Daily tweet scheduled and executed |
| Adaptation engine | Week 4 recommendations based on outcomes |
| Metrics collection | Follower count, engagement tracked |

### Week 17-18: Life Dashboard
| Task | Test |
|------|------|
| Unified LifeGoal model | Health goals + missions in same model |
| Dashboard UI | Today's focus shows items from both types |
| Goal/Mission cards | Progress, health, next action visible |
| Sakhi Insights | Correlations surfaced automatically |
| Check-in flow | Quick complete/skip actions |

---

## Production Readiness (Ongoing)

| Status | Item | Description | Files | Test Criteria |
|--------|------|-------------|-------|---------------|
| ⬜ | Health Endpoints | `/health` with component status | `routes/health.py` | All components report status |
| ⬜ | Diagnostics | Debug endpoint | `routes/diagnostics.py` | System state visible |
| ⬜ | Error Monitoring | Sentry or similar | `apps/api/core/monitoring.py` | Errors tracked |
| ⬜ | Performance Metrics | Response times, token usage | `apps/api/core/metrics.py` | Metrics collected |
| ⬜ | Windows Agent | Electron agent for Windows | `desktop-agent/` | Works on Windows |

---

## Priority Summary

### Week 1-2: Demo Build (CURRENT)
| Day | Task | Test |
|-----|------|------|
| ✅ DONE | **🎯 Generate Diya Simulation Data** | 30 days, 56 entries, 31 snapshots in `hormonal_harmony.json` |
| ✅ DONE | **🎯 Simulation Personalization Demo** | Maya vs Diya comparison ready at `/lab/simulation` |
| ✅ DONE | **🎯 LLM Recommendation API** | Real GPT-4o-mini powered advice, not hardcoded |
| ✅ DONE | **🎯 Conversation LLM Reasoning** | Verified reasoning flows through chat, not just simulation |
| ✅ DONE | **User Experience Gap (A.0.2)** | Reasoning, memories, state changes now visible in chat UI |
| ✅ DONE | **Hybrid Search** | BM25 + vector merge in `bm25.py` + `recall.py` |
| ✅ DONE | **Vision Loop (A.1)** | Claude Vision via OpenRouter, image compression, proper message format |
| ✅ DONE | **Screen analyzer + action decider** | Claude 3.5 Sonnet for vision, Haiku for decisions |
| ✅ DONE | **Browser Automation (A.1.1)** | Playwright with DOM-first, Vision-fallback - Car perfume search tested $0 cost |
| ✅ DONE | **Preference engine (A.3)** | Extensible framework with 8 domains + product matching |
| ✅ DONE | **Integration testing** | Browser automation + preference engine connected via `personalized_search.py` |
| ✅ DONE | Split-screen demo UI | Personal mesh demo works at `/demo/coordination` |
| ✅ DONE | Restaurant Sakhi dashboard | Business mesh demo works at `/demo/restaurant` |
| ✅ DONE | Reflective polish | "Last time" lookup works |
| ⬜ | End-to-end demo | All 4 acts run smoothly in sequence |
| ✅ DONE | Mesh Communication (A.6) | Discovery, Auth, Async handling complete |
| ✅ DONE | Learning Pipeline (A.7) | Behaviors auto-extracted, patterns detected |
| ✅ DONE | Preference Feedback (A.8) | Recommendations improve from implicit signals |

### Week 3-4: Voice Interface
| Task | Test |
|------|------|
| Speech-to-Text | "What's my day?" transcribed correctly |
| Text-to-Speech | Briefing read aloud naturally |
| Voice conversation | 5-minute back-and-forth dialogue |

### Week 5-6: Personal Dashboard
| Task | Test |
|------|------|
| Unified dashboard | All info visible at glance |
| Widget system | Widgets load independently |
| Customization | Layout persists after refresh |

### Week 7-8: Proactive Intelligence
| Task | Test |
|------|------|
| Morning briefing | Delivered at user's time with full context |
| Relationship nudges | Surfaces neglected connections |
| Birthday tracking | Reminds 1 week before |
| Focus protection | Blocks non-urgent during focus |

### Week 9-10: Bridge Skills
| Task | Test |
|------|------|
| Google Calendar | Bidirectional sync works |
| Apple Calendar | iCal import works |
| Gmail | Read and send works |

### Week 11-12: Data Sovereignty
| Task | Test |
|------|------|
| Data export | Full export downloads |
| Privacy controls | Delete data, confirm gone |
| Self-hosting | `docker-compose up` works |

### Week 13+: Mobile
| Task | Test |
|------|------|
| PWA | Install on iPhone works |
| Push notifications | Morning briefing delivered |
| Offline | View calendar offline |

---

## Architecture Decisions

### Web + API First, Mobile Last

```
Phase 1-6: Build everything on Web + API
    ├── All features work in browser
    ├── API is the source of truth
    └── UI is responsive but web-first

Phase 7: Convert to Mobile
    ├── PWA wraps existing web
    ├── Add push notifications
    ├── Add offline support
    └── Optional: native apps later
```

### Bridge then Native Strategy

```
User starts → Uses existing tools (Google Cal, Gmail, etc.)
            ↓
        Sakhi bridges sync bidirectionally
            ↓
        User gradually migrates data to Sakhi native
            ↓
User ends up → All data lives in Sakhi ecosystem
```

### Task Execution Parity (vs OpenClaw)

| Feature | OpenClaw | Sakhi | Status |
|---------|----------|-------|--------|
| Error Classification | ✅ | ✅ | At par |
| Retry Logic | 5-layer | 3-layer | Functional |
| Timeout Clamping | ✅ | ✅ | At par |
| Session Locking | File-based | PostgreSQL | Better |
| State Persistence | JSON files | PostgreSQL | Better |

---

## Success Metrics

### Demo Success (Phase A)

| Capability | Success Metric |
|------------|----------------|
| Computer Use | Browse Amazon, find product, < 10 iterations |
| Mesh (Personal) | Split screen shows coordination in real-time |
| Mesh (Business) | Restaurant sees guest preferences |
| Personalization | "That's so me" feeling |
| Reflective | "Last time" finds relevant episode |
| **Personalization Demo** | Maya vs Diya: same symptom, opposite advice — investor says "I get it now" ✅ VERIFIED |
| **LLM in Conversation** | Reasoning appears in chat, not just simulation page ✅ VERIFIED |
| **Mesh (REAL)** | Two Sakhis on :8080 and :8081 exchange scheduling request |
| **Learning (REAL)** | "Why am I anxious?" returns patterns learned from YOUR logged behaviors |
| **Feedback (REAL)** | "Too spicy" → spice preference auto-adjusts without explicit command |
| **UX Gap Closed** | User in chat sees their state, gets reasoning — same "aha moment" as investor demo ✅ DONE |

### Vision Success (Phase B-G)

| Capability | Success Metric |
|------------|----------------|
| Voice | 5-minute natural conversation |
| Dashboard | All info visible in < 3s |
| Morning Briefing | Delivered daily with actionable content |
| Nudges | Reconnected with 3 neglected relationships |
| Focus | Zero non-urgent interruptions during focus |
| Mobile | Full experience on phone |

### Long-Running Tasks & Life Dashboard Success (Phase H-I)

| Capability | Success Metric |
|------------|----------------|
| Mission Decomposition | "Build Twitter brand" → 12-week plan with daily actions in < 30s |
| Scheduled Execution | Daily actions execute at scheduled time without manual trigger |
| Adaptation | Week 4 plan adjusts based on engagement data (drops polls, adds threads) |
| Human Approval | Phase transitions require explicit user approval before proceeding |
| Metrics Collection | External metrics (followers, engagement) auto-collected daily |
| Progress Tracking | Shows "450/1000 followers = 45%" with completion date prediction |
| Life Dashboard | Today's Focus shows actions from BOTH health goals AND missions |
| Unified View | User sees all life goals in one place, not separate systems |
| Sakhi Insights | Auto-surfaces "walks reduce your anxiety by 40%" from correlation |
| Check-in Flow | Complete 5 daily actions in < 30 seconds via quick actions |

---

## References

- [SAKHI_EVOLUTION_PLAN.md](../SAKHI_EVOLUTION_PLAN.md) - Full evolution plan with phases
- [VISION_GAP_ANALYSIS.md](./VISION_GAP_ANALYSIS.md) - Gap analysis against Personal OS vision
- [Agent Task Execution](./agent-task-execution.md) - Task execution architecture
- [Sakhi vs OpenClaw Comparison](./sakhi-vs-openclaw-comparison.md) - Feature comparison
- [LONG_RUNNING_TASKS.md](./LONG_RUNNING_TASKS.md) - **Long-running task architecture for Life Missions**
- OpenClaw source: `/Users/fanantics/Downloads/openclaw-main/`
