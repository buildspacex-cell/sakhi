"use client";

import type { Violation } from "../types";

interface ViolationCardProps {
  violation: Violation;
}

export default function ViolationCard({ violation }: ViolationCardProps) {
  return (
    <div
      style={{
        padding: "10px 12px",
        borderRadius: 6,
        border: "1px solid #27272a",
        borderLeft: "3px solid #ef4444",
        background: "rgba(239, 68, 68, 0.05)",
      }}
    >
      {/* Constraint name */}
      <div
        style={{
          fontSize: 11,
          fontWeight: 600,
          color: "#fca5a5",
          marginBottom: 6,
          fontFamily: "monospace",
        }}
      >
        {violation.constraint_id || "constraint"}
      </div>

      {/* Field / operator / value expression */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 4,
          fontSize: 11,
          fontFamily: "monospace",
          color: "#d4d4d8",
          flexWrap: "wrap",
        }}
      >
        <span style={{ color: "#93c5fd" }}>{violation.field}</span>
        <span style={{ color: "#71717a" }}>(</span>
        <span style={{ color: "#fbbf24" }}>{String(violation.actual ?? "?")}</span>
        <span style={{ color: "#71717a" }}>)</span>
        <span style={{ color: "#ef4444" }}>{violation.operator}</span>
        <span style={{ color: "#fbbf24" }}>{String(violation.expected)}</span>
      </div>

      {/* Description */}
      {violation.message && (
        <div
          style={{
            fontSize: 10,
            color: "#a1a1aa",
            marginTop: 6,
            lineHeight: 1.4,
          }}
        >
          {violation.message}
        </div>
      )}
    </div>
  );
}
