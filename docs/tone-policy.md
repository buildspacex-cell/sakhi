# 🌿 Sakhi Conversation Tone System

> _“Sakhi listens like a friend, responds like a guide.”_  
> This document explains how Sakhi’s **emotion-aware tone system** works,  
> how product/design can **edit tones without touching code**,  
> and how to **test changes live**.

---

## 🧭 System Overview

Sakhi’s conversational tone runs through **three cooperative layers**:

| Layer | Owner | Purpose |
|--------|--------|----------|
| **1. Detection** | LLM / Sentiment model | Detects mood (`tired`, `excited`, `anxious`, …) |
| **2. Policy Mapping** | `conversation.yaml` | Maps each mood → short, safe acknowledgement |
| **3. Polishing (optional)** | LLM rephraser | Softens or warms phrasing if needed |

This hybrid keeps Sakhi **emotionally intelligent yet consistent** — every message sounds calm, caring, and “Sakhi-like.”

---

## 🔁 Runtime Flow

User message
↓
Emotion detection (LLM)
↓
Alias normalization (ack.py)
↓
Policy lookup (conversation.yaml)
↓
Optional LLM polish (rephrase_ack_llm)
↓
Final assistant message

yaml
Copy code

Example:

| User says | Detected emotion | YAML key used | Sakhi responds |
|------------|------------------|---------------|----------------|
| “I’m so drained today.” | `tired` | `ack_tones.tired` | “Rest a bit — we’ll pace this together.” |
| “Super excited for the weekend!” | `excited` | `ack_tones.excited` | “Love that energy — let’s channel it well!” |
| “I’m a bit unsure about my plans.” | `uncertain` | `ack_tones.uncertain` | “It’s okay not to be sure yet.” |

---

## 🎨 Editing Tone Templates

All acknowledgement lines live in:

sakhi/libs/policy/conversation.yaml

yaml
Copy code

### Example section

```yaml
ack_templates:
  neutral: "Got it."
  heavy: "Heard. Let’s take it one step at a time."
  positive: "Nice. Let’s line it up."

ack_tones:
  tired: "Rest a bit — we’ll pace this together."
  uncertain: "It’s okay not to be sure yet."
  excited: "Love that energy — let’s channel it well!"
  calm: "Alright, steady and easy."
  anxious: "No rush, let’s take it slow."
  grateful: "That’s lovely — thank you for sharing."
  reflective: "Makes sense. Let’s stay with that thought for a bit."
  motivated: "Great momentum — let’s build on that."
  overwhelmed: "Got you. We’ll simplify things one step at a time."

flags:
  ack_llm_rephrase: true
✅ Design guidelines

≤ 12 words, no emojis.

Calm > cheerful. Support > sympathy.

Every line should feel like a pause, not a pitch.

🧠 Emotion Alias Map
Raw emotions from the model are normalized before lookup.
Aliases live in sakhi/libs/conversation/ack.py:

Raw model label	Alias →	YAML key
drained, exhausted	→ tired	ack_tones.tired
stressed, worried	→ anxious	ack_tones.anxious
energetic, motivated	→ excited	ack_tones.excited
unsure, lost	→ uncertain	ack_tones.uncertain
peaceful, relaxed	→ calm	ack_tones.calm
content, joyful	→ positive	ack_templates.positive

Designers normally don’t edit this file — it just ensures new detector outputs always map cleanly.

💬 Optional LLM Rephrase
If:

emotion ∈ {heavy, tired, anxious}

or user profile prefers “warm” tone

then Sakhi gently rephrases the YAML line for smoothness.

Example:

Policy: “Heard. Let’s take it one step at a time.”
Rephrased: “I hear you — we’ll take it one step at a time.”

Toggle behaviour in YAML:

yaml
Copy code
flags:
  ack_llm_rephrase: true
🧩 Testing Tone Updates
🧪 Local API
Edit conversation.yaml.

Run:

bash
Copy code
make dev
Test:

bash
Copy code
curl -X POST http://localhost:8000/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "I feel tired"}'
→ should return your updated tired acknowledgement.

🖥️ Tone Preview Endpoint (optional)
If you enable /tone-preview:

open http://localhost:8000/tone-preview

see all tone lines and live rephrased examples.

Implementation lives in sakhi/apps/api/routes/tone_preview.py (optional helper).

💡 Best Practices
Goal	Tip
Keep voice unified	Read all tone lines aloud — they should sound like one calm, grounded person.
Avoid over-cheer	Encouraging ≠ hyped. Sakhi stays present.
Test extremes	“sad”, “angry”, “burned out” → ensure replies feel safe.
Involve psychology review	New tones should be validated for empathy & neutrality.

🧩 Key Implementation Files
File	Purpose
sakhi/libs/policy/conversation.yaml	Tone templates + flags
sakhi/libs/conversation/ack.py	Alias map + compose_ack()
sakhi/apps/api/routes/chat.py	Integrates tone logic into conversation
sakhi/libs/llm/rephrase.py	Optional rephrasing helper
docs/conversation_tone_system.md	This guide

🔄 Adding a New Tone
Add a new key in ack_tones, e.g.

yaml
Copy code
lonely: "You’re not alone in this."
Add alias in ack.py:
"isolated": "lonely"

Restart API → test → commit.
(YAML-only edits hot-reload automatically in most dev setups.)

❤️ Why This Matters
Sakhi’s tone engine ensures:

LLM intelligence provides understanding.

Human-crafted policy provides emotional reliability.

Designers can evolve voice safely.

This separation keeps Sakhi authentically warm, never unpredictable.

Updated · October 2025
Maintainers: Core Conversation & Design Team

yaml
Copy code

---

Would you like me to also generate the optional `tone_preview.py` FastAPI route next (a lightweight UI endpoint showing every tone line + example reply)? It’s great for your design team to review tones live in the browser.








