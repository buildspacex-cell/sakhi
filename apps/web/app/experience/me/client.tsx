"use client";

import { useSearchParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

// ─────────────────────────────────────────────────────────────
// Inline SVG Icons
// ─────────────────────────────────────────────────────────────
const IconArrowLeft = ({ size = 24 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M19 12H5M12 19l-7-7 7-7" />
  </svg>
);

const IconUser = ({ size = 18 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="8" r="4" />
    <path d="M4 20c0-4.4 3.6-8 8-8s8 3.6 8 8" />
  </svg>
);

const IconZap = ({ size = 18 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
  </svg>
);

const IconMoon = ({ size = 14 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
  </svg>
);

const IconSun = ({ size = 14 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="5" />
    <line x1="12" y1="1" x2="12" y2="3" />
    <line x1="12" y1="21" x2="12" y2="23" />
    <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
    <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
    <line x1="1" y1="12" x2="3" y2="12" />
    <line x1="21" y1="12" x2="23" y2="12" />
    <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
    <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
  </svg>
);

const IconBrain = ({ size = 18 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96.44 2.5 2.5 0 0 1-2.96-3.08 3 3 0 0 1-.34-5.58 2.5 2.5 0 0 1 1.32-4.24 2.5 2.5 0 0 1 1.98-3A2.5 2.5 0 0 1 9.5 2Z" />
    <path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96.44 2.5 2.5 0 0 0 2.96-3.08 3 3 0 0 0 .34-5.58 2.5 2.5 0 0 0-1.32-4.24 2.5 2.5 0 0 0-1.98-3A2.5 2.5 0 0 0 14.5 2Z" />
  </svg>
);

const IconSparkles = ({ size = 18 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z" />
    <path d="M5 3v4M19 17v4M3 5h4M17 19h4" />
  </svg>
);

const IconTrendingUp = ({ size = 18 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" />
    <polyline points="17 6 23 6 23 12" />
  </svg>
);

const IconChevronDown = ({ size = 18 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="6 9 12 15 18 9" />
  </svg>
);

const IconChevronUp = ({ size = 18 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="18 15 12 9 6 15" />
  </svg>
);

// ─────────────────────────────────────────────────────────────
// Palette
// ─────────────────────────────────────────────────────────────
const palette = {
  bg: "#0e0f12",
  fg: "#f4f4f5",
  muted: "#a1a1aa",
  accent: "#6366f1",
  cardBg: "#18191d",
  border: "#27272a",
  // Friction states
  chaos: "#e8c547",
  intensity: "#ef6461",
  stagnation: "#4787e8",
  balanced: "#22c55e",
  // Operating modes
  clarity: "#22c55e",
  activation: "#f59e0b",
  recovery: "#6366f1",
  // Doshas
  vata: "#e8c547",
  pitta: "#ef6461",
  kapha: "#4ecdc4",
};

// ─────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────
interface FrictionState {
  friction_state: string;
  operating_mode: string;
  baseline_drift: number;
  current_dosha: { vata: number; pitta: number; kapha: number };
  description?: string;
}

interface OSProfile {
  os_type: string;
  tagline?: string;
  baseline_dosha: { vata: number; pitta: number; kapha: number };
  life_context?: {
    roles?: string[];
    life_phase?: string;
    responsibility_load?: string;
  };
  strengths?: string[];
}

interface SoulSummary {
  soul_light: string[];
  soul_shadow: string[];
  soul_friction?: string[];
  coherence: number;
}

interface MemoryDetails {
  memories_count: number;
  patterns_count: number;
  topics_count: number;
  connections_count: number;
  days_journaling: number;
}

interface PersonalizedRecommendation {
  name: string;
  why: string;
  personal_relevance?: string;
  dosha_target?: string;
  priority_score?: number;
}

interface PersonalizedRecommendations {
  friction_state: string;
  urgency_level: string;
  personalization_confidence: number;
  why_this_state?: string;
  personal_insight?: string;
  recommendations: {
    immediate_actions: PersonalizedRecommendation[];
    foods: PersonalizedRecommendation[];
    practices: PersonalizedRecommendation[];
  };
  watch_for?: string[];
}

interface WeeklyState {
  days: { date: string; has_entry: boolean; coherence?: number }[];
  trend: "up" | "down" | "stable";
  insight?: string;
}

// ─────────────────────────────────────────────────────────────
// Main Component
// ─────────────────────────────────────────────────────────────
export default function MePageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const userId = searchParams.get("user") || "a";

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Data states
  const [currentState, setCurrentState] = useState<FrictionState | null>(null);
  const [osProfile, setOSProfile] = useState<OSProfile | null>(null);
  const [soulSummary, setSoulSummary] = useState<SoulSummary | null>(null);
  const [memoryDetails, setMemoryDetails] = useState<MemoryDetails | null>(null);
  const [recommendations, setRecommendations] = useState<PersonalizedRecommendations | null>(null);
  const [weeklyState, setWeeklyState] = useState<WeeklyState | null>(null);

  // UI states
  const [osExpanded, setOsExpanded] = useState(true);

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      setError(null);

      try {
        const [
          currentStateRes,
          osProfileRes,
          soulSummaryRes,
          memoryDetailsRes,
          recommendationsRes,
          weeklyStateRes,
        ] = await Promise.all([
          fetch(`/api/friction/state/current?user=${userId}`).catch(() => null),
          fetch(`/api/profile/operating-system?user=${userId}`).catch(() => null),
          fetch(`/api/soul/summary?user=${userId}`).catch(() => null),
          fetch(`/api/lab/memory-details?person_id=${userId}`).catch(() => null),
          fetch(`/api/friction/recommendations?user=${userId}`).catch(() => null),
          fetch(`/api/friction/state/weekly?user=${userId}`).catch(() => null),
        ]);

        if (currentStateRes?.ok) {
          const data = await currentStateRes.json();
          setCurrentState(data);
        }
        if (osProfileRes?.ok) {
          const data = await osProfileRes.json();
          setOSProfile(data);
        }
        if (soulSummaryRes?.ok) {
          const data = await soulSummaryRes.json();
          setSoulSummary(data);
        }
        if (memoryDetailsRes?.ok) {
          const data = await memoryDetailsRes.json();
          setMemoryDetails(data);
        }
        if (recommendationsRes?.ok) {
          const data = await recommendationsRes.json();
          // Handle both new personalized format and legacy format
          if (data.recommendations && typeof data.recommendations === "object" && !Array.isArray(data.recommendations)) {
            setRecommendations(data);
          } else {
            // Legacy format - wrap in new structure
            setRecommendations(null);
          }
        }
        if (weeklyStateRes?.ok) {
          const data = await weeklyStateRes.json();
          setWeeklyState(data);
        }
      } catch (err) {
        setError("Failed to load data");
        console.error(err);
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, [userId]);

  if (loading) {
    return (
      <div style={{ minHeight: "100vh", background: palette.bg, display: "flex", alignItems: "center", justifyContent: "center", color: palette.muted }}>
        Loading your profile...
      </div>
    );
  }

  return (
    <div style={{ minHeight: "100vh", background: palette.bg, color: palette.fg, padding: "1rem", maxWidth: 480, margin: "0 auto" }}>
      {/* Header */}
      <header style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "1.5rem" }}>
        <button
          onClick={() => router.push("/experience/converse")}
          style={{ background: "none", border: "none", color: palette.muted, cursor: "pointer", padding: "0.5rem" }}
        >
          <IconArrowLeft size={24} />
        </button>
        <div>
          <h1 style={{ fontSize: "1.5rem", fontWeight: 600, margin: 0 }}>Me</h1>
          {osProfile?.os_type && (
            <span style={{ fontSize: "0.75rem", color: palette.accent, background: `${palette.accent}22`, padding: "0.125rem 0.5rem", borderRadius: 12 }}>
              {osProfile.os_type}
            </span>
          )}
        </div>
      </header>

      {error && (
        <div style={{ background: "#ef646122", border: `1px solid ${palette.intensity}`, borderRadius: 8, padding: "1rem", marginBottom: "1rem", color: palette.intensity }}>
          {error}
        </div>
      )}

      {/* Current State Card */}
      <CurrentStateCard state={currentState} baselineDosha={osProfile?.baseline_dosha} />

      {/* Operating System Card */}
      <OperatingSystemCard profile={osProfile} expanded={osExpanded} onToggle={() => setOsExpanded(!osExpanded)} />

      {/* Soul State Card */}
      <SoulStateCard soul={soulSummary} />

      {/* Understanding Depth Card */}
      <UnderstandingCard details={memoryDetails} />

      {/* Personalized Recommendations Card */}
      <PersonalizedRecommendationsCard recommendations={recommendations} />

      {/* Weekly Rhythm Card */}
      <WeeklyRhythmCard weekly={weeklyState} />
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Current State Card
// ─────────────────────────────────────────────────────────────
function CurrentStateCard({ state, baselineDosha }: { state: FrictionState | null; baselineDosha?: { vata: number; pitta: number; kapha: number } }) {
  if (!state) {
    return (
      <Card title="Current State" icon={<IconZap size={18} />}>
        <p style={{ color: palette.muted, fontSize: "0.875rem" }}>
          Share a journal entry to see your current state
        </p>
      </Card>
    );
  }

  const frictionKey = (state.friction_state || "").toString().toLowerCase();
  const modeKey = (state.operating_mode || "").toString().toLowerCase();

  const frictionColor = {
    chaos: palette.chaos,
    intensity: palette.intensity,
    stagnation: palette.stagnation,
    balanced: palette.balanced,
  }[frictionKey] || palette.muted;

  const modeColor = {
    clarity: palette.clarity,
    activation: palette.activation,
    recovery: palette.recovery,
  }[modeKey] || palette.muted;

  const ModeIcon = {
    clarity: IconSun,
    activation: IconZap,
    recovery: IconMoon,
  }[modeKey] || IconZap;

  return (
    <Card title="Current State" icon={<IconZap size={18} />}>
      <div style={{ display: "flex", gap: "0.75rem", marginBottom: "1rem", flexWrap: "wrap" }}>
        {/* Friction State Badge */}
        <div style={{ background: `${frictionColor}22`, border: `1px solid ${frictionColor}`, borderRadius: 8, padding: "0.5rem 0.75rem" }}>
          <div style={{ fontSize: "0.625rem", color: palette.muted, textTransform: "uppercase", letterSpacing: "0.05em" }}>Friction</div>
          <div style={{ color: frictionColor, fontWeight: 600, textTransform: "capitalize" }}>{frictionKey || "unknown"}</div>
        </div>

        {/* Operating Mode Badge */}
        <div style={{ background: `${modeColor}22`, border: `1px solid ${modeColor}`, borderRadius: 8, padding: "0.5rem 0.75rem" }}>
          <div style={{ fontSize: "0.625rem", color: palette.muted, textTransform: "uppercase", letterSpacing: "0.05em" }}>Mode</div>
          <div style={{ display: "flex", alignItems: "center", gap: "0.25rem", color: modeColor, fontWeight: 600, textTransform: "capitalize" }}>
            <ModeIcon size={14} />
            {modeKey || "unknown"}
          </div>
        </div>

        {/* Baseline Drift */}
        <div style={{ background: palette.cardBg, border: `1px solid ${palette.border}`, borderRadius: 8, padding: "0.5rem 0.75rem" }}>
          <div style={{ fontSize: "0.625rem", color: palette.muted, textTransform: "uppercase", letterSpacing: "0.05em" }}>Drift</div>
          <div style={{ color: (state.baseline_drift ?? 0) > 50 ? palette.intensity : palette.fg, fontWeight: 600 }}>
            {Math.round(state.baseline_drift ?? 0)}%
          </div>
        </div>
      </div>

      {/* Current vs Baseline Dosha */}
      {baselineDosha && state.current_dosha && (
        <div style={{ marginTop: "1rem" }}>
          <div style={{ fontSize: "0.75rem", color: palette.muted, marginBottom: "0.5rem" }}>Current vs Baseline</div>
          <div style={{ display: "flex", gap: "1rem" }}>
            <div style={{ flex: 1 }}>
              <DoshaCompareBar label="Adaptive" current={state.current_dosha.vata} baseline={baselineDosha.vata} color={palette.vata} />
              <DoshaCompareBar label="Performance" current={state.current_dosha.pitta} baseline={baselineDosha.pitta} color={palette.pitta} />
              <DoshaCompareBar label="Conservation" current={state.current_dosha.kapha} baseline={baselineDosha.kapha} color={palette.kapha} />
            </div>
          </div>
        </div>
      )}

      {state.description && (
        <p style={{ fontSize: "0.875rem", color: palette.muted, marginTop: "1rem", lineHeight: 1.5 }}>
          {state.description}
        </p>
      )}
    </Card>
  );
}

// ─────────────────────────────────────────────────────────────
// Operating System Card
// ─────────────────────────────────────────────────────────────
function OperatingSystemCard({ profile, expanded, onToggle }: { profile: OSProfile | null; expanded: boolean; onToggle: () => void }) {
  if (!profile) {
    return (
      <Card title="Operating System" icon={<IconUser size={18} />}>
        <p style={{ color: palette.muted, fontSize: "0.875rem" }}>
          Complete onboarding to discover your operating system
        </p>
      </Card>
    );
  }

  return (
    <Card
      title="Operating System"
      icon={<IconUser size={18} />}
      headerRight={
        <button onClick={onToggle} style={{ background: "none", border: "none", color: palette.muted, cursor: "pointer" }}>
          {expanded ? <IconChevronUp size={18} /> : <IconChevronDown size={18} />}
        </button>
      }
    >
      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: expanded ? "1rem" : 0 }}>
        <span style={{ fontWeight: 600, color: palette.accent }}>{profile.os_type}</span>
        {profile.tagline && <span style={{ color: palette.muted, fontSize: "0.875rem" }}>— {profile.tagline}</span>}
      </div>

      {expanded && (
        <>
          {/* Baseline Dosha Bars */}
          {profile.baseline_dosha && (
            <div style={{ marginBottom: "1rem" }}>
              <div style={{ fontSize: "0.75rem", color: palette.muted, marginBottom: "0.5rem" }}>Baseline Profile</div>
              <DoshaBar label="Adaptive (Vata)" value={profile.baseline_dosha.vata ?? 0} color={palette.vata} />
              <DoshaBar label="Performance (Pitta)" value={profile.baseline_dosha.pitta ?? 0} color={palette.pitta} />
              <DoshaBar label="Conservation (Kapha)" value={profile.baseline_dosha.kapha ?? 0} color={palette.kapha} />
            </div>
          )}

          {/* Life Context */}
          {profile.life_context && (
            <div style={{ marginBottom: "1rem" }}>
              <div style={{ fontSize: "0.75rem", color: palette.muted, marginBottom: "0.5rem" }}>Life Context</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
                {profile.life_context.roles?.map((role, i) => (
                  <span key={i} style={{ background: `${palette.accent}22`, color: palette.accent, padding: "0.25rem 0.5rem", borderRadius: 12, fontSize: "0.75rem" }}>
                    {role}
                  </span>
                ))}
                {profile.life_context.life_phase && (
                  <span style={{ background: `${palette.muted}22`, color: palette.muted, padding: "0.25rem 0.5rem", borderRadius: 12, fontSize: "0.75rem" }}>
                    {profile.life_context.life_phase}
                  </span>
                )}
              </div>
            </div>
          )}

          {/* Strengths */}
          {profile.strengths && profile.strengths.length > 0 && (
            <div>
              <div style={{ fontSize: "0.75rem", color: palette.muted, marginBottom: "0.5rem" }}>Strengths</div>
              <ul style={{ margin: 0, paddingLeft: "1.25rem", color: palette.fg, fontSize: "0.875rem" }}>
                {profile.strengths.map((s, i) => (
                  <li key={i} style={{ marginBottom: "0.25rem" }}>{s}</li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}
    </Card>
  );
}

// ─────────────────────────────────────────────────────────────
// Soul State Card
// ─────────────────────────────────────────────────────────────
function SoulStateCard({ soul }: { soul: SoulSummary | null }) {
  if (!soul) {
    return (
      <Card title="Soul State" icon={<IconSparkles size={18} />}>
        <p style={{ color: palette.muted, fontSize: "0.875rem" }}>
          As you share more, patterns will emerge
        </p>
      </Card>
    );
  }

  const lights = soul.soul_light || [];
  const shadows = soul.soul_shadow || [];
  const frictions = soul.soul_friction || [];

  return (
    <Card title="Soul State" icon={<IconSparkles size={18} />}>
      <div style={{ display: "flex", gap: "2rem", marginBottom: "1rem" }}>
        {/* Coherence Ring */}
        <CoherenceRing value={soul.coherence ?? 0} />

        <div style={{ flex: 1 }}>
          {/* Soul Lights */}
          {lights.length > 0 && (
            <div style={{ marginBottom: "0.75rem" }}>
              <div style={{ fontSize: "0.625rem", color: palette.muted, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "0.25rem" }}>Lights</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "0.25rem" }}>
                {lights.map((light, i) => (
                  <SoulPill key={i} text={light} type="light" />
                ))}
              </div>
            </div>
          )}

          {/* Soul Shadows */}
          {shadows.length > 0 && (
            <div>
              <div style={{ fontSize: "0.625rem", color: palette.muted, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "0.25rem" }}>Shadows</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "0.25rem" }}>
                {shadows.map((shadow, i) => (
                  <SoulPill key={i} text={shadow} type="shadow" />
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Soul Friction */}
      {frictions.length > 0 && (
        <div style={{ borderTop: `1px solid ${palette.border}`, paddingTop: "0.75rem", marginTop: "0.5rem" }}>
          <div style={{ fontSize: "0.625rem", color: palette.muted, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "0.25rem" }}>Tensions</div>
          <ul style={{ margin: 0, paddingLeft: "1rem", fontSize: "0.875rem", color: palette.muted }}>
            {frictions.map((f, i) => (
              <li key={i}>{f}</li>
            ))}
          </ul>
        </div>
      )}
    </Card>
  );
}

// ─────────────────────────────────────────────────────────────
// Understanding Depth Card
// ─────────────────────────────────────────────────────────────
function UnderstandingCard({ details }: { details: MemoryDetails | null }) {
  if (!details) {
    return (
      <Card title="Understanding" icon={<IconBrain size={18} />}>
        <p style={{ color: palette.muted, fontSize: "0.875rem" }}>
          Getting to know you...
        </p>
      </Card>
    );
  }

  const metrics = [
    { label: "Memories", value: details.memories_count },
    { label: "Patterns", value: details.patterns_count },
    { label: "Topics", value: details.topics_count },
    { label: "Connections", value: details.connections_count },
  ];

  return (
    <Card title="Understanding" icon={<IconBrain size={18} />}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "0.75rem", marginBottom: "0.75rem" }}>
        {metrics.map((m) => (
          <div key={m.label} style={{ background: palette.bg, borderRadius: 8, padding: "0.75rem", textAlign: "center" }}>
            <div style={{ fontSize: "1.25rem", fontWeight: 600, color: palette.accent }}>{m.value}</div>
            <div style={{ fontSize: "0.75rem", color: palette.muted }}>{m.label}</div>
          </div>
        ))}
      </div>
      {details.days_journaling > 0 && (
        <p style={{ fontSize: "0.875rem", color: palette.muted, textAlign: "center" }}>
          {details.days_journaling} days of journaling
        </p>
      )}
    </Card>
  );
}

// ─────────────────────────────────────────────────────────────
// Personalized Recommendations Card
// ─────────────────────────────────────────────────────────────
function PersonalizedRecommendationsCard({ recommendations }: { recommendations: PersonalizedRecommendations | null }) {
  const [activeTab, setActiveTab] = useState<"actions" | "foods" | "practices">("actions");

  if (!recommendations) {
    return (
      <Card title="For You" icon={<IconTrendingUp size={18} />}>
        <p style={{ color: palette.muted, fontSize: "0.875rem" }}>
          Share how you&apos;re feeling to get personalized recommendations
        </p>
      </Card>
    );
  }

  const { recommendations: recs, urgency_level, personalization_confidence, personal_insight, watch_for } = recommendations;

  const urgencyColor = {
    low: palette.balanced,
    moderate: palette.chaos,
    high: palette.intensity,
    critical: palette.intensity,
  }[urgency_level] || palette.muted;

  const tabs = [
    { key: "actions" as const, label: "Quick Wins", items: recs.immediate_actions || [] },
    { key: "foods" as const, label: "Foods", items: recs.foods || [] },
    { key: "practices" as const, label: "Practices", items: recs.practices || [] },
  ];

  const activeItems = tabs.find(t => t.key === activeTab)?.items || [];

  return (
    <Card title="For You" icon={<IconTrendingUp size={18} />}>
      {/* Header with urgency and confidence */}
      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem", flexWrap: "wrap" }}>
        <span style={{
          background: `${urgencyColor}22`,
          color: urgencyColor,
          padding: "0.25rem 0.5rem",
          borderRadius: 12,
          fontSize: "0.75rem",
          textTransform: "capitalize"
        }}>
          {urgency_level} priority
        </span>
        {personalization_confidence > 0.5 && (
          <span style={{
            background: `${palette.accent}22`,
            color: palette.accent,
            padding: "0.25rem 0.5rem",
            borderRadius: 12,
            fontSize: "0.75rem"
          }}>
            {Math.round(personalization_confidence * 100)}% personalized
          </span>
        )}
      </div>

      {/* Personal insight */}
      {personal_insight && (
        <p style={{
          fontSize: "0.875rem",
          color: palette.fg,
          marginBottom: "1rem",
          padding: "0.75rem",
          background: `${palette.accent}11`,
          borderRadius: 8,
          borderLeft: `3px solid ${palette.accent}`,
          lineHeight: 1.5
        }}>
          {personal_insight}
        </p>
      )}

      {/* Tab navigation */}
      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem" }}>
        {tabs.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            style={{
              flex: 1,
              padding: "0.5rem",
              background: activeTab === tab.key ? palette.accent : palette.bg,
              border: `1px solid ${activeTab === tab.key ? palette.accent : palette.border}`,
              borderRadius: 8,
              color: activeTab === tab.key ? palette.fg : palette.muted,
              fontSize: "0.75rem",
              fontWeight: 500,
              cursor: "pointer",
              transition: "all 0.15s ease"
            }}
          >
            {tab.label} ({tab.items.length})
          </button>
        ))}
      </div>

      {/* Recommendations list */}
      <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
        {activeItems.length === 0 ? (
          <p style={{ color: palette.muted, fontSize: "0.875rem", textAlign: "center" }}>
            No recommendations in this category
          </p>
        ) : (
          activeItems.slice(0, 4).map((item, i) => (
            <div key={i} style={{ background: palette.bg, borderRadius: 8, padding: "0.75rem" }}>
              <div style={{ fontWeight: 500, color: palette.fg, marginBottom: "0.25rem" }}>
                {item.name}
              </div>
              <div style={{ fontSize: "0.75rem", color: palette.muted, marginBottom: item.personal_relevance ? "0.5rem" : 0 }}>
                {item.why}
              </div>
              {item.personal_relevance && (
                <div style={{
                  fontSize: "0.75rem",
                  color: palette.accent,
                  fontStyle: "italic",
                  paddingTop: "0.25rem",
                  borderTop: `1px solid ${palette.border}`
                }}>
                  ✦ {item.personal_relevance}
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {/* Watch for symptoms */}
      {watch_for && watch_for.length > 0 && (
        <div style={{ marginTop: "1rem", paddingTop: "0.75rem", borderTop: `1px solid ${palette.border}` }}>
          <div style={{ fontSize: "0.625rem", color: palette.muted, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "0.5rem" }}>
            Watch for
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "0.25rem" }}>
            {watch_for.slice(0, 4).map((symptom, i) => (
              <span key={i} style={{
                background: `${palette.intensity}22`,
                color: palette.intensity,
                padding: "0.25rem 0.5rem",
                borderRadius: 12,
                fontSize: "0.75rem"
              }}>
                {symptom}
              </span>
            ))}
          </div>
        </div>
      )}
    </Card>
  );
}

// ─────────────────────────────────────────────────────────────
// Weekly Rhythm Card
// ─────────────────────────────────────────────────────────────
function WeeklyRhythmCard({ weekly }: { weekly: WeeklyState | null }) {
  if (!weekly || !weekly.days || weekly.days.length === 0) {
    return null;
  }

  const trendIcon = weekly.trend === "up" ? "↑" : weekly.trend === "down" ? "↓" : "→";
  const trendColor = weekly.trend === "up" ? palette.balanced : weekly.trend === "down" ? palette.intensity : palette.muted;

  return (
    <Card title="Weekly Rhythm">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
        <div style={{ display: "flex", gap: "0.5rem" }}>
          {weekly.days.map((day, i) => (
            <div
              key={i}
              style={{
                width: 32,
                height: 32,
                borderRadius: "50%",
                background: day.has_entry ? `${palette.accent}` : palette.bg,
                border: `1px solid ${day.has_entry ? palette.accent : palette.border}`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "0.625rem",
                color: day.has_entry ? palette.fg : palette.muted,
              }}
              title={day.date}
            >
              {new Date(day.date).toLocaleDateString("en", { weekday: "narrow" })}
            </div>
          ))}
        </div>
        <span style={{ color: trendColor, fontWeight: 600 }}>{trendIcon}</span>
      </div>
      {weekly.insight && (
        <p style={{ fontSize: "0.875rem", color: palette.muted }}>{weekly.insight}</p>
      )}
    </Card>
  );
}

// ─────────────────────────────────────────────────────────────
// Shared Components
// ─────────────────────────────────────────────────────────────
function Card({ title, icon, headerRight, children }: { title?: string; icon?: React.ReactNode; headerRight?: React.ReactNode; children: React.ReactNode }) {
  return (
    <div style={{ background: palette.cardBg, borderRadius: 12, padding: "1rem", marginBottom: "1rem", border: `1px solid ${palette.border}` }}>
      {title && (
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.75rem" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", color: palette.fg, fontWeight: 500 }}>
            {icon}
            {title}
          </div>
          {headerRight}
        </div>
      )}
      {children}
    </div>
  );
}

function DoshaBar({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div style={{ marginBottom: "0.5rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.75rem", marginBottom: "0.25rem" }}>
        <span style={{ color: palette.muted }}>{label}</span>
        <span style={{ color }}>{Math.round(value)}%</span>
      </div>
      <div style={{ height: 6, background: palette.bg, borderRadius: 3, overflow: "hidden" }}>
        <div style={{ height: "100%", width: `${value}%`, background: color, borderRadius: 3 }} />
      </div>
    </div>
  );
}

function DoshaCompareBar({ label, current, baseline, color }: { label: string; current: number; baseline: number; color: string }) {
  const diff = current - baseline;
  const diffColor = Math.abs(diff) > 10 ? palette.intensity : palette.muted;

  return (
    <div style={{ marginBottom: "0.5rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.75rem", marginBottom: "0.25rem" }}>
        <span style={{ color: palette.muted }}>{label}</span>
        <span style={{ color: diffColor }}>{diff > 0 ? "+" : ""}{Math.round(diff)}%</span>
      </div>
      <div style={{ position: "relative", height: 6, background: palette.bg, borderRadius: 3, overflow: "hidden" }}>
        {/* Baseline marker */}
        <div style={{ position: "absolute", left: `${baseline}%`, top: 0, bottom: 0, width: 2, background: palette.muted, zIndex: 1 }} />
        {/* Current value */}
        <div style={{ height: "100%", width: `${current}%`, background: color, borderRadius: 3 }} />
      </div>
    </div>
  );
}

function CoherenceRing({ value }: { value: number }) {
  const size = 64;
  const strokeWidth = 6;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (value / 100) * circumference;

  return (
    <div style={{ position: "relative", width: size, height: size }}>
      <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
        <circle cx={size / 2} cy={size / 2} r={radius} stroke={palette.bg} strokeWidth={strokeWidth} fill="none" />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={palette.accent}
          strokeWidth={strokeWidth}
          fill="none"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
        />
      </svg>
      <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", fontSize: "0.875rem", fontWeight: 600, color: palette.fg }}>
        {Math.round(value)}
      </div>
    </div>
  );
}

function SoulPill({ text, type }: { text: string; type: "light" | "shadow" }) {
  const bg = type === "light" ? `${palette.balanced}22` : `${palette.muted}22`;
  const color = type === "light" ? palette.balanced : palette.muted;

  return (
    <span style={{ background: bg, color, padding: "0.25rem 0.5rem", borderRadius: 12, fontSize: "0.75rem" }}>
      {text}
    </span>
  );
}
