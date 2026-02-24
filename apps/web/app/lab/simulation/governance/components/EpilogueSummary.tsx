"use client";

import type { GateDecision } from "@/app/demo/simulation/types";
import { GOV_PROFILES, govPalette } from "../theme";
import { SCENARIOS } from "@/app/demo/simulation/scenarioConfigs";

interface EpilogueSummaryProps {
  results: Record<string, Record<string, GateDecision>>;
}

interface Stats {
  total: number;
  allowed: number;
  confirmed: number;
  blocked: number;
  reconciled: number;
}

export default function EpilogueSummary({ results }: EpilogueSummaryProps) {
  const overall: Stats = { total: 0, allowed: 0, confirmed: 0, blocked: 0, reconciled: 0 };
  const perProfile: Record<string, Stats> = {};

  for (const p of GOV_PROFILES) {
    perProfile[p.id] = { total: 0, allowed: 0, confirmed: 0, blocked: 0, reconciled: 0 };
  }

  for (const scenarioId of Object.keys(results)) {
    const scenarioResults = results[scenarioId];
    for (const profileId of Object.keys(scenarioResults)) {
      const d = scenarioResults[profileId];
      if (!d) continue;

      overall.total++;
      const pStats = perProfile[profileId];
      if (pStats) pStats.total++;

      switch (d.action) {
        case "allow":
          overall.allowed++;
          if (pStats) pStats.allowed++;
          break;
        case "require_confirmation":
          overall.confirmed++;
          if (pStats) pStats.confirmed++;
          break;
        case "block":
          overall.blocked++;
          if (pStats) pStats.blocked++;
          break;
        case "require_reconciliation":
          overall.reconciled++;
          if (pStats) pStats.reconciled++;
          break;
      }
    }
  }

  const scenarioCount = Object.keys(results).length;

  return (
    <div>
      <div style={{ textAlign: "center", marginBottom: 32 }}>
        <h2 style={{ fontSize: 22, fontWeight: 700, margin: "0 0 8px", color: govPalette.text }}>
          Governance Summary
        </h2>
        <p style={{ fontSize: 13, color: govPalette.dim, margin: 0 }}>
          {scenarioCount} scenarios evaluated across {GOV_PROFILES.length} constitutional profiles
        </p>
      </div>

      {/* Overall stats */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(4, 1fr)",
          gap: 12,
          marginBottom: 32,
        }}
      >
        <StatCard label="Allowed" value={overall.allowed} color={govPalette.allow} icon="\u2713" />
        <StatCard label="Confirmed" value={overall.confirmed} color={govPalette.warn} icon="\u26a0" />
        <StatCard label="Blocked" value={overall.blocked} color={govPalette.block} icon="\u2716" />
        <StatCard label="Reconciled" value={overall.reconciled} color={govPalette.reconcile} icon="\u21c4" />
      </div>

      {/* Per-profile breakdown */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: 12,
        }}
      >
        {GOV_PROFILES.map((profile) => {
          const stats = perProfile[profile.id];
          if (!stats) return null;
          return (
            <div
              key={profile.id}
              style={{
                padding: 16,
                borderRadius: 12,
                border: `1px solid ${profile.color}20`,
                background: profile.colorDim,
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
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
                <span style={{ fontSize: 11, color: govPalette.dim, marginLeft: "auto" }}>
                  {profile.osType}
                </span>
              </div>
              <div style={{ display: "flex", gap: 12 }}>
                <MiniStat value={stats.allowed} label="Allow" color={govPalette.allow} />
                <MiniStat value={stats.confirmed} label="Confirm" color={govPalette.warn} />
                <MiniStat value={stats.blocked} label="Block" color={govPalette.block} />
                <MiniStat value={stats.reconciled} label="Reconcile" color={govPalette.reconcile} />
              </div>
            </div>
          );
        })}
      </div>

      {/* Closing statement */}
      <div
        style={{
          marginTop: 32,
          padding: "20px 24px",
          borderRadius: 12,
          background: govPalette.cardAlt,
          border: `1px solid ${govPalette.border}`,
          textAlign: "center",
        }}
      >
        <p style={{ fontSize: 14, color: govPalette.text, margin: 0, lineHeight: 1.6 }}>
          Deterministic governance. Personalized agency.
          <br />
          <span style={{ color: govPalette.dim }}>
            Every decision auditable. Every boundary enforced. Every action contextual.
          </span>
        </p>
      </div>
    </div>
  );
}

function StatCard({ label, value, color, icon }: { label: string; value: number; color: string; icon: string }) {
  return (
    <div
      style={{
        padding: "16px",
        borderRadius: 10,
        background: govPalette.card,
        border: `1px solid ${govPalette.border}`,
        textAlign: "center",
      }}
    >
      <div style={{ fontSize: 28, fontWeight: 700, color, fontFamily: "monospace" }}>
        {value}
      </div>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 4, marginTop: 4 }}>
        <span style={{ color, fontSize: 12 }}>{icon}</span>
        <span style={{ fontSize: 11, color: govPalette.dim }}>{label}</span>
      </div>
    </div>
  );
}

function MiniStat({ value, label, color }: { value: number; label: string; color: string }) {
  return (
    <div style={{ textAlign: "center" }}>
      <div style={{ fontSize: 18, fontWeight: 700, color, fontFamily: "monospace" }}>
        {value}
      </div>
      <div style={{ fontSize: 9, color: govPalette.dim }}>{label}</div>
    </div>
  );
}
