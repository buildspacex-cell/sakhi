# ChatGPT-Style Voice Rollout Plan (Main Branch)

## Objective
Ship low-latency, interruptible, natural voice conversation in `main`, while preserving Sakhi's existing `/v2/turn` intelligence and keeping spend predictable.

## Current Baseline In This Repo
- `apps/web/lib/hooks/useVoice.ts`: push-to-talk recorder (`MediaRecorder`) with stop-to-send.
- `apps/web/app/api/voice/turn/route.ts`: `whisper-1` STT -> `/v2/turn` -> `tts-1` audio, returned as base64.
- `apps/web/app/api/voice/tts/route.ts`: standalone TTS endpoint.
- `apps/web/app/experience/converse/page.tsx`: voice integrated in existing chat UI.

Current behavior is reliable but half-duplex. It does not feel like ChatGPT Voice because first response audio starts only after full STT + full LLM + full TTS complete.

## Option Analysis
| Option | UX Fit vs ChatGPT Voice | Engineering Complexity | Unit Cost | Recommended Use |
|---|---|---:|---:|---|
| A. Improve existing pipeline (streaming STT/TTS, VAD) | Medium | Medium | Lowest | Cost-first rollout |
| B. OpenAI Realtime `gpt-realtime-mini` + tool bridge to `/v2/turn` | High | Medium-High | Medium | Best balance (recommended) |
| C. OpenAI Realtime `gpt-realtime` end-to-end | Highest | Medium | Highest | Premium tier only |

## Recommended Architecture (Option B)
Use OpenAI Realtime over WebRTC for conversational feel, but keep Sakhi reasoning in `/v2/turn`.

### High-level flow
1. Client requests ephemeral realtime session token from backend.
2. Client opens WebRTC connection directly to OpenAI Realtime.
3. Realtime model handles speech turn-taking and interruptions.
4. Model calls a tool (`sakhi_turn`) for semantic response generation.
5. Tool executor calls existing `/v2/turn` with `source="voice"`.
6. Tool result is returned to realtime session.
7. Realtime model speaks response audio immediately.
8. Transcripts + state are persisted through existing Sakhi pathways.
9. If realtime fails, automatically fall back to current `/api/voice/turn`.

### Why this fits Sakhi
- Keeps current memory/context/personalization investment in `sakhi/apps/api/routes/turn_v2.py`.
- Adds real-time conversational UX without rewriting core intelligence.
- Maintains graceful fallback to today's stable pipeline.

## Implementation Plan

### Phase 0: Foundations (2-3 days)
- Add feature flags:
  - `VOICE_MODE=pipeline|realtime_mini|realtime_full`
  - `VOICE_REALTIME_ENABLED=true|false`
- Add spend guardrails:
  - per-user daily minute cap
  - org-level daily budget cap
- Add telemetry schema:
  - `voice_session_started`, `voice_first_audio_ms`, `voice_interrupt_count`, `voice_fallback_count`, `voice_cost_estimate_usd`.

### Phase 1: Web Realtime MVP (5-7 days)
- New frontend hook: `apps/web/lib/hooks/useRealtimeVoice.ts`.
- New route for ephemeral tokens: `apps/web/app/api/voice/realtime/session/route.ts`.
- Integrate into `apps/web/app/experience/converse/page.tsx` behind feature flag.
- Preserve existing `useVoice` as fallback path.

### Phase 2: Tool Bridge To Sakhi Brain (5-7 days)
- Add secure tool execution layer in API service:
  - `sakhi/apps/api/routes/voice_realtime.py`
  - `sakhi/apps/api/services/voice/realtime_tool_bridge.py`
- Define tool contract:
  - `sakhi_turn({ person_id, text, session_id, conversation_id }) -> { reply, metadata }`
- Enforce auth and per-session ownership checks.

### Phase 3: Hardening + Rollout (5-7 days)
- Add chaos/failure tests (network drop, token expiry, reconnect).
- Add latency SLO dashboards.
- Progressive rollout:
  - internal 5%
  - beta 20%
  - general 100%
- Auto-fallback policy:
  - >2 realtime errors in 60s -> fallback to pipeline for that session.

### Phase 4: Mobile (7-10 days)
- Start with existing Expo audio pipeline parity.
- Introduce realtime path once `react-native-webrtc` stability is validated.
- Keep platform-specific fallback to non-realtime when WebRTC transport degrades.

## Cost Model (USD)
Pricing references are OpenAI official pages, checked on **February 15, 2026**.

### Pricing inputs used
- Realtime mini: input audio ~$0.02/min, output audio ~$0.08/min.
- Realtime full: input audio ~$0.06/min, output audio ~$0.24/min.
- STT fallback:
  - `gpt-4o-mini-transcribe` ~$0.003/min input audio.
- TTS fallback:
  - `gpt-4o-mini-tts` ~$0.015/min output audio.
- Text LLM in current `/v2/turn` path:
  - `gpt-4o-mini` at $0.60/M input tokens and $2.40/M output tokens.

### Assumptions
- Light user: 150 voice-input minutes/month (about 5 min/day).
- Medium user: 600 voice-input minutes/month (about 20 min/day).
- Heavy user: 1,800 voice-input minutes/month (about 60 min/day).
- Assistant output audio is 0.8x user input minutes.
- Pipeline option includes STT + text LLM + TTS.
- Add 20% budget headroom for retries/silence/reconnects.

### Per-user monthly cost
| Profile | A. Pipeline improved | B. Realtime mini | C. Realtime full |
|---|---:|---:|---:|
| Light (150 min) | $2.48 base / $2.97 with 20% headroom | $12.60 / $15.12 | $37.80 / $45.36 |
| Medium (600 min) | $9.90 / $11.88 | $50.40 / $60.48 | $151.20 / $181.44 |
| Heavy (1,800 min) | $29.70 / $35.64 | $151.20 / $181.44 | $453.60 / $544.32 |

### Portfolio budget example (1,000 voice MAU)
Assuming 70% light, 20% medium, 10% heavy:
- A. Pipeline improved: ~$6,682/month base (~$8,019 with headroom).
- B. Realtime mini: ~$34,020/month base (~$40,824 with headroom).
- C. Realtime full: ~$102,060/month base (~$122,472 with headroom).

## Rate-Limit + Capacity Notes
- `gpt-realtime-mini` model page lists high default throughput ceilings (including TPM and RPM), but limits are tier-dependent and must be verified in your OpenAI project before launch.
- Add admission control at session start:
  - reject new realtime sessions when daily spend cap or concurrency cap is reached.
  - automatically route overflow to pipeline mode.

## Risks And Mitigations
- Cost spikes from always-on sessions: enforce idle timeout + minute caps.
- Realtime instability on weak networks: fallback to pipeline after repeated transport errors.
- Security of tool execution: server-side tool bridge, never expose privileged tools to client.
- Behavioral regressions vs current Sakhi tone: run A/B with scripted voice QA sets before 100% rollout.

## Decision Recommendation
Adopt **Option B (`gpt-realtime-mini` + `/v2/turn` tool bridge)** as default for launch.

It is the closest ChatGPT-like experience at materially lower cost than full realtime, while preserving Sakhi's current intelligence stack and providing a safe fallback path.

## Source Links
- OpenAI Pricing: https://openai.com/api/pricing/
- Realtime API docs: https://platform.openai.com/docs/guides/realtime
- Realtime with WebRTC: https://platform.openai.com/docs/guides/realtime-webrtc
- Realtime model page (`gpt-realtime-mini`): https://platform.openai.com/docs/models/gpt-realtime-mini
- Realtime model page (`gpt-realtime`): https://platform.openai.com/docs/models/gpt-realtime
- Audio generation/transcription pricing details: https://platform.openai.com/docs/pricing#audio-generation
