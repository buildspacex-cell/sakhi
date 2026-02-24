"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import type { GateDecision, LedgerEvent, IntelligenceData } from "@/app/demo/simulation/types";
import { govPalette } from "../governance/theme";
import ProfileColumn from "../governance/components/ProfileColumn";
import ComingSoonCard from "./components/ComingSoonCard";
import {
  DEMO_USER_ID,
  PERSON_PROFILES,
  PROFILES_USER_STATEMENT,
  PROFILES_SCENARIO_ID,
} from "./profilesConfig";

export default function ProfilesContrast() {
  const [seeded, setSeeded] = useState(false);
  const [seeding, setSeeding] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const seededRef = useRef(false);

  const [decisions, setDecisions] = useState<Record<string, GateDecision>>({});
  const [loading, setLoading] = useState(false);
  const [intelligence, setIntelligence] = useState<IntelligenceData | null>(null);
  const [ledgerEvents, setLedgerEvents] = useState<Record<string, LedgerEvent[]>>({});

  // Lazy-mount
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

        // Fetch intelligence
        const intelRes = await fetch(
          `/api/demo/simulation/intelligence?person_id=${DEMO_USER_ID}`
        );
        if (intelRes.ok) {
          setIntelligence((await intelRes.json()) as IntelligenceData);
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to seed");
      } finally {
        setSeeding(false);
      }
    }
    seed();
  }, [visible, seeded, seeding]);

  // Evaluate active profiles once seeded
  const evaluate = useCallback(async () => {
    if (!seededRef.current) return;
    setLoading(true);
    setError(null);

    const activeProfiles = PERSON_PROFILES.filter(
      (p) => !p.isComingSoon && p.scenarioData
    );

    try {
      const promises = activeProfiles.map(async (person) => {
        const res = await fetch("/api/demo/simulation/evaluate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            person_id: DEMO_USER_ID,
            scenario_id: PROFILES_SCENARIO_ID,
            profile: person.constitutionType,
            action_context: person.scenarioData!.actionContext,
          }),
        });
        if (!res.ok) throw new Error(`Evaluate failed for ${person.name}`);
        const decision: GateDecision = await res.json();
        return { personId: person.id, decision };
      });

      const settled = await Promise.allSettled(promises);
      const newDecisions: Record<string, GateDecision> = {};
      for (const result of settled) {
        if (result.status === "fulfilled" && result.value) {
          newDecisions[result.value.personId] = result.value.decision;
        }
      }
      setDecisions(newDecisions);

      // Fetch ledger
      const ledgerRes = await fetch(
        `/api/demo/simulation/ledger?person_id=${DEMO_USER_ID}&limit=100`
      );
      if (ledgerRes.ok) {
        const data = await ledgerRes.json();
        const allEvents: LedgerEvent[] = Array.isArray(data)
          ? data
          : data.events || [];

        const byPerson: Record<string, LedgerEvent[]> = {};
        for (const person of activeProfiles) {
          byPerson[person.id] = allEvents.filter(
            (e) =>
              e.data &&
              (e.data as Record<string, unknown>).profile ===
                person.constitutionType &&
              (e.data as Record<string, unknown>).scenario_id ===
                PROFILES_SCENARIO_ID
          );
        }
        setLedgerEvents(byPerson);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Evaluation failed");
    } finally {
      setLoading(false);
    }
  }, []);

  // Auto-evaluate when seeded
  useEffect(() => {
    if (seeded) evaluate();
  }, [seeded, evaluate]);

  return (
    <div ref={sectionRef}>
      {!visible ? (
        <div style={{ height: 200 }} />
      ) : (
        <>
          {/* Hero header */}
          <div style={{ marginBottom: 20 }}>
            <h2
              style={{
                fontSize: 24,
                fontWeight: 700,
                color: govPalette.text,
                margin: 0,
              }}
            >
              Same Moment. Different People.
            </h2>
            <p
              style={{
                fontSize: 14,
                color: govPalette.muted,
                margin: "4px 0 0",
              }}
            >
              Three real people react to the same situation. Each gets a
              different right answer based on their constitution, life context,
              and current drift.
            </p>
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

          {/* Main content card */}
          <div
            style={{
              padding: 24,
              borderRadius: 12,
              background: govPalette.card,
              border: `1px solid ${govPalette.border}`,
            }}
          >
            {/* User statement */}
            <div
              style={{
                padding: "8px 12px",
                borderRadius: 8,
                background: govPalette.cardAlt,
                border: `1px solid ${govPalette.border}`,
                fontSize: 12,
                color: govPalette.dim,
                fontStyle: "italic",
                marginBottom: 16,
              }}
            >
              &ldquo;{PROFILES_USER_STATEMENT}&rdquo;
              <span
                style={{
                  display: "block",
                  fontSize: 10,
                  color: govPalette.veryDim,
                  marginTop: 4,
                  fontStyle: "normal",
                }}
              >
                6:45 PM
              </span>
            </div>

            {/* Three columns */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(3, 1fr)",
                gap: 12,
                alignItems: "stretch",
              }}
            >
              {PERSON_PROFILES.map((person) => {
                if (person.isComingSoon) {
                  return (
                    <ComingSoonCard key={person.id} profile={person} />
                  );
                }

                const decision = decisions[person.id] || null;
                const events = ledgerEvents[person.id] || [];

                return (
                  <ProfileColumn
                    key={person.id}
                    profile={person}
                    scenarioData={person.scenarioData!}
                    decision={decision}
                    ledgerEvents={events}
                    loading={loading}
                    divergent={!!decision}
                    intelligence={intelligence}
                  />
                );
              })}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
