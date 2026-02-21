"use client";

import type { ProfileConfig } from "../types";

interface WhyChipsProps {
  profile: ProfileConfig;
  driftPercentage: number;
  frictionState: string;
}

export default function WhyChips({ profile, driftPercentage, frictionState }: WhyChipsProps) {
  const chips = [
    { label: "OS", value: profile.osType },
    { label: "Drift", value: `${driftPercentage}%` },
    { label: "State", value: frictionState },
  ];

  return (
    <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
      {chips.map((chip) => (
        <span
          key={chip.label}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 4,
            padding: "3px 8px",
            borderRadius: 12,
            border: `1px solid ${profile.color}40`,
            background: profile.colorDim,
            fontSize: 11,
            fontWeight: 500,
            color: "#d4d4d8",
            letterSpacing: 0.2,
          }}
        >
          <span style={{ color: "#71717a", fontSize: 10 }}>{chip.label}</span>
          <span style={{ color: profile.color }}>{chip.value}</span>
        </span>
      ))}
    </div>
  );
}
