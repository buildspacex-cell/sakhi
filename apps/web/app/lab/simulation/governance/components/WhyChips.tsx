"use client";

import type { ProfileConfig } from "@/app/demo/simulation/types";
import { govPalette } from "../theme";

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
            border: `1px solid ${profile.color}30`,
            background: profile.colorDim,
            fontSize: 11,
            fontWeight: 500,
            color: govPalette.textSecondary,
            letterSpacing: 0.2,
          }}
        >
          <span style={{ color: govPalette.dim, fontSize: 10 }}>{chip.label}</span>
          <span style={{ color: profile.color, fontWeight: 600 }}>{chip.value}</span>
        </span>
      ))}
    </div>
  );
}
