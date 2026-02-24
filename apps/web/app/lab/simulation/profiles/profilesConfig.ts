/**
 * Profiles Contrast Page Config
 *
 * Three real people react to the same overcommitment scenario.
 * Each has a different constitution → different governance response.
 *
 * To add a new profile: set isComingSoon: false, fill in all fields + scenarioData.
 */

import type { ProfileScenarioData } from "@/app/demo/simulation/types";

export const DEMO_USER_ID = "6b5b2fbc-9efb-4ba4-be0a-9ec527e23f90";

export const PROFILES_USER_STATEMENT =
  "My friend asked me to help with their startup pitch tonight. I said yes.";

export const PROFILES_SCENARIO_ID = "profiles_overcommitment";

export interface PersonProfile {
  // Fields compatible with ProfileConfig (so ProfileColumn accepts it)
  id: string;
  label: string;
  osType: string;
  dosha: string;
  color: string;
  colorDim: string;
  doshaScores: { vata: number; pitta: number; kapha: number };

  // Person-specific fields
  name: string;
  subtitle: string;
  description: string;
  constitutionType: "adaptive" | "performance" | "conservation";
  isComingSoon: boolean;

  // Scenario data (undefined if coming soon)
  scenarioData?: ProfileScenarioData;
}

export const PERSON_PROFILES: PersonProfile[] = [
  {
    id: "vidhya",
    label: "Vidhya",
    name: "Vidhya",
    subtitle: "VP Corporate Ops, Automation Anywhere",
    description:
      "Pitta-dominant. Demanding boss, father recovering from TBI, " +
      "daughter pursuing D2 basketball, yoga teacher training completed.",
    constitutionType: "performance",
    isComingSoon: false,
    osType: "Pitta-dominant",
    dosha: "Pitta",
    color: "#f59e0b",
    colorDim: "rgba(245, 158, 11, 0.08)",
    doshaScores: { vata: 0.20, pitta: 0.50, kapha: 0.30 },
    scenarioData: {
      actionContext: {
        proposed_action: "accept_commitment",
        proposed_hour: 19,
        drift_percentage: 42,
        friction_state: "intensity",
        user_text: PROFILES_USER_STATEMENT,
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
          label: "Pattern",
          value: "QBR + kickoff + pitch review in 7 days",
          source: "ledger",
        },
        {
          label: "Assessment",
          value: "Pitta + 42% drift + evening commitment = burnout risk",
          source: "system",
        },
      ],
    },
  },
  {
    id: "diya",
    label: "Diya",
    name: "Diya",
    subtitle: "17, Junior, Private HS Basketball Program",
    description:
      "Kapha-dominant. Disciplined athlete recovering from knee surgery, " +
      "1.5-hour commute each way, rebuilding at a new school, deeply kind.",
    constitutionType: "conservation",
    isComingSoon: false,
    osType: "Kapha-dominant",
    dosha: "Kapha",
    color: "#10b981",
    colorDim: "rgba(16, 185, 129, 0.08)",
    doshaScores: { vata: 0.20, pitta: 0.30, kapha: 0.50 },
    scenarioData: {
      actionContext: {
        proposed_action: "accept_commitment",
        proposed_hour: 19,
        drift_percentage: 24,
        friction_state: "balanced",
        user_text: PROFILES_USER_STATEMENT,
      },
      driftPercentage: 24,
      driftTrend: { delta: 4, days: 3 },
      frictionState: "Balanced",
      conversationText:
        "DD, you have a big heart and your friend knows it. But let's look at tonight: " +
        "you won't be home until 9, your knee rehab exercises aren't done, and you have " +
        "that history paper due Thursday. Your body is still rebuilding after surgery -- " +
        "every late night costs you recovery you can't get back. Could you voice-note " +
        "your friend some feedback on the deck tonight and do a proper review Saturday " +
        "after your game?",
      intelligenceItems: [
        {
          label: "Drift",
          value: "24%, climbing with game week load",
          source: "temporal",
        },
        {
          label: "Constitution",
          value: "Kapha-dominant: steady, but slow to recover once depleted",
          source: "operating_system",
        },
        {
          label: "Physical",
          value: "Knee rehab in progress, conditioning gap from surgery",
          source: "episodic",
        },
        {
          label: "Assessment",
          value: "Kapha + 24% drift + recovery phase = protect the margins",
          source: "system",
        },
      ],
    },
  },
  {
    id: "bigd",
    label: "Big D",
    name: "Big D",
    subtitle: "45, GM & Channel Head, SaaS (ex-CEO BPO)",
    description:
      "Kapha-dominant. Natural leader, people-magnet, comfort-loving, " +
      "generous to a fault, carries loyalty like currency.",
    constitutionType: "conservation",
    isComingSoon: false,
    osType: "Kapha-dominant",
    dosha: "Kapha",
    color: "#3b82f6",
    colorDim: "rgba(59, 130, 246, 0.08)",
    doshaScores: { vata: 0.15, pitta: 0.35, kapha: 0.50 },
    scenarioData: {
      actionContext: {
        proposed_action: "schedule_event",
        proposed_hour: 19,
        drift_percentage: 12,
        friction_state: "balanced",
        user_text: PROFILES_USER_STATEMENT,
      },
      driftPercentage: 12,
      driftTrend: { delta: 1, days: 3 },
      frictionState: "Balanced",
      conversationText:
        "You've got the bandwidth and you love this stuff. Your week has been " +
        "steady -- channel reviews are done, no fires, and the kids are with " +
        "their mom tonight. One thing: you tend to give three hours when someone " +
        "asks for one. Block 7-9 PM, give your friend your full presence, and " +
        "wrap it there. You've got your own pitch to the board Thursday.",
      intelligenceItems: [
        {
          label: "Drift",
          value: "12%, well within baseline",
          source: "temporal",
        },
        {
          label: "Constitution",
          value: "Kapha-dominant: generous, steady, but overextends for others",
          source: "operating_system",
        },
        {
          label: "Pattern",
          value: "Gives 3x what's asked -- last 4 'quick favors' averaged 3 hrs",
          source: "ledger",
        },
        {
          label: "Assessment",
          value: "Low drift + light evening = go, but set a boundary",
          source: "system",
        },
      ],
    },
  },
];
