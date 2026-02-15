# Voice Commercial Viability Analysis (Realtime Mini vs Realtime Full)

Date: February 15, 2026

## Question
If we want best-in-class voice quality, can we make it commercially viable without passing excessive cost to customers?

## Executive Summary
- Yes, **commercial viability is realistic** with `gpt-realtime-mini` if you package voice with caps, routing, and fallback.
- No, **"unlimited best quality for everyone" is usually not viable** unless price point is very high.
- Market pattern today is consistent:
  - included minutes by plan
  - per-minute overage
  - quality fallback after caps
  - concurrency/usage controls

## What Leading Apps/Platforms Are Doing

### 1) Tiered access + fallback quality
- OpenAI explicitly states ChatGPT voice usage falls back from GPT-4o voice to GPT-4o mini voice when daily GPT-4o usage is exhausted.
- This is a direct example of preserving UX continuity while controlling top-tier spend.

### 2) Included monthly minute buckets
- ElevenLabs lists plan-based included conversational AI minutes (e.g., Free 15 min/month, Starter 50, Creator 100, Pro 250) with overages by provider plus margin.
- This is a classic "bundle + overage" packaging model.

### 3) Usage-metered pricing and pass-through
- Retell documents usage-based billing (voice API, LLM, telephony, etc.) and notes no fixed platform fee (all usage based).
- This model makes margin control a routing problem, not just list-price setting.

### 4) Concurrency + rate controls
- Bland publishes per-minute rates by model and ties higher throughput/concurrency to higher plans.
- This is another strong pattern: monetize peak usage behavior, not only total minutes.

## Cost Model For Sakhi

## Source-backed pricing inputs (OpenAI, Feb 15 2026)
- `gpt-realtime-mini` audio:
  - input: $10 / 1M audio tokens
  - output: $20 / 1M audio tokens
- `gpt-realtime` audio:
  - input: $32 / 1M audio tokens
  - output: $64 / 1M audio tokens
- Audio tokenization (Realtime docs):
  - user audio: ~1 token per 100ms (~600 tokens/min)
  - assistant audio: ~1 token per 50ms (~1200 tokens/min)
- Non-realtime fallback components:
  - `gpt-4o-mini-transcribe`: ~$0.003 / input minute
  - `gpt-4o-mini-tts`: ~$0.015 / output minute

## Formulas
Let `r = assistant_output_minutes / user_input_minutes`.

- Realtime mini cost per input minute:
  - `mini = 0.006 + 0.024*r`
- Realtime full cost per input minute:
  - `full = 0.0192 + 0.0768*r`

Using `r = 0.8`:
- `mini = $0.0252` per input minute
- `full = $0.08064` per input minute

Inference: add ~30% operational headroom (retries, reconnects, silence, orchestration).
- `mini_effective ~= $0.0328 / input min`
- `full_effective ~= $0.1048 / input min`

## Monthly per-user spend scenarios
Profiles:
- Light: 150 input minutes/month
- Medium: 600 input minutes/month
- Heavy: 1,800 input minutes/month

| Profile | Realtime mini (base) | Realtime mini (+30%) | Realtime full (base) | Realtime full (+30%) |
|---|---:|---:|---:|---:|
| Light (150m) | $3.78 | $4.91 | $12.10 | $15.72 |
| Medium (600m) | $15.12 | $19.66 | $48.38 | $62.90 |
| Heavy (1800m) | $45.36 | $58.97 | $145.15 | $188.70 |

## Interpretation
- `gpt-realtime-mini` is manageable at moderate usage.
- `gpt-realtime` should be premium-only or burst-only.
- Cost risk is mostly from heavy users and long live sessions.

## Is Realtime Mini "Too Costly" To Pass Through?
- For broad consumer plans, raw pass-through is rarely the right product strategy.
- Viable strategy is **not** "charge users exactly our backend usage."
- Viable strategy is:
  - bundle realtime minutes into plans
  - enforce caps
  - overage pricing above caps
  - fallback to cheaper voice pipeline past included usage

Inference: this is exactly how major voice products protect gross margin while keeping UX smooth.

## Recommended Sakhi Packaging

### Plan design (example)
| Plan | Monthly Price | Included Realtime Mini | Included Realtime Full | Overage |
|---|---:|---:|---:|---:|
| Core | $19 | 120 min | 0 | Mini: $0.10/min |
| Plus | $39 | 450 min | 0 | Mini: $0.10/min |
| Pro | $99 | 1200 min | 0 (or very limited burst) | Mini: $0.10/min, Full: $0.30/min |

With 30% headroom assumptions:
- Core included-cost ~ $3.93 (voice margin strong)
- Plus included-cost ~ $14.74
- Pro included-cost ~ $39.31

## Quality routing policy
- Default to `gpt-realtime-mini`.
- Allow `gpt-realtime` only for:
  - explicit premium users
  - short, high-value moments (strict daily cap)
- After included minutes:
  - keep conversation going via improved non-realtime voice pipeline
  - do not hard-stop conversation unless abuse/rate limits are hit

## Guardrails Required For Margin Protection
- Session and idle controls:
  - session time cap (Realtime docs: sessions can run up to 60 minutes)
  - automatic idle timeout and disconnect
- Realtime context controls:
  - truncation strategy to limit context growth
  - prompt caching for stable instructions and repeated history prefixes
- Budget controls:
  - per-user daily minute caps
  - org-level daily budget circuit breaker
  - automatic downgrade from full -> mini -> pipeline

## Commercial Decision
- Launch default voice on `gpt-realtime-mini` with packaged minute buckets and overage.
- Reserve `gpt-realtime` for premium tier and tightly capped burst usage.
- Keep improved non-realtime voice as graceful fallback to preserve UX and margin.

This gives high perceived quality, predictable cost, and prevents heavy-user outliers from breaking unit economics.

## Sources
- OpenAI API pricing: https://openai.com/api/pricing/
- OpenAI platform pricing details (realtime + audio): https://platform.openai.com/docs/pricing
- OpenAI Realtime API guide: https://platform.openai.com/docs/guides/realtime
- OpenAI Realtime model pages:
  - https://platform.openai.com/docs/models/gpt-realtime-mini
  - https://platform.openai.com/docs/models/gpt-realtime
- OpenAI Help (ChatGPT voice fallback behavior): https://help.openai.com/en/articles/8400625
- ChatGPT plan matrix: https://chatgpt.com/pricing
- ElevenLabs agents pricing and minute bundles: https://help.elevenlabs.io/hc/en-us/articles/29298065878929-How-much-does-ElevenAgents-cost
- Retell usage-based pricing docs: https://docs.retellai.com/build/telephony/pricing
- Bland rate limit and per-minute model pricing docs: https://docs.bland.ai/welcome/rate-limits-and-pricing
