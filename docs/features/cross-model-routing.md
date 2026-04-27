# Cross-Model Routing — Product & Economics Decision

> Internal decision document. Last updated: 2026-04-17
> Status: Approved direction. Not yet built.

---

## Context: How This Decision Was Made

During a pre-seed pitch audit (April 2026), the one-pager at `/company-deck/one-pager-v1` was evaluated against the actual codebase. The audit found one overclaim:

> *"Power users can choose the model; everyone else can let Sakhi route the discussion automatically."*

The `LLMRouter` infrastructure exists and is well-architected for multi-provider routing (`sakhi/libs/llm_router/`), but at audit time:
- Only one provider is live: OpenAI (`openai_provider.py`)
- Default model: `gpt-4o-mini` via env var
- No user-facing model picker exists anywhere in the product
- No Anthropic/Claude or Google/Gemini provider is connected

This document records the product and economic decision made in response to that finding.

**Decision: Build cross-model routing. Ship it as Pro (smart auto-routing) + capped user choice. Not a separate pricing tier.**

---

## What "Cross-Model" Means for Sakhi

There are two distinct features that get conflated under "cross-model":

### Feature A — Smart Auto-Routing (internal)
Sakhi automatically selects the right model for each task type without the user knowing or caring. Cheaper models handle lightweight turns; frontier models handle high-stakes reasoning. The LLMRouter already has a `policy: dict[Task, list[str]]` field designed for exactly this.

### Feature B — User Model Choice (explicit)
The user can override which model Sakhi uses for their sessions, up to a monthly cap.

**Both are Pro features. Neither is a separate pricing tier.**

---

## Economics Analysis

### Assumptions per turn

| Variable | Value |
|---|---|
| System prompt + continuity context | ~3,500 input tokens |
| User message | ~150 input tokens |
| Assistant response | ~350 output tokens |
| Total per turn | ~4,000 tokens in, ~350 out |

The continuity context is heavy by design — loading 180-day arc, thread state, memory pack. This is a feature, not waste. It is also the reason model choice has real cost implications.

### Cost per turn by model (April 2026 pricing)

| Model | Input $/1M | Output $/1M | Cost/turn |
|---|---|---|---|
| GPT-4o-mini | $0.15 | $0.60 | ~$0.0007 |
| GPT-4o | $2.50 | $10.00 | ~$0.0123 |
| Claude Sonnet 3.7 | $3.00 | $15.00 | ~$0.0158 |
| Claude Opus 4 | $15.00 | $75.00 | ~$0.079 |
| Gemini 1.5 Pro | $1.25 | $5.00 | ~$0.0062 |

*Note: Inference costs are deflationary. These figures will likely drop 30–50% by 2027.*

### Monthly cost at $20/mo Pro (LLM budget: ~$12–14 after 35% margin target)

| Usage profile | GPT-4o-mini | GPT-4o | Claude Sonnet | Claude Opus |
|---|---|---|---|---|
| Light (500 turns/mo) | $0.35 ✅ | $6.15 ✅ | $7.90 ✅ | $39.50 ❌ |
| Regular (1,500 turns/mo) | $1.05 ✅ | $18.45 ❌ | $23.70 ❌ | $118.50 ❌ |
| Power (3,000 turns/mo) | $2.10 ✅ | $36.90 ❌ | $47.40 ❌ | $237.00 ❌ |

### Key finding

**Free model choice at $20/mo is not economically safe.** One regular user on Claude Sonnet (1,500 turns/month) costs $23.70 in LLM alone — more than the subscription revenue. One power user on GPT-4o costs $36.90.

GPT-4o-mini is safe at any realistic usage level. Frontier models require either a cap, a higher tier, or smart routing that limits their use to high-value turns.

---

## The Recommendation

### Pro ($20/mo): Smart Auto-Routing

Sakhi routes to the optimal model for each turn automatically. The user never sees a model selector. This is:

- **Economically sound**: Most turns (continuity recall, short responses, follow-up questions) route to `gpt-4o-mini`. Only high-complexity reasoning turns escalate to frontier models.
- **On-brand**: The continuity thesis is that Sakhi handles complexity so you don't have to. Hiding model choice reinforces this. Users should not think about models any more than they think about which server their email sits on.
- **Architecturally ready**: The `LLMRouter` already has `policy: dict[Task, list[str]]` and `DailyBudget` per provider. Task-based routing is the design intent.

**Routing policy (proposed):**

| Task type | Model | Rationale |
|---|---|---|
| Continuity recall / context loading | GPT-4o-mini | Structured retrieval, not reasoning |
| Short conversational turns (<200 tokens out) | GPT-4o-mini | Fast, cheap, quality sufficient |
| Standard conversational turns | GPT-4o | Reasoning quality matters |
| Deep Reflect | GPT-4o or Claude Sonnet | Highest reasoning quality needed |
| Arc compilation / pattern detection | GPT-4o | Analytical, structured output |
| Onboarding / Operating System inference | Claude Sonnet | Nuanced psychological inference |

Estimated blended cost under this routing policy: **$4–7/user/month** for a regular user, yielding **65–80% gross margin**.

### Pro ($20/mo): Capped User Model Choice

On top of smart routing, Pro users get a monthly allocation of **"premium model turns"** — explicit overrides where they can force a specific model for a session or conversation.

**Proposed cap: 100 premium model turns/month** (roughly 3–4 sessions/week where the user actively chooses).

This covers the "power user who wants Claude for their weekly strategy session" use case without opening unlimited frontier model access.

**Cap economics:**

| Scenario | Cost |
|---|---|
| User hits full 100-turn cap on Claude Sonnet | $1.58 additional cost |
| User hits full 100-turn cap on GPT-4o | $1.23 additional cost |
| Combined with smart routing base | $5.58–8.58/month total |
| Gross margin at $20 | 57–72% |

This holds margin safely even when users actively use the override feature.

---

## What "Cross-Model" Is NOT

- **Not a separate pricing tier.** "Collective" remains the third tier (continuity across people/teams, Year 2). Cross-model is a Pro capability, not a tier upgrade.
- **Not a pitch feature.** The one-pager should describe it as: *"Sakhi routes to the right model automatically."* User model choice is a secondary detail, not the headline.
- **Not a reason to raise the Pro price.** The economics work at $20 with smart routing. The cap handles the edge case. No price change needed.

---

## Updated Pitch Language

**Before (overclaim):**
> "Sakhi also carries that thread across models and time. Power users can choose the model; everyone else can let Sakhi route the discussion automatically."

**After (accurate):**
> "Sakhi carries that thread across time. It routes to the right model for each discussion automatically — and Pro users can override for sessions that need it."

**Solution section of one-pager:** Change *"across models and time"* → *"across time"*. The model routing is an implementation detail of how Sakhi maintains quality, not the core value proposition.

---

## Build Plan

### Phase 1 — Smart Auto-Routing (Ship with MVP)
- [ ] Add Anthropic provider to `sakhi/libs/llm_router/openai_provider.py` pattern → `anthropic_provider.py`
- [ ] Define task routing policy in `LLMRouteConfig` (see table above)
- [ ] Wire `DailyBudget` per provider with provider-level cost tracking
- [ ] Update `call_llm()` to pass task type, letting router select model
- [ ] Add `MODEL_ROUTING_POLICY` env var for runtime config without redeploy

### Phase 2 — User Model Choice with Cap (Post-MVP, Pre-Seed)
- [ ] Add `preferred_model` and `premium_turns_used` / `premium_turns_cap` to user settings
- [ ] Expose model selector in conversation settings UI (web + mobile)
- [ ] Enforce cap in turn route: if `premium_turns_used >= cap`, fall back to smart routing
- [ ] Reset cap monthly via worker job
- [ ] Show cap usage in user settings ("87 of 100 premium turns used this month")

### Phase 3 — Expanded Model Menu (Year 1, as providers mature)
- [ ] Add Gemini provider (`gemini_provider.py`)
- [ ] Evaluate Llama/local model for continuity retrieval tasks (cost reduction)
- [ ] Dynamic cap based on subscription age (long-tenure users get higher cap as loyalty signal)

---

## Architectural Notes

The `LLMRouter` in `sakhi/libs/llm_router/router.py` is already designed for this:

```python
@dataclass
class LLMRouteConfig:
    policy: dict[Task, list[str]]          # task → ordered list of providers to try
    provider_budgets: dict[str, float | None]  # per-provider daily spend limits
```

The `Task` enum in `sakhi/libs/llm_router/types.py` needs to be extended with the task types from the routing policy table above. Current providers: `openai_provider.py`. Anthropic and Gemini follow the same `BaseProvider` interface — adding providers is low-risk, isolated work.

`call_llm()` in `sakhi/apps/api/core/llm.py` currently accepts a `model: str | None` override. The task-routing layer sits above this: callers pass a `task` type, the router resolves it to a provider + model, and `call_llm()` executes. No changes needed to downstream callers for Phase 1.

---

## Open Questions

- [ ] Which models should be in the user-choice menu at launch? Recommendation: GPT-4o and Claude Sonnet only. Opus is too expensive; mini is the default and shouldn't be user-selectable.
- [ ] Should the cap be hard (turns above cap → smart routing) or soft (warning at 80%, hard stop at 100%)?
- [ ] Does the cap reset on calendar month or subscription renewal date? Subscription renewal is cleaner.
- [ ] Should users be able to buy extra premium turns? Not at pre-seed — keep it simple.
- [ ] At what user mix does it make sense to differentiate a "Model Power" tier at $30–35/mo vs. raising the cap? If >15% of Pro users consistently hit the 100-turn cap, revisit.
