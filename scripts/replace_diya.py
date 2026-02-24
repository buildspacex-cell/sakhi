#!/usr/bin/env python3
"""Replace hormonal_harmony persona data with Diya's real profile"""

import json

INPUT = "apps/web/public/simulation/hormonal_harmony.json"
OUTPUT = INPUT

with open(INPUT, "r") as f:
    data = json.load(f)

# ── 1. Replace persona definition ──
data["persona"] = {
    "id": "hormonal_harmony",
    "name": "Diya",
    "description": (
        "A 17-year-old high school junior in San Jose, California. Disciplined basketball "
        "player at a competitive private school on full financial aid. Kapha-dominant: steady, "
        "kind, deeply loyal, resilient. Recovering from knee surgery (sophomore year April). "
        "Left her friend group for a better athletic opportunity. Commutes 1-1.5 hours each way. "
        "Quietly ambitious with a heart for service. Wants to play D2 basketball and solve "
        "poverty at its root."
    ),
    "dosha_baseline": {"vata": 0.20, "pitta": 0.30, "kapha": 0.50},
    "rhythm": {
        "morning": "low",
        "afternoon": "high",
        "evening": "low",
        "best_work_time": "afternoon",
        "sleep_quality": "poor",
    },
    "traits": [
        {
            "name": "disciplined_athlete",
            "description": "Self-motivated, willingly sacrifices social life for basketball",
            "intensity": 0.9,
            "journal_patterns": [
                "practice was tough but I pushed through",
                "left at 6:45, home at 9",
                "the grind is worth it",
                "my body knows the work",
            ],
        },
        {
            "name": "deeply_kind",
            "description": "Considerate beyond her years, feels things deeply",
            "intensity": 0.85,
            "journal_patterns": [
                "I noticed someone struggling",
                "couldn't just walk away",
                "it matters to me that people are okay",
                "my heart hurts for them",
            ],
        },
        {
            "name": "quietly_ambitious",
            "description": "Driven but doesn't broadcast it, internal fire",
            "intensity": 0.8,
            "journal_patterns": [
                "I know what I want",
                "D2 is the goal",
                "I'm not there yet but I will be",
                "every rep counts",
            ],
        },
        {
            "name": "rebuilding_resilience",
            "description": "Processing school change, knee surgery, and social reset",
            "intensity": 0.75,
            "journal_patterns": [
                "it's hard being the new one",
                "my knee feels stronger today",
                "I miss my old friends",
                "starting over takes courage",
            ],
        },
    ],
    "life_context": {
        "occupation": "High School Junior, Competitive Basketball Program (Full Financial Aid)",
        "relationships": {
            "parents": "deeply loves her family, attached, shows affection in subtle steady ways",
            "younger_sibling": "protective, observant, quietly supportive of younger brother",
            "old_friends": "maintains a couple of deep friendships from previous school",
            "new_school": "forming bonds slowly, coaches respect her, smaller circle",
            "coaches": "see her potential, find her coachable and disciplined",
        },
        "current_challenges": [
            "Knee rehab after surgery (6-7 months recovery)",
            "Conditioning and stamina gap from missing summer training",
            "Not getting the game minutes she hoped for this season",
            "Practice performance doesn't translate to game confidence yet",
            "1-1.5 hour commute each way, exhausting daily schedule",
            "Balancing homework with extreme physical demands",
        ],
        "values": ["Service", "Discipline", "Integrity", "Deep connection", "Impact"],
        "hobbies": [
            "basketball (where she feels most alive)",
            "spending time with family",
            "deep conversations with close friends",
        ],
    },
    "arc": {
        "name": "Discipline and Recovery",
        "description": (
            "A young athlete rebuilding physically and socially after knee surgery "
            "and a school change. Balancing an intense daily schedule with recovery, "
            "learning to trust her body again in competition, and finding her place "
            "in a new environment."
        ),
        "phases": data["persona"]["arc"]["phases"],  # Keep original phase structure
    },
    "writing_style": "honest",
    "typical_entry_length": "medium",
    "entry_times": ["evening"],
    "checkpoints": data["persona"]["checkpoints"],  # Keep original checkpoints
}

# ── 2. Replace journal entries in each snapshot ──
DIYA_JOURNALS = [
    # Day 1
    (
        "got home at 9 again. practice was good though, coach said my lateral movement is "
        "looking sharper since rehab. my knee felt solid today which is huge because last "
        "week i was still guarding it on cuts. the drive home was long, I almost fell asleep "
        "in the car. i have a history paper due thursday that i haven't started and i know "
        "i should be working on it right now but my body just wants to shut down. i miss my "
        "old school sometimes. not the basketball program, that's better here, but the people. "
        "my best friend texted me today and it made me smile but also made me feel the distance. "
        "at the new school i'm getting closer with a couple of girls on the team but it's not "
        "the same yet. it takes time, i know that. dad picked me up today and we didn't even "
        "talk much but just having him there felt good. i looked at my little brother's math "
        "homework on the counter when i got home and thought about how different our days are. "
        "he doesn't know how lucky he is to just be a kid. i wouldn't trade my path though. "
        "this is what D2 costs and i'm willing to pay it."
    ),
    # Day 2
    (
        "rough game today. i only got about 8 minutes and didn't play the way i know i can. "
        "in practice i've been hitting shots and making reads but when the game starts "
        "something tightens up. coach pulled me aside after and said 'trust the work, it'll "
        "come.' i believe him but it's frustrating. the girls who trained all summer together "
        "have this chemistry i'm still catching up to. i was rehabbing while they were building "
        "that. no one's fault, just the reality. my knee feels fine physically, it's my head "
        "that needs to catch up. the drive home was quiet. i could tell my parents wanted to "
        "say something encouraging but they know me well enough to give me space. i ate "
        "dinner and went straight to homework. there's a calc quiz tomorrow i haven't studied "
        "for. some days this schedule feels impossible but then i think about the girls who "
        "would give anything to be in my position, full aid at a program like this. i'm not "
        "going to waste it. i just need to be patient with myself and that's the hardest part."
    ),
]

DIYA_SOUL_SUMMARY = (
    "i'm in a rebuilding year and some days that feels exciting and some days it feels "
    "lonely. the knee is getting stronger every week and coach sees it. but games are "
    "different from practice. in practice i can play free, i can make mistakes and try "
    "again. in games there's this pressure i put on myself to prove i belong here, that "
    "leaving my old school was worth it, that the surgery didn't take anything permanent. "
    "i know it didn't, my body is telling me that, but my mind hasn't caught up yet. "
    "the commute is brutal. leaving at 6:45 and getting home at 9 doesn't leave room "
    "for much. homework gets done late, sleep is never enough, and social life is basically "
    "just my teammates and a few texts to my old friends. but i chose this. i chose "
    "challenge over comfort because i know that's where growth lives. i love my family "
    "so much. my parents sacrifice a lot for me to be here and i feel that every single "
    "day. my little brother looks up to me and i want to show him that hard things are "
    "worth doing. and underneath all the basketball, i carry this feeling that i'm meant "
    "to do something bigger. not for fame or money, but to actually help people who don't "
    "have what i have. basketball is my passion. service is my purpose."
)

for snapshot in data["snapshots"]:
    pm = snapshot["personal_model"]

    day = snapshot["day"]
    journal_idx = min(day - 1, len(DIYA_JOURNALS) - 1)
    journal_text = DIYA_JOURNALS[journal_idx]

    # Update short_term
    st = json.loads(pm["short_term"])
    st["text"] = journal_text
    if "observation" in st:
        st["observation"]["text"] = journal_text
    pm["short_term"] = json.dumps(st)

    # Update long_term soul summary
    lt = json.loads(pm["long_term"])
    if "layers" in lt and "soul" in lt["layers"]:
        lt["layers"]["soul"]["summary"] = DIYA_SOUL_SUMMARY
    if "observations" in lt:
        for obs in lt["observations"]:
            obs_idx = min(lt["observations"].index(obs), len(DIYA_JOURNALS) - 1)
            obs["text"] = DIYA_JOURNALS[obs_idx]
    pm["long_term"] = json.dumps(lt)

# ── 3. Write output ──
with open(OUTPUT, "w") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"Done: replaced persona data in {OUTPUT}")
print(f"  - Updated persona definition (name: Diya)")
print(f"  - Updated {len(data['snapshots'])} snapshot journal entries")
