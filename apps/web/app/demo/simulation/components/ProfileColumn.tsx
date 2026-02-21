"use client";

import type { ProfileConfig, GateDecision, LedgerEvent, ProfileScenarioData } from "../types";
import WhyChips from "./WhyChips";
import DriftGauge from "./DriftGauge";
import GateResult from "./GateResult";
import ViolationCard from "./ViolationCard";
import LedgerEntry from "./LedgerEntry";

interface ProfileColumnProps {
  profile: ProfileConfig;
  scenarioData: ProfileScenarioData;
  decision: GateDecision | null;
  ledgerEvents: LedgerEvent[];
  loading?: boolean;
  /** Whether this column's decision differs from others — adds glow */
  divergent?: boolean;
}

export default function ProfileColumn({
  profile,
  scenarioData,
  decision,
  ledgerEvents,
  loading,
  divergent,
}: ProfileColumnProps) {
  return (
    <div
      style={{
        flex: 1,
        minWidth: 0,
        padding: 16,
        borderRadius: 12,
        border: `1px solid ${divergent ? profile.color + "60" : "#27272a"}`,
        background: divergent ? profile.colorDim : "#131416",
        boxShadow: divergent ? `0 0 20px ${profile.color}15` : "none",
        display: "flex",
        flexDirection: "column",
        gap: 12,
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
        <span style={{ fontSize: 14, fontWeight: 700, color: profile.color }}>
          {profile.label}
        </span>
      </div>

      {/* 1. WHY Chips — causality inputs */}
      <WhyChips
        profile={profile}
        driftPercentage={scenarioData.driftPercentage}
        frictionState={scenarioData.frictionState}
      />

      {/* 2. Drift gauge */}
      <DriftGauge percentage={scenarioData.driftPercentage} color={profile.color} />

      {/* 3. Gate Result — from REAL API */}
      <GateResult decision={decision} loading={loading} />

      {/* 4. Violation cards — from REAL API */}
      {decision && decision.violations && decision.violations.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {decision.violations.map((v, i) => (
            <ViolationCard key={i} violation={v} />
          ))}
        </div>
      )}

      {/* 5. Ledger entries — from REAL API */}
      {ledgerEvents.length > 0 && (
        <div
          style={{
            borderTop: "1px solid #27272a",
            paddingTop: 8,
          }}
        >
          <div
            style={{
              fontSize: 10,
              fontWeight: 600,
              color: "#52525b",
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

      {/* 6. Intelligence items (secondary) */}
      {scenarioData.intelligenceItems.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          {scenarioData.intelligenceItems.map((item, i) => (
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
                  color: "#52525b",
                  fontWeight: 600,
                  whiteSpace: "nowrap",
                  fontSize: 9,
                  textTransform: "uppercase",
                }}
              >
                {item.label}
              </span>
              <span style={{ color: "#a1a1aa" }}>{item.value}</span>
            </div>
          ))}
        </div>
      )}

      {/* 7. Conversation — SECONDARY, dimmer, at bottom */}
      <div
        style={{
          marginTop: "auto",
          padding: "10px 12px",
          borderRadius: 8,
          background: "#1a1b1e",
          border: "1px solid #27272a",
        }}
      >
        <div
          style={{
            fontSize: 9,
            fontWeight: 600,
            color: "#3f3f46",
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
            color: "#71717a",
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
