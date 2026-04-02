# Sakhi Pricing & Unit Economics Assumptions

> Internal working document. Last updated: 2026-04-02
> Not for distribution. Informs the pre-seed investor deck.

---

## Core Thesis

Sakhi is not a subscription product. It is a compounding system.

Every session makes the model more accurate. Every month of continuity makes switching more costly. Churn destroys the value proposition — so the product is designed to make churn irrational. Retention is not a growth metric here. It is the product.

This shapes every pricing and economics decision below.

---

## Pricing Decision: $20/month Pro

### Why $20

ChatGPT Pro, Claude Pro, and Gemini Advanced are all $20/mo. This is the market-established price for "serious AI I pay for." Sakhi at $12 signals it belongs below them. Sakhi at $20 signals a different category at the same commitment level.

More importantly: $20 is a behavioral signal. A user who pays $20/mo for Sakhi is stating they are committed to building a model of themselves. That commitment is exactly what the product requires to deliver value. Price filters for the right user archetype.

**This is not "what the cost structure supports." This is what commitment to continuity costs.**

**Annual plan: $180/yr (save 25%)**
Annual billing is not a discount play. It is a continuity lock. A user who commits annually is more likely to do the work of building a real model — which is what makes Sakhi valuable for them. The product and the pricing reinforce the same behaviour.

---

## The Moat — Precise Language

Sakhi is building a **proprietary longitudinal model of a person** — not storing memory, but computing evolving states across time.

Three compounding advantages:

**1. Data advantage**
Time-series personal data — thoughts, decisions, patterns, emotional states — accumulated across months and years. This dataset does not exist anywhere. It cannot be bootstrapped by a competitor who arrives late.

**2. System advantage**
Deterministic reasoning layers (Continuity Engine, Life Occupancy, Arc) that compute drift, pattern crystallisation, and attention mapping. These are not prompts. They are engineered inference systems built on top of the raw model.

**3. Switching cost**
Your life model lives in Sakhi. Two years of context, patterns, and arcs cannot be exported meaningfully to a new product. The longer you stay, the more irrational it becomes to leave.

---

## API Cost Structure

Sakhi uses frontier models (GPT-4o or Claude Sonnet) for all quality-sensitive interactions. We do not route substantive reflection tasks to cheaper models — that would compromise the core product.

| Component | Model | Est. cost/user/mo |
|---|---|---|
| Conversational turns (substantive) | GPT-4o / Claude Sonnet | $4–6 |
| Memory retrieval + threading | GPT-4o-mini (retrieval only) | $0.50–1 |
| Deep Reflect (5–10x/mo) | GPT-4o | $1.50–2.50 |
| Arc + Occupancy computation | GPT-4o | $0.50–1 |
| **Total estimated COGS/user** | | **$6.50–10.50** |

**Gross margin at $20:**
- Light user: $20 − $6.50 = **67% margin**
- Regular user: $20 − $8.50 = **57% margin**
- Heavy user: $20 − $10.50 = **47% margin**
- **Blended Year 2 target: 50–65%**

---

## User Interaction Spread

### Archetype 1 — Light User (30% of base)

Checks in 2–3x per week. Occasional reflection. Does not engage Deep Reflect regularly.

| Metric | Estimate |
|---|---|
| Sessions/month | 8–12 |
| Avg tokens/session | ~3,000 |
| Monthly tokens | ~30K |
| Deep Reflect uses | 1–2/mo |
| Est. API cost | $3–5/mo |
| Gross margin | 75–85% |

**Retention risk:** This archetype is at churn risk if passive value (Arc nudges, pattern surfacing) is not strong enough. Product must deliver value between active sessions.

---

### Archetype 2 — Regular User (50% of base)

Uses Sakhi 5–7x per week. Engages Deep Reflect weekly. Core persona: knowledge worker, founder, or caregiver with meaningful mental load.

| Metric | Estimate |
|---|---|
| Sessions/month | 20–28 |
| Avg tokens/session | ~4,000 |
| Monthly tokens | ~100K |
| Deep Reflect uses | 4–6/mo |
| Est. API cost | $6–8/mo |
| Gross margin | 60–70% |

This is the target persona and the median cost assumption. Highest LTV, strongest retention incentive.

---

### Archetype 3 — Power User (20% of base)

Uses Sakhi daily. Long sessions. Uses every feature.

| Metric | Estimate |
|---|---|
| Sessions/month | 40–60 |
| Avg tokens/session | ~6,000 |
| Monthly tokens | ~280K |
| Deep Reflect uses | 10–15/mo |
| Est. API cost | $10–15/mo |
| Gross margin | 25–50% |

### Honest stance on power users

Power users can compress margins at the extremes. This is a real risk, not a "figure it out later" problem. Our position:

**This is intentional and temporary at pre-seed. It becomes controlled by Year 2.**

Power users are the loudest advocates, generate the richest training signal, and have the lowest churn. Subsidising them in Year 1 is a deliberate distribution investment.

By Year 2 we have three levers to address this structurally (see Margin Control Levers below). If the power user mix exceeds 30% of the base, a higher tier ($30–35/mo) is the right response — not cost reduction. These users are getting disproportionate value and will pay for it.

**The risk we are watching:** If early adopters skew heavily toward power users and the lighter tiers do not materialise, Year 1 margins will be 40–50%, not 55–65%. The business still works at $20 — it just requires more disciplined cost management in the first 12 months.

---

## Blended Economics

| Archetype | Mix | Avg cost/mo | Revenue | Margin |
|---|---|---|---|---|
| Light (30%) | 0.30 | $4 | $6 | $6 |
| Regular (50%) | 0.50 | $7 | $10 | $6.50 |
| Power (20%) | 0.20 | $12.50 | $4 | $1.50 |
| **Blended** | | **$7.25** | | **~64%** |

---

## Margin Control Levers

This is not passive. We have four specific levers to manage cost as we scale:

**1. Model routing**
Not every interaction needs GPT-4o. Memory retrieval, simple threading, and short responses route to GPT-4o-mini (~10× cheaper). Target: 40% of total token volume on cheaper models by Month 18 without quality loss.

**2. Caching**
Repeated memory reads (context loading at session start) are expensive and redundant. A caching layer for the top 20% of memory retrievals cuts cost by an estimated 25–30%. Engineering priority in Year 1.

**3. Deep Reflect gating**
Deep Reflect is the most expensive feature. On the free tier it is not available. On Pro it fires on meaningful reflection prompts, not casual chat. Rate logic is already in the architecture.

**4. Tiered pricing evolution**
If a power user tier ($30–35/mo) is warranted by usage data, we introduce it. This is not a fallback — it is a natural evolution. High-engagement users who get high value should pay proportionally.

---

## LTV:CAC Assumptions

| Metric | Value | Basis |
|---|---|---|
| ARPU | $240/yr ($20/mo) | Pro plan, monthly billing |
| CAC | $8–12 | Organic-led: content, community, referral |
| 1-yr LTV:CAC | 20–30× | $240 ÷ $12 and $240 ÷ $8 |
| Target retention | 18–24 months | Structural switching cost by design |
| 2-yr LTV | $480 | Conservative; no expansion revenue |
| 2-yr LTV:CAC | 40–60× | At maturity |

### Honest CAC assessment

$8–12 CAC only holds under specific conditions:

- Founder-led distribution lands (early community, thoughtful positioning)
- Content resonates with the target archetype (knowledge workers who feel the problem)
- Product generates word of mouth from the first cohort

This is realistic for pre-seed but fragile. Investors are right to probe it.

**What changes this:** Paid acquisition in Year 2 will push CAC to $20–40. The model still works — 2-yr LTV of $480 against $40 CAC is 12× — but the pre-seed story depends on not needing paid channels yet.

**What proves it:** First cohort referral rate. If 1 in 5 users refers at least 1 other user organically in Month 1–3, CAC stays in range. This is the metric to track immediately at launch.

---

## Retention: The Most Important Number

Retention is not assumed. It is unproven. This is the most significant risk in the business.

Current status: no live cohort data.

**Why we believe retention will be high:**
- Switching cost is structural: your model lives here, your Arc lives here, your patterns live here
- The product compounds: Month 6 Sakhi is meaningfully better for you than Month 1 Sakhi
- Annual plan filters for committed users who see the value of continuity

**What we are watching for in early cohorts:**
- Day-30 retention as the first signal
- Day-90 retention as the PMF indicator (target: 60%+)
- Session frequency trend — does it increase or decrease after Month 2?
- Deep Reflect engagement — users who use this feature at least 2x/month have the strongest retention hypothesis

Until cohort data exists, retention is an architecture argument, not a proven number. We are building it in as a structural advantage, not relying on engagement tactics.

---

## Growth Trajectory

| Milestone | Paying users | MRR | ARR | Key assumption |
|---|---|---|---|---|
| Month 12 | 2,000 | $40K | $480K | Organic only. Founder community + content. |
| Month 18 | 10,000 | $200K | $2.4M | Content flywheel active. Referral loop established. |
| Month 24 | 50,000 | $1M | $12M | Seed deployed. Growth team in place. |

---

## Three Real Risks (Honest)

**1. Retention is unproven**
The entire unit economics model assumes 18–24 month retention. We do not have cohort data yet. If Day-90 retention is 40% rather than 60%, LTV halves and the business requires either higher pricing or lower CAC to work. This is the number to prove first.

**2. Power user mix risk**
If early adopters skew heavily toward power users (>30% of base), Year 1 gross margins compress to 40–50%. The business still works but requires tighter cost discipline. The mitigation is tiered pricing in Year 2 — but that is a future lever, not a current one.

**3. CAC depends on organic distribution landing**
$8–12 CAC is only achievable with founder-led organic growth. If the first content and community efforts do not generate referral momentum by Month 6, paid acquisition becomes necessary and CAC rises to $25–40. The model still works at that CAC but the pre-seed runway calculation changes.

---

## The Answer to "Why $20 when you depend on OpenAI?"

Three-part answer:

**1. Users are not paying for LLM access.**
They get GPT-4o free or at $20 directly. They are paying for the continuity layer — the longitudinal model of themselves that compounds over time. That is what no LLM provides and what Sakhi is.

**2. The cost structure supports it.**
Frontier model inference costs $6–10/user/mo. $20 yields 50–65% gross margin — healthy for consumer SaaS. Notion AI, Superhuman, and Perplexity Pro run similar structures.

**3. Inference costs are deflationary.**
GPT-4o costs ~40% less than GPT-4 did at launch. In 24 months our COGS per user will likely be $3–5. Margin expands without a price increase.

---

## Open Questions to Resolve Before Seed

- [ ] What is actual Day-90 retention in first cohort? This is the most important number.
- [ ] What is the real power user percentage? If >30%, introduce higher tier before Seed.
- [ ] Does annual plan ($180/yr) convert at 30%+ of Pro users by Month 12?
- [ ] What is the referral rate from first cohort? Validates organic CAC assumption.
- [ ] Fine-tuning timeline: can we reduce frontier model dependency for non-reflection tasks by Month 18?
- [ ] At what usage level does a $30–35/mo power tier make sense?
