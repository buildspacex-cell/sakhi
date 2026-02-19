# Kala

> काल — Sanskrit for *time*

**Temporal intelligence for AI agents.**

Your AI doesn't need more data. It needs a sense of time.

---

Kala gives AI systems the temporal primitives that living systems use to stay coherent: memory that decays and consolidates, state that drifts and recovers, signals that accumulate into patterns, and awareness that knows what matters right now.

```
pip install kala
```

---

## Why Kala Exists

RAG solved "what does the AI know?" but not "what has changed?"

When your agent talks to a customer on Monday and again on Friday, it doesn't notice the mood shift. When your automation runs a 5-step workflow over 3 days, it loses context between steps. When your copilot helps someone daily for a month, it can't detect that they're burning out.

The problem isn't retrieval. The problem is that AI has no sense of time.

Kala solves this by extracting the temporal primitives from biological systems — rhythms, homeostasis, drift, accumulation, consolidation — and making them available as a developer library.

**Origin:** Extracted from [Sakhi](https://github.com/anthropics/sakhi), a personal wellness AI that needed to understand people over months, not moments. The temporal layer turned out to be domain-agnostic.

---

## Quick Start

```python
import kala

engine = kala.Engine(database_url="postgresql://...")
entity = await engine.entity("user-123")

# Set a baseline — what "normal" looks like
await entity.set_baseline({"energy": 0.7, "focus": 0.6, "stress": 0.3})

# Record observations over time
await entity.observe("Felt scattered today, couldn't focus")
await entity.observe("Great workout but still anxious about the deadline")

# How far have they drifted from their baseline?
drift = await entity.drift()
# DriftResult(percentage=28, severity="moderate", primary="focus", direction="depleted")

# Get temporal context for your LLM call
context = await entity.context("How should I prioritize today?")
```

---

## Five Modules

| Module | Biological Analog | What It Does |
|---|---|---|
| **Memory** | How living systems remember | Tiered memory (STM → episodic → LTM) with temporal decay, hybrid recall, associative graph |
| **State** | How living systems maintain identity | Baseline vs current deviation, N-dimensional drift detection, cause-effect pattern learning |
| **Signals** | How living systems sense the environment | Event accumulation, cadence detection, trend analysis, capacity/load scoring |
| **Awareness** | How living systems pay attention | Context routing (what's relevant now), temporal context assembly for LLM calls |
| **Timeline** | How you prove it works | Time-travel simulation, persona-based testing, state snapshots, temporal assertions |

---

## Documentation

| Document | What's Inside |
|---|---|
| [VISION.md](VISION.md) | Name, positioning, origin story, competitive differentiation, design principles |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Module structure, every primitive with parameters and formulas, extraction map from Sakhi |
| [API_DESIGN.md](API_DESIGN.md) | Developer experience, full API surface, code examples, domain examples, configuration |
| [BUSINESS_STRATEGY.md](BUSINESS_STRATEGY.md) | Why proprietary (not open-source), monetization model, go-to-market, distribution strategy |

---

## How It Compares

| | RAG / Vector DB | Memory Layer | **Kala** |
|---|---|---|---|
| Store + retrieve | Yes | Yes | Yes |
| Temporal decay | No | Partial | **Configurable half-life** |
| Drift detection | No | No | **N-dimensional** |
| Pattern learning | No | No | **Cause-effect with confidence** |
| Multi-source fusion | No | No | **Weighted with confidence** |
| Time-travel testing | No | No | **Built-in** |

**RAG gives AI knowledge. Kala gives AI time.**

---

## Status

**Phase: Design & Extraction**

Kala's primitives are currently running in production inside Sakhi. This documentation defines the extraction plan — separating the domain-agnostic temporal layer from Sakhi's wellness-specific implementation.

**Distribution: Proprietary with strategic openness.** See [BUSINESS_STRATEGY.md](BUSINESS_STRATEGY.md) for the full reasoning. Short version: the value is the primitives, not the hosting. Open-source Timeline module as a Trojan horse; keep the core proprietary; free tier for developers, paid for production.

### Next Steps

1. Define and stabilize the API surface (this document)
2. Extract core primitives from Sakhi into standalone package
3. Implement PostgreSQL storage backend with clean schema
4. Build test suite using Timeline module (dog-fooding the simulation harness)
5. Open-source Timeline module separately (awareness + gateway)
6. Launch free tier (`pip install kala`)
7. Find 3-5 design partners across domains

---

*Last updated: 2026-02-20*
