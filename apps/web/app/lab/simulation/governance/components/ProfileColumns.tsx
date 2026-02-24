"use client";

import type { GateDecision, LedgerEvent, ScenarioConfig } from "@/app/demo/simulation/types";
import { GOV_PROFILES } from "../theme";
import ProfileColumn from "./ProfileColumn";

interface ProfileColumnsProps {
  scenario: ScenarioConfig;
  decisions: Record<string, GateDecision | null>;
  ledgerEvents: Record<string, LedgerEvent[]>;
  loading?: boolean;
}

export default function ProfileColumns({
  scenario,
  decisions,
  ledgerEvents,
  loading,
}: ProfileColumnsProps) {
  const actions = GOV_PROFILES.map((p) => decisions[p.id]?.action).filter(Boolean);
  const allSame = actions.length > 0 && actions.every((a) => a === actions[0]);
  const hasDivergence = actions.length > 1 && !allSame;

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(3, 1fr)",
        gap: 12,
        width: "100%",
      }}
    >
      {GOV_PROFILES.map((profile) => {
        const profileData = scenario.profiles[profile.id];
        if (!profileData) return null;

        const decision = decisions[profile.id] || null;
        const events = ledgerEvents[profile.id] || [];

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
