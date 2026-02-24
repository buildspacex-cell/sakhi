"use client";

import type { GateDecision } from "@/app/demo/simulation/types";
import { govPalette } from "../theme";

interface GateResultProps {
  decision: GateDecision | null;
  loading?: boolean;
}

const ACTION_STYLES: Record<string, { bg: string; border: string; text: string; label: string; icon: string }> = {
  allow: {
    bg: govPalette.allowBg,
    border: govPalette.allow,
    text: govPalette.allow,
    label: "PROCEED",
    icon: "\u2713",
  },
  require_confirmation: {
    bg: govPalette.warnBg,
    border: govPalette.warn,
    text: govPalette.warn,
    label: "CONFIRM FIRST",
    icon: "\u26a0",
  },
  block: {
    bg: govPalette.blockBg,
    border: govPalette.block,
    text: govPalette.block,
    label: "HARD STOP",
    icon: "\u2716",
  },
  require_reconciliation: {
    bg: govPalette.reconcileBg,
    border: govPalette.reconcile,
    text: govPalette.reconcile,
    label: "RECONSIDER",
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
          border: `1px solid ${govPalette.border}`,
          background: govPalette.cardAlt,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div
            style={{
              width: 8,
              height: 8,
              borderRadius: "50%",
              background: govPalette.veryDim,
              animation: "pulse 1.5s infinite",
            }}
          />
          <span style={{ fontSize: 12, color: govPalette.dim }}>Evaluating...</span>
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
                  color: triggered ? govPalette.checkFail : govPalette.checkPass,
                  fontWeight: 600,
                  width: 14,
                  textAlign: "center",
                }}
              >
                {triggered ? "\u2717" : "\u2713"}
              </span>
              <span style={{ color: triggered ? govPalette.block : govPalette.allow }}>
                {check.label}
              </span>
              {triggered && decision.action === "block" && check.key === "constraints" && (
                <span style={{ color: govPalette.block, fontSize: 10 }}>HARD</span>
              )}
            </div>
          );
        })}
      </div>

      {/* Reasons */}
      {decision.reasons && decision.reasons.length > 0 && (
        <div style={{ marginTop: 8, paddingTop: 8, borderTop: `1px solid ${govPalette.border}` }}>
          {decision.reasons.map((reason, i) => (
            <div
              key={i}
              style={{
                fontSize: 10,
                color: govPalette.muted,
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
