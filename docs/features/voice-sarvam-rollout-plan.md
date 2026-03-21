# Sarvam Voice Rollout Plan

## Objective

Adopt Sarvam as the voice input/output layer for Sakhi while keeping Sakhi's existing `/v2/turn` intelligence, continuity, memory, and prompt behavior unchanged.

This is an India-first multilingual voice plan:
- Sarvam handles speech-to-text
- Sakhi `/v2/turn` remains the reasoning layer
- Sarvam handles text-to-speech where language support exists

## Decision Summary

We are choosing **Sarvam for now** as the voice provider for both web and mobile.

Why:
- better fit for Indian languages and code-mixed speech
- solves the current English-first web voice limitation
- lets us keep Sakhi's current conversation engine intact
- lower-risk than changing core chat or continuity logic

## Current Repo Baseline

### Web

Current live web voice path:
- `apps/web/app/api/voice/turn/route.ts`
- `apps/web/app/api/voice/tts/route.ts`
- `apps/web/lib/hooks/useVoice.ts`
- `apps/web/app/experience/voice/page.tsx`

Current behavior:
- browser records audio with `MediaRecorder`
- web `POST /api/voice/turn` sends audio to OpenAI Whisper
- transcript is sent to Sakhi `/v2/turn`
- reply is synthesized with OpenAI TTS

Known limitation:
- STT is currently hardcoded to English via `language: "en"` in `apps/web/app/api/voice/turn/route.ts`

### Mobile

Current mobile reality:
- `expo-av` is installed in `apps/mobile/package.json`
- there is no active mobile voice runtime in the current MVP path
- the old dedicated mobile voice screen is not part of the live MVP runtime

This means mobile voice should be reintroduced only after the shared backend voice layer is in place.

## Product Principles

1. Voice is an input/output transport layer only.
2. Sakhi `/v2/turn` remains the brain.
3. Continuity, memory, prompt behavior, and auth binding must not change.
4. Voice turns should still be stored as normal turns with `source="voice"`.
5. Backend should own provider credentials and language logic.
6. Mobile app must not call Sarvam directly with secret keys.

## Recommended Architecture

### Shared Backend Voice Layer

Add a backend-owned voice service under the FastAPI app:

- `sakhi/apps/api/routes/voice.py`
- `sakhi/apps/api/services/voice/__init__.py`
- `sakhi/apps/api/services/voice/service.py`
- `sakhi/apps/api/services/voice/providers/sarvam.py`

Recommended endpoints:
- `POST /voice/stt`
- `POST /voice/tts`
- `POST /voice/turn`

### Canonical Voice Flow

1. Client records audio
2. Client sends audio to backend `POST /voice/turn`
3. Backend transcribes with Sarvam STT
4. Backend calls Sakhi `/v2/turn` with `source="voice"`
5. Backend synthesizes Sakhi's reply with Sarvam TTS when supported
6. Backend returns:
   - transcript
   - detected language
   - Sakhi reply text
   - optional audio payload or audio URL

## Language Support Policy

We should not assume STT and TTS support are symmetric.

Policy:
- use Sarvam STT with automatic language detection
- use Sarvam TTS only when the reply language is supported
- if STT succeeds but TTS is unavailable for that language, return text normally and skip spoken output

Required UX behavior:
- do not fail the turn if TTS is unavailable
- show transcript + Sakhi text reply
- surface a small message like: `Audio reply unavailable for this language`

## Web Rollout Plan

### Phase 1: Backend Unification

Goal:
- move voice provider logic out of Next routes and into the Python backend

Changes:
- keep `apps/web/app/api/voice/turn/route.ts` and `apps/web/app/api/voice/tts/route.ts` as thin authenticated proxy routes
- remove provider-specific STT/TTS logic from Next
- proxy web voice requests to backend `/voice/*`

Result:
- one voice stack for web and mobile
- no duplication of provider logic

### Phase 2: Web Voice Contract Upgrade

Update the web response contract to include:
- `transcript`
- `reply`
- `audio_url` or `audio_base64`
- `language_detected`
- `tts_available`

Web files affected:
- `apps/web/app/api/voice/turn/route.ts`
- `apps/web/app/api/voice/tts/route.ts`
- `apps/web/lib/hooks/useVoice.ts`

### Phase 3: Web UI Controls

Add or expand web voice settings:
- language mode: `auto` or `fixed`
- voice/speaker
- speed
- auto-play

UI surface:
- `apps/web/app/experience/voice/page.tsx`

### Phase 4: Web QA

Minimum QA set:
- English
- Hindi
- Hinglish
- Tamil/English code-mix
- Marathi/Hindi code-mix

Verify:
- STT accuracy
- language detection correctness
- TTS availability behavior
- transcript and reply persistence
- no change to normal Sakhi turn quality

## Mobile Rollout Plan

### Phase 1: Do Not Revive the Old Screen

Do not restore a separate dedicated voice mode first.

Instead:
- add voice directly into the current chat experience
- keep voice and text in the same conversation thread

Primary target:
- `apps/mobile/app/experience/converse/index.tsx`

### Phase 2: Mobile Voice Hook

Add a mobile voice hook:
- `apps/mobile/hooks/useVoice.ts`

Responsibilities:
- record audio using Expo AV
- send multipart audio to backend `POST /voice/turn`
- receive transcript, Sakhi reply, and optional audio
- play audio response in-app

### Phase 3: Mobile UI Integration

Add a microphone entry point near the existing message composer in:
- `apps/mobile/app/experience/converse/index.tsx`

Behavior:
- voice input should create a normal user turn
- Sakhi response should appear in the same thread
- spoken playback should be optional, not mandatory

### Phase 4: Mobile Voice Settings

Add voice preferences to the current settings model:
- auto-play voice replies
- preferred speaker
- language mode if needed

Settings surface:
- `apps/mobile/app/account/settings.tsx`

### Phase 5: Mobile QA

Verify:
- recording permissions
- upload stability on mobile networks
- audio playback behavior
- text fallback when TTS is unavailable
- continuity/history unaffected by `source="voice"` turns

## Backend Contract Notes

### `POST /voice/turn`

Recommended request shape:
- multipart audio file
- authenticated user context
- optional voice settings

Recommended response shape:

```json
{
  "transcript": "user transcript",
  "reply": "sakhi response",
  "language_detected": "hi-IN",
  "tts_available": true,
  "audio_url": "data:audio/mp3;base64,..."
}
```

### Auth Rules

- backend resolves person context from the authenticated principal
- do not trust arbitrary client `person_id`
- keep the same user-binding rules used by normal chat/data routes

## Non-Goals For Phase 1

Do not do these in the first rollout:
- realtime full-duplex conversation
- interruptible streaming voice
- separate mobile voice mode
- any change to `/v2/turn` prompts or logic
- any change to continuity or reflection behavior
- direct Sarvam calls from the mobile client

## Rollout Order

1. backend Sarvam adapter + `/voice/*` routes
2. web proxy migration
3. web QA
4. mobile voice-in-chat
5. mobile QA
6. optional streaming/realtime later

## Build And Release Note

For mobile release instructions:
- we do **not** use Expo/EAS build for iOS release
- the canonical iOS/TestFlight path is `./scripts/ios-build.sh`
- that script runs the Fastlane release path

This matters for any future mobile voice rollout because production iOS shipping should follow the same Fastlane path already documented in `docs/guides/production-launch.md`

## Success Criteria

Web:
- multilingual STT works through Sarvam
- Sakhi replies remain unchanged in quality
- unsupported TTS languages degrade gracefully to text-only

Mobile:
- voice works inside the existing chat thread
- no separate voice-only UX is required for MVP
- no change to auth, memory, continuity, or turn routing

## Open Questions

1. Which Sarvam voices should map to Sakhi's brand tone on web and mobile?
2. Do we want a single auto-detect language mode only, or both `auto` and `fixed`?
3. Should unsupported TTS fall back to text-only always, or optionally to a default spoken language later?
4. Do we want to keep the separate web `/experience/voice` page after voice-in-chat is good enough?

## Official Sarvam References

- STT overview: https://docs.sarvam.ai/api-reference-docs/api-guides-tutorials/speech-to-text/overview
- TTS overview: https://docs.sarvam.ai/api-reference-docs/api-guides-tutorials/text-to-speech/overview
- Bulbul model docs: https://docs.sarvam.ai/api-reference-docs/getting-started/models/bulbul
- Pricing: https://www.sarvam.ai/api-pricing
