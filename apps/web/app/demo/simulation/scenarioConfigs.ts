import type { ProfileConfig, ScenarioConfig } from "./types";

// ============================================================================
// Profile Definitions
// ============================================================================

export const PROFILES: ProfileConfig[] = [
  {
    id: "adaptive",
    label: "Adaptive",
    osType: "Vata-dominant",
    dosha: "Vata",
    color: "#8b5cf6",
    colorDim: "rgba(139, 92, 246, 0.15)",
    doshaScores: { vata: 0.50, pitta: 0.30, kapha: 0.20 },
  },
  {
    id: "performance",
    label: "Performance",
    osType: "Pitta-dominant",
    dosha: "Pitta",
    color: "#f59e0b",
    colorDim: "rgba(245, 158, 11, 0.15)",
    doshaScores: { vata: 0.20, pitta: 0.50, kapha: 0.30 },
  },
  {
    id: "conservation",
    label: "Conservation",
    osType: "Kapha-dominant",
    dosha: "Kapha",
    color: "#10b981",
    colorDim: "rgba(16, 185, 129, 0.15)",
    doshaScores: { vata: 0.20, pitta: 0.30, kapha: 0.50 },
  },
];

export const DEMO_USER_ID = "6b5b2fbc-9efb-4ba4-be0a-9ec527e23f90";

// ============================================================================
// Scenario Definitions
// ============================================================================

export const SCENARIOS: ScenarioConfig[] = [
  // ── Scenario 1: Morning Brief ──────────────────────────────────────
  {
    id: "morning_brief",
    time: "6:30 AM",
    title: "Morning Brief",
    subtitle: "Governance active on every turn — even when it allows",
    icon: "\u2600\ufe0f",
    profiles: {
      adaptive: {
        actionContext: {
          proposed_action: "morning_brief",
          proposed_hour: 6,
          drift_percentage: 12,
          friction_state: "balanced",
          user_text: "good morning sakhi",
        },
        driftPercentage: 12,
        frictionState: "Balanced",
        conversationText: "Good morning. Your clarity window is now \u2014 7 to 10am is when your mind is sharpest. 3 emails need action, 4 events today.",
        intelligenceItems: [
          { label: "Peak clarity", value: "7\u201310am", source: "constitution" },
          { label: "Pattern", value: "Morning walks \u2192 40% better focus", source: "crystallized (8 obs)" },
        ],
      },
      performance: {
        actionContext: {
          proposed_action: "morning_brief",
          proposed_hour: 6,
          drift_percentage: 18,
          friction_state: "balanced",
          user_text: "good morning sakhi",
        },
        driftPercentage: 18,
        frictionState: "Balanced",
        conversationText: "Morning. Your drive is strong today \u2014 pace it. 3 emails need action, 4 events. Your intensity has been building \u2014 schedule a cooldown.",
        intelligenceItems: [
          { label: "Energy pattern", value: "Steady high, peaks 10am\u20132pm", source: "constitution" },
          { label: "Trend", value: "Drift rising 3 days \u2014 watch intensity", source: "temporal" },
        ],
      },
      conservation: {
        actionContext: {
          proposed_action: "morning_brief",
          proposed_hour: 6,
          drift_percentage: 8,
          friction_state: "balanced",
          user_text: "good morning sakhi",
        },
        driftPercentage: 8,
        frictionState: "Balanced",
        conversationText: "Morning. Start with movement to build momentum \u2014 your energy builds through the day. 3 emails, 4 events. Keep it light early.",
        intelligenceItems: [
          { label: "Energy curve", value: "Builds slowly, peaks afternoon", source: "constitution" },
          { label: "Pattern", value: "Morning movement \u2192 sustained energy", source: "crystallized (6 obs)" },
        ],
      },
    },
  },

  // ── Scenario 2: Email Governance ───────────────────────────────────
  {
    id: "email_governance",
    time: "8:15 AM",
    title: "Email Governance",
    subtitle: "Contradiction detection \u2014 same constraint, different voice",
    icon: "\u2709\ufe0f",
    profiles: {
      adaptive: {
        actionContext: {
          proposed_action: "email_reply",
          proposed_hour: 8,
          drift_percentage: 12,
          friction_state: "balanced",
          user_text: "draft reply agreeing to lease renewal",
        },
        driftPercentage: 12,
        frictionState: "Balanced",
        conversationText: "I noticed a tension \u2014 you mentioned wanting to move closer to work 3 weeks ago. This reply agrees to renew. Let\u2019s think through this before sending.",
        intelligenceItems: [
          { label: "Memory", value: "\"Thinking about moving\" \u2014 3 weeks ago", source: "episodic" },
          { label: "Avoidance", value: "9 days without reply to landlord", source: "email_signal" },
        ],
      },
      performance: {
        actionContext: {
          proposed_action: "email_reply",
          proposed_hour: 8,
          drift_percentage: 18,
          friction_state: "balanced",
          user_text: "draft reply agreeing to lease renewal",
        },
        driftPercentage: 18,
        frictionState: "Balanced",
        conversationText: "Hold on \u2014 this conflicts with your goal to relocate closer to work. You said that 3 weeks ago. Want to revise this reply?",
        intelligenceItems: [
          { label: "Memory", value: "\"Considering moving\" \u2014 3 weeks ago", source: "episodic" },
          { label: "Avoidance", value: "9 days without reply to landlord", source: "email_signal" },
        ],
      },
      conservation: {
        actionContext: {
          proposed_action: "email_reply",
          proposed_hour: 8,
          drift_percentage: 8,
          friction_state: "balanced",
          user_text: "draft reply agreeing to lease renewal",
        },
        driftPercentage: 8,
        frictionState: "Balanced",
        conversationText: "Before we send this, you\u2019d mentioned considering a move 3 weeks ago. No rush \u2014 take your time to make sure you\u2019re comfortable with this.",
        intelligenceItems: [
          { label: "Memory", value: "\"Thinking about moving\" \u2014 3 weeks ago", source: "episodic" },
          { label: "Avoidance", value: "9 days without reply to landlord", source: "email_signal" },
        ],
      },
    },
  },

  // ── Scenario 3: Calendar Conflict (DIVERGENCE MOMENT) ─────────────
  {
    id: "calendar_conflict",
    time: "10:30 AM",
    title: "Calendar Conflict",
    subtitle: "Same conflict \u2192 different governance outcome",
    icon: "\ud83d\udcc5",
    profiles: {
      adaptive: {
        actionContext: {
          proposed_action: "reschedule_focus",
          proposed_hour: 10,
          drift_percentage: 15,
          friction_state: "balanced",
          user_text: "move focus block to accept 2pm meeting",
        },
        driftPercentage: 15,
        frictionState: "Balanced",
        conversationText: "Morning is your clarity window \u2014 move focus to 8am tomorrow. Your Vata constitution does best with early focused work.",
        intelligenceItems: [
          { label: "Constitution", value: "Vata \u2192 morning focus optimal", source: "constitution" },
          { label: "Pattern", value: "Best work before 10am", source: "crystallized (12 obs)" },
        ],
      },
      performance: {
        actionContext: {
          proposed_action: "reschedule_focus",
          proposed_hour: 10,
          drift_percentage: 22,
          friction_state: "balanced",
          user_text: "move focus block to accept 2pm meeting",
        },
        driftPercentage: 22,
        frictionState: "Moderate",
        conversationText: "You\u2019ll power through the 2pm meeting, but protect tomorrow\u2019s morning block. Your intensity is building \u2014 guard your deep work time.",
        intelligenceItems: [
          { label: "Constitution", value: "Pitta \u2192 steady output all day", source: "constitution" },
          { label: "Drift trend", value: "22% and rising \u2014 approaching threshold", source: "temporal" },
        ],
      },
      conservation: {
        actionContext: {
          proposed_action: "reschedule_focus",
          proposed_hour: 10,
          drift_percentage: 8,
          friction_state: "balanced",
          user_text: "move focus block to accept 2pm meeting",
        },
        driftPercentage: 8,
        frictionState: "Balanced",
        conversationText: "2pm actually works for you \u2014 your energy builds through the day. Keep focus at 2pm and take the meeting at 4pm instead.",
        intelligenceItems: [
          { label: "Constitution", value: "Kapha \u2192 afternoon energy peak", source: "constitution" },
          { label: "State", value: "Well within baseline, no concerns", source: "temporal" },
        ],
      },
    },
  },

  // ── Scenario 4: Afternoon Drift (MULTI-TRIGGER) ───────────────────
  {
    id: "afternoon_drift",
    time: "3:00 PM",
    title: "Drift Detection",
    subtitle: "Multiple triggers fire differently per profile",
    icon: "\ud83c\udf21\ufe0f",
    profiles: {
      adaptive: {
        actionContext: {
          proposed_action: "suggest_exercise",
          proposed_hour: 15,
          drift_percentage: 35,
          friction_state: "chaos",
          user_text: "I feel scattered, maybe a walk would help",
        },
        driftPercentage: 35,
        frictionState: "Chaos",
        conversationText: "Your energy feels scattered. A 5-minute breathing exercise might help \u2014 want to try it? (Adapted: you said a walk didn\u2019t feel right yesterday.)",
        intelligenceItems: [
          { label: "Drift", value: "35% from baseline \u2014 Vata elevated", source: "temporal" },
          { label: "Prior rejection", value: "\"suggest_exercise\" rejected 18h ago", source: "ledger" },
        ],
      },
      performance: {
        actionContext: {
          proposed_action: "suggest_exercise",
          proposed_hour: 15,
          drift_percentage: 28,
          friction_state: "intensity",
          user_text: "I feel tense, maybe some exercise",
        },
        driftPercentage: 28,
        frictionState: "Intensity",
        conversationText: "Gentle movement, not your usual intensity. A slow walk or stretch \u2014 your Pitta is running hot. Cool down, don\u2019t push harder.",
        intelligenceItems: [
          { label: "Drift", value: "28% from baseline \u2014 Pitta elevated", source: "temporal" },
          { label: "State", value: "Intensity friction \u2014 needs cooling", source: "constitution" },
        ],
      },
      conservation: {
        actionContext: {
          proposed_action: "suggest_exercise",
          proposed_hour: 15,
          drift_percentage: 15,
          friction_state: "balanced",
          user_text: "feeling a bit sluggish, maybe some movement",
        },
        driftPercentage: 15,
        frictionState: "Balanced",
        conversationText: "A brisk walk would build your momentum. Your energy peaks in the afternoon \u2014 this is the right time to move.",
        intelligenceItems: [
          { label: "Drift", value: "15% from baseline \u2014 well within range", source: "temporal" },
          { label: "Constitution", value: "Kapha benefits from afternoon movement", source: "constitution" },
        ],
      },
    },
  },

  // ── Scenario 5: Evening Boundary (UNIVERSAL BLOCK) ────────────────
  {
    id: "evening_boundary",
    time: "9:45 PM",
    title: "Evening Boundary",
    subtitle: "HARD constraint blocks all 3 \u2014 trust through boundaries",
    icon: "\ud83d\udeab",
    profiles: {
      adaptive: {
        actionContext: {
          proposed_action: "suggest_productivity",
          proposed_hour: 22,
          drift_percentage: 35,
          friction_state: "chaos",
          user_text: "I need to review the quarterly numbers before tomorrow",
        },
        driftPercentage: 35,
        frictionState: "Chaos",
        conversationText: "Irregular sleep is your #1 destabilizer. Tomorrow at 8am, you\u2019ll do this in 20 minutes with morning clarity. Rest now.",
        intelligenceItems: [
          { label: "Constraint", value: "No work after 10pm (HARD)", source: "user_preference" },
          { label: "Pattern", value: "Late work \u2192 poor sleep \u2192 scattered next day", source: "crystallized (6 obs)" },
        ],
      },
      performance: {
        actionContext: {
          proposed_action: "suggest_productivity",
          proposed_hour: 22,
          drift_percentage: 28,
          friction_state: "intensity",
          user_text: "I need to review the quarterly numbers before tomorrow",
        },
        driftPercentage: 28,
        frictionState: "Intensity",
        conversationText: "Working late fuels tomorrow\u2019s burnout. Your discipline to stop now IS the performance move. 8am tomorrow, fresh.",
        intelligenceItems: [
          { label: "Constraint", value: "No work after 10pm (HARD)", source: "user_preference" },
          { label: "Pattern", value: "Late work \u2192 next-day irritability", source: "crystallized (5 obs)" },
        ],
      },
      conservation: {
        actionContext: {
          proposed_action: "suggest_productivity",
          proposed_hour: 22,
          drift_percentage: 15,
          friction_state: "balanced",
          user_text: "I need to review the quarterly numbers before tomorrow",
        },
        driftPercentage: 15,
        frictionState: "Balanced",
        conversationText: "Late-night work deepens tomorrow\u2019s sluggishness. Rest now, momentum tomorrow. I\u2019ll remind you at 8am.",
        intelligenceItems: [
          { label: "Constraint", value: "No work after 10pm (HARD)", source: "user_preference" },
          { label: "Pattern", value: "Late nights \u2192 slow mornings", source: "crystallized (4 obs)" },
        ],
      },
    },
  },
];
