"use client";

import { useState } from "react";

type SuppressionDecision = {
  decision: "allow" | "suppress" | "defer";
  reason: string;
  sensitivity: "low" | "medium" | "high";
  user_state: Record<string, any>;
  tested_at: string;
  demo_user_id: string;
};

type ScaffoldTest = {
  scaffold_type: string;
  label: string;
  description: string;
  recommended_sensitivity: "low" | "medium" | "high";
  result?: SuppressionDecision;
  loading?: boolean;
  error?: string;
};

const palette = {
  bg: "#0e0f12",
  card: "#141518",
  border: "#1f2937",
  text: "#e5e7eb",
  muted: "#9ca3af",
  accent: "#22d3ee",
  success: "#10b981",
  warning: "#f59e0b",
  danger: "#ef4444",
};

const cardStyle: React.CSSProperties = {
  border: `1px solid ${palette.border}`,
  borderRadius: 10,
  padding: 14,
  background: palette.card,
  color: palette.text,
  display: "flex",
  flexDirection: "column",
  gap: 8,
};

const buttonStyle: React.CSSProperties = {
  padding: "10px 14px",
  borderRadius: 8,
  border: `1px solid ${palette.border}`,
  background: palette.accent,
  color: "#0b1220",
  fontSize: 13,
  cursor: "pointer",
  fontWeight: 600,
};

const secondaryButtonStyle: React.CSSProperties = {
  ...buttonStyle,
  background: "transparent",
  color: palette.text,
};

// All proactive scaffolds that should be tested
const SCAFFOLD_TYPES: Omit<ScaffoldTest, "result" | "loading" | "error">[] = [
  {
    scaffold_type: "morning_preview",
    label: "Morning Preview",
    description: "Morning forecast and readiness check",
    recommended_sensitivity: "medium",
  },
  {
    scaffold_type: "morning_ask",
    label: "Morning Ask",
    description: "Morning engagement question",
    recommended_sensitivity: "medium",
  },
  {
    scaffold_type: "morning_momentum",
    label: "Morning Momentum",
    description: "Morning momentum nudge",
    recommended_sensitivity: "medium",
  },
  {
    scaffold_type: "nudge",
    label: "Nudge",
    description: "Proactive nudge (highest sensitivity)",
    recommended_sensitivity: "high",
  },
  {
    scaffold_type: "focus_path",
    label: "Focus Path",
    description: "Focus path generation",
    recommended_sensitivity: "medium",
  },
  {
    scaffold_type: "micro_momentum",
    label: "Micro Momentum",
    description: "Micro-level momentum nudges",
    recommended_sensitivity: "medium",
  },
  {
    scaffold_type: "micro_recovery",
    label: "Micro Recovery",
    description: "Micro-level recovery suggestions",
    recommended_sensitivity: "medium",
  },
  {
    scaffold_type: "mini_flow",
    label: "Mini Flow",
    description: "Mini flow scaffold",
    recommended_sensitivity: "medium",
  },
  {
    scaffold_type: "daily_reflection",
    label: "Daily Reflection",
    description: "End-of-day reflection",
    recommended_sensitivity: "low",
  },
  {
    scaffold_type: "evening_closure",
    label: "Evening Closure",
    description: "End-of-day closure",
    recommended_sensitivity: "low",
  },
];

function getDecisionColor(decision?: string): string {
  switch (decision) {
    case "allow":
      return palette.success;
    case "suppress":
      return palette.danger;
    case "defer":
      return palette.warning;
    default:
      return palette.muted;
  }
}

function getSensitivityBadgeColor(sensitivity: string): string {
  switch (sensitivity) {
    case "high":
      return palette.danger;
    case "medium":
      return palette.warning;
    case "low":
      return palette.success;
    default:
      return palette.muted;
  }
}

export default function SuppressionTestLabPage() {
  const [scaffoldTests, setScaffoldTests] = useState<ScaffoldTest[]>(
    SCAFFOLD_TYPES.map((t) => ({ ...t }))
  );
  const [runningAll, setRunningAll] = useState(false);

  const runTest = async (scaffold_type: string, sensitivity?: string) => {
    // Mark test as loading
    setScaffoldTests((prev) =>
      prev.map((t) =>
        t.scaffold_type === scaffold_type
          ? { ...t, loading: true, error: undefined, result: undefined }
          : t
      )
    );

    try {
      const test = scaffoldTests.find((t) => t.scaffold_type === scaffold_type);
      const res = await fetch("/api/lab/scaffolding/test-suppression", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          scaffold_type,
          sensitivity: sensitivity || test?.recommended_sensitivity || "medium",
        }),
      });

      const text = await res.text();
      const data = text ? JSON.parse(text) : {};

      if (!res.ok) {
        throw new Error(data?.error || res.statusText || "Test failed");
      }

      setScaffoldTests((prev) =>
        prev.map((t) =>
          t.scaffold_type === scaffold_type
            ? { ...t, loading: false, result: data as SuppressionDecision }
            : t
        )
      );
    } catch (err: any) {
      setScaffoldTests((prev) =>
        prev.map((t) =>
          t.scaffold_type === scaffold_type
            ? { ...t, loading: false, error: err?.message || "Test failed" }
            : t
        )
      );
    }
  };

  const runAllTests = async () => {
    setRunningAll(true);
    for (const test of scaffoldTests) {
      await runTest(test.scaffold_type, test.recommended_sensitivity);
    }
    setRunningAll(false);
  };

  const clearResults = () => {
    setScaffoldTests((prev) =>
      prev.map((t) => ({ ...t, result: undefined, error: undefined, loading: false }))
    );
  };

  const allowCount = scaffoldTests.filter((t) => t.result?.decision === "allow").length;
  const suppressCount = scaffoldTests.filter((t) => t.result?.decision === "suppress").length;
  const deferCount = scaffoldTests.filter((t) => t.result?.decision === "defer").length;
  const testedCount = scaffoldTests.filter((t) => t.result).length;

  return (
    <div
      style={{
        minHeight: "100vh",
        background: palette.bg,
        padding: 16,
        color: palette.text,
        fontFamily: "Inter, system-ui, -apple-system, sans-serif",
      }}
    >
      <div style={{ maxWidth: 1200, margin: "0 auto", display: "flex", flexDirection: "column", gap: 12 }}>
        {/* Header */}
        <div
          style={{
            background: "#312e81",
            color: "#e0e7ff",
            padding: 10,
            border: "1px solid #4338ca",
            borderRadius: 8,
            textAlign: "center",
          }}
        >
          Internal Testing Tool - Scaffolding Suppression Lab
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <div style={{ fontSize: 12, letterSpacing: "0.06em", textTransform: "uppercase", color: "#4b5563" }}>
            Suppression First - Phase 1 Foundation Testing
          </div>
          <h1 style={{ margin: 0, fontSize: 24, fontWeight: 600 }}>Scaffolding Suppression Test Panel</h1>
          <p style={{ margin: 0, color: palette.muted, fontSize: 14 }}>
            Test suppression logic for all proactive scaffolds. Each scaffold checks user state before running to
            prevent harm during vulnerable moments (crisis, conflict, exhaustion, emotional volatility).
          </p>
        </div>

        {/* Summary Stats */}
        {testedCount > 0 && (
          <div style={{ ...cardStyle, background: "#1a1d24", borderColor: "#2d3748" }}>
            <div style={{ fontWeight: 600, marginBottom: 6 }}>Test Summary</div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 12 }}>
              <div>
                <div style={{ fontSize: 12, color: palette.muted }}>Tested</div>
                <div style={{ fontSize: 20, fontWeight: 600, color: palette.accent }}>
                  {testedCount} / {scaffoldTests.length}
                </div>
              </div>
              <div>
                <div style={{ fontSize: 12, color: palette.muted }}>Allowed</div>
                <div style={{ fontSize: 20, fontWeight: 600, color: palette.success }}>{allowCount}</div>
              </div>
              <div>
                <div style={{ fontSize: 12, color: palette.muted }}>Suppressed</div>
                <div style={{ fontSize: 20, fontWeight: 600, color: palette.danger }}>{suppressCount}</div>
              </div>
              <div>
                <div style={{ fontSize: 12, color: palette.muted }}>Deferred</div>
                <div style={{ fontSize: 20, fontWeight: 600, color: palette.warning }}>{deferCount}</div>
              </div>
            </div>
          </div>
        )}

        {/* Control Buttons */}
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <button style={buttonStyle} onClick={runAllTests} disabled={runningAll}>
            {runningAll ? "Running all tests..." : "Run all tests"}
          </button>
          <button style={secondaryButtonStyle} onClick={clearResults}>
            Clear results
          </button>
        </div>

        {/* Test Grid */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(380px, 1fr))", gap: 12 }}>
          {scaffoldTests.map((test) => (
            <div
              key={test.scaffold_type}
              style={{
                ...cardStyle,
                borderColor: test.result ? getDecisionColor(test.result.decision) : palette.border,
                borderWidth: test.result ? 2 : 1,
              }}
            >
              {/* Header */}
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8 }}>
                <div>
                  <div style={{ fontWeight: 600, fontSize: 15 }}>{test.label}</div>
                  <div style={{ color: palette.muted, fontSize: 12, marginTop: 2 }}>{test.description}</div>
                </div>
                <div
                  style={{
                    padding: "4px 8px",
                    borderRadius: 6,
                    fontSize: 11,
                    fontWeight: 600,
                    textTransform: "uppercase",
                    background: `${getSensitivityBadgeColor(test.recommended_sensitivity)}20`,
                    color: getSensitivityBadgeColor(test.recommended_sensitivity),
                    border: `1px solid ${getSensitivityBadgeColor(test.recommended_sensitivity)}40`,
                  }}
                >
                  {test.recommended_sensitivity}
                </div>
              </div>

              {/* Test Button */}
              <button
                style={{
                  ...secondaryButtonStyle,
                  background: test.loading ? palette.muted : palette.accent,
                  color: "#0b1220",
                  opacity: test.loading ? 0.6 : 1,
                }}
                onClick={() => runTest(test.scaffold_type)}
                disabled={test.loading}
              >
                {test.loading ? "Testing..." : "Run test"}
              </button>

              {/* Error */}
              {test.error && (
                <div
                  style={{
                    padding: 10,
                    borderRadius: 8,
                    background: `${palette.danger}20`,
                    border: `1px solid ${palette.danger}40`,
                    color: palette.danger,
                    fontSize: 13,
                  }}
                >
                  {test.error}
                </div>
              )}

              {/* Result */}
              {test.result && (
                <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 4 }}>
                  <div
                    style={{
                      padding: 10,
                      borderRadius: 8,
                      background: `${getDecisionColor(test.result.decision)}20`,
                      border: `1px solid ${getDecisionColor(test.result.decision)}40`,
                    }}
                  >
                    <div
                      style={{
                        fontSize: 13,
                        fontWeight: 600,
                        color: getDecisionColor(test.result.decision),
                        textTransform: "uppercase",
                        letterSpacing: "0.05em",
                      }}
                    >
                      {test.result.decision}
                    </div>
                    <div style={{ fontSize: 12, color: palette.text, marginTop: 4 }}>{test.result.reason}</div>
                  </div>

                  {/* User State Details */}
                  {test.result.user_state && Object.keys(test.result.user_state).length > 0 && (
                    <div style={{ fontSize: 12 }}>
                      <div style={{ color: palette.muted, marginBottom: 4, fontWeight: 600 }}>User State Signals:</div>
                      <div
                        style={{
                          background: "#0b1220",
                          padding: 8,
                          borderRadius: 6,
                          border: `1px solid ${palette.border}`,
                        }}
                      >
                        {Object.entries(test.result.user_state).map(([key, value]) => (
                          <div key={key} style={{ marginBottom: 4 }}>
                            <span style={{ color: palette.muted }}>{key}:</span>{" "}
                            <span style={{ color: palette.text }}>
                              {typeof value === "boolean" ? (value ? "Yes" : "No") : JSON.stringify(value)}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  <div style={{ fontSize: 11, color: palette.muted }}>
                    Tested at: {new Date(test.result.tested_at).toLocaleString()}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Documentation */}
        <div style={{ ...cardStyle, background: "#1a1d24", marginTop: 12 }}>
          <div style={{ fontWeight: 600, marginBottom: 6 }}>About Suppression Testing</div>
          <div style={{ fontSize: 13, color: palette.text, lineHeight: 1.6 }}>
            <p style={{ margin: "0 0 8px 0" }}>
              <strong>Suppression First</strong> is a core design principle: every proactive scaffold checks user state
              before running. If the user is in a vulnerable moment, the scaffold is suppressed.
            </p>
            <p style={{ margin: "0 0 8px 0" }}>
              <strong>Six suppression rules:</strong>
            </p>
            <ul style={{ margin: "0 0 8px 0", paddingLeft: 20 }}>
              <li>Crisis language detection</li>
              <li>Silence mode active</li>
              <li>Recent conflict/friction</li>
              <li>Rhythm exhaustion</li>
              <li>Emotional volatility</li>
              <li>Low engagement signal</li>
            </ul>
            <p style={{ margin: 0 }}>
              <strong>Sensitivity levels:</strong> HIGH (most conservative) = only runs when user is very stable,
              MEDIUM = standard protection, LOW = end-of-day scaffolds with less intrusive timing.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
