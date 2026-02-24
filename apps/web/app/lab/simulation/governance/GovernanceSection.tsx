"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import type { GateDecision, LedgerEvent } from "@/app/demo/simulation/types";
import { SCENARIOS, DEMO_USER_ID } from "@/app/demo/simulation/scenarioConfigs";
import { GOV_PROFILES, govPalette } from "./theme";
import TimelineNav from "./components/TimelineNav";
import ProfileColumns from "./components/ProfileColumns";
import GovernanceLedger from "./components/GovernanceLedger";
import EpilogueSummary from "./components/EpilogueSummary";
import TryItYourself from "./components/TryItYourself";

export default function GovernanceSection() {
  const [currentScenario, setCurrentScenario] = useState(0);
  const [showEpilogue, setShowEpilogue] = useState(false);
  const [seeded, setSeeded] = useState(false);
  const [seeding, setSeeding] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [results, setResults] = useState<Record<string, Record<string, GateDecision>>>({});
  const [ledger, setLedger] = useState<LedgerEvent[]>([]);
  const [completedScenarios, setCompletedScenarios] = useState<Set<number>>(new Set());
  const [evaluating, setEvaluating] = useState(false);

  const evaluatedRef = useRef<Set<string>>(new Set());

  // Lazy-mount: only seed when this section becomes visible
  const sectionRef = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) setVisible(true); },
      { rootMargin: "200px" }
    );
    if (sectionRef.current) observer.observe(sectionRef.current);
    return () => observer.disconnect();
  }, []);

  // Seed when visible
  useEffect(() => {
    if (!visible || seeded || seeding) return;
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
        setError(e instanceof Error ? e.message : "Failed to seed");
      } finally {
        setSeeding(false);
      }
    }
    seed();
  }, [visible, seeded, seeding]);

  // Evaluate current scenario
  const evaluateScenario = useCallback(
    async (scenarioIndex: number) => {
      const scenario = SCENARIOS[scenarioIndex];
      if (!scenario || !seeded) return;
      if (evaluatedRef.current.has(scenario.id)) return;

      evaluatedRef.current.add(scenario.id);
      setEvaluating(true);
      setError(null);

      try {
        const promises = GOV_PROFILES.map(async (profile) => {
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

        setResults((prev) => {
          const scenarioResults: Record<string, GateDecision> = {};
          for (const ev of evaluations) {
            if (ev) scenarioResults[ev.profileId] = ev.decision;
          }
          return { ...prev, [scenario.id]: scenarioResults };
        });

        setCompletedScenarios((prev) => new Set(Array.from(prev).concat(scenarioIndex)));

        const ledgerRes = await fetch(
          `/api/demo/simulation/ledger?person_id=${DEMO_USER_ID}&limit=100`
        );
        if (ledgerRes.ok) {
          const data = await ledgerRes.json();
          setLedger(Array.isArray(data) ? data : data.events || []);
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : "Evaluation failed");
        evaluatedRef.current.delete(scenario.id);
      } finally {
        setEvaluating(false);
      }
    },
    [seeded]
  );

  useEffect(() => {
    if (seeded && !showEpilogue) {
      evaluateScenario(currentScenario);
    }
  }, [currentScenario, seeded, showEpilogue, evaluateScenario]);

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
    } catch {
      setError("Reset failed");
    }
  };

  const scenario = SCENARIOS[currentScenario];
  const scenarioDecisions = results[scenario?.id] || {};

  const profileLedgerEvents: Record<string, LedgerEvent[]> = {};
  for (const p of GOV_PROFILES) {
    profileLedgerEvents[p.id] = ledger.filter(
      (e) =>
        e.data &&
        (e.data as Record<string, unknown>).profile === p.id &&
        (e.data as Record<string, unknown>).scenario_id === scenario?.id
    );
  }

  return (
    <div ref={sectionRef} id="governance">
      {!visible ? (
        <div style={{ height: 400 }} />
      ) : (
        <>
          {/* Section header */}
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
            <div>
              <h2 style={{ fontSize: 22, fontWeight: 700, color: govPalette.text, margin: 0 }}>
                A Day with Sakhi
              </h2>
              <p style={{ fontSize: 13, color: govPalette.muted, margin: "4px 0 0" }}>
                Same situation. Different constitution. Watch governance decide.
              </p>
            </div>
            <button
              onClick={handleReset}
              style={{
                padding: "6px 14px",
                borderRadius: 6,
                border: `1px solid ${govPalette.border}`,
                background: govPalette.cardAlt,
                color: govPalette.muted,
                fontSize: 12,
                cursor: "pointer",
              }}
            >
              Reset
            </button>
          </div>

          {/* Seeding */}
          {seeding && (
            <div style={{ padding: "12px 16px", borderRadius: 8, background: govPalette.cardAlt, border: `1px solid ${govPalette.border}`, marginBottom: 16, fontSize: 12, color: govPalette.muted }}>
              Seeding governance constraints and events...
            </div>
          )}

          {/* Error */}
          {error && (
            <div style={{ padding: "12px 16px", borderRadius: 8, background: govPalette.blockBg, border: `1px solid ${govPalette.block}30`, marginBottom: 16, fontSize: 12, color: govPalette.block }}>
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
              <div style={{ marginBottom: 16 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <span style={{ fontSize: 22 }}>{scenario.icon}</span>
                  <div>
                    <h3 style={{ fontSize: 17, fontWeight: 700, margin: 0, color: govPalette.text }}>
                      {scenario.time} — {scenario.title}
                    </h3>
                    <p style={{ fontSize: 12, color: govPalette.dim, margin: "2px 0 0" }}>
                      {scenario.subtitle}
                    </p>
                  </div>
                  <span
                    style={{
                      marginLeft: "auto",
                      fontSize: 11,
                      color: govPalette.veryDim,
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
                  borderTop: `1px solid ${govPalette.border}`,
                }}
              >
                <button
                  onClick={goPrev}
                  disabled={currentScenario === 0}
                  style={{
                    padding: "8px 20px",
                    borderRadius: 8,
                    border: `1px solid ${govPalette.border}`,
                    background: govPalette.card,
                    color: currentScenario === 0 ? govPalette.veryDim : govPalette.muted,
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
                      ? govPalette.accent
                      : govPalette.border,
                    color: completedScenarios.has(currentScenario)
                      ? "#ffffff"
                      : govPalette.veryDim,
                    fontSize: 13,
                    fontWeight: 600,
                    cursor: completedScenarios.has(currentScenario) ? "pointer" : "default",
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
                    border: `1px solid ${govPalette.border}`,
                    background: govPalette.card,
                    color: govPalette.muted,
                    fontSize: 13,
                    cursor: "pointer",
                  }}
                >
                  Back to scenarios
                </button>
              </div>
            </div>
          ) : null}

          {/* Interactive sandbox */}
          {seeded && <TryItYourself />}
        </>
      )}
    </div>
  );
}
