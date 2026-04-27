# Current Task

> What we're working on right now. Update when switching tasks.

---

## Active Task

**Phase AC: Active Context & Morning Review**

### Status: In Progress — Plan updated, starting AC.1

### Build Sequence
1. **AC.1 Session UX rewrite** ← START HERE (no infra needed, immediate lift)
2. **AC.2 Stance-shift detection** ("What Changed") — gating feature, validate internally first
3. **AC.3 Decision extraction + Open Loops Ledger** — feeds everything downstream
4. **AC.4 Active Context panel** — surface once extraction is reliable
5. **AC.5 Morning Review home screen** — delivery surface (Think/Act/Review)
6. **AC.6 Paywall** — gates Active Context behind paid tier

### What's Done
- [x] Product spec rated + reviewed (9/10)
- [x] Plan document updated (`docs/BUILD_PLAN.md`)
- [x] New Phase AC added with full task breakdown
- [x] Build sequence reordered: stance-shift detection first, morning review last

### In Progress
- [ ] AC.1: Session UX rewrite — system prompt stance + first-message anchoring

---

## Context

Product direction refocused: Sakhi is "AI that keeps track of your unfinished thinking and helps you resolve it over time."

**The gating risk**: Decision extraction quality — open loops must be real or the whole panel feels like a horoscope. Validate internally before any panel goes live.

**"What Changed" is the differentiating feature** — lead with it in the morning review, build it second.

All infrastructure already exists (continuity arcs, enrichment workers, session memory, decision ledger columns). What's missing is the product surface.

---

## Key Files

- `sakhi/apps/api/routes/turn_v2.py` — turn handler, continuity pack assembly
- `sakhi/apps/api/services/conversation_v2/conversation_reasoner.py` — system prompt + metadata → LLM context
- `sakhi/apps/api/services/conversation_v2/conversation_engine.py` — LLM call + reply generation
- `sakhi/apps/api/services/continuity/chat.py` — continuity pack builder
- `sakhi/apps/api/routes/continuity.py` — continuity API endpoints
- `apps/web/app/experience/converse/page.tsx` — web chat UI
- `apps/mobile/app/experience/converse/index.tsx` — mobile chat UI

---

*Updated: 2026-04-25*
