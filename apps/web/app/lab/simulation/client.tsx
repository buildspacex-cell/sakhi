"use client";

import React, { useState, useEffect, useMemo, useCallback } from "react";
// Recharts v2 types don't fully match React 18 JSX types — cast to any
import {
  AreaChart as _AreaChart,
  Area as _Area,
  LineChart as _LineChart,
  Line as _Line,
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
} from "recharts";
const AreaChart = _AreaChart as any;
const Area = _Area as any;
const LineChart = _LineChart as any;
const Line = _Line as any;
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
import type {
  SimulationData,
  StateSnapshot,
  ArcPhase,
  PhaseBoundary,
  CheckpointResult,
  JournalEntry,
} from "./types";

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

// ============================================================================
// Main Client Component
// ============================================================================

export default function SimulationDemoClient() {
  const [personaId, setPersonaId] = useState<string>("anxious_achiever");
  const [data, setData] = useState<SimulationData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Timeline
  const [currentDay, setCurrentDay] = useState(1);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playSpeed, setPlaySpeed] = useState(400);

  // Narration mode — auto-pauses at phase transitions + checkpoints
  const [narrateMode, setNarrateMode] = useState(true);
  const [pauseReason, setPauseReason] = useState<string | null>(null);

  // Load data
  useEffect(() => {
    setLoading(true);
    setError(null);
    setCurrentDay(1);
    setIsPlaying(false);

    fetch(`/simulation/${personaId}.json`)
      .then((res) => {
        if (!res.ok) throw new Error("Failed to load simulation data");
        return res.json();
      })
      .then((result: SimulationData) => {
        setData(result);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, [personaId]);

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

  // Normalized growth chart data (0-100% for each metric)
  const growthChartData = useMemo(() => {
    if (!data) return [];
    return data.snapshots
      .filter((s) => s.day <= currentDay)
      .map((s) => ({
        day: s.day,
        memories: Math.round(
          ((s.memory_count ?? 0) / finalStats.mem) * 100,
        ),
        patterns: Math.round(
          ((s.pattern_count ?? 0) / finalStats.pat) * 100,
        ),
        nodes: Math.round(
          ((s.provenance?.graph_nodes ?? 0) / finalStats.nodes) * 100,
        ),
        edges: Math.round(
          ((s.provenance?.graph_edges ?? 0) / finalStats.edges) * 100,
        ),
      }));
  }, [data, currentDay, finalStats]);

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

  // Keyboard navigation
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "ArrowRight")
        setCurrentDay((d) => Math.min(d + 1, data?.total_days ?? d));
      if (e.key === "ArrowLeft") setCurrentDay((d) => Math.max(d - 1, 1));
      if (e.key === " ") {
        e.preventDefault();
        setIsPlaying((p) => !p);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [data]);

  if (loading) {
    return (
      <div
        style={{
          ...styles.page,
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          minHeight: "100vh",
        }}
      >
        <div style={{ color: palette.muted, fontSize: 18 }}>
          Loading simulation...
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div
        style={{
          ...styles.page,
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          minHeight: "100vh",
        }}
      >
        <div style={{ color: palette.chaos, fontSize: 18 }}>
          {error || "No data available"}
        </div>
      </div>
    );
  }

  return (
    <div style={styles.page}>
      {/* 1. Header + Real Data Badge */}
      <div style={styles.header}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 12,
          }}
        >
          <h1 style={styles.title}>How Understanding Deepens</h1>
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
          Watch Sakhi build a complete picture of someone over 2 months of
          journaling
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

      {/* 3.5 Current Friction State - shows REAL computed state from simulation */}
      <CurrentFrictionState
        currentSnapshot={currentSnapshot}
        persona={data.persona}
        currentDay={currentDay}
      />

      {/* 3.6 Personalization Demo - LLM-generated recommendations */}
      <PersonalizationDemo
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

      {/* 6. Intelligence Growth Chart — THE CENTERPIECE */}
      <IntelligenceGrowthChart
        chartData={growthChartData}
        phaseBoundaries={phaseBoundaries}
        currentDay={currentDay}
        finalStats={finalStats}
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

      {/* 10. Checkpoint Cards */}
      <CheckpointCards
        checkpoints={data.persona.checkpoints}
        results={data.checkpoint_results}
        currentDay={currentDay}
        onJumpToDay={setCurrentDay}
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
          paddingBottom: 48,
        }}
      >
        Simulated {data.total_days} days &middot; {data.total_entries} journal
        entries
        {data.real_pipeline && " \u00b7 Real Worker Pipeline"}
      </div>
    </div>
  );
}

// ============================================================================
// Sub-Components
// ============================================================================

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
    { id: "anxious_achiever", label: "Maya", subtitle: "Burnout & Recovery", prakruti: "Pitta-dominant" },
    { id: "stuck_creative", label: "Alex", subtitle: "Stagnation & Awakening", prakruti: "Kapha-Pitta" },
    { id: "hormonal_harmony", label: "Diya", subtitle: "Cycle Awareness", prakruti: "Kapha-Vata" },
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

// ============================================================================
// Personalization Comparison - Side-by-side LLM recommendations for Maya vs Diya
// ============================================================================

const SYMPTOM_OPTIONS = [
  "Feeling tired and low energy",
  "Feeling anxious and scattered",
  "Trouble sleeping",
  "Overwhelmed by workload",
];

// Fixed prakruti for comparison
const MAYA_PRAKRUTI = { vata: 0.25, pitta: 0.50, kapha: 0.25 };
const DIYA_PRAKRUTI = { vata: 0.30, pitta: 0.20, kapha: 0.50 };

interface LLMRecommendation {
  action: string;
  details?: {
    what: string;
    when: string;
    how: string;
  };
  why: string;
  category: string;
}

interface LLMRecommendationResponse {
  constitution: {
    dominant: string;
    secondary: string;
    type: string;
    vata: number;
    pitta: number;
    kapha: number;
  };
  friction_state: string;
  recommendations: LLMRecommendation[];
  pattern_insight?: {
    pattern: string;
    suggestion: string;
  };
  source: string;
}

function PersonalizationDemo({
  persona,
  currentDay,
}: {
  persona: SimulationData["persona"];
  currentDay: number;
}) {
  const [selectedSymptom, setSelectedSymptom] = useState(0);
  const [mayaResponse, setMayaResponse] = useState<LLMRecommendationResponse | null>(null);
  const [diyaResponse, setDiyaResponse] = useState<LLMRecommendationResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isMaya = persona.id === "anxious_achiever";
  const isDiya = persona.id === "hormonal_harmony";

  // Only show after day 7
  if (currentDay < 7) return null;

  const fetchBothRecommendations = async () => {
    setIsLoading(true);
    setError(null);

    const symptom = SYMPTOM_OPTIONS[selectedSymptom];

    try {
      // Fetch both in parallel
      const [mayaRes, diyaRes] = await Promise.all([
        fetch("/api/friction/recommendations/by-constitution", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ...MAYA_PRAKRUTI, symptom }),
        }),
        fetch("/api/friction/recommendations/by-constitution", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ...DIYA_PRAKRUTI, symptom }),
        }),
      ]);

      if (!mayaRes.ok || !diyaRes.ok) {
        throw new Error("Failed to get recommendations");
      }

      const [mayaData, diyaData] = await Promise.all([
        mayaRes.json(),
        diyaRes.json(),
      ]);

      setMayaResponse(mayaData);
      setDiyaResponse(diyaData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setIsLoading(false);
    }
  };

  const hasResults = mayaResponse && diyaResponse;
  const source = mayaResponse?.source || "none";

  return (
    <div style={{ ...styles.card, marginBottom: 24, borderLeft: `4px solid ${palette.accent}` }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
        <div>
          <div style={{ fontSize: 15, fontWeight: 600, color: palette.text }}>
            Personalization in Action
          </div>
          <div style={{ fontSize: 12, color: palette.muted, marginTop: 2 }}>
            Same symptom, different advice — real LLM-generated based on constitution
          </div>
        </div>
        <span
          style={{
            padding: "4px 10px",
            background: source === "llm" ? "#e3f2fd" : "#e8f5e9",
            borderRadius: 6,
            color: source === "llm" ? "#1976d2" : palette.balanced,
            fontWeight: 600,
            fontSize: 11,
          }}
        >
          {source === "llm" ? "LLM Powered" : "Why Sakhi is Different"}
        </span>
      </div>

      {/* Symptom selector */}
      <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
        {SYMPTOM_OPTIONS.map((symptom, i) => (
          <button
            key={i}
            onClick={() => {
              setSelectedSymptom(i);
              setMayaResponse(null);
              setDiyaResponse(null);
            }}
            style={{
              padding: "6px 12px",
              border: `1px solid ${selectedSymptom === i ? palette.accent : palette.border}`,
              borderRadius: 20,
              background: selectedSymptom === i ? palette.accentLight : palette.card,
              color: selectedSymptom === i ? palette.accent : palette.muted,
              fontSize: 12,
              cursor: "pointer",
              fontWeight: selectedSymptom === i ? 600 : 400,
            }}
          >
            {symptom}
          </button>
        ))}
      </div>

      {/* Generate button */}
      <button
        onClick={fetchBothRecommendations}
        disabled={isLoading}
        style={{
          padding: "10px 20px",
          background: isLoading ? palette.muted : palette.accent,
          color: "#fff",
          border: "none",
          borderRadius: 8,
          fontSize: 13,
          fontWeight: 600,
          cursor: isLoading ? "not-allowed" : "pointer",
          marginBottom: 16,
        }}
      >
        {isLoading ? "Generating personalized advice..." : "Compare Maya vs Diya"}
      </button>

      {/* Error */}
      {error && (
        <div style={{ padding: 12, background: "#ffebee", borderRadius: 8, color: "#c62828", fontSize: 12, marginBottom: 16 }}>
          {error}. Make sure the Python backend is running on port 8080.
        </div>
      )}

      {/* Side-by-side comparison */}
      {hasResults && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
          {/* Maya (Pitta) */}
          <div
            style={{
              padding: 16,
              borderRadius: 12,
              background: isMaya ? palette.accentLight : palette.cardAlt,
              border: isMaya ? `2px solid ${palette.accent}` : `1px solid ${palette.border}`,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
              <div
                style={{
                  width: 32,
                  height: 32,
                  borderRadius: "50%",
                  background: palette.pitta,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "#fff",
                  fontWeight: 700,
                  fontSize: 14,
                }}
              >
                M
              </div>
              <div>
                <div style={{ fontWeight: 600, fontSize: 14, color: palette.text }}>Maya</div>
                <div style={{ fontSize: 11, color: palette.muted }}>
                  {mayaResponse.constitution.type} (50% Pitta)
                </div>
              </div>
              {isMaya && (
                <span style={{ marginLeft: "auto", fontSize: 10, color: palette.accent, fontWeight: 600 }}>
                  CURRENT
                </span>
              )}
            </div>

            <div style={{ marginBottom: 10 }}>
              <span
                style={{
                  fontSize: 10,
                  padding: "2px 8px",
                  background: palette.pitta,
                  color: "#fff",
                  borderRadius: 10,
                  fontWeight: 600,
                }}
              >
                {mayaResponse.friction_state}
              </span>
            </div>

            {/* First recommendation */}
            {mayaResponse.recommendations[0] && (
              <>
                <div style={{ fontSize: 13, color: palette.text, lineHeight: 1.6, marginBottom: 8 }}>
                  <strong>Advice:</strong> {mayaResponse.recommendations[0].action}
                </div>

                {/* Details: What, When, How */}
                {mayaResponse.recommendations[0].details && (
                  <div style={{
                    fontSize: 11,
                    color: palette.text,
                    lineHeight: 1.6,
                    marginBottom: 10,
                    padding: "10px 12px",
                    background: "rgba(255,255,255,0.7)",
                    borderRadius: 8,
                    borderLeft: `3px solid ${palette.pitta}`,
                  }}>
                    <div style={{ marginBottom: 6 }}>
                      <strong style={{ color: palette.pitta }}>What:</strong>{" "}
                      {mayaResponse.recommendations[0].details.what}
                    </div>
                    <div style={{ marginBottom: 6 }}>
                      <strong style={{ color: palette.pitta }}>When:</strong>{" "}
                      {mayaResponse.recommendations[0].details.when}
                    </div>
                    <div>
                      <strong style={{ color: palette.pitta }}>How:</strong>{" "}
                      {mayaResponse.recommendations[0].details.how}
                    </div>
                  </div>
                )}

                <div
                  style={{
                    fontSize: 11,
                    color: palette.muted,
                    lineHeight: 1.5,
                    padding: "8px 10px",
                    background: "rgba(255,255,255,0.5)",
                    borderRadius: 6,
                    fontStyle: "italic",
                  }}
                >
                  <strong>Why:</strong> {mayaResponse.recommendations[0].why}
                </div>
              </>
            )}
          </div>

          {/* Diya (Kapha) */}
          <div
            style={{
              padding: 16,
              borderRadius: 12,
              background: isDiya ? palette.accentLight : palette.cardAlt,
              border: isDiya ? `2px solid ${palette.accent}` : `1px solid ${palette.border}`,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
              <div
                style={{
                  width: 32,
                  height: 32,
                  borderRadius: "50%",
                  background: palette.kapha,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "#fff",
                  fontWeight: 700,
                  fontSize: 14,
                }}
              >
                D
              </div>
              <div>
                <div style={{ fontWeight: 600, fontSize: 14, color: palette.text }}>Diya</div>
                <div style={{ fontSize: 11, color: palette.muted }}>
                  {diyaResponse.constitution.type} (50% Kapha)
                </div>
              </div>
              {isDiya && (
                <span style={{ marginLeft: "auto", fontSize: 10, color: palette.accent, fontWeight: 600 }}>
                  CURRENT
                </span>
              )}
            </div>

            <div style={{ marginBottom: 10 }}>
              <span
                style={{
                  fontSize: 10,
                  padding: "2px 8px",
                  background: palette.kapha,
                  color: "#fff",
                  borderRadius: 10,
                  fontWeight: 600,
                }}
              >
                {diyaResponse.friction_state}
              </span>
            </div>

            {/* First recommendation */}
            {diyaResponse.recommendations[0] && (
              <>
                <div style={{ fontSize: 13, color: palette.text, lineHeight: 1.6, marginBottom: 8 }}>
                  <strong>Advice:</strong> {diyaResponse.recommendations[0].action}
                </div>

                {/* Details: What, When, How */}
                {diyaResponse.recommendations[0].details && (
                  <div style={{
                    fontSize: 11,
                    color: palette.text,
                    lineHeight: 1.6,
                    marginBottom: 10,
                    padding: "10px 12px",
                    background: "rgba(255,255,255,0.7)",
                    borderRadius: 8,
                    borderLeft: `3px solid ${palette.kapha}`,
                  }}>
                    <div style={{ marginBottom: 6 }}>
                      <strong style={{ color: palette.kapha }}>What:</strong>{" "}
                      {diyaResponse.recommendations[0].details.what}
                    </div>
                    <div style={{ marginBottom: 6 }}>
                      <strong style={{ color: palette.kapha }}>When:</strong>{" "}
                      {diyaResponse.recommendations[0].details.when}
                    </div>
                    <div>
                      <strong style={{ color: palette.kapha }}>How:</strong>{" "}
                      {diyaResponse.recommendations[0].details.how}
                    </div>
                  </div>
                )}

                <div
                  style={{
                    fontSize: 11,
                    color: palette.muted,
                    lineHeight: 1.5,
                    padding: "8px 10px",
                    background: "rgba(255,255,255,0.5)",
                    borderRadius: 6,
                    fontStyle: "italic",
                  }}
                >
                  <strong>Why:</strong> {diyaResponse.recommendations[0].why}
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* Bottom insight */}
      <div
        style={{
          marginTop: 16,
          padding: "12px 16px",
          background: palette.cardAlt,
          borderRadius: 8,
          fontSize: 12,
          color: palette.muted,
          textAlign: "center",
        }}
      >
        <strong style={{ color: palette.text }}>Generic health apps give everyone the same advice.</strong>
        {" "}Sakhi uses {source === "llm" ? "real LLM + Ayurvedic reasoning" : "constitution-aware logic"} to tailor recommendations to YOUR body.
      </div>
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
// NEW: Intelligence Growth Chart — THE CENTERPIECE
// ============================================================================

function IntelligenceGrowthChart({
  chartData,
  phaseBoundaries,
  currentDay,
  finalStats,
}: {
  chartData: Array<{
    day: number;
    memories: number;
    patterns: number;
    nodes: number;
    edges: number;
  }>;
  phaseBoundaries: PhaseBoundary[];
  currentDay: number;
  finalStats: { mem: number; pat: number; nodes: number; edges: number };
}) {
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
        Sakhi&apos;s Understanding Over Time
      </div>
      <div
        style={{ fontSize: 12, color: palette.muted, marginBottom: 16 }}
      >
        Four dimensions of understanding, normalized to show relative growth
      </div>
      <ResponsiveContainer width="100%" height={320}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke={palette.border} />
          <XAxis dataKey="day" stroke={palette.muted} fontSize={11} />
          <YAxis
            stroke={palette.muted}
            fontSize={11}
            domain={[0, 100]}
            tickFormatter={(v: number) => `${v}%`}
          />
          <RTooltip
            contentStyle={{
              background: palette.card,
              border: `1px solid ${palette.border}`,
              borderRadius: 8,
              fontSize: 12,
            }}
            formatter={(value: number, name: string) => {
              const labels: Record<string, string> = {
                memories: "Episodic Memories",
                patterns: "Patterns Detected",
                nodes: "Knowledge Nodes",
                edges: "Connections",
              };
              return [`${value}%`, labels[name] ?? name];
            }}
            labelFormatter={(day: number) => `Day ${day}`}
          />
          {/* Phase boundary lines */}
          {phaseBoundaries.slice(1).map((b) =>
            b.start <= currentDay ? (
              <ReferenceLine
                key={b.start}
                x={b.start}
                stroke={palette.muted}
                strokeDasharray="4 4"
                strokeOpacity={0.3}
              />
            ) : null,
          )}
          <Line
            type="monotone"
            dataKey="memories"
            stroke={palette.memories}
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
          <Line
            type="monotone"
            dataKey="patterns"
            stroke={palette.patterns}
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
          <Line
            type="monotone"
            dataKey="nodes"
            stroke={palette.nodes}
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
          <Line
            type="monotone"
            dataKey="edges"
            stroke={palette.edges}
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
      <div
        style={{
          display: "flex",
          gap: 16,
          justifyContent: "center",
          marginTop: 8,
        }}
      >
        <LegendDot
          color={palette.memories}
          label={`Memories (${finalStats.mem})`}
        />
        <LegendDot
          color={palette.patterns}
          label={`Patterns (${finalStats.pat})`}
        />
        <LegendDot
          color={palette.nodes}
          label={`Nodes (${finalStats.nodes})`}
        />
        <LegendDot
          color={palette.edges}
          label={`Edges (${finalStats.edges})`}
        />
      </div>
    </div>
  );
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
