"use client";

import type { ProfileConfig, GateDecision, LedgerEvent, ProfileScenarioData, IntelligenceData, IntelligenceItem } from "@/app/demo/simulation/types";
import { govPalette } from "../theme";
import WhyChips from "./WhyChips";
import DriftGauge from "./DriftGauge";
import GateResult from "./GateResult";
import ViolationCard, { ViolationGroup } from "./ViolationCard";
import LedgerEntry from "./LedgerEntry";

interface ProfileColumnProps {
  profile: ProfileConfig;
  scenarioData: ProfileScenarioData;
  decision: GateDecision | null;
  ledgerEvents: LedgerEvent[];
  loading?: boolean;
  divergent?: boolean;
  intelligence?: IntelligenceData | null;
}

export default function ProfileColumn({
  profile,
  scenarioData,
  decision,
  ledgerEvents,
  loading,
  divergent,
  intelligence,
}: ProfileColumnProps) {
  // Build intelligence items: backend universal items + profile-specific from config
  const items: IntelligenceItem[] = (() => {
    if (!intelligence?.intelligence_items?.length) {
      return scenarioData.intelligenceItems;
    }
    // Universal items from backend (objective, pattern, drift trend, acknowledgment)
    const universal = intelligence.intelligence_items;
    // Profile-specific items from config (constitution, schedule, etc.)
    const profileSpecific = scenarioData.intelligenceItems.filter(
      (item) => item.source === "operating_system" || item.source === "calendar"
    );
    return [...universal, ...profileSpecific];
  })();
  return (
    <div
      style={{
        flex: 1,
        minWidth: 0,
        padding: 12,
        borderRadius: 12,
        border: `1px solid ${divergent ? profile.color + "40" : govPalette.border}`,
        background: divergent ? profile.colorDim : govPalette.card,
        boxShadow: divergent ? `0 0 16px ${profile.color}10` : "none",
        display: "flex",
        flexDirection: "column",
        gap: 10,
        transition: "border-color 0.4s, box-shadow 0.4s, background 0.4s",
      }}
    >
      {/* Profile header */}
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <div
          style={{
            width: 10,
            height: 10,
            borderRadius: "50%",
            background: profile.color,
          }}
        />
        <span style={{ fontSize: 13, fontWeight: 700, color: profile.color }}>
          {profile.label}
        </span>
      </div>

      {/* 1. WHY Chips */}
      <WhyChips
        profile={profile}
        driftPercentage={scenarioData.driftPercentage}
        frictionState={scenarioData.frictionState}
      />

      {/* 2. Drift gauge */}
      <DriftGauge percentage={scenarioData.driftPercentage} color={profile.color} trend={scenarioData.driftTrend} />

      {/* 3. Gate Result — from REAL API */}
      <GateResult decision={decision} loading={loading} />

      {/* 4. Violations: grouped when 2+, single card when 1 */}
      {decision && decision.violations && decision.violations.length > 1 && (
        <ViolationGroup violations={decision.violations} />
      )}
      {decision && decision.violations && decision.violations.length === 1 && (
        <ViolationCard violation={decision.violations[0]} />
      )}

      {/* 5. Ledger entries */}
      {ledgerEvents.length > 0 && (
        <div style={{ borderTop: `1px solid ${govPalette.border}`, paddingTop: 8 }}>
          <div
            style={{
              fontSize: 10,
              fontWeight: 600,
              color: govPalette.veryDim,
              letterSpacing: 1,
              marginBottom: 4,
              textTransform: "uppercase",
            }}
          >
            Ledger
          </div>
          {ledgerEvents.slice(0, 3).map((event) => (
            <LedgerEntry key={event.id} event={event} profileColor={profile.color} />
          ))}
        </div>
      )}

      {/* 6. Intelligence items — from real backend + profile-specific config */}
      {items.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          {items.map((item, i) => (
            <div
              key={i}
              style={{
                display: "flex",
                alignItems: "baseline",
                gap: 6,
                fontSize: 10,
                lineHeight: 1.4,
              }}
            >
              <span
                style={{
                  color: govPalette.veryDim,
                  fontWeight: 600,
                  whiteSpace: "nowrap",
                  fontSize: 9,
                  textTransform: "uppercase",
                }}
              >
                {item.label}
              </span>
              <span style={{ color: govPalette.muted }}>{item.value}</span>
            </div>
          ))}
        </div>
      )}

      {/* 7. Conversation — secondary */}
      <div
        style={{
          marginTop: "auto",
          padding: "10px 12px",
          borderRadius: 8,
          background: govPalette.cardAlt,
          border: `1px solid ${govPalette.border}`,
        }}
      >
        <div
          style={{
            fontSize: 9,
            fontWeight: 600,
            color: govPalette.veryDim,
            letterSpacing: 1,
            marginBottom: 4,
            textTransform: "uppercase",
          }}
        >
          Sakhi says
        </div>
        <div
          style={{
            fontSize: 12,
            color: govPalette.dim,
            lineHeight: 1.5,
            fontStyle: "italic",
          }}
        >
          &ldquo;{scenarioData.conversationText}&rdquo;
        </div>
      </div>
    </div>
  );
}
