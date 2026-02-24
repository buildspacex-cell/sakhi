"use client";

import { govPalette } from "../theme";
import { USER_STATEMENT, STATELESS_RESPONSE } from "../actScenarioConfig";

interface ActI_IllusionProps {
  onContinue: () => void;
}

export default function ActI_Illusion({ onContinue }: ActI_IllusionProps) {
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
        Act I: The Illusion
      </div>

      {/* User statement */}
      <div
        style={{
          display: "flex",
          justifyContent: "flex-end",
          marginBottom: 16,
        }}
      >
        <div
          style={{
            maxWidth: "75%",
            padding: "12px 16px",
            borderRadius: "16px 16px 4px 16px",
            background: govPalette.accent,
            color: "#ffffff",
            fontSize: 14,
            lineHeight: 1.5,
          }}
        >
          {USER_STATEMENT}
        </div>
      </div>

      {/* Stateless LLM response */}
      <div style={{ display: "flex", gap: 10, marginBottom: 16 }}>
        <div
          style={{
            width: 32,
            height: 32,
            borderRadius: "50%",
            background: "#e0e0e0",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 14,
            color: "#666",
            flexShrink: 0,
          }}
        >
          AI
        </div>
        <div
          style={{
            maxWidth: "75%",
            padding: "12px 16px",
            borderRadius: "4px 16px 16px 16px",
            background: "#f0f0f0",
            color: "#333",
            fontSize: 14,
            lineHeight: 1.6,
            whiteSpace: "pre-line",
          }}
        >
          {STATELESS_RESPONSE}
        </div>
      </div>

      {/* Punchline + continue */}
      <div style={{ textAlign: "center" }}>
        <p
          style={{
            fontSize: 15,
            fontWeight: 600,
            color: govPalette.text,
            marginBottom: 4,
          }}
        >
          Helpful, but unaware.
        </p>
        <p
          style={{
            fontSize: 13,
            color: govPalette.muted,
            marginBottom: 16,
          }}
        >
          No longitudinal memory. No evolving objectives. No record of past decisions.
        </p>
        <button
          onClick={onContinue}
          style={{
            padding: "10px 28px",
            borderRadius: 8,
            border: "none",
            background: govPalette.accent,
            color: "#fff",
            fontSize: 14,
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          Now add continuity →
        </button>
      </div>
    </div>
  );
}
