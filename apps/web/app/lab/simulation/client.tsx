"use client";

import React, { useState, useEffect, useMemo, useCallback } from "react";
// Recharts v2 types don't fully match React 18 JSX types — cast to any
import {
  AreaChart as _AreaChart,
  Area as _Area,
  LineChart as _LineChart,
  Line as _Line,
  BarChart as _BarChart,
  Bar as _Bar,
  XAxis as _XAxis,
  YAxis as _YAxis,
  CartesianGrid as _CartesianGrid,
  Tooltip as _Tooltip,
  ResponsiveContainer as _ResponsiveContainer,
  ReferenceLine as _ReferenceLine,
  RadarChart as _RadarChart,
  Radar as _Radar,
  PolarGrid as _PolarGrid,
  PolarAngleAxis as _PolarAngleAxis,
  PolarRadiusAxis as _PolarRadiusAxis,
} from "recharts";
const AreaChart = _AreaChart as any;
const Area = _Area as any;
const LineChart = _LineChart as any;
const Line = _Line as any;
const BarChart = _BarChart as any;
const Bar = _Bar as any;
const XAxis = _XAxis as any;
const YAxis = _YAxis as any;
const CartesianGrid = _CartesianGrid as any;
const RTooltip = _Tooltip as any;
const ResponsiveContainer = _ResponsiveContainer as any;
const ReferenceLine = _ReferenceLine as any;
const RadarChart = _RadarChart as any;
const Radar = _Radar as any;
const PolarGrid = _PolarGrid as any;
const PolarAngleAxis = _PolarAngleAxis as any;
const PolarRadiusAxis = _PolarRadiusAxis as any;
import type {
  SimulationData,
  SimulationAddJournalResult,
  StateSnapshot,
  ArcPhase,
  PhaseBoundary,
  CheckpointResult,
  JournalEntry,
  BrainStates,
  ThemeSnapshot,
  CrystallizedPattern,
  ReplayFrictionState,
  SimulationContinuityData,
  CompiledContinuityTopic,
  CompiledContinuityArc,
  CompiledContinuityEntryTag,
  CompiledContinuityEventRef,
  TurnDebugData,
  ContinuityDeepReflectionResponse,
} from "./types";
import { makeAnchorLine, makeRecap, makeMirrorTitle } from "./continuityMirror";
import ThreeActDemo from "./governance/ThreeActDemo";

// ============================================================================
// Palette
// ============================================================================

const palette = {
  bg: "#faf8f5",
  card: "#ffffff",
  cardAlt: "#f5f0eb",
  border: "#e8e0d8",
  text: "#2d2a26",
  muted: "#8a7f73",
  accent: "#c4703f",
  accentLight: "#f0e0d0",
  // Friction states
  balanced: "#4caf7a",
  chaos: "#e05555",
  intensity: "#e6923a",
  stagnation: "#5b8db5",
  unknown: "#c4bdb5",
  // Doshas
  vata: "#7baed6",
  pitta: "#e6923a",
  kapha: "#6ab573",
  // Growth chart lines
  memories: "#7baed6",
  patterns: "#c4703f",
  nodes: "#6ab573",
  edges: "#e6923a",
};

type DeepReflectionRunMode = "deep_answer" | "topic_reflection";

type ContinuityEventRef = CompiledContinuityEventRef;
type PositionedContinuityEvent = ContinuityEventRef & {
  index: number;
  x: number;
  y: number;
  highlighted: boolean;
};

async function resolveSimulationUserId(personaId: string): Promise<string> {
  const res = await fetch(`/simulation/${personaId}.json?ts=${Date.now()}`, {
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Unable to load simulation user for ${personaId}`);
  }
  const payload = (await res.json()) as { user_id?: string };
  const userId = String(payload.user_id || "").trim();
  if (!userId) {
    throw new Error(`Simulation user_id missing for ${personaId}`);
  }
  return userId;
}

// ============================================================================
// Main Client Component
// ============================================================================

export default function SimulationDemoClient() {
  const [personaId, setPersonaId] = useState<string>("vidhya");
  const [data, setData] = useState<SimulationData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Timeline
  const [currentDay, setCurrentDay] = useState(1);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playSpeed, setPlaySpeed] = useState(400);

  // Narration mode — auto-pauses at phase transitions + checkpoints
  const [narrateMode, setNarrateMode] = useState(true);
  const [pauseReason, setPauseReason] = useState<string | null>(null);

  // Collapsible understanding section — governance leads the page
  const [showUnderstanding, setShowUnderstanding] = useState(false);

  // Conversation replay — step-based (0=not started, then 2 steps per entry: journal + reply)
  const [replayStep, setReplayStep] = useState(0);
  const [replayPlaying, setReplayPlaying] = useState(false);
  const [replaySpeed, setReplaySpeed] = useState(3000);

  // Ask Sakhi — add new journal entries to the live simulation
  const [askText, setAskText] = useState("");
  const [askTimeOfDay, setAskTimeOfDay] = useState<"morning" | "afternoon" | "evening">("evening");
  const [askLoading, setAskLoading] = useState(false);
  const [askError, setAskError] = useState<string | null>(null);
  const [askLastEntry, setAskLastEntry] = useState<{
    content: string;
    reply: string;
    friction_state?: ReplayFrictionState;
    day: number;
  } | null>(null);
  const [askLastDebug, setAskLastDebug] = useState<TurnDebugData | null>(null);
  const [askReflectionLoading, setAskReflectionLoading] = useState(false);
  const [askReflectionStatus, setAskReflectionStatus] = useState<string | null>(null);
  const [askReflectionError, setAskReflectionError] = useState<string | null>(null);
  const [askReflectionMode, setAskReflectionMode] = useState<DeepReflectionRunMode | null>(null);
  const [askReflectionResult, setAskReflectionResult] =
    useState<ContinuityDeepReflectionResponse | null>(null);

  const handleAskSakhi = useCallback(async () => {
    const content = askText.trim();
    if (!content || askLoading) return;
    setAskLoading(true);
    setAskError(null);
    setAskLastDebug(null);
    setAskReflectionError(null);
    setAskReflectionResult(null);
    setAskReflectionStatus(null);
    setAskReflectionMode(null);
    try {
      const res = await fetch("/api/demo/simulation/add-journal", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ persona_id: personaId, content, time_of_day: askTimeOfDay }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error((err.detail ?? err.error) || `Request failed (${res.status})`);
      }
      const result: SimulationAddJournalResult = await res.json();
      const newEntry: JournalEntry = result.entry;
      // Append to local data state so replay includes new entry immediately
      setData((prev) =>
        prev
          ? {
              ...prev,
              entries: [...prev.entries, newEntry],
              total_entries: result.total_entries,
              total_days: result.total_days,
            }
          : prev,
      );
      setAskLastDebug(result.turn_debug ?? null);
      setAskLastEntry({
        content,
        reply: newEntry.reply ?? "",
        friction_state: newEntry.friction_state,
        day: result.snapshot_day,
      });
      setAskText("");
      // Jump replay to the new entry
      setReplayStep(result.total_entries);
    } catch (e) {
      setAskError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setAskLoading(false);
    }
  }, [askText, askTimeOfDay, askLoading, personaId]);

  const handleRunAskDeepReflection = useCallback(async (mode: DeepReflectionRunMode) => {
    const topicKey = String(askLastDebug?.continuity_pack?.topic_key || "").trim();
    if (!topicKey || askReflectionLoading) return;
    const queryText = mode === "deep_answer" ? String(askLastEntry?.content || "").trim() : "";
    if (mode === "deep_answer" && !queryText) {
      setAskReflectionError("Deep Answer needs an active query from the latest user message.");
      return;
    }

    setAskReflectionLoading(true);
    setAskReflectionError(null);
    setAskReflectionResult(null);
    setAskReflectionStatus("enabling_policy");
    setAskReflectionMode(mode);

    try {
      const personId =
        String(data?.user_id || "").trim() || (await resolveSimulationUserId(personaId));

      const policyRes = await fetch("/api/continuity/policy/enable", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ person_id: personId }),
      });
      if (!policyRes.ok) {
        const policyErr = await policyRes.json().catch(() => ({}));
        throw new Error(
          (policyErr.detail ?? policyErr.error) || `Policy enable failed (${policyRes.status})`,
        );
      }

      setAskReflectionStatus("queued");
      const runRes = await fetch("/api/continuity/reflection/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          person_id: personId,
          topic_key: topicKey,
          window: "3650d",
          mode,
          user_query: mode === "deep_answer" ? queryText : undefined,
        }),
      });
      if (!runRes.ok) {
        const runErr = await runRes.json().catch(() => ({}));
        throw new Error((runErr.detail ?? runErr.error) || `Run failed (${runRes.status})`);
      }
      const runPayload = (await runRes.json()) as ContinuityDeepReflectionResponse;
      const reflectionId = String(runPayload.reflection_id || "").trim();
      if (!reflectionId) {
        throw new Error("Missing reflection_id in deep reflection response");
      }

      const fetchReflectionResult = async () => {
        const resultNonce = Date.now();
        const params = new URLSearchParams({
          id: reflectionId,
          person_id: personId,
          t: String(resultNonce),
        });
        const resultRes = await fetch(
          `/api/continuity/reflection/result?${params.toString()}`,
          { cache: "no-store" },
        );
        if (!resultRes.ok) {
          const resultErr = await resultRes.json().catch(() => ({}));
          throw new Error(
            (resultErr.detail ?? resultErr.error) || `Result failed (${resultRes.status})`,
          );
        }
        return (await resultRes.json()) as ContinuityDeepReflectionResponse;
      };

      let done = false;
      for (let attempt = 0; attempt < 60; attempt += 1) {
        const pollNonce = Date.now();
        const statusParams = new URLSearchParams({
          id: reflectionId,
          person_id: personId,
          t: String(pollNonce),
        });
        const statusRes = await fetch(
          `/api/continuity/reflection/status?${statusParams.toString()}`,
          { cache: "no-store" },
        );
        if (!statusRes.ok) {
          const statusErr = await statusRes.json().catch(() => ({}));
          throw new Error(
            (statusErr.detail ?? statusErr.error) || `Status failed (${statusRes.status})`,
          );
        }

        const statusPayload = (await statusRes.json()) as ContinuityDeepReflectionResponse;
        const status = String(statusPayload.status || "queued");
        setAskReflectionStatus(status);

        if (status === "done") {
          const resultPayload = await fetchReflectionResult();
          setAskReflectionResult(resultPayload);
          done = true;
          break;
        }

        if (status === "failed") {
          throw new Error(String(statusPayload.error || "Deep reflection failed"));
        }

        if (attempt % 3 === 0) {
          const probePayload = await fetchReflectionResult();
          const probeStatus = String(probePayload.status || "queued");
          if (probeStatus === "done" && probePayload.result) {
            setAskReflectionStatus("done");
            setAskReflectionResult(probePayload);
            done = true;
            break;
          }
          if (probeStatus === "failed") {
            throw new Error(String(probePayload.error || "Deep reflection failed"));
          }
        }

        await new Promise((resolve) => setTimeout(resolve, 2000));
      }

      if (!done) {
        const finalProbe = await fetchReflectionResult();
        const finalStatus = String(finalProbe.status || "queued");
        if (finalStatus === "done" && finalProbe.result) {
          setAskReflectionStatus("done");
          setAskReflectionResult(finalProbe);
          done = true;
        }
      }

      if (!done) {
        throw new Error("Deep reflection timed out after 120 seconds");
      }
    } catch (e) {
      setAskReflectionError(e instanceof Error ? e.message : "Deep reflection failed");
    } finally {
      setAskReflectionLoading(false);
    }
  }, [askLastDebug?.continuity_pack?.topic_key, askLastEntry?.content, askReflectionLoading, data?.user_id, personaId]);

  const reloadSimulationData = useCallback(
    async (targetPersonaId: string): Promise<SimulationData> => {
      const res = await fetch(`/simulation/${targetPersonaId}.json?ts=${Date.now()}`, {
        cache: "no-store",
      });
      if (!res.ok) throw new Error("Failed to load simulation data");
      const result: SimulationData = await res.json();
      setData(result);
      setError(null);
      return result;
    },
    [],
  );

  useEffect(() => {
    setAskReflectionLoading(false);
    setAskReflectionStatus(null);
    setAskReflectionError(null);
    setAskReflectionResult(null);
    setAskReflectionMode(null);
  }, [personaId]);

  // Load data — only when understanding section is visible
  useEffect(() => {
    if (!showUnderstanding) return;
    setLoading(true);
    setError(null);
    setCurrentDay(1);
    setIsPlaying(false);
    setReplayStep(0);
    setReplayPlaying(false);

    reloadSimulationData(personaId)
      .then(() => {
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, [personaId, showUnderstanding, reloadSimulationData]);

  // Compute phase boundary days and checkpoint days for narration pauses
  const pauseDays = useMemo(() => {
    if (!data) return new Set<number>();
    const days = new Set<number>();
    let cum = 0;
    for (const phase of data.persona.arc.phases) {
      if (cum > 0) days.add(cum + 1);
      cum += phase.duration_days;
    }
    for (const cp of data.persona.checkpoints) {
      days.add(cp.day);
    }
    return days;
  }, [data]);

  const getPauseLabel = useCallback(
    (day: number): string | null => {
      if (!data) return null;
      const cp = data.persona.checkpoints.find((c) => c.day === day);
      if (cp) return `Checkpoint: ${cp.name}`;
      let cum = 0;
      for (let i = 0; i < data.persona.arc.phases.length; i++) {
        cum += data.persona.arc.phases[i].duration_days;
        if (cum + 1 === day && i < data.persona.arc.phases.length - 1) {
          return `Phase Shift: ${data.persona.arc.phases[i + 1].name}`;
        }
      }
      return null;
    },
    [data],
  );

  // Auto-play with narration-aware pausing
  useEffect(() => {
    if (!isPlaying || !data) return;
    const timer = setInterval(() => {
      setCurrentDay((d) => {
        const next = d + 1;
        if (next > data.total_days) {
          setIsPlaying(false);
          return d;
        }
        if (narrateMode && pauseDays.has(next)) {
          setIsPlaying(false);
          setPauseReason(getPauseLabel(next) || "Key moment");
          return next;
        }
        setPauseReason(null);
        return next;
      });
    }, playSpeed);
    return () => clearInterval(timer);
  }, [isPlaying, playSpeed, data, narrateMode, pauseDays, getPauseLabel]);

  // Computed values
  const currentSnapshot = useMemo(() => {
    if (!data) return null;
    const candidates = data.snapshots.filter((s) => s.day <= currentDay);
    return candidates.length > 0 ? candidates[candidates.length - 1] : null;
  }, [data, currentDay]);

  const phaseBoundaries = useMemo((): PhaseBoundary[] => {
    if (!data) return [];
    const boundaries: PhaseBoundary[] = [];
    let cumulative = 0;
    for (const phase of data.persona.arc.phases) {
      boundaries.push({
        start: cumulative + 1,
        end: cumulative + phase.duration_days,
        phase,
      });
      cumulative += phase.duration_days;
    }
    return boundaries;
  }, [data]);

  const currentBoundary = useMemo((): PhaseBoundary | null => {
    for (const b of phaseBoundaries) {
      if (currentDay >= b.start && currentDay <= b.end) return b;
    }
    return phaseBoundaries[phaseBoundaries.length - 1] ?? null;
  }, [phaseBoundaries, currentDay]);

  const currentPhaseIndex = useMemo(() => {
    return phaseBoundaries.findIndex(
      (b) => currentDay >= b.start && currentDay <= b.end,
    );
  }, [phaseBoundaries, currentDay]);

  const dayEntries = useMemo(() => {
    if (!data) return [];
    return data.entries.filter((e) => e.day === currentDay);
  }, [data, currentDay]);

  // Final stats for normalization
  const finalStats = useMemo(() => {
    if (!data || data.snapshots.length === 0)
      return { mem: 1, pat: 1, nodes: 1, edges: 1 };
    const last = data.snapshots[data.snapshots.length - 1];
    return {
      mem: Math.max(last.memory_count ?? 1, 1),
      pat: Math.max(last.pattern_count ?? 1, 1),
      nodes: Math.max(last.provenance?.graph_nodes ?? 1, 1),
      edges: Math.max(last.provenance?.graph_edges ?? 1, 1),
    };
  }, [data]);

  // Soul evolution: track how the soul vector drifts from its initial state
  const soulEvolutionData = useMemo(() => {
    if (!data) return [];
    let baseVector: number[] | null = null;

    return data.snapshots
      .filter((s) => s.day <= currentDay)
      .map((s) => {
        const pm = s.personal_model as Record<string, any> | undefined;
        const svRaw = pm?.soul_vector;
        let vec: number[] | null = null;
        if (typeof svRaw === "string" && svRaw.startsWith("[")) {
          try {
            vec = JSON.parse(svRaw);
          } catch {}
        } else if (Array.isArray(svRaw)) {
          vec = svRaw;
        }

        if (vec && vec.length > 0 && !baseVector) {
          baseVector = vec;
        }

        let drift = 0;
        if (vec && baseVector && vec.length === baseVector.length) {
          let dot = 0,
            na = 0,
            nb = 0;
          for (let i = 0; i < vec.length; i++) {
            dot += baseVector[i] * vec[i];
            na += baseVector[i] * baseVector[i];
            nb += vec[i] * vec[i];
          }
          na = Math.sqrt(na);
          nb = Math.sqrt(nb);
          const cosSim = na > 0 && nb > 0 ? dot / (na * nb) : 1;
          drift = (1 - cosSim) * 100; // 0–100 scale
        }

        // Soul light count (strengths discovered)
        const slRaw = pm?.soul_light;
        let lightCount = 0;
        if (typeof slRaw === "string" && slRaw.startsWith("[")) {
          try {
            lightCount = JSON.parse(slRaw).length;
          } catch {}
        } else if (Array.isArray(slRaw)) {
          lightCount = slRaw.length;
        }

        // Soul friction areas count (tensions recognized)
        const sfRaw = pm?.soul_friction;
        let frictionCount = 0;
        if (typeof sfRaw === "string" && sfRaw.startsWith("[")) {
          try {
            const arr = JSON.parse(sfRaw) as any[];
            frictionCount = arr.filter(
              (f: any) => f && typeof f === "object" && f.areas,
            ).length;
          } catch {}
        } else if (Array.isArray(sfRaw)) {
          frictionCount = (sfRaw as any[]).filter(
            (f: any) => f && typeof f === "object" && f.areas,
          ).length;
        }

        return {
          day: s.day,
          drift: Math.round(drift * 10) / 10,
          lights: lightCount,
          frictions: frictionCount,
        };
      });
  }, [data, currentDay]);

  // Current episodic memory for side-by-side view
  const currentMemory = useMemo(() => {
    return currentSnapshot?.recent_memories?.[0] ?? null;
  }, [currentSnapshot]);

  // Entries processed up to current day
  const entriesUpToDay = useMemo(() => {
    if (!data) return 0;
    return data.entries.filter((e) => e.day <= currentDay).length;
  }, [data, currentDay]);

  // Radar chart dimensions (normalized 0-100)
  const radarData = useMemo(() => {
    if (!currentSnapshot) return [];
    const mem =
      ((currentSnapshot.memory_count ?? 0) / finalStats.mem) * 100;
    const pat =
      ((currentSnapshot.pattern_count ?? 0) / finalStats.pat) * 100;
    const nod =
      ((currentSnapshot.provenance?.graph_nodes ?? 0) / finalStats.nodes) *
      100;
    const edg =
      ((currentSnapshot.provenance?.graph_edges ?? 0) / finalStats.edges) *
      100;
    const nodes = currentSnapshot.provenance?.graph_nodes ?? 0;
    const edges = currentSnapshot.provenance?.graph_edges ?? 0;
    const density =
      nodes > 0 ? Math.min((edges / nodes / 10) * 100, 100) : 0;
    return [
      { dimension: "Stories", value: Math.round(mem) },
      { dimension: "Patterns", value: Math.round(pat) },
      { dimension: "Knowledge", value: Math.round(nod) },
      { dimension: "Connections", value: Math.round(edg) },
      { dimension: "Depth", value: Math.round(density) },
    ];
  }, [currentSnapshot, finalStats]);

  // Overall understanding depth (average of radar values)
  const overallDepth = useMemo(() => {
    if (radarData.length === 0) return 0;
    return Math.round(
      radarData.reduce((sum, d) => sum + d.value, 0) / radarData.length,
    );
  }, [radarData]);

  // Journal entries for the current phase (up to currentDay)
  const phaseEntries = useMemo(() => {
    if (!data || !currentBoundary) return [];
    return data.entries.filter(
      (e) =>
        e.day >= currentBoundary.start &&
        e.day <= Math.min(currentBoundary.end, currentDay),
    );
  }, [data, currentBoundary, currentDay]);

  // ── Conversation Replay Logic ──
  // 1 step per entry + 1 for governance = entries.length + 1
  const replayTotalSteps = data ? data.entries.length + 1 : 0;
  const replayEntryIndex = replayStep > 0 ? replayStep - 1 : -1;
  const replayShowGovernance = replayStep > 0 && replayStep >= replayTotalSteps;
  const replayCurrentDay =
    replayEntryIndex >= 0 && data
      ? (data.entries[Math.min(replayEntryIndex, data.entries.length - 1)]?.day ?? 0)
      : 0;

  // Phase boundaries for replay
  const replayPhaseBoundaries = useMemo(() => {
    if (!data) return [];
    const boundaries: PhaseBoundary[] = [];
    let cumulative = 0;
    for (const phase of data.persona.arc.phases) {
      boundaries.push({ start: cumulative + 1, end: cumulative + phase.duration_days, phase });
      cumulative += phase.duration_days;
    }
    return boundaries;
  }, [data]);

  // Current friction from snapshot for replay
  const replayCurrentFriction = useMemo<ReplayFrictionState | null>(() => {
    if (!data || replayCurrentDay === 0) return null;
    const snap = data.snapshots?.find((s) => s.day === replayCurrentDay);
    if (snap?.friction_state?.friction) {
      const f = snap.friction_state.friction;
      return {
        state: f.state,
        description: f.description,
        drift_percentage: f.drift_percentage,
        primary_contributor: snap.friction_state.drift?.primary_contributor || "",
      };
    }
    const entry =
      replayEntryIndex >= 0 && replayEntryIndex < data.entries.length
        ? data.entries[replayEntryIndex]
        : data.entries.find((e) => e.day === replayCurrentDay);
    return entry?.friction_state || null;
  }, [data, replayCurrentDay, replayEntryIndex]);

  // Sync currentDay from replay so understanding sections below update
  useEffect(() => {
    if (replayCurrentDay > 0) {
      setCurrentDay(replayCurrentDay);
    }
  }, [replayCurrentDay]);

  // Replay auto-play
  useEffect(() => {
    if (!replayPlaying || !data) return;
    const timer = setInterval(() => {
      setReplayStep((s) => {
        const next = s + 1;
        if (next > replayTotalSteps) {
          setReplayPlaying(false);
          return replayTotalSteps;
        }
        return next;
      });
    }, replaySpeed);
    return () => clearInterval(timer);
  }, [replayPlaying, replaySpeed, data, replayTotalSteps]);

  // Keyboard navigation
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const target = e.target;
      if (
        target instanceof HTMLInputElement ||
        target instanceof HTMLTextAreaElement ||
        target instanceof HTMLSelectElement ||
        (target instanceof HTMLElement && target.isContentEditable)
      )
        return;
      if (e.key === " ") {
        e.preventDefault();
        if (replayStep > 0 || replayPlaying) {
          setReplayPlaying((p) => !p);
        } else {
          setIsPlaying((p) => !p);
        }
      }
      if (e.key === "ArrowRight") {
        e.preventDefault();
        if (replayStep > 0) {
          setReplayStep((s) => Math.min(s + 1, replayTotalSteps));
        } else {
          setCurrentDay((d) => Math.min(d + 1, data?.total_days ?? d));
        }
      }
      if (e.key === "ArrowLeft") {
        e.preventDefault();
        if (replayStep > 0) {
          setReplayStep((s) => Math.max(s - 1, 0));
        } else {
          setCurrentDay((d) => Math.max(d - 1, 1));
        }
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [data, replayStep, replayPlaying, replayTotalSteps]);

  return (
    <div style={styles.page}>
      {/* ── Governance Demo (leads the page) ── */}
      <ThreeActDemo />

      {/* ── Collapsible Understanding Section ── */}
      <div
        style={{
          marginTop: 48,
          paddingTop: 32,
          borderTop: `1px solid ${palette.border}`,
          textAlign: "center",
        }}
      >
        <button
          onClick={() => setShowUnderstanding(!showUnderstanding)}
          style={{
            padding: "12px 28px",
            borderRadius: 8,
            border: `1px solid ${palette.border}`,
            background: showUnderstanding ? palette.cardAlt : palette.card,
            color: palette.accent,
            fontSize: 14,
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          {showUnderstanding
            ? "Hide understanding details"
            : "See how Sakhi built this understanding →"}
        </button>
      </div>

      {showUnderstanding && (
        <>
          {loading && (
            <div style={{ textAlign: "center", padding: 48, color: palette.muted, fontSize: 16 }}>
              Loading simulation data...
            </div>
          )}

          {error && !loading && (
            <div style={{ textAlign: "center", padding: 48, color: palette.chaos, fontSize: 16 }}>
              {error}
            </div>
          )}

          {data && !loading && (
            <>
              {/* 1. Header */}
              <div style={{ ...styles.header, marginTop: 24 }}>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    gap: 12,
                  }}
                >
                  <h2 style={{ ...styles.title, fontSize: 20 }}>How Understanding Deepens</h2>
                  {data.real_pipeline && (
                    <span
                      style={{
                        padding: "4px 10px",
                        background: "#e8f5e9",
                        borderRadius: 6,
                        color: palette.balanced,
                        fontWeight: 600,
                        fontSize: 11,
                        whiteSpace: "nowrap",
                      }}
                    >
                      Real Pipeline Data
                    </span>
                  )}
                </div>
                <p style={styles.subtitle}>
                  Watch Sakhi build a complete picture of someone over 2 months of journaling
                </p>
              </div>

              {/* 2. Persona Selector */}
      <PersonaSelector
        current={personaId}
        data={data}
        onChange={(id) => setPersonaId(id)}
      />

      {/* 3. Story Intro Card */}
      <StoryIntroCard persona={data.persona} />

      {/* 3.1 Conversation Replay — journal + Sakhi replies, one card at a time */}
      <ConversationReplay
        data={data}
        step={replayStep}
        totalSteps={replayTotalSteps}
        entryIndex={replayEntryIndex}
        showGovernance={replayShowGovernance}
        isPlaying={replayPlaying}
        playSpeed={replaySpeed}
        currentDay={replayCurrentDay}
        currentFriction={replayCurrentFriction}
        phaseBoundaries={replayPhaseBoundaries}
        onTogglePlay={() => {
          if (!data) return;
          if (replayStep === 0) {
            setReplayStep(1);
            setReplayPlaying(true);
          } else if (replayStep >= replayTotalSteps && !replayPlaying) {
            setReplayStep(1);
            setReplayPlaying(true);
          } else {
            setReplayPlaying((p) => !p);
          }
        }}
        onSpeedChange={setReplaySpeed}
        onStepForward={() => setReplayStep((s) => Math.min(s + 1, replayTotalSteps))}
        onStepBack={() => setReplayStep((s) => Math.max(s - 1, 0))}
      />

      <AddJournalToProfile
        personaId={personaId}
        personaName={data.persona.name}
        onAdded={async (addedDay) => {
          setLoading(true);
          try {
            await reloadSimulationData(personaId);
            if (addedDay) setCurrentDay(addedDay);
            setReplayStep(0);
            setReplayPlaying(false);
            setIsPlaying(false);
            setPauseReason(
              addedDay ? `New journal added at Day ${addedDay}` : "New journal added",
            );
          } catch (e) {
            setError(e instanceof Error ? e.message : "Failed to refresh simulation data");
          } finally {
            setLoading(false);
          }
        }}
      />

      <ContinuityArcSection
        personaName={data.persona.name}
        entries={data.entries}
        continuity={data.continuity}
      />

      {/* 3.5 Current Friction State - shows REAL computed state from simulation */}
      <CurrentFrictionState
        currentSnapshot={currentSnapshot}
        persona={data.persona}
        currentDay={currentDay}
      />

      {/* 4. Timeline Controls */}
      <TimelineControls
        currentDay={currentDay}
        totalDays={data.total_days}
        isPlaying={isPlaying}
        playSpeed={playSpeed}
        narrateMode={narrateMode}
        pauseReason={pauseReason}
        phaseBoundaries={phaseBoundaries}
        currentPhaseName={currentBoundary?.phase.name ?? null}
        checkpointDays={data.persona.checkpoints.map((c) => c.day)}
        onDayChange={(d) => {
          setCurrentDay(d);
          setPauseReason(null);
        }}
        onTogglePlay={() => {
          setIsPlaying((p) => !p);
          setPauseReason(null);
        }}
        onSpeedChange={setPlaySpeed}
        onToggleNarrate={() => setNarrateMode((n) => !n)}
      />

      {/* 5. Phase Story — narrative + journal evidence */}
      <PhaseStory
        phase={currentBoundary?.phase ?? null}
        phaseIndex={currentPhaseIndex}
        totalPhases={phaseBoundaries.length}
        boundary={currentBoundary}
        phaseEntries={phaseEntries}
        personaName={data.persona.name}
        currentDay={currentDay}
      />

      {/* 7. Journal vs Memory — KILLER FEATURE */}
      <JournalVsMemory
        entries={dayEntries}
        memory={currentMemory}
        currentDay={currentDay}
        personaName={data.persona.name}
        memoryCount={currentSnapshot?.memory_count ?? 0}
        isRealPipeline={data.real_pipeline === true}
      />

      {/* 8. Understanding Profile — radar + counters + rings */}
      <UnderstandingProfile
        snapshot={currentSnapshot}
        finalStats={finalStats}
        personaName={data.persona.name}
        radarData={radarData}
        overallDepth={overallDepth}
        entriesUpToDay={entriesUpToDay}
        totalEntries={data.total_entries}
      />

      {/* 9. Soul Evolution Chart */}
      <div style={styles.card}>
        <div
          style={{
            fontSize: 15,
            fontWeight: 600,
            color: palette.text,
            marginBottom: 4,
          }}
        >
          Soul Evolution
        </div>
        <div
          style={{
            fontSize: 12,
            color: palette.muted,
            marginBottom: 16,
          }}
        >
          How Sakhi&apos;s understanding of who this person truly is shifts over
          time
        </div>
        <ResponsiveContainer width="100%" height={280}>
          <AreaChart data={soulEvolutionData}>
            <CartesianGrid strokeDasharray="3 3" stroke={palette.border} />
            <XAxis dataKey="day" stroke={palette.muted} fontSize={11} />
            <YAxis
              stroke={palette.muted}
              fontSize={11}
              yAxisId="drift"
              domain={[0, "auto"]}
              tickFormatter={(v: number) => `${v}%`}
            />
            <YAxis
              stroke={palette.muted}
              fontSize={11}
              yAxisId="count"
              orientation="right"
              domain={[0, "auto"]}
              allowDecimals={false}
            />
            <RTooltip
              contentStyle={{
                background: palette.card,
                border: `1px solid ${palette.border}`,
                borderRadius: 8,
                fontSize: 12,
              }}
              formatter={(value: number, name: string) => [
                name === "drift" ? `${value}%` : value,
                name === "drift"
                  ? "Identity drift"
                  : name === "frictions"
                    ? "Tensions recognized"
                    : "Strengths discovered",
              ]}
              labelFormatter={(day: number) => `Day ${day}`}
            />
            {phaseBoundaries.slice(1).map((b) =>
              b.start <= currentDay ? (
                <ReferenceLine
                  key={b.start}
                  x={b.start}
                  stroke={palette.muted}
                  strokeDasharray="4 4"
                  strokeOpacity={0.4}
                  yAxisId="drift"
                />
              ) : null,
            )}
            <Area
              type="monotone"
              dataKey="drift"
              yAxisId="drift"
              stroke={palette.accent}
              fill={palette.accent}
              fillOpacity={0.15}
              strokeWidth={2}
              isAnimationActive={false}
            />
            <Line
              type="stepAfter"
              dataKey="frictions"
              yAxisId="count"
              stroke={palette.pitta}
              dot={false}
              strokeWidth={1.5}
              isAnimationActive={false}
            />
            <Line
              type="stepAfter"
              dataKey="lights"
              yAxisId="count"
              stroke={palette.nodes}
              dot={false}
              strokeWidth={1.5}
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
        <div
          style={{
            display: "flex",
            gap: 16,
            justifyContent: "center",
            marginTop: 8,
          }}
        >
          <LegendDot color={palette.accent} label="Identity drift" />
          <LegendDot color={palette.pitta} label="Tensions recognized" />
          <LegendDot color={palette.nodes} label="Strengths discovered" />
        </div>
      </div>

      {/* 10. Deep-Dive Brain Sections */}
      <CoherenceMapSection
        snapshots={data.snapshots}
        currentDay={currentDay}
        phaseBoundaries={phaseBoundaries}
      />
      <AlignmentTensionSection
        snapshots={data.snapshots}
        currentDay={currentDay}
        phaseBoundaries={phaseBoundaries}
      />
      <IdentityMomentumSection
        snapshots={data.snapshots}
        currentDay={currentDay}
        phaseBoundaries={phaseBoundaries}
      />
      <ThemeEvolutionSection
        snapshots={data.snapshots}
        currentDay={currentDay}
      />

      {/* 11. Pipeline Strip */}
      <PipelineStrip
        isRealPipeline={data.real_pipeline === true}
        userId={data.user_id}
      />

      {/* 12. Footer */}
      <div
        style={{
          textAlign: "center",
          color: palette.muted,
          fontSize: 12,
          marginTop: 24,
          paddingBottom: 16,
        }}
      >
        Simulated {data.total_days} days &middot; {data.total_entries} journal
        entries
        {data.real_pipeline && " \u00b7 Real Worker Pipeline"}
      </div>

            </>
          )}
        </>
      )}

      {/* ── Ask Sakhi — continue the conversation ── */}
      <AskSakhiSection
        personaId={personaId}
        loading={askLoading}
        error={askError}
        text={askText}
        timeOfDay={askTimeOfDay}
        lastEntry={askLastEntry}
        debug={askLastDebug}
        deepReflectionLoading={askReflectionLoading}
        deepReflectionMode={askReflectionMode}
        deepReflectionStatus={askReflectionStatus}
        deepReflectionError={askReflectionError}
        deepReflectionResult={askReflectionResult}
        onTextChange={setAskText}
        onTimeOfDayChange={setAskTimeOfDay}
        onSubmit={handleAskSakhi}
        onRunDeepReflection={handleRunAskDeepReflection}
      />
    </div>
  );
}

// ============================================================================
// Sub-Components
// ============================================================================

// ── Conversation Replay (single-card stepper) ──────────────────────────────

function frictionColor(state: string): string {
  switch (state) {
    case "balanced": return palette.balanced;
    case "chaos": return palette.chaos;
    case "intensity": return palette.intensity;
    case "stagnation": return palette.stagnation;
    default: return palette.unknown;
  }
}

function ConversationReplay({
  data,
  step,
  totalSteps,
  entryIndex,
  showGovernance,
  isPlaying,
  playSpeed,
  currentDay,
  currentFriction,
  phaseBoundaries,
  onTogglePlay,
  onSpeedChange,
  onStepForward,
  onStepBack,
}: {
  data: SimulationData;
  step: number;
  totalSteps: number;
  entryIndex: number;
  showGovernance: boolean;
  isPlaying: boolean;
  playSpeed: number;
  currentDay: number;
  currentFriction: ReplayFrictionState | null;
  phaseBoundaries: PhaseBoundary[];
  onTogglePlay: () => void;
  onSpeedChange: (speed: number) => void;
  onStepForward: () => void;
  onStepBack: () => void;
}) {
  const personaName = data.persona.name;
  const totalDays = data.total_days;
  const entry = entryIndex >= 0 && entryIndex < data.entries.length ? data.entries[entryIndex] : null;

  // Current phase
  const currentPhase = useMemo(() => {
    return phaseBoundaries.find((b) => currentDay >= b.start && currentDay <= b.end) ?? null;
  }, [currentDay, phaseBoundaries]);

  const currentPhaseIndex = useMemo(() => {
    return phaseBoundaries.findIndex((b) => currentDay >= b.start && currentDay <= b.end);
  }, [currentDay, phaseBoundaries]);

  // Governance scenario from persona data
  const govScenario = useMemo(() => {
    const pm = data.persona as Record<string, any>;
    return pm.governance_scenario as { user_text: string; proposed_action: string } | undefined;
  }, [data.persona]);

  // Progress as percentage
  const progressPct = totalSteps > 0 ? Math.round((step / totalSteps) * 100) : 0;

  // ── Not started ──
  if (step === 0) {
    return (
      <div style={{ marginTop: 24, marginBottom: 24 }}>
        <div style={{ marginBottom: 16 }}>
          <div style={{ fontSize: 15, fontWeight: 600, color: palette.text, marginBottom: 4 }}>
            30-Day Conversation
          </div>
          <div style={{ fontSize: 12, color: palette.muted }}>
            Step through {personaName}&apos;s journal entries and Sakhi&apos;s replies, one at a time
          </div>
        </div>
        <div
          style={{
            display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
            padding: "32px 16px", textAlign: "center", gap: 12,
            background: palette.card, border: `1px solid ${palette.border}`, borderRadius: 12,
          }}
        >
          <div style={{ fontSize: 14, color: palette.muted, maxWidth: 400, lineHeight: 1.6 }}>
            See how Sakhi&apos;s responses evolve as understanding deepens over 30 days.
          </div>
          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <button
              onClick={onStepForward}
              style={{
                padding: "10px 28px", borderRadius: 10, border: "none",
                background: palette.accent, color: "#fff", fontWeight: 700,
                fontSize: 14, cursor: "pointer",
              }}
            >
              Start &rarr;
            </button>
          </div>
          <div style={{ fontSize: 11, color: palette.muted, opacity: 0.6 }}>
            &larr; &rarr; arrows to step &middot; Space to auto-play
          </div>
        </div>
      </div>
    );
  }

  // ── Active replay ──
  return (
    <div style={{ marginTop: 24, marginBottom: 24 }}>
      {/* Section header */}
      <div style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 15, fontWeight: 600, color: palette.text, marginBottom: 4 }}>
          30-Day Conversation
        </div>
        <div style={{ fontSize: 12, color: palette.muted }}>
          Step through {personaName}&apos;s journal entries and Sakhi&apos;s replies
        </div>
      </div>

      {/* Controls bar */}
      <div
        style={{
          background: palette.card,
          border: `1px solid ${palette.border}`,
          borderRadius: 12,
          padding: "14px 18px",
          marginBottom: 16,
        }}
      >
        {/* Top row: day info + nav */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
          <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
            <span style={{ fontSize: 18, fontWeight: 700, color: palette.text }}>
              Day {currentDay}
            </span>
            <span style={{ fontSize: 12, color: palette.muted }}>
              of {totalDays}
            </span>
            {currentPhase && (
              <span style={{ fontSize: 12, color: palette.accent, fontWeight: 600 }}>
                &middot; {currentPhase.phase.name}
              </span>
            )}
          </div>
          <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
            <button
              onClick={onStepBack}
              disabled={step <= 0}
              style={{
                padding: "6px 12px", borderRadius: 6, border: `1px solid ${palette.border}`,
                background: palette.card, color: step <= 0 ? palette.border : palette.text,
                fontSize: 14, cursor: step <= 0 ? "default" : "pointer", fontWeight: 600,
              }}
            >
              &larr;
            </button>
            <button
              onClick={onTogglePlay}
              style={{
                padding: "6px 14px", borderRadius: 8, border: "none",
                background: isPlaying ? palette.muted : palette.accent,
                color: "#fff", fontWeight: 600, fontSize: 12, cursor: "pointer",
              }}
            >
              {isPlaying ? "\u23F8" : "\u25B6"}
            </button>
            <button
              onClick={onStepForward}
              disabled={step >= totalSteps}
              style={{
                padding: "6px 12px", borderRadius: 6, border: `1px solid ${palette.border}`,
                background: palette.card, color: step >= totalSteps ? palette.border : palette.text,
                fontSize: 14, cursor: step >= totalSteps ? "default" : "pointer", fontWeight: 600,
              }}
            >
              &rarr;
            </button>
            <select
              value={playSpeed}
              onChange={(e) => onSpeedChange(Number(e.target.value))}
              style={{
                padding: "5px 6px", borderRadius: 6, border: `1px solid ${palette.border}`,
                fontSize: 11, color: palette.text, background: palette.card, cursor: "pointer",
              }}
            >
              <option value={5000}>Slow</option>
              <option value={3000}>Normal</option>
              <option value={1500}>Fast</option>
              <option value={500}>Skim</option>
            </select>
          </div>
        </div>

        {/* Progress bar */}
        <div style={{ height: 4, borderRadius: 2, background: palette.border, overflow: "hidden" }}>
          <div
            style={{
              height: "100%", width: `${progressPct}%`,
              background: palette.accent, borderRadius: 2,
              transition: "width 0.3s ease",
            }}
          />
        </div>

        {/* Friction pill */}
        {currentFriction && (
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 8 }}>
            <span
              style={{
                padding: "2px 10px", borderRadius: 10,
                background: `${frictionColor(currentFriction.state)}18`,
                color: frictionColor(currentFriction.state),
                fontSize: 11, fontWeight: 600, textTransform: "capitalize",
              }}
            >
              {currentFriction.state}
            </span>
            <span style={{ fontSize: 11, color: palette.muted }}>
              drift: {currentFriction.drift_percentage}%
            </span>
            {currentFriction.primary_contributor && (
              <span style={{ fontSize: 11, color: palette.muted }}>
                &middot; {currentFriction.primary_contributor}
              </span>
            )}
          </div>
        )}
      </div>

      {/* ── Single card: current message ── */}
      {showGovernance ? (
        // Governance card (final step)
        data.governance_result && govScenario ? (
          <div
            style={{
              background: palette.card,
              border: `2px solid ${
                data.governance_result.requires_confirmation
                  ? palette.intensity
                  : data.governance_result.is_blocked
                    ? palette.chaos
                    : palette.balanced
              }`,
              borderRadius: 16, padding: 28,
            }}
          >
            <div
              style={{
                fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: 0.8,
                color: data.governance_result.requires_confirmation
                  ? palette.intensity
                  : data.governance_result.is_blocked
                    ? palette.chaos
                    : palette.balanced,
              }}
            >
              Constitution Gate
            </div>
            <div style={{ fontSize: 17, fontWeight: 700, color: palette.text, marginTop: 8, lineHeight: 1.4 }}>
              After 30 days of understanding {personaName}&hellip;
            </div>
            <div
              style={{
                padding: 14, background: palette.cardAlt, borderRadius: 10, margin: "14px 0",
                fontSize: 14, fontStyle: "italic", color: palette.text, lineHeight: 1.6,
                borderLeft: `3px solid ${palette.muted}`,
              }}
            >
              &ldquo;{govScenario.user_text}&rdquo;
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14 }}>
              <span
                style={{
                  padding: "5px 14px", borderRadius: 8, fontWeight: 700, fontSize: 14,
                  background: `${
                    data.governance_result.requires_confirmation ? palette.intensity
                    : data.governance_result.is_blocked ? palette.chaos
                    : palette.balanced
                  }18`,
                  color: data.governance_result.requires_confirmation ? palette.intensity
                    : data.governance_result.is_blocked ? palette.chaos
                    : palette.balanced,
                }}
              >
                {data.governance_result.requires_confirmation ? "Requires Confirmation"
                  : data.governance_result.is_blocked ? "Blocked" : "Allowed"}
              </span>
            </div>
            {data.governance_result.violations.map((v, i) => (
              <div
                key={i}
                style={{
                  padding: 12, background: `${palette.chaos}08`, borderRadius: 10,
                  borderLeft: `3px solid ${palette.chaos}`, marginBottom: 8,
                  fontSize: 13, color: palette.text, lineHeight: 1.5,
                }}
              >
                <div style={{ fontWeight: 600, marginBottom: 4 }}>{v.description}</div>
                <div style={{ fontSize: 12, color: palette.muted }}>{v.message}</div>
              </div>
            ))}
            <div style={{ fontSize: 13, color: palette.muted, marginTop: 14, lineHeight: 1.6 }}>
              Sakhi knows {personaName} well enough to protect them from their own patterns.
            </div>
          </div>
        ) : (
          <div style={{ textAlign: "center", padding: 32, color: palette.muted, fontSize: 13 }}>
            End of {totalDays}-day replay
          </div>
        )
      ) : entry ? (
        // Journal + Reply card together
        <div
          style={{
            background: palette.card,
            border: `1px solid ${palette.border}`,
            borderRadius: 16,
            padding: 24,
          }}
        >
          {/* Phase marker if this is the first day of a new phase */}
          {currentPhase && currentDay === currentPhase.start && (
            <div
              style={{
                display: "flex", alignItems: "center", gap: 8, marginBottom: 16,
                padding: "8px 12px", borderRadius: 8, background: palette.accentLight,
              }}
            >
              <span style={{ fontSize: 11, color: palette.muted, textTransform: "uppercase" }}>
                Phase {currentPhaseIndex + 1}
              </span>
              <span style={{ fontSize: 13, fontWeight: 600, color: palette.accent }}>
                {currentPhase.phase.name}
              </span>
              <span style={{ fontSize: 12, color: palette.muted, fontStyle: "italic" }}>
                &mdash; {currentPhase.phase.emotional_state}
              </span>
            </div>
          )}

          {/* Day + time label */}
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14 }}>
            <span style={{ fontSize: 12, color: palette.muted }}>
              Day {entry.day} &middot; {entry.time_of_day}
            </span>
          </div>

          {/* Journal entry */}
          <div
            style={{
              fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: 0.3,
              marginBottom: 8, color: palette.accent,
            }}
          >
            {personaName}
          </div>
          <div
            style={{
              fontSize: 14, color: palette.text, lineHeight: 1.75, whiteSpace: "pre-line",
              borderLeft: `3px solid ${palette.accent}`,
              background: "#fdf8f3",
              borderRadius: "0 12px 12px 0",
              padding: "14px 18px 14px 16px",
              marginBottom: 20,
            }}
          >
            {entry.content}
          </div>

          {/* Sakhi reply */}
          {entry.reply && (
            <>
              <div
                style={{
                  fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: 0.3,
                  marginBottom: 8, color: palette.vata,
                }}
              >
                Sakhi
              </div>
              <div
                style={{
                  fontSize: 14, color: palette.text, lineHeight: 1.75, whiteSpace: "pre-line",
                  borderLeft: `3px solid ${palette.vata}`,
                  background: "#f3f7fb",
                  borderRadius: "0 12px 12px 0",
                  padding: "14px 18px 14px 16px",
                }}
              >
                {entry.reply}
              </div>
            </>
          )}
        </div>
      ) : null}
    </div>
  );
}

function AddJournalToProfile({
  personaId,
  personaName,
  onAdded,
}: {
  personaId: string;
  personaName: string;
  onAdded: (addedDay: number | null) => Promise<void> | void;
}) {
  const [journalText, setJournalText] = useState("");
  const [timeOfDay, setTimeOfDay] = useState<"morning" | "afternoon" | "evening">("evening");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const submit = async () => {
    const content = journalText.trim();
    if (!content || saving) return;

    setSaving(true);
    setError(null);
    setSuccess(null);

    try {
      const res = await fetch("/api/demo/simulation/add-journal", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          persona_id: personaId,
          content,
          time_of_day: timeOfDay,
        }),
      });
      const payload = await res.json().catch(() => ({}));
      if (!res.ok) {
        const detail = payload?.detail || payload?.error || "Failed to add journal";
        throw new Error(String(detail));
      }

      const addedDay =
        payload?.entry && typeof payload.entry.day === "number"
          ? (payload.entry.day as number)
          : null;
      setJournalText("");
      setSuccess(
        addedDay
          ? `Added to ${personaName} as Day ${addedDay}. Replay has been updated.`
          : `Added to ${personaName}. Replay has been updated.`,
      );
      await onAdded(addedDay);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setSaving(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <div style={{ ...styles.card, marginBottom: 24, borderLeft: `4px solid ${palette.vata}` }}>
      <div style={{ fontSize: 15, fontWeight: 600, color: palette.text, marginBottom: 4 }}>
        Add Journal To This Profile
      </div>
      <div style={{ fontSize: 12, color: palette.muted, marginBottom: 12 }}>
        Runs through the same simulation pipeline (`/v2/turn` + daily workers) and becomes replayable.
      </div>

      <textarea
        value={journalText}
        onChange={(e) => setJournalText(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={`What's on ${personaName}'s mind today? (Cmd+Enter to send)`}
        rows={5}
        style={{
          width: "100%",
          border: `1px solid ${palette.border}`,
          borderRadius: 10,
          padding: "12px 14px",
          fontSize: 14,
          lineHeight: 1.6,
          color: palette.text,
          resize: "vertical",
          background: palette.bg,
          marginBottom: 12,
          boxSizing: "border-box" as const,
          fontFamily: "inherit",
          minHeight: 180,
          outline: "none",
        }}
      />

      <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
        {(["morning", "afternoon", "evening"] as const).map((tod) => (
          <button
            key={tod}
            onClick={() => setTimeOfDay(tod)}
            style={{
              flex: 1,
              padding: "6px 0",
              borderRadius: 8,
              border: `1px solid ${timeOfDay === tod ? palette.accent : palette.border}`,
              background: timeOfDay === tod ? palette.accentLight : "transparent",
              color: timeOfDay === tod ? palette.accent : palette.muted,
              fontSize: 13,
              fontWeight: timeOfDay === tod ? 600 : 400,
              cursor: "pointer",
              textTransform: "capitalize" as const,
            }}
          >
            {tod}
          </button>
        ))}
      </div>

      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 10,
        }}
      >
        <span style={{ fontSize: 12, color: palette.muted }}>
          Processes through the real Sakhi pipeline
        </span>
        <button
          onClick={submit}
          disabled={saving || journalText.trim().length === 0}
          style={{
            padding: "10px 24px",
            borderRadius: 8,
            border: "none",
            background: saving || journalText.trim().length === 0 ? palette.muted : palette.accent,
            color: "#fff",
            fontSize: 14,
            fontWeight: 600,
            cursor: saving || journalText.trim().length === 0 ? "not-allowed" : "pointer",
            opacity: saving ? 0.75 : 1,
          }}
        >
          {saving ? "Processing..." : "Send to Sakhi \u2192"}
        </button>
      </div>

      {error && (
        <div
          style={{
            marginTop: 10,
            fontSize: 12,
            color: palette.chaos,
            background: "#ffebee",
            borderRadius: 8,
            padding: "8px 10px",
          }}
        >
          {error}
        </div>
      )}

      {success && (
        <div
          style={{
            marginTop: 10,
            fontSize: 12,
            color: palette.balanced,
            background: "#e8f5e9",
            borderRadius: 8,
            padding: "8px 10px",
          }}
        >
          {success}
        </div>
      )}
    </div>
  );
}

type RelationType = "revisits" | "reinforces" | "pivots" | "reverses" | "resolves";

function formatContinuityTimestamp(timestamp: string): string {
  const value = new Date(timestamp);
  if (Number.isNaN(value.getTime())) return timestamp;
  return value.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function formatFacetLabel(facet: string): string {
  return facet.replace(/_/g, " ");
}

function formatDecisionStateLabel(value: string): string {
  return value.replace(/_/g, " ");
}

function simulationEntryKey(entry: { day: number; timestamp: string }): string {
  return `${entry.day}|${entry.timestamp}`;
}

function ContinuityArcSection({
  personaName,
  entries,
  continuity,
}: {
  personaName: string;
  entries: JournalEntry[];
  continuity?: SimulationContinuityData;
}) {
  const topics = continuity?.topics ?? [];
  const [selectedAnchor, setSelectedAnchor] = useState<string>(topics[0]?.anchor ?? "");
  const [showIncludedMoments, setShowIncludedMoments] = useState(false);
  const continuityVersionKey = continuity?.compiled_at ?? continuity?.generated_at;

  useEffect(() => {
    setSelectedAnchor(topics[0]?.anchor ?? "");
    setShowIncludedMoments(false);
  }, [personaName, continuityVersionKey, topics]);

  const selectedTopic = useMemo<CompiledContinuityTopic | null>(() => {
    if (!topics.length) return null;
    return topics.find((topic) => topic.anchor === selectedAnchor) ?? topics[0] ?? null;
  }, [selectedAnchor, topics]);

  const entryByKey = useMemo(() => {
    const index = new Map<string, JournalEntry>();
    for (const entry of entries) {
      index.set(simulationEntryKey(entry), entry);
    }
    return index;
  }, [entries]);

  const revealArcDetail = useCallback(() => {
    if (typeof window === "undefined") return;
    window.requestAnimationFrame(() => {
      document.getElementById("arc-detail")?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }, []);

  if (!selectedTopic) {
    return (
      <div style={{ ...styles.card, marginBottom: 24, borderLeft: `4px solid ${palette.accent}` }}>
        <div style={{ fontSize: 15, fontWeight: 600, color: palette.text, marginBottom: 4 }}>
          Continuity Arc
        </div>
        <div style={{ fontSize: 12, color: palette.muted }}>
          No compiled continuity topics are available for this simulation yet. Add or regenerate the
          simulation profile to compile continuity from the journal history.
        </div>
      </div>
    );
  }

  const surface = selectedTopic.surface ?? {
    mirror_allowed: true,
    detail_allowed: true,
    classification_score: selectedTopic.confidence,
    coherence_score: 1,
    blocked_reason: null as string | null,
  };

  return (
    <div style={{ ...styles.card, marginBottom: 24, borderLeft: `4px solid ${palette.accent}` }}>
      <div style={{ fontSize: 15, fontWeight: 600, color: palette.text, marginBottom: 4 }}>
        Continuity Arc
      </div>
      <div style={{ fontSize: 12, color: palette.muted, marginBottom: 12 }}>
        Topics are compiled directly from the simulation journals. Selecting a topic loads the
        precomputed continuity arc with no live tagging or preset overrides.
      </div>

      <div
        style={{
          display: "flex",
          gap: 10,
          alignItems: "center",
          flexWrap: "wrap",
          marginBottom: 12,
        }}
      >
        <select
          value={selectedTopic.anchor}
          onChange={(e) => setSelectedAnchor(e.target.value)}
          style={{
            border: `1px solid ${palette.border}`,
            borderRadius: 8,
            padding: "8px 10px",
            fontSize: 12,
            color: palette.text,
            background: palette.card,
          }}
        >
          {topics.map((topic) => (
            <option key={topic.anchor} value={topic.anchor}>
              {topic.label}
            </option>
          ))}
        </select>

        <span style={{ fontSize: 11, color: palette.muted }}>
          Auto-compiled confidence {Math.round(selectedTopic.confidence * 100)}%
        </span>
        <span style={{ fontSize: 11, color: palette.muted }}>
          Classification {Math.round(surface.classification_score * 100)}% · Coherence{" "}
          {Math.round(surface.coherence_score * 100)}%
        </span>
      </div>

      <div
        style={{
          display: "flex",
          gap: 8,
          flexWrap: "wrap",
          marginBottom: 14,
        }}
      >
        <MetricChip label="Topic" value={selectedTopic.label} />
        <MetricChip label="Span" value={`${selectedTopic.arc.span_days.toFixed(1)} Days`} />
        <MetricChip label="Entries" value={String(selectedTopic.arc.element_count)} />
        <MetricChip label="Direction" value={selectedTopic.arc.features?.direction ?? "flat"} />
        <MetricChip label="Phases" value={String(selectedTopic.arc.phase_count)} />
      </div>

      <div
        style={{
          fontSize: 11,
          color: palette.muted,
          lineHeight: 1.5,
          marginTop: -4,
          marginBottom: 12,
        }}
      >
        Direction reflects pattern consistency over time, not progress or success.
      </div>

      <div
        style={{
          fontSize: 12,
          color: palette.text,
          lineHeight: 1.6,
          marginBottom: 12,
        }}
      >
        Arc membership is inferred from the journal text and compiled into the simulation artifact.
        Sakhi can now show this topic as one unfolding storyline instead of isolated moments.
      </div>

      {!surface.mirror_allowed ? (
        <div
          style={{
            marginTop: 14,
            border: `1px solid ${palette.border}`,
            borderRadius: 14,
            background: palette.cardAlt,
            padding: 14,
          }}
        >
          <div style={{ fontSize: 13, fontWeight: 700, color: palette.text, marginBottom: 6 }}>
            Not enough continuity signal yet
          </div>
          <div style={{ fontSize: 12, color: palette.muted, lineHeight: 1.6 }}>
            This topic stays hidden until both classification confidence and arc coherence clear the
            surfacing threshold. Current status: {Math.round(surface.classification_score * 100)}%
            {" "}classification, {Math.round(surface.coherence_score * 100)}% coherence.
          </div>
        </div>
      ) : (
        <ContinuityMirrorCard
          topicLabel={selectedTopic.label}
          arc={selectedTopic.arc}
          onRevealDetail={revealArcDetail}
        />
      )}

      <div id="arc-detail" style={{ marginTop: 14 }}>
        <ContinuitySpineDiagram arc={selectedTopic.arc} entryTags={selectedTopic.entry_tags} />

        <div
          style={{
            border: `1px solid ${palette.border}`,
            borderRadius: 14,
            padding: 16,
            background: palette.card,
            marginTop: 14,
          }}
        >
          <div style={{ fontSize: 13, fontWeight: 700, color: palette.text, marginBottom: 10 }}>
            Phase Structure
          </div>
          <div style={{ display: "grid", gap: 10 }}>
            {selectedTopic.arc.phases.map((phase) => (
              <div
                key={`${selectedTopic.arc.id}-phase-${phase.index}`}
                style={{
                  border: `1px solid ${palette.border}`,
                  borderRadius: 10,
                  background: palette.cardAlt,
                  padding: 12,
                }}
              >
                <div
                  style={{
                    display: "flex",
                    gap: 8,
                    alignItems: "center",
                    flexWrap: "wrap",
                    marginBottom: 6,
                  }}
                >
                  <span style={{ fontSize: 11, fontWeight: 700, color: palette.accent }}>
                    Phase {phase.index + 1}
                  </span>
                  <span style={{ fontSize: 11, color: palette.muted }}>
                    Days {phase.start_day}-{phase.end_day}
                  </span>
                  <span style={{ fontSize: 11, color: palette.muted }}>
                    {phase.element_count} moments
                  </span>
                </div>
                <div style={{ fontSize: 11, color: palette.text, lineHeight: 1.55 }}>
                  This slice covers {formatContinuityTimestamp(phase.start_ts)} to{" "}
                  {formatContinuityTimestamp(phase.end_ts)} with {phase.element_count} compiled
                  moments.
                </div>
              </div>
            ))}
          </div>
        </div>

        <div
          style={{
            border: `1px solid ${palette.border}`,
            borderRadius: 14,
            padding: 16,
            background: palette.card,
            marginTop: 14,
          }}
        >
          <button
            type="button"
            onClick={() => setShowIncludedMoments((value) => !value)}
            aria-label={showIncludedMoments ? "Hide included moments" : "Show included moments"}
            style={{
              padding: 0,
              border: "none",
              background: "transparent",
              color: palette.text,
              fontSize: 13,
              fontWeight: 700,
              cursor: "pointer",
            }}
          >
            {showIncludedMoments ? "Hide Included Moments" : "Show Included Moments"}
          </button>

          {showIncludedMoments && (
            <div style={{ display: "grid", gap: 10, marginTop: 12 }}>
              {selectedTopic.arc.event_refs.map((event, index) => {
                const compiledTag = selectedTopic.entry_tags[
                  simulationEntryKey({ day: event.day, timestamp: event.ts })
                ];
                const fullEntry = entryByKey.get(
                  simulationEntryKey({ day: event.day, timestamp: event.ts }),
                );
                return (
                  <div
                    key={`${selectedTopic.arc.id}-event-${index}`}
                    style={{
                      border: `1px solid ${palette.border}`,
                      borderRadius: 10,
                      background: palette.cardAlt,
                      padding: 12,
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        gap: 8,
                        alignItems: "center",
                        flexWrap: "wrap",
                        marginBottom: 6,
                      }}
                    >
                      <span style={{ fontSize: 11, fontWeight: 700, color: palette.accent }}>
                        Day {event.day}
                      </span>
                      <span style={{ fontSize: 11, color: palette.muted }}>
                        {formatContinuityTimestamp(event.ts)}
                      </span>
                      <span style={{ fontSize: 10, color: palette.muted, textTransform: "capitalize" }}>
                        {event.time_of_day}
                      </span>
                      {compiledTag && (
                        <span style={{ fontSize: 10, color: palette.muted }}>
                          {Math.round(compiledTag.confidence * 100)}% confidence
                        </span>
                      )}
                    </div>

                    <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 8 }}>
                      {event.facet && (
                        <span
                          style={{
                            padding: "3px 7px",
                            borderRadius: 999,
                            background: palette.accentLight,
                            color: palette.accent,
                            fontSize: 10,
                            fontWeight: 700,
                          }}
                        >
                          {formatFacetLabel(event.facet)}
                        </span>
                      )}
                      {event.decision_state && (
                        <span
                          style={{
                            padding: "3px 7px",
                            borderRadius: 999,
                            background: "#eef3f8",
                            color: palette.stagnation,
                            fontSize: 10,
                            fontWeight: 700,
                          }}
                        >
                          {formatDecisionStateLabel(event.decision_state)}
                        </span>
                      )}
                      {event.stance && (
                        <span
                          style={{
                            padding: "3px 7px",
                            borderRadius: 999,
                            background:
                              event.stance === "toward"
                                ? "#f7efe7"
                                : event.stance === "away"
                                  ? "#eef5fb"
                                  : "#f3f1ee",
                            color:
                              event.stance === "toward"
                                ? palette.accent
                                : event.stance === "away"
                                  ? palette.stagnation
                                  : palette.muted,
                            fontSize: 10,
                            fontWeight: 700,
                          }}
                        >
                          {formatDecisionStateLabel(event.stance)}
                        </span>
                      )}
                    </div>

                    <div style={{ fontSize: 12, color: palette.text, lineHeight: 1.6 }}>
                      {fullEntry?.content || event.excerpt}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function deriveContinuityRelation(
  previous: ContinuityEventRef,
  next: ContinuityEventRef,
): RelationType {
  if (next.decision_state === "resolved") return "resolves";
  if (next.decision_state === "reversed") return "reverses";
  if (previous.stance && next.stance && previous.stance !== next.stance) return "pivots";
  if (previous.stance && next.stance && previous.stance === next.stance) return "reinforces";
  return "revisits";
}

function ContinuityMirrorCard({
  topicLabel,
  arc,
  onRevealDetail,
}: {
  topicLabel: string;
  arc: CompiledContinuityArc;
  onRevealDetail: () => void;
}) {
  const [showRecap, setShowRecap] = useState(false);
  const width = 860;
  const height = 142;
  const paddingX = 36;
  const baselineY = 62;
  const usableWidth = width - paddingX * 2;
  const phasePalette = ["#ebe0d6", "#e5ebf2", "#e2e9dc"];
  const recap = useMemo(() => makeRecap(arc), [arc]);

  const phaseRects = useMemo(() => {
    if (!arc.phases.length) {
      return [{ index: 0, x: paddingX, width: usableWidth, fill: phasePalette[0] }];
    }

    const startMs = new Date(arc.start_ts).getTime();
    const endMs = new Date(arc.end_ts).getTime();
    if (!Number.isFinite(startMs) || !Number.isFinite(endMs) || endMs <= startMs) {
      return arc.phases.map((phase, index) => {
        const x = paddingX + (index / arc.phases.length) * usableWidth;
        const widthPx =
          index === arc.phases.length - 1
            ? width - paddingX - x
            : Math.max(56, usableWidth / arc.phases.length);

        return {
          index,
          x,
          width: widthPx,
          fill: phasePalette[index % phasePalette.length],
        };
      });
    }

    const totalSpan = Math.max(endMs - startMs, 1);

    return arc.phases.map((phase, index) => {
      const phaseStartMs = new Date(phase.start_ts).getTime();
      const phaseEndMs = new Date(phase.end_ts).getTime();
      const x = paddingX + Math.max(0, ((phaseStartMs - startMs) / totalSpan) * usableWidth);
      const endX = paddingX + Math.min(1, (phaseEndMs - startMs) / totalSpan) * usableWidth;
      const widthPx =
        index === arc.phases.length - 1
          ? width - paddingX - x
          : Math.max(56, endX - x);

      return {
        index,
        x,
        width: widthPx,
        fill: phasePalette[index % phasePalette.length],
      };
    });
  }, [arc.end_ts, arc.phases, arc.start_ts, usableWidth, width]);

  const boundaryDots = phaseRects.slice(0, -1).map((phase) => phase.x + phase.width);

  return (
    <div
      style={{
        border: `1px solid ${palette.border}`,
        borderRadius: 16,
        background: palette.card,
        padding: 18,
        marginTop: 14,
      }}
    >
      <div style={{ fontSize: 17, fontWeight: 700, color: palette.text, marginBottom: 6 }}>
        {makeMirrorTitle(topicLabel, arc)}
      </div>
      <div style={{ fontSize: 12, color: palette.muted, lineHeight: 1.55, marginBottom: 12 }}>
        {makeAnchorLine(arc)}
      </div>

      <div
        style={{
          borderRadius: 18,
          background: "#f6f1ec",
          padding: "12px 14px 10px",
          overflowX: "auto",
        }}
      >
        <svg
          viewBox={`0 0 ${width} ${height}`}
          style={{ width: "100%", minWidth: 620 }}
          role="img"
          aria-label={`${topicLabel} continuity mirror`}
        >
          <rect x={0} y={0} width={width} height={height} rx={18} fill="#f3ece5" />

          {phaseRects.map((phase) => (
            <rect
              key={`${arc.id}-mirror-phase-${phase.index}`}
              x={phase.x}
              y={34}
              width={phase.width}
              height={56}
              rx={14}
              fill={phase.fill}
              opacity={0.96}
            />
          ))}

          <path
            d={`M ${paddingX} ${baselineY} C ${width * 0.28} ${baselineY - 2}, ${width * 0.72} ${baselineY + 2}, ${width - paddingX} ${baselineY}`}
            fill="none"
            stroke={palette.text}
            strokeWidth={4}
            strokeLinecap="round"
          />

          {boundaryDots.map((x, index) => (
            <circle
              key={`${arc.id}-mirror-boundary-${index}`}
              cx={x}
              cy={baselineY}
              r={5}
              fill={palette.card}
              stroke={palette.accent}
              strokeWidth={2}
            />
          ))}
        </svg>

        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            gap: 8,
            marginTop: 6,
            fontSize: 11,
            color: palette.muted,
          }}
        >
          <span>{formatContinuityTimestamp(arc.start_ts)}</span>
          <span>{formatContinuityTimestamp(arc.end_ts)}</span>
        </div>
      </div>

      <button
        type="button"
        onClick={() => setShowRecap((value) => !value)}
        aria-label={showRecap ? "Hide quick continuity recap" : "Show quick continuity recap"}
        style={{
          marginTop: 12,
          padding: 0,
          border: "none",
          background: "transparent",
          color: palette.text,
          fontSize: 12,
          fontWeight: 700,
          cursor: "pointer",
        }}
      >
        {showRecap ? "Hide quick recap" : "Quick recap"}
      </button>

      {showRecap && (
        <div
          style={{
            marginTop: 10,
            border: `1px solid ${palette.border}`,
            borderRadius: 12,
            background: palette.cardAlt,
            padding: "12px 14px",
          }}
        >
          <div style={{ display: "grid", gap: 8 }}>
            <div style={{ display: "flex", gap: 8, alignItems: "baseline", flexWrap: "wrap" }}>
              <span style={{ fontSize: 11, fontWeight: 700, color: palette.accent }}>Start</span>
              <span style={{ fontSize: 12, color: palette.text, lineHeight: 1.5 }}>{recap.start}</span>
            </div>
            <div style={{ display: "flex", gap: 8, alignItems: "baseline", flexWrap: "wrap" }}>
              <span style={{ fontSize: 11, fontWeight: 700, color: palette.accent }}>Pivots</span>
              <span style={{ fontSize: 12, color: palette.text, lineHeight: 1.5 }}>{recap.pivots}</span>
            </div>
            <div style={{ display: "flex", gap: 8, alignItems: "baseline", flexWrap: "wrap" }}>
              <span style={{ fontSize: 11, fontWeight: 700, color: palette.accent }}>Current</span>
              <span style={{ fontSize: 12, color: palette.text, lineHeight: 1.5 }}>{recap.current}</span>
            </div>
          </div>
        </div>
      )}

      <button
        type="button"
        onClick={onRevealDetail}
        aria-label="See how this continuity arc was inferred"
        style={{
          marginTop: 12,
          padding: 0,
          border: "none",
          background: "transparent",
          color: palette.accent,
          fontSize: 12,
          fontWeight: 700,
          cursor: "pointer",
        }}
      >
        See how this was inferred
      </button>
    </div>
  );
}

function ContinuitySpineDiagram({
  arc,
  entryTags,
}: {
  arc: CompiledContinuityArc;
  entryTags: Record<string, CompiledContinuityEntryTag>;
}) {
  const width = 960;
  const height = 420;
  const paddingX = 70;
  const baselineY = 240;
  const usableWidth = width - paddingX * 2;
  const totalSegments = Math.max(arc.event_refs.length - 1, 1);

  const resolveDisplayFacet = useCallback(
    (event: ContinuityEventRef): { facet: string | null; provisional: boolean } => {
      if (event.facet) {
        return { facet: event.facet, provisional: false };
      }
      const compiledTag = entryTags[simulationEntryKey({ day: event.day, timestamp: event.ts })];
      if (compiledTag?.facet_state !== "UNCERTAIN") {
        return { facet: null, provisional: false };
      }
      const trace = compiledTag.trace;
      const facetWinner = trace?.facet?.winner;
      const fallbackFacet =
        facetWinner && typeof facetWinner.key === "string" ? String(facetWinner.key).trim() : "";
      if (!fallbackFacet) {
        return { facet: null, provisional: false };
      }
      return { facet: fallbackFacet, provisional: true };
    },
    [entryTags],
  );

  const positionedEvents = arc.event_refs.map((event, index) => ({
    ...event,
    index,
    x: paddingX + (index / totalSegments) * usableWidth,
    y: baselineY,
    ...resolveDisplayFacet(event),
    highlighted: Boolean(resolveDisplayFacet(event).facet),
  }));

  const phasePalette = ["#ece2d8", "#e8edf3", "#e4eadf"];
  const phaseRects = arc.phases.map((phase, index) => {
    const firstIndex = Math.max(
      0,
      positionedEvents.findIndex((event) => event.ts === phase.start_ts),
    );
    const lastIndex = Math.max(
      firstIndex,
      positionedEvents.findIndex((event) => event.ts === phase.end_ts),
    );
    const fallbackFirst = Math.floor((index * arc.event_refs.length) / Math.max(arc.phase_count, 1));
    const fallbackLast = Math.max(
      fallbackFirst,
      Math.ceil(((index + 1) * arc.event_refs.length) / Math.max(arc.phase_count, 1)) - 1,
    );
    const startEvent = positionedEvents[firstIndex >= 0 ? firstIndex : fallbackFirst];
    const endEvent =
      positionedEvents[lastIndex >= 0 ? lastIndex : fallbackLast] ??
      positionedEvents[positionedEvents.length - 1];
    const x = (startEvent?.x ?? paddingX) - 28;
    const bandWidth = Math.max((endEvent?.x ?? x) - x + 56, 92);
    return {
      index,
      x,
      width: bandWidth,
      fill: phasePalette[index % phasePalette.length],
      start: phase.start_ts,
      end: phase.end_ts,
    };
  });

  const repeatedFacets = Array.from(
    positionedEvents.reduce((groups, event) => {
      if (!event.facet) return groups;
      const items = groups.get(event.facet) ?? [];
      items.push(event);
      groups.set(event.facet, items);
      return groups;
    }, new Map<string, typeof positionedEvents>()),
  )
    .filter(([, events]) => events.length >= 2)
    .map(([facet, events]) => ({
      facet,
      events,
      provisional: events.filter((event) => !event.provisional).length < 2,
    }))
    .slice(0, 4);

  const strandOffsets = [-72, -118, -164, 62];
  const relationStroke = (relation: RelationType) => {
    switch (relation) {
      case "reinforces":
        return { color: palette.accent, dash: "", width: 3 };
      case "reverses":
        return { color: palette.chaos, dash: "6 5", width: 3 };
      case "pivots":
        return { color: palette.stagnation, dash: "5 5", width: 2.5 };
      case "resolves":
        return { color: palette.balanced, dash: "", width: 3 };
      default:
        return { color: palette.muted, dash: "3 6", width: 2 };
    }
  };

  const renderNode = (event: PositionedContinuityEvent) => {
    const fill =
      event.stance === "toward"
        ? palette.accent
        : event.stance === "away"
          ? palette.stagnation
          : palette.card;
    const stroke =
      event.stance === "toward"
        ? palette.accent
        : event.stance === "away"
          ? palette.stagnation
          : palette.muted;

    if (event.decision_state === "reversed") {
      const points = `${event.x},${event.y - 12} ${event.x + 12},${event.y} ${event.x},${event.y + 12} ${event.x - 12},${event.y}`;
      return <polygon points={points} fill={fill} stroke={stroke} strokeWidth={4} />;
    }
    if (event.decision_state === "deferred") {
      return (
        <rect
          x={event.x - 11}
          y={event.y - 11}
          width={22}
          height={22}
          fill={fill}
          stroke={stroke}
          strokeWidth={4}
          rx={4}
        />
      );
    }
    if (event.decision_state === "resolved") {
      return (
        <rect
          x={event.x - 12}
          y={event.y - 10}
          width={24}
          height={20}
          fill={fill}
          stroke={stroke}
          strokeWidth={4}
          rx={10}
        />
      );
    }
    if (event.decision_state === "committed") {
      return <circle cx={event.x} cy={event.y} r={12} fill={fill} stroke={stroke} strokeWidth={4} />;
    }
    if (event.decision_state === "leaning_yes" || event.decision_state === "leaning_no") {
      return (
        <>
          <circle cx={event.x} cy={event.y} r={12} fill={palette.card} stroke={stroke} strokeWidth={4} />
          <path
            d={`M ${event.x - 8} ${event.y} L ${event.x + 8} ${event.y}`}
            stroke={stroke}
            strokeWidth={4}
            strokeLinecap="round"
          />
        </>
      );
    }
    return <circle cx={event.x} cy={event.y} r={12} fill={palette.card} stroke={stroke} strokeWidth={4} />;
  };

  return (
    <div
      style={{
        border: `1px solid ${palette.border}`,
        borderRadius: 16,
        background: palette.card,
        padding: 18,
      }}
    >
      <div style={{ fontSize: 18, fontWeight: 700, color: palette.text, marginBottom: 6 }}>
        Continuity Spine
      </div>
      <div style={{ fontSize: 12, color: palette.muted, marginBottom: 12, lineHeight: 1.55 }}>
        The main line is the continuous story. Repeated inferred themes appear as side strands, and
        the shaded bands keep the compiled phase structure visible.
      </div>

      <div
        style={{
          borderRadius: 18,
          background: "#f6f1ec",
          padding: 12,
          overflowX: "auto",
        }}
      >
        <svg viewBox={`0 0 ${width} ${height}`} style={{ width: "100%", minWidth: 760 }}>
          <rect x={0} y={0} width={width} height={height} rx={20} fill="#f3ece5" />

          {phaseRects.map((phase) => (
            <g key={`${arc.id}-phase-band-${phase.index}`}>
              <rect
                x={phase.x}
                y={42}
                width={phase.width}
                height={282}
                rx={18}
                fill={phase.fill}
                opacity={0.92}
              />
              <text
                x={phase.x + phase.width / 2}
                y={72}
                textAnchor="middle"
                style={{ fill: palette.muted, fontSize: 12, fontWeight: 600 }}
              >
                {`Phase ${phase.index + 1}`}
              </text>
            </g>
          ))}

          <path
            d={`M ${paddingX} ${baselineY} L ${width - paddingX} ${baselineY}`}
            stroke={palette.text}
            strokeWidth={5}
            strokeLinecap="round"
          />

          {repeatedFacets.map(({ facet, events: facetEvents, provisional }, facetIndex) => {
            const offset = strandOffsets[facetIndex % strandOffsets.length];
            const strandY = baselineY + offset;

            return (
              <g key={`${arc.id}-facet-${facet}`}>
                {facetEvents.map((event, index) => {
                  const current = event;
                  const next = index < facetEvents.length - 1 ? facetEvents[index + 1] : null;
                  const relation =
                    index < facetEvents.length - 1
                      ? deriveContinuityRelation(event, facetEvents[index + 1])
                      : null;
                  const stroke = provisional
                    ? { color: palette.muted, dash: "5 6", width: 2.5 }
                    : relation
                      ? relationStroke(relation)
                      : null;
                  return (
                    <React.Fragment key={`${arc.id}-facet-link-${facet}-${event.day}`}>
                      <line
                        x1={current.x}
                        y1={baselineY}
                        x2={current.x}
                        y2={strandY}
                        stroke={palette.border}
                        strokeWidth={2}
                      />
                      {next && stroke && (
                        <path
                          d={`M ${current.x} ${strandY} Q ${(current.x + next.x) / 2} ${strandY - 16} ${next.x} ${strandY}`}
                          fill="none"
                          stroke={stroke.color}
                          strokeWidth={stroke.width}
                          strokeDasharray={stroke.dash}
                          strokeLinecap="round"
                          opacity={provisional ? 0.9 : 1}
                        />
                      )}
                    </React.Fragment>
                  );
                })}

                {facetEvents.map((event) => {
                  return (
                    <circle
                      key={`${arc.id}-facet-node-${facet}-${event.day}`}
                      cx={event.x}
                      cy={strandY}
                      r={5}
                      fill={palette.card}
                      stroke={provisional ? palette.muted : palette.accent}
                      strokeWidth={2}
                      opacity={provisional ? 0.92 : 1}
                    />
                  );
                })}

                <text
                  x={facetEvents[0]?.x ?? paddingX}
                  y={strandY - 14}
                  textAnchor="middle"
                  style={{
                    fill: palette.muted,
                    fontSize: 10,
                    fontWeight: 600,
                    opacity: provisional ? 0.82 : 1,
                  }}
                >
                  {formatFacetLabel(facet)}
                </text>
              </g>
            );
          })}

          {positionedEvents.map((event) => (
            <g key={`${arc.id}-node-${event.day}`}>
              {renderNode(event)}
              <text
                x={event.x}
                y={event.y - 22}
                textAnchor="middle"
                style={{ fill: palette.text, fontSize: 11, fontWeight: 700 }}
              >
                {`D${event.day}`}
              </text>
            </g>
          ))}

          <text x={paddingX} y={374} textAnchor="start" style={{ fill: palette.muted, fontSize: 11 }}>
            {formatContinuityTimestamp(arc.start_ts)}
          </text>
          <text
            x={width - paddingX}
            y={374}
            textAnchor="end"
            style={{ fill: palette.muted, fontSize: 11 }}
          >
            {formatContinuityTimestamp(arc.end_ts)}
          </text>
        </svg>
      </div>
    </div>
  );
}

function MetricChip({ label, value }: { label: string; value: string }) {
  return (
    <div
      style={{
        display: "inline-flex",
        gap: 6,
        alignItems: "center",
        borderRadius: 999,
        background: palette.card,
        border: `1px solid ${palette.border}`,
        padding: "6px 10px",
      }}
    >
      <span style={{ fontSize: 10, color: palette.muted, textTransform: "uppercase" }}>
        {label}
      </span>
      <span style={{ fontSize: 12, fontWeight: 700, color: palette.text, textTransform: "capitalize" }}>
        {value}
      </span>
    </div>
  );
}

function PersonaSelector({
  current,
  data,
  onChange,
}: {
  current: string;
  data: SimulationData;
  onChange: (id: string) => void;
}) {
  const personas = [
    { id: "vidhya", label: "Vidhya", subtitle: "Overcommitment & Rediscovery", prakruti: "Pitta-dominant" },
    { id: "bigd", label: "Big D", subtitle: "Leadership & Generosity", prakruti: "Kapha-dominant" },
    { id: "diya", label: "Diya", subtitle: "Discipline & Recovery", prakruti: "Kapha-dominant" },
  ];

  return (
    <div style={{ display: "flex", gap: 12, marginBottom: 24, flexWrap: "wrap" }}>
      {personas.map((p) => {
        const isActive = current === p.id;
        return (
          <button
            key={p.id}
            onClick={() => onChange(p.id)}
            style={{
              flex: "1 1 200px",
              padding: "14px 20px",
              border: `2px solid ${isActive ? palette.accent : palette.border}`,
              borderRadius: 12,
              background: isActive ? palette.accentLight : palette.card,
              cursor: "pointer",
              textAlign: "left",
              transition: "all 0.2s",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div style={{ fontWeight: 600, fontSize: 16, color: palette.text }}>
                {p.label}
              </div>
              <span
                style={{
                  fontSize: 10,
                  padding: "2px 6px",
                  borderRadius: 4,
                  background: isActive ? palette.accent : palette.cardAlt,
                  color: isActive ? "#fff" : palette.muted,
                  fontWeight: 500,
                }}
              >
                {p.prakruti}
              </span>
            </div>
            <div style={{ fontSize: 13, color: palette.muted, marginTop: 4 }}>
              {p.subtitle}
              {isActive && (
                <span
                  style={{
                    marginLeft: 8,
                    color: palette.accent,
                    fontWeight: 500,
                  }}
                >
                  {data.total_entries} entries, {data.total_days} days
                </span>
              )}
            </div>
          </button>
        );
      })}
    </div>
  );
}

function StoryIntroCard({
  persona,
}: {
  persona: SimulationData["persona"];
}) {
  const baseline = persona.dosha_baseline;

  return (
    <div style={{ ...styles.card, marginBottom: 24 }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
        }}
      >
        <div style={{ flex: 1 }}>
          <div
            style={{ fontSize: 24, fontWeight: 700, color: palette.text }}
          >
            {persona.name}
          </div>
          <div
            style={{ fontSize: 14, color: palette.muted, marginTop: 4 }}
          >
            {persona.life_context.occupation}
          </div>
          <p
            style={{
              fontSize: 14,
              color: palette.text,
              marginTop: 12,
              lineHeight: 1.6,
              maxWidth: 520,
            }}
          >
            {persona.description}
          </p>
        </div>
        <div style={{ textAlign: "right", minWidth: 180 }}>
          <div
            style={{
              fontSize: 12,
              color: palette.muted,
              marginBottom: 8,
            }}
          >
            Onboarding Baseline
          </div>
          <DoshaBar
            label="Quick-moving"
            value={baseline.vata}
            color={palette.vata}
          />
          <DoshaBar
            label="Driven"
            value={baseline.pitta}
            color={palette.pitta}
          />
          <DoshaBar
            label="Steady"
            value={baseline.kapha}
            color={palette.kapha}
          />
        </div>
      </div>
      {/* Arc phase pills */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 0,
          marginTop: 20,
          flexWrap: "wrap",
        }}
      >
        {persona.arc.phases.map((phase, i) => (
          <React.Fragment key={phase.name}>
            <span
              style={{
                padding: "5px 12px",
                background: palette.cardAlt,
                borderRadius: 20,
                fontSize: 12,
                color: palette.text,
                fontWeight: 500,
                whiteSpace: "nowrap",
              }}
            >
              {phase.name}
            </span>
            {i < persona.arc.phases.length - 1 && (
              <span
                style={{
                  color: palette.muted,
                  fontSize: 14,
                  margin: "0 6px",
                }}
              >
                &rarr;
              </span>
            )}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}

function DoshaBar({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color: string;
}) {
  return (
    <div style={{ marginBottom: 6 }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          fontSize: 11,
          color: palette.muted,
        }}
      >
        <span>{label}</span>
        <span>{Math.round(value * 100)}%</span>
      </div>
      <div
        style={{
          background: palette.cardAlt,
          borderRadius: 4,
          height: 6,
          width: 140,
          marginTop: 2,
        }}
      >
        <div
          style={{
            background: color,
            borderRadius: 4,
            height: 6,
            width: `${value * 100}%`,
            transition: "width 0.3s",
          }}
        />
      </div>
    </div>
  );
}

// ============================================================================
// Current Friction State - Shows REAL computed friction state from simulation
// ============================================================================

function CurrentFrictionState({
  currentSnapshot,
  persona,
  currentDay,
}: {
  currentSnapshot: StateSnapshot | null;
  persona: SimulationData["persona"];
  currentDay: number;
}) {
  // Only show after day 5 (once some data is available)
  if (currentDay < 5 || !currentSnapshot) return null;

  const friction = currentSnapshot.friction_state?.friction;
  const drift = currentSnapshot.friction_state?.drift;
  const baseline = currentSnapshot.friction_state?.baseline;

  if (!friction) return null;

  // Color based on friction state
  const stateColors: Record<string, string> = {
    chaos: palette.chaos,
    intensity: palette.intensity,
    stagnation: palette.stagnation,
    balanced: palette.balanced,
  };
  const stateColor = stateColors[friction.state] || palette.muted;

  // Dosha colors
  const doshaColors: Record<string, string> = {
    vata: palette.vata,
    pitta: palette.pitta,
    kapha: palette.kapha,
  };

  return (
    <div style={{ ...styles.card, marginBottom: 24, borderLeft: `4px solid ${stateColor}` }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
        <div>
          <div style={{ fontSize: 15, fontWeight: 600, color: palette.text }}>
            Current Friction State
          </div>
          <div style={{ fontSize: 12, color: palette.muted, marginTop: 2 }}>
            Computed from {persona.name}&apos;s journal entries through Day {currentDay}
          </div>
        </div>
        <span
          style={{
            padding: "4px 10px",
            background: "#e8f5e9",
            borderRadius: 6,
            color: palette.balanced,
            fontWeight: 600,
            fontSize: 11,
          }}
        >
          Real Pipeline Data
        </span>
      </div>

      {/* Friction State Badge + Description */}
      <div style={{ marginBottom: 16 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
          <span
            style={{
              padding: "6px 14px",
              background: stateColor,
              color: "#fff",
              borderRadius: 20,
              fontWeight: 600,
              fontSize: 13,
            }}
          >
            {friction.name || friction.state.toUpperCase()}
          </span>
          {drift && (
            <span style={{ fontSize: 12, color: palette.muted }}>
              {drift.drift_percentage.toFixed(1)}% drift from baseline
              {drift.direction && ` (${drift.direction})`}
            </span>
          )}
        </div>
        {friction.description && (
          <div style={{ fontSize: 13, color: palette.text, lineHeight: 1.6 }}>
            {friction.description}
          </div>
        )}
      </div>

      {/* Recommendations Focus */}
      {friction.recommendations_focus && friction.recommendations_focus.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: palette.muted, marginBottom: 8 }}>
            Focus Areas for Balance:
          </div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            {friction.recommendations_focus.map((focus, i) => (
              <span
                key={i}
                style={{
                  padding: "4px 10px",
                  background: palette.accentLight,
                  color: palette.accent,
                  borderRadius: 12,
                  fontSize: 12,
                  fontWeight: 500,
                }}
              >
                {focus}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Dosha Drift Visualization */}
      {drift?.raw_distances && (
        <div style={{ marginBottom: 16 }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: palette.muted, marginBottom: 8 }}>
            Dosha Drift from Baseline:
          </div>
          <div style={{ display: "flex", gap: 16 }}>
            {(["vata", "pitta", "kapha"] as const).map((dosha) => {
              const distance = drift.raw_distances[dosha] || 0;
              const direction = distance > 0 ? "↑" : distance < 0 ? "↓" : "—";
              const isPrimary = drift.primary_contributor === dosha;
              return (
                <div key={dosha} style={{ flex: 1 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                    <span style={{
                      fontSize: 11,
                      color: isPrimary ? doshaColors[dosha] : palette.muted,
                      fontWeight: isPrimary ? 600 : 400,
                    }}>
                      {dosha.charAt(0).toUpperCase() + dosha.slice(1)}
                      {isPrimary && " (primary)"}
                    </span>
                    <span style={{ fontSize: 11, color: palette.muted }}>
                      {direction} {Math.abs(distance * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div style={{ height: 6, background: palette.cardAlt, borderRadius: 3 }}>
                    <div
                      style={{
                        height: "100%",
                        width: `${Math.min(Math.abs(distance) * 200, 100)}%`,
                        background: doshaColors[dosha],
                        borderRadius: 3,
                        opacity: isPrimary ? 1 : 0.5,
                      }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Constitution Reminder */}
      {baseline?.dosha_baseline && (
        <div
          style={{
            padding: "12px 16px",
            background: palette.cardAlt,
            borderRadius: 8,
            fontSize: 12,
            color: palette.muted,
          }}
        >
          <strong style={{ color: palette.text }}>{persona.name}&apos;s Constitution (Prakruti):</strong>{" "}
          {Math.round(baseline.dosha_baseline.vata * 100)}% Vata,{" "}
          {Math.round(baseline.dosha_baseline.pitta * 100)}% Pitta,{" "}
          {Math.round(baseline.dosha_baseline.kapha * 100)}% Kapha
        </div>
      )}
    </div>
  );
}

function TimelineControls({
  currentDay,
  totalDays,
  isPlaying,
  playSpeed,
  narrateMode,
  pauseReason,
  phaseBoundaries,
  currentPhaseName,
  checkpointDays,
  onDayChange,
  onTogglePlay,
  onSpeedChange,
  onToggleNarrate,
}: {
  currentDay: number;
  totalDays: number;
  isPlaying: boolean;
  playSpeed: number;
  narrateMode: boolean;
  pauseReason: string | null;
  phaseBoundaries: PhaseBoundary[];
  currentPhaseName: string | null;
  checkpointDays: number[];
  onDayChange: (day: number) => void;
  onTogglePlay: () => void;
  onSpeedChange: (speed: number) => void;
  onToggleNarrate: () => void;
}) {
  return (
    <div
      style={{
        ...styles.card,
        marginBottom: 16,
        position: "sticky",
        top: 0,
        zIndex: 50,
        boxShadow: "0 4px 12px rgba(0,0,0,0.08)",
      }}
    >
      {/* Pause reason banner */}
      {pauseReason && !isPlaying && (
        <div
          style={{
            background: palette.accentLight,
            border: `1px solid ${palette.accent}`,
            borderRadius: 8,
            padding: "10px 16px",
            marginBottom: 12,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <div>
            <div
              style={{
                fontSize: 11,
                color: palette.accent,
                fontWeight: 600,
                textTransform: "uppercase" as const,
                letterSpacing: 0.5,
              }}
            >
              Auto-paused
            </div>
            <div
              style={{
                fontSize: 15,
                fontWeight: 600,
                color: palette.text,
                marginTop: 2,
              }}
            >
              {pauseReason}
            </div>
          </div>
          <button
            onClick={onTogglePlay}
            style={{
              ...styles.playButton,
              fontSize: 13,
              padding: "6px 16px",
            }}
          >
            Continue
          </button>
        </div>
      )}

      {/* Day display + phase name */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 12,
        }}
      >
        <div>
          <span
            style={{ fontSize: 28, fontWeight: 700, color: palette.text }}
          >
            Day {currentDay}
          </span>
          {currentPhaseName && (
            <span
              style={{
                fontSize: 14,
                color: palette.accent,
                marginLeft: 12,
                fontWeight: 500,
              }}
            >
              {currentPhaseName}
            </span>
          )}
          <span
            style={{ fontSize: 14, color: palette.muted, marginLeft: 8 }}
          >
            of {totalDays}
          </span>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <button onClick={onTogglePlay} style={styles.playButton}>
            {isPlaying ? "\u23F8 Pause" : "\u25B6 Play"}
          </button>
          <select
            value={playSpeed}
            onChange={(e) => onSpeedChange(Number(e.target.value))}
            style={styles.speedSelect}
          >
            <option value={800}>Slow</option>
            <option value={400}>Normal</option>
            <option value={150}>Fast</option>
          </select>
          <button
            onClick={onToggleNarrate}
            title={
              narrateMode
                ? "Narration mode ON: pauses at key moments"
                : "Narration mode OFF: plays straight through"
            }
            style={{
              padding: "8px 12px",
              border: `1px solid ${narrateMode ? palette.accent : palette.border}`,
              borderRadius: 8,
              background: narrateMode ? palette.accentLight : palette.card,
              color: narrateMode ? palette.accent : palette.muted,
              fontSize: 13,
              cursor: "pointer",
              fontWeight: narrateMode ? 600 : 400,
            }}
          >
            {narrateMode ? "Narrate ON" : "Narrate"}
          </button>
        </div>
      </div>

      {/* Phase segments above scrubber */}
      <div
        style={{
          display: "flex",
          height: 20,
          borderRadius: 4,
          overflow: "hidden",
          marginBottom: 4,
        }}
      >
        {phaseBoundaries.map((b, i) => {
          const width = ((b.end - b.start + 1) / totalDays) * 100;
          const isActive = currentDay >= b.start && currentDay <= b.end;
          return (
            <div
              key={i}
              style={{
                width: `${width}%`,
                background: isActive
                  ? palette.accentLight
                  : palette.cardAlt,
                borderRight:
                  i < phaseBoundaries.length - 1
                    ? `1px solid ${palette.border}`
                    : "none",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 10,
                color: isActive ? palette.accent : palette.muted,
                fontWeight: isActive ? 600 : 400,
                overflow: "hidden",
                whiteSpace: "nowrap",
                cursor: "pointer",
              }}
              onClick={() => onDayChange(b.start)}
              title={b.phase.name}
            >
              {width > 12 ? b.phase.name : ""}
            </div>
          );
        })}
      </div>

      {/* Scrubber */}
      <div style={{ position: "relative" }}>
        <input
          type="range"
          min={1}
          max={totalDays}
          value={currentDay}
          onChange={(e) => onDayChange(Number(e.target.value))}
          style={{
            width: "100%",
            height: 6,
            WebkitAppearance: "none",
            appearance: "none",
            background: palette.cardAlt,
            borderRadius: 3,
            outline: "none",
            cursor: "pointer",
            accentColor: palette.accent,
          }}
        />
        {/* Checkpoint markers */}
        <div
          style={{
            position: "absolute",
            top: -6,
            left: 0,
            right: 0,
            pointerEvents: "none",
          }}
        >
          {checkpointDays.map((day) => (
            <div
              key={day}
              style={{
                position: "absolute",
                left: `${((day - 1) / (totalDays - 1)) * 100}%`,
                width: 8,
                height: 8,
                borderRadius: "50%",
                background:
                  day <= currentDay ? palette.accent : palette.border,
                transform: "translateX(-50%)",
              }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// NEW: Phase Story — narrative summary with journal evidence
// ============================================================================

function PhaseStory({
  phase,
  phaseIndex,
  totalPhases,
  boundary,
  phaseEntries,
  personaName,
  currentDay,
}: {
  phase: ArcPhase | null;
  phaseIndex: number;
  totalPhases: number;
  boundary: PhaseBoundary | null;
  phaseEntries: JournalEntry[];
  personaName: string;
  currentDay: number;
}) {
  if (!phase || !boundary) return null;

  // Pick up to 3 representative excerpts spread across the phase
  const excerpts = pickExcerpts(phaseEntries, 3);
  const daysInPhase = Math.min(currentDay, boundary.end) - boundary.start + 1;
  const daysReached = Math.max(0, daysInPhase);

  return (
    <div
      style={{
        ...styles.card,
        borderLeft: `4px solid ${palette.accent}`,
        marginBottom: 16,
      }}
    >
      {/* Phase header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
        }}
      >
        <div>
          <div
            style={{ fontSize: 12, color: palette.muted, marginBottom: 4 }}
          >
            Phase {phaseIndex + 1} of {totalPhases} &middot; Days{" "}
            {boundary.start}&ndash;{boundary.end}
          </div>
          <div
            style={{ fontSize: 20, fontWeight: 600, color: palette.text }}
          >
            {phase.name}
          </div>
          <div
            style={{
              fontSize: 15,
              color: palette.accent,
              marginTop: 4,
              fontStyle: "italic",
            }}
          >
            {phase.emotional_state}
          </div>
        </div>
        <div
          style={{
            textAlign: "right",
            fontSize: 12,
            color: palette.muted,
            minWidth: 100,
          }}
        >
          <div style={{ fontSize: 22, fontWeight: 700, color: palette.text }}>
            {phaseEntries.length}
          </div>
          <div>
            {phaseEntries.length === 1 ? "entry" : "entries"} across{" "}
            {daysReached} {daysReached === 1 ? "day" : "days"}
          </div>
        </div>
      </div>

      {/* Themes */}
      <div
        style={{
          display: "flex",
          gap: 6,
          marginTop: 12,
          flexWrap: "wrap",
        }}
      >
        {phase.themes.map((t) => (
          <span
            key={t}
            style={{
              padding: "3px 10px",
              background: palette.accentLight,
              borderRadius: 20,
              fontSize: 11,
              color: palette.accent,
              fontWeight: 500,
            }}
          >
            {t}
          </span>
        ))}
      </div>

      {/* Narrative summary */}
      <div
        style={{
          fontSize: 13,
          color: palette.text,
          lineHeight: 1.7,
          marginTop: 16,
          padding: "12px 16px",
          background: palette.cardAlt,
          borderRadius: 8,
        }}
      >
        During this phase, {personaName} was{" "}
        <span style={{ color: palette.accent, fontWeight: 500 }}>
          {phase.emotional_state}
        </span>
        .{" "}
        {phase.themes.length > 0 && (
          <>
            Recurring themes of{" "}
            <strong>
              {phase.themes.slice(0, 3).join(", ")}
              {phase.themes.length > 3 &&
                `, and ${phase.themes.length - 3} more`}
            </strong>{" "}
            surfaced throughout.{" "}
          </>
        )}
        {phase.events.length > 0 && (
          <>
            Key moments included{" "}
            {phase.events
              .map((ev) => ev.toLowerCase())
              .join(", ")}
            .
          </>
        )}
      </div>

      {/* Journal evidence excerpts */}
      {excerpts.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <div
            style={{
              fontSize: 11,
              fontWeight: 600,
              color: palette.muted,
              marginBottom: 10,
              textTransform: "uppercase" as const,
              letterSpacing: 0.5,
            }}
          >
            From {personaName}&apos;s journal
          </div>
          <div
            style={{ display: "flex", flexDirection: "column", gap: 10 }}
          >
            {excerpts.map((entry, i) => (
              <div
                key={i}
                style={{
                  padding: "10px 14px",
                  background: "#fdf8f3",
                  borderRadius: 8,
                  borderLeft: `3px solid ${palette.accent}`,
                  fontSize: 13,
                  color: palette.text,
                  lineHeight: 1.6,
                  fontStyle: "italic",
                }}
              >
                <span style={{ opacity: 0.7 }}>
                  &ldquo;
                  {entry.content.length > 200
                    ? entry.content.slice(0, 200) + "..."
                    : entry.content}
                  &rdquo;
                </span>
                <div
                  style={{
                    fontSize: 10,
                    color: palette.muted,
                    marginTop: 6,
                    fontStyle: "normal",
                  }}
                >
                  Day {entry.day} &middot; {entry.time_of_day}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/** Pick N representative excerpts spread across the entries */
function pickExcerpts(entries: JournalEntry[], count: number): JournalEntry[] {
  if (entries.length === 0) return [];
  if (entries.length <= count) return entries;
  // Spread evenly: first, middle(s), last
  const result: JournalEntry[] = [];
  for (let i = 0; i < count; i++) {
    const idx = Math.round((i / (count - 1)) * (entries.length - 1));
    result.push(entries[idx]);
  }
  return result;
}

// ============================================================================
// NEW: Journal vs Memory — Side-by-side comparison
// ============================================================================

function JournalVsMemory({
  entries,
  memory,
  currentDay,
  personaName,
  memoryCount,
  isRealPipeline,
}: {
  entries: JournalEntry[];
  memory: { content: string; created_at: string } | null;
  currentDay: number;
  personaName: string;
  memoryCount: number;
  isRealPipeline: boolean;
}) {
  if (!isRealPipeline) return null;

  const hasEntry = entries.length > 0;
  const hasMemory = memory !== null;

  if (!hasEntry && !hasMemory) {
    return (
      <div
        style={{
          ...styles.card,
          textAlign: "center",
          color: palette.muted,
        }}
      >
        <div style={{ fontSize: 14 }}>
          No journal entry on Day {currentDay}
        </div>
        <div style={{ fontSize: 12, marginTop: 4 }}>
          {memoryCount} episodic memories stored so far
        </div>
      </div>
    );
  }

  return (
    <div style={styles.card}>
      <div
        style={{
          fontSize: 15,
          fontWeight: 600,
          color: palette.text,
          marginBottom: 4,
        }}
      >
        From Journal to Understanding
      </div>
      <div
        style={{ fontSize: 12, color: palette.muted, marginBottom: 16 }}
      >
        The left shows what was written. The right shows what Sakhi
        extracted.
      </div>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 16,
        }}
      >
        {/* Left: raw journal entry */}
        <div>
          <div
            style={{
              fontSize: 11,
              fontWeight: 600,
              color: palette.muted,
              marginBottom: 8,
              textTransform: "uppercase" as const,
              letterSpacing: 0.5,
            }}
          >
            {personaName}&apos;s Words
          </div>
          {hasEntry ? (
            <div
              style={{
                padding: 16,
                background: "#fdf8f3",
                borderRadius: 8,
                borderLeft: `3px solid ${palette.accent}`,
                fontSize: 13,
                color: palette.text,
                lineHeight: 1.7,
                fontStyle: "italic",
                maxHeight: 300,
                overflow: "auto",
              }}
            >
              &ldquo;{entries[0].content}&rdquo;
              {entries.length > 1 && (
                <div
                  style={{
                    fontSize: 11,
                    color: palette.muted,
                    marginTop: 8,
                  }}
                >
                  +{entries.length - 1} more{" "}
                  {entries.length - 1 === 1 ? "entry" : "entries"} today
                </div>
              )}
            </div>
          ) : (
            <div
              style={{
                padding: 16,
                background: palette.cardAlt,
                borderRadius: 8,
                fontSize: 13,
                color: palette.muted,
              }}
            >
              No journal entry on Day {currentDay}
            </div>
          )}
        </div>

        {/* Right: episodic memory */}
        <div>
          <div
            style={{
              fontSize: 11,
              fontWeight: 600,
              color: palette.muted,
              marginBottom: 8,
              textTransform: "uppercase" as const,
              letterSpacing: 0.5,
            }}
          >
            Sakhi&apos;s Understanding
          </div>
          {hasMemory ? (
            <div
              style={{
                padding: 16,
                background: "#f3f7fb",
                borderRadius: 8,
                borderLeft: `3px solid ${palette.vata}`,
                fontSize: 13,
                color: palette.text,
                lineHeight: 1.7,
                maxHeight: 300,
                overflow: "auto",
              }}
            >
              {memory.content}
            </div>
          ) : (
            <div
              style={{
                padding: 16,
                background: palette.cardAlt,
                borderRadius: 8,
                fontSize: 13,
                color: palette.muted,
              }}
            >
              Processing...
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// NEW: Understanding Profile — Radar + Counters + Rings
// ============================================================================

function UnderstandingProfile({
  snapshot,
  finalStats,
  personaName,
  radarData,
  overallDepth,
  entriesUpToDay,
  totalEntries,
}: {
  snapshot: StateSnapshot | null;
  finalStats: { mem: number; pat: number; nodes: number; edges: number };
  personaName: string;
  radarData: Array<{ dimension: string; value: number }>;
  overallDepth: number;
  entriesUpToDay: number;
  totalEntries: number;
}) {
  const counters = [
    {
      label: "Life stories remembered",
      value: snapshot?.memory_count ?? 0,
      max: finalStats.mem,
      color: palette.memories,
    },
    {
      label: "Patterns detected",
      value: snapshot?.pattern_count ?? 0,
      max: finalStats.pat,
      color: palette.patterns,
    },
    {
      label: "Topics understood",
      value: snapshot?.provenance?.graph_nodes ?? 0,
      max: finalStats.nodes,
      color: palette.nodes,
    },
    {
      label: "Connections mapped",
      value: snapshot?.provenance?.graph_edges ?? 0,
      max: finalStats.edges,
      color: palette.edges,
    },
  ];

  return (
    <div style={{ ...styles.card, marginBottom: 16 }}>
      {/* Header with overall depth */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 20,
        }}
      >
        <div>
          <div
            style={{
              fontSize: 15,
              fontWeight: 600,
              color: palette.text,
            }}
          >
            How Well Sakhi Knows {personaName}
          </div>
          <div
            style={{ fontSize: 12, color: palette.muted, marginTop: 2 }}
          >
            Understanding builds across five dimensions over time
          </div>
        </div>
        <div style={{ textAlign: "right" }}>
          <div
            style={{
              fontSize: 36,
              fontWeight: 700,
              color: palette.accent,
              lineHeight: 1,
            }}
          >
            {overallDepth}%
          </div>
          <div
            style={{
              fontSize: 11,
              color: palette.muted,
              marginTop: 2,
            }}
          >
            understanding depth
          </div>
        </div>
      </div>

      {/* Two-column: Radar (left) + Rings & Counters (right) */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 24,
          alignItems: "center",
        }}
      >
        {/* Left: Understanding Radar */}
        <div>
          <ResponsiveContainer width="100%" height={280}>
            <RadarChart data={radarData} outerRadius="75%">
              <PolarGrid stroke={palette.border} />
              <PolarAngleAxis
                dataKey="dimension"
                tick={{
                  fill: palette.muted,
                  fontSize: 11,
                  fontWeight: 500,
                }}
              />
              <Radar
                dataKey="value"
                stroke={palette.accent}
                fill={palette.accent}
                fillOpacity={0.25}
                strokeWidth={2}
                isAnimationActive={false}
              />
            </RadarChart>
          </ResponsiveContainer>
        </div>

        {/* Right: Knowledge Rings + Reframed Counters */}
        <div>
          {/* Knowledge Depth Rings */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 24,
              marginBottom: 20,
            }}
          >
            <KnowledgeRings
              entries={entriesUpToDay}
              totalEntries={totalEntries}
              patterns={snapshot?.pattern_count ?? 0}
              maxPatterns={finalStats.pat}
              edges={snapshot?.provenance?.graph_edges ?? 0}
              maxEdges={finalStats.edges}
            />
            <div style={{ fontSize: 11, color: palette.muted }}>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                  marginBottom: 6,
                }}
              >
                <div
                  style={{
                    width: 10,
                    height: 3,
                    borderRadius: 2,
                    background: palette.muted,
                  }}
                />
                <span>Journal entries</span>
              </div>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                  marginBottom: 6,
                }}
              >
                <div
                  style={{
                    width: 10,
                    height: 3,
                    borderRadius: 2,
                    background: palette.patterns,
                  }}
                />
                <span>Patterns</span>
              </div>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                }}
              >
                <div
                  style={{
                    width: 10,
                    height: 3,
                    borderRadius: 2,
                    background: palette.edges,
                  }}
                />
                <span>Deep knowledge</span>
              </div>
            </div>
          </div>

          {/* Reframed counters */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: 10,
            }}
          >
            {counters.map((c) => {
              const pct = c.max > 0 ? (c.value / c.max) * 100 : 0;
              return (
                <div key={c.label}>
                  <div
                    style={{
                      fontSize: 22,
                      fontWeight: 700,
                      color: palette.text,
                    }}
                  >
                    {c.value.toLocaleString()}
                  </div>
                  <div
                    style={{
                      fontSize: 11,
                      color: palette.muted,
                      marginTop: 1,
                    }}
                  >
                    {c.label}
                  </div>
                  <div
                    style={{
                      background: palette.cardAlt,
                      borderRadius: 3,
                      height: 4,
                      marginTop: 6,
                      width: "100%",
                    }}
                  >
                    <div
                      style={{
                        background: c.color,
                        borderRadius: 3,
                        height: 4,
                        width: `${pct}%`,
                        transition: "width 0.3s",
                      }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// NEW: Knowledge Depth Rings (concentric SVG)
// ============================================================================

function KnowledgeRings({
  entries,
  totalEntries,
  patterns,
  maxPatterns,
  edges,
  maxEdges,
}: {
  entries: number;
  totalEntries: number;
  patterns: number;
  maxPatterns: number;
  edges: number;
  maxEdges: number;
}) {
  const rings = [
    {
      label: "Journal",
      value: entries,
      max: totalEntries,
      color: palette.muted,
      radius: 58,
    },
    {
      label: "Patterns",
      value: patterns,
      max: maxPatterns,
      color: palette.patterns,
      radius: 42,
    },
    {
      label: "Deep Knowledge",
      value: edges,
      max: maxEdges,
      color: palette.edges,
      radius: 26,
    },
  ];

  return (
    <svg
      width={136}
      height={136}
      viewBox="0 0 136 136"
      style={{ flexShrink: 0 }}
    >
      {rings.map((ring) => {
        const pct = ring.max > 0 ? ring.value / ring.max : 0;
        const circumference = 2 * Math.PI * ring.radius;
        return (
          <g key={ring.label}>
            <circle
              cx={68}
              cy={68}
              r={ring.radius}
              fill="none"
              stroke={palette.cardAlt}
              strokeWidth={10}
            />
            <circle
              cx={68}
              cy={68}
              r={ring.radius}
              fill="none"
              stroke={ring.color}
              strokeWidth={10}
              strokeDasharray={`${circumference * pct} ${circumference * (1 - pct)}`}
              strokeLinecap="round"
              transform="rotate(-90 68 68)"
              style={{ transition: "stroke-dasharray 0.4s" }}
            />
          </g>
        );
      })}
      {/* Center label */}
      <text
        x={68}
        y={64}
        textAnchor="middle"
        fill={palette.text}
        fontSize={16}
        fontWeight={700}
      >
        {Math.round(
          ((entries / Math.max(totalEntries, 1)) * 100 +
            (patterns / Math.max(maxPatterns, 1)) * 100 +
            (edges / Math.max(maxEdges, 1)) * 100) /
            3,
        )}
        %
      </text>
      <text
        x={68}
        y={80}
        textAnchor="middle"
        fill={palette.muted}
        fontSize={9}
      >
        processed
      </text>
    </svg>
  );
}

// ============================================================================
// Coherence Map — 6-dimension radar + fragmentation + score trend
// ============================================================================

function CoherenceMapSection({
  snapshots,
  currentDay,
  phaseBoundaries,
}: {
  snapshots: StateSnapshot[];
  currentDay: number;
  phaseBoundaries: PhaseBoundary[];
}) {
  const visibleSnapshots = snapshots.filter((s) => s.day <= currentDay);
  const currentSnapshot = visibleSnapshots.length > 0 ? visibleSnapshots[visibleSnapshots.length - 1] : null;
  const coherence = currentSnapshot?.brain_states?.coherence_state;
  if (!coherence) return null;

  const map = coherence.coherence_map;
  const dimensions = ["thought", "emotion", "behavior", "identity", "alignment", "narrative"];
  const dimensionLabels: Record<string, string> = {
    thought: "Thought", emotion: "Emotion", behavior: "Behavior",
    identity: "Identity", alignment: "Alignment", narrative: "Narrative",
  };

  // Radar data from coherence_map
  const radarData = dimensions.map((d) => ({
    dimension: dimensionLabels[d] || d,
    value: map ? Math.round((map[d] ?? 0) * 100) : 0,
    fullMark: 100,
  }));

  // Trend data: coherence_score + fragmentation over time
  const trendData = visibleSnapshots
    .filter((s) => s.brain_states?.coherence_state)
    .map((s) => ({
      day: s.day,
      coherence: Math.round((s.brain_states!.coherence_state!.coherence_score ?? 0) * 100),
      fragmentation: Math.round((s.brain_states!.coherence_state!.fragmentation_index ?? 0) * 100),
    }));

  return (
    <div style={{ ...styles.card, marginBottom: 16 }}>
      <div style={{ fontSize: 15, fontWeight: 600, color: palette.text, marginBottom: 4 }}>
        Coherence Map
      </div>
      <div style={{ fontSize: 12, color: palette.muted, marginBottom: 16 }}>
        How consistent is this person across 6 dimensions of self?
      </div>

      <div style={{ display: "flex", gap: 24, flexWrap: "wrap" }}>
        {/* Radar chart */}
        <div style={{ flex: 1, minWidth: 240 }}>
          <ResponsiveContainer width="100%" height={240}>
            <RadarChart data={radarData} cx="50%" cy="50%" outerRadius="75%">
              <PolarGrid stroke={palette.border} />
              <PolarAngleAxis dataKey="dimension" fontSize={11} stroke={palette.muted} />
              <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
              <Radar
                name="Coherence"
                dataKey="value"
                stroke={palette.balanced}
                fill={palette.balanced}
                fillOpacity={0.2}
                strokeWidth={2}
                isAnimationActive={false}
              />
            </RadarChart>
          </ResponsiveContainer>
          {/* Score + fragmentation badges */}
          <div style={{ display: "flex", gap: 12, justifyContent: "center", marginTop: 4 }}>
            <span style={{ fontSize: 12, fontWeight: 600, color: palette.balanced }}>
              Score: {Math.round((coherence.coherence_score ?? 0) * 100)}%
            </span>
            {coherence.fragmentation_index != null && (
              <span style={{ fontSize: 12, fontWeight: 600, color: palette.intensity }}>
                Fragmentation: {Math.round(coherence.fragmentation_index * 100)}%
              </span>
            )}
          </div>
        </div>

        {/* Trend line */}
        {trendData.length > 1 && (
          <div style={{ flex: 1, minWidth: 280 }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: palette.text, marginBottom: 8 }}>
              Coherence Over Time
            </div>
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={trendData}>
                <CartesianGrid strokeDasharray="3 3" stroke={palette.border} />
                <XAxis dataKey="day" stroke={palette.muted} fontSize={10} />
                <YAxis domain={[0, 100]} stroke={palette.muted} fontSize={10} tickFormatter={(v: number) => `${v}%`} />
                <RTooltip
                  contentStyle={{ background: palette.card, border: `1px solid ${palette.border}`, borderRadius: 8, fontSize: 11 }}
                  formatter={(v: number, name: string) => [`${v}%`, name === "coherence" ? "Coherence" : "Fragmentation"]}
                  labelFormatter={(d: number) => `Day ${d}`}
                />
                {phaseBoundaries.slice(1).map((b) =>
                  b.start <= currentDay ? (
                    <ReferenceLine key={b.start} x={b.start} stroke={palette.muted} strokeDasharray="4 4" strokeOpacity={0.4} />
                  ) : null,
                )}
                <Area type="monotone" dataKey="coherence" stroke={palette.balanced} fill={palette.balanced}
                  fillOpacity={0.15} strokeWidth={2} isAnimationActive={false} />
                <Line type="monotone" dataKey="fragmentation" stroke={palette.intensity}
                  dot={false} strokeWidth={1.5} strokeDasharray="4 4" isAnimationActive={false} />
              </AreaChart>
            </ResponsiveContainer>
            <div style={{ display: "flex", gap: 16, justifyContent: "center", marginTop: 4 }}>
              <LegendDot color={palette.balanced} label="Coherence" />
              <LegendDot color={palette.intensity} label="Fragmentation" />
            </div>
          </div>
        )}
      </div>

      {/* Summary text */}
      {coherence.summary && (
        <div style={{
          marginTop: 12, padding: 10, background: palette.cardAlt,
          borderRadius: 8, fontSize: 12, color: palette.text, lineHeight: 1.5,
        }}>
          {coherence.summary}
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Alignment & Tension — score trends + conflict zones + suggestions
// ============================================================================

function AlignmentTensionSection({
  snapshots,
  currentDay,
  phaseBoundaries,
}: {
  snapshots: StateSnapshot[];
  currentDay: number;
  phaseBoundaries: PhaseBoundary[];
}) {
  const visibleSnapshots = snapshots.filter((s) => s.day <= currentDay);
  const currentSnapshot = visibleSnapshots.length > 0 ? visibleSnapshots[visibleSnapshots.length - 1] : null;
  const alignment = currentSnapshot?.brain_states?.alignment_state;
  if (!alignment) return null;

  // Trend data
  const trendData = visibleSnapshots
    .filter((s) => s.brain_states?.alignment_state)
    .map((s) => ({
      day: s.day,
      alignment: Math.round((s.brain_states!.alignment_state!.alignment_score ?? 0) * 100),
      tension: Math.round((s.brain_states!.alignment_state!.tension_score ?? 0) * 100),
    }));

  const alignColor = palette.balanced;
  const tensionColor = palette.chaos;

  return (
    <div style={{ ...styles.card, marginBottom: 16 }}>
      <div style={{ fontSize: 15, fontWeight: 600, color: palette.text, marginBottom: 4 }}>
        Alignment & Tension
      </div>
      <div style={{ fontSize: 12, color: palette.muted, marginBottom: 16 }}>
        Are this person&apos;s actions aligned with their values and intentions?
      </div>

      {/* Score gauges */}
      <div style={{ display: "flex", gap: 24, marginBottom: 16, flexWrap: "wrap" }}>
        <ScoreRing label="Alignment" value={alignment.alignment_score ?? 0} color={alignColor} />
        <ScoreRing label="Tension" value={alignment.tension_score ?? 0} color={tensionColor} />
        {alignment.energy_profile && (
          <div style={{ display: "flex", flexDirection: "column", justifyContent: "center" }}>
            <div style={{ fontSize: 11, color: palette.muted, marginBottom: 4 }}>Energy</div>
            <span style={{
              padding: "4px 12px", borderRadius: 12, fontSize: 12, fontWeight: 600,
              background: alignment.energy_profile === "high" ? "#e0f0e0" : alignment.energy_profile === "low" ? "#fde0d0" : palette.accentLight,
              color: palette.text,
            }}>{String(alignment.energy_profile)}</span>
          </div>
        )}
        {alignment.focus_profile && (
          <div style={{ display: "flex", flexDirection: "column", justifyContent: "center" }}>
            <div style={{ fontSize: 11, color: palette.muted, marginBottom: 4 }}>Focus</div>
            <span style={{
              padding: "4px 12px", borderRadius: 12, fontSize: 12, fontWeight: 600,
              background: alignment.focus_profile === "clear" ? "#e0f0e0" : alignment.focus_profile === "overloaded" ? "#fde0d0" : palette.accentLight,
              color: palette.text,
            }}>{String(alignment.focus_profile)}</span>
          </div>
        )}
      </div>

      {/* Trend chart */}
      {trendData.length > 1 && (
        <div style={{ marginBottom: 16 }}>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={trendData}>
              <CartesianGrid strokeDasharray="3 3" stroke={palette.border} />
              <XAxis dataKey="day" stroke={palette.muted} fontSize={10} />
              <YAxis domain={[0, 100]} stroke={palette.muted} fontSize={10} tickFormatter={(v: number) => `${v}%`} />
              <RTooltip
                contentStyle={{ background: palette.card, border: `1px solid ${palette.border}`, borderRadius: 8, fontSize: 11 }}
                formatter={(v: number, name: string) => [`${v}%`, name === "alignment" ? "Alignment" : "Tension"]}
                labelFormatter={(d: number) => `Day ${d}`}
              />
              {phaseBoundaries.slice(1).map((b) =>
                b.start <= currentDay ? (
                  <ReferenceLine key={b.start} x={b.start} stroke={palette.muted} strokeDasharray="4 4" strokeOpacity={0.4} />
                ) : null,
              )}
              <Line type="monotone" dataKey="alignment" stroke={alignColor} strokeWidth={2} dot={false} isAnimationActive={false} />
              <Line type="monotone" dataKey="tension" stroke={tensionColor} strokeWidth={2} dot={false} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
          <div style={{ display: "flex", gap: 16, justifyContent: "center", marginTop: 4 }}>
            <LegendDot color={alignColor} label="Alignment" />
            <LegendDot color={tensionColor} label="Tension" />
          </div>
        </div>
      )}

      {/* Conflict zones + suggestions */}
      <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
        {alignment.conflict_zones && alignment.conflict_zones.length > 0 && (
          <div style={{ flex: 1, minWidth: 200 }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: palette.text, marginBottom: 6 }}>Conflict Zones</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
              {alignment.conflict_zones.map((zone, i) => (
                <span key={i} style={{
                  padding: "3px 10px", background: "#fde0d0", borderRadius: 12,
                  fontSize: 11, color: palette.text,
                }}>
                  {zone}
                </span>
              ))}
            </div>
          </div>
        )}
        {alignment.action_suggestions && alignment.action_suggestions.length > 0 && (
          <div style={{ flex: 1, minWidth: 200 }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: palette.text, marginBottom: 6 }}>Suggested Actions</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
              {alignment.action_suggestions.map((action, i) => (
                <span key={i} style={{
                  padding: "3px 10px", background: "#e0f0e0", borderRadius: 12,
                  fontSize: 11, color: palette.text,
                }}>
                  {action}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ============================================================================
// Identity Momentum — direction + magnitude + stability over time
// ============================================================================

function IdentityMomentumSection({
  snapshots,
  currentDay,
  phaseBoundaries,
}: {
  snapshots: StateSnapshot[];
  currentDay: number;
  phaseBoundaries: PhaseBoundary[];
}) {
  const visibleSnapshots = snapshots.filter((s) => s.day <= currentDay);
  const currentSnapshot = visibleSnapshots.length > 0 ? visibleSnapshots[visibleSnapshots.length - 1] : null;
  const momentum = currentSnapshot?.brain_states?.identity_momentum_state;
  if (!momentum) return null;

  // Trend data
  const trendData = visibleSnapshots
    .filter((s) => s.brain_states?.identity_momentum_state)
    .map((s) => {
      const m = s.brain_states!.identity_momentum_state!;
      return {
        day: s.day,
        magnitude: Math.round((m.magnitude ?? 0) * 100),
        stability: Math.round((m.stability ?? 0) * 100),
        confidence: Math.round((m.confidence ?? 0) * 100),
      };
    });

  const directionColors: Record<string, string> = {
    toward: palette.balanced,
    away: palette.chaos,
    oscillating: palette.intensity,
    unclear: palette.muted,
  };
  const directionColor = directionColors[momentum.direction] || palette.muted;
  const directionLabels: Record<string, string> = {
    toward: "Growing toward self",
    away: "Moving away from self",
    oscillating: "Searching / oscillating",
    unclear: "Direction unclear",
  };

  return (
    <div style={{ ...styles.card, marginBottom: 16, borderLeft: `4px solid ${directionColor}` }}>
      <div style={{ fontSize: 15, fontWeight: 600, color: palette.text, marginBottom: 4 }}>
        Identity Momentum
      </div>
      <div style={{ fontSize: 12, color: palette.muted, marginBottom: 16 }}>
        Is this person growing toward who they want to be?
      </div>

      {/* Direction + scores */}
      <div style={{ display: "flex", gap: 20, alignItems: "center", marginBottom: 16, flexWrap: "wrap" }}>
        <div style={{
          padding: "8px 16px", borderRadius: 12, background: `${directionColor}18`,
          border: `1px solid ${directionColor}40`,
        }}>
          <div style={{ fontSize: 11, color: palette.muted, marginBottom: 2 }}>Direction</div>
          <div style={{ fontSize: 14, fontWeight: 700, color: directionColor }}>
            {directionLabels[momentum.direction] || momentum.direction}
          </div>
        </div>
        <ScoreRing label="Magnitude" value={momentum.magnitude ?? 0} color={palette.accent} />
        <ScoreRing label="Stability" value={momentum.stability ?? 0} color={palette.vata} />
        <ScoreRing label="Confidence" value={momentum.confidence ?? 0} color={palette.balanced} />
      </div>

      {/* Trend chart */}
      {trendData.length > 1 && (
        <div style={{ marginBottom: 12 }}>
          <ResponsiveContainer width="100%" height={180}>
            <LineChart data={trendData}>
              <CartesianGrid strokeDasharray="3 3" stroke={palette.border} />
              <XAxis dataKey="day" stroke={palette.muted} fontSize={10} />
              <YAxis domain={[0, 100]} stroke={palette.muted} fontSize={10} tickFormatter={(v: number) => `${v}%`} />
              <RTooltip
                contentStyle={{ background: palette.card, border: `1px solid ${palette.border}`, borderRadius: 8, fontSize: 11 }}
                formatter={(v: number, name: string) => [`${v}%`, name.charAt(0).toUpperCase() + name.slice(1)]}
                labelFormatter={(d: number) => `Day ${d}`}
              />
              {phaseBoundaries.slice(1).map((b) =>
                b.start <= currentDay ? (
                  <ReferenceLine key={b.start} x={b.start} stroke={palette.muted} strokeDasharray="4 4" strokeOpacity={0.4} />
                ) : null,
              )}
              <Line type="monotone" dataKey="magnitude" stroke={palette.accent} strokeWidth={2} dot={false} isAnimationActive={false} />
              <Line type="monotone" dataKey="stability" stroke={palette.vata} strokeWidth={1.5} dot={false} strokeDasharray="4 4" isAnimationActive={false} />
              <Line type="monotone" dataKey="confidence" stroke={palette.balanced} strokeWidth={1.5} dot={false} strokeDasharray="2 2" isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
          <div style={{ display: "flex", gap: 16, justifyContent: "center", marginTop: 4 }}>
            <LegendDot color={palette.accent} label="Magnitude" />
            <LegendDot color={palette.vata} label="Stability" />
            <LegendDot color={palette.balanced} label="Confidence" />
          </div>
        </div>
      )}

      {/* Evidence summary */}
      {momentum.evidence_summary && (
        <div style={{
          padding: 10, background: palette.cardAlt,
          borderRadius: 8, fontSize: 12, color: palette.text, lineHeight: 1.5,
        }}>
          {momentum.evidence_summary}
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Theme Evolution — themes discovered + crystallized patterns
// ============================================================================

function ThemeEvolutionSection({
  snapshots,
  currentDay,
}: {
  snapshots: StateSnapshot[];
  currentDay: number;
}) {
  const visibleSnapshots = snapshots.filter((s) => s.day <= currentDay);
  const currentSnapshot = visibleSnapshots.length > 0 ? visibleSnapshots[visibleSnapshots.length - 1] : null;

  const themes = currentSnapshot?.themes;
  const patterns = currentSnapshot?.crystallized_patterns;
  if (!themes?.length && !patterns?.length) return null;

  // Theme bar chart data — top 8 by clarity
  const themeBarData = (themes || []).slice(0, 8).map((t) => ({
    name: t.theme.length > 18 ? t.theme.slice(0, 16) + "..." : t.theme,
    clarity: Math.round(t.clarity_score * 100),
  }));

  // Pattern breakdown by type
  const patternsByType: Record<string, CrystallizedPattern[]> = {};
  for (const p of patterns || []) {
    const type = p.pattern_type || "unknown";
    if (!patternsByType[type]) patternsByType[type] = [];
    patternsByType[type].push(p);
  }

  const trajectoryColors: Record<string, string> = {
    improving: palette.balanced,
    emerging: palette.vata,
    stable: palette.muted,
    worsening: palette.chaos,
    fading: "#c4bdb5",
  };

  // Count trends over time
  const countData = visibleSnapshots
    .filter((s) => s.themes?.length || s.crystallized_patterns?.length)
    .map((s) => ({
      day: s.day,
      themes: s.themes?.length ?? 0,
      patterns: s.crystallized_patterns?.length ?? 0,
    }));

  return (
    <div style={{ ...styles.card, marginBottom: 16 }}>
      <div style={{ fontSize: 15, fontWeight: 600, color: palette.text, marginBottom: 4 }}>
        Theme & Pattern Evolution
      </div>
      <div style={{ fontSize: 12, color: palette.muted, marginBottom: 16 }}>
        Life themes and behavioral patterns Sakhi has crystallized
      </div>

      <div style={{ display: "flex", gap: 24, flexWrap: "wrap" }}>
        {/* Theme clarity chart */}
        {themeBarData.length > 0 && (
          <div style={{ flex: 1, minWidth: 280 }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: palette.text, marginBottom: 8 }}>
              Active Themes ({themes?.length ?? 0})
            </div>
            <ResponsiveContainer width="100%" height={Math.max(themeBarData.length * 32, 120)}>
              <BarChart data={themeBarData} layout="vertical" margin={{ left: 0, right: 16 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={palette.border} horizontal={false} />
                <XAxis type="number" domain={[0, 100]} stroke={palette.muted} fontSize={10}
                  tickFormatter={(v: number) => `${v}%`} />
                <YAxis type="category" dataKey="name" width={110} stroke={palette.muted} fontSize={10} />
                <RTooltip
                  contentStyle={{ background: palette.card, border: `1px solid ${palette.border}`, borderRadius: 8, fontSize: 11 }}
                  formatter={(v: number) => [`${v}%`, "Clarity"]}
                />
                <Bar dataKey="clarity" fill={palette.accent} radius={[0, 4, 4, 0]} barSize={16}
                  isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Crystallized patterns by type */}
        {Object.keys(patternsByType).length > 0 && (
          <div style={{ flex: 1, minWidth: 260 }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: palette.text, marginBottom: 8 }}>
              Crystallized Patterns ({patterns?.length ?? 0})
            </div>
            {Object.entries(patternsByType).map(([type, items]) => (
              <div key={type} style={{ marginBottom: 10 }}>
                <div style={{ fontSize: 11, color: palette.muted, fontWeight: 500, marginBottom: 4, textTransform: "capitalize" }}>
                  {type} ({items.length})
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                  {items.slice(0, 5).map((p, i) => (
                    <span key={i} style={{
                      padding: "3px 10px",
                      background: `${trajectoryColors[p.trajectory] || palette.muted}20`,
                      border: `1px solid ${trajectoryColors[p.trajectory] || palette.muted}40`,
                      borderRadius: 12, fontSize: 10, color: palette.text,
                      display: "inline-flex", alignItems: "center", gap: 4,
                    }}>
                      <span style={{
                        width: 6, height: 6, borderRadius: 3,
                        background: trajectoryColors[p.trajectory] || palette.muted,
                      }} />
                      {p.pattern_value.length > 24 ? p.pattern_value.slice(0, 22) + "..." : p.pattern_value}
                      <span style={{ fontSize: 9, color: palette.muted }}>
                        {Math.round(p.confidence * 100)}%
                      </span>
                    </span>
                  ))}
                </div>
              </div>
            ))}
            {/* Trajectory legend */}
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 8 }}>
              {Object.entries(trajectoryColors).slice(0, 4).map(([label, color]) => (
                <LegendDot key={label} color={color} label={label} />
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Discovery trend over time */}
      {countData.length > 1 && (
        <div style={{ marginTop: 16 }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: palette.text, marginBottom: 8 }}>
            Discovery Over Time
          </div>
          <ResponsiveContainer width="100%" height={160}>
            <AreaChart data={countData}>
              <CartesianGrid strokeDasharray="3 3" stroke={palette.border} />
              <XAxis dataKey="day" stroke={palette.muted} fontSize={10} />
              <YAxis stroke={palette.muted} fontSize={10} allowDecimals={false} />
              <RTooltip
                contentStyle={{ background: palette.card, border: `1px solid ${palette.border}`, borderRadius: 8, fontSize: 11 }}
                labelFormatter={(d: number) => `Day ${d}`}
              />
              <Area type="stepAfter" dataKey="themes" stroke={palette.accent} fill={palette.accent}
                fillOpacity={0.15} strokeWidth={2} isAnimationActive={false} />
              <Area type="stepAfter" dataKey="patterns" stroke={palette.balanced} fill={palette.balanced}
                fillOpacity={0.1} strokeWidth={1.5} isAnimationActive={false} />
            </AreaChart>
          </ResponsiveContainer>
          <div style={{ display: "flex", gap: 16, justifyContent: "center", marginTop: 4 }}>
            <LegendDot color={palette.accent} label="Themes" />
            <LegendDot color={palette.balanced} label="Patterns" />
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Shared: Score Ring gauge
// ============================================================================

function ScoreRing({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div style={{ textAlign: "center" }}>
      <div style={{ position: "relative", width: 56, height: 56, margin: "0 auto 6px" }}>
        <svg width={56} height={56} viewBox="0 0 56 56">
          <circle cx={28} cy={28} r={24} fill="none" stroke={palette.border} strokeWidth={4} />
          <circle
            cx={28} cy={28} r={24}
            fill="none" stroke={color} strokeWidth={4}
            strokeDasharray={`${value * 150.8} 150.8`}
            strokeLinecap="round"
            transform="rotate(-90 28 28)"
          />
        </svg>
        <div style={{
          position: "absolute", top: "50%", left: "50%",
          transform: "translate(-50%, -50%)",
          fontSize: 13, fontWeight: 700, color: palette.text,
        }}>
          {(value * 100).toFixed(0)}
        </div>
      </div>
      <div style={{ fontSize: 11, color: palette.muted, fontWeight: 500 }}>{label}</div>
    </div>
  );
}

// ============================================================================
// Checkpoint Cards (modified: LEARNING badge for friction failures)
// ============================================================================

function CheckpointCards({
  checkpoints,
  results,
  currentDay,
  onJumpToDay,
}: {
  checkpoints: SimulationData["persona"]["checkpoints"];
  results: Record<string, CheckpointResult[]>;
  currentDay: number;
  onJumpToDay: (day: number) => void;
}) {
  return (
    <div style={{ ...styles.card, marginBottom: 16 }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          marginBottom: 12,
        }}
      >
        <div
          style={{ fontSize: 15, fontWeight: 600, color: palette.text }}
        >
          Understanding Checkpoints
        </div>
        <span style={{ fontSize: 11, color: palette.muted }}>
          Checkpoints verify understanding milestones
        </span>
      </div>
      <div
        style={{
          display: "flex",
          gap: 12,
          overflowX: "auto",
          paddingBottom: 8,
        }}
      >
        {checkpoints.map((cp) => {
          const reached = cp.day <= currentDay;
          const cpResults = results[String(cp.day)] ?? [];
          const allPassed =
            cpResults.length > 0 && cpResults.every((r) => r.passed);
          const someFailed = cpResults.some((r) => !r.passed);

          // Friction-related failures get "LEARNING" instead of red FAIL
          const isFrictionOnly =
            someFailed &&
            cpResults.every(
              (r) =>
                r.passed ||
                r.type.includes("friction") ||
                r.type.includes("dosha"),
            );

          const borderColor = !reached
            ? palette.border
            : allPassed
              ? palette.balanced
              : isFrictionOnly
                ? palette.vata
                : someFailed
                  ? palette.chaos
                  : palette.border;

          const badge = allPassed
            ? { text: "PASS", bg: "#e8f5e9", color: palette.balanced }
            : isFrictionOnly
              ? { text: "LEARNING", bg: "#e3f2fd", color: palette.vata }
              : { text: "PARTIAL", bg: "#fdecea", color: palette.chaos };

          return (
            <div
              key={cp.day}
              onClick={() => onJumpToDay(cp.day)}
              style={{
                minWidth: 200,
                padding: 16,
                border: `2px solid ${borderColor}`,
                borderRadius: 12,
                background: reached ? palette.card : palette.cardAlt,
                opacity: reached ? 1 : 0.5,
                cursor: "pointer",
                transition: "all 0.2s",
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <span style={{ fontSize: 12, color: palette.muted }}>
                  Day {cp.day}
                </span>
                {reached && (
                  <span
                    style={{
                      fontSize: 11,
                      fontWeight: 600,
                      padding: "2px 8px",
                      borderRadius: 4,
                      background: badge.bg,
                      color: badge.color,
                    }}
                  >
                    {badge.text}
                  </span>
                )}
              </div>
              <div
                style={{
                  fontSize: 14,
                  fontWeight: 600,
                  color: palette.text,
                  marginTop: 6,
                }}
              >
                {cp.name}
              </div>
              {reached && cpResults.length > 0 && (
                <div style={{ marginTop: 8 }}>
                  {cpResults.map((r, i) => {
                    const isFriction =
                      !r.passed &&
                      (r.type.includes("friction") ||
                        r.type.includes("dosha"));
                    return (
                      <div
                        key={i}
                        style={{
                          fontSize: 11,
                          color: r.passed
                            ? palette.balanced
                            : isFriction
                              ? palette.vata
                              : palette.chaos,
                          marginTop: 3,
                          display: "flex",
                          alignItems: "center",
                          gap: 4,
                        }}
                      >
                        <span>
                          {r.passed
                            ? "\u2713"
                            : isFriction
                              ? "\u25CB"
                              : "\u2717"}
                        </span>
                        <span>{r.type.replace(/_/g, " ")}</span>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ============================================================================
// NEW: Pipeline Strip (compact replacement for PipelineProof)
// ============================================================================

function PipelineStrip({
  isRealPipeline,
  userId,
}: {
  isRealPipeline: boolean;
  userId: string;
}) {
  if (!isRealPipeline) return null;

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 10,
        padding: "10px 16px",
        background: "#f7faf7",
        border: `1px solid ${palette.balanced}`,
        borderRadius: 8,
        marginBottom: 16,
        fontSize: 12,
        fontFamily: "monospace",
        color: palette.muted,
      }}
    >
      <span style={{ color: palette.balanced, fontSize: 14 }}>
        &#9679;
      </span>
      <span style={{ fontWeight: 600, color: palette.text }}>
        Verified Pipeline Data
      </span>
      <span>User: {userId.slice(0, 8)}...</span>
      <span style={{ color: palette.border }}>|</span>
      <span>
        journal &rarr; STM &rarr; episodic &rarr; patterns &rarr; graph
      </span>
    </div>
  );
}

// ============================================================================
// Shared helpers
// ============================================================================

function LegendDot({ color, label }: { color: string; label: string }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
      <div
        style={{
          width: 10,
          height: 10,
          borderRadius: "50%",
          background: color,
        }}
      />
      <span style={{ fontSize: 11, color: palette.muted }}>{label}</span>
    </div>
  );
}

// ============================================================================
// Ask Sakhi Section
// ============================================================================

const PERSONA_NAMES: Record<string, string> = {
  vidhya: "Vidhya",
  diya: "Diya",
  bigd: "Big D",
};

function AskSakhiSection({
  personaId,
  loading,
  error,
  text,
  timeOfDay,
  lastEntry,
  debug,
  deepReflectionLoading,
  deepReflectionMode,
  deepReflectionStatus,
  deepReflectionError,
  deepReflectionResult,
  onTextChange,
  onTimeOfDayChange,
  onSubmit,
  onRunDeepReflection,
}: {
  personaId: string;
  loading: boolean;
  error: string | null;
  text: string;
  timeOfDay: "morning" | "afternoon" | "evening";
  lastEntry: {
    content: string;
    reply: string;
    friction_state?: ReplayFrictionState;
    day: number;
  } | null;
  debug: TurnDebugData | null;
  deepReflectionLoading: boolean;
  deepReflectionMode: DeepReflectionRunMode | null;
  deepReflectionStatus: string | null;
  deepReflectionError: string | null;
  deepReflectionResult: ContinuityDeepReflectionResponse | null;
  onTextChange: (v: string) => void;
  onTimeOfDayChange: (v: "morning" | "afternoon" | "evening") => void;
  onSubmit: () => void;
  onRunDeepReflection: (mode: DeepReflectionRunMode) => void;
}) {
  const personaName = PERSONA_NAMES[personaId] ?? personaId;
  const continuityPack = debug?.continuity_pack || null;
  const continuityEvidence = continuityPack?.evidence || [];
  const arcCompact = continuityPack?.arc_compact || null;
  const engineDebug = debug?.conversation_engine_debug || null;
  const promptText = engineDebug?.base_prompt || engineDebug?.prompt || "";
  const reflectionBody = deepReflectionResult?.result || null;
  const reflectionLlmMeta =
    reflectionBody && reflectionBody.llm_reflection && typeof reflectionBody.llm_reflection === "object"
      ? reflectionBody.llm_reflection
      : null;
  const reflectionMode =
    String(reflectionBody?.reflection_mode || deepReflectionMode || "topic_reflection").trim() ||
    "topic_reflection";
  const reflectionModeLabel = reflectionMode === "deep_answer" ? "Deep Answer" : "Topic Reflection";
  const reflectionQueryContext =
    reflectionBody && reflectionBody.query_context && typeof reflectionBody.query_context === "object"
      ? reflectionBody.query_context
      : null;
  const reflectionActiveQuery = String(reflectionQueryContext?.active_query || "").trim();
  const reflectionQuerySource = String(reflectionQueryContext?.active_query_source || "").trim();
  const reflectionChatSource = String(reflectionBody?.chat_response_source || "deterministic").trim();
  const reflectionChatResponseFromPayload =
    reflectionBody && typeof reflectionBody.chat_response === "string"
      ? String(reflectionBody.chat_response).trim()
      : "";
  const reflectionOpenQuestion =
    reflectionBody && Array.isArray(reflectionBody.open_questions)
      ? String(reflectionBody.open_questions[0] || "").trim()
      : "";
  const reflectionPivot =
    reflectionBody && Array.isArray(reflectionBody.key_pivots)
      ? String(reflectionBody.key_pivots[0] || "").trim()
      : "";
  const reflectionRecurring =
    reflectionBody && Array.isArray(reflectionBody.recurring_tensions)
      ? String(reflectionBody.recurring_tensions[0] || "").trim()
      : "";
  const reflectionChatResponse =
    reflectionChatResponseFromPayload ||
    [
      reflectionBody?.origin_story ? `I can see where this started: ${reflectionBody.origin_story}` : "",
      reflectionPivot ? `A key pivot was: ${reflectionPivot}` : "",
      reflectionBody?.current_stage ? `Right now this thread feels like: ${reflectionBody.current_stage}` : "",
      reflectionOpenQuestion ? `One question to hold: ${reflectionOpenQuestion}` : "",
    ]
      .filter(Boolean)
      .join(" ");
  const deepReflectionTopicKey = String(continuityPack?.topic_key || "").trim();
  const canRunDeepReflection = deepReflectionTopicKey.length > 0;
  const canRunDeepAnswer = canRunDeepReflection && Boolean(String(lastEntry?.content || "").trim());
  const deepReflectionDisabledReason = canRunDeepReflection
    ? ""
    : "No continuity topic was selected for this turn yet. Send a follow-up tied to a recurring thread (sakhi, family, career) and try again.";
  const deepAnswerDisabledReason = canRunDeepAnswer
    ? ""
    : "Deep Answer needs the latest user query in this turn.";

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      onSubmit();
    }
  };

  return (
    <div
      style={{
        marginTop: 48,
        paddingTop: 32,
        borderTop: `1px solid ${palette.border}`,
      }}
    >
      <div style={{ textAlign: "center", marginBottom: 24 }}>
        <h2 style={{ fontSize: 20, fontWeight: 700, color: palette.text, margin: 0 }}>
          Continue the Conversation
        </h2>
        <p style={{ fontSize: 14, color: palette.muted, marginTop: 6, marginBottom: 0 }}>
          Add a new journal entry as {personaName} and watch Sakhi respond through the real
          pipeline.
        </p>
      </div>

      <div
        style={{
          maxWidth: 640,
          margin: "0 auto",
          background: palette.card,
          border: `1px solid ${palette.border}`,
          borderRadius: 14,
          padding: 24,
        }}
      >
        {/* Time of day selector */}
        <div style={{ display: "flex", gap: 8, marginBottom: 14 }}>
          {(["morning", "afternoon", "evening"] as const).map((tod) => (
            <button
              key={tod}
              onClick={() => onTimeOfDayChange(tod)}
              style={{
                flex: 1,
                padding: "6px 0",
                borderRadius: 8,
                border: `1px solid ${timeOfDay === tod ? palette.accent : palette.border}`,
                background: timeOfDay === tod ? palette.accentLight : "transparent",
                color: timeOfDay === tod ? palette.accent : palette.muted,
                fontSize: 13,
                fontWeight: timeOfDay === tod ? 600 : 400,
                cursor: "pointer",
                textTransform: "capitalize" as const,
              }}
            >
              {tod}
            </button>
          ))}
        </div>

        {/* Textarea */}
        <textarea
          value={text}
          onChange={(e) => onTextChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={`What's on ${personaName}'s mind today? (Cmd+Enter to send)`}
          rows={5}
          style={{
            width: "100%",
            padding: "12px 14px",
            borderRadius: 10,
            border: `1px solid ${palette.border}`,
            fontSize: 14,
            lineHeight: 1.6,
            color: palette.text,
            background: palette.bg,
            resize: "vertical" as const,
            fontFamily: "inherit",
            boxSizing: "border-box" as const,
            outline: "none",
          }}
        />

        {/* Submit row */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginTop: 12,
          }}
        >
          <span style={{ fontSize: 12, color: palette.muted }}>
            Processes through the real Sakhi pipeline
          </span>
          <button
            onClick={onSubmit}
            disabled={!text.trim() || loading}
            style={{
              padding: "10px 24px",
              background: !text.trim() || loading ? palette.muted : palette.accent,
              color: "#fff",
              border: "none",
              borderRadius: 8,
              fontSize: 14,
              fontWeight: 600,
              cursor: !text.trim() || loading ? "not-allowed" : "pointer",
              opacity: loading ? 0.75 : 1,
            }}
          >
            {loading ? "Processing..." : "Send to Sakhi \u2192"}
          </button>
        </div>

        {error && (
          <div
            style={{
              marginTop: 12,
              padding: "10px 14px",
              background: "#fff5f5",
              border: `1px solid ${palette.chaos}44`,
              borderRadius: 8,
              color: palette.chaos,
              fontSize: 13,
            }}
          >
            {error}
          </div>
        )}
      </div>

      {/* Sakhi reply */}
      {lastEntry && (
        <div
          style={{
            maxWidth: 640,
            margin: "16px auto 0",
            background: palette.cardAlt,
            border: `1px solid ${palette.border}`,
            borderRadius: 14,
            padding: 24,
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              marginBottom: 14,
            }}
          >
            <span
              style={{
                fontSize: 11,
                fontWeight: 700,
                color: palette.muted,
                textTransform: "uppercase" as const,
                letterSpacing: 0.5,
              }}
            >
              Day {lastEntry.day}
            </span>
            {lastEntry.friction_state && (
              <span
                style={{
                  padding: "2px 10px",
                  borderRadius: 10,
                  background: frictionColor(lastEntry.friction_state.state) + "22",
                  color: frictionColor(lastEntry.friction_state.state),
                  fontSize: 11,
                  fontWeight: 600,
                }}
              >
                {lastEntry.friction_state.state}
              </span>
            )}
          </div>

          {/* Journal echo */}
          <div
            style={{
              padding: "10px 14px",
              background: palette.card,
              borderRadius: 8,
              fontSize: 13,
              color: palette.muted,
              fontStyle: "italic",
              lineHeight: 1.6,
              marginBottom: 14,
              borderLeft: `3px solid ${palette.border}`,
            }}
          >
            {lastEntry.content}
          </div>

          {/* Sakhi reply */}
          {lastEntry.reply && (
            <div>
              <div
                style={{
                  fontSize: 11,
                  fontWeight: 600,
                  color: palette.accent,
                  marginBottom: 6,
                  textTransform: "uppercase" as const,
                  letterSpacing: 0.5,
                }}
              >
                Sakhi
              </div>
              <div style={{ fontSize: 14, color: palette.text, lineHeight: 1.75 }}>
                {lastEntry.reply}
              </div>
            </div>
          )}

          {(continuityPack || promptText || debug) && (
            <details
              style={{
                marginTop: 16,
                border: `1px solid ${palette.border}`,
                borderRadius: 10,
                background: palette.card,
                padding: "10px 12px",
              }}
            >
              <summary
                style={{
                  cursor: "pointer",
                  fontSize: 12,
                  fontWeight: 700,
                  color: palette.accent,
                  textTransform: "uppercase",
                  letterSpacing: 0.4,
                }}
              >
                Turn Debug (LLM Input)
              </summary>

              <div style={{ marginTop: 12, fontSize: 12, color: palette.text }}>
                {continuityPack && (
                  <>
                    <div style={{ marginBottom: 8 }}>
                      <strong>Continuity Topic:</strong>{" "}
                      {continuityPack.topic_label || continuityPack.topic_key || "unknown"}
                    </div>
                    <div style={{ marginBottom: 8 }}>
                      <strong>Evidence Count:</strong> {continuityEvidence.length}
                    </div>
                    {arcCompact && (
                      <div style={{ marginBottom: 8, lineHeight: 1.6 }}>
                        <div>
                          <strong>Start:</strong> {arcCompact.start_signal || "n/a"}
                        </div>
                        <div>
                          <strong>Pivots:</strong> {arcCompact.pivots_signal || "n/a"}
                        </div>
                        <div>
                          <strong>Current:</strong> {arcCompact.current_signal || "n/a"}
                        </div>
                      </div>
                    )}
                    {continuityEvidence.length > 0 && (
                      <div style={{ marginBottom: 10 }}>
                        <div style={{ fontWeight: 600, marginBottom: 4 }}>Evidence passed:</div>
                        <div
                          style={{
                            maxHeight: 160,
                            overflowY: "auto",
                            border: `1px solid ${palette.border}`,
                            borderRadius: 8,
                            padding: "8px 10px",
                            background: palette.bg,
                          }}
                        >
                          {continuityEvidence.map((item, idx) => (
                            <div key={`${item.source_ref || "ref"}-${idx}`} style={{ marginBottom: 8 }}>
                              <div style={{ color: palette.muted, fontSize: 11 }}>
                                {item.ts ? item.ts.slice(0, 19) : "no-ts"} · {item.source_ref || "unknown-source"}
                              </div>
                              <div style={{ lineHeight: 1.45 }}>{item.snippet || "(empty snippet)"}</div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    <div
                      style={{
                        border: `1px solid ${palette.border}`,
                        borderRadius: 8,
                        padding: "10px 12px",
                        background: palette.cardAlt,
                        marginBottom: 8,
                      }}
                    >
                      <div
                        style={{
                          display: "flex",
                          alignItems: "flex-start",
                          justifyContent: "space-between",
                          gap: 12,
                          flexWrap: "wrap",
                        }}
                      >
                        <div style={{ fontSize: 12, fontWeight: 600, lineHeight: 1.5 }}>
                          Deep Reflection Test
                          <div style={{ fontSize: 11, fontWeight: 400, color: palette.muted }}>
                            Deep Answer = current query + full history, Topic Reflection = whole-story arc without a required query.
                          </div>
                        </div>
                        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                          <button
                            type="button"
                            onClick={() => onRunDeepReflection("deep_answer")}
                            disabled={deepReflectionLoading || !canRunDeepAnswer}
                            style={{
                              padding: "6px 12px",
                              borderRadius: 8,
                              border: "none",
                              background:
                                deepReflectionLoading || !canRunDeepAnswer
                                  ? palette.muted
                                  : palette.accent,
                              color: "#fff",
                              fontSize: 12,
                              fontWeight: 600,
                              cursor:
                                deepReflectionLoading || !canRunDeepAnswer
                                  ? "not-allowed"
                                  : "pointer",
                              opacity: deepReflectionLoading || !canRunDeepAnswer ? 0.8 : 1,
                            }}
                          >
                            {deepReflectionLoading && deepReflectionMode === "deep_answer"
                              ? "Running..."
                              : "Run Deep Answer"}
                          </button>
                          <button
                            type="button"
                            onClick={() => onRunDeepReflection("topic_reflection")}
                            disabled={deepReflectionLoading || !canRunDeepReflection}
                            style={{
                              padding: "6px 12px",
                              borderRadius: 8,
                              border: "none",
                              background:
                                deepReflectionLoading || !canRunDeepReflection
                                  ? palette.muted
                                  : palette.accent,
                              color: "#fff",
                              fontSize: 12,
                              fontWeight: 600,
                              cursor:
                                deepReflectionLoading || !canRunDeepReflection
                                  ? "not-allowed"
                                  : "pointer",
                              opacity: deepReflectionLoading || !canRunDeepReflection ? 0.8 : 1,
                            }}
                          >
                            {deepReflectionLoading && deepReflectionMode === "topic_reflection"
                              ? "Running..."
                              : "Run Topic Reflection"}
                          </button>
                        </div>
                      </div>

                      {!canRunDeepReflection && (
                        <div style={{ fontSize: 11, color: palette.muted, marginTop: 8 }}>
                          {deepReflectionDisabledReason}
                        </div>
                      )}
                      {!deepReflectionLoading && canRunDeepReflection && !canRunDeepAnswer && (
                        <div style={{ fontSize: 11, color: palette.muted, marginTop: 8 }}>
                          {deepAnswerDisabledReason}
                        </div>
                      )}

                      {deepReflectionStatus && (
                        <div style={{ fontSize: 11, color: palette.muted, marginTop: 8 }}>
                          Status{deepReflectionMode ? ` (${deepReflectionMode === "deep_answer" ? "deep_answer" : "topic_reflection"})` : ""}: {deepReflectionStatus}
                        </div>
                      )}

                      {deepReflectionError && (
                        <div
                          style={{
                            fontSize: 12,
                            color: palette.chaos,
                            marginTop: 8,
                          }}
                        >
                          {deepReflectionError}
                        </div>
                      )}

                      {reflectionBody && (
                        <div style={{ marginTop: 8, fontSize: 12, lineHeight: 1.6 }}>
                          {reflectionChatResponse && (
                            <div
                              style={{
                                border: `1px solid ${palette.border}`,
                                borderRadius: 8,
                                background: palette.card,
                                padding: "10px 12px",
                                marginBottom: 8,
                              }}
                            >
                              <div
                                style={{
                                  fontSize: 11,
                                  fontWeight: 700,
                                  color: palette.accent,
                                  textTransform: "uppercase",
                                  letterSpacing: 0.4,
                                  marginBottom: 6,
                                }}
                              >
                                Sakhi ({reflectionModeLabel})
                              </div>
                              <div
                                style={{
                                  fontSize: 10,
                                  color: palette.muted,
                                  marginBottom: 6,
                                  textTransform: "uppercase",
                                  letterSpacing: 0.35,
                                }}
                              >
                                Source: {reflectionChatSource}
                                {reflectionLlmMeta?.model ? ` · ${String(reflectionLlmMeta.model)}` : ""}
                              </div>
                              {reflectionActiveQuery && (
                                <div style={{ fontSize: 11, color: palette.muted, marginBottom: 6 }}>
                                  Query ({reflectionQuerySource || "unknown"}): {reflectionActiveQuery}
                                </div>
                              )}
                              <div style={{ fontSize: 12, color: palette.text, lineHeight: 1.6 }}>
                                {reflectionChatResponse}
                              </div>
                            </div>
                          )}
                          {reflectionLlmMeta?.error && (
                            <div style={{ color: palette.chaos, fontSize: 11, marginBottom: 6 }}>
                              LLM synthesis error: {String(reflectionLlmMeta.error)}
                            </div>
                          )}
                          {reflectionBody.origin_story && (
                            <div>
                              <strong>Origin:</strong> {reflectionBody.origin_story}
                            </div>
                          )}
                          {reflectionPivot && (
                            <div>
                              <strong>Pivot:</strong> {reflectionPivot}
                            </div>
                          )}
                          {reflectionBody.current_stage && (
                            <div>
                              <strong>Current:</strong> {reflectionBody.current_stage}
                            </div>
                          )}
                          {reflectionRecurring && (
                            <div>
                              <strong>Recurring:</strong> {reflectionRecurring}
                            </div>
                          )}

                          <details style={{ marginTop: 8 }}>
                            <summary
                              style={{
                                cursor: "pointer",
                                fontSize: 11,
                                fontWeight: 600,
                                color: palette.text,
                              }}
                            >
                              Deep reflection raw payload
                            </summary>
                            <pre
                              style={{
                                marginTop: 8,
                                whiteSpace: "pre-wrap",
                                wordBreak: "break-word",
                                maxHeight: 220,
                                overflowY: "auto",
                                border: `1px solid ${palette.border}`,
                                borderRadius: 8,
                                padding: "8px 10px",
                                background: palette.bg,
                                color: palette.text,
                                fontSize: 11,
                                lineHeight: 1.5,
                              }}
                            >
                              {JSON.stringify(reflectionBody, null, 2)}
                            </pre>
                          </details>
                        </div>
                      )}
                    </div>
                  </>
                )}

                {promptText && (
                  <details style={{ marginTop: 8 }}>
                    <summary
                      style={{
                        cursor: "pointer",
                        fontSize: 12,
                        fontWeight: 600,
                        color: palette.text,
                      }}
                    >
                      Prompt sent to LLM
                    </summary>
                    <pre
                      style={{
                        marginTop: 8,
                        whiteSpace: "pre-wrap",
                        wordBreak: "break-word",
                        maxHeight: 320,
                        overflowY: "auto",
                        border: `1px solid ${palette.border}`,
                        borderRadius: 8,
                        padding: "10px 12px",
                        background: palette.bg,
                        color: palette.text,
                        fontSize: 11,
                        lineHeight: 1.55,
                      }}
                    >
                      {promptText}
                    </pre>
                  </details>
                )}
              </div>
            </details>
          )}
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Styles
// ============================================================================

const styles: Record<string, React.CSSProperties> = {
  page: {
    maxWidth: 960,
    margin: "0 auto",
    padding: "32px 24px",
    background: palette.bg,
    minHeight: "100vh",
    fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
  },
  header: {
    textAlign: "center" as const,
    marginBottom: 32,
  },
  title: {
    fontSize: 28,
    fontWeight: 700,
    color: palette.text,
    margin: 0,
  },
  subtitle: {
    fontSize: 15,
    color: palette.muted,
    marginTop: 8,
  },
  card: {
    background: palette.card,
    border: `1px solid ${palette.border}`,
    borderRadius: 12,
    padding: 20,
    marginBottom: 16,
  },
  row: {
    display: "flex",
    gap: 16,
    marginBottom: 16,
  },
  playButton: {
    padding: "8px 20px",
    background: palette.accent,
    color: "#fff",
    border: "none",
    borderRadius: 8,
    cursor: "pointer",
    fontWeight: 600,
    fontSize: 14,
  },
  speedSelect: {
    padding: "8px 12px",
    border: `1px solid ${palette.border}`,
    borderRadius: 8,
    background: palette.card,
    color: palette.text,
    fontSize: 13,
    cursor: "pointer",
  },
};
