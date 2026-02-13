"use client";

import React from "react";

type DemoMode = "production-ready" | "partial" | "simulated";

interface DemoModeBadgeProps {
  mode: DemoMode;
  detail: string;
}

const modeConfig: Record<DemoMode, { label: string; border: string; bg: string; fg: string }> = {
  "production-ready": {
    label: "Production-ready",
    border: "rgba(16, 185, 129, 0.5)",
    bg: "rgba(16, 185, 129, 0.12)",
    fg: "#10b981",
  },
  partial: {
    label: "Partially Real",
    border: "rgba(245, 158, 11, 0.5)",
    bg: "rgba(245, 158, 11, 0.12)",
    fg: "#f59e0b",
  },
  simulated: {
    label: "Simulated",
    border: "rgba(244, 63, 94, 0.5)",
    bg: "rgba(244, 63, 94, 0.12)",
    fg: "#f43f5e",
  },
};

export default function DemoModeBadge({ mode, detail }: DemoModeBadgeProps) {
  const cfg = modeConfig[mode];

  return (
    <div
      style={{
        display: "flex",
        flexWrap: "wrap",
        gap: 8,
        alignItems: "center",
        border: `1px solid ${cfg.border}`,
        background: cfg.bg,
        borderRadius: 12,
        padding: "10px 12px",
      }}
    >
      <span
        style={{
          border: `1px solid ${cfg.border}`,
          color: cfg.fg,
          borderRadius: 999,
          padding: "2px 8px",
          fontSize: 11,
          fontWeight: 700,
          letterSpacing: "0.03em",
          textTransform: "uppercase",
        }}
      >
        {cfg.label}
      </span>
      <span style={{ color: "#a1a1aa", fontSize: 13 }}>{detail}</span>
    </div>
  );
}
