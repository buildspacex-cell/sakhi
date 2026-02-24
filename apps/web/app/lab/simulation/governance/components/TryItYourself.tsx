"use client";

import { useState, useCallback } from "react";
import type { GateDecision } from "@/app/demo/simulation/types";
import { DEMO_USER_ID } from "@/app/demo/simulation/scenarioConfigs";
import { GOV_PROFILES, govPalette } from "../theme";
import GateResult from "./GateResult";
import ViolationCard from "./ViolationCard";

const HOUR_OPTIONS = [
  { label: "6 AM", value: 6 },
  { label: "9 AM", value: 9 },
  { label: "12 PM", value: 12 },
  { label: "3 PM", value: 15 },
  { label: "6 PM", value: 18 },
  { label: "9 PM", value: 21 },
  { label: "11 PM", value: 23 },
];

const DRIFT_PRESETS = [
  { label: "Low (10%)", value: 10, color: govPalette.allow },
  { label: "Medium (25%)", value: 25, color: govPalette.warn },
  { label: "High (38%)", value: 38, color: govPalette.block },
];

const EXAMPLE_PROMPTS = [
  "I agreed to help with another project tonight",
  "I need to finish this report before tomorrow",
  "Skip my morning walk today",
  "Move my focus block to take a meeting",
  "I should do some exercise",
];

export default function TryItYourself() {
  const [userText, setUserText] = useState("");
  const [hour, setHour] = useState(15);
  const [drift, setDrift] = useState(10);
  const [results, setResults] = useState<Record<string, GateDecision | null>>({});
  const [evaluating, setEvaluating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const evaluate = useCallback(async () => {
    if (!userText.trim()) return;
    setEvaluating(true);
    setError(null);
    setResults({});

    const frictionState = drift >= 35 ? "chaos" : drift >= 25 ? "intensity" : "balanced";
    const proposedAction = inferAction(userText);

    try {
      const promises = GOV_PROFILES.map(async (profile) => {
        const profileDrift = adjustDriftForProfile(drift, profile.id);
        const res = await fetch("/api/demo/simulation/evaluate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            person_id: DEMO_USER_ID,
            scenario_id: "sandbox",
            profile: profile.id,
            action_context: {
              proposed_action: proposedAction,
              proposed_hour: hour,
              drift_percentage: profileDrift,
              friction_state: frictionState,
              user_text: userText,
            },
          }),
        });

        if (!res.ok) throw new Error(`Failed for ${profile.label}`);
        const decision: GateDecision = await res.json();
        return { profileId: profile.id, decision };
      });

      const evaluations = await Promise.all(promises);
      const newResults: Record<string, GateDecision | null> = {};
      for (const ev of evaluations) {
        if (ev) newResults[ev.profileId] = ev.decision;
      }
      setResults(newResults);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Evaluation failed");
    } finally {
      setEvaluating(false);
    }
  }, [userText, hour, drift]);

  const hasResults = Object.keys(results).length > 0;

  return (
    <div
      style={{
        marginTop: 32,
        padding: 24,
        borderRadius: 12,
        background: govPalette.card,
        border: `1px solid ${govPalette.accent}30`,
      }}
    >
      {/* Header */}
      <div style={{ marginBottom: 20 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
          <span style={{ fontSize: 11, fontWeight: 600, color: govPalette.accent, textTransform: "uppercase", letterSpacing: 1 }}>
            Interactive
          </span>
        </div>
        <h3 style={{ fontSize: 18, fontWeight: 700, color: govPalette.text, margin: 0 }}>
          Try It Yourself
        </h3>
        <p style={{ fontSize: 12, color: govPalette.muted, margin: "4px 0 0" }}>
          Type any action and see how governance responds across all three constitutions.
        </p>
      </div>

      {/* Input area */}
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {/* Text input */}
        <div>
          <label style={{ fontSize: 11, fontWeight: 600, color: govPalette.dim, display: "block", marginBottom: 4 }}>
            What do you want to do?
          </label>
          <input
            type="text"
            value={userText}
            onChange={(e) => setUserText(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && evaluate()}
            placeholder="e.g. I need to finish this report before tomorrow"
            style={{
              width: "100%",
              padding: "10px 14px",
              borderRadius: 8,
              border: `1px solid ${govPalette.border}`,
              background: govPalette.bg,
              color: govPalette.text,
              fontSize: 14,
              outline: "none",
              boxSizing: "border-box",
            }}
          />
          {/* Quick examples */}
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 6 }}>
            {EXAMPLE_PROMPTS.map((prompt) => (
              <button
                key={prompt}
                onClick={() => setUserText(prompt)}
                style={{
                  padding: "3px 8px",
                  borderRadius: 10,
                  border: `1px solid ${govPalette.border}`,
                  background: userText === prompt ? govPalette.accentLight : "transparent",
                  color: govPalette.muted,
                  fontSize: 10,
                  cursor: "pointer",
                  whiteSpace: "nowrap",
                }}
              >
                {prompt}
              </button>
            ))}
          </div>
        </div>

        {/* Controls row */}
        <div style={{ display: "flex", gap: 16, alignItems: "flex-end", flexWrap: "wrap" }}>
          {/* Time picker */}
          <div style={{ flex: 1, minWidth: 120 }}>
            <label style={{ fontSize: 11, fontWeight: 600, color: govPalette.dim, display: "block", marginBottom: 4 }}>
              Time of day
            </label>
            <select
              value={hour}
              onChange={(e) => setHour(Number(e.target.value))}
              style={{
                width: "100%",
                padding: "8px 12px",
                borderRadius: 8,
                border: `1px solid ${govPalette.border}`,
                background: govPalette.bg,
                color: govPalette.text,
                fontSize: 13,
                cursor: "pointer",
              }}
            >
              {HOUR_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>

          {/* Drift level */}
          <div style={{ flex: 1, minWidth: 200 }}>
            <label style={{ fontSize: 11, fontWeight: 600, color: govPalette.dim, display: "block", marginBottom: 4 }}>
              Drift level
            </label>
            <div style={{ display: "flex", gap: 6 }}>
              {DRIFT_PRESETS.map((d) => (
                <button
                  key={d.value}
                  onClick={() => setDrift(d.value)}
                  style={{
                    flex: 1,
                    padding: "6px 10px",
                    borderRadius: 6,
                    border: `1px solid ${drift === d.value ? d.color : govPalette.border}`,
                    background: drift === d.value ? `${d.color}10` : "transparent",
                    color: drift === d.value ? d.color : govPalette.muted,
                    fontSize: 11,
                    fontWeight: drift === d.value ? 600 : 400,
                    cursor: "pointer",
                  }}
                >
                  {d.label}
                </button>
              ))}
            </div>
          </div>

          {/* Evaluate button */}
          <button
            onClick={evaluate}
            disabled={!userText.trim() || evaluating}
            style={{
              padding: "10px 24px",
              borderRadius: 8,
              border: "none",
              background: userText.trim() && !evaluating ? govPalette.accent : govPalette.border,
              color: userText.trim() && !evaluating ? "#fff" : govPalette.veryDim,
              fontSize: 13,
              fontWeight: 600,
              cursor: userText.trim() && !evaluating ? "pointer" : "default",
              whiteSpace: "nowrap",
            }}
          >
            {evaluating ? "Evaluating..." : "Evaluate"}
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div style={{ marginTop: 12, padding: "8px 12px", borderRadius: 6, background: govPalette.blockBg, fontSize: 12, color: govPalette.block }}>
          {error}
        </div>
      )}

      {/* Results */}
      {(hasResults || evaluating) && (
        <div style={{ marginTop: 20, paddingTop: 20, borderTop: `1px solid ${govPalette.border}` }}>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(3, 1fr)",
              gap: 12,
            }}
          >
            {GOV_PROFILES.map((profile) => {
              const decision = results[profile.id] || null;
              return (
                <div
                  key={profile.id}
                  style={{
                    padding: 12,
                    borderRadius: 10,
                    border: `1px solid ${govPalette.border}`,
                    background: govPalette.bg,
                  }}
                >
                  {/* Profile header */}
                  <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
                    <div style={{ width: 8, height: 8, borderRadius: "50%", background: profile.color }} />
                    <span style={{ fontSize: 12, fontWeight: 700, color: profile.color }}>
                      {profile.label}
                    </span>
                    <span style={{ fontSize: 10, color: govPalette.veryDim, marginLeft: "auto" }}>
                      drift: {adjustDriftForProfile(drift, profile.id)}%
                    </span>
                  </div>

                  {/* Gate Result */}
                  <GateResult decision={decision} loading={evaluating} />

                  {/* Violations */}
                  {decision && decision.violations && decision.violations.length > 0 && (
                    <div style={{ display: "flex", flexDirection: "column", gap: 4, marginTop: 8 }}>
                      {decision.violations.map((v, i) => (
                        <ViolationCard key={i} violation={v} />
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

/** Adjust drift per profile to show constitutional differences */
function adjustDriftForProfile(baseDrift: number, profileId: string): number {
  switch (profileId) {
    case "adaptive": return Math.min(baseDrift + 15, 50); // Vata: higher drift
    case "performance": return Math.min(baseDrift + 8, 45); // Pitta: moderate
    case "conservation": return baseDrift; // Kapha: stable baseline
    default: return baseDrift;
  }
}

/** Infer a proposed_action from user text */
function inferAction(text: string): string {
  const lower = text.toLowerCase();
  if (lower.includes("commit") || lower.includes("agree") || lower.includes("said yes") || lower.includes("help") || lower.includes("project") || lower.includes("volunteer"))
    return "accept_commitment";
  if (lower.includes("exercise") || lower.includes("walk") || lower.includes("run") || lower.includes("workout"))
    return "suggest_exercise";
  if (lower.includes("email") || lower.includes("reply") || lower.includes("draft") || lower.includes("send"))
    return "email_reply";
  if (lower.includes("focus") || lower.includes("reschedule") || lower.includes("move") || lower.includes("meeting") || lower.includes("calendar"))
    return "reschedule_focus";
  if (lower.includes("work") || lower.includes("report") || lower.includes("finish") || lower.includes("review") || lower.includes("task"))
    return "suggest_productivity";
  if (lower.includes("sleep") || lower.includes("rest") || lower.includes("meditat"))
    return "suggest_rest";
  return "conversation_turn";
}
