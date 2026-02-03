# Sakhi vs OpenClaw: Comprehensive Feature Comparison

> Reference documentation for feature parity analysis and roadmap planning.

## Executive Summary

| Aspect | OpenClaw | Sakhi |
|--------|----------|-------|
| **Primary Focus** | Multi-channel messaging platform with browser automation | Personal AI companion with vision-based desktop control |
| **Core Architecture** | Gateway server + Agent + Plugins | Web + API + Desktop Agent + Workers |
| **Automation Approach** | Playwright (DOM manipulation) | Vision + LLM (screenshot-based) |
| **Target Users** | Developers building AI bots | Individuals seeking personal AI assistance |

---

## 1. Communication Channels

| Feature | OpenClaw | Sakhi | Priority |
|---------|----------|-------|----------|
| WhatsApp | ✅ Built-in (Baileys) | ❌ | Low |
| Telegram | ✅ Built-in | ❌ | Low |
| Discord | ✅ Built-in | ❌ | Low |
| Slack | ✅ Built-in | ❌ | Low |
| Signal | ✅ Built-in | ❌ | Low |
| iMessage | ✅ macOS native | ❌ | Low |
| Teams | ✅ Plugin | ❌ | Low |
| Matrix | ✅ Plugin | ❌ | Low |
| Web Chat | ✅ Built-in | ✅ Primary | N/A |
| Voice | ✅ Twilio telephony | ✅ Voice journal | Different use |
| **Total Channels** | **28+** | **1 (web)** | - |

**Assessment**: OpenClaw is a messaging platform; Sakhi is a personal companion. Multi-channel is not a priority for Sakhi's use case.

---

## 2. Browser/Desktop Automation

| Feature | OpenClaw | Sakhi | Notes |
|---------|----------|-------|-------|
| **Approach** | Playwright (DOM) | Vision + LLM | Fundamentally different |
| Speed per action | ~100-500ms | ~2-5s | Trade-off for flexibility |
| Web apps | ✅ Native | ✅ Via screenshot | |
| Native apps | ❌ | ✅ Any visual app | **Sakhi advantage** |
| DOM selectors | ✅ | ❌ | |
| Screenshot capture | ✅ | ✅ Core | |
| Coordinate clicking | ❌ | ✅ | |
| Form interaction | ✅ Direct | ✅ Vision-based | |
| JavaScript execution | ✅ | ❌ | |
| CDP integration | ✅ | ❌ | |
| Trace recording | ✅ | ❌ | Consider |
| Profile persistence | ✅ | N/A | |

**Assessment**: Different paradigms. Sakhi's vision approach is slower but works with ANY application (web + native). This is a strategic advantage for a personal assistant.

---

## 3. Agent System & Task Execution

| Feature | OpenClaw | Sakhi | Parity | Action |
|---------|----------|-------|--------|--------|
| Multi-step execution | ✅ | ✅ | ✅ At par | - |
| Error classification | ✅ FailoverError | ✅ AgentError | ✅ At par | - |
| Retry logic | ✅ 5-layer | ✅ 3-layer | ⚠️ Functional | Consider adding auth/lane layers |
| Exponential backoff | ✅ | ✅ | ✅ At par | - |
| Timeout clamping | ✅ | ✅ | ✅ At par | - |
| Session locking | ✅ File-based | ✅ PostgreSQL | ✅ **Better** | - |
| Action queue | ✅ Lane-based | ✅ asyncio.Lock | ✅ At par | - |
| Action history | ✅ Full + compact | ✅ 50-item | ✅ At par | - |
| Cooldown tracking | ✅ | ✅ | ✅ At par | - |
| Step limits | ✅ | ✅ 50 max | ✅ At par | - |
| Context compaction | ✅ On overflow | ⚠️ Flag only | 🔴 Gap | **Implement** |
| Auth profile rotation | ✅ Multi-profile | ❌ Single | N/A | Not needed |

### Action Items for Task Execution
1. [ ] Implement context window compaction when `context_compaction_attempted` is triggered
2. [ ] Consider adding lane-based parallel execution for multi-task scenarios

---

## 4. Approval & Safety System

| Feature | OpenClaw | Sakhi | Notes |
|---------|----------|-------|-------|
| Execution approvals | ✅ User confirmation | ✅ Risk-based | Both have it |
| Risk classification | ❌ | ✅ LOW→CRITICAL | **Sakhi advantage** |
| Pre-approval rules | ✅ Safelist | ✅ Auto-approve rules | ✅ At par |
| Approval UI | ✅ Control UI | ✅ Chat-based | |
| Approval persistence | ✅ | ✅ Database | |
| Timeout handling | ✅ | ✅ 5-min default | |
| Bash safelist | ✅ | ❌ (not applicable) | |

**Assessment**: Sakhi has a more sophisticated risk-based approval system. No action needed.

---

## 5. Memory & Knowledge

| Feature | OpenClaw | Sakhi | Priority |
|---------|----------|-------|----------|
| **Vector storage** | ✅ LanceDB | ✅ pgvector | ✅ At par |
| **Memory types** | Session memory | Episodic + Semantic | **Sakhi richer** |
| Graph-based memory | ❌ | ✅ Nodes + Edges | **Sakhi advantage** |
| Relationship tracking | ❌ | ✅ Weighted edges | **Sakhi advantage** |
| Time decay | ❌ | ✅ Decay functions | **Sakhi advantage** |
| Salient extraction | ❌ | ✅ Auto-extract | **Sakhi advantage** |
| BM25 search | ❌ | ✅ Hybrid | **Sakhi advantage** |
| Deep context | ❌ | ✅ Multi-layer | **Sakhi advantage** |
| Memory compaction | ✅ | ✅ | ✅ At par |
| Session dedup | ✅ | ✅ | ✅ At par |

**Assessment**: Sakhi significantly ahead in memory capabilities. This is a core differentiator.

---

## 6. Personalization

| Feature | OpenClaw | Sakhi | Notes |
|---------|----------|-------|-------|
| **Ayurvedic system** | ❌ | ✅ Full dosha tracking | **Sakhi unique** |
| Energy tracking | ❌ | ✅ Circadian + infradian | **Sakhi unique** |
| Chronotype detection | ❌ | ✅ | **Sakhi unique** |
| Preference learning | ❌ | ✅ Reinforcement | **Sakhi unique** |
| User profile | ✅ Basic | ✅ Comprehensive | **Sakhi richer** |
| Identity/Avatar | ✅ | ✅ | ✅ At par |
| Communication style | ❌ | ✅ Tone analysis | **Sakhi advantage** |

**Assessment**: Personalization is Sakhi's core strength. Continue investing here.

---

## 7. Reflection & Insights

| Feature | OpenClaw | Sakhi | Notes |
|---------|----------|-------|-------|
| Weekly synthesis | ❌ | ✅ | **Sakhi unique** |
| Meta reflection | ❌ | ✅ | **Sakhi unique** |
| Soul dashboard | ❌ | ✅ Visualization | **Sakhi unique** |
| Shadow work | ❌ | ✅ | **Sakhi unique** |
| Values tracking | ❌ | ✅ | **Sakhi unique** |
| Narrative generation | ❌ | ✅ | **Sakhi unique** |
| Contradiction detection | ❌ | ✅ | **Sakhi unique** |
| Open loops tracking | ❌ | ✅ | **Sakhi unique** |

**Assessment**: Entirely unique to Sakhi. Core differentiator for personal AI companion use case.

---

## 8. Scheduling & Jobs

| Feature | OpenClaw | Sakhi | Action |
|---------|----------|-------|--------|
| Cron scheduling | ✅ Croner | ✅ RQ workers | ✅ At par |
| Recurring jobs | ✅ | ✅ | ✅ At par |
| One-shot jobs | ✅ | ✅ | ✅ At par |
| Job persistence | ✅ | ✅ | ✅ At par |
| Background workers | ✅ | ✅ Multiple types | ✅ At par |
| Calendar integration | ❌ | ✅ Full calendar | **Sakhi advantage** |

**Assessment**: At parity with additional calendar capabilities in Sakhi.

---

## 9. Tools & Capabilities

| Feature | OpenClaw | Sakhi | Priority |
|---------|----------|-------|----------|
| **Total tools** | 37+ | ~15 | Medium |
| Browser tool | ✅ | ✅ (vision) | - |
| Message tool | ✅ | ✅ | - |
| Web fetch | ✅ | ✅ | - |
| Web search | ✅ | ✅ | - |
| Image tool | ✅ Vision | ✅ Vision | - |
| TTS | ✅ Multiple | ❌ | Low |
| Memory tool | ✅ | ✅ Deep | - |
| Cron tool | ✅ | ✅ | - |
| Canvas/UI tool | ✅ | ❌ | Low |
| Discord actions | ✅ | ❌ | Low |
| Telegram actions | ✅ | ❌ | Low |
| Nodes (remote device) | ✅ | ❌ | Medium |

### Action Items for Tools
1. [ ] Consider adding TTS for voice-first interactions
2. [ ] Evaluate remote device control for mobile → desktop scenarios

---

## 10. Platform Support

| Platform | OpenClaw | Sakhi | Priority |
|----------|----------|-------|----------|
| macOS native app | ✅ SwiftUI | ✅ Electron | - |
| iOS app | ✅ | ✅ React Native | - |
| Android app | ✅ Compose | ✅ React Native | - |
| Linux | ✅ systemd | ❌ | Low |
| Windows | ✅ WSL2 | ❌ | Medium |
| Docker | ✅ | ❌ | Medium |
| Cloud platforms | ✅ 9+ | ✅ Vercel | - |

### Action Items for Platforms
1. [ ] Consider Docker support for self-hosted deployment
2. [ ] Evaluate Windows support for broader reach

---

## 11. LLM Integration

| Feature | OpenClaw | Sakhi | Priority |
|---------|----------|-------|----------|
| **Providers** | 10+ | 2 (OpenAI, OpenRouter) | Medium |
| Anthropic | ✅ Native | ✅ Via OpenRouter | - |
| OpenAI | ✅ | ✅ | - |
| Gemini | ✅ | ❌ | Low |
| Ollama | ✅ | ❌ | Medium |
| Groq | ✅ | ❌ | Low |
| AWS Bedrock | ✅ | ❌ | Low |
| Custom endpoints | ✅ | ✅ | - |
| Provider budgeting | ❌ | ✅ Daily limits | **Sakhi advantage** |
| Policy routing | ❌ | ✅ Task-specific | **Sakhi advantage** |

### Action Items for LLM
1. [ ] Consider Ollama support for local/private deployment
2. [ ] Current provider budgeting is a strength - maintain

---

## 12. Skills & Capabilities Strategy

### Sakhi's Hybrid Approach

Sakhi uses a **"Bridge then Native"** strategy to reduce friction while building toward a self-contained ecosystem:

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER JOURNEY                                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  PHASE 1: Bridge (Reduce Friction)                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │ Google   │  │ Apple    │  │ Gmail    │  │ Notion   │            │
│  │ Calendar │  │ Reminders│  │          │  │          │            │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘            │
│       │             │             │             │                   │
│       └─────────────┴─────────────┴─────────────┘                   │
│                         │                                            │
│                         ▼                                            │
│              ┌─────────────────────┐                                │
│              │   SAKHI LAYER       │  ← Unified interface           │
│              │   (Skills/Bridge)   │                                │
│              └─────────────────────┘                                │
│                         │                                            │
│  PHASE 2: Migrate (Gradual)                                         │
│                         ▼                                            │
│              ┌─────────────────────┐                                │
│              │   SAKHI NATIVE      │                                │
│              │  ┌───────┐ ┌──────┐ │                                │
│              │  │Calendar│ │Tasks │ │                                │
│              │  └───────┘ └──────┘ │                                │
│              │  ┌───────┐ ┌──────┐ │                                │
│              │  │ Notes │ │ Mesh │ │  ← User's data in Sakhi       │
│              │  └───────┘ └──────┘ │                                │
│              │  ┌───────┐ ┌──────┐ │                                │
│              │  │Memory │ │Email │ │  ← @user.sakhi.id             │
│              │  └───────┘ └──────┘ │                                │
│              └─────────────────────┘                                │
│                                                                      │
│  PHASE 3: Vision Loop (Universal Fallback)                          │
│              ┌─────────────────────┐                                │
│              │  Desktop Agent      │  ← For external apps          │
│              │  (Screenshot+LLM)   │    not in Sakhi ecosystem     │
│              └─────────────────────┘                                │
└─────────────────────────────────────────────────────────────────────┘
```

### Capability Categories

| Category | Phase 1 (Bridge) | Phase 2 (Native) | Phase 3 (Vision) |
|----------|------------------|------------------|------------------|
| **Calendar** | Google/Apple Calendar sync | Sakhi Calendar | - |
| **Tasks** | Apple Reminders, Todoist | Sakhi Tasks (Intents) | - |
| **Notes** | Notion, Obsidian, Apple Notes | Sakhi Journal/Observations | - |
| **Contacts** | Apple/Google Contacts | Sakhi Mesh | - |
| **Email** | Gmail read/send | `@user.sakhi.id` | - |
| **Booking** | - | - | OpenTable, Resy via vision |
| **Shopping** | - | - | Amazon, etc. via vision |
| **Banking** | - | - | Bank apps via vision |

### What Already Exists in Sakhi

| Native Feature | Status | Location |
|----------------|--------|----------|
| Calendar | ✅ Exists | `/experience/calendar`, calendar APIs |
| Tasks/Intents | ✅ Exists | `intents` table, goal tracking |
| Journal/Notes | ✅ Exists | `observations`, journal APIs |
| Contacts/Mesh | ✅ Exists | Mesh system for connections |
| Memory | ✅ Exists | Episodic, nodes, edges |
| Email | 🔜 Planned | `@user.sakhi.id` identity |

### Skills Needed (Phase 1 Bridges)

| Skill | Purpose | Priority | Effort |
|-------|---------|----------|--------|
| **Google Calendar Sync** | Import/export events | High | Medium |
| **Apple Calendar Sync** | Import/export events | High | Medium |
| **Apple Reminders Bridge** | Sync tasks bidirectionally | Medium | Low |
| **Gmail Bridge** | Read/send via user's Gmail | Medium | Medium |
| **Notion Import** | One-time migration | Low | Low |

### Plugin/Extension System

| Feature | OpenClaw | Sakhi | Priority |
|---------|----------|-------|----------|
| Plugin architecture | ✅ TypeScript modules | 🔜 Planned | Medium |
| Skills system | ✅ 52+ skills | 🔜 Hybrid approach | Medium |
| Runtime API | ✅ | ❌ | Medium |
| Tool registration | ✅ | ❌ | Medium |
| Custom CLI commands | ✅ | ❌ | Low |
| Bundled extensions | ✅ 28+ | ❌ | Low |

### Action Items for Skills/Extensibility
1. [ ] Design skill interface (Bridge skills + Native actions)
2. [ ] Implement Google Calendar sync skill
3. [ ] Implement Apple Calendar sync skill
4. [ ] Build migration path from external → native
5. [ ] Consider plugin architecture for community extensions

---

## 13. Security

| Feature | OpenClaw | Sakhi | Notes |
|---------|----------|-------|-------|
| Channel-level ACL | ✅ | N/A | Not applicable |
| Execution safelist | ✅ | ✅ Risk-based | **Sakhi richer** |
| Sandbox mode | ✅ | ❌ | Consider |
| Permission model | ✅ Multi-level | ✅ OS permissions | Different approach |
| Credential storage | ✅ Keychain | ✅ Encrypted | ✅ At par |
| mDNS auth | ✅ | ❌ | Not needed |
| Tailscale integration | ✅ | ❌ | Not needed |

### Action Items for Security
1. [ ] Consider sandbox mode for high-risk actions

---

## 14. Data Persistence

| Feature | OpenClaw | Sakhi | Notes |
|---------|----------|-------|-------|
| Primary store | SQLite + JSON | PostgreSQL | **Sakhi more robust** |
| Vector store | LanceDB | pgvector | Both valid |
| Session store | File-based | PostgreSQL | **Sakhi better** |
| Config format | JSON5 | Env vars | Different approach |
| State persistence | JSON files | PostgreSQL | **Sakhi better** |

**Assessment**: Sakhi's PostgreSQL-based persistence is more production-ready.

---

## 15. Observability

| Feature | OpenClaw | Sakhi | Priority |
|---------|----------|-------|----------|
| Health endpoints | ✅ Detailed | ⚠️ Basic | High |
| Subsystem logging | ✅ | ✅ | - |
| Diagnostics | ✅ Comprehensive | ⚠️ Basic | High |
| Token/cost tracking | ✅ Per-provider | ✅ Budget tracking | - |
| Heartbeat monitoring | ✅ | ✅ | - |

### Action Items for Observability
1. [ ] Add detailed health check endpoint (`/health` with component status)
2. [ ] Add diagnostics endpoint for debugging
3. [ ] Consider structured event logging for analytics

---

## Priority Roadmap

### High Priority (Production Readiness)
| Item | Description | Effort |
|------|-------------|--------|
| Context compaction | Implement LLM context compaction on overflow | Medium |
| Health endpoints | Add `/health` with detailed component status | Low |
| Diagnostics | Add debugging/diagnostics endpoint | Medium |

### High Priority (User Onboarding - Phase 1 Bridges)
| Item | Description | Effort |
|------|-------------|--------|
| Calendar Sync | Google/Apple Calendar bidirectional sync | Medium |
| Skill Interface | Design skill/bridge architecture | Medium |
| Migration Tools | Import data from Notion, Apple Notes, etc. | Medium |

### Medium Priority (Native Ecosystem - Phase 2)
| Item | Description | Effort |
|------|-------------|--------|
| Sakhi Email | `@user.sakhi.id` identity and inbox | High |
| Enhanced Tasks | Rich task system beyond intents | Medium |
| Native Notes | Full-featured note-taking in Sakhi | Medium |
| Mesh Contacts | Complete contact management | Medium |

### Medium Priority (Platform)
| Item | Description | Effort |
|------|-------------|--------|
| Plugin system | Design extensibility architecture | High |
| Ollama support | Local LLM for privacy-focused users | Medium |
| Docker support | Container deployment option | Medium |
| Windows agent | Electron agent for Windows | High |

### Low Priority (Nice to Have)
| Item | Description | Effort |
|------|-------------|--------|
| TTS | Text-to-speech for voice output | Medium |
| Sandbox mode | Containerized action execution | High |
| Additional providers | Gemini, Groq, Bedrock | Low each |

---

## Strategic Differentiators

### Sakhi's Unique Value (Maintain & Invest)
1. **Self-contained personal ecosystem** - Calendar, tasks, notes, contacts, email all native
2. **Vision-based automation** - Works with ANY app, not just web
3. **Deep memory system** - Episodic + semantic + graph-based
4. **Personalization** - Ayurvedic, energy, chronotype, preferences
5. **Reflection/Insights** - Weekly synthesis, shadow work, values
6. **Risk-based approvals** - Graduated safety system
7. **"Bridge then Native" strategy** - Meet users where they are, migrate to Sakhi

### OpenClaw's Strengths (Don't Compete)
1. Multi-channel messaging (28+ platforms)
2. Plugin ecosystem (52+ skills for external services)
3. Browser automation speed (Playwright)
4. Enterprise networking (Tailscale, mDNS)

### Key Strategic Difference

```
OpenClaw: Integrates WITH external services (Gmail, Notion, etc.)
          └── User's data lives in those services

Sakhi:    REPLACES external services over time
          └── User's data lives IN Sakhi
          └── Bridges for initial onboarding only
```

---

## Conclusion

Sakhi and OpenClaw serve fundamentally different purposes:

| Aspect | OpenClaw | Sakhi |
|--------|----------|-------|
| **Purpose** | Platform for AI bots | Personal AI companion |
| **Data** | Lives in external services | Lives IN Sakhi |
| **Skills** | Integrations forever | Bridges → Native migration |
| **Vision** | Messaging across channels | Self-contained personal OS |

### Current Status

**Task Execution**: ~90% parity with OpenClaw
- ✅ Error classification, retry logic, timeouts, session locking
- 🔴 Gap: Context compaction, health endpoints

**Skills/Capabilities**: Different approach
- OpenClaw: 52+ external integrations (permanent)
- Sakhi: Bridge skills (temporary) → Native features (permanent)

### Next Steps

1. **Phase 1 (Now)**: Build bridge skills for frictionless onboarding
   - Calendar sync (Google/Apple)
   - Task import
   - Notes migration

2. **Phase 2 (Soon)**: Complete native feature set
   - Sakhi Email (`@user.sakhi.id`)
   - Enhanced native calendar/tasks/notes

3. **Phase 3 (Ongoing)**: Vision loop for everything else
   - External apps that can't be bridged
   - Universal automation fallback

Sakhi's unique strengths in memory, personalization, and reflection - combined with a self-contained ecosystem - make it fundamentally different from OpenClaw's integration-focused approach.

---

## References

- OpenClaw source: `/Users/fanantics/Downloads/openclaw-main/`
- Sakhi agent docs: `/Users/fanantics/Documents/Sakhi/docs/agent-task-execution.md`
- Key Sakhi files:
  - `sakhi/apps/api/services/agent/vision_loop.py`
  - `sakhi/apps/api/services/agent/errors.py`
  - `sakhi/apps/api/services/agent/timeouts.py`
  - `sakhi/apps/api/services/agent/session_lock.py`
  - `sakhi/apps/api/services/agent/actions.py`
