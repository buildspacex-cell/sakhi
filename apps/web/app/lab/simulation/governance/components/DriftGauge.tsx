"use client";

import { govPalette } from "../theme";

interface DriftGaugeProps {
  percentage: number;
  color: string;
  trend?: { delta: number; days: number };
}

const THRESHOLDS = [
  { value: 25, label: "25%", color: "#e6923a" },
  { value: 40, label: "40%", color: "#e05555" },
];

export default function DriftGauge({ percentage, color, trend }: DriftGaugeProps) {
  const barColor = percentage >= 40 ? govPalette.block : percentage >= 25 ? govPalette.warn : color;

  return (
    <div style={{ width: "100%" }}>
      <div
        style={{
          position: "relative",
          height: 6,
          borderRadius: 3,
          background: govPalette.border,
          overflow: "visible",
        }}
      >
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            height: "100%",
            width: `${Math.min(percentage, 100)}%`,
            borderRadius: 3,
            background: barColor,
            transition: "width 0.6s ease-out, background 0.3s",
          }}
        />
        {THRESHOLDS.map((t) => (
          <div
            key={t.value}
            style={{
              position: "absolute",
              top: -2,
              left: `${t.value}%`,
              width: 1,
              height: 10,
              background: t.color,
              opacity: 0.5,
            }}
          />
        ))}
      </div>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          marginTop: 2,
          fontSize: 9,
          color: govPalette.veryDim,
        }}
      >
        <span>0%</span>
        <span style={{ color: barColor, fontWeight: 600, fontSize: 10 }}>
          {percentage}%
          {trend && trend.delta > 0 && (
            <span style={{ color: govPalette.warn, marginLeft: 4, fontSize: 9 }}>
              ↑ +{trend.delta}% over {trend.days}d
            </span>
          )}
        </span>
        <span>50%</span>
      </div>
    </div>
  );
}
