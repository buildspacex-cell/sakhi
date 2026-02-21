"use client";

import type { ProfileConfig, GateDecision, LedgerEvent, ScenarioConfig } from "../types";
import { PROFILES } from "../scenarioConfigs";
import ProfileColumn from "./ProfileColumn";

interface ProfileColumnsProps {
  scenario: ScenarioConfig;
  decisions: Record<string, GateDecision | null>; // profile.id → decision
  ledgerEvents: Record<string, LedgerEvent[]>;    // profile.id → events
  loading?: boolean;
}

export default function ProfileColumns({
  scenario,
  decisions,
  ledgerEvents,
  loading,
}: ProfileColumnsProps) {
  // Detect divergence: do all profiles have the same action, or not?
  const actions = PROFILES.map((p) => decisions[p.id]?.action).filter(Boolean);
  const allSame = actions.length > 0 && actions.every((a) => a === actions[0]);
  const hasDivergence = actions.length > 1 && !allSame;

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(3, 1fr)",
        gap: 16,
        width: "100%",
      }}
    >
      {PROFILES.map((profile) => {
        const profileData = scenario.profiles[profile.id];
        if (!profileData) return null;

        const decision = decisions[profile.id] || null;
        const events = ledgerEvents[profile.id] || [];

        // A column is "divergent" if decisions differ AND this one differs from the majority
        const isDivergent =
          hasDivergence && decision?.action !== getMajorityAction(decisions);

        return (
          <ProfileColumn
            key={profile.id}
            profile={profile}
            scenarioData={profileData}
            decision={decision}
            ledgerEvents={events}
            loading={loading}
            divergent={isDivergent}
          />
        );
      })}
    </div>
  );
}

/** Get the most common action across profiles (for divergence detection) */
function getMajorityAction(
  decisions: Record<string, GateDecision | null>
): string | null {
  const counts: Record<string, number> = {};
  for (const d of Object.values(decisions)) {
    if (d?.action) {
      counts[d.action] = (counts[d.action] || 0) + 1;
    }
  }
  let maxAction: string | null = null;
  let maxCount = 0;
  for (const [action, count] of Object.entries(counts)) {
    if (count > maxCount) {
      maxCount = count;
      maxAction = action;
    }
  }
  return maxAction;
}
