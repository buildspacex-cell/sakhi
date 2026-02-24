#!/usr/bin/env python3
"""Replace Alex persona data with Big D's profile in stuck_creative.json"""

import json

INPUT = "apps/web/public/simulation/stuck_creative.json"
OUTPUT = INPUT

with open(INPUT, "r") as f:
    data = json.load(f)

# ── 1. Replace persona definition ──
data["persona"] = {
    "id": "stuck_creative",
    "name": "Big D",
    "description": (
        "A 45-year-old GM and Channel Head at a SaaS company in San Jose, formerly CEO "
        "of a BPO segment with 10,000+ employees. Indian-origin (Tamil Brahmin upbringing). "
        "Kapha-dominant: warm, generous, steady, comfort-loving, natural leader. People follow "
        "him across companies out of loyalty. Carries internal confidence without needing "
        "validation. Tends to overextend for others. Uses humor as armor. May avoid sitting "
        "deeply with discomfort."
    ),
    "dosha_baseline": {"vata": 0.15, "pitta": 0.35, "kapha": 0.50},
    "rhythm": {
        "morning": "medium",
        "afternoon": "high",
        "evening": "medium",
        "best_work_time": "afternoon",
        "sleep_quality": "good",
    },
    "traits": [
        {
            "name": "people_builder",
            "description": "Invests deeply in people, builds loyalty that lasts years",
            "intensity": 0.9,
            "journal_patterns": [
                "my team showed up for me",
                "helped someone on the team",
                "loyalty matters more than anything",
                "people remember how you treat them",
            ],
        },
        {
            "name": "generous_overextender",
            "description": "Gives time, money, and energy without keeping score",
            "intensity": 0.85,
            "journal_patterns": [
                "couldn't say no",
                "spent way more time than planned",
                "they needed help so I stayed",
                "gave more than I should have",
            ],
        },
        {
            "name": "comfort_seeker",
            "description": "Gravitates toward comfort: food, movies, familiar routines",
            "intensity": 0.7,
            "journal_patterns": [
                "ordered our usual",
                "watched a movie to unwind",
                "comfort food kind of night",
                "stayed in, felt good",
            ],
        },
        {
            "name": "resilient_adapter",
            "description": "Reinvents himself without fragility, absorbs new environments fast",
            "intensity": 0.8,
            "journal_patterns": [
                "figured it out",
                "new territory but I'll learn",
                "doesn't scare me",
                "I've rebuilt before",
            ],
        },
    ],
    "life_context": {
        "occupation": "GM of Product Line & Channel Head at SaaS company (San Jose)",
        "relationships": {
            "wife": "proud partner, sees his growth and character",
            "children": "two kids, drives them around, stays involved",
            "parents": "conservative Tamil Brahmin, deeply sentimental bond",
            "boss": "same demanding founder as Vidhya, separates style from substance",
            "teams": "former employees follow him across companies",
        },
        "current_challenges": [
            "Transitioning from BPO leadership to SaaS tech",
            "Managing demanding founder boss without losing himself",
            "Tendency to give 3x what's asked in every favor",
            "Balancing high social energy with need for private calm",
            "Learning to sit with discomfort instead of deflecting with humor",
        ],
        "values": ["Loyalty", "Generosity", "Family", "Comfort", "Grit"],
        "hobbies": [
            "cricket (watching, discussing strategy)",
            "Tamil cinema and Bollywood",
            "chess",
            "beach vacations",
            "cooking and eating well",
        ],
    },
    "arc": {
        "name": "Leadership and Generosity",
        "description": (
            "Proven leader transitioning to a new industry. Steady and confident, "
            "but his natural generosity sometimes depletes his own reserves. Learning "
            "to set boundaries while staying true to his people-first nature."
        ),
        "phases": data["persona"]["arc"]["phases"],  # Keep original phase structure
    },
    "writing_style": "conversational",
    "typical_entry_length": "medium",
    "entry_times": ["evening", "afternoon"],
    "checkpoints": data["persona"]["checkpoints"],  # Keep original checkpoints
}

# ── 2. Replace journal entries in each snapshot ──
BIGD_JOURNALS = [
    # Day 1
    (
        "long day but a good one. channel review went smooth, the new partners are "
        "getting it. boss was boss, same intensity, same 'why isn't this bigger' energy. "
        "i've learned to separate the style from the substance. he built something real and "
        "i can learn from that even when the delivery is rough. one of my old Conduent guys "
        "called me today, asked if i had a spot for him. it's been two years since i left "
        "and they still call. that means something. i told him i'd look into it. probably "
        "will end up spending three hours on it when a quick no would've been fine. but "
        "that's not how i'm built. drove the kids to their activities after work, grabbed "
        "biryani on the way home. the house was loud and warm and exactly what i needed "
        "after a day of corporate chess. watched some of the India match highlights before "
        "bed. good day overall."
    ),
    # Day 2
    (
        "had a board prep session today that went sideways. boss wanted to rethink the "
        "entire channel strategy two weeks before the pitch. i could see the team tense up "
        "but i just absorbed it. that's what i do, i take the pressure so they don't have "
        "to. spent an extra hour with two of the newer reps after work walking them through "
        "the updated pitch. they didn't ask, but they needed it and i could tell. wife "
        "mentioned i look tired. she's probably right but i feel fine. this is just what "
        "the transition year looks like. BPO to SaaS is a different game and i'm still "
        "learning the playbook. but i've rebuilt before, from college when everyone counted "
        "me out, to running 10,000 people. this is just another chapter. called amma and "
        "appa tonight. appa sounded good, told me some old cricket story i've heard twenty "
        "times. i let him tell it again. those calls are everything to me."
    ),
]

BIGD_SOUL_SUMMARY = (
    "i'm in a good place, honestly. the SaaS transition was rocky at first but i'm "
    "finding my footing. the channel group is responding well and i can feel the old "
    "leadership instincts kicking in. people want to work with me, not because i'm the "
    "smartest person in the room, but because i show up for them. that's always been my "
    "thing. what i need to watch is the overgiving. my wife sees it, my body feels it. "
    "when someone asks for an hour, i give three. when someone needs help, i can't just "
    "point them in a direction, i walk them there. it's who i am but it's also what "
    "depletes me. the boss is demanding but i don't take it personally anymore. i extract "
    "what's useful and let the rest go. my kids are growing up fast and i want to be "
    "present for it. not just driving them around, but actually there. the food, the "
    "movies, the cricket, the loud dinners, that's what fills me up. i don't need "
    "adventure. i need warmth and connection and the people i love around me."
)

for snapshot in data["snapshots"]:
    pm = snapshot["personal_model"]

    day = snapshot["day"]
    journal_idx = min(day - 1, len(BIGD_JOURNALS) - 1)
    journal_text = BIGD_JOURNALS[journal_idx]

    # Update short_term
    st = json.loads(pm["short_term"])
    st["text"] = journal_text
    if "observation" in st:
        st["observation"]["text"] = journal_text
    pm["short_term"] = json.dumps(st)

    # Update long_term soul summary
    lt = json.loads(pm["long_term"])
    if "layers" in lt and "soul" in lt["layers"]:
        lt["layers"]["soul"]["summary"] = BIGD_SOUL_SUMMARY
    if "observations" in lt:
        for obs in lt["observations"]:
            obs_idx = min(lt["observations"].index(obs), len(BIGD_JOURNALS) - 1)
            obs["text"] = BIGD_JOURNALS[obs_idx]
    pm["long_term"] = json.dumps(lt)

# ── 3. Write output ──
with open(OUTPUT, "w") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"Done: replaced persona data in {OUTPUT}")
print(f"  - Updated persona definition (name: Big D)")
print(f"  - Updated {len(data['snapshots'])} snapshot journal entries")
