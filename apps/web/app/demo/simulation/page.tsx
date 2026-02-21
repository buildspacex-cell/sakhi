"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import type { GateDecision, LedgerEvent } from "./types";
import { SCENARIOS, PROFILES, DEMO_USER_ID } from "./scenarioConfigs";
import TimelineNav from "./components/TimelineNav";
import ProfileColumns from "./components/ProfileColumns";
import GovernanceLedger from "./components/GovernanceLedger";
import EpilogueSummary from "./components/EpilogueSummary";

export const dynamic = "force-dynamic";

type ProfileId = "adaptive" | "performance" | "conservation";

export default function SimulationPage() {
  const [currentScenario, setCurrentScenario] = useState(0);
  const [showEpilogue, setShowEpilogue] = useState(false);
  const [seeded, setSeeded] = useState(false);
  const [seeding, setSeeding] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Results: scenarioId → profileId → GateDecision
  const [results, setResults] = useState<Record<string, Record<string, GateDecision>>>({});
  // Ledger events from real API
  const [ledger, setLedger] = useState<LedgerEvent[]>([]);
  // Track which scenarios have been evaluated
  const [completedScenarios, setCompletedScenarios] = useState<Set<number>>(new Set());
  // Loading state for current evaluation
  const [evaluating, setEvaluating] = useState(false);

  const evaluatedRef = useRef<Set<string>>(new Set());

  // ── Seed on mount ──────────────────────────────────────────────────
  useEffect(() => {
    async function seed() {
      setSeeding(true);
      try {
        const res = await fetch("/api/demo/simulation/seed", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ person_id: DEMO_USER_ID }),
        });
        if (!res.ok) throw new Error(`Seed failed: ${res.status}`);
        setSeeded(true);
      } catch (e) {
        console.error("Seed error:", e);
        setError(e instanceof Error ? e.message : "Failed to seed");
      } finally {
        setSeeding(false);
      }
    }
    seed();
  }, []);

  // ── Evaluate current scenario ──────────────────────────────────────
  const evaluateScenario = useCallback(
    async (scenarioIndex: number) => {
      const scenario = SCENARIOS[scenarioIndex];
      if (!scenario || !seeded) return;
      if (evaluatedRef.current.has(scenario.id)) return;

      evaluatedRef.current.add(scenario.id);
      setEvaluating(true);
      setError(null);

      try {
        // 3 parallel evaluate calls — one per profile
        const promises = PROFILES.map(async (profile) => {
          const profileData = scenario.profiles[profile.id];
          if (!profileData) return null;

          const res = await fetch("/api/demo/simulation/evaluate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              person_id: DEMO_USER_ID,
              scenario_id: scenario.id,
              profile: profile.id,
              action_context: profileData.actionContext,
            }),
          });

          if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(
              `Evaluate failed for ${profile.id}: ${(err as Record<string, string>).error || res.status}`
            );
          }

          const decision: GateDecision = await res.json();
          return { profileId: profile.id, decision };
        });

        const evaluations = await Promise.all(promises);

        // Store results
        setResults((prev) => {
          const scenarioResults: Record<string, GateDecision> = {};
          for (const ev of evaluations) {
            if (ev) scenarioResults[ev.profileId] = ev.decision;
          }
          return { ...prev, [scenario.id]: scenarioResults };
        });

        setCompletedScenarios((prev) => new Set(Array.from(prev).concat(scenarioIndex)));

        // Refresh ledger
        const ledgerRes = await fetch(
          `/api/demo/simulation/ledger?person_id=${DEMO_USER_ID}&limit=100`
        );
        if (ledgerRes.ok) {
          const data = await ledgerRes.json();
          setLedger(Array.isArray(data) ? data : data.events || []);
        }
      } catch (e) {
        console.error("Evaluate error:", e);
        setError(e instanceof Error ? e.message : "Evaluation failed");
        evaluatedRef.current.delete(scenario.id);
      } finally {
        setEvaluating(false);
      }
    },
    [seeded]
  );

  // Auto-evaluate when scenario changes
  useEffect(() => {
    if (seeded && !showEpilogue) {
      evaluateScenario(currentScenario);
    }
  }, [currentScenario, seeded, showEpilogue, evaluateScenario]);

  // ── Navigation ─────────────────────────────────────────────────────
  const goNext = () => {
    if (currentScenario < SCENARIOS.length - 1) {
      setCurrentScenario((i) => i + 1);
    } else {
      setShowEpilogue(true);
    }
  };

  const goPrev = () => {
    if (showEpilogue) {
      setShowEpilogue(false);
    } else if (currentScenario > 0) {
      setCurrentScenario((i) => i - 1);
    }
  };

  // ── Reset ──────────────────────────────────────────────────────────
  const handleReset = async () => {
    setResults({});
    setLedger([]);
    setCompletedScenarios(new Set());
    setCurrentScenario(0);
    setShowEpilogue(false);
    evaluatedRef.current.clear();
    setSeeded(false);
    setError(null);

    try {
      await fetch("/api/demo/simulation/reset", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ person_id: DEMO_USER_ID }),
      });
      setSeeded(true);
    } catch (e) {
      setError("Reset failed");
    }
  };

  // ── Current scenario data ─────────────────────────────────────────
  const scenario = SCENARIOS[currentScenario];
  const scenarioDecisions = results[scenario?.id] || {};

  // Build per-profile ledger events
  const profileLedgerEvents: Record<string, LedgerEvent[]> = {};
  for (const p of PROFILES) {
    profileLedgerEvents[p.id] = ledger.filter(
      (e) =>
        e.data &&
        (e.data as Record<string, unknown>).profile === p.id &&
        (e.data as Record<string, unknown>).scenario_id === scenario?.id
    );
  }

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#0e0f12",
        color: "#f4f4f5",
        padding: "24px",
      }}
    >
      {/* Header */}
      <div style={{ maxWidth: 1200, margin: "0 auto" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
          <div>
            <h1 style={{ fontSize: 24, fontWeight: 700, margin: 0 }}>
              A Day with Sakhi
            </h1>
            <p style={{ fontSize: 13, color: "#71717a", margin: "4px 0 0" }}>
              Same situation. Different constitution. Watch governance decide.
            </p>
          </div>
          <button
            onClick={handleReset}
            style={{
              padding: "6px 14px",
              borderRadius: 6,
              border: "1px solid #27272a",
              background: "#1a1b1e",
              color: "#71717a",
              fontSize: 12,
              cursor: "pointer",
            }}
          >
            Reset
          </button>
        </div>

        {/* Seeding state */}
        {seeding && (
          <div style={{ padding: "12px 16px", borderRadius: 8, background: "#1a1b1e", border: "1px solid #27272a", marginBottom: 16, fontSize: 12, color: "#a1a1aa" }}>
            Seeding governance constraints and events...
          </div>
        )}

        {/* Error */}
        {error && (
          <div style={{ padding: "12px 16px", borderRadius: 8, background: "rgba(239,68,68,0.1)", border: "1px solid #ef444440", marginBottom: 16, fontSize: 12, color: "#fca5a5" }}>
            {error}
          </div>
        )}

        {/* Timeline */}
        <TimelineNav
          scenarios={SCENARIOS}
          currentIndex={currentScenario}
          completedIndices={completedScenarios}
          onSelect={(i) => {
            setShowEpilogue(false);
            setCurrentScenario(i);
          }}
          showEpilogue={showEpilogue}
          onEpilogue={() => setShowEpilogue(true)}
        />

        {/* Main content */}
        {!showEpilogue && scenario ? (
          <div>
            {/* Scenario header */}
            <div style={{ marginBottom: 20 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <span style={{ fontSize: 22 }}>{scenario.icon}</span>
                <div>
                  <h2 style={{ fontSize: 18, fontWeight: 700, margin: 0 }}>
                    {scenario.time} — {scenario.title}
                  </h2>
                  <p style={{ fontSize: 12, color: "#71717a", margin: "2px 0 0" }}>
                    {scenario.subtitle}
                  </p>
                </div>
                <span
                  style={{
                    marginLeft: "auto",
                    fontSize: 11,
                    color: "#52525b",
                    fontFamily: "monospace",
                  }}
                >
                  [{currentScenario + 1}/{SCENARIOS.length}]
                </span>
              </div>
            </div>

            {/* 3-column profile comparison */}
            <ProfileColumns
              scenario={scenario}
              decisions={scenarioDecisions}
              ledgerEvents={profileLedgerEvents}
              loading={evaluating}
            />

            {/* Navigation */}
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                marginTop: 24,
                paddingTop: 16,
                borderTop: "1px solid #1a1b1e",
              }}
            >
              <button
                onClick={goPrev}
                disabled={currentScenario === 0}
                style={{
                  padding: "8px 20px",
                  borderRadius: 8,
                  border: "1px solid #27272a",
                  background: "#1a1b1e",
                  color: currentScenario === 0 ? "#3f3f46" : "#a1a1aa",
                  fontSize: 13,
                  cursor: currentScenario === 0 ? "default" : "pointer",
                }}
              >
                Previous
              </button>
              <button
                onClick={goNext}
                disabled={!completedScenarios.has(currentScenario)}
                style={{
                  padding: "8px 20px",
                  borderRadius: 8,
                  border: "none",
                  background: completedScenarios.has(currentScenario)
                    ? "#6366f1"
                    : "#27272a",
                  color: completedScenarios.has(currentScenario)
                    ? "#ffffff"
                    : "#52525b",
                  fontSize: 13,
                  fontWeight: 600,
                  cursor: completedScenarios.has(currentScenario)
                    ? "pointer"
                    : "default",
                }}
              >
                {currentScenario === SCENARIOS.length - 1 ? "View Summary" : "Next Scenario"}
              </button>
            </div>
          </div>
        ) : showEpilogue ? (
          <div>
            <EpilogueSummary results={results} />
            <div style={{ marginTop: 32 }}>
              <GovernanceLedger events={ledger} />
            </div>
            <div style={{ textAlign: "center", marginTop: 24 }}>
              <button
                onClick={goPrev}
                style={{
                  padding: "8px 20px",
                  borderRadius: 8,
                  border: "1px solid #27272a",
                  background: "#1a1b1e",
                  color: "#a1a1aa",
                  fontSize: 13,
                  cursor: "pointer",
                }}
              >
                Back to scenarios
              </button>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
