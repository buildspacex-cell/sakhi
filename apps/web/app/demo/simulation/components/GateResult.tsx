"use client";

import type { GateDecision } from "../types";

interface GateResultProps {
  decision: GateDecision | null;
  loading?: boolean;
}

const ACTION_STYLES: Record<string, { bg: string; border: string; text: string; label: string; icon: string }> = {
  allow: {
    bg: "rgba(34, 197, 94, 0.1)",
    border: "#22c55e",
    text: "#22c55e",
    label: "ALLOW",
    icon: "\u2713",
  },
  require_confirmation: {
    bg: "rgba(245, 158, 11, 0.1)",
    border: "#f59e0b",
    text: "#f59e0b",
    label: "CONFIRM",
    icon: "\u26a0",
  },
  block: {
    bg: "rgba(239, 68, 68, 0.1)",
    border: "#ef4444",
    text: "#ef4444",
    label: "BLOCK",
    icon: "\u2716",
  },
  require_reconciliation: {
    bg: "rgba(168, 85, 247, 0.1)",
    border: "#a855f7",
    text: "#a855f7",
    label: "RECONCILE",
    icon: "\u21c4",
  },
};

const CHECK_ITEMS = [
  { key: "constraints", label: "Constraints" },
  { key: "drift", label: "Drift gate" },
  { key: "contradictions", label: "Contradictions" },
] as const;

export default function GateResult({ decision, loading }: GateResultProps) {
  if (loading) {
    return (
      <div
        style={{
          padding: "12px 14px",
          borderRadius: 8,
          border: "1px solid #27272a",
          background: "#1a1b1e",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div
            style={{
              width: 8,
              height: 8,
              borderRadius: "50%",
              background: "#52525b",
              animation: "pulse 1.5s infinite",
            }}
          />
          <span style={{ fontSize: 12, color: "#71717a" }}>Evaluating...</span>
        </div>
      </div>
    );
  }

  if (!decision) return null;

  const style = ACTION_STYLES[decision.action] || ACTION_STYLES.allow;
  const triggers = new Set(decision.triggers || []);

  return (
    <div
      style={{
        padding: "12px 14px",
        borderRadius: 8,
        border: `1px solid ${style.border}30`,
        background: style.bg,
      }}
    >
      {/* Decision badge */}
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
        <span
          style={{
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            width: 22,
            height: 22,
            borderRadius: 6,
            background: `${style.border}20`,
            color: style.text,
            fontSize: 12,
            fontWeight: 700,
          }}
        >
          {style.icon}
        </span>
        <span
          style={{
            fontSize: 13,
            fontWeight: 700,
            color: style.text,
            letterSpacing: 1,
            fontFamily: "monospace",
          }}
        >
          {style.label}
        </span>
      </div>

      {/* 3-check indicators */}
      <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        {CHECK_ITEMS.map((check) => {
          const triggered = triggers.has(check.key);
          return (
            <div
              key={check.key}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 6,
                fontSize: 11,
                fontFamily: "monospace",
              }}
            >
              <span
                style={{
                  color: triggered ? "#ef4444" : "#22c55e",
                  fontWeight: 600,
                  width: 14,
                  textAlign: "center",
                }}
              >
                {triggered ? "\u2717" : "\u2713"}
              </span>
              <span style={{ color: triggered ? "#fca5a5" : "#86efac" }}>
                {check.label}
              </span>
              {triggered && decision.action === "block" && check.key === "constraints" && (
                <span style={{ color: "#ef4444", fontSize: 10 }}>HARD</span>
              )}
            </div>
          );
        })}
      </div>

      {/* Reasons */}
      {decision.reasons && decision.reasons.length > 0 && (
        <div style={{ marginTop: 8, paddingTop: 8, borderTop: "1px solid #27272a" }}>
          {decision.reasons.map((reason, i) => (
            <div
              key={i}
              style={{
                fontSize: 10,
                color: "#a1a1aa",
                lineHeight: 1.4,
                marginTop: i > 0 ? 2 : 0,
              }}
            >
              {reason}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
