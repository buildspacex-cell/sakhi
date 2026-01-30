# Voice Integration

Sakhi supports voice conversations using a traditional pipeline: Speech-to-Text → Sakhi Turn API → Text-to-Speech.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  USER SPEAKS                                                │
│  Browser captures audio via MediaRecorder API               │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  /api/voice/turn                                            │
│  1. Receive audio (webm/mp3)                                │
│  2. Transcribe via OpenAI Whisper                           │
│  3. Call /v2/turn with transcript + source: "voice"         │
│  4. Generate TTS with OpenAI (nova voice)                   │
│  5. Return audio + transcript + response text               │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  USER HEARS                                                 │
│  Browser plays audio response                               │
└─────────────────────────────────────────────────────────────┘
```

---

## Components

### 1. useVoice Hook

**File:** `apps/web/lib/hooks/useVoice.ts`

React hook for voice capture and playback.

```typescript
const voice = useVoice({
  personId: "user-uuid",
  autoPlayResponse: true,
  onTranscript: (t) => console.log(t.text),
  onResponse: (r) => console.log(r.text),
  onStateChange: (state) => console.log(state),
  onError: (e) => console.error(e),
});

// States: idle → recording → processing → speaking → idle
voice.startRecording();
voice.stopRecording();
voice.stopPlayback();
```

### 2. Voice Turn API

**File:** `apps/web/app/api/voice/turn/route.ts`

Handles the full voice pipeline.

**Request:** Multipart form data with audio file
- `audio` — Audio blob (webm, mp3, etc.)
- `personId` — User UUID

**Response:**
```json
{
  "transcript": "I've been feeling anxious",
  "text": "That sounds challenging...",
  "audio_url": "data:audio/mp3;base64,..."
}
```

### 3. TTS API

**File:** `apps/web/app/api/voice/tts/route.ts`

Standalone text-to-speech endpoint.

**Request:**
```json
{
  "text": "Hello, how are you?",
  "voice": "default",
  "speed": 1.0
}
```

**Voice Options:**
| Key | OpenAI Voice | Description |
|-----|--------------|-------------|
| `default` | nova | Warm, friendly (Sakhi default) |
| `calm` | shimmer | Soft, calming |
| `energetic` | alloy | Clear, neutral |
| `warm` | nova | Expressive, warm |

**Response:**
```json
{
  "audio_url": "data:audio/mp3;base64,...",
  "text": "Hello, how are you?",
  "voice": "nova"
}
```

---

## UI Integration

### Converse Page

**File:** `apps/web/app/experience/converse/page.tsx`

The voice button shows visual states:

| State | Color | Icon |
|-------|-------|------|
| Idle | Grey | Microphone |
| Recording | Red + pulse | Microphone |
| Processing | Amber + spinner | Spinner |
| Speaking | Green + pulse | Sound waves |

### Source Tracking

Messages are tagged with `source: "voice" | "text"`:
- Stored in `conversation_turns.source` column
- Returned in conversation history
- Voice messages show a small mic icon

---

## Database Schema

```sql
-- Migration: 0041_conversation_turn_source.sql
ALTER TABLE conversation_turns
ADD COLUMN source TEXT DEFAULT 'text';

ALTER TABLE conversation_turns
ADD CONSTRAINT conversation_turns_source_check
CHECK (source IN ('text', 'voice'));
```

---

## Environment Variables

```bash
# Required for voice
OPENAI_API_KEY=sk-...
```

---

## Usage

### From Converse Page
1. Navigate to `/experience/converse`
2. Tap the microphone button
3. Speak your message
4. Release to send (or tap again to stop)
5. Sakhi responds with voice + text

### Programmatic
```typescript
// Start recording
await voice.startRecording();

// Stop and process
await voice.stopRecording();
// → Automatically sends to API
// → Automatically plays response
```

---

## Testing

### Test TTS
```bash
curl -X POST "http://localhost:3000/api/voice/tts" \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello from Sakhi", "voice": "default"}'
```

### Check Source in History
```bash
curl "http://localhost:8000/v2/conversation/history?user=565bdb63-124b-4692-a039-846fddceff90" \
  | jq '.messages[] | {role, source, content}'
```

---

## Future Enhancements

1. **Streaming TTS** — Stream audio chunks for faster response
2. **Full-duplex** — Allow interruptions (NVIDIA PersonaPlex)
3. **Voice activity detection** — Auto-stop on silence
4. **Mobile native** — Native audio capture on iOS/Android

---

## Related Documents

- [Conversation Flow](../architecture/conversation-flow.md) — Turn processing
- [Testing Guide](../guides/testing.md) — Testing instructions
