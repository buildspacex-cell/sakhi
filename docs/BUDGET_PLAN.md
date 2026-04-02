# Sakhi Pre-Seed Budget Plan — $1.25M

> Internal working document. Last updated: 2026-04-02
> Based on 18-month runway from close. Informs the pre-seed investor deck.
> This document captures not just the numbers but the reasoning behind every decision.

---

## Pre-Raise Investment (Founder-Funded)

Before the raise, founders have already deployed **$15,000** of personal capital.

| Category | Est. spend |
|---|---|
| LLC incorporation (state fees + legal) | ~$3K |
| Apple Developer account | ~$0.1K |
| Domain + hosting (early) | ~$0.5K |
| Tool subscriptions (Notion, GitHub, Figma, etc.) | ~$2K |
| API costs (OpenAI, Anthropic — development + testing) | ~$4K |
| Design, assets, early product work | ~$3K |
| Miscellaneous (contractors, legal review) | ~$2.4K |
| **Total founder capital deployed** | **~$15K** |

This is not included in the $1.25M raise. It represents founder skin-in-the-game prior to institutional capital and is a relevant data point in valuation conversations — founders have been building with personal capital before asking for external money.

---

## Raise Target: $1,250,000

### Why $1.25M and not $1M

We stress-tested the budget from the ground up — building every cost line from first principles rather than working backwards from a round number. The true cost of 18 months of execution comes to ~$900K in known costs. The remaining $350K is runway buffer — approximately 8 months of full team burn held in reserve.

We chose $1.25M over $1M for three reasons:

1. **Seed timing buffer.** Pre-seed to Seed typically takes 3–6 months to close after hitting milestones. $350K of buffer means we are never raising from a position of desperation.
2. **Round structure.** We are targeting at least one institutional investor (micro-VC). Institutional investors at pre-seed typically write $250–500K checks. A $1M round with one institutional investor at 50% concentration makes the round harder to fill cleanly. $1.25M gives better structure.
3. **Discipline signal.** Showing $350K of identified runway — not vague "operations" — signals we know our costs precisely. This builds more trust than a tighter ask with less transparency.

We considered $1.5M but decided against it. The additional capital would not be deployed meaningfully in 18 months and would result in unnecessary dilution.

### Round Structure
| Investor type | Check size | Count |
|---|---|---|
| Lead institutional (micro-VC) | $500–750K | 1 |
| Angel syndicate / individual angels | $100–250K each | 2–3 |
| **Total** | **$1.25M** | |

### Instrument: SAFE with Valuation Cap

We chose a SAFE over a priced round for two reasons:
1. A priced round at pre-seed adds $15–25K in additional legal fees with no meaningful benefit to either party.
2. SAFEs are the standard instrument for institutional pre-seed in 2026. Every micro-VC expects it.

Standard terms: valuation cap, MFN clause, pro-rata rights for lead investor.
SAFE legal fees: ~$5K (included in legal budget).

---

## Full Budget at a Glance

| Bucket | Amount | % | One-line summary |
|---|---|---|---|
| People | $350K | 28% | 4 people, 2 geographies, 12–18 months |
| Engineering | $254K | 20% | Infra, AI tools, LLM API, design, QA, equipment, observability, 10% buffer |
| GTM | $171K | 14% | Content, community, creators, paid experiments, marketing tools |
| Legal + Compliance | $75K | 6% | Entity, IP, data privacy, SAFE |
| Operations | $50K | 4% | Payroll, accounting, tools, co-working |
| **Known costs** | **$900K** | **72%** | |
| **Runway + Buffer** | **$350K** | **28%** | ~8 months full team burn in reserve |
| **Total** | **$1.25M** | | |

---

## 1. People — $350K (28%)

### Why this team structure

We debated three configurations:

**Option A — Founders only, no hires**
Maximum runway, minimum burn. Rejected because Continuity Engine V2 + mobile + life signal layer is too much for two people in 18 months even with AI coding tools. The product would ship late and thin.

**Option B — US-based hires**
A senior AI/ML engineer in the US costs $180–220K/yr in salary alone. Two US hires would consume the entire raise on people. Rejected immediately.

**Option C — India-based hires for engineering and growth (chosen)**
Bangalore has world-class AI/ML and engineering talent. A senior AI/ML engineer at ₹50L/yr (~$60K) is top-of-market in Bangalore. This gives us the engineering depth we need at a third of the US cost, preserving capital for product and runway.

### Entity structure decision

**India Private Limited company — not contractor arrangements.**

Three people building core product IP as contractors is a red flag for institutional investors. IP ownership is ambiguous under contractor structures, especially when the contractors are working exclusively for one company full-time. Any serious institutional investor will require clean IP assignment before closing.

India Pvt Ltd removes this risk entirely. Setup cost: ~$2K. Annual compliance: ~$2K/yr. Worth every rupee for the clean cap table and IP story it enables.

**LLC to Delaware C-Corp conversion — required before institutional close.**

Most VCs cannot invest in an LLC. Preferred stock — the standard instrument for VC investment — requires a C-Corp. Our existing LLC must be converted to a Delaware C-Corp before any institutional money closes. Cost: ~$4K. Timeline: 4–6 weeks. This needs to start the moment investor interest is confirmed, not after a term sheet is signed.

### Salary decisions

**CEO — $96K/yr, San Jose, 12 months then revisit**

$96K in San Jose is below market by 40–50%. After California + federal tax, take-home is ~$5,600/mo. Rent for a 1BR is $2,500–3,000/mo. This is survivable — CEO's spouse is salaried, providing household stability. We considered $72K but decided against it: a CEO stressed about rent is a distracted CEO. $96K is the number that keeps the CEO fully focused without being extractive on the raise.

No company health insurance for the CEO — covered by spouse's employer plan. This removes ~$7,200/yr from the budget.

Reviewed at Month 12 based on Seed raise trajectory. Pre-agreed plan if Seed is delayed: extend at current rate from flex budget, or convert excess to equity.

**CTO — $84K/yr (~₹70L gross, ₹4L/month after tax), Bangalore, 12 months then revisit**

₹4L/month after tax is the CTO's stated minimum for 12 months. This is above Bangalore market for a senior engineer (₹40–60L range) but appropriate for a CTO co-founder taking a significant pay cut from a senior IC role. We are not negotiating this number for Year 1 — it is a fixed input in the model.

From Month 13 onwards, the CTO is open to revisiting based on Seed progress. This flexibility is agreed upfront, not assumed.

**Senior AI/ML Engineer — $60K/yr (~₹50L gross), Bangalore, 18 months**

Top of Bangalore market for AI/ML engineering. Equity-supplemented to compensate for the below-global-market cash. 18-month commitment gives stability to the Continuity Engine V2 build.

**Growth Hire — $30K/yr (~₹25L gross), Bangalore, 18 months**

Mid-market for a Bangalore growth/marketing hire. Focused on content production, community building, and first cohort acquisition. This is not a pure paid-acquisition role — it is an organic growth role, which is appropriate for our GTM strategy.

### Statutory costs — India entity

India employees require Provident Fund contributions (12% of basic salary), ESI where applicable, and group health insurance. These are not optional — they are statutory obligations.

| Person | Cash salary (18mo) | PF + statutory (15%) | Health | Total |
|---|---|---|---|---|
| CTO | $84K (12mo) | $12.6K | $0.3K | $96.9K |
| Senior AI/ML | $90K (18mo) | $13.5K | $0.45K | $103.95K |
| Growth hire | $45K (18mo) | $6.75K | $0.45K | $52.2K |
| CEO | $96K (12mo) | — | $0 | $96K |
| **Total** | **$315K** | **$32.85K** | **$1.2K** | **$349.05K** |

Rounded to **$350K** with small buffer for payroll timing differences.

---

## 2. Engineering — $193K (15%)

### The AI-first engineering model

We made a deliberate decision to build AI-first rather than hire-first. In 2026, two strong engineers using Cursor, Claude Code, and GitHub Copilot can realistically ship what previously required four engineers. This is not a hope — it is observable in how modern AI-native teams build.

This means our engineering cost is dominated by tools, infrastructure, API costs, and specialist contractors for design and QA — not headcount. Headcount is in the People budget. Engineering here is everything needed to build the product beyond salaries.

### AI Coding Tools — $7,164

| Tool | Users | Cost/mo | 18-month total | Why |
|---|---|---|---|---|
| Cursor Pro | 2 | $40 each | $1,440 | Primary AI coding environment for CTO + AI/ML engineer. Significant velocity multiplier for boilerplate, refactoring, and test generation. |
| Claude Code (Max plan) | 2 | $100 each | $3,600 | Deep reasoning for architecture decisions, complex debugging, and code review. Complements Cursor for higher-order engineering tasks. |
| GitHub Copilot | 2 | $19 each | $684 | IDE-level autocomplete. Cheap and effective for day-to-day coding velocity. |
| **Total** | | | **$5,724** | |

We are not budgeting AI tools for the Growth hire or CEO at this tier — they use the standard team tools (Claude Pro, ChatGPT Plus) in the operations budget.

### Product Infrastructure — $12,000

| Service | M1–3 avg | M12 | M18 | 18-mo total | Decision |
|---|---|---|---|---|---|
| Railway | $50 | $400 | $1,200 | ~$8K | API hosting. Scales automatically with load. Simple DevOps. Right choice for a 2-engineer team that cannot afford to spend time on infrastructure management. |
| Vercel | $20 | $40 | $40 | ~$650 | Web hosting. Zero-config Next.js deployments. Pro plan needed for custom domains + analytics. |
| Supabase | $25 | $100 | $200 | ~$1,800 | Database + auth + realtime. Pro to Team as user base grows. Chosen over self-managed Postgres because the managed service removes DBA overhead entirely at this stage. |
| Apple Developer | $8 | $8 | $8 | $144 | Required for iOS. Non-negotiable. |
| Google Play | $2 | $2 | $2 | $36 | Required for Android. $25 one-time + minimal monthly. |
| SendGrid | $20 | $35 | $35 | ~$540 | Transactional email — onboarding, notifications, password reset. |
| Sentry | $26 | $26 | $26 | $468 | Error monitoring. Team plan. Essential for a product with complex memory and inference layers where silent failures are a real risk. |
| PostHog | $0 | $50 | $100 | ~$450 | Product analytics. Free until scale, then self-hosted option available to keep costs low. |
| **Total** | | | | **~$12K** | |

### LLM API Costs — $100,000

**Why frontier models only — the quality decision**

We debated using cheaper models (GPT-4o-mini, Haiku) for cost reduction. The answer is no for quality-sensitive tasks.

Sakhi's core value — Deep Reflect, Continuity Arc, pattern surfacing, meaning-making — requires frontier model quality. A shallow reflection from a cheaper model directly destroys the product's reason to exist. Users who pay $20/mo for a "life intelligence" product and receive GPT-4o-mini quality reflections will churn immediately and tell others.

We do use cheaper models for retrieval and threading (non-quality-sensitive tasks) but all substantive interactions use GPT-4o or Claude Sonnet.

**Cost curve with 40% buffer**

We increased the buffer from 30% to 40% after honest assessment of:
- Development and testing token usage (not just production)
- Prompt iteration overhead in early months
- Usage spikes from power users (see PRICING_ECONOMICS.md)
- Faster-than-expected growth scenarios

| Period | Paying users | Base ($7/user/mo) | +40% buffer | Total |
|---|---|---|---|---|
| M1–M3 | 0–200 | ~$2,100 | $840 | $2,940 |
| M4–M6 | 200–500 | ~$8,400 | $3,360 | $11,760 |
| M7–M9 | 500–1,200 | ~$23,100 | $9,240 | $32,340 |
| M10–M12 | 1,200–2,000 | ~$37,800 | $15,120 | $52,920 |
| **Total M1–M12** | | | | **~$100K** |

From Month 12, MRR ($40K) comfortably covers LLM costs ($20K). The raise funds the build phase only. M13–M18 LLM costs are self-funded from revenue.

**App Store revenue cut — critical**

Apple takes 30% of in-app purchases in Year 1, 15% after. If Pro subscriptions go through iOS in-app purchase, $20/mo becomes $14/mo net. At 10,000 paying users, that is $720K of lost ARR annually.

**Decision: web-first subscription flow. This is P0.**

Users download the iOS app for the experience but subscribe through the web. Standard practice (Spotify, Netflix model). Apple allows this — they prohibit directing users to web from within the app, but the web subscription itself is fine. This must be architected from day one, not retrofitted.

### Design Contractor — $29,000

| Item | Cost | Duration | Total |
|---|---|---|---|
| UI/UX contractor (mobile + web) | $4,000/mo | 6 months | $24,000 |
| Brand / motion design (one-time) | — | one-time | $5,000 |
| **Total** | | | **$29,000** |

We considered hiring a full-time designer. At Bangalore rates a competent UI/UX designer costs $24–36K/yr. The contractor model gives us the same output for 6 months at $24K — appropriate for the build phase. Post-launch, design needs reduce significantly as the system design matures.

### QA + Testing — $24,800

| Item | Cost | Duration | Total |
|---|---|---|---|
| QA contractor | $2,000/mo | 6 months | $12,000 |
| BrowserStack (device testing) | $400/mo | 12 months | $4,800 |
| Security pen test (pre-launch) | one-time | — | $8,000 |
| **Total** | | | **$24,800** |

Security pen testing is non-negotiable for a product handling personal data, health data, calendar data, and email data. HealthKit integration in particular will receive scrutiny from Apple during App Store review. Going in with a clean pen test report removes a major approval risk.

**App Store submission risk:** HealthKit integration requires Apple review. Rejection and resubmission can add 4–8 weeks to launch timeline. Build a 6-week review buffer into the mobile launch plan.

### Development Tools + Licences — $5,184

| Tool | Cost/mo | 18-mo total | Why |
|---|---|---|---|
| Expo (React Native) | $99 | $1,782 | Cross-platform mobile development. One codebase for iOS and Android. Correct choice for a 2-engineer team. |
| RevenueCat | $99 | $1,782 | Subscription management across iOS, Android, and web. Handles App Store and Play Store billing complexity so engineers don't have to. Worth every dollar. |
| Cloudflare | $20 | $360 | CDN + DDoS protection + edge caching. Cheap insurance for a product that will have viral moments. |
| AWS S3 | $50 | $900 | Media and asset storage. Cheaper than Supabase storage at scale. |
| ngrok / dev tunnels | $20 | $360 | Local development tunnels for mobile testing and webhook development. |
| **Total** | | | **$5,184** |

### Production Infrastructure Additions — $10,684

World-class production systems require observability, vector storage, job infrastructure, and incident management beyond the basics. These were missing from the original budget.

| Item | Cost/mo | 18-mo total | Priority | Why |
|---|---|---|---|---|
| Datadog / Grafana Cloud | $100 | $1,800 | P0 | APM, log aggregation, LLM latency per user, token usage per request. Flying blind in production is not acceptable. |
| Langfuse / Helicone (LLM observability) | $50 | $900 | P0 | Tracks every LLM call, cost per call, latency, prompt versions. Essential for cost control and quality monitoring. |
| Upstash Redis | $30 | $540 | P0 | Background job queue (RQ workers). Not explicitly budgeted previously. |
| Pinecone / vector DB | $100 | $1,800 | P0 | pgvector inside Postgres becomes a bottleneck at 5,000+ users. Dedicated vector storage for the memory architecture. |
| Uptime monitoring (Better Uptime) | $20 | $360 | P0 | External uptime checks. Sentry does not catch this. |
| Staging environment (Railway) | $20 | $360 | P0 | No world-class production system ships directly from dev to prod. |
| EAS Update / CodePush | $99 | $1,782 | P1 | Over-the-air mobile updates without App Store review cycle. Critical for fixing production bugs fast. |
| PagerDuty / incident.io | $20 | $360 | P1 | On-call alerting and incident management. Who gets paged at 2am? |
| Push notifications (OneSignal) | $99 | $1,782 | P1 | Arc updates, pattern surfacing, Deep Reflect prompts. Required for retention mechanics. |
| k6 load testing | one-time | $100 | P1 | Load test before each major launch. Cheap insurance. |
| Cross-region backup | $50 | $900 | P1 | User memories are irreplaceable. Daily Supabase backup is not enough at 10K users. |
| **Total** | | **$10,684** | | |

### Equipment — $12,100

All engineers require macOS machines. iOS development requires XCode and Apple Simulator — non-negotiable on Mac. Growth hire included.

**Laptops**

| Person | Machine | Cost | Why |
|---|---|---|---|
| CEO (San Jose) | MacBook Pro 14" M4 | $2,000 | Primary work machine |
| CTO (Bangalore) | MacBook Pro 14" M4 | $1,800 (~₹1.5L) | iOS dev requires Mac |
| Senior AI/ML (Bangalore) | MacBook Pro 14" M4 | $1,800 | ML workloads, iOS testing |
| Growth hire (Bangalore) | MacBook Air M3 | $1,200 (~₹1L) | Content, community, analytics |
| **Subtotal** | | **$6,800** | |

**Peripherals (3 engineers, Bangalore)**

| Item | Cost | Why |
|---|---|---|
| External monitors x3 (27" 4K) | $900 | Productivity. Code + design on one screen. |
| Keyboards x2 | $200 | CTO + AI/ML engineer |
| Ergonomic mice x3 | $150 | All 3 Bangalore team |
| USB-C hubs/docks x3 | $300 | Single-cable desk setup |
| **Subtotal** | | **$1,550** |

**Testing devices**

| Item | Cost | Why |
|---|---|---|
| iPhone 15 | $700 | Real device testing. HealthKit, push notifications, and memory-intensive features behave differently on physical hardware vs simulator. |
| iPhone 13 | $400 | Backward compatibility testing on older iOS |
| Samsung Galaxy S23 / Pixel 8 | $400 | Android physical device for push notification and background processing testing |
| **Subtotal** | | **$1,500** |

**Bangalore workspace**

| Item | Cost | Why |
|---|---|---|
| Dedicated high-speed internet (office) | $100/mo x18 = $1,800 | Video calls, LLM API traffic, large model downloads. Home internet in Bangalore is unreliable for production work. |
| NAS + backup drive | $300 | Local development backup. Cheap insurance. |
| **Subtotal** | | **$2,100** |

**Software licences**

| Item | Cost | Why |
|---|---|---|
| Proxyman (iOS network debugging) | $100 | Essential for debugging HealthKit and API calls on physical device |
| Miscellaneous dev tools | $50 | |
| **Subtotal** | | **$150** |

**Equipment Total: $12,100**

### Engineering Contingency — $30,000

Increased from $15K to $30K to absorb:
- Specialist input for technical spikes (vector DB optimisation, memory architecture review, mobile performance profiling)
- Engineering time for GDPR deletion pipeline (2–4 weeks of work not explicitly scoped)
- Engineering time for disaster recovery implementation
- Engineering time for ML data pipeline and training signal capture
- Any unexpected re-architecture needs in the Continuity Engine

### Engineering Total

| Category | Total |
|---|---|
| AI coding tools | $7,164 |
| Product infrastructure | $12,000 |
| LLM API costs (M1–M12, 40% buffer) | $100,000 |
| Design contractor | $29,000 |
| QA + testing | $24,800 |
| Dev tools + licences | $5,184 |
| Production infrastructure additions | $10,684 |
| Equipment | $12,100 |
| Engineering contingency | $30,000 |
| **10% engineering buffer** | **$23,093** |
| **Total** | **$254,025** |

The 10% buffer accounts for scope creep, underestimated complexity in the Continuity Engine V2, unexpected third-party integration costs, and the general reality that engineering projects run over. Better to have it in the engineering line than to raid the runway buffer for predictable overruns.

---

## 3. GTM — $171K (14%)

### The organic-first decision

We chose organic-led growth over paid acquisition for pre-seed for three reasons:

1. **CAC validation.** We do not yet know which channels convert. Spending heavily on paid acquisition before knowing this burns money without signal. Organic content and community generates signal cheaply.
2. **Product fit signal.** If organic content resonates, it proves the positioning lands. If it doesn't, we have a positioning problem that paid acquisition would mask, not solve.
3. **The target persona responds to organic.** Knowledge workers, founders, and caregivers — the people who feel Sakhi's problem most acutely — discover products through thoughtful content and peer recommendation, not ads.

**Why 14% and not 8%:** GTM is the rate-limiting step between a product that works and a product that grows. Under-investing in distribution at pre-seed is one of the most common ways good products die quietly. $171K gives us real budget for creator partnerships, a full marketing tool stack, and meaningful paid experiments — not just a symbolic allocation. The full channel-by-channel plan is in MARKETING_PLAN.md.

| Activity | Budget | Notes |
|---|---|---|
| First cohort acquisition | $20K | Referral program, early access, waitlist seeding |
| Content production + SEO | $30K | Long-form essays, founder voice, freelance support, video |
| Community building | $15K | Events, early access program, community sponsorships |
| Creator partnerships | $20K | 6–8 niche partnerships (productivity, PKM, founders) |
| PR + press | $10K | One targeted launch push, journalist outreach |
| Paid experiments (M6+) | $20K | Meta, Google Search, Twitter — validate CAC before scaling |
| Marketing AI tools (18mo) | $19K | Ahrefs, Surfer SEO, Descript, HeyGen, Clay, Modash, etc. |
| Referral program | $5K | Infrastructure + rewards (extended memory window mechanic) |
| ASO | $2K | App Store + Play Store optimisation |
| Buffer | $30K | Opportunistic spend, channel pivots if needed |
| **Total** | **$171K** | |

---

## 4. Legal + Compliance — $75K (6%)

Legal looks high for a pre-seed. It is high — and completely justified. Sakhi touches more regulated data surfaces than almost any consumer pre-seed product: health data (HealthKit), email, calendar, personal conversations, and cross-border employment. Getting this wrong costs more than $75K to fix.

| Item | Cost | Why |
|---|---|---|
| LLC to Delaware C-Corp conversion | $4K | Required before institutional close. Most VCs cannot invest in an LLC. |
| India Private Limited setup | $2K | Required for clean IP ownership on Bangalore-built product. |
| India entity annual compliance | $3K | CA + statutory filings over 18 months. |
| IP assignment (founders to company) | $2K | All pre-incorporation IP formally assigned to the C-Corp. Critical before any money closes. |
| SAFE legal fees | $5K | Document preparation and review. Standard pre-seed instrument. |
| Privacy policy + terms of service | $8K | Specialist privacy counsel. Cannot use generic templates for a product with this data profile. |
| GDPR compliance | $12K | EU data handling, right to erasure, data processing agreements. |
| CCPA compliance | $8K | California-specific. CEO is California-based. Applies. |
| Apple HealthKit data policy | $10K | Required for App Store approval. Apple reviews health data handling rigorously. |
| Email + calendar data policies | $10K | Google and Microsoft OAuth scope compliance. Required for Gmail and calendar integrations. |
| Founder agreements + employment contracts | $5K | Clean documentation for both founders and India employees. |
| Legal buffer | $6K | Unexpected issues — Apple rejection response, regulatory query, investor diligence requests. |
| **Total** | **$75K** | |

---

## 5. Operations — $50K (4%)

The unsexy costs that are nonetheless real.

### Team Operational Tools — 4 people, 18 months — $8,370

| Tool | Plan | Cost/mo | 18-mo total | Why |
|---|---|---|---|---|
| Claude Pro | Pro x4 | $80 | $1,440 | Primary AI assistant for all team members. Non-negotiable for a company building on top of LLMs. |
| ChatGPT Plus | Plus x4 | $80 | $1,440 | Secondary model access. Different strengths from Claude. Research, content, cross-checking. |
| Notion | Plus x4 | $64 | $1,152 | Docs, planning, knowledge base. Already in use. |
| Zoom (AI Companion) | Pro x4 | $60 | $1,080 | Investor calls, team sync, async summaries. AI companion for meeting notes. |
| GitHub | Team | $16 | $288 | Code hosting. |
| Linear | Startup | $32 | $576 | Issue tracking. Better than Jira for a small technical team. |
| Figma | Professional x2 | $60 | $1,080 | Design. CEO + design contractor. |
| Slack | Pro x4 | $28 | $504 | Team comms. |
| 1Password | Teams | $20 | $360 | Credential management. Non-negotiable for a privacy-first product. |
| Loom | Business x2 | $25 | $450 | Async video for team communication and investor updates. |
| **Total** | | | **$8,370** | |

### Payroll + Accounting — $12,190

| Item | Cost | 18-mo total | Why |
|---|---|---|---|
| US payroll (Gusto) | $55/mo | $990 | CEO payroll processing. Required for US employment compliance. |
| India payroll + wire transfers | $100/mo | $1,800 | Monthly salary transfers + compliance. |
| Bookkeeping (US) | $300/mo | $5,400 | Monthly reconciliation, expense tracking. Essential from day one for clean books at Seed. |
| US corporate tax filing | one-time | $2,500 | Annual C-Corp filing. |
| India CA + statutory compliance | one-time | $1,500 | Annual India entity filings. |
| **Total** | | **$12,190** | |

### Bangalore Co-working — $5,400

3 desks at ~$100/desk/month over 18 months. CTO + 2 hires working in the same space is worth more than the cost — collaboration, accountability, and culture cannot be replicated over Slack.

### Customer Support Tooling — $1,800

Intercom or Crisp from approximately Month 9 when paying user base reaches 500+. $100/mo x 18 months, starting mid-year. Earlier than needed is fine, but not before product has stabilised.

### Operations Total — ~$28K

Buffer to $50K absorbs: unexpected travel for investor meetings, one-off equipment purchases (testing devices, monitors for Bangalore team), emergency operational needs.

---

## 6. Runway + Buffer — $350K (28%)

This is not waste. This is the most important line in the budget.

**What $350K buys:**
- ~8 months of full team burn held in reserve
- 3–5 months of Seed raise process without pressure
- Ability to scale GTM spend if a paid channel proves out at Month 6–8
- Ability to bring forward a third Bangalore hire (Android, ~$45K for 9 months) if iOS traction demands it
- Buffer for LLM costs if growth exceeds plan by 2x

**Why this is the right buffer size:**
We stress-tested going lower ($100K) and rejected it. $100K = 3 months of people + ops burn. If Seed takes 4 months to close or any one cost line runs over, $100K does not survive contact with reality. $350K gives genuine optionality. Reducing the buffer further to reach a round $1M number is not a sound reason to increase execution risk.

**Why this builds investor confidence:**
"We know exactly what we're spending and have 8 months of buffer" is a stronger signal than a tight budget with no slack. It says: we are not raising because we are desperate, we are raising to execute a plan we have already stress-tested.

---

## Self-Funding Timeline

| Month | MRR | Monthly burn (excl. people) | Net |
|---|---|---|---|
| M6 | $5K | $8K | -$3K |
| M9 | $16K | $13K | +$3K |
| M12 | $40K | $22K | +$18K |
| M18 | $200K | $100K | +$100K |

From Month 9, revenue covers all non-people operational costs. People costs (salaries) are covered by the raise through Month 12 for CEO/CTO and Month 18 for Bangalore hires.

---

## Investor Q&A Prep

**Q: What does $254K of engineering buy that your existing team can't deliver?**

Three specific workstreams that require dedicated build time beyond what two founders can ship while also running the company: Continuity Engine V2 (the core memory and inference architecture), iOS with HealthKit integration (a full mobile product requiring separate QA and App Store process), and the life signal layer (HealthKit, calendar, email — three separate OAuth and API integrations each with their own compliance requirements). Without dedicated engineering budget these ship 6–9 months late. The $254K includes a 10% buffer and full observability stack — not a plug number.

**Q: GTM is 14% — more than most pre-seeds allocate. Why?**

GTM is the rate-limiting step between a product that works and a product that grows. $171K gives us creator partnerships, a full AI-powered marketing tool stack, paid experiments after Month 6, and a referral program — not just organic hope. The detailed channel plan with CAC targets by channel is in MARKETING_PLAN.md. Month 6 is the decision point: if channels are underperforming, the $350K buffer gives us room to pivot without panic.

**Q: Why is legal so high at $75K?**

Sakhi touches more regulated data than almost any consumer pre-seed: health data, email, calendar, personal conversations, cross-border employment. The alternative — cutting legal corners — costs multiples of $75K to fix post-raise and creates IP and App Store approval risk that could kill the product before it launches.

**Q: People is 28% — seems high for a pre-seed.**

It is four people across two geographies with India statutory obligations included. The Bangalore hires are at market rates for India, not US rates. Without India-based hires this number would be $600K+. The structure is efficient — we have the engineering depth of a 4-person team at the cost of a 2-person US team.

---

## Key Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| App Store 30% cut if web-first not implemented | High if not prioritised | $720K ARR loss at scale | Web-first subscription is P0 from day one |
| LLM costs at 2.5x growth | Medium | $45K/mo by M12 | 40% buffer + flex budget absorbs through M14 |
| C-Corp conversion delay | Low | Blocks institutional close | Start conversion immediately on investor interest |
| India entity setup delay | Low | IP risk, blocks close | Run parallel to C-Corp conversion |
| CEO/CTO salary revision at M12 | Medium | Team stability | Pre-agreed plan in writing before clock starts |
| Organic GTM stalls by M6 | Medium | CAC assumption breaks | $30K GTM buffer + $350K runway available to pivot to paid |
| Power user LLM cost concentration | Medium | Year 1 margin compression | 40% buffer + tiered pricing in Year 2 |
| Apple HealthKit App Store rejection | Medium | 4–8 week delay | Security pen test + legal review before submission |

---

## Open Questions

- [ ] Pre-money valuation target for the $1.25M raise
- [ ] Founder equity split and ESOP pool size (typically 10–15% pre-raise)
- [ ] SAFE valuation cap — what number reflects current traction and market?
- [ ] C-Corp conversion: start immediately or wait for first investor commitment?
- [ ] India entity: who is the India-side director? CTO or a nominee director?
- [ ] Web-first subscription: confirmed as P0 before iOS launch?
- [ ] Does the CTO handle all backend + AI + mobile, or do we need a dedicated mobile contractor earlier?
- [ ] Growth hire profile: pure growth/marketing or technical growth (SEO, product analytics)?
- [ ] Founder equity vesting schedule: standard 4-year/1-year cliff?
