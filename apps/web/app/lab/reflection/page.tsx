"use client";

import type { CSSProperties } from "react";
import { useEffect, useMemo, useState } from "react";

type WorkerSummary = {
  worker: string;
  inputs?: string[];
  writes?: Record<string, unknown> | null;
  signals?: Record<string, unknown> | null;
  evidence?: string[];
  notes?: string;
  confidence?: number | string | null;
  previous_state?: string | null;
  new_state?: string | null;
};

type WorkerRunState = {
  status: "idle" | "queued" | "running" | "completed" | "error";
  summary?: WorkerSummary;
  raw?: any;
  error?: string;
  startedAt?: string;
  finishedAt?: string;
  mode?: "live-turn" | "manual" | "results";
  sessionId?: string;
};

type TimelineEvent = {
  id: string;
  timestamp: string;
  label: string;
  detail?: string;
  tone?: "info" | "success" | "warning" | "error";
};

type LiveTurnState = {
  status: "idle" | "running" | "done" | "error";
  turnId?: string;
  jobIds?: string[];
  response?: any;
  raw?: any;
  llmDebug?: any;
  error?: string;
};

type ManualRunState = {
  status: "idle" | "running" | "done" | "error";
  raw?: any;
  error?: string;
};

type WorkerConfig = {
  key: string;
  label: string;
  description: string;
  readOnly?: boolean;
  optInOnly?: boolean;
};

const palette = {
  // Softer, airy palette inspired by pickle.com/os
  bg: "#f6f4f0",
  card: "#ffffff",
  border: "#dcd8d0",
  text: "#1f2a33",
  muted: "#6f7b83",
  accent: "#1f8a70",
  accent2: "#d6a34f",
  danger: "#e06464",
  caution: "#d8a24f",
  surface: "#eef1f4",
};

const cardStyle: CSSProperties = {
  background: palette.card,
  border: `1px solid ${palette.border}`,
  borderRadius: 14,
  padding: 16,
  display: "flex",
  flexDirection: "column",
  gap: 10,
  boxShadow: "0 10px 30px rgba(0,0,0,0.25)",
};

const badgeStyle: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  gap: 6,
  padding: "4px 10px",
  borderRadius: 999,
  fontSize: 12,
  letterSpacing: "0.03em",
  textTransform: "uppercase",
  color: palette.text,
  background: "rgba(94, 234, 212, 0.12)",
  border: `1px solid rgba(94, 234, 212, 0.25)`,
};

const workerCatalog: WorkerConfig[] = [
  // Memory Spine (primary)
  { key: "memory", label: "Memory Update Worker", description: "Writes short/long term memory; must explain inputs and writes." },
  { key: "episodic", label: "Episodic (legacy)", description: "Legacy episodic builder from recent journals (read-only until replaced)." },
  { key: "episodic-v21", label: "Episodic v2.1", description: "Daily episodic consolidation (v2.1) with summary + embedding." },
  { key: "consolidation", label: "Graph Consolidation", description: "Merge duplicate memory nodes/edges (graph dedup only)." },
  { key: "memory-graph-builder", label: "Memory Graph Builder", description: "Build memory graph from enrichment for a journal." },
  { key: "personal-model", label: "Personal Model Worker", description: "Updates personal_model from recent signals/rollups." },
  { key: "context-refresh", label: "Context Refresh", description: "Rebuilds context cache snapshot (merged vectors).", optInOnly: true },

  // Core turn workers
  { key: "planner", label: "Planner Worker", description: "Plans/updates weekly plan; should expose deltas." },
  { key: "rhythm", label: "Rhythm Worker", description: "Tracks rhythm state and curve, grounded in evidence." },
  { key: "persona", label: "Persona Worker", description: "Updates persona model with transparent evidence." },
  { key: "meta-reflection", label: "Meta-Reflection Worker", description: "Higher-level coherence check; optional." },
  { key: "insight", label: "Insight Generator (read-only)", description: "Outputs only; cannot be triggered here.", readOnly: true },
  { key: "soul-refresh", label: "Soul Refresh", description: "Refreshes soul layers from recent signals.", optInOnly: true },
  { key: "neutral_signal_extraction", label: "Neutral Signal Extraction", description: "Extracts deterministic neutral signals into STM (prerequisite for elemental/energy layers)." },
  { key: "ayurvedic_pipeline", label: "Ayurvedic & Energy Pipeline", description: "Runs elemental and energy intelligence layers", optInOnly: true },

  // Expanded worker plane (inventory from systems stocktake)
  { key: "memory-spine", label: "Memory Spine", description: "End-to-end memory spine updates/consistency." },
  { key: "planner-alignment", label: "Planner + Alignment", description: "Alignment checks + planning artifacts." },
  { key: "rhythm-forecast", label: "Rhythm & Forecast", description: "Rhythm state + forward projection." },
  { key: "longitudinal-update", label: "Longitudinal Update Worker", description: "Updates personal_model.longitudinal_state from episodic signals.", optInOnly: true },
  { key: "insight-engine", label: "Insight Engine", description: "Insight generation; should return structured evidence." },
  { key: "daily-micro-flows", label: "Daily / Micro Flows", description: "Day-level or micro-flow synthesis." },
  { key: "presence-followups", label: "Presence / Follow-Ups", description: "Follow-up queue / presence nudges." },
  { key: "insights-queue", label: "Insights Queue", description: "Queue state (read-only)", readOnly: true },
  { key: "task-weaver", label: "Task Weaver", description: "Task threading + weaving." },
  { key: "analytics-calibration", label: "Analytics / Calibration", description: "Calibration and analytics checks." },
  { key: "maintenance-tempo", label: "Maintenance / Tempo", description: "Maintenance jobs and tempo health." },

  // Deep layers (episodic v2.1+ consumers)
  { key: "narrative-deep", label: "Narrative Deep", description: "Builds soul narrative from episodic memory.", optInOnly: true },
  { key: "identity-momentum-deep", label: "Identity Momentum Deep", description: "Tracks identity drift using episodic signals.", optInOnly: true },
  { key: "decision-graph-deep", label: "Decision Graph Deep", description: "Builds internal decision graph from conflicts/friction.", optInOnly: true },
  { key: "rhythm-soul-deep", label: "Rhythm Soul Deep", description: "Assesses rhythm alignment with soul direction.", optInOnly: true },
  { key: "emotion-soul-rhythm-deep", label: "Emotion × Soul × Rhythm", description: "Sensemaking join of emotion, values, and rhythm capacity.", optInOnly: true },
  { key: "esr-deep", label: "ESR Deep", description: "Stability / regulation synthesis from episodic signals.", optInOnly: true },
  { key: "esr", label: "ESR (emotion state)", description: "Deterministic emotional signal extraction.", optInOnly: true },
];

const defaultSelectedWorkers = workerCatalog.filter((w) => !w.readOnly && !w.optInOnly).map((w) => w.key);

function createSessionId() {
  const ts = new Date().toISOString().replace(/[-:TZ.]/g, "").slice(0, 14);
  const rand = Math.random().toString(36).slice(2, 6);
  return `lab-${ts}-${rand}`;
}

function formatTime(value?: string) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function safeStringify(value: any) {
  const redact = (v: any): any => {
    if (v === null || v === undefined) return v;
    if (Array.isArray(v)) {
      const allNumbers = v.every((x) => typeof x === "number");
      if (allNumbers && v.length > 8) {
        return { has_vec: true, dim: v.length };
      }
      return v.map(redact);
    }
    if (typeof v === "object") {
      const out: any = {};
      for (const [k, val] of Object.entries(v)) {
        const key = k.toLowerCase();
        const isVectorKey = key.includes("vector") || key.endsWith("_vec") || key.endsWith("_embedding");
        if (isVectorKey) {
          const asArr = Array.isArray(val) ? val : [];
          out[k] = { has_vec: !!val, dim: asArr.length || undefined };
        } else {
          out[k] = redact(val);
        }
      }
      return out;
    }
    return v;
  };

  try {
    return JSON.stringify(redact(value), null, 2);
  } catch {
    return String(value);
  }
}

function toArray(value: any): string[] {
  if (!value) return [];
  if (Array.isArray(value)) return value.map((v) => String(v));
  if (typeof value === "string") return [value];
  return Object.values(value).map((v) => String(v));
}

function summarizeMetadata(meta: any) {
  if (!meta) return [];
  const items: Array<{ label: string; value: string }> = [];
  if ("cache_hit" in meta) items.push({ label: "cache_hit", value: String(meta.cache_hit) });
  if (meta.rhythm) items.push({ label: "rhythm", value: safeStringify(meta.rhythm) });
  if (meta.persona) items.push({ label: "persona", value: safeStringify(meta.persona) });
  if (meta.tasks) items.push({ label: "tasks", value: safeStringify(meta.tasks) });
  if (meta.behavior_profile) items.push({ label: "behavior_profile", value: safeStringify(meta.behavior_profile) });
  return items;
}

function parseSystemContext(raw: any) {
  if (!raw || typeof raw !== "string") return null;
  const sections = raw.split(/Patterns:/i);
  const memoriesPart = sections[0] || "";
  const patternsPart = sections[1] || "";
  const memoryLines = memoriesPart
    .split("\n")
    .map((l) => l.trim())
    .filter((l) => l.startsWith("-"))
    .map((l) => l.replace(/^-+\s*/, ""))
    .filter(Boolean);
  const patternLines = patternsPart
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean);
  return { memoryLines, patternLines };
}

function buildSummary(payload: any): WorkerSummary {
  return {
    worker: payload?.worker || payload?.name || "unknown",
    inputs: payload?.inputs_used || payload?.inputs || payload?.sources || [],
    writes: payload?.writes ?? payload?.delta ?? payload?.changes ?? null,
    signals: payload?.signals ?? payload?.inferences ?? payload?.findings ?? null,
    evidence: toArray(payload?.evidence ?? payload?.support ?? payload?.proofs),
    notes: payload?.notes ?? payload?.comment ?? payload?.message ?? null,
    confidence: payload?.confidence ?? payload?.score ?? payload?.confidence_score ?? null,
    previous_state: payload?.previous_state ?? payload?.prev_state ?? null,
    new_state: payload?.new_state ?? payload?.state ?? payload?.updated_state ?? null,
  };
}

function makeId() {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `id-${Math.random().toString(36).slice(2, 10)}`;
}

function workerStatusColor(status: WorkerRunState["status"]) {
  switch (status) {
    case "running":
    case "queued":
      return palette.accent2;
    case "completed":
      return palette.accent;
    case "error":
      return palette.danger;
    default:
      return palette.muted;
  }
}

export default function ReflectionLab() {
  const [userId, setUserId] = useState("c10fbd98-25fa-4445-8aba-e5243bc01564");
  const [sessionId, setSessionId] = useState("");
  const [sessionStartedAt, setSessionStartedAt] = useState("");
  const [selectedWorkers, setSelectedWorkers] = useState<string[]>(defaultSelectedWorkers);
  const [workerRuns, setWorkerRuns] = useState<Record<string, WorkerRunState>>(() => {
    const base: Record<string, WorkerRunState> = {};
    workerCatalog.forEach((w) => {
      base[w.key] = { status: "idle" };
    });
    return base;
  });
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [liveTurn, setLiveTurn] = useState<LiveTurnState>({ status: "idle" });
  const [manualRun, setManualRun] = useState<ManualRunState>({ status: "idle" });
  const [showOutputs, setShowOutputs] = useState(false);
  const [resultsMeta, setResultsMeta] = useState<{ loading: boolean; lastFetched?: string; error?: string }>({ loading: false });
  const [cleanupStatus, setCleanupStatus] = useState<{ status: "idle" | "running" | "done" | "error"; message?: string }>({
    status: "idle",
  });
  const [rawExpanded, setRawExpanded] = useState<Record<string, boolean>>({});
  const [hydrated, setHydrated] = useState(false);
  const [nowLabel, setNowLabel] = useState("—");
  const [timestampIso, setTimestampIso] = useState("");
  const [journalText, setJournalText] = useState("");
  const [replayExisting, setReplayExisting] = useState(false);
  const [batchText, setBatchText] = useState("");
  const [batchStatus, setBatchStatus] = useState<{ status: "idle" | "running" | "done" | "error"; message?: string; error?: string }>({
    status: "idle",
  });
  const [showDebugCards, setShowDebugCards] = useState(false);
  const [showWorkerChecklist, setShowWorkerChecklist] = useState(false);
  const [ayurReflection, setAyurReflection] = useState<string | null>(null);
  const [ayurStatus, setAyurStatus] = useState<"idle" | "loading" | "error" | "ready">("idle");
  const [ayurError, setAyurError] = useState<string | null>(null);
  const [ayurAnchorDays, setAyurAnchorDays] = useState<number>(1500);

  const availableUsers = useMemo(() => ["c10fbd98-25fa-4445-8aba-e5243bc01564", "founder_a", "founder_b"], []);

  useEffect(() => {
    const ts = new Date().toISOString();
    setSessionId((prev) => prev || createSessionId());
    setSessionStartedAt((prev) => prev || ts);
    setNowLabel(formatTime(ts));
    setTimestampIso(ts);
    setHydrated(true);
  }, []);

  const resetOutputs = () => {
    setWorkerRuns((prev) => {
      const base: Record<string, WorkerRunState> = {};
      Object.keys(prev).forEach((k) => {
        base[k] = { status: "idle" };
      });
      return base;
    });
    setTimeline([]);
    setLiveTurn({ status: "idle" });
    setManualRun({ status: "idle" });
    setResultsMeta({ loading: false, lastFetched: undefined, error: undefined });
    setRawExpanded({});
    const nextSession = createSessionId();
    setSessionId(nextSession);
    setSessionStartedAt(new Date().toISOString());
  };

  const logEvent = (label: string, detail?: string, tone: TimelineEvent["tone"] = "info") => {
    setTimeline((prev) => [
      { id: makeId(), timestamp: new Date().toISOString(), label, detail, tone },
      ...prev,
    ]);
  };

  const markWorkers = (keys: string[], status: WorkerRunState["status"], mode?: WorkerRunState["mode"]) => {
    if (!keys.length) return;
    const now = new Date().toISOString();
    setWorkerRuns((prev) => {
      const next = { ...prev };
      keys.forEach((key) => {
        next[key] = {
          ...prev[key],
          status,
          mode: mode ?? prev[key]?.mode,
          startedAt: status === "running" || status === "queued" ? now : prev[key]?.startedAt,
          finishedAt: status === "completed" || status === "error" ? now : prev[key]?.finishedAt,
          error: status === "error" ? prev[key]?.error : undefined,
          sessionId,
        };
      });
      return next;
    });
  };

  const applyWorkerResults = (results: any[], mode: WorkerRunState["mode"]) => {
    if (!results?.length) return;
    const now = new Date().toISOString();
    setWorkerRuns((prev) => {
      const next = { ...prev };
      results.forEach((res) => {
        const workerKey = String(res?.worker || res?.name || "unknown");
        next[workerKey] = {
          status: "completed",
          summary: buildSummary(res),
          raw: res,
          error: undefined,
          startedAt: prev[workerKey]?.startedAt ?? now,
          finishedAt: now,
          mode,
          sessionId,
        };
      });
      return next;
    });
  };

  const runLiveTurn = async () => {
    const activeSession = sessionId || createSessionId();
    setSessionId(activeSession);
    setSessionStartedAt(new Date().toISOString());
    setLiveTurn({ status: "running" });
    const replayMode = replayExisting && !(journalText || "").trim();
    logEvent("Live turn submitted", `Session ${activeSession} • User ${userId} • enqueue workers`);
    markWorkers(selectedWorkers, "queued", "live-turn");
    try {
      const res = await fetch("/api/lab/live-turn", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: userId,
          journal_text: replayMode ? "" : journalText || "",
          ts: timestampIso,
          mode: replayMode ? "replay_existing" : undefined,
          options: { enqueue_workers: false, sync_workers: true },
          workers: selectedWorkers,
          session_id: activeSession,
        }),
      });
      const text = await res.text();
      const data = text ? JSON.parse(text) : {};
      if (!res.ok) {
        throw new Error(data?.error || res.statusText || "Live turn failed");
      }
      const jobIds = Array.isArray(data?.job_ids) ? data.job_ids : [];
      setLiveTurn({
        status: "done",
        turnId: data?.turn_id,
        jobIds,
        response: data?.immediate_response ?? data?.response ?? data?.reply,
        raw: data,
        llmDebug: data?.llm_debug,
      });
      markWorkers(selectedWorkers, "running", "live-turn");
      logEvent("Live turn acknowledged", `Turn ${data?.turn_id || "unknown"} • jobs ${jobIds.length}`, "success");
    } catch (err: any) {
      const message = err?.message || "Live turn failed";
      setLiveTurn({ status: "error", error: message });
      logEvent("Live turn error", message, "error");
    }
  };

  const parseBatchJournals = (raw: string): Array<{ ts?: string; text: string }> => {
    const blocks = raw
      .split(/\n\s*\n/)
      .map((b) => b.trim())
      .filter(Boolean);
    const entries: Array<{ ts?: string; text: string }> = [];
    for (const block of blocks) {
      const lines = block.split(/\n/);
      if (!lines.length) continue;
      const firstLine = lines.shift() || "";
      const text = lines.join("\n").trim();
      const date = new Date(firstLine);
      const ts = Number.isNaN(date.getTime()) ? undefined : date.toISOString();
      if (text) {
        entries.push({ ts, text });
      }
    }
    return entries;
  };

  const runBatchJournals = async () => {
    if (!batchText.trim()) {
      setBatchStatus({ status: "error", error: "Provide batch journals in the specified format." });
      return;
    }
    if (!userId) {
        setBatchStatus({ status: "error", error: "Set a user id first." });
        return;
    }
    const entries = parseBatchJournals(batchText);
    if (!entries.length) {
      setBatchStatus({ status: "error", error: "No valid journal blocks found. Check formatting." });
      return;
    }
    setBatchStatus({ status: "running" });
    const activeSession = sessionId || createSessionId();
    setSessionId(activeSession);
    setSessionStartedAt(new Date().toISOString());
    let success = 0;
    let failure = 0;
    let lastError: string | undefined;
    for (const entry of entries) {
      if (!entry.text.trim()) {
        failure += 1;
        lastError = "Empty journal text after parsing.";
        continue;
      }
      try {
        const res = await fetch("/api/lab/live-turn", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            user_id: userId,
            journal_text: entry.text,
            ts: entry.ts,
            options: { enqueue_workers: false, sync_workers: true },
            workers: selectedWorkers,
            session_id: activeSession,
          }),
        });
        const text = await res.text();
        const data = text ? JSON.parse(text) : {};
        if (!res.ok) {
          const errMessage = data?.detail || data?.error || res.statusText || "Live turn failed";
          throw new Error(errMessage);
        }
        success += 1;
        // mark worker states as running for visibility
        markWorkers(selectedWorkers, "running", "live-turn");
      } catch (err: any) {
        failure += 1;
        lastError = err?.message || "Live turn failed";
      }
    }
    setBatchStatus({
      status: "done",
      message: `Processed ${entries.length} journals (${success} ok, ${failure} failed).`,
      error: failure ? lastError || `${failure} failed` : undefined,
    });
  };

  const runWorkersManually = async () => {
    if (!selectedWorkers.length) {
      logEvent("Worker run blocked", "Select at least one worker", "warning");
      return;
    }
    const activeSession = sessionId || createSessionId();
    setSessionId(activeSession);
    setSessionStartedAt(new Date().toISOString());
    setManualRun({ status: "running", error: undefined });
    markWorkers(selectedWorkers, "running", "manual");
    logEvent("Manual worker run", `Session ${activeSession} • Workers: ${selectedWorkers.join(", ")}`);
    try {
      const res = await fetch("/api/lab/run-workers", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: userId,
          workers: selectedWorkers,
          session_id: activeSession,
        }),
      });
      const text = await res.text();
      const data = text ? JSON.parse(text) : {};
      if (!res.ok) {
        throw new Error(data?.error || res.statusText || "Worker run failed");
      }
      const results = Array.isArray(data?.results) ? data.results : Array.isArray(data) ? data : [];
      applyWorkerResults(results, "manual");
      setManualRun({ status: "done", raw: data });
      logEvent("Workers completed (manual)", `Results: ${results.length}`, "success");
    } catch (err: any) {
      const message = err?.message || "Worker run failed";
      setManualRun({ status: "error", error: message });
      markWorkers(selectedWorkers, "error", "manual");
      logEvent("Worker run error", message, "error");
    }
  };

  const fetchWorkerResults = async () => {
    setResultsMeta((prev) => ({ ...prev, loading: true, error: undefined }));
    logEvent("Fetching worker results", `Session ${sessionId}`);
    try {
      const url = new URL("/api/lab/worker-results", window.location.origin);
      url.searchParams.set("session_id", sessionId);
      url.searchParams.set("user_id", userId);
      const res = await fetch(url.toString());
      const text = await res.text();
      const data = text ? JSON.parse(text) : {};
      if (!res.ok) {
        throw new Error(data?.error || res.statusText || "Failed to fetch worker results");
      }
      const results = Array.isArray(data?.results) ? data.results : Array.isArray(data) ? data : data?.workers || [];
      applyWorkerResults(results, "results");
      setResultsMeta({ loading: false, lastFetched: new Date().toISOString() });
      logEvent("Worker results updated", `${results.length} payloads`, "success");
    } catch (err: any) {
      const message = err?.message || "Failed to fetch worker results";
      setResultsMeta({ loading: false, error: message });
      logEvent("Worker results error", message, "error");
    }
  };

  const runCleanup = async () => {
    setCleanupStatus({ status: "running" });
    logEvent("Cleanup requested", `User ${userId}`);
    try {
      const res = await fetch("/api/lab/cleanup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId }),
      });
      const text = await res.text();
      const data = text ? JSON.parse(text) : {};
      if (!res.ok) {
        throw new Error(data?.error || res.statusText || "Cleanup failed");
      }
      const deleted = data?.deleted || {};
      const message = `Removed journal/memory rows: ${Object.entries(deleted)
        .map(([k, v]) => `${k}=${v}`)
        .join(", ")}`;
      setCleanupStatus({ status: "done", message });
      logEvent("Cleanup completed", message, "success");
    } catch (err: any) {
      const message = err?.message || "Cleanup failed";
      setCleanupStatus({ status: "error", message });
      logEvent("Cleanup error", message, "error");
    }
  };

  const generateAyurvedicReflection = async () => {
    if (!userId) {
      setAyurError("User ID is required");
      setAyurStatus("error");
      return;
    }
    setAyurStatus("loading");
    setAyurError(null);
    setAyurReflection(null);
    try {
      const res = await fetch("/api/lab/ayurvedic-reflection", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ person_id: userId, anchor_days: ayurAnchorDays || 1500 }),
      });
      const text = await res.text();
      const data = text ? JSON.parse(text) : {};
      if (!res.ok) {
        throw new Error(data?.error || res.statusText || "Failed to generate reflection");
      }
      setAyurReflection(data?.reflection || "");
      setAyurStatus("ready");
      logEvent("Ayurvedic reflection generated", `anchor_days=${ayurAnchorDays}`, "success");
    } catch (err: any) {
      const message = err?.message || "Failed to generate reflection";
      setAyurError(message);
      setAyurStatus("error");
      logEvent("Ayurvedic reflection error", message, "error");
    }
  };

  const toggleWorker = (key: string) => {
    if (workerCatalog.find((w) => w.key === key)?.readOnly) return;
    setSelectedWorkers((prev) => {
      if (prev.includes(key)) {
        return prev.filter((k) => k !== key);
      }
      return [...prev, key];
    });
  };

  const allSelectable = useMemo(() => workerCatalog.filter((w) => !w.readOnly).map((w) => w.key), []);
  const allSelected = allSelectable.every((k) => selectedWorkers.includes(k)) && allSelectable.length > 0;

  const toggleAllWorkers = () => {
    if (allSelected) {
      setSelectedWorkers([]);
    } else {
      setSelectedWorkers(allSelectable);
    }
  };

  const toggleRaw = (key: string) => {
    setRawExpanded((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const workerPanels = useMemo(() => {
    const orderedKeys = Array.from(new Set([...workerCatalog.map((w) => w.key), ...Object.keys(workerRuns)]));
    return orderedKeys.map((key) => {
      const config = workerCatalog.find((w) => w.key === key);
      const state = workerRuns[key] ?? { status: "idle" };
      const summary = state.summary;
      const raw = state.raw;
      const isRawOpen = rawExpanded[key];
      const memoryDetailsLink =
        key === "memory" || key === "memory-spine"
          ? `/lab/memory-details?person_id=${encodeURIComponent(userId)}${
              liveTurn.raw?.entry_id ? `&entry_id=${encodeURIComponent(liveTurn.raw.entry_id)}` : ""
            }`
          : null;
      const memorySpineDetailsLink =
        key === "memory-spine"
          ? `/lab/memory-spine-details?person_id=${encodeURIComponent(userId)}`
          : null;
      const plannerDetailsLink =
        key === "planner" || key === "planner-alignment"
          ? `/lab/planner-details?person_id=${encodeURIComponent(userId)}`
          : null;
      const rhythmDetailsLink =
        key === "rhythm" || key === "rhythm-forecast"
          ? `/lab/rhythm-details?person_id=${encodeURIComponent(userId)}`
          : null;
      const personaDetailsLink =
        key === "persona"
          ? `/lab/persona-details?person_id=${encodeURIComponent(userId)}`
          : null;
      const metaReflectionDetailsLink =
        key === "meta-reflection"
          ? `/lab/meta-reflection-details?person_id=${encodeURIComponent(userId)}`
          : null;
      const microFlowDetailsLink =
        key === "daily-micro-flows"
          ? `/lab/micro-flows-details?person_id=${encodeURIComponent(userId)}`
          : null;
      const presenceDetailsLink =
        key === "presence-followups"
          ? `/lab/presence-details?person_id=${encodeURIComponent(userId)}`
          : null;
      const taskWeaverDetailsLink =
        key === "task-weaver"
          ? `/lab/task-weaver-details?person_id=${encodeURIComponent(userId)}`
          : null;
      const consolidationDetailsLink =
        key === "consolidation"
          ? `/lab/consolidation-details?person_id=${encodeURIComponent(userId)}`
          : null;
      const analyticsDetailsLink =
        key === "analytics-calibration"
          ? `/lab/analytics-calibration-details?person_id=${encodeURIComponent(userId)}`
          : null;
      const maintenanceDetailsLink =
        key === "maintenance-tempo"
          ? `/lab/maintenance-tempo-details?person_id=${encodeURIComponent(userId)}`
          : null;
      const insightsDetailsLink =
        key === "insight" || key === "insight-engine" || key === "insights-queue"
          ? `/lab/insights-details?person_id=${encodeURIComponent(userId)}`
          : null;
      return (
        <div key={key} style={{ ...cardStyle, borderColor: workerStatusColor(state.status) }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            <div>
              <div style={{ fontWeight: 600, color: palette.text }}>{config?.label || key}</div>
              <div style={{ color: palette.muted, fontSize: 13 }}>{config?.description || "Worker output"}</div>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ ...badgeStyle, borderColor: workerStatusColor(state.status), color: workerStatusColor(state.status) }}>
                {state.status.toUpperCase()}
              </span>
              {state.mode && <span style={{ ...badgeStyle, background: "rgba(56,189,248,0.1)", borderColor: "rgba(56,189,248,0.3)" }}>{state.mode}</span>}
            </div>
          </div>

          <div style={{ display: "grid", gap: 8, gridTemplateColumns: "repeat(auto-fit,minmax(220px,1fr))" }}>
            <div>
              <div style={{ color: palette.muted, fontSize: 12, letterSpacing: "0.03em" }}>Inputs used</div>
              <div style={{ marginTop: 4, fontSize: 13, color: palette.text }}>
                {summary?.inputs?.length ? summary.inputs.join(", ") : "—"}
              </div>
            </div>
            {metaReflectionDetailsLink && (
              <div style={{ gridColumn: "1 / -1" }}>
                <a href={metaReflectionDetailsLink} style={{ color: "#ffffff", fontSize: 12 }}>
                  View meta-reflection DB details
                </a>
              </div>
            )}
            <div>
              <div style={{ color: palette.muted, fontSize: 12, letterSpacing: "0.03em" }}>Signals</div>
              <div style={{ marginTop: 4, fontSize: 13, color: palette.text }}>
                {summary?.signals ? safeStringify(summary.signals) : "—"}
              </div>
            </div>
            <div>
              <div style={{ color: palette.muted, fontSize: 12, letterSpacing: "0.03em" }}>Writes / deltas</div>
              <div style={{ marginTop: 4, fontSize: 13, color: palette.text }}>
                {summary?.writes ? safeStringify(summary.writes) : "—"}
              </div>
            </div>
            <div>
              <div style={{ color: palette.muted, fontSize: 12, letterSpacing: "0.03em" }}>Evidence</div>
              <div style={{ marginTop: 4, fontSize: 13, color: palette.text }}>
                {summary?.evidence?.length ? summary.evidence.join(" • ") : "—"}
              </div>
            </div>
            <div>
              <div style={{ color: palette.muted, fontSize: 12, letterSpacing: "0.03em" }}>Confidence</div>
              <div style={{ marginTop: 4, fontSize: 13, color: palette.text }}>
                {summary?.confidence ?? "—"}
              </div>
            </div>
            <div>
              <div style={{ color: palette.muted, fontSize: 12, letterSpacing: "0.03em" }}>State change</div>
              <div style={{ marginTop: 4, fontSize: 13, color: palette.text }}>
                {summary?.previous_state || summary?.new_state
                  ? `${summary?.previous_state || "?"} → ${summary?.new_state || "?"}`
                  : "—"}
              </div>
            </div>
            <div>
              <div style={{ color: palette.muted, fontSize: 12, letterSpacing: "0.03em" }}>Notes</div>
              <div style={{ marginTop: 4, fontSize: 13, color: palette.text }}>
                {summary?.notes || "—"}
              </div>
            </div>
            <div>
              <div style={{ color: palette.muted, fontSize: 12, letterSpacing: "0.03em" }}>Timestamps</div>
              <div style={{ marginTop: 4, fontSize: 13, color: palette.text }}>
                {state.startedAt ? `Started: ${formatTime(state.startedAt)}` : "—"}
                {state.finishedAt ? ` • Finished: ${formatTime(state.finishedAt)}` : ""}
              </div>
            </div>
          </div>

          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <button
                style={{
                  ...badgeStyle,
                  padding: "6px 10px",
                  background: "#0f1115",
                  border: "1px solid #0f1115",
                  color: "#ffffff",
                  cursor: "pointer",
                }}
                onClick={() => toggleRaw(key)}
              >
                {isRawOpen ? "Hide raw JSON" : "Show raw JSON"}
              </button>
            {state.error && <span style={{ color: palette.danger, fontSize: 13 }}>{state.error}</span>}
            {memoryDetailsLink ? (
              <a href={memoryDetailsLink} style={{ color: palette.accent, fontSize: 12 }}>
                View memory DB details
              </a>
            ) : null}
            {memorySpineDetailsLink ? (
              <a href={memorySpineDetailsLink} style={{ color: palette.accent, fontSize: 12 }}>
                View memory spine DB details
              </a>
            ) : null}
            {plannerDetailsLink ? (
              <a href={plannerDetailsLink} style={{ color: palette.accent, fontSize: 12 }}>
                View planner DB details
              </a>
            ) : null}
            {rhythmDetailsLink ? (
              <a href={rhythmDetailsLink} style={{ color: palette.accent, fontSize: 12 }}>
                View rhythm DB details
              </a>
            ) : null}
            {personaDetailsLink ? (
              <a href={personaDetailsLink} style={{ color: palette.accent, fontSize: 12 }}>
                View persona DB details
              </a>
            ) : null}
            {metaReflectionDetailsLink ? (
              <a href={metaReflectionDetailsLink} style={{ color: "#ffffff", fontSize: 12 }}>
                View meta-reflection DB details
              </a>
            ) : null}
            {microFlowDetailsLink ? (
              <a href={microFlowDetailsLink} style={{ color: "#ffffff", fontSize: 12 }}>
                View micro-flows DB details
              </a>
            ) : null}
            {presenceDetailsLink ? (
              <a href={presenceDetailsLink} style={{ color: "#ffffff", fontSize: 12 }}>
                View presence/follow-ups DB details
              </a>
            ) : null}
            {taskWeaverDetailsLink ? (
              <a href={taskWeaverDetailsLink} style={{ color: "#ffffff", fontSize: 12 }}>
                View task weaver DB details
              </a>
            ) : null}
            {consolidationDetailsLink ? (
              <a href={consolidationDetailsLink} style={{ color: "#ffffff", fontSize: 12 }}>
                View consolidation DB details
              </a>
            ) : null}
            {analyticsDetailsLink ? (
              <a href={analyticsDetailsLink} style={{ color: "#ffffff", fontSize: 12 }}>
                View analytics/calibration DB details
              </a>
            ) : null}
            {maintenanceDetailsLink ? (
              <a href={maintenanceDetailsLink} style={{ color: "#ffffff", fontSize: 12 }}>
                View maintenance/tempo DB details
              </a>
            ) : null}
            {insightsDetailsLink ? (
              <a href={insightsDetailsLink} style={{ color: "#ffffff", fontSize: 12 }}>
                View insights/queue DB details
              </a>
            ) : null}
          </div>

          {isRawOpen && (
            <pre
              style={{
                background: palette.surface,
                border: `1px solid ${palette.border}`,
                borderRadius: 10,
                padding: 12,
                fontSize: 12,
                color: palette.text,
                overflow: "auto",
                maxHeight: 280,
              }}
            >
              {raw ? safeStringify(raw) : "No payload yet."}
            </pre>
          )}
        </div>
      );
    });
  }, [rawExpanded, workerRuns, userId, liveTurn.raw]);

  return (
    <div style={{ minHeight: "100vh", background: palette.bg, color: palette.text, padding: "20px 16px", fontFamily: "Inter, system-ui, -apple-system, sans-serif" }}>
      <div style={{ maxWidth: 1240, margin: "0 auto", display: "flex", flexDirection: "column", gap: 14 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
          <div>
            <div style={{ ...badgeStyle, marginBottom: 8 }}>Reflection Lab</div>
            <h1 style={{ margin: 0, fontSize: 26, letterSpacing: "-0.01em" }}>Personal-Intelligence Spine Check</h1>
            <div style={{ color: palette.muted, marginTop: 4, maxWidth: 720 }}>
              Freeze UX, stress the spine. Run live turns or individual workers, see deterministic artifacts, and decide if the system is coherent, overreaching, or missing signals.
            </div>
          </div>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <div style={{ ...badgeStyle, background: "rgba(251,191,36,0.14)", borderColor: "rgba(251,191,36,0.4)", color: palette.caution }}>
              Internal systems lab
            </div>
          </div>

          <div style={cardStyle}>
            <div style={{ color: palette.muted, fontSize: 12, letterSpacing: "0.05em" }}>Batch Journals (one per block)</div>
            <div style={{ fontSize: 12, color: palette.muted, marginTop: 4 }}>
              Format: first line is timestamp, following lines are the journal text. Separate entries with a blank line. Example:
              <pre style={{ background: palette.surface, border: `1px solid ${palette.border}`, borderRadius: 10, padding: 10, fontSize: 12, color: palette.text, whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
1 Jan 2023, 06:18:42
Woke up earlier than usual today. New year energy, but my lower back feels stiff again. Told myself I’ll stretch for 10 minutes before the day takes over.

1 Jan 2023, 09:07:15
Kids were excited about the holiday. Breakfast felt rushed anyway. I’m already thinking about emails piling up tomorrow. Hard to stay present.
              </pre>
            </div>
            <textarea
              value={batchText}
              onChange={(e) => setBatchText(e.target.value)}
              placeholder="Paste multiple journals in the format shown above"
              style={{
                marginTop: 8,
                minHeight: 180,
                width: "100%",
                borderRadius: 12,
                border: `1px solid ${palette.border}`,
                background: palette.surface,
                color: palette.text,
                padding: 12,
                fontFamily: "inherit",
              }}
            />
            {batchStatus.status === "error" && <div style={{ color: palette.danger, fontSize: 12 }}>{batchStatus.error}</div>}
            {batchStatus.status === "done" && <div style={{ color: "#ffffff", fontSize: 12 }}>{batchStatus.message}</div>}
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1.35fr 1fr", gap: 12 }}>
          <div style={cardStyle}>
            <div style={{ display: "flex", justifyContent: "space-between", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
              <div>
                <div style={{ color: palette.muted, fontSize: 12, letterSpacing: "0.05em" }}>Context Selector</div>
                <div style={{ fontSize: 18, fontWeight: 600 }}>User</div>
              </div>
              <button
                onClick={resetOutputs}
                style={{
                  ...badgeStyle,
                  background: "#0f1115",
                  border: "1px solid #0f1115",
                  color: "#ffffff",
                  cursor: "pointer",
                }}
              >
                🧹 Clear outputs
              </button>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(220px,1fr))", gap: 10 }}>
              <div>
                <div style={{ color: palette.muted, fontSize: 12, letterSpacing: "0.03em" }}>User ID</div>
                <input
                  list="lab-users"
                  value={userId}
                  onChange={(e) => setUserId(e.target.value)}
                  style={{
                    width: "100%",
                    marginTop: 6,
                    padding: "10px 12px",
                    borderRadius: 10,
                    border: `1px solid ${palette.border}`,
                    background: palette.surface,
                    color: palette.text,
                  }}
                />
                <datalist id="lab-users">
                  {availableUsers.map((u) => (
                    <option key={u} value={u} />
                  ))}
                </datalist>
              </div>
              <div>
                <div style={{ color: palette.muted, fontSize: 12, letterSpacing: "0.03em" }}>Timestamp (editable)</div>
                <input
                  type="text"
                  value={nowLabel}
                  onChange={(e) => {
                    const val = e.target.value;
                    setNowLabel(val);
                    const parsed = new Date(val);
                    if (!Number.isNaN(parsed.getTime())) {
                      setTimestampIso(parsed.toISOString());
                    }
                  }}
                  placeholder="Set timestamp label"
                  style={{
                    marginTop: 6,
                    padding: "10px 12px",
                    borderRadius: 10,
                    border: `1px solid ${palette.border}`,
                    background: palette.surface,
                    color: palette.text,
                    width: "100%",
                  }}
                />
              </div>
            </div>
          </div>

          <div style={{ ...cardStyle, borderTop: `1px solid ${palette.border}`, paddingTop: 14, background: "rgba(255,255,255,0.02)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap", marginBottom: 6, justifyContent: "space-between" }}>
              <div style={{ color: palette.muted, fontSize: 12, letterSpacing: "0.05em" }}>Worker Checklist</div>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                <button
                  type="button"
                  onClick={() => setShowWorkerChecklist((v) => !v)}
                  style={{
                    background: showWorkerChecklist ? "rgba(94,234,212,0.14)" : "rgba(255,255,255,0.06)",
                    color: palette.text,
                    border: `1px solid ${palette.border}`,
                    borderRadius: 999,
                    padding: "6px 12px",
                    cursor: "pointer",
                  }}
                >
                  {showWorkerChecklist ? "Hide workers" : "Show workers"}
                </button>
                <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <input type="checkbox" checked={allSelected} onChange={toggleAllWorkers} />
                  <span style={{ fontWeight: 600 }}>{allSelected ? "Unselect all" : "Select all"}</span>
                </label>
              </div>
            </div>
            <div style={{ color: palette.muted, fontSize: 12, marginBottom: 4 }}>
              {allSelected ? "All non-readonly workers selected" : "Toggle workers and expand to choose individually"}
            </div>
            {showWorkerChecklist && (
              <div style={{ display: "flex", flexWrap: "wrap", gap: 12, marginTop: 10 }}>
                {workerCatalog.map((worker) => (
                  <label
                    key={worker.key}
                    style={{
                      display: "flex",
                      gap: 8,
                      alignItems: "flex-start",
                      color: palette.text,
                      padding: "10px 12px",
                      border: `1px solid ${palette.border}`,
                      borderRadius: 10,
                      background: palette.surface,
                      minWidth: 220,
                      flex: "1 1 230px",
                    }}
                  >
                    <input
                      type="checkbox"
                      disabled={worker.readOnly}
                      checked={selectedWorkers.includes(worker.key)}
                      onChange={() => toggleWorker(worker.key)}
                      style={{ marginTop: 4 }}
                    />
                    <div>
                      <div style={{ fontWeight: 600, color: worker.readOnly ? palette.muted : palette.text }}>{worker.label}</div>
                      <div style={{ color: palette.muted, fontSize: 12 }}>{worker.description}</div>
                    </div>
                  </label>
                ))}
              </div>
            )}
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: 12 }}>
          <div style={cardStyle}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12 }}>
              <div style={{ color: palette.muted, fontSize: 12, letterSpacing: "0.05em" }}>Journal Input (optional)</div>
              <label style={{ display: "flex", alignItems: "center", gap: 8, color: palette.text, fontSize: 13 }}>
                <input
                  type="checkbox"
                  checked={replayExisting}
                  onChange={(e) => {
                    setReplayExisting(e.target.checked);
                    if (e.target.checked) setJournalText("");
                  }}
                  style={{ margin: 0 }}
                />
                Replay existing journals (no new input)
              </label>
            </div>
            <textarea
              value={journalText}
              onChange={(e) => setJournalText(e.target.value)}
              readOnly={replayExisting}
              placeholder={
                replayExisting
                  ? "Replay mode enabled: existing journals will be re-run in order."
                  : "Paste a journal entry here (or leave empty to run workers on existing memory)"
              }
              style={{
                marginTop: 8,
                minHeight: 140,
                width: "100%",
                borderRadius: 12,
                border: `1px solid ${palette.border}`,
                background: palette.surface,
                color: palette.text,
                padding: 12,
                fontFamily: "inherit",
              }}
            />
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <button
                onClick={runLiveTurn}
                disabled={liveTurn.status === "running"}
                style={{
                  ...badgeStyle,
                  background: "#0f1115",
                  border: "1px solid #0f1115",
                  color: "#ffffff",
                  cursor: "pointer",
                  fontWeight: 600,
                  padding: "10px 14px",
                }}
              >
                {liveTurn.status === "running" ? "Running live turn…" : "▶️ Run Live Turn"}
              </button>
              <button
                onClick={runBatchJournals}
                disabled={batchStatus.status === "running"}
                style={{
                  ...badgeStyle,
                  background: "#0f1115",
                  border: "1px solid #0f1115",
                  color: "#ffffff",
                  cursor: "pointer",
                  fontWeight: 600,
                  padding: "10px 14px",
                }}
              >
                {batchStatus.status === "running" ? "Running batch…" : "▶️ Run Batch Journals"}
              </button>
              <button
                onClick={runWorkersManually}
                disabled={manualRun.status === "running"}
                style={{
                  ...badgeStyle,
                  background: "#0f1115",
                  border: "1px solid #0f1115",
                  color: "#ffffff",
                  cursor: "pointer",
                  fontWeight: 600,
                  padding: "10px 14px",
                }}
              >
                {manualRun.status === "running" ? "Running workers…" : "⚙️ Run Worker(s)"}
              </button>
              <button
                onClick={fetchWorkerResults}
                disabled={resultsMeta.loading}
                style={{
                  ...badgeStyle,
                  background: "#0f1115",
                  border: "1px solid #0f1115",
                  color: "#ffffff",
                  cursor: "pointer",
                  padding: "10px 14px",
                }}
              >
                {resultsMeta.loading ? "Pulling results…" : "⟳ Fetch worker results"}
              </button>
              {resultsMeta.lastFetched && (
                <span style={{ color: palette.muted, fontSize: 12 }}>Updated {formatTime(resultsMeta.lastFetched)}</span>
              )}
              {resultsMeta.error && <span style={{ color: palette.danger, fontSize: 12 }}>{resultsMeta.error}</span>}
            </div>
            <div style={{ marginTop: 8, padding: 10, borderRadius: 12, border: `1px dashed ${palette.border}`, background: palette.surface }}>
              <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                <button
                  onClick={runCleanup}
                  disabled={cleanupStatus.status === "running"}
                  style={{
                    ...badgeStyle,
                    background: "#0f1115",
                    border: "1px solid #0f1115",
                    color: "#ffffff",
                    cursor: "pointer",
                    padding: "8px 12px",
                  }}
                >
                  {cleanupStatus.status === "running" ? "Cleaning…" : "🧹 Cleanup user data"}
                </button>
                <span style={{ color: palette.muted, fontSize: 12 }}>
                  Deletes journal + memory rows for this user. Re-run ingest/workers after cleaning.
                </span>
              </div>
              {cleanupStatus.message && (
                <div style={{ color: cleanupStatus.status === "error" ? palette.danger : palette.accent2, fontSize: 12, marginTop: 6 }}>
                  {cleanupStatus.message}
                </div>
              )}
            </div>
            <div style={{ color: palette.muted, fontSize: 12, marginTop: 6 }}>
              Live turn flow: journal → /v2/turn → synchronous capture → queues workers → subscribe here.
            </div>
            <div style={{ marginTop: 12 }}>
              <div style={{ ...cardStyle, background: palette.card }}>
                <div style={{ fontWeight: 600, marginBottom: 6 }}>Live Turn Artifact</div>
                {liveTurn.status === "idle" && <div style={{ color: palette.muted, fontSize: 13 }}>Not run yet.</div>}
                {liveTurn.status === "running" && <div style={{ color: "#ffffff" }}>Running… waiting for immediate response.</div>}
                {liveTurn.status === "error" && <div style={{ color: palette.danger }}>{liveTurn.error}</div>}
                {liveTurn.response && (
                  <>
                    <div style={{ color: palette.muted, fontSize: 12, marginBottom: 6 }}>Immediate response</div>
                    <div
                      style={{
                        background: palette.surface,
                        border: `1px solid ${palette.border}`,
                        borderRadius: 10,
                        padding: 12,
                        fontSize: 13,
                        color: palette.text,
                        whiteSpace: "pre-wrap",
                        wordBreak: "break-word",
                        lineHeight: 1.6,
                      }}
                    >
                      {typeof liveTurn.response === "string" ? liveTurn.response : safeStringify(liveTurn.response)}
                    </div>
                  </>
                )}
                {liveTurn.llmDebug && (
                  <div style={{ marginTop: 12, display: "flex", flexDirection: "column", gap: 12 }}>
                    <div>
                      <div style={{ color: palette.muted, fontSize: 12, marginBottom: 4 }}>System context (recall + patterns)</div>
                      {parseSystemContext(liveTurn.llmDebug?.system_context) ? (
                        (() => {
                          const parsed = parseSystemContext(liveTurn.llmDebug?.system_context);
                          if (!parsed) return null;
                          return (
                            <div style={{ background: palette.surface, border: `1px solid ${palette.border}`, borderRadius: 10, padding: 12, lineHeight: 1.5 }}>
                              <div style={{ fontWeight: 600, marginBottom: 4 }}>Relevant memory</div>
                              <ul style={{ margin: 0, paddingLeft: 18 }}>
                                {parsed.memoryLines.length ? (
                                  parsed.memoryLines.map((line, idx) => (
                                    <li key={`mem-${idx}`} style={{ color: palette.text }}>
                                      {line}
                                    </li>
                                  ))
                                ) : (
                                  <li style={{ color: palette.muted }}>No recalled memory</li>
                                )}
                              </ul>
                              <div style={{ fontWeight: 600, marginTop: 10, marginBottom: 4 }}>Patterns</div>
                              <ul style={{ margin: 0, paddingLeft: 18 }}>
                                {parsed.patternLines.length ? (
                                  parsed.patternLines.map((line, idx) => (
                                    <li key={`pat-${idx}`} style={{ color: palette.text }}>
                                      {line}
                                    </li>
                                  ))
                                ) : (
                                  <li style={{ color: palette.muted }}>No patterns surfaced</li>
                                )}
                              </ul>
                            </div>
                          );
                        })()
                      ) : (
                        <pre
                          style={{
                            background: palette.surface,
                            border: `1px solid ${palette.border}`,
                            borderRadius: 10,
                            padding: 10,
                            fontSize: 12,
                            color: palette.text,
                            whiteSpace: "pre-wrap",
                            wordBreak: "break-word",
                            maxHeight: 320,
                            overflow: "auto",
                          }}
                        >
                          {safeStringify(liveTurn.llmDebug?.system_context || "")}
                        </pre>
                      )}
                    </div>

                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(260px,1fr))", gap: 10 }}>
                      <div>
                        <div style={{ color: palette.muted, fontSize: 12, marginBottom: 4 }}>Tone blueprint</div>
                        <pre
                          style={{
                            background: palette.surface,
                            border: `1px solid ${palette.border}`,
                            borderRadius: 10,
                            padding: 10,
                            fontSize: 12,
                            color: palette.text,
                            whiteSpace: "pre-wrap",
                            wordBreak: "break-word",
                            maxHeight: 180,
                            overflow: "auto",
                          }}
                        >
                          {safeStringify(liveTurn.llmDebug?.tone_blueprint || {})}
                        </pre>
                      </div>
                      <div>
                        <div style={{ color: palette.muted, fontSize: 12, marginBottom: 4 }}>Behavior profile</div>
                        <pre
                          style={{
                            background: palette.surface,
                            border: `1px solid ${palette.border}`,
                            borderRadius: 10,
                            padding: 10,
                            fontSize: 12,
                            color: palette.text,
                            whiteSpace: "pre-wrap",
                            wordBreak: "break-word",
                            maxHeight: 180,
                            overflow: "auto",
                          }}
                        >
                          {safeStringify(liveTurn.llmDebug?.metadata?.behavior_profile || {})}
                        </pre>
                      </div>
                    </div>

                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(260px,1fr))", gap: 10 }}>
                      <div>
                        <div style={{ color: palette.muted, fontSize: 12, marginBottom: 4 }}>Signals / metadata</div>
                        <div
                          style={{
                            background: palette.surface,
                            border: `1px solid ${palette.border}`,
                            borderRadius: 10,
                            padding: 10,
                            fontSize: 12,
                            color: palette.text,
                            display: "grid",
                            gridTemplateColumns: "repeat(auto-fit,minmax(180px,1fr))",
                            gap: 10,
                          }}
                        >
                          {["cache_hit", "rhythm", "persona", "tasks"].map((key) => (
                            <div key={key}>
                              <div style={{ color: palette.muted, fontSize: 11, marginBottom: 4 }}>{key}</div>
                              <pre style={{ margin: 0, whiteSpace: "pre-wrap", wordBreak: "break-word", lineHeight: 1.4 }}>
                                {safeStringify((liveTurn.llmDebug?.metadata as any)?.[key] ?? {})}
                              </pre>
                            </div>
                          ))}
                        </div>
                      </div>
                      <div>
                        <div style={{ color: palette.muted, fontSize: 12, marginBottom: 4 }}>Conversation context snapshot</div>
                        <pre
                          style={{
                            background: palette.surface,
                            border: `1px solid ${palette.border}`,
                            borderRadius: 10,
                            padding: 10,
                            fontSize: 12,
                            color: palette.text,
                            whiteSpace: "pre-wrap",
                            wordBreak: "break-word",
                            maxHeight: 220,
                            overflow: "auto",
                          }}
                        >
                          {safeStringify(liveTurn.llmDebug?.context_snapshot || {})}
                        </pre>
                      </div>
                    </div>

                    <div>
                      <div style={{ color: palette.muted, fontSize: 12, marginBottom: 4 }}>Journaling AI guidance</div>
                      <pre
                        style={{
                          background: palette.surface,
                          border: `1px solid ${palette.border}`,
                          borderRadius: 10,
                          padding: 10,
                          fontSize: 12,
                          color: palette.text,
                          whiteSpace: "pre-wrap",
                          wordBreak: "break-word",
                          maxHeight: 260,
                          overflow: "auto",
                        }}
                      >
                        {safeStringify(liveTurn.llmDebug?.journaling_ai || liveTurn.llmDebug?.metadata?.journaling_ai || {})}
                      </pre>
                    </div>

                    <div>
                      <div style={{ color: palette.muted, fontSize: 12, marginBottom: 4 }}>LLM prompt</div>
                      <pre
                        style={{
                          background: palette.surface,
                          border: `1px solid ${palette.border}`,
                          borderRadius: 10,
                          padding: 10,
                          fontSize: 12,
                          color: palette.text,
                          whiteSpace: "pre-wrap",
                          wordBreak: "break-word",
                          maxHeight: 260,
                          overflow: "auto",
                        }}
                      >
                        {safeStringify(liveTurn.llmDebug?.prompt || "")}
                      </pre>
                    </div>
                  </div>
                )}

                {liveTurn.raw && (
                  <>
                    <div style={{ color: palette.muted, fontSize: 12, marginTop: 12 }}>Turn payload (echo)</div>
                    <pre style={{ background: palette.surface, border: `1px solid ${palette.border}`, borderRadius: 10, padding: 10, fontSize: 12, color: palette.text, overflow: "auto", whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
                      {safeStringify(liveTurn.raw)}
                    </pre>
                    {liveTurn.jobIds?.length ? (
                      <div style={{ color: palette.muted, fontSize: 13, marginTop: 6 }}>
                        Jobs enqueued: {liveTurn.jobIds.join(", ")}
                      </div>
                    ) : (
                      <div style={{ color: palette.muted, fontSize: 13, marginTop: 6 }}>No job IDs returned.</div>
                    )}
                  </>
                )}
              </div>
            </div>
          </div>
        </div>

        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 12,
            borderTop: `1px solid ${palette.border}`,
            paddingTop: 14,
            background: "rgba(255,255,255,0.02)",
            borderRadius: 14,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
            <div style={{ fontWeight: 700, fontSize: 18 }}>Execution Timeline & Manual Runs</div>
            <button
              type="button"
              onClick={() => setShowDebugCards((v) => !v)}
              style={{
                background: showDebugCards ? "rgba(94,234,212,0.14)" : "rgba(255,255,255,0.06)",
                color: palette.text,
                border: `1px solid ${palette.border}`,
                borderRadius: 999,
                padding: "6px 12px",
                cursor: "pointer",
              }}
            >
              {showDebugCards ? "Hide details" : "Show details"}
            </button>
          </div>

          {showDebugCards && (
            <div style={{ display: "grid", gridTemplateColumns: "1.3fr 1fr", gap: 12 }}>
              <div style={cardStyle}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div style={{ fontWeight: 600 }}>Execution Timeline</div>
                  <div style={{ color: palette.muted, fontSize: 12 }}>Newest first</div>
                </div>
                {!timeline.length && <div style={{ color: palette.muted }}>No events yet. Run a live turn or worker to start.</div>}
                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                  {timeline.map((event) => (
                    <div
                      key={event.id}
                      style={{
                        border: `1px solid ${palette.border}`,
                        borderRadius: 10,
                        padding: 10,
                        background: "rgba(15,23,42,0.7)",
                      }}
                    >
                      <div style={{ fontSize: 13, color: palette.muted }}>{formatTime(event.timestamp)}</div>
                      <div style={{ fontWeight: 600, color: palette.text }}>{event.label}</div>
                      {event.detail && (
                        <div style={{ color: palette.muted, fontSize: 13, marginTop: 4 }}>
                          {event.detail}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                <div style={cardStyle}>
                  <div style={{ fontWeight: 600, marginBottom: 6 }}>Manual Worker Run</div>
                  {manualRun.status === "idle" && <div style={{ color: palette.muted, fontSize: 13 }}>Not run yet.</div>}
                  {manualRun.status === "running" && <div style={{ color: "#ffffff" }}>Running workers…</div>}
                  {manualRun.status === "error" && <div style={{ color: palette.danger }}>{manualRun.error}</div>}
                  {manualRun.raw && (
                    <pre style={{ background: palette.surface, border: `1px solid ${palette.border}`, borderRadius: 10, padding: 10, fontSize: 12, color: palette.text, overflow: "auto" }}>
                      {safeStringify(manualRun.raw)}
                    </pre>
                  )}
                </div>

                <div style={cardStyle}>
                  <div style={{ fontWeight: 600, marginBottom: 6 }}>Worker Output Contract</div>
                  <pre style={{ background: palette.surface, border: `1px solid ${palette.border}`, borderRadius: 10, padding: 10, fontSize: 12, color: palette.text }}>
{`{
  "worker": "memory",
  "inputs_used": ["journal_entries", "short_term_memory"],
  "writes": { "short_term_memory": 1, "long_term_memory": 0 },
  "signals": { "emotion": "mixed", "salience": ["work_pressure"] },
  "notes": "Detected repeated overextension language",
  "confidence": 0.64
}`}
                  </pre>
                  <div style={{ color: palette.muted, fontSize: 12, marginTop: 6 }}>
                    If a worker cannot explain itself, it is not v1-ready.
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 12,
            borderTop: `1px solid ${palette.border}`,
            paddingTop: 14,
            background: "rgba(255,255,255,0.02)",
            borderRadius: 14,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
            <div style={{ fontWeight: 700, fontSize: 18 }}>Worker Outputs (inspectable)</div>
            <button
              type="button"
              onClick={() => setShowOutputs((v) => !v)}
              style={{
                background: showOutputs ? "rgba(94,234,212,0.14)" : "rgba(255,255,255,0.06)",
                color: palette.text,
                border: `1px solid ${palette.border}`,
                borderRadius: 999,
                padding: "6px 12px",
                cursor: "pointer",
              }}
            >
              {showOutputs ? "Hide outputs" : "Show outputs"}
            </button>
          </div>
          {showOutputs && (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(340px,1fr))", gap: 12 }}>
              {workerPanels}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
