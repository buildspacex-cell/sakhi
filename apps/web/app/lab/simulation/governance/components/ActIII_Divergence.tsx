"use client";

import Link from "next/link";
import type { GateDecision, LedgerEvent, ScenarioConfig, IntelligenceData } from "@/app/demo/simulation/types";
import { govPalette } from "../theme";
import { USER_STATEMENT, ACT_III_STATE_PROFILES } from "../actScenarioConfig";
import ProfileColumn from "./ProfileColumn";

interface ActIII_DivergenceProps {
  scenario: ScenarioConfig;
  decisions: Record<string, GateDecision>;
  ledgerEvents: Record<string, LedgerEvent[]>;
  loading: boolean;
  intelligence: IntelligenceData | null;
}

export default function ActIII_Divergence({
  scenario,
  decisions,
  ledgerEvents,
  loading,
  intelligence,
}: ActIII_DivergenceProps) {
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
        Act III: The Divergence
      </div>

      {/* Subtitle */}
      <p style={{ fontSize: 13, color: govPalette.muted, marginBottom: 4 }}>
        Same person. Same constitution. Three different current states.
      </p>
      <p style={{ fontSize: 11, color: govPalette.veryDim, marginBottom: 4, marginTop: 0 }}>
        The divergence comes from where she is in her week, not who she is.
      </p>

      {/* Compact user statement */}
      <div
        style={{
          padding: "8px 12px",
          borderRadius: 8,
          background: govPalette.cardAlt,
          border: `1px solid ${govPalette.border}`,
          fontSize: 12,
          color: govPalette.dim,
          fontStyle: "italic",
          marginBottom: 16,
        }}
      >
        &ldquo;{USER_STATEMENT}&rdquo;
      </div>

      {/* Three columns */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: 12,
        }}
      >
        {ACT_III_STATE_PROFILES.map((profile) => {
          const profileData = scenario.profiles[profile.id];
          if (!profileData) return null;
          const decision = decisions[profile.id] || null;
          const events = ledgerEvents[profile.id] || [];

          return (
            <ProfileColumn
              key={profile.id}
              profile={profile}
              scenarioData={profileData}
              decision={decision}
              ledgerEvents={events}
              loading={loading}
              divergent={!!decision}
              intelligence={intelligence}
            />
          );
        })}
      </div>

      {/* Bottom insight */}
      {!loading && Object.keys(decisions).length === 3 && (
        <>
          <div
            style={{
              marginTop: 20,
              padding: "16px 20px",
              borderRadius: 10,
              background: govPalette.cardAlt,
              border: `1px solid ${govPalette.border}`,
              textAlign: "center",
            }}
          >
            <p
              style={{
                fontSize: 14,
                color: govPalette.text,
                fontWeight: 600,
                marginBottom: 4,
              }}
            >
              Same person. Same constitution. Three different right answers.
            </p>
            <p style={{ fontSize: 12, color: govPalette.muted, margin: 0 }}>
              The governance engine doesn&apos;t just know who you are -- it knows where you are right now.
              Drift, load, and recent patterns shape every decision.
            </p>
          </div>

          {/* Link to profiles contrast page */}
          <div style={{ marginTop: 16, textAlign: "center" }}>
            <Link
              href="/lab/simulation/profiles"
              style={{
                display: "inline-block",
                padding: "10px 20px",
                borderRadius: 8,
                background: govPalette.accent,
                color: "#fff",
                fontSize: 13,
                fontWeight: 600,
                textDecoration: "none",
              }}
            >
              See how different people respond &rarr;
            </Link>
          </div>
        </>
      )}
    </div>
  );
}
