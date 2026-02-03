# Sakhi Demo & Pitch Plan

## The Vision

**Sakhi: Infrastructure for humans to reclaim their lives.**

The world comes through YOUR Sakhi. You don't chase — you live.
Focus on what matters: health, joy, connection.

---

## The One-Liner Pitches

**For Investors:**
> "Sakhi is the operating system for your life. It knows you deeply, executes for you, coordinates for you — so you can focus on health, joy, and connection."

**For Users:**
> "Sakhi knows you. The world comes to you."

**For Technical Audience:**
> "A personal AI that truly understands you through Ayurvedic intelligence, executes tasks based on your preferences, and coordinates with other Sakhis."

---

## The Demo: Four Acts

**Core Theme:** Every act demonstrates that **Sakhi knows you**. Act 4 reveals **how**.

```
NARRATIVE ARC:

  ┌─────────────────────────────────────────────────────────────────┐
  │                    "SAKHI KNOWS YOU"                             │
  │                                                                  │
  │   ACT 1          ACT 2          ACT 3          ACT 4            │
  │   ──────         ──────         ──────         ──────           │
  │   Knows your     Knows your     Knows your     THE REVEAL:      │
  │   TASTE          RELATIONSHIPS  BODY           How Sakhi knows  │
  │                  (Personal)     (Business)     you so deeply    │
  │                                                                  │
  │   "Find me a     "Plan with     "Order food    "Why am I        │
  │   car perfume    Mom"           for me"        feeling this?"   │
  │   that suits                                                    │
  │   my taste"      → Your Sakhi   → Your Sakhi   → Ayurveda +     │
  │                    ↔ Mom's        ↔ Restaurant   patterns +     │
  │   → searches       Sakhi          Sakhi          memory         │
  │   → matches to                                                  │
  │     YOUR taste   [SPLIT SCREEN] [SPLIT SCREEN]                  │
  │                                                                  │
  └─────────────────────────────────────────────────────────────────┘

  MESH STORY COMPLETE:
  - Act 2: Your Sakhi ↔ Mom's Sakhi (personal relationship)
  - Act 3: Your Sakhi ↔ Restaurant's Sakhi (business relationship)

  Throughout: "How does Sakhi know all this?"
  Act 4: The answer.
```

---

## ACT 1: SAKHI KNOWS YOUR TASTE

### The Story
*"I want something that suits ME. Not best-rated. Not popular. What I would love."*

### Demo Script

**Setup:** User is talking to Sakhi on their phone/web

**User:** "Sakhi, I need a car perfume. Find something that suits my taste."

**Sakhi:** "Let me find something perfect for you..."

*[Screen shows: Desktop agent activates, browsing Amazon/Flipkart]*

**What Sakhi is thinking (shown subtly):**
- "You prefer subtle, not overpowering scents"
- "You gravitate toward woody, sandalwood notes"
- "You're sensitive to strong florals — avoid those"
- "You mentioned loving the smell of old books once"

*[Browser shows: Sakhi searching, filtering, reading reviews]*

**Sakhi:** "Found three options that match your taste:

1. **Forest Breeze** — Subtle cedarwood and pine. ₹450.
   *This feels like that cabin you loved in Manali.*

2. **Sandalwood Classic** — Traditional, calming. ₹380.
   *Your grandmother's house had this scent.*

3. **Ocean Mist** — Light, fresh, not sweet. ₹520.
   *You liked the sea breeze smell in Goa.*

I'd go with Forest Breeze — it matches your current Kapha season preference for grounding scents."

**User:** "Get the Forest Breeze"

**Sakhi:** "Done. Ordered. Arrives Wednesday."

### What This Shows

- Sakhi knows **sensory preferences** (not just what's popular)
- Sakhi **connects to memories** (Manali cabin, grandmother's house)
- Sakhi considers **Ayurvedic context** (Kapha season → grounding scents)
- **Personalization is not a feature, it's the foundation**

### Technical Requirements

| Component | Status | Needed |
|-----------|--------|--------|
| Desktop Agent | ✅ Basic | Vision loop with Claude |
| Preference memory | ✅ Partial | Sensory preferences in memory graph |
| Taste reasoning | ❌ Missing | LLM prompt with preference context |
| Memory associations | ⚠️ Partial | Connect products to personal memories |
| Ayurvedic context | ✅ Built | Current dosha state influences recommendation |

### Build Items for Act 1

1. **Vision Loop Service** (Priority: HIGH)
   ```
   Files to create:
   - sakhi/apps/api/services/agent/vision_loop.py
   - Bridge: screenshot → Claude → action → repeat
   ```

2. **Taste/Preference Memory** (Priority: HIGH)
   ```
   Extend memory_nodes:
   - kind: 'sensory_preference'
   - Data: scent likes/dislikes, texture preferences, etc.
   ```

3. **Preference-Aware Search** (Priority: HIGH)
   ```
   When searching, Claude gets:
   - User's sensory preferences
   - Relevant memories (places, people, experiences)
   - Current Ayurvedic state
   ```

---

## ACT 2: SAKHI KNOWS YOUR RELATIONSHIPS

### The Story
*"I want to see Mom. Sakhi knows what we both enjoy, when we're both free."*

### Demo Script

**Setup:** Split screen showing TWO phones — User and Mom

**[LEFT SCREEN - User]**
**User:** "Sakhi, plan something with Mom this week"

**Sakhi:** "Let me coordinate with her Sakhi..."

*[Visual: Connection animation between the two screens]*

**Sakhi (thinking, shown subtly):**
- "You haven't seen Mom in 3 weeks"
- "You both enjoy cooking together"
- "Mom's energy is lower in evenings lately"
- "Saturday afternoon works for both"

**[RIGHT SCREEN - Mom]**
*Mom's phone lights up*

**Mom's Sakhi:** "Your son wants to spend time together this week. How about Saturday afternoon? You could cook together — you both love that. He can come over around 3pm when your energy is best."

**Mom:** "That sounds lovely"

**[LEFT SCREEN - User]**
**Sakhi:** "Mom confirmed! Saturday 3pm at her place. You'll cook together. I've reminded you to pick up those spices she mentioned needing."

**[BOTH SCREENS]**
*Calendar shows event with context*

### What This Shows

- Sakhi knows **relationship dynamics** (how long since you met)
- Sakhi knows **shared interests** (cooking together)
- Sakhi knows **energy patterns** (Mom's best time)
- Sakhi adds **thoughtful touches** (spices reminder)

### Technical Requirements

| Component | Status | Needed |
|-----------|--------|--------|
| Mesh coordination | ✅ Built | Works |
| Relationship memory | ✅ Built | Has context |
| Shared interests | ⚠️ Partial | Need to surface in coordination |
| Energy-aware scheduling | ✅ Built | Operating system integration |
| Thoughtful extras | ❌ Missing | Extract "spices" from past conversations |

### Build Items for Act 2

1. **Demo UI for Split Screen** (Priority: HIGH)
   ```
   Files to create:
   - apps/web/app/demo/coordination/page.tsx
   - Shows two users side by side
   - Real-time updates via WebSocket
   ```

2. **Relationship Context in Coordination** (Priority: MEDIUM)
   ```
   Enhance initiate_coordination:
   - Include shared interests
   - Include relevant past mentions
   - Add thoughtful suggestions
   ```

---

## ACT 3: SAKHI KNOWS YOUR BODY (+ Business Mesh)

### The Story
*"I'm hungry but tired. Sakhi knows what my body needs — and coordinates with the restaurant's Sakhi to get it right."*

### Demo Script

**Setup:** Split screen showing User and Restaurant's Sakhi interface

**[LEFT SCREEN - User]**
**User:** "Sakhi, order some food for dinner"

**Sakhi:** "Let me coordinate with Annapurna's Sakhi..."

*[Visual: Connection animation between User's Sakhi and Restaurant's Sakhi]*

**Sakhi (thinking, shown subtly):**
- "Your Pitta is slightly elevated today"
- "You had a heavy lunch — lighter dinner better"
- "You mentioned craving something warm"
- "You're avoiding dairy this week (digestion)"

**[RIGHT SCREEN - Restaurant's Sakhi]**
*Restaurant dashboard lights up with coordination request*

**Annapurna's Sakhi:** "Incoming order coordination from a regular guest...

**Guest Profile (shared via mesh):**
- Prefers less spicy (mild to medium)
- Currently avoiding dairy
- Loves our khichdi — ordered 3 times last month
- Prefers warm, comfort food
- Ayurvedic note: Pitta elevated, needs cooling balance

**Suggested order:** Dal Khichdi (no ghee) + Jeera Rice + Cucumber Raita (oat-based)

*This matches their current needs. Should I confirm?"*

**Restaurant Staff sees:** Auto-prepared order with special instructions

**[LEFT SCREEN - User]**
**Sakhi:** "Annapurna's Sakhi remembers you love their khichdi. They've suggested:

**Dal Khichdi** (no ghee, less spicy) — your usual ₹180
**Cucumber Raita** (oat-based, no dairy) — ₹60

*They know you're avoiding dairy and prefer mild spice. Total: ₹240*

This will cool your Pitta without heaviness. Want me to confirm?"

**User:** "Yes, that's perfect"

**[BOTH SCREENS - Coordination Complete]**
**Sakhi:** "Confirmed with Annapurna. 35 minutes. I've dimmed the lights for when you eat — you digest better in calm environments."

**Annapurna's Sakhi:** "Order confirmed. Guest preferences applied. Delivery in 35 minutes."

### What This Shows

- **Sakhi-to-Sakhi mesh works for commerce** (not just personal relationships)
- **Restaurant knows you through YOUR Sakhi** (privacy-preserving personalization)
- Sakhi knows **current body state** (Pitta, digestion)
- Sakhi knows **dietary patterns** (avoiding dairy, spice preference)
- Sakhi knows **what worked before** (loved their khichdi)
- **Business Sakhis** can serve you better without you repeating preferences
- **The mesh story is complete:** Personal (Mom) + Business (Restaurant)
- **Food is medicine, not just calories**

### Technical Requirements

| Component | Status | Needed |
|-----------|--------|--------|
| Dosha state | ✅ Built | Real-time dosha tracking |
| Dietary preferences | ⚠️ Partial | Need food memory |
| Restaurant memory | ❌ Missing | What you liked from where |
| Smart home integration | ❌ Future | Dimming lights (mock for demo) |
| Transaction coordination | ✅ Schema | Built but needs polish |
| **Business Sakhi mock** | ❌ Missing | Restaurant dashboard view |
| **Mesh profile sharing** | ✅ Built | Privacy-aware preference sharing |

### Build Items for Act 3

1. **Mock Restaurant Sakhi Dashboard** (Priority: HIGH for demo)
   ```
   Files to create:
   - apps/web/app/demo/restaurant/page.tsx
   - Shows restaurant's view of incoming coordination
   - Displays guest profile (shared via mesh)
   - Shows auto-suggested order based on preferences
   ```

2. **Food Preference Memory** (Priority: MEDIUM)
   ```
   Extend memory:
   - Dishes liked/disliked
   - Restaurant experiences
   - Spice tolerance
   - Dietary restrictions over time
   ```

3. **Ayurveda-Aware Food Recommendations** (Priority: HIGH)
   ```
   Connect dosha state to food:
   - Pitta elevated → cooling foods, less spicy
   - Vata high → grounding, warm, moist
   - Kapha high → light, stimulating
   ```

4. **Privacy-Preserving Preference Sharing** (Priority: MEDIUM)
   ```
   Via mesh coordination:
   - Share only relevant preferences
   - Guest controls what's visible
   - Restaurant sees "Guest prefers X" not raw data
   ```

---

## ACT 4: THE REVEAL — HOW SAKHI KNOWS

### The Story
*"How does Sakhi know all this about me? This is where we reveal the magic."*

### Demo Script

**User:** "Sakhi, I've been feeling really off the past few days. Scattered, anxious, can't focus."

**Sakhi:** "I've noticed that too. Let me show you what I see..."

*[Visual: Beautiful visualization of the user's patterns]*

**Sakhi:** "Your Vata has been elevated since Tuesday. Here's what's contributing:

**Sleep:** Three nights under 6 hours
*Your Vata always rises when sleep drops.*

**Routine:** You skipped morning meditation Wed & Thu
*This is your grounding practice — without it, Vata accumulates.*

**Stress:** That conversation with your manager on Monday
*I noticed the shift in your journaling tone after that.*

**Weather:** It's been cold and windy
*External Vata increases internal Vata for you.*

---

**The last time this happened was October.**
You felt exactly like this. What helped:
- Evening walks for 3 days
- Warm sesame oil on feet before bed
- You called your sister — that always grounds you

Within 4 days, you felt centered again.

---

**Would you like me to:**
1. Block 30 minutes for a walk today at 6pm?
2. Remind you about the sesame oil tonight?
3. Suggest calling your sister this weekend?

*Or I can do all three.*"

**User:** "Do all three"

**Sakhi:** "Done. I'll guide you through this like last time. You'll feel better soon."

### What This Shows

- **Deep pattern recognition** across time
- **Ayurvedic framework** (Vata/Pitta/Kapha)
- **Personal history** ("last time this happened")
- **What worked for YOU** (not generic advice)
- **Proactive execution** (blocks calendar, sets reminders)
- **THE REVEAL:** This is how Sakhi knows your taste, relationships, body — the same intelligence engine powers everything

### Technical Requirements

| Component | Status | Needed |
|-----------|--------|--------|
| Causal reasoning | ✅ Built | "Why am I feeling X" |
| Historical patterns | ✅ Built | Pattern learning |
| Ayurvedic engine | ✅ Built | Dosha tracking |
| "Last time" lookup | ⚠️ Partial | Need to surface more explicitly |
| Recommendation → Action | ⚠️ Partial | Need seamless "do all three" |
| Beautiful visualization | ❌ Missing | Show patterns visually |

### Build Items for Act 4

1. **Polish "Last Time" Retrieval** (Priority: HIGH)
   ```
   Enhance causal_reasoning.py:
   - Find similar historical episodes
   - What interventions were tried
   - What worked (from feedback)
   ```

2. **Seamless Multi-Action** (Priority: MEDIUM)
   ```
   "Do all three" should:
   - Block calendar
   - Set reminder
   - Suggest call with context
   ```

3. **Pattern Visualization** (Priority: MEDIUM)
   ```
   Create visual for:
   - Timeline of Vata rise
   - Contributing factors
   - Similar past episodes
   ```

---

## Demo Script: Full Run-Through (5 minutes)

### Opening (30 seconds)
*"What if there was someone who truly knew you? Not your browsing history. Not your likes. YOU."*

*"Your taste. Your relationships. Your body. Your patterns."*

*"Meet Sakhi."*

### Act 1: Taste (60 seconds)
*"Watch Sakhi find a car perfume..."*
- Not best-rated. What YOU would love.
- Connects to memories, considers your current state.
- "How does it know this?"

### Act 2: Relationships (60 seconds)
*"Now watch two Sakhis coordinate..."*
- Knows what you both enjoy
- Schedules around energy, not just availability
- Adds thoughtful touches

### Act 3: Body + Business Mesh (60 seconds)
*"Now watch your Sakhi coordinate with the restaurant's Sakhi..."*
- Split screen: You and Restaurant dashboard
- Restaurant's Sakhi knows you: "prefers less spicy, avoiding dairy"
- Food as medicine, matched to your body state
- Mesh works for commerce, not just family

### Act 4: The Reveal (90 seconds)
*"How does Sakhi know all this?"*
- Show the pattern recognition
- Ayurvedic framework
- Personal history
- "Last time this happened..."
- Seamless action from insight

### Closing (30 seconds)
*"Sakhi knows your taste. Your relationships. Your body. Your patterns."*

*"The world comes through Sakhi. Matched to you."*

*"You get your life back."*

*"Health. Joy. Connection."*

*"This is Sakhi."*

---

## Build Priority Order (Updated)

### Phase A: Demo-Ready in 2 Weeks

| Priority | Item | Act | Effort | Why First |
|----------|------|-----|--------|-----------|
| 1 | Vision Loop for Desktop | 1, 3 | 3-4 days | Enables autonomous browsing |
| 2 | Taste/Preference Memory | 1 | 2 days | Makes Act 1 personal |
| 3 | Split-Screen Demo UI (Personal) | 2 | 2 days | Visual impact for Mom coordination |
| 4 | Split-Screen Demo UI (Business) | 3 | 1-2 days | Restaurant Sakhi dashboard |
| 5 | "Last Time" + Seamless Action | 4 | 2 days | The reveal payoff |
| 6 | Ayurveda-Food Connection | 3 | 1-2 days | Body intelligence |
| 7 | End-to-end demo flow | All | 2 days | Polish |

### Key Insight

The **same intelligence engine** powers all four acts:
- Act 1: Preferences → Product matching
- Act 2: Relationship context → Coordination
- Act 3: Body state → Food recommendation
- Act 4: All of the above → Explanation

Act 4 isn't a separate feature — it's **revealing what powers everything**.

---

## Technical Architecture: The Knowledge Core

```
┌─────────────────────────────────────────────────────────────────────┐
│                    SAKHI KNOWLEDGE CORE                              │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                   PERSONAL MODEL                                │ │
│  │                                                                 │ │
│  │   ┌───────────────┐  ┌───────────────┐  ┌───────────────┐     │ │
│  │   │ BODY STATE    │  │ MIND STATE    │  │ SOUL STATE    │     │ │
│  │   │ - Doshas      │  │ - Energy      │  │ - Values      │     │ │
│  │   │ - Digestion   │  │ - Focus       │  │ - Purpose     │     │ │
│  │   │ - Sleep       │  │ - Mood        │  │ - Growth      │     │ │
│  │   └───────────────┘  └───────────────┘  └───────────────┘     │ │
│  │                                                                 │ │
│  │   ┌───────────────┐  ┌───────────────┐  ┌───────────────┐     │ │
│  │   │ PREFERENCES   │  │ RELATIONSHIPS │  │ PATTERNS      │     │ │
│  │   │ - Taste       │  │ - People      │  │ - What works  │     │ │
│  │   │ - Sensory     │  │ - Dynamics    │  │ - Triggers    │     │ │
│  │   │ - Style       │  │ - History     │  │ - Rhythms     │     │ │
│  │   └───────────────┘  └───────────────┘  └───────────────┘     │ │
│  │                                                                 │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                              │                                       │
│                              ▼                                       │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                   EXECUTION LAYER                               │ │
│  │                                                                 │ │
│  │   ACT 1: DOES      ACT 2: COORDS     ACT 3: TRANSACTS          │ │
│  │   (Desktop Agent)  (Mesh Network)    (Commerce)                │ │
│  │        │                │                  │                   │ │
│  │        └────────────────┴──────────────────┘                   │ │
│  │                         │                                       │ │
│  │              All powered by Knowledge Core                      │ │
│  │                                                                 │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                              │                                       │
│                              ▼                                       │ │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                   ACT 4: KNOWS (The Reveal)                     │ │
│  │                                                                 │ │
│  │   "This is how Sakhi knows your taste, your relationships,     │ │
│  │    your body. The same intelligence that recommends a          │ │
│  │    car perfume is what understands why you feel scattered."    │ │
│  │                                                                 │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Success Metrics for Demo

| Metric | Target |
|--------|--------|
| Act 1: Taste match | Recommendation feels "that's so me" |
| Act 2: Coordination | Thoughtful touch beyond just scheduling |
| Act 3: Food | Ayurvedic reasoning visible, not hidden |
| Act 4: Reveal | Audience understands how all connects |
| Overall | "This actually knows me" reaction |

---

*Document created: January 31, 2026*
*Last updated: January 31, 2026*
*Vision: Sakhi as infrastructure for humans to reclaim their lives*
*Theme: Sakhi knows you. The world comes through Sakhi. Matched to you.*
