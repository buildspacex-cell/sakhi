"use client";

interface DriftGaugeProps {
  percentage: number;
  color: string;
}

const THRESHOLDS = [
  { value: 25, label: "25%", color: "#f59e0b" },
  { value: 40, label: "40%", color: "#ef4444" },
];

export default function DriftGauge({ percentage, color }: DriftGaugeProps) {
  const barColor = percentage >= 40 ? "#ef4444" : percentage >= 25 ? "#f59e0b" : color;

  return (
    <div style={{ width: "100%" }}>
      <div
        style={{
          position: "relative",
          height: 6,
          borderRadius: 3,
          background: "#27272a",
          overflow: "visible",
        }}
      >
        {/* Fill bar */}
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
        {/* Threshold markers */}
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
          color: "#52525b",
        }}
      >
        <span>0%</span>
        <span style={{ color: barColor, fontWeight: 600, fontSize: 10 }}>{percentage}%</span>
        <span>50%</span>
      </div>
    </div>
  );
}
