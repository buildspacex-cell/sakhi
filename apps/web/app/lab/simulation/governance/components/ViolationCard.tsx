"use client";

import { useState } from "react";
import type { Violation } from "@/app/demo/simulation/types";
import { govPalette } from "../theme";

/** Map raw constraint IDs to human-readable rule names */
const RULE_NAMES: Record<string, string> = {
  "sim-c-stop-overcommitting": "Stop Overcommitting (v2)",
  "sim-c-no-work-after-10pm": "No Work After 10 PM",
  "sim-c-protect-focus-time": "Protect Focus Time",
  "sim-c-drift-safety": "Drift Safety Net",
};

/** Map constraint IDs to plain-English explanations */
const RULE_EXPLANATIONS: Record<string, string> = {
  "sim-c-stop-overcommitting":
    "Accepting a new commitment contradicts your current objective to reduce overcommitting.",
  "sim-c-no-work-after-10pm":
    "This would schedule work past your 10 PM boundary.",
  "sim-c-protect-focus-time":
    "This action would interrupt a protected focus block.",
  "sim-c-drift-safety":
    "Your constitution is running hot. Adding obligation at this drift level increases burnout risk.",
};

export function getRuleName(violation: Violation): string {
  return (
    RULE_NAMES[violation.constraint_id] ||
    violation.description ||
    violation.constraint_id
  );
}

export function getRuleExplanation(violation: Violation): string {
  return (
    RULE_EXPLANATIONS[violation.constraint_id] ||
    violation.message ||
    ""
  );
}

/** Single violation display (used when only 1 violation) */
export default function ViolationCard({ violation }: { violation: Violation }) {
  const [showTrace, setShowTrace] = useState(false);
  const ruleName = getRuleName(violation);
  const explanation = getRuleExplanation(violation);

  return (
    <div
      style={{
        padding: "10px 12px",
        borderRadius: 6,
        border: `1px solid ${govPalette.border}`,
        borderLeft: `3px solid ${govPalette.block}`,
        background: govPalette.blockBg,
      }}
    >
      <div
        style={{
          fontSize: 11,
          fontWeight: 600,
          color: govPalette.block,
          marginBottom: 4,
        }}
      >
        Rule triggered: {ruleName}
      </div>

      {explanation && (
        <div
          style={{
            fontSize: 11,
            color: govPalette.text,
            lineHeight: 1.4,
            marginBottom: 6,
          }}
        >
          {explanation}
        </div>
      )}

      <TraceToggle violations={[violation]} showTrace={showTrace} setShowTrace={setShowTrace} />
    </div>
  );
}

/** Grouped violations display (used when 2+ violations) */
export function ViolationGroup({ violations }: { violations: Violation[] }) {
  const [showTrace, setShowTrace] = useState(false);

  return (
    <div
      style={{
        padding: "10px 12px",
        borderRadius: 6,
        border: `1px solid ${govPalette.border}`,
        borderLeft: `3px solid ${govPalette.block}`,
        background: govPalette.blockBg,
      }}
    >
      <div
        style={{
          fontSize: 11,
          fontWeight: 600,
          color: govPalette.block,
          marginBottom: 6,
        }}
      >
        Rules triggered ({violations.length}):
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        {violations.map((v, i) => (
          <div key={i} style={{ display: "flex", alignItems: "baseline", gap: 6 }}>
            <span style={{ color: govPalette.block, fontSize: 10 }}>&bull;</span>
            <span style={{ fontSize: 11, color: govPalette.text, lineHeight: 1.4 }}>
              {getRuleName(v)}
            </span>
          </div>
        ))}
      </div>

      <div style={{ marginTop: 6 }}>
        <TraceToggle violations={violations} showTrace={showTrace} setShowTrace={setShowTrace} />
      </div>
    </div>
  );
}

/** Shared expandable trace section */
function TraceToggle({
  violations,
  showTrace,
  setShowTrace,
}: {
  violations: Violation[];
  showTrace: boolean;
  setShowTrace: (v: boolean) => void;
}) {
  return (
    <>
      <button
        onClick={() => setShowTrace(!showTrace)}
        style={{
          background: "none",
          border: "none",
          padding: 0,
          fontSize: 10,
          color: govPalette.dim,
          cursor: "pointer",
          display: "flex",
          alignItems: "center",
          gap: 4,
        }}
      >
        <span style={{ fontSize: 8 }}>{showTrace ? "\u25BC" : "\u25B6"}</span>
        {showTrace ? "Hide evaluation trace" : "Show evaluation trace"}
      </button>

      {showTrace && (
        <div
          style={{
            marginTop: 6,
            padding: "6px 8px",
            borderRadius: 4,
            background: `${govPalette.border}40`,
            fontFamily: "monospace",
            fontSize: 10,
            color: govPalette.dim,
            lineHeight: 1.5,
            display: "flex",
            flexDirection: "column",
            gap: 6,
          }}
        >
          {violations.map((v, i) => (
            <div key={i}>
              {violations.length > 1 && (
                <div style={{ color: govPalette.veryDim, fontWeight: 600, marginBottom: 2 }}>
                  [{i + 1}] {v.constraint_id}
                </div>
              )}
              {violations.length === 1 && (
                <div>
                  <span style={{ color: govPalette.veryDim }}>constraint: </span>
                  {v.constraint_id}
                </div>
              )}
              <div>
                <span style={{ color: govPalette.veryDim }}>check: </span>
                <span style={{ color: "#5b8db5" }}>{v.field}</span>
                {" "}
                <span style={{ color: govPalette.block }}>{v.operator}</span>
                {" "}
                <span style={{ color: govPalette.warn }}>{String(v.expected)}</span>
              </div>
              <div>
                <span style={{ color: govPalette.veryDim }}>actual: </span>
                <span style={{ color: govPalette.warn }}>{String(v.actual ?? "?")}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </>
  );
}
