"""
Test constants and demo data.

These constants are used across tests to ensure consistency
and avoid hardcoding UUIDs throughout the test suite.
"""

# ─────────────────────────────────────────────────────────────────────────────
# Demo Users
# ─────────────────────────────────────────────────────────────────────────────

# Primary demo user - has full data seeded
DEMO_USER_ID = "6b5b2fbc-9efb-4ba4-be0a-9ec527e23f90"
DEMO_USER_NAME = "Vidhya"
DEMO_USER_EMAIL = "vidhya@demo.sakhi.ai"

# Secondary test user for multi-user scenarios
TEST_USER_ID = "test-user-0001-0001-0001-000000000001"
TEST_USER_NAME = "Test User"
TEST_USER_EMAIL = "test@test.sakhi.ai"


# ─────────────────────────────────────────────────────────────────────────────
# Operating Systems (Friction Framework)
# ─────────────────────────────────────────────────────────────────────────────

OPERATING_SYSTEM_ADAPTIVE = {
    "type": "adaptive",
    "primary_dosha": "vata",
    "characteristics": ["creative", "variable", "quick-thinking"],
    "strengths": ["adaptability", "creativity", "enthusiasm"],
    "challenges": ["consistency", "grounding", "completion"],
}

OPERATING_SYSTEM_PERFORMANCE = {
    "type": "performance",
    "primary_dosha": "pitta",
    "characteristics": ["driven", "intense", "sharp"],
    "strengths": ["focus", "determination", "leadership"],
    "challenges": ["patience", "delegation", "rest"],
}

OPERATING_SYSTEM_CONSERVATION = {
    "type": "conservation",
    "primary_dosha": "kapha",
    "characteristics": ["steady", "grounded", "enduring"],
    "strengths": ["stability", "patience", "loyalty"],
    "challenges": ["change", "motivation", "letting go"],
}


# ─────────────────────────────────────────────────────────────────────────────
# Sample Messages (for conversation tests)
# ─────────────────────────────────────────────────────────────────────────────

SAMPLE_MESSAGES = {
    "greeting": "Hi Sakhi, how are you today?",
    "stress": "I've been feeling really stressed about work lately.",
    "food": "What should I eat for dinner tonight?",
    "sleep": "I'm having trouble sleeping, any suggestions?",
    "exercise": "I want to start exercising more regularly.",
    "mood_low": "I'm feeling a bit down today.",
    "mood_high": "I had such a great day!",
    "question_about_self": "Why do I always procrastinate?",
    "planning": "Can you help me plan my day tomorrow?",
}


# ─────────────────────────────────────────────────────────────────────────────
# Sample Journal Entries
# ─────────────────────────────────────────────────────────────────────────────

SAMPLE_JOURNAL_ENTRIES = [
    {
        "title": "Morning Reflection",
        "content": "Woke up feeling refreshed. Had a good night's sleep for once.",
        "mood": "positive",
    },
    {
        "title": "Work Stress",
        "content": "Big deadline coming up. Feeling the pressure but trying to stay calm.",
        "mood": "anxious",
    },
    {
        "title": "Evening Wind Down",
        "content": "Good walk after dinner. The fresh air really helped clear my mind.",
        "mood": "calm",
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# API Endpoints
# ─────────────────────────────────────────────────────────────────────────────

API_BASE_URL = "http://localhost:8000"
API_V2_TURN = f"{API_BASE_URL}/v2/turn"
API_FRICTION_STATE = f"{API_BASE_URL}/friction-framework/state/current"
API_MEMORY_RECALL = f"{API_BASE_URL}/memory/recall"
