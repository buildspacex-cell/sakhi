# Sakhi Memory Strategy

> Internal working document. Last updated: 2026-04-02
> Covers memory architecture philosophy, retention model, compaction strategy, and pricing implications.

---

## The Core Principle

**The model always lives. The detail fades.**

This mirrors how human memory actually works. You don't remember every conversation verbatim. But the shape of who you were in a period — your anxieties, priorities, what mattered, what was shifting — that stays. The verbatim detail fades. The intelligence persists.

Sakhi's memory architecture is designed around this truth, not against it.

---

## The Razor / Cartridge Frame

This is the mental model for all pricing and memory decisions.

**Razor = the model.** Free. Always yours. Keeps updating with every conversation. Sakhi never forgets who you are becoming — even on the free tier.

**Cartridge = raw memory depth.** That's what you pay for. The longer the history retained at full fidelity, the sharper the recall. Standard cartridge = 1 year (Pro). Premium cartridge = unlimited archive (add-on).

The user is not paying for features in the abstract. They are paying for **fidelity over time** and **depth of intelligence.**

---

## Three Layers of Memory

### Layer 1 — Raw Memory
Full verbatim conversation logs. Every turn, every message, every reflection stored at full fidelity.

- High storage cost
- High recall precision ("on January 14th you said...")
- Diminishing retrieval value after 90 days for most users
- Required for Deep Reflect and Arc to run at maximum accuracy

### Layer 2 — Episodic Summaries
Monthly distillations of what happened, what mattered, what shifted. Generated automatically by the Continuity Engine from raw memory.

- Compact. ~1–5KB per month of activity
- High signal, low noise
- What Arc and Occupancy primarily run on
- The "shape" of a period without the verbatim detail

### Layer 3 — The Living Model
Traits, patterns, values, attention map, drift state, arc trajectory. Continuously updated with every interaction.

- The compounding asset
- Sub-MB even after years of use
- **Never deleted. Never compacted. Exists on all tiers.**
- The answer to "who are you becoming" lives here

---

## The Compaction Model

When raw memory is compacted, Layer 1 is distilled into Layer 2. The model (Layer 3) updates with any new signals. Raw logs are then archived (Pro + add-on) or deleted (Free / Pro at cap).

```
New conversation
       ↓
Raw memory stored (Layer 1)
       ↓
Model updates in real-time (Layer 3)
       ↓
Monthly: episodic summary generated (Layer 2)
       ↓
At tier threshold:
  Free (30 days)      → raw logs deleted, episodic + model retained
  Pro (1 year)        → raw logs deleted after 1yr, episodic + model retained
  Pro + Memory add-on → raw logs archived indefinitely, full recall always
```

### What compaction preserves
- All pattern-level intelligence
- Drift detection and arc trajectory
- Life Occupancy mapping
- Emotional and thematic signatures of the period
- "Around that time you were navigating X, high on Y, pulling away from Z"

### What compaction loses
- Verbatim recall of specific conversations
- Exact dates and sequences within a period
- Word-for-word quotes from your own reflections

### How to communicate this to users
Honestly. Frame it as:

*"Sakhi remembers the shape of that time. Not every word — but who you were, what mattered, what was shifting. The same way you do."*

This is not a limitation. It is a feature of how intelligence actually works.

---

## User-Controlled Compaction

Users can initiate compaction manually at any time — on a specific period, a specific thread, or their full history.

**Why this matters:**
- Builds trust: the user understands what happens to their data
- Aligns with privacy positioning: you control your memory, not us
- Creates a meaningful ritual: "compact this chapter" is an intentional act
- GDPR: right to erasure is cleanly implemented at the compaction layer

**The compaction ritual as product:**
A user closing a difficult period — a job, a relationship, a season of their life — choosing to compact it is a meaningful moment. Sakhi marks it: *"This chapter has been distilled. The patterns are held. The weight is released."* That is not a technical operation. That is product.

---

## Pricing Structure: Full Options Considered

### Option A — Two tiers, unlimited Pro (rejected)
- Free: 30-day raw
- Pro: unlimited raw + all features

**Why rejected:** Unlimited raw on Pro means power users store years of verbose conversations with no cost ceiling. COGS becomes unpredictable. No third revenue stream.

---

### Option B — Two tiers + storage add-on (recommended)

| Tier | Model | Raw memory | Features | Price |
|---|---|---|---|---|
| Free | Always lives | 30 days, then compacts | Basic conversation, 3 Deep Reflects/mo, 1 Story/mo, Arc view-only | $0 |
| Pro | Always lives | 1 year raw, then compacts | Full Deep Reflect, full Story, Arc + Occupancy live, full features | $20/mo |
| Pro + Memory | Always lives | Unlimited raw archive | Everything in Pro, verbatim recall forever | $20 + $5/mo |

**Annual:** Pro $180/yr (save 25%). Pro + Memory $240/yr.

**Why this works:**
- Pro at $20 feels complete — 1 year of your life is substantial for most users
- The add-on is opt-in — power users, journalers, people in major transitions self-select
- Storage as a flat add-on ($5/mo) is simple to explain and bill
- Mirrors the razor/cartridge model cleanly

---

### Option C — Three fixed tiers (considered, not recommended)
- Free / Pro / Pro Max
- Rejected because fixed tiers force users into a higher price point rather than letting them add incrementally. The add-on model is more elegant and less friction.

---

## Feature Gating Strategy

Memory depth alone is one conversion trigger. Feature limits create a second, earlier trigger — catching new users before the 30-day memory wall.

**The principle:** limits must feel like *"I want more of this"* not *"I'm being blocked."* The number matters.

| Feature | Free | Pro |
|---|---|---|
| Deep Reflect | 3/month | Unlimited |
| Story / My Story | 1/month | Unlimited |
| Continuity Arc | View-only snapshot | Live, updating |
| Life Occupancy | View-only snapshot | Live, updating |
| Memory recall depth | 30 days | 1 year (+ add-on for unlimited) |
| Pattern surfacing | Basic | Full cross-session inference |

### Why these limits

**Deep Reflect — 3/month:**
Enough to experience the value twice and want it a third time. The conversion moment is hitting the limit right when a user has something meaningful to reflect on. Too low (1/month) feels punitive. Too high (10/month) removes urgency.

**Story / My Story — 1/month:**
These are high-synthesis, frontier-model-heavy queries. One taste is enough to convert. A user who sees their own story surfaced once will want it again immediately. The gap between 1 and unlimited is felt acutely.

**Arc / Occupancy — view-only on free:**
The model computes these even on free — that's the razor. But the live, updating, interactive version is Pro. Free users see a snapshot that says "your Arc is building" but can't drill in. This creates aspiration without full blocking.

### Two distinct conversion triggers

**Trigger 1 — Feature limit (felt in Week 1–2):**
New user experiences Deep Reflect or Story, hits the limit, wants more. Converts early based on immediate value felt.

**Trigger 2 — Memory depth (felt at Day 30–45):**
User notices Sakhi losing the thread of something from 5–6 weeks ago. Compaction has happened. The model still knows the shape, but not the detail. Converts based on wanting their full history preserved.

Together these cover two user archetypes:
- **Fast converter:** engaged early, hits feature limit, upgrades in Week 2
- **Slow converter:** uses casually, feels memory fading at Day 30–45, upgrades then

---

## Recall Quality After Compaction

| Question type | Free (post-compaction) | Pro (within 1 year) | Pro + Memory |
|---|---|---|---|
| "What was I anxious about in early 2025?" | Pattern level only | Full verbatim | Full verbatim |
| "How have my priorities shifted?" | Full Arc | Full Arc | Full Arc |
| "What did I say on January 14th?" | No | Yes | Yes |
| "What patterns keep coming back?" | Yes | Yes | Yes |
| "Who am I becoming?" | Yes | Yes | Yes |
| "What was I working through last March?" | Shape only | Full detail | Full detail |

---

## The Switching Cost Built Into Memory

After 6 months, your patterns are in here.
After 12 months, your arc is in here.
After 24 months, your model is irreplaceable.

Even if a competitor builds a better interface, they cannot import your model. The data is proprietary. The compacted episodic history is not portable in any meaningful way.

**Lock-in through value accumulation, not friction.** The distinction matters for trust and for positioning.

---

## Unit Economics Impact

### Storage cost per user/month (estimated)

| Tier | Raw storage | Episodic | Model | Total storage cost |
|---|---|---|---|---|
| Free | ~50MB (30 days) | ~5MB | ~1MB | ~$0.01/mo |
| Pro | ~600MB (1 year) | ~60MB | ~1MB | ~$0.08/mo |
| Pro + Memory | Unbounded | ~60MB+ | ~1MB | ~$0.05–0.50/mo |

Storage is not the dominant cost — inference is (see PRICING_ECONOMICS.md). But capping raw memory keeps it predictable.

### Effect on gross margin

Capping Pro at 1 year raw prevents the unbounded storage cost of the original "unlimited" model. Power users on the add-on self-fund their higher storage cost ($5/mo add-on covers well above actual storage cost at current rates).

---

## Privacy and Data Architecture

- **Right to erasure:** deletes raw logs, episodic summaries, and model updates derived from the user. Full purge by default.
- **Export:** human-readable report of patterns, arc, and occupancy map. Not a machine-readable model file.
- **Compaction audit log:** users can see what was compacted, when, and what episodic summary was generated.
- **Local-first vs cloud:** decision pending. Recommendation: encrypted cloud with local cache. Full local limits Arc/Occupancy computation.

---

## Open Questions

- [ ] Compaction trigger: time-based (auto at 30 days for free) or volume-based?
- [ ] What does the compaction UI look like? Ritual-like or silent?
- [ ] Cross-device sync: how does the model stay consistent across mobile and web?
- [ ] At what usage level does the $5/mo add-on need repricing? (volume-based in Year 2?)
- [ ] Fine-tuning: can we reduce frontier model dependency for non-reflection tasks by Month 18?
- [ ] Arc and Occupancy on free: what exactly does the "view-only snapshot" show without being misleading?
