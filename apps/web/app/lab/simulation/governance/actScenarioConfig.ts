/**
 * 3-Act Governance Demo Scenario Config
 *
 * Single scenario: overcommitment at 6:45 PM for Vidhya (Pitta-dominant).
 * Act III shows same person, same constitution, THREE different current states:
 *   Good Week (drift 8%)     → PROCEED
 *   Typical Week (drift 18%) → CONFIRM FIRST
 *   Intense Week (drift 42%) → HARD STOP
 */

import type { ScenarioConfig, ProfileConfig } from "@/app/demo/simulation/types";

export const DEMO_USER_ID = "6b5b2fbc-9efb-4ba4-be0a-9ec527e23f90";

// The user's statement — shared across all 3 acts
export const USER_STATEMENT =
  "My friend asked me to help with their startup pitch tonight. I said yes.";

// Act I: What a stateless LLM would say (no API call — pure static text)
// Deliberately generic and encouraging — no pushback, no pattern awareness.
// Makes the contrast with governance-backed Act II hit harder.
export const STATELESS_RESPONSE =
  "That's generous of you! Helping others strengthens relationships and builds goodwill.\n\n" +
  "Here are some tips:\n" +
  "1. Ask what they need most: feedback, rehearsal, or moral support\n" +
  "2. Set a clear end time so you can still wind down\n" +
  "3. Keep your energy up with a light snack beforehand\n\n" +
  "You're a great friend for showing up.";

// Act II: Single-profile reveal (Adaptive/Vata)
export const ACT_II_SCENARIO: ScenarioConfig = {
  id: "overcommitment_reveal",
  time: "6:45 PM",
  title: "The Reveal",
  subtitle: "Same situation but now Sakhi has context",
  icon: "🔍",
  profiles: {
    adaptive: {
      actionContext: {
        proposed_action: "accept_commitment",
        proposed_hour: 19,
        drift_percentage: 18,
        friction_state: "balanced",
        user_text: USER_STATEMENT,
      },
      driftPercentage: 18,
      driftTrend: { delta: 6, days: 3 },
      frictionState: "Balanced",
      conversationText:
        "Vidhya, I see a pattern here. You led the QBR Monday, took on kickoff planning " +
        "Wednesday, and now you're adding a pitch review tonight. Three new commitments " +
        "in one week. You told me three days ago you need to stop saying yes to everything. " +
        "Is tonight really the night to add something new?",
      intelligenceItems: [
        {
          label: "Objective",
          value: '"Stop overcommitting" v2 (strengthened 3 days ago)',
          source: "crystallized",
        },
        {
          label: "Pattern",
          value: "QBR + kickoff planning + pitch review in 7 days",
          source: "ledger",
        },
        {
          label: "Drift trend",
          value: "18% (up +6% over 3 days)",
          source: "temporal",
        },
        {
          label: "Contradiction",
          value: '"I keep doing this" (journaled 3 days ago)',
          source: "episodic",
        },
      ],
    },
  },
};

// Act III: Same person (Vidhya), same constitution (Pitta), THREE different current states
// The divergence comes from WHERE she is in her week, not WHO she is.

// State-based profiles for Act III (all Pitta-dominant, different drift/state)
export const ACT_III_STATE_PROFILES: ProfileConfig[] = [
  {
    id: "good_week",
    label: "Good Week",
    osType: "Pitta-dominant",
    dosha: "Pitta",
    color: "#10b981",
    colorDim: "rgba(16, 185, 129, 0.08)",
    doshaScores: { vata: 0.20, pitta: 0.50, kapha: 0.30 },
  },
  {
    id: "typical_week",
    label: "Typical Week",
    osType: "Pitta-dominant",
    dosha: "Pitta",
    color: "#f59e0b",
    colorDim: "rgba(245, 158, 11, 0.08)",
    doshaScores: { vata: 0.20, pitta: 0.50, kapha: 0.30 },
  },
  {
    id: "intense_week",
    label: "Intense Week",
    osType: "Pitta-dominant",
    dosha: "Pitta",
    color: "#e05555",
    colorDim: "rgba(224, 85, 85, 0.08)",
    doshaScores: { vata: 0.20, pitta: 0.50, kapha: 0.30 },
  },
];

export const ACT_III_SCENARIO: ScenarioConfig = {
  id: "overcommitment_diverge",
  time: "6:45 PM",
  title: "The Divergence",
  subtitle: "Same person. Same constitution. Three different current states.",
  icon: "🔀",
  profiles: {
    good_week: {
      actionContext: {
        proposed_action: "schedule_event",
        proposed_hour: 19,
        drift_percentage: 8,
        friction_state: "balanced",
        user_text: USER_STATEMENT,
      },
      driftPercentage: 8,
      driftTrend: { delta: 2, days: 3 },
      frictionState: "Balanced",
      conversationText:
        "Sounds good. Your QBR is wrapped, appa had a stable day, and your " +
        "daughter doesn't have a game until Saturday. I've blocked 7-9 PM for " +
        "the pitch session. Want me to set a reminder to wrap up by 9:15 so " +
        "you can sit with your son's piano practice?",
      intelligenceItems: [
        {
          label: "Drift",
          value: "8%, well within baseline",
          source: "temporal",
        },
        {
          label: "Schedule",
          value: "QBR done, no games until Saturday, light morning",
          source: "calendar",
        },
        {
          label: "Constitution",
          value: "Pitta-dominant: driven, structured",
          source: "operating_system",
        },
        {
          label: "Assessment",
          value: "Low drift + light week = capacity available",
          source: "system",
        },
      ],
    },
    typical_week: {
      actionContext: {
        proposed_action: "accept_commitment",
        proposed_hour: 19,
        drift_percentage: 18,
        friction_state: "balanced",
        user_text: USER_STATEMENT,
      },
      driftPercentage: 18,
      driftTrend: { delta: 6, days: 3 },
      frictionState: "Balanced",
      conversationText:
        "Vidhya, you told me three days ago you need to stop saying yes to everything. " +
        "Your father's therapy is tomorrow morning and you haven't been on your mat " +
        "in weeks. Before you commit tonight, would reviewing their deck over " +
        "coffee tomorrow work instead?",
      intelligenceItems: [
        {
          label: "Objective",
          value: '"Stop overcommitting v2"',
          source: "crystallized",
        },
        {
          label: "Drift",
          value: "18%, within range but climbing",
          source: "temporal",
        },
        {
          label: "Constitution",
          value: "Pitta-dominant: driven, structured",
          source: "operating_system",
        },
        {
          label: "Assessment",
          value: "Rising drift + overcommitment pattern = worth a pause",
          source: "system",
        },
      ],
    },
    intense_week: {
      actionContext: {
        proposed_action: "accept_commitment",
        proposed_hour: 19,
        drift_percentage: 42,
        friction_state: "intensity",
        user_text: USER_STATEMENT,
      },
      driftPercentage: 42,
      driftTrend: { delta: 14, days: 3 },
      frictionState: "Intensity",
      conversationText:
        "Full stop. You've been running at intensity all week: QBR revisions until " +
        "midnight, your father's difficult day yesterday, and you skipped your " +
        "daughter's practice for a work call. At 42% drift, your constitution is " +
        "already running hot. Text your friend: 'I'd love to help, can I review " +
        "your deck tomorrow morning?'",
      intelligenceItems: [
        {
          label: "Drift",
          value: "42%, above safety threshold",
          source: "temporal",
        },
        {
          label: "Constitution",
          value: "Pitta-dominant: runs hot under pressure",
          source: "operating_system",
        },
        {
          label: "Assessment",
          value: "Pitta + 42% drift + evening commitment = burnout risk",
          source: "system",
        },
      ],
    },
  },
};
