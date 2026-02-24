"use client";

import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import type {
  ArcPhase,
  GovernanceResult,
  ReplayData,
  ReplayEntry,
  ReplayFrictionState,
} from "@/app/demo/simulation/types";

// ---------------------------------------------------------------------------
// Palette (matches existing simulation page)
// ---------------------------------------------------------------------------

const palette = {
  bg: "#faf8f5",
  card: "#ffffff",
  cardAlt: "#f5f0eb",
  border: "#e8e0d8",
  text: "#2d2a26",
  muted: "#8a7f73",
  accent: "#c4703f",
  accentLight: "#f0e0d0",
  balanced: "#4caf7a",
  chaos: "#e05555",
  intensity: "#e6923a",
  stagnation: "#5b8db5",
  unknown: "#c4bdb5",
  vata: "#7baed6",
  pitta: "#e6923a",
  kapha: "#6ab573",
  journalBg: "#fdf8f3",
  sakhiBg: "#f3f7fb",
};

function frictionColor(state: string): string {
  switch (state) {
    case "balanced":
      return palette.balanced;
    case "chaos":
      return palette.chaos;
    case "intensity":
      return palette.intensity;
    case "stagnation":
      return palette.stagnation;
    default:
      return palette.unknown;
  }
}

// ---------------------------------------------------------------------------
// Persona definitions
// ---------------------------------------------------------------------------

const PERSONAS = [
  {
    id: "vidhya",
    label: "Vidhya",
    subtitle: "VP Ops \u00b7 Pitta-dominant",
    short: "Overcommitment & Rediscovery",
  },
  {
    id: "diya",
    label: "Diya",
    subtitle: "Student Athlete \u00b7 Kapha-dominant",
    short: "Discipline & Recovery",
  },
  {
    id: "bigd",
    label: "Big D",
    subtitle: "GM & Leader \u00b7 Kapha-dominant",
    short: "Leadership & Generosity",
  },
];

// ---------------------------------------------------------------------------
// Phase boundary helper
// ---------------------------------------------------------------------------

interface PhaseBoundary {
  start: number;
  end: number;
  phase: ArcPhase;
}

function computePhaseBoundaries(phases: ArcPhase[]): PhaseBoundary[] {
  const boundaries: PhaseBoundary[] = [];
  let cumulative = 0;
  for (const phase of phases) {
    boundaries.push({
      start: cumulative + 1,
      end: cumulative + phase.duration_days,
      phase,
    });
    cumulative += phase.duration_days;
  }
  return boundaries;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function PersonaSelector({
  selected,
  onChange,
}: {
  selected: string;
  onChange: (id: string) => void;
}) {
  return (
    <div style={{ display: "flex", gap: 8, marginBottom: 24 }}>
      {PERSONAS.map((p) => {
        const active = p.id === selected;
        return (
          <button
            key={p.id}
            onClick={() => onChange(p.id)}
            style={{
              flex: 1,
              padding: "12px 8px",
              border: active
                ? `2px solid ${palette.accent}`
                : `1px solid ${palette.border}`,
              borderRadius: 12,
              background: active ? palette.accentLight : palette.card,
              cursor: "pointer",
              textAlign: "center",
              transition: "all 0.15s",
            }}
          >
            <div
              style={{
                fontSize: 16,
                fontWeight: 700,
                color: active ? palette.accent : palette.text,
              }}
            >
              {p.label}
            </div>
            <div style={{ fontSize: 11, color: palette.muted, marginTop: 2 }}>
              {p.subtitle}
            </div>
          </button>
        );
      })}
    </div>
  );
}

function ReplayHeader({
  persona,
  totalDays,
}: {
  persona: ReplayData["persona"];
  totalDays: number;
}) {
  const arcDesc = persona.arc?.description || "";
  return (
    <div
      style={{
        background: palette.card,
        border: `1px solid ${palette.border}`,
        borderRadius: 12,
        padding: 24,
        marginBottom: 16,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "baseline",
          gap: 12,
          marginBottom: 8,
        }}
      >
        <span style={{ fontSize: 22, fontWeight: 700, color: palette.text }}>
          {persona.name}
        </span>
        <span style={{ fontSize: 13, color: palette.muted }}>
          {totalDays} days of journaling
        </span>
      </div>
      <div
        style={{
          fontSize: 14,
          color: palette.text,
          lineHeight: 1.6,
          marginBottom: 12,
        }}
      >
        {persona.description}
      </div>
      {arcDesc && (
        <div
          style={{
            fontSize: 13,
            color: palette.accent,
            fontStyle: "italic",
          }}
        >
          Arc: {arcDesc}
        </div>
      )}
      {/* Dosha baseline bars */}
      <div
        style={{
          display: "flex",
          gap: 16,
          marginTop: 12,
        }}
      >
        {(["vata", "pitta", "kapha"] as const).map((d) => {
          const val = persona.dosha_baseline[d];
          const color = palette[d];
          return (
            <div key={d} style={{ flex: 1 }}>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  fontSize: 11,
                  color: palette.muted,
                  marginBottom: 3,
                }}
              >
                <span style={{ textTransform: "capitalize" }}>{d}</span>
                <span>{Math.round(val * 100)}%</span>
              </div>
              <div
                style={{
                  height: 6,
                  borderRadius: 3,
                  background: palette.border,
                  overflow: "hidden",
                }}
              >
                <div
                  style={{
                    height: "100%",
                    width: `${val * 100}%`,
                    background: color,
                    borderRadius: 3,
                  }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ReplayTimeline({
  currentDay,
  totalDays,
  isPlaying,
  playSpeed,
  phaseBoundaries,
  currentFriction,
  onTogglePlay,
  onSpeedChange,
  onDayChange,
}: {
  currentDay: number;
  totalDays: number;
  isPlaying: boolean;
  playSpeed: number;
  phaseBoundaries: PhaseBoundary[];
  currentFriction: ReplayFrictionState | null;
  onTogglePlay: () => void;
  onSpeedChange: (speed: number) => void;
  onDayChange: (day: number) => void;
}) {
  const currentPhaseName = useMemo(() => {
    const pb = phaseBoundaries.find(
      (b) => currentDay >= b.start && currentDay <= b.end,
    );
    return pb ? pb.phase.name : null;
  }, [currentDay, phaseBoundaries]);

  const maxPhaseDay =
    phaseBoundaries.length > 0
      ? phaseBoundaries[phaseBoundaries.length - 1].end
      : totalDays;

  return (
    <div
      style={{
        position: "sticky",
        top: 0,
        zIndex: 50,
        background: palette.card,
        border: `1px solid ${palette.border}`,
        borderRadius: 12,
        padding: "16px 20px",
        marginBottom: 16,
        boxShadow: "0 4px 12px rgba(0,0,0,0.08)",
      }}
    >
      {/* Top row: day counter, phase, controls */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 12,
        }}
      >
        <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
          <span
            style={{ fontSize: 22, fontWeight: 700, color: palette.text }}
          >
            Day {currentDay || "\u2014"}
          </span>
          <span style={{ fontSize: 13, color: palette.muted }}>
            of {totalDays}
          </span>
          {currentPhaseName && (
            <span
              style={{
                fontSize: 12,
                color: palette.accent,
                fontWeight: 600,
                marginLeft: 4,
              }}
            >
              {currentPhaseName}
            </span>
          )}
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <button
            onClick={onTogglePlay}
            style={{
              padding: "6px 16px",
              borderRadius: 8,
              border: "none",
              background: isPlaying ? palette.muted : palette.accent,
              color: "#fff",
              fontWeight: 600,
              fontSize: 13,
              cursor: "pointer",
            }}
          >
            {isPlaying ? "\u23F8 Pause" : "\u25B6 Play"}
          </button>
          <select
            value={playSpeed}
            onChange={(e) => onSpeedChange(Number(e.target.value))}
            style={{
              padding: "6px 8px",
              borderRadius: 6,
              border: `1px solid ${palette.border}`,
              fontSize: 12,
              color: palette.text,
              background: palette.card,
              cursor: "pointer",
            }}
          >
            <option value={5000}>Slow</option>
            <option value={3000}>Normal</option>
            <option value={1500}>Fast</option>
            <option value={500}>Skim</option>
          </select>
        </div>
      </div>

      {/* Phase segments */}
      <div
        style={{
          display: "flex",
          height: 6,
          borderRadius: 3,
          overflow: "hidden",
          marginBottom: 6,
          background: palette.border,
        }}
      >
        {phaseBoundaries.map((pb, i) => {
          const widthPct = (pb.phase.duration_days / totalDays) * 100;
          const colors = [palette.accent, palette.pitta, palette.vata, palette.kapha];
          return (
            <div
              key={i}
              style={{
                width: `${widthPct}%`,
                background: colors[i % colors.length],
                opacity: 0.6,
              }}
            />
          );
        })}
        {/* Remaining days beyond defined phases */}
        {maxPhaseDay < totalDays && (
          <div
            style={{
              width: `${((totalDays - maxPhaseDay) / totalDays) * 100}%`,
              background: palette.muted,
              opacity: 0.3,
            }}
          />
        )}
      </div>

      {/* Scrubber */}
      <input
        type="range"
        min={0}
        max={totalDays}
        value={currentDay}
        onChange={(e) => onDayChange(Number(e.target.value))}
        style={{ width: "100%", cursor: "pointer" }}
      />

      {/* Drift indicator */}
      {currentFriction && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            marginTop: 8,
          }}
        >
          <span
            style={{
              padding: "2px 10px",
              borderRadius: 10,
              background: `${frictionColor(currentFriction.state)}18`,
              color: frictionColor(currentFriction.state),
              fontSize: 11,
              fontWeight: 600,
              textTransform: "capitalize",
            }}
          >
            {currentFriction.state}
          </span>
          <span style={{ fontSize: 11, color: palette.muted }}>
            drift: {currentFriction.drift_percentage}%
          </span>
          {currentFriction.primary_contributor && (
            <span style={{ fontSize: 11, color: palette.muted }}>
              \u00b7 {currentFriction.primary_contributor}
            </span>
          )}
        </div>
      )}
    </div>
  );
}

function PhaseMarker({
  phase,
  phaseIndex,
}: {
  phase: ArcPhase;
  phaseIndex: number;
}) {
  return (
    <div
      style={{
        background: palette.card,
        border: `1px solid ${palette.border}`,
        borderLeft: `4px solid ${palette.accent}`,
        borderRadius: 12,
        padding: "16px 20px",
        marginBottom: 16,
        marginTop: 24,
      }}
    >
      <div
        style={{
          fontSize: 11,
          color: palette.muted,
          textTransform: "uppercase",
          letterSpacing: 0.5,
          marginBottom: 4,
        }}
      >
        Phase {phaseIndex + 1}
      </div>
      <div
        style={{ fontSize: 18, fontWeight: 700, color: palette.text }}
      >
        {phase.name}
      </div>
      <div
        style={{
          fontSize: 13,
          color: palette.accent,
          fontStyle: "italic",
          marginTop: 4,
        }}
      >
        {phase.emotional_state}
      </div>
      {phase.themes && phase.themes.length > 0 && (
        <div
          style={{
            display: "flex",
            gap: 6,
            flexWrap: "wrap",
            marginTop: 8,
          }}
        >
          {phase.themes.map((t, i) => (
            <span
              key={i}
              style={{
                padding: "2px 8px",
                borderRadius: 8,
                background: palette.accentLight,
                fontSize: 11,
                color: palette.accent,
              }}
            >
              {t}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function DayDivider({
  day,
  timeOfDay,
}: {
  day: number;
  timeOfDay: string;
}) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 12,
        justifyContent: "center",
        margin: "20px 0 12px",
      }}
    >
      <div style={{ flex: 1, height: 1, background: palette.border }} />
      <span style={{ fontSize: 12, color: palette.muted, fontWeight: 500 }}>
        Day {day} \u00b7 {timeOfDay}
      </span>
      <div style={{ flex: 1, height: 1, background: palette.border }} />
    </div>
  );
}

function JournalBubble({
  content,
  personaName,
}: {
  content: string;
  personaName: string;
}) {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "flex-start",
        marginBottom: 12,
      }}
    >
      <div
        style={{
          maxWidth: "85%",
          padding: "16px 20px",
          background: palette.journalBg,
          borderRadius: "16px 16px 16px 4px",
          borderLeft: `3px solid ${palette.accent}`,
          fontSize: 14,
          color: palette.text,
          lineHeight: 1.7,
        }}
      >
        <div
          style={{
            fontSize: 11,
            fontWeight: 700,
            color: palette.accent,
            marginBottom: 8,
            textTransform: "uppercase",
            letterSpacing: 0.3,
          }}
        >
          {personaName}
        </div>
        <div style={{ whiteSpace: "pre-line" }}>{content}</div>
      </div>
    </div>
  );
}

function SakhiReplyBubble({ reply }: { reply: string }) {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "flex-end",
        marginBottom: 12,
      }}
    >
      <div
        style={{
          maxWidth: "85%",
          padding: "16px 20px",
          background: palette.sakhiBg,
          borderRadius: "16px 16px 4px 16px",
          borderRight: `3px solid ${palette.vata}`,
          fontSize: 14,
          color: palette.text,
          lineHeight: 1.7,
        }}
      >
        <div
          style={{
            fontSize: 11,
            fontWeight: 700,
            color: palette.vata,
            marginBottom: 8,
            textTransform: "uppercase",
            letterSpacing: 0.3,
          }}
        >
          Sakhi
        </div>
        <div style={{ whiteSpace: "pre-line" }}>{reply}</div>
      </div>
    </div>
  );
}

function DriftPill({
  frictionState,
}: {
  frictionState: ReplayFrictionState | undefined;
}) {
  if (!frictionState) return null;
  const color = frictionColor(frictionState.state);
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        gap: 8,
        margin: "8px 0 20px",
      }}
    >
      <span
        style={{
          padding: "2px 10px",
          borderRadius: 10,
          background: `${color}15`,
          color,
          fontSize: 11,
          fontWeight: 600,
          textTransform: "capitalize",
        }}
      >
        {frictionState.state}
      </span>
      <span style={{ fontSize: 11, color: palette.muted }}>
        drift: {frictionState.drift_percentage}%
      </span>
    </div>
  );
}

function GovernanceGateCard({
  scenario,
  result,
  personaName,
}: {
  scenario: { user_text: string; proposed_action: string };
  result: GovernanceResult;
  personaName: string;
}) {
  const actionColor = result.requires_confirmation
    ? palette.intensity
    : result.is_blocked
      ? palette.chaos
      : palette.balanced;
  const actionLabel = result.requires_confirmation
    ? "Requires Confirmation"
    : result.is_blocked
      ? "Blocked"
      : "Allowed";

  return (
    <div
      style={{
        background: palette.card,
        border: `2px solid ${actionColor}`,
        borderRadius: 16,
        padding: 28,
        marginTop: 32,
      }}
    >
      <div
        style={{
          fontSize: 11,
          color: actionColor,
          fontWeight: 700,
          textTransform: "uppercase",
          letterSpacing: 0.8,
        }}
      >
        Constitution Gate
      </div>
      <div
        style={{
          fontSize: 18,
          fontWeight: 700,
          color: palette.text,
          marginTop: 8,
          lineHeight: 1.4,
        }}
      >
        After 30 days of understanding {personaName}\u2026
      </div>

      {/* Scenario quote */}
      <div
        style={{
          padding: 16,
          background: palette.cardAlt,
          borderRadius: 10,
          margin: "16px 0",
          fontSize: 14,
          fontStyle: "italic",
          color: palette.text,
          lineHeight: 1.6,
          borderLeft: `3px solid ${palette.muted}`,
        }}
      >
        \u201C{scenario.user_text}\u201D
      </div>

      {/* Decision badge */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          marginBottom: 16,
        }}
      >
        <span
          style={{
            padding: "5px 14px",
            borderRadius: 8,
            background: `${actionColor}18`,
            color: actionColor,
            fontWeight: 700,
            fontSize: 14,
          }}
        >
          {actionLabel}
        </span>
      </div>

      {/* Violations */}
      {result.violations.map((v, i) => (
        <div
          key={i}
          style={{
            padding: 14,
            background: `${palette.chaos}08`,
            borderRadius: 10,
            borderLeft: `3px solid ${palette.chaos}`,
            marginBottom: 8,
            fontSize: 13,
            color: palette.text,
            lineHeight: 1.5,
          }}
        >
          <div style={{ fontWeight: 600, marginBottom: 4 }}>
            {v.description}
          </div>
          <div style={{ fontSize: 12, color: palette.muted }}>
            {v.message}
          </div>
        </div>
      ))}

      {/* Narrative */}
      <div
        style={{
          fontSize: 13,
          color: palette.muted,
          marginTop: 16,
          lineHeight: 1.6,
        }}
      >
        Sakhi knows {personaName} well enough to protect them from their own
        patterns. The Constitution Gate uses 30 days of accumulated
        understanding to evaluate whether this commitment aligns with their
        goals.
      </div>
    </div>
  );
}

function IntroScreen({ onStart }: { onStart: () => void }) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        minHeight: 300,
        textAlign: "center",
        gap: 16,
      }}
    >
      <div style={{ fontSize: 48, opacity: 0.3 }}>{"\u{1F4D6}"}</div>
      <div style={{ fontSize: 20, fontWeight: 700, color: palette.text }}>
        Ready to replay 30 days
      </div>
      <div
        style={{
          fontSize: 14,
          color: palette.muted,
          maxWidth: 400,
          lineHeight: 1.6,
        }}
      >
        Watch the conversation unfold day by day. See how Sakhi&apos;s
        responses evolve as understanding deepens.
      </div>
      <button
        onClick={onStart}
        style={{
          padding: "12px 32px",
          borderRadius: 12,
          border: "none",
          background: palette.accent,
          color: "#fff",
          fontWeight: 700,
          fontSize: 15,
          cursor: "pointer",
          marginTop: 8,
        }}
      >
        Start Replay
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main ReplayClient
// ---------------------------------------------------------------------------

export default function ReplayClient() {
  const [personaId, setPersonaId] = useState("vidhya");
  const [data, setData] = useState<ReplayData | null>(null);
  const [loading, setLoading] = useState(true);
  // Step-based: 0=intro, then each entry has 2 steps (journal, reply)
  // step 1 = entry[0] journal, step 2 = entry[0] reply,
  // step 3 = entry[1] journal, step 4 = entry[1] reply, etc.
  // Final step = governance card
  const [step, setStep] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playSpeed, setPlaySpeed] = useState(3000);

  const latestRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Total steps: 2 per entry (journal + reply) + 1 for governance
  const totalSteps = data ? data.entries.length * 2 + 1 : 0;

  // Derive current day and whether reply is visible from step
  const currentEntryIndex = step > 0 ? Math.floor((step - 1) / 2) : -1;
  const showReplyForCurrent = step > 0 && (step - 1) % 2 === 1;
  const showGovernance = step > 0 && step >= totalSteps;
  const currentDay =
    currentEntryIndex >= 0 && data
      ? (data.entries[Math.min(currentEntryIndex, data.entries.length - 1)]
          ?.day ?? 0)
      : 0;

  // ---- Data loading ----
  useEffect(() => {
    setLoading(true);
    setStep(0);
    setIsPlaying(false);
    fetch(`/simulation/${personaId}.json`)
      .then((res) => res.json())
      .then((result: ReplayData) => {
        setData(result);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [personaId]);

  // ---- Phase boundaries ----
  const phaseBoundaries = useMemo<PhaseBoundary[]>(() => {
    if (!data) return [];
    return computePhaseBoundaries(data.persona.arc.phases);
  }, [data]);

  // ---- Visible entries with reply visibility ----
  const visibleMessages = useMemo(() => {
    if (!data || step === 0) return [];
    const msgs: Array<{
      entry: ReplayEntry;
      entryIndex: number;
      showReply: boolean;
      isLatest: boolean;
    }> = [];
    // All entries up to current, with full reply shown for all except maybe the latest
    const lastVisibleIndex = currentEntryIndex;
    for (let i = 0; i <= lastVisibleIndex && i < data.entries.length; i++) {
      const isLast = i === lastVisibleIndex;
      msgs.push({
        entry: data.entries[i],
        entryIndex: i,
        showReply: isLast ? showReplyForCurrent : true,
        isLatest: isLast,
      });
    }
    return msgs;
  }, [data, step, currentEntryIndex, showReplyForCurrent]);

  // ---- Current friction from snapshot (more accurate than entry) ----
  const currentFriction = useMemo<ReplayFrictionState | null>(() => {
    if (!data || currentDay === 0) return null;
    const snap = data.snapshots?.find((s) => s.day === currentDay);
    if (snap?.friction_state?.friction) {
      const f = snap.friction_state.friction;
      return {
        state: f.state,
        description: f.description,
        drift_percentage: f.drift_percentage,
        drift_direction: "elevated",
        primary_contributor:
          snap.friction_state.drift?.primary_contributor || "",
      };
    }
    const entry = data.entries.find((e) => e.day === currentDay);
    return entry?.friction_state || null;
  }, [data, currentDay]);

  // ---- Auto-play ----
  useEffect(() => {
    if (!isPlaying || !data) return;
    const timer = setInterval(() => {
      setStep((s) => {
        const next = s + 1;
        if (next > totalSteps) {
          setIsPlaying(false);
          return totalSteps; // show governance
        }
        return next;
      });
    }, playSpeed);
    return () => clearInterval(timer);
  }, [isPlaying, playSpeed, data, totalSteps]);

  // ---- Auto-scroll ----
  useEffect(() => {
    if (latestRef.current && step > 0) {
      latestRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [step]);

  // ---- Keyboard ----
  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (!data) return;
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLSelectElement
      )
        return;
      switch (e.key) {
        case " ":
          e.preventDefault();
          setIsPlaying((p) => !p);
          break;
        case "ArrowRight":
          e.preventDefault();
          setStep((s) => Math.min(s + 1, totalSteps));
          break;
        case "ArrowLeft":
          e.preventDefault();
          setStep((s) => Math.max(s - 1, 0));
          break;
        case "Home":
          e.preventDefault();
          setStep(0);
          break;
        case "End":
          e.preventDefault();
          setStep(totalSteps);
          break;
      }
    }
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [data, totalSteps]);

  // ---- Handlers ----
  const handleTogglePlay = useCallback(() => {
    if (!data) return;
    if (step === 0) {
      setStep(1);
      setIsPlaying(true);
    } else if (step >= totalSteps && !isPlaying) {
      // Restart
      setStep(1);
      setIsPlaying(true);
    } else {
      setIsPlaying((p) => !p);
    }
  }, [data, step, isPlaying, totalSteps]);

  // Map scrubber day to step: jump to the journal step for that day
  const handleDayChange = useCallback(
    (day: number) => {
      if (!data || day === 0) {
        setStep(0);
        setIsPlaying(false);
        return;
      }
      // Find the entry index for this day, then compute its reply step
      const idx = data.entries.findIndex((e) => e.day >= day);
      if (idx >= 0) {
        setStep(idx * 2 + 2); // show journal + reply for that day
      }
      setIsPlaying(false);
    },
    [data],
  );

  const handleStart = useCallback(() => {
    setStep(1);
    setIsPlaying(true);
  }, []);

  // ---- Determine which phases need markers ----
  const phaseStartDays = useMemo(() => {
    const map = new Map<number, { phase: ArcPhase; index: number }>();
    phaseBoundaries.forEach((pb, idx) => {
      map.set(pb.start, { phase: pb.phase, index: idx });
    });
    return map;
  }, [phaseBoundaries]);

  // ---- Render ----
  if (loading) {
    return (
      <div
        style={{
          minHeight: "100vh",
          background: palette.bg,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: palette.muted,
          fontSize: 16,
        }}
      >
        Loading {personaId}\u2026
      </div>
    );
  }

  if (!data) {
    return (
      <div
        style={{
          minHeight: "100vh",
          background: palette.bg,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: palette.chaos,
          fontSize: 16,
        }}
      >
        Failed to load simulation data.
      </div>
    );
  }

  const personaName = data.persona.name;

  return (
    <div
      ref={containerRef}
      style={{
        minHeight: "100vh",
        background: palette.bg,
        fontFamily:
          '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      }}
    >
      <div
        style={{
          maxWidth: 720,
          margin: "0 auto",
          padding: "24px 20px 80px",
        }}
      >
        {/* Persona selector */}
        <PersonaSelector selected={personaId} onChange={setPersonaId} />

        {/* Header */}
        <ReplayHeader persona={data.persona} totalDays={data.total_days} />

        {/* Timeline controls */}
        {step > 0 && (
          <ReplayTimeline
            currentDay={currentDay}
            totalDays={data.total_days}
            isPlaying={isPlaying}
            playSpeed={playSpeed}
            phaseBoundaries={phaseBoundaries}
            currentFriction={currentFriction}
            onTogglePlay={handleTogglePlay}
            onSpeedChange={setPlaySpeed}
            onDayChange={handleDayChange}
          />
        )}

        {/* Intro screen or conversation */}
        {step === 0 ? (
          <IntroScreen onStart={handleStart} />
        ) : (
          <div>
            {/* Conversation messages — one at a time */}
            {visibleMessages.map((msg, idx) => {
              const prevDay =
                idx > 0 ? visibleMessages[idx - 1].entry.day : 0;
              const isNewDay = msg.entry.day !== prevDay;
              const phaseInfo = phaseStartDays.get(msg.entry.day);

              // Get snapshot friction for this day (more accurate)
              const snap = data.snapshots?.find(
                (s) => s.day === msg.entry.day,
              );
              const snapFriction: ReplayFrictionState | undefined =
                snap?.friction_state?.friction
                  ? {
                      state: snap.friction_state.friction.state,
                      drift_percentage:
                        snap.friction_state.friction.drift_percentage,
                      primary_contributor:
                        snap.friction_state.drift?.primary_contributor,
                    }
                  : msg.entry.friction_state;

              return (
                <div key={`${msg.entry.day}-${msg.entryIndex}`}>
                  {/* Phase marker (if new phase starts on this day) */}
                  {isNewDay && phaseInfo && (
                    <PhaseMarker
                      phase={phaseInfo.phase}
                      phaseIndex={phaseInfo.index}
                    />
                  )}

                  {/* Day divider */}
                  {isNewDay && (
                    <DayDivider
                      day={msg.entry.day}
                      timeOfDay={msg.entry.time_of_day}
                    />
                  )}

                  {/* Journal entry — always visible once this entry is reached */}
                  <div
                    ref={
                      msg.isLatest && !msg.showReply ? latestRef : undefined
                    }
                  >
                    <JournalBubble
                      content={msg.entry.content}
                      personaName={personaName}
                    />
                  </div>

                  {/* Sakhi reply — only visible on the reply step */}
                  {msg.showReply && msg.entry.reply && (
                    <div ref={msg.isLatest ? latestRef : undefined}>
                      <SakhiReplyBubble reply={msg.entry.reply} />
                    </div>
                  )}

                  {/* Drift indicator — shown after reply is visible */}
                  {msg.showReply && <DriftPill frictionState={snapFriction} />}
                </div>
              );
            })}

            {/* Governance gate (appears as the final step) */}
            {showGovernance &&
              data.governance_result &&
              data.persona.governance_scenario && (
                <div ref={latestRef}>
                  <GovernanceGateCard
                    scenario={data.persona.governance_scenario}
                    result={data.governance_result}
                    personaName={personaName}
                  />
                </div>
              )}

            {/* End marker */}
            {showGovernance && (
              <div
                style={{
                  textAlign: "center",
                  margin: "32px 0",
                  color: palette.muted,
                  fontSize: 13,
                }}
              >
                End of {data.total_days}-day replay
                <div style={{ marginTop: 12 }}>
                  <button
                    onClick={() => {
                      setStep(0);
                      window.scrollTo({ top: 0, behavior: "smooth" });
                    }}
                    style={{
                      padding: "8px 20px",
                      borderRadius: 8,
                      border: `1px solid ${palette.border}`,
                      background: palette.card,
                      color: palette.text,
                      fontSize: 13,
                      cursor: "pointer",
                    }}
                  >
                    Restart
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Keyboard hint */}
        <div
          style={{
            textAlign: "center",
            fontSize: 11,
            color: palette.muted,
            marginTop: 32,
            opacity: 0.6,
          }}
        >
          Space: play/pause \u00b7 \u2190\u2192: step \u00b7 Home/End: jump
        </div>
      </div>
    </div>
  );
}
