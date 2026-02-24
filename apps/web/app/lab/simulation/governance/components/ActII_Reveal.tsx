"use client";

import type { GateDecision, ScenarioConfig, IntelligenceData, IntelligenceItem } from "@/app/demo/simulation/types";
import { govPalette } from "../theme";
import { USER_STATEMENT } from "../actScenarioConfig";
import DriftGauge from "./DriftGauge";
import GateResult from "./GateResult";
import ViolationCard from "./ViolationCard";

interface ActII_RevealProps {
  scenario: ScenarioConfig;
  decision: GateDecision | null;
  loading: boolean;
  onContinue: () => void;
  intelligence: IntelligenceData | null;
}

export default function ActII_Reveal({
  scenario,
  decision,
  loading,
  onContinue,
  intelligence,
}: ActII_RevealProps) {
  const profileData = scenario.profiles["adaptive"];
  if (!profileData) return null;

  // Use real intelligence items from backend, fall back to hardcoded config
  const items: IntelligenceItem[] = intelligence?.intelligence_items?.length
    ? intelligence.intelligence_items
    : profileData.intelligenceItems;

  return (
    <div>
      {/* Act label */}
      <div
        style={{
          fontSize: 11,
          fontWeight: 600,
          color: govPalette.accent,
          letterSpacing: 1,
          textTransform: "uppercase",
          marginBottom: 8,
        }}
      >
        Act II: The Reveal
      </div>

      {/* Subtitle */}
      <p style={{ fontSize: 13, color: govPalette.muted, marginBottom: 16 }}>
        Same situation but now Sakhi has longitudinal context.
      </p>

      {/* User statement (compact) */}
      <div
        style={{
          display: "flex",
          justifyContent: "flex-end",
          marginBottom: 16,
        }}
      >
        <div
          style={{
            maxWidth: "75%",
            padding: "10px 14px",
            borderRadius: "14px 14px 4px 14px",
            background: govPalette.accent,
            color: "#ffffff",
            fontSize: 13,
            lineHeight: 1.4,
          }}
        >
          {USER_STATEMENT}
        </div>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 16,
          marginBottom: 20,
        }}
      >
        {/* Left: What Sakhi knows */}
        <div
          style={{
            padding: 16,
            borderRadius: 10,
            border: `1px solid ${govPalette.border}`,
            background: govPalette.card,
          }}
        >
          <div
            style={{
              fontSize: 10,
              fontWeight: 600,
              color: govPalette.accent,
              letterSpacing: 1,
              textTransform: "uppercase",
              marginBottom: 10,
            }}
          >
            What Sakhi knows about you
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {items.map((item, i) => (
              <div key={i} style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
                <span
                  style={{
                    fontSize: 9,
                    fontWeight: 600,
                    color: govPalette.veryDim,
                    textTransform: "uppercase",
                    whiteSpace: "nowrap",
                    minWidth: 70,
                  }}
                >
                  {item.label}
                </span>
                <span style={{ fontSize: 12, color: govPalette.text, lineHeight: 1.4 }}>
                  {item.value}
                </span>
              </div>
            ))}
          </div>

          {/* Drift gauge */}
          <div style={{ marginTop: 12 }}>
            <DriftGauge
              percentage={profileData.driftPercentage}
              color="#8b5cf6"
              trend={
                intelligence?.drift_trend
                  ? { delta: intelligence.drift_trend.delta, days: intelligence.drift_trend.days }
                  : profileData.driftTrend
              }
            />
          </div>
        </div>

        {/* Right: Gate Result */}
        <div
          style={{
            padding: 16,
            borderRadius: 10,
            border: `1px solid ${govPalette.border}`,
            background: govPalette.card,
            display: "flex",
            flexDirection: "column",
            gap: 10,
          }}
        >
          <div
            style={{
              fontSize: 10,
              fontWeight: 600,
              color: govPalette.accent,
              letterSpacing: 1,
              textTransform: "uppercase",
              marginBottom: 2,
            }}
          >
            Governance Decision
          </div>

          <GateResult decision={decision} loading={loading} />

          {/* Violations */}
          {decision && decision.violations && decision.violations.length > 0 && (
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {decision.violations.map((v, i) => (
                <ViolationCard key={i} violation={v} />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Sakhi's response */}
      <div
        style={{
          padding: "14px 16px",
          borderRadius: 10,
          background: govPalette.cardAlt,
          border: `1px solid ${govPalette.border}`,
          marginBottom: 20,
        }}
      >
        <div
          style={{
            fontSize: 10,
            fontWeight: 600,
            color: "#8b5cf6",
            letterSpacing: 1,
            textTransform: "uppercase",
            marginBottom: 6,
          }}
        >
          Sakhi says
        </div>
        <div style={{ fontSize: 14, color: govPalette.text, lineHeight: 1.6, fontStyle: "italic" }}>
          &ldquo;{profileData.conversationText}&rdquo;
        </div>
      </div>

      {/* Punchline */}
      <div style={{ textAlign: "center" }}>
        <p style={{ fontSize: 14, color: govPalette.muted, marginBottom: 16 }}>
          That&apos;s one constitution. Now watch the same moment split three ways.
        </p>
        <button
          onClick={onContinue}
          disabled={loading}
          style={{
            padding: "10px 28px",
            borderRadius: 8,
            border: "none",
            background: !loading ? govPalette.accent : govPalette.border,
            color: !loading ? "#fff" : govPalette.veryDim,
            fontSize: 14,
            fontWeight: 600,
            cursor: !loading ? "pointer" : "default",
          }}
        >
          See how constitutions diverge →
        </button>
      </div>
    </div>
  );
}
