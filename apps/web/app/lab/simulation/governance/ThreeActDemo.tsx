"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import type { GateDecision, LedgerEvent, IntelligenceData, IntelligenceItem } from "@/app/demo/simulation/types";
import {
  DEMO_USER_ID,
  ACT_II_SCENARIO,
  ACT_III_SCENARIO,
  ACT_III_STATE_PROFILES,
} from "./actScenarioConfig";
import { govPalette } from "./theme";
import ActI_Illusion from "./components/ActI_Illusion";
import ActII_Reveal from "./components/ActII_Reveal";
import ActIII_Divergence from "./components/ActIII_Divergence";
import GovernanceLedger from "./components/GovernanceLedger";
import TryItYourself from "./components/TryItYourself";

type Act = 1 | 2 | 3 | "post";

export default function ThreeActDemo() {
  const [currentAct, setCurrentAct] = useState<Act>(1);
  const [seeded, setSeeded] = useState(false);
  const [seeding, setSeeding] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Ref to avoid stale closures in evaluate callbacks
  const seededRef = useRef(false);

  // Act II state
  const [actIIDecision, setActIIDecision] = useState<GateDecision | null>(null);
  const [actIILoading, setActIILoading] = useState(false);

  // Act III state
  const [actIIIDecisions, setActIIIDecisions] = useState<Record<string, GateDecision>>({});
  const [actIIILoading, setActIIILoading] = useState(false);
  const [actIIILedger, setActIIILedger] = useState<Record<string, LedgerEvent[]>>({});

  // Intelligence data (from real backend)
  const [intelligence, setIntelligence] = useState<IntelligenceData | null>(null);

  // Ledger
  const [ledger, setLedger] = useState<LedgerEvent[]>([]);

  // Track pending evaluate requests (user clicked before seed finished)
  const pendingEvalRef = useRef<"actII" | "actIII" | null>(null);

  // Lazy-mount: seed when section becomes visible
  const sectionRef = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) setVisible(true);
      },
      { rootMargin: "200px" }
    );
    if (sectionRef.current) observer.observe(sectionRef.current);
    return () => observer.disconnect();
  }, []);

  // Seed on visibility
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
        seededRef.current = true;
        setSeeded(true);

        // Fetch intelligence data from real backend
        const intelRes = await fetch(
          `/api/demo/simulation/intelligence?person_id=${DEMO_USER_ID}`
        );
        if (intelRes.ok) {
          const intelData = await intelRes.json();
          setIntelligence(intelData as IntelligenceData);
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to seed");
      } finally {
        setSeeding(false);
      }
    }
    seed();
  }, [visible, seeded, seeding]);

  // Evaluate Act II (single profile: adaptive)
  const evaluateActII = useCallback(async () => {
    if (!seededRef.current) {
      pendingEvalRef.current = "actII";
      return;
    }
    setActIILoading(true);
    setError(null);
    try {
      const profileData = ACT_II_SCENARIO.profiles["adaptive"];
      if (!profileData) throw new Error("No adaptive profile data");

      const res = await fetch("/api/demo/simulation/evaluate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          person_id: DEMO_USER_ID,
          scenario_id: ACT_II_SCENARIO.id,
          profile: "adaptive",
          action_context: profileData.actionContext,
        }),
      });
      if (!res.ok) throw new Error(`Evaluate failed: ${res.status}`);
      const decision: GateDecision = await res.json();
      setActIIDecision(decision);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Evaluation failed");
    } finally {
      setActIILoading(false);
    }
  }, []);

  // Evaluate Act III (all 3 profiles)
  const evaluateActIII = useCallback(async () => {
    if (!seededRef.current) {
      pendingEvalRef.current = "actIII";
      return;
    }
    setActIIILoading(true);
    setError(null);
    try {
      const promises = ACT_III_STATE_PROFILES.map(async (stateProfile) => {
        const profileData = ACT_III_SCENARIO.profiles[stateProfile.id];
        if (!profileData) return null;

        const res = await fetch("/api/demo/simulation/evaluate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            person_id: DEMO_USER_ID,
            scenario_id: ACT_III_SCENARIO.id,
            profile: "performance",  // Always Pitta — same constitution, different states
            action_context: profileData.actionContext,
          }),
        });
        if (!res.ok) throw new Error(`Evaluate failed for ${stateProfile.label}`);
        const decision: GateDecision = await res.json();
        return { profileId: stateProfile.id, decision };
      });

      const settled = await Promise.allSettled(promises);
      const newDecisions: Record<string, GateDecision> = {};
      for (const result of settled) {
        if (result.status === "fulfilled" && result.value) {
          newDecisions[result.value.profileId] = result.value.decision;
        }
      }
      setActIIIDecisions(newDecisions);

      // Fetch ledger
      const ledgerRes = await fetch(
        `/api/demo/simulation/ledger?person_id=${DEMO_USER_ID}&limit=100`
      );
      if (ledgerRes.ok) {
        const data = await ledgerRes.json();
        const allEvents: LedgerEvent[] = Array.isArray(data) ? data : data.events || [];
        setLedger(allEvents);

        // Split ledger by profile
        const byProfile: Record<string, LedgerEvent[]> = {};
        for (const sp of ACT_III_STATE_PROFILES) {
          byProfile[sp.id] = allEvents.filter(
            (e) =>
              e.data &&
              (e.data as Record<string, unknown>).scenario_id === ACT_III_SCENARIO.id
          );
        }
        setActIIILedger(byProfile);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Evaluation failed");
    } finally {
      setActIIILoading(false);
    }
  }, []);

  // Fire pending evaluation when seed completes
  useEffect(() => {
    if (!seeded || !pendingEvalRef.current) return;
    const pending = pendingEvalRef.current;
    pendingEvalRef.current = null;
    if (pending === "actII") evaluateActII();
    else if (pending === "actIII") evaluateActIII();
  }, [seeded, evaluateActII, evaluateActIII]);

  // Act transitions
  const goToActII = useCallback(() => {
    setCurrentAct(2);
    evaluateActII();
  }, [evaluateActII]);

  const goToActIII = useCallback(() => {
    setCurrentAct(3);
    evaluateActIII();
  }, [evaluateActIII]);

  const handleReset = async () => {
    setCurrentAct(1);
    setActIIDecision(null);
    setActIIIDecisions({});
    setActIIILedger({});
    setLedger([]);
    setIntelligence(null);
    seededRef.current = false;
    setSeeded(false);
    setError(null);

    try {
      await fetch("/api/demo/simulation/reset", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ person_id: DEMO_USER_ID }),
      });
      seededRef.current = true;
      setSeeded(true);
    } catch {
      setError("Reset failed");
    }
  };

  return (
    <div ref={sectionRef} id="governance">
      {!visible ? (
        <div style={{ height: 200 }} />
      ) : (
        <>
          {/* Section header */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              marginBottom: 20,
            }}
          >
            <div>
              <h2
                style={{
                  fontSize: 24,
                  fontWeight: 700,
                  color: govPalette.text,
                  margin: 0,
                }}
              >
                The Same Moment. Different Outcomes.
              </h2>
              <p
                style={{
                  fontSize: 14,
                  color: govPalette.muted,
                  margin: "4px 0 0",
                }}
              >
                What changes when AI understands who you are and who you&apos;re becoming.
              </p>
            </div>
            {currentAct !== 1 && (
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
            )}
          </div>

          {/* Seeding indicator */}
          {seeding && (
            <div
              style={{
                padding: "10px 14px",
                borderRadius: 8,
                background: govPalette.cardAlt,
                border: `1px solid ${govPalette.border}`,
                marginBottom: 16,
                fontSize: 12,
                color: govPalette.muted,
              }}
            >
              Preparing governance engine...
            </div>
          )}

          {/* Error */}
          {error && (
            <div
              style={{
                padding: "10px 14px",
                borderRadius: 8,
                background: govPalette.blockBg,
                border: `1px solid ${govPalette.block}30`,
                marginBottom: 16,
                fontSize: 12,
                color: govPalette.block,
              }}
            >
              {error}
            </div>
          )}

          {/* Act content */}
          <div
            style={{
              padding: 24,
              borderRadius: 12,
              background: govPalette.card,
              border: `1px solid ${govPalette.border}`,
              marginBottom: 24,
            }}
          >
            {currentAct === 1 && <ActI_Illusion onContinue={goToActII} />}

            {currentAct === 2 && (
              <ActII_Reveal
                scenario={ACT_II_SCENARIO}
                decision={actIIDecision}
                loading={actIILoading}
                onContinue={goToActIII}
                intelligence={intelligence}
              />
            )}

            {(currentAct === 3 || currentAct === "post") && (
              <ActIII_Divergence
                scenario={ACT_III_SCENARIO}
                decisions={actIIIDecisions}
                ledgerEvents={actIIILedger}
                loading={actIIILoading}
                intelligence={intelligence}
              />
            )}
          </div>

          {/* Post-Act III: Ledger + Sandbox */}
          {(currentAct === 3 || currentAct === "post") &&
            Object.keys(actIIIDecisions).length >= 2 && (
              <>
                {/* Ledger */}
                {ledger.length > 0 && (
                  <div style={{ marginBottom: 24 }}>
                    <GovernanceLedger events={ledger} />
                  </div>
                )}

                {/* Interactive sandbox */}
                <TryItYourself />
              </>
            )}
        </>
      )}
    </div>
  );
}
