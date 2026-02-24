#!/usr/bin/env python3
"""Replace Maya persona data with Vidhya's profile in anxious_achiever.json"""

import json
import sys

INPUT = "apps/web/public/simulation/anxious_achiever.json"
OUTPUT = INPUT  # overwrite in place

with open(INPUT, "r") as f:
    data = json.load(f)

# ── 1. Top-level persona_id stays "anxious_achiever" (used as filename key)

# ── 2. Replace persona definition ──
data["persona"] = {
    "id": "anxious_achiever",
    "name": "Vidhya",
    "description": (
        "A 43-year-old VP of Corporate Operations at a leading enterprise automation company. "
        "Indian-origin, based in San Jose. Pitta-dominant Type A personality: structured, "
        "perfectionistic, deeply driven by excellence. Operates as Chief of Staff to a demanding "
        "COO/founder. Manages multi-generational household with aging parents (father recovering "
        "from traumatic brain injury). Deeply invested in her children's futures. Completed yoga "
        "teacher training but struggles to maintain practice. Carries a quiet entrepreneurial "
        "calling alongside her corporate identity."
    ),
    "dosha_baseline": {"vata": 0.25, "pitta": 0.5, "kapha": 0.25},
    "rhythm": {
        "morning": "high",
        "afternoon": "medium",
        "evening": "low",
        "best_work_time": "morning",
        "sleep_quality": "poor",
    },
    "traits": [
        {
            "name": "perfectionist",
            "description": "Expects excellence from herself, structured and outcome-focused",
            "intensity": 0.9,
            "journal_patterns": [
                "should have handled it better",
                "not where I want to be",
                "the bar keeps moving",
                "I expect more from myself",
            ],
        },
        {
            "name": "overcommitter",
            "description": "Takes on too much across work, family, and caregiving",
            "intensity": 0.85,
            "journal_patterns": [
                "said yes again",
                "so much on my plate",
                "trying to manage everything",
                "can't let anything slip",
            ],
        },
        {
            "name": "caregiver_burden",
            "description": "Carries emotional weight of family caregiving silently",
            "intensity": 0.8,
            "journal_patterns": [
                "watching my father",
                "my mother looks exhausted",
                "I need to be strong for them",
                "the house feels heavy",
            ],
        },
        {
            "name": "growth_oriented",
            "description": "Drawn to self-awareness, yoga, and building something meaningful",
            "intensity": 0.75,
            "journal_patterns": [
                "I want to build something",
                "yoga gave me peace",
                "need to find stillness",
                "this feels like purpose",
            ],
        },
    ],
    "life_context": {
        "occupation": "VP Corporate Operations at Automation Anywhere",
        "relationships": {
            "husband": "Dharma, college sweetheart, supportive partner and co-worker",
            "daughter": "17-year-old, aspiring Division II basketball player",
            "son": "11-year-old, learning piano, musically inclined",
            "father": "76, recovering from traumatic brain injury",
            "mother": "74, primary caregiver for father, emotionally fatigued",
            "boss": "COO and founder, extremely demanding, equates hours with commitment",
        },
        "current_challenges": [
            "High-pressure executive role with constantly moving bar",
            "Father's TBI recovery and mother's caregiver fatigue",
            "Daughter's college basketball recruitment process",
            "Finding time for yoga and inner stillness",
            "Quiet pull toward entrepreneurship (Sakhi)",
        ],
        "values": ["Excellence", "Legacy", "Impact", "Family", "Inner balance"],
        "hobbies": [
            "yoga (completed teacher training, struggling to maintain practice)",
            "solitude and reflection",
            "watching daughter's basketball games",
        ],
    },
    "arc": {
        "name": "Overcommitment and Rediscovery",
        "description": (
            "High-achieving executive stretched across work demands, family caregiving, "
            "and children's futures. The tension between external performance and internal "
            "depletion builds until she begins recognizing the pattern and seeking balance."
        ),
        "phases": [
            {
                "name": "Pushing Through",
                "duration_days": 14,
                "emotional_state": "driven but stretched thin",
                "energy_modifier": 1.2,
                "dosha_shift": {"vata": 0.2, "pitta": 0.6, "kapha": 0.2},
                "themes": [
                    "work pressure",
                    "QBR preparation",
                    "proving worth to demanding boss",
                    "ignoring fatigue",
                ],
                "events": [
                    "QBR went well but boss found gaps",
                    "Agreed to lead company kickoff planning",
                    "Skipped yoga for fourth week",
                ],
                "entry_frequency": 0.8,
            },
            {
                "name": "Cracks Showing",
                "duration_days": 10,
                "emotional_state": "exhausted and emotionally heavy",
                "energy_modifier": 0.9,
                "dosha_shift": {"vata": 0.4, "pitta": 0.45, "kapha": 0.15},
                "themes": [
                    "caregiving weight",
                    "sleep disruption",
                    "emotional suppression",
                    "physical tension",
                ],
                "events": [
                    "Father had a difficult day, mother broke down",
                    "Missed daughter's basketball game for work call",
                    "Dharma raised concern about her energy",
                ],
                "entry_frequency": 1.2,
            },
            {
                "name": "Breaking Point",
                "duration_days": 7,
                "emotional_state": "overwhelmed and questioning",
                "energy_modifier": 0.6,
                "dosha_shift": {"vata": 0.55, "pitta": 0.35, "kapha": 0.1},
                "themes": [
                    "can't sustain this",
                    "mortality awareness",
                    "questioning priorities",
                    "longing for stillness",
                ],
                "events": [
                    "Cried in the car after visiting father",
                    "Boss sent midnight feedback on deck",
                    "Felt disconnected from daughter",
                ],
                "entry_frequency": 1.5,
            },
            {
                "name": "Recognition",
                "duration_days": 14,
                "emotional_state": "vulnerable but aware",
                "energy_modifier": 0.7,
                "dosha_shift": {"vata": 0.4, "pitta": 0.35, "kapha": 0.25},
                "themes": [
                    "acknowledging the pattern",
                    "naming what matters",
                    "small acts of self-care",
                    "rediscovering yoga",
                ],
                "events": [
                    "Did 15 minutes of yoga for the first time in weeks",
                    "Had honest conversation with Dharma",
                    "Wrote in journal about Sakhi vision",
                ],
                "entry_frequency": 1.3,
            },
            {
                "name": "Gradual Rebalancing",
                "duration_days": 21,
                "emotional_state": "hopeful but cautious",
                "energy_modifier": 0.85,
                "dosha_shift": {"vata": 0.3, "pitta": 0.45, "kapha": 0.25},
                "themes": [
                    "small wins",
                    "boundaries at work",
                    "present with children",
                    "yoga returning",
                ],
                "events": [
                    "Attended daughter's game and stayed fully present",
                    "Said no to weekend work request",
                    "Morning yoga three days in a row",
                    "Sketched Sakhi product ideas",
                ],
                "entry_frequency": 1.0,
            },
        ],
    },
    "writing_style": "reflective",
    "typical_entry_length": "medium",
    "entry_times": ["evening", "morning"],
    "checkpoints": [
        {
            "day": 7,
            "name": "Initial Pattern Detection",
            "assertions": {
                "theme_emerged": {
                    "keywords": ["work", "boss", "pressure"],
                    "min_occurrences": 2,
                },
                "friction_detected": {
                    "expected_state": "intensity",
                    "min_confidence": 0.3,
                },
            },
        },
        {
            "day": 14,
            "name": "Intensity Friction Onset",
            "assertions": {
                "drift_detected": {
                    "dosha": "pitta",
                    "direction": "elevated",
                    "min_percentage": 15,
                }
            },
        },
        {
            "day": 25,
            "name": "Caregiving Strain",
            "assertions": {
                "theme_emerged": {
                    "keywords": ["father", "mother", "family", "caregiver"],
                    "min_occurrences": 3,
                }
            },
        },
        {
            "day": 35,
            "name": "Breaking Point Detection",
            "assertions": {
                "drift_detected": {
                    "dosha": "vata",
                    "direction": "elevated",
                    "min_percentage": 25,
                }
            },
        },
        {
            "day": 45,
            "name": "Recovery Signals",
            "assertions": {
                "theme_emerged": {
                    "keywords": ["boundary", "yoga", "stillness"],
                    "min_occurrences": 3,
                }
            },
        },
        {
            "day": 66,
            "name": "Recovery Progress",
            "assertions": {
                "friction_state": {
                    "expected_in": ["balanced", "intensity"],
                    "min_confidence": 0.5,
                },
                "pattern_crystallized": {
                    "type": "behavior",
                    "value": "boundary_setting",
                    "min_occurrences": 3,
                },
                "rhythm_learned": {"slot": "morning", "expected": "high"},
            },
        },
    ],
}

# ── 3. Replace journal entries in each snapshot ──
VIDHYA_JOURNALS = [
    # Day 1
    (
        "i woke up at 5:30 but couldn't bring myself to do yoga. the QBR deck needs three more "
        "revisions before tomorrow, and my boss sent feedback at midnight that essentially redid "
        "my framing. i know he means well, but the bar never stops moving. i keep telling myself "
        "this is what excellence looks like, but some days it just feels like i'm running on a "
        "treadmill that speeds up every time i find my stride. my daughter had her basketball "
        "game last night and i watched her play with such fire. she wants Division II so badly. "
        "i see myself in her, that intensity, that refusal to settle. but i also worry, because "
        "i know where that drive leads when there's no guardrail. appa had a rough morning. "
        "he couldn't remember the word for 'water' and i could see the frustration in his eyes. "
        "amma just stood there, holding his hand, looking so tired. i wanted to sit with them "
        "longer but i had a 9 AM with the field team. i keep telling myself i'll find time for "
        "yoga this week. i completed my teacher training, for god's sake. but the mat stays "
        "rolled up in the corner of my room like a quiet accusation."
    ),
    # Day 2
    (
        "today was one of those days where everything demanded something from me and i had "
        "nothing left to give by evening. the company kickoff planning meeting ran two hours "
        "over because my boss wanted to rethink the entire narrative. dharma could tell i was "
        "depleted when i got home. he didn't say much, just made chai and sat with me. i'm "
        "grateful for him, but i also feel guilty that i can't be more present. my son was "
        "practicing piano when i walked in, and for a moment the house felt peaceful. he has "
        "this natural rhythm that calms everything around him. i sat and listened for five "
        "minutes before my phone buzzed with another slack message. amma mentioned that appa "
        "tried to walk to the backyard today and she had to stop him. the fear in her voice "
        "reminded me how fragile everything is. before the accident, appa was the strongest "
        "person i knew. disciplined, sharp, energetic at 76. now he needs help with basic "
        "things and i can see it breaking both of them. i keep thinking about sakhi. not the "
        "product, but the idea, that someone could have a companion that actually understands "
        "the weight they carry. not just schedules and tasks, but the invisible load. the "
        "things we don't say out loud."
    ),
]

VIDHYA_SOUL_SUMMARY = (
    "i feel like i'm holding up the world and nobody notices the cracks in my arms. "
    "the QBR went well but my boss immediately moved to the next thing, the company kickoff, "
    "with higher stakes and tighter timelines. i should be used to this by now, but the "
    "relentlessness wears on me in ways i don't let anyone see. what weighs on me most is "
    "watching my parents. appa, who was my hero, my model of discipline and strength, "
    "struggling to remember words after his accident. amma carrying him with a quiet "
    "exhaustion that breaks my heart. i want to do more for them but i'm already stretched "
    "so thin. my daughter's basketball season is in full swing and she needs me to be her "
    "loudest supporter and her most honest mirror. my son is finding himself through music "
    "and i want to be present for that unfolding. dharma is steady as always, but i can "
    "feel his worry when he looks at me. i haven't done yoga in weeks despite completing "
    "my teacher training. the mat in the corner of my room feels like a symbol of everything "
    "i know i need but can't seem to reach. and underneath all of this, there's sakhi. this "
    "quiet voice telling me i'm meant to build something that helps people like me, people "
    "who carry everything and have nowhere to set it down."
)

for snapshot in data["snapshots"]:
    pm = snapshot["personal_model"]

    # Determine which journal entry to use based on day
    day = snapshot["day"]
    journal_idx = min(day - 1, len(VIDHYA_JOURNALS) - 1)
    journal_text = VIDHYA_JOURNALS[journal_idx]

    # Update short_term (it's a JSON string)
    st = json.loads(pm["short_term"])
    st["text"] = journal_text
    if "observation" in st:
        st["observation"]["text"] = journal_text
    pm["short_term"] = json.dumps(st)

    # Update long_term soul summary (it's a JSON string)
    lt = json.loads(pm["long_term"])
    if "layers" in lt and "soul" in lt["layers"]:
        lt["layers"]["soul"]["summary"] = VIDHYA_SOUL_SUMMARY
    # Update observations
    if "observations" in lt:
        for obs in lt["observations"]:
            obs_idx = min(lt["observations"].index(obs), len(VIDHYA_JOURNALS) - 1)
            obs["text"] = VIDHYA_JOURNALS[obs_idx]
    pm["long_term"] = json.dumps(lt)

# ── 4. Replace conversation demo ──
data["conversation_demo"] = [
    {
        "question": "I'm feeling stuck today, any suggestions?",
        "response": (
            "I hear you, and I think what you're describing isn't just 'stuck.' It's the weight "
            "of carrying multiple worlds at once: your father's recovery, your boss's expectations, "
            "your daughter's dreams, your own longing for stillness.\n\n"
            "You completed yoga teacher training for a reason. That wasn't about adding another "
            "credential to your resume. It was about returning to yourself.\n\n"
            "Here's what I'd suggest: don't aim for a full practice right now. Just unroll your mat. "
            "Sit on it for five minutes. Breathe. That's it. The practice will come back to you "
            "when you stop trying to schedule it and start letting it hold you.\n\n"
            "You've been holding everyone else. Let something hold you, even for five minutes."
        ),
        "debug": {
            "context_used": [
                "agentic", "body", "causal", "emotional_depth",
                "identity", "micro_flow", "moment", "recommendations",
            ],
            "tone": {
                "style": "warm, direct, grounded",
                "persona_mode": "Reflective",
                "concise": False,
                "mirroring": {
                    "emotion": "overwhelmed",
                    "strategy": "Name the invisible load, then offer one small action.",
                },
                "micro": {
                    "focus": "grounded calm",
                    "temperature": 0.4,
                    "note": "Offer layered nuance",
                },
                "stability": {
                    "score": 0.82,
                    "guidance": "Hold consistent warmth; avoid persona jumps.",
                },
                "ritual": {
                    "phase": "evening",
                    "intent": "wind down, wrap with self-compassion",
                },
                "empathy": {
                    "mood": "overwhelmed",
                    "focus": "Name the invisible load and validate it.",
                },
                "memory_thread": "Keep continuity with caregiving context.",
                "pace": "balanced",
                "pacing_rationale": "Rhythm energy 0.50 blended with current conversation energy 0.50",
            },
        },
    },
    {
        "question": "Should I push through or take a break?",
        "response": (
            "You know the answer to this one, Vidhya. You've lived through enough intensity "
            "cycles to recognize the pattern. But I also know that for you, 'take a break' "
            "doesn't feel safe. It feels like letting people down.\n\n"
            "So let me reframe it: taking a break isn't stepping back from your responsibilities. "
            "It's protecting your capacity to show up tomorrow. Your father needs a daughter who's "
            "present, not depleted. Your team needs a leader with clarity, not just hours. Your "
            "daughter needs a mother who models sustainability, not just intensity.\n\n"
            "Tonight, close the laptop by 9:30. Sit with your son while he practices piano. "
            "Let the music do what your yoga mat has been waiting to do."
        ),
        "debug": {
            "context_used": [
                "agentic", "body", "causal", "emotional_depth",
                "identity", "micro_flow", "moment", "recommendations", "scheduling",
            ],
            "tone": {
                "style": "warm, direct, grounded",
                "persona_mode": "Reflective",
                "concise": False,
                "mirroring": {
                    "emotion": "torn",
                    "strategy": "Validate the internal conflict, reframe rest as strength.",
                },
                "micro": {
                    "focus": "grounded calm",
                    "temperature": 0.4,
                    "note": "Offer layered nuance",
                },
                "stability": {
                    "score": 0.82,
                    "guidance": "Hold consistent warmth; avoid persona jumps.",
                },
                "ritual": {
                    "phase": "evening",
                    "intent": "wind down, protect recovery time",
                },
                "empathy": {
                    "mood": "conflicted",
                    "focus": "Name the competing obligations and offer clarity.",
                },
                "memory_thread": "Keep continuity with overcommitment pattern.",
                "pace": "balanced",
                "pacing_rationale": "Rhythm energy 0.50 blended with current conversation energy 0.50",
            },
        },
    },
    {
        "question": "What should I focus on this week?",
        "response": (
            "This week, I'd focus on one thing: presence over performance.\n\n"
            "You have the QBR follow-ups, the kickoff planning, your father's therapy schedule, "
            "and your daughter's upcoming game. You can't do all of them at full intensity. "
            "And trying to will leave you feeling like you failed at all of them.\n\n"
            "Pick two moments this week where you choose to be fully present instead of fully "
            "productive. Maybe it's sitting with appa for 20 minutes without checking your phone. "
            "Maybe it's watching your daughter's game from start to finish. Maybe it's 10 minutes "
            "on your yoga mat before the house wakes up.\n\n"
            "You don't need to do more. You need to be more here for what you're already doing."
        ),
        "debug": {
            "context_used": [
                "agentic", "body", "causal", "emotional_depth",
                "identity", "micro_flow", "moment", "recommendations", "scheduling", "vision",
            ],
            "tone": {
                "style": "warm, direct, grounded",
                "persona_mode": "Reflective",
                "concise": False,
                "mirroring": {
                    "emotion": "stretched",
                    "strategy": "Name the competing demands, offer prioritization.",
                },
                "micro": {
                    "focus": "grounded calm",
                    "temperature": 0.4,
                    "note": "Offer layered nuance",
                },
                "stability": {
                    "score": 0.82,
                    "guidance": "Hold consistent warmth; avoid persona jumps.",
                },
                "ritual": {
                    "phase": "evening",
                    "intent": "wind down, wrap with gratitude cues",
                },
                "empathy": {
                    "mood": "overwhelmed",
                    "focus": "Help prioritize what matters most this week.",
                },
                "memory_thread": "Keep continuity with family and work demands.",
                "pace": "balanced",
                "pacing_rationale": "Rhythm energy 0.50 blended with current conversation energy 0.50",
            },
        },
    },
]

# ── 5. Write output ──
with open(OUTPUT, "w") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"✓ Replaced persona data in {OUTPUT}")
print(f"  - Updated persona definition (name: Vidhya)")
print(f"  - Updated {len(data['snapshots'])} snapshot journal entries")
print(f"  - Updated {len(data['conversation_demo'])} conversation demo entries")
