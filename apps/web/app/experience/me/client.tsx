"use client";

import { useSearchParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

// Add keyframe animation for loader
const spinKeyframes = `
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
`;

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

const IconMail = ({ size = 18 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="2" y="4" width="20" height="16" rx="2" />
    <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
  </svg>
);

const IconLink = ({ size = 18 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
    <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
  </svg>
);

const IconCheck = ({ size = 18 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="20 6 9 17 4 12" />
  </svg>
);

const IconLoader = ({ size = 18 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ animation: "spin 1s linear infinite" }}>
    <path d="M21 12a9 9 0 1 1-6.219-8.56" />
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

interface EmailSignals {
  status: string;
  extracted_at?: string;
  subscriptions: Array<{
    sender_email: string;
    sender_name?: string;
    category?: string;
    is_marketing?: boolean;
    cadence?: string;
    total_received?: number;
  }>;
  avoidance: Array<{
    thread_id: string;
    subject: string;
    sender_email: string;
    duration_days: number;
    severity: string;
    follow_up_count?: number;
    suggested_action?: string;
  }>;
  boundary: {
    erosion_score: number;
    after_hours_pct: number;
    weekend_pct: number;
    trend: string;
    friction_impact?: string;
  } | null;
  cognitive_load: {
    active_threads: number;
    heavy_threads: number;
    load_score: number;
    overwhelm_risk: string;
  } | null;
}

interface EmailStatus {
  connected: boolean;
  status: string;
  email?: string;
  last_sync_at?: string;
  messages_synced?: number;
}

interface EmailCommitmentItem {
  id?: string;
  commitment: string;
  deadline?: string;
  subject: string;
  recipient: string;
  commitment_type?: string;
  extracted_at?: string;
  status?: string;
}

interface EmailDigest {
  status: string;
  triage_counts?: { needs_action: number; fyi: number; noise: number };
  action_items?: Array<{
    message_id: string;
    subject: string;
    sender: string;
    sender_name?: string;
    action_summary?: string;
    deadline?: string;
    priority: string;
    draft_reply?: string;
  }>;
  fyi_items?: Array<{
    message_id: string;
    subject: string;
    sender: string;
    sender_name?: string;
    one_line_summary?: string;
  }>;
  noise_summary?: { count: number; categories: Record<string, number> };
  commitments?: EmailCommitmentItem[];
  subscriptions?: EmailCommitmentItem[];
  emails_analyzed?: number;
  created_at?: string;
  error_message?: string;
}

// ─────────────────────────────────────────────────────────────
// Main Component
// ─────────────────────────────────────────────────────────────
export default function MePageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [userId, setUserId] = useState(searchParams.get("user") || "");

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Data states
  const [currentState, setCurrentState] = useState<FrictionState | null>(null);
  const [osProfile, setOSProfile] = useState<OSProfile | null>(null);
  const [soulSummary, setSoulSummary] = useState<SoulSummary | null>(null);
  const [memoryDetails, setMemoryDetails] = useState<MemoryDetails | null>(null);
  const [recommendations, setRecommendations] = useState<PersonalizedRecommendations | null>(null);
  const [weeklyState, setWeeklyState] = useState<WeeklyState | null>(null);
  const [emailStatus, setEmailStatus] = useState<EmailStatus | null>(null);
  const [emailSignals, setEmailSignals] = useState<EmailSignals | null>(null);
  const [emailDigest, setEmailDigest] = useState<EmailDigest | null>(null);
  const [digestLoading, setDigestLoading] = useState(false);

  // UI states
  const [osExpanded, setOsExpanded] = useState(true);
  const [emailConnecting, setEmailConnecting] = useState(false);

  // Resolve person_id from server-side auth
  useEffect(() => {
    if (userId) return; // Already have it from query param
    async function resolveUser() {
      try {
        const res = await fetch("/api/auth/me");
        if (res.ok) {
          const data = await res.json();
          if (data.person_id) setUserId(data.person_id);
        }
      } catch {}
    }
    resolveUser();
  }, [userId]);

  useEffect(() => {
    if (!userId) return;

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
          emailStatusRes,
        ] = await Promise.all([
          fetch(`/api/friction/state/current?user=${userId}`).catch(() => null),
          fetch(`/api/profile/operating-system?user=${userId}`).catch(() => null),
          fetch(`/api/soul/summary?user=${userId}`).catch(() => null),
          fetch(`/api/lab/memory-details?person_id=${userId}`).catch(() => null),
          fetch(`/api/friction/recommendations?user=${userId}`).catch(() => null),
          fetch(`/api/friction/state/weekly?user=${userId}`).catch(() => null),
          fetch(`/api/email/status`).catch(() => null),
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
        if (emailStatusRes?.ok) {
          const data = await emailStatusRes.json();
          setEmailStatus(data);
        } else {
          setEmailStatus({ connected: false, status: "not_connected" });
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

  // Gmail connection handlers
  const handleConnectGmail = async () => {
    setEmailConnecting(true);
    try {
      const response = await fetch("/api/email/connect/gmail", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          app_redirect_uri: `${window.location.origin}/experience/me?email_connected=1`,
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to initiate Gmail connection");
      }

      const data = await response.json();
      if (data.auth_url) {
        // Redirect to Google OAuth
        window.location.href = data.auth_url;
      }
    } catch (err) {
      console.error("Failed to connect Gmail:", err);
      setEmailConnecting(false);
    }
  };

  const handleDisconnectGmail = async () => {
    if (!confirm("Disconnect Gmail? This will remove all email insights.")) {
      return;
    }

    try {
      const response = await fetch("/api/email/disconnect", {
        method: "POST",
      });

      if (response.ok) {
        setEmailStatus({ connected: false, status: "not_connected" });
      }
    } catch (err) {
      console.error("Failed to disconnect Gmail:", err);
    }
  };

  // Fetch email signals and digest when connected
  useEffect(() => {
    if (emailStatus?.connected) {
      fetch("/api/email/signals")
        .then((res) => (res.ok ? res.json() : null))
        .then((data) => {
          if (data && data.status !== "error") {
            setEmailSignals(data);
          }
        })
        .catch(() => {});

      // Fetch digest
      fetch("/api/email/digest")
        .then((res) => (res.ok ? res.json() : null))
        .then((data) => {
          if (data) {
            setEmailDigest(data);
          }
        })
        .catch(() => {});
    } else {
      setEmailSignals(null);
      setEmailDigest(null);
    }
  }, [emailStatus]);

  // Check for email connection callback
  useEffect(() => {
    const emailConnected = searchParams.get("email_connected");
    if (emailConnected === "1") {
      // Refresh email status after OAuth callback
      fetch("/api/email/status")
        .then((res) => res.json())
        .then((data) => setEmailStatus(data))
        .catch(() => {});
      // Clean up URL
      router.replace("/experience/me");
    }
  }, [searchParams, router]);

  if (loading) {
    return (
      <div style={{ minHeight: "100vh", background: palette.bg, display: "flex", alignItems: "center", justifyContent: "center", color: palette.muted }}>
        Loading your profile...
      </div>
    );
  }

  return (
    <div style={{ minHeight: "100vh", background: palette.bg, color: palette.fg, padding: "2rem 3rem", maxWidth: 1280, margin: "0 auto" }}>
      {/* Inject keyframe animation */}
      <style dangerouslySetInnerHTML={{ __html: spinKeyframes }} />

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

      {/* Dashboard grid */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", alignItems: "start" }}>
        {/* Row 1 */}
        <CurrentStateCard state={currentState} baselineDosha={osProfile?.baseline_dosha} />
        <UnderstandingCard details={memoryDetails} />

        {/* Row 2 */}
        <OperatingSystemCard profile={osProfile} expanded={osExpanded} onToggle={() => setOsExpanded(!osExpanded)} />
        <SoulStateCard soul={soulSummary} />

        {/* Row 3 */}
        <WeeklyRhythmCard weekly={weeklyState} />
        <ConnectionsCard
          emailStatus={emailStatus}
          connecting={emailConnecting}
          onConnectGmail={handleConnectGmail}
          onDisconnectGmail={handleDisconnectGmail}
        />

        {/* Full-width: Recommendations */}
        <div style={{ gridColumn: "1 / -1" }}>
          <PersonalizedRecommendationsCard recommendations={recommendations} />
        </div>

        {/* Full-width: Email Digest */}
        <div style={{ gridColumn: "1 / -1" }}>
          <EmailDigestCard
            digest={emailDigest}
            signals={emailSignals}
            connected={emailStatus?.connected === true}
            loading={digestLoading}
            onRefresh={() => {
              setDigestLoading(true);
              fetch("/api/email/digest", { method: "POST" })
                .then((res) => (res.ok ? res.json() : null))
                .then((data) => {
                  if (data) setEmailDigest(data);
                })
                .catch(() => {})
                .finally(() => setDigestLoading(false));
            }}
          />
        </div>
      </div>
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
    <div style={{ background: palette.cardBg, borderRadius: 12, padding: "1rem", border: `1px solid ${palette.border}`, height: "100%" }}>
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

// ─────────────────────────────────────────────────────────────
// Email Peek Modal (focused email view with context + reply)
// ─────────────────────────────────────────────────────────────
interface EmailDetail {
  message_id: string;
  provider_message_id?: string;
  subject: string;
  sender_email: string;
  sender_name?: string;
  direction?: string;
  timestamp?: string;
  body?: string | null;
  gmail_url?: string | null;
}

function EmailPeekModal({
  item,
  onClose,
}: {
  item: {
    message_id: string;
    subject: string;
    sender: string;
    sender_name?: string;
    action_summary?: string;
    priority: string;
    draft_reply?: string;
    deadline?: string;
  };
  onClose: () => void;
}) {
  const [detail, setDetail] = useState<EmailDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(true);
  const [draftText, setDraftText] = useState(item.draft_reply || "");
  const [sendState, setSendState] = useState<"idle" | "confirm" | "sending" | "sent" | "error">("idle");
  const [sendError, setSendError] = useState("");

  useEffect(() => {
    setLoadingDetail(true);
    fetch(`/api/email/message/${encodeURIComponent(item.message_id)}`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data) setDetail(data);
      })
      .catch(() => {})
      .finally(() => setLoadingDetail(false));
  }, [item.message_id]);

  const handleSendClick = () => {
    if (sendState === "idle") {
      setSendState("confirm");
    }
  };

  const handleConfirmSend = async () => {
    setSendState("sending");
    setSendError("");
    try {
      const res = await fetch(
        `/api/email/message/${encodeURIComponent(item.message_id)}/reply`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ body: draftText }),
        }
      );
      if (res.ok) {
        setSendState("sent");
      } else {
        const errData = await res.json().catch(() => ({}));
        setSendError(errData.error || "Failed to send");
        setSendState("error");
      }
    } catch {
      setSendError("Network error");
      setSendState("error");
    }
  };

  const handleCancelConfirm = () => {
    setSendState("idle");
  };

  const priorityColor = (p: string) => {
    switch (p) {
      case "high": return palette.intensity;
      case "medium": return palette.chaos;
      default: return palette.muted;
    }
  };

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 1000,
        display: "flex",
        flexDirection: "column",
        background: palette.bg,
      }}
    >
      {/* Header bar */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "0.5rem",
          padding: "0.75rem 1rem",
          borderBottom: `1px solid ${palette.border}`,
          flexShrink: 0,
        }}
      >
        <button
          onClick={onClose}
          style={{
            background: "none",
            border: "none",
            color: palette.muted,
            cursor: "pointer",
            padding: "0.25rem",
            display: "flex",
            alignItems: "center",
          }}
        >
          <IconArrowLeft size={20} />
        </button>
        <span style={{ fontSize: "0.875rem", color: palette.fg, fontWeight: 500 }}>
          Email Detail
        </span>
        <div style={{ flex: 1 }} />
        <span
          style={{
            fontSize: "0.6rem",
            background: `${priorityColor(item.priority)}22`,
            color: priorityColor(item.priority),
            padding: "0.125rem 0.4rem",
            borderRadius: 10,
            textTransform: "uppercase",
          }}
        >
          {item.priority}
        </span>
      </div>

      {/* Scrollable content */}
      <div style={{ flex: 1, overflowY: "auto", padding: "1rem" }}>
        {/* Sender + subject */}
        <div style={{ marginBottom: "1rem" }}>
          <div style={{ fontSize: "1rem", fontWeight: 600, color: palette.fg, marginBottom: "0.25rem" }}>
            {item.sender_name || item.sender}
          </div>
          {item.sender_name && (
            <div style={{ fontSize: "0.75rem", color: palette.muted, marginBottom: "0.5rem" }}>
              {item.sender}
            </div>
          )}
          <div style={{ fontSize: "0.875rem", color: palette.fg }}>
            {item.subject}
          </div>
          {detail?.timestamp && (
            <div style={{ fontSize: "0.7rem", color: palette.muted, marginTop: "0.25rem" }}>
              {new Date(detail.timestamp).toLocaleString()}
            </div>
          )}
        </div>

        {/* Why Sakhi surfaced this */}
        {item.action_summary && (
          <div
            style={{
              background: `${palette.accent}11`,
              borderLeft: `3px solid ${palette.accent}`,
              borderRadius: 6,
              padding: "0.6rem 0.75rem",
              marginBottom: "1rem",
            }}
          >
            <div style={{ fontSize: "0.625rem", color: palette.accent, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "0.2rem" }}>
              Why Sakhi surfaced this
            </div>
            <div style={{ fontSize: "0.8rem", color: palette.fg, lineHeight: 1.4 }}>
              {item.action_summary}
              {item.deadline && (
                <span style={{ color: palette.chaos }}> (deadline: {item.deadline})</span>
              )}
            </div>
          </div>
        )}

        {/* Email body */}
        <div style={{ marginBottom: "1.25rem" }}>
          <div style={{ fontSize: "0.625rem", color: palette.muted, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "0.4rem" }}>
            Email Content
          </div>
          {loadingDetail ? (
            <div style={{ color: palette.muted, fontSize: "0.8rem", padding: "1rem 0" }}>
              Loading email...
            </div>
          ) : detail?.body ? (
            <div
              style={{
                background: palette.cardBg,
                border: `1px solid ${palette.border}`,
                borderRadius: 8,
                padding: "0.75rem",
                fontSize: "0.8rem",
                color: palette.fg,
                lineHeight: 1.6,
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
                maxHeight: 300,
                overflowY: "auto",
              }}
            >
              {detail.body}
            </div>
          ) : (
            <div style={{ color: palette.muted, fontSize: "0.8rem", fontStyle: "italic" }}>
              Could not load email body
            </div>
          )}
        </div>

        {/* Draft reply editor */}
        <div style={{ marginBottom: "1rem" }}>
          <div style={{ fontSize: "0.625rem", color: palette.muted, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "0.4rem" }}>
            Draft Reply
          </div>
          <textarea
            value={draftText}
            onChange={(e) => { setDraftText(e.target.value); if (sendState === "confirm") setSendState("idle"); }}
            placeholder="Write your reply here..."
            disabled={sendState === "sending" || sendState === "sent"}
            style={{
              width: "100%",
              minHeight: 100,
              background: palette.cardBg,
              border: `1px solid ${palette.border}`,
              borderRadius: 8,
              padding: "0.75rem",
              fontSize: "0.8rem",
              color: palette.fg,
              lineHeight: 1.5,
              resize: "vertical",
              fontFamily: "inherit",
              outline: "none",
              opacity: sendState === "sent" ? 0.5 : 1,
            }}
            onFocus={(e) => {
              e.currentTarget.style.borderColor = palette.accent;
            }}
            onBlur={(e) => {
              e.currentTarget.style.borderColor = palette.border;
            }}
          />
          <div style={{ fontSize: "0.65rem", color: palette.muted, marginTop: "0.25rem" }}>
            Sakhi drafted this for you — edit it, then send when ready
          </div>
        </div>
      </div>

      {/* Sticky CTA footer */}
      <div
        style={{
          padding: "0.75rem 1rem",
          borderTop: `1px solid ${palette.border}`,
          flexShrink: 0,
          background: palette.bg,
        }}
      >
        {/* Confirmation bar */}
        {sendState === "confirm" && (
          <div
            style={{
              background: `${palette.chaos}15`,
              border: `1px solid ${palette.chaos}44`,
              borderRadius: 8,
              padding: "0.6rem 0.75rem",
              marginBottom: "0.5rem",
              fontSize: "0.75rem",
              color: palette.fg,
              lineHeight: 1.4,
            }}
          >
            This will send the reply above from your Gmail to <strong>{item.sender_name || item.sender}</strong>. Are you sure?
          </div>
        )}

        {/* Error message */}
        {sendState === "error" && (
          <div
            style={{
              background: `${palette.intensity}15`,
              border: `1px solid ${palette.intensity}44`,
              borderRadius: 8,
              padding: "0.5rem 0.75rem",
              marginBottom: "0.5rem",
              fontSize: "0.75rem",
              color: palette.intensity,
            }}
          >
            {sendError || "Failed to send"}
          </div>
        )}

        {/* Success message */}
        {sendState === "sent" && (
          <div
            style={{
              background: `${palette.balanced}15`,
              border: `1px solid ${palette.balanced}44`,
              borderRadius: 8,
              padding: "0.6rem 0.75rem",
              marginBottom: "0.5rem",
              fontSize: "0.8rem",
              color: palette.balanced,
              display: "flex",
              alignItems: "center",
              gap: "0.4rem",
            }}
          >
            <IconCheck size={16} />
            Reply sent successfully
          </div>
        )}

        <div style={{ display: "flex", gap: "0.5rem" }}>
          {sendState === "confirm" ? (
            <>
              <button
                onClick={handleCancelConfirm}
                style={{
                  flex: 1,
                  background: palette.cardBg,
                  color: palette.muted,
                  border: `1px solid ${palette.border}`,
                  borderRadius: 8,
                  padding: "0.7rem",
                  fontSize: "0.8rem",
                  fontWeight: 500,
                  cursor: "pointer",
                }}
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmSend}
                style={{
                  flex: 1,
                  background: palette.accent,
                  color: "#fff",
                  border: "none",
                  borderRadius: 8,
                  padding: "0.7rem",
                  fontSize: "0.8rem",
                  fontWeight: 600,
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: "0.4rem",
                }}
              >
                <IconMail size={14} />
                Confirm & Send
              </button>
            </>
          ) : sendState === "sent" ? (
            <button
              onClick={onClose}
              style={{
                flex: 1,
                background: palette.cardBg,
                color: palette.fg,
                border: `1px solid ${palette.border}`,
                borderRadius: 8,
                padding: "0.7rem",
                fontSize: "0.8rem",
                fontWeight: 500,
                cursor: "pointer",
              }}
            >
              Done
            </button>
          ) : (
            <button
              onClick={sendState === "error" ? handleConfirmSend : handleSendClick}
              disabled={!draftText.trim() || sendState === "sending"}
              style={{
                flex: 1,
                background: palette.accent,
                color: "#fff",
                border: "none",
                borderRadius: 8,
                padding: "0.7rem",
                fontSize: "0.8rem",
                fontWeight: 600,
                cursor: !draftText.trim() || sendState === "sending" ? "not-allowed" : "pointer",
                opacity: !draftText.trim() || sendState === "sending" ? 0.5 : 1,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "0.4rem",
              }}
            >
              {sendState === "sending" ? (
                <>
                  <IconLoader size={14} />
                  Sending...
                </>
              ) : sendState === "error" ? (
                <>
                  <IconMail size={14} />
                  Retry Send
                </>
              ) : (
                <>
                  <IconMail size={14} />
                  Send via Sakhi
                </>
              )}
            </button>
          )}
        </div>
        {/* Open in Gmail fallback */}
        {detail?.gmail_url && sendState !== "sent" && (
          <div style={{ textAlign: "center", marginTop: "0.4rem" }}>
            <a
              href={detail.gmail_url}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                fontSize: "0.65rem",
                color: palette.muted,
                textDecoration: "none",
              }}
            >
              Need attachments or formatting? Open in Gmail
            </a>
          </div>
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Email Digest Card (LLM-powered cognitive offload)
// ─────────────────────────────────────────────────────────────
function EmailDigestCard({
  digest,
  signals,
  connected,
  loading,
  onRefresh,
}: {
  digest: EmailDigest | null;
  signals: EmailSignals | null;
  connected: boolean;
  loading: boolean;
  onRefresh: () => void;
}) {
  const [expandedDraft, setExpandedDraft] = useState<string | null>(null);
  const [showNoise, setShowNoise] = useState(false);
  const [showFyi, setShowFyi] = useState(false);
  const [hiddenCommitments, setHiddenCommitments] = useState<Set<string>>(new Set());
  const [hiddenActions, setHiddenActions] = useState<Set<string>>(new Set());
  const [hiddenSubscriptions, setHiddenSubscriptions] = useState<Set<string>>(new Set());
  const [peekItem, setPeekItem] = useState<{
    message_id: string;
    subject: string;
    sender: string;
    sender_name?: string;
    action_summary?: string;
    priority: string;
    draft_reply?: string;
    deadline?: string;
  } | null>(null);

  if (!connected) return null;

  const hasDigest = digest && digest.status === "complete" && digest.triage_counts;

  // Priority color helper
  const priorityColor = (p: string) => {
    switch (p) {
      case "high": return palette.intensity;
      case "medium": return palette.chaos;
      default: return palette.muted;
    }
  };

  // Time ago helper
  const timeAgo = (isoStr?: string) => {
    if (!isoStr) return "";
    const diff = Date.now() - new Date(isoStr).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return "just now";
    if (mins < 60) return `${mins}m ago`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h ago`;
    return `${Math.floor(hours / 24)}d ago`;
  };

  // Generating state
  if (digest && digest.status === "generating") {
    return (
      <Card title="Email Digest" icon={<IconMail size={18} />}>
        <div style={{ textAlign: "center", padding: "1.5rem 0", color: palette.muted }}>
          <div style={{ marginBottom: "0.5rem", fontSize: "0.875rem" }}>Reading your emails...</div>
          <div style={{ fontSize: "0.75rem" }}>Sakhi is analyzing your inbox to find what matters</div>
        </div>
      </Card>
    );
  }

  // No digest yet - show fallback with signals data
  if (!hasDigest) {
    // Show a generate button if connected but no digest
    if (connected) {
      return (
        <Card title="Email Digest" icon={<IconMail size={18} />}>
          <div style={{ textAlign: "center", padding: "1rem 0" }}>
            <div style={{ fontSize: "0.875rem", color: palette.fg, marginBottom: "0.5rem" }}>
              Let Sakhi read your emails for you
            </div>
            <div style={{ fontSize: "0.75rem", color: palette.muted, marginBottom: "1rem" }}>
              Get a smart summary of what needs your attention
            </div>
            <button
              onClick={onRefresh}
              disabled={loading}
              style={{
                background: palette.accent,
                color: "#fff",
                border: "none",
                borderRadius: 8,
                padding: "0.5rem 1.25rem",
                fontSize: "0.8rem",
                cursor: loading ? "not-allowed" : "pointer",
                opacity: loading ? 0.6 : 1,
              }}
            >
              {loading ? "Generating..." : "Generate Digest"}
            </button>
          </div>
        </Card>
      );
    }
    return null;
  }

  const { triage_counts, action_items = [], fyi_items = [], noise_summary, commitments = [], subscriptions = [] } = digest;

  return (
    <Card
      title="Email Digest"
      icon={<IconMail size={18} />}
      headerRight={
        <button
          onClick={onRefresh}
          disabled={loading}
          style={{
            background: "transparent",
            border: `1px solid ${palette.border}`,
            color: palette.muted,
            borderRadius: 6,
            padding: "0.25rem 0.5rem",
            fontSize: "0.625rem",
            cursor: loading ? "not-allowed" : "pointer",
            opacity: loading ? 0.6 : 1,
          }}
        >
          {loading ? "..." : "Refresh"}
        </button>
      }
    >
      {/* Triage Summary Header */}
      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem" }}>
        {triage_counts!.needs_action > 0 && (
          <div style={{
            flex: 1,
            background: `${palette.intensity}15`,
            border: `1px solid ${palette.intensity}33`,
            borderRadius: 8,
            padding: "0.6rem",
            textAlign: "center",
          }}>
            <div style={{ fontSize: "1.5rem", fontWeight: 700, color: palette.intensity }}>
              {triage_counts!.needs_action}
            </div>
            <div style={{ fontSize: "0.625rem", color: palette.intensity, opacity: 0.8 }}>need you</div>
          </div>
        )}
        {triage_counts!.fyi > 0 && (
          <div style={{
            flex: 1,
            background: `${palette.accent}15`,
            border: `1px solid ${palette.accent}33`,
            borderRadius: 8,
            padding: "0.6rem",
            textAlign: "center",
          }}>
            <div style={{ fontSize: "1.5rem", fontWeight: 700, color: palette.accent }}>
              {triage_counts!.fyi}
            </div>
            <div style={{ fontSize: "0.625rem", color: palette.accent, opacity: 0.8 }}>FYI</div>
          </div>
        )}
        {triage_counts!.noise > 0 && (
          <div style={{
            flex: 1,
            background: `${palette.muted}15`,
            border: `1px solid ${palette.muted}33`,
            borderRadius: 8,
            padding: "0.6rem",
            textAlign: "center",
          }}>
            <div style={{ fontSize: "1.5rem", fontWeight: 700, color: palette.muted }}>
              {triage_counts!.noise}
            </div>
            <div style={{ fontSize: "0.625rem", color: palette.muted, opacity: 0.8 }}>noise</div>
          </div>
        )}
      </div>

      {/* Action Items */}
      {action_items.filter((a) => !hiddenActions.has(a.message_id)).length > 0 && (
        <div style={{ marginBottom: "1rem" }}>
          <div style={{ fontSize: "0.625rem", color: palette.muted, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "0.5rem" }}>
            Needs Your Attention
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            {action_items
              .filter((a) => !hiddenActions.has(a.message_id))
              .slice(0, 5)
              .map((item, i) => {
                const handleDismissAction = () => {
                  setHiddenActions((prev) => { const next = new Set(prev); next.add(item.message_id); return next; });
                  fetch("/api/email/actions/dismiss", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ message_id: item.message_id }),
                  }).catch(() => {
                    setHiddenActions((prev) => { const next = new Set(prev); next.delete(item.message_id); return next; });
                  });
                };

                return (
                  <div
                    key={i}
                    style={{
                      background: palette.bg,
                      borderRadius: 8,
                      padding: "0.75rem",
                      borderLeft: `3px solid ${priorityColor(item.priority)}`,
                      cursor: "pointer",
                    }}
                    onClick={() => setPeekItem(item)}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "0.5rem" }}>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontSize: "0.8rem", color: palette.fg, fontWeight: 500, marginBottom: "0.2rem" }}>
                          {item.sender_name || item.sender}
                        </div>
                        <div style={{ fontSize: "0.75rem", color: palette.muted, marginBottom: "0.3rem" }}>
                          {item.subject && item.subject.length > 50
                            ? item.subject.slice(0, 50) + "..."
                            : item.subject}
                        </div>
                        {item.action_summary && (
                          <div style={{ fontSize: "0.8rem", color: palette.fg }}>
                            {item.action_summary}
                          </div>
                        )}
                      </div>
                      <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: "0.25rem", flexShrink: 0 }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "0.3rem" }}>
                          <span style={{
                            fontSize: "0.6rem",
                            background: `${priorityColor(item.priority)}22`,
                            color: priorityColor(item.priority),
                            padding: "0.125rem 0.4rem",
                            borderRadius: 10,
                            textTransform: "uppercase",
                          }}>
                            {item.priority}
                          </span>
                          <button
                            onClick={(e) => { e.stopPropagation(); handleDismissAction(); }}
                            title="Dismiss"
                            style={{
                              background: `${palette.muted}15`,
                              border: `1px solid ${palette.muted}33`,
                              color: palette.muted,
                              borderRadius: 4,
                              width: 20,
                              height: 20,
                              fontSize: "0.6rem",
                              cursor: "pointer",
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "center",
                              padding: 0,
                            }}
                          >
                            ✕
                          </button>
                        </div>
                        {item.deadline && (
                          <span style={{ fontSize: "0.625rem", color: palette.chaos }}>
                            {item.deadline}
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Tap hint */}
                    <div style={{ fontSize: "0.6rem", color: palette.muted, marginTop: "0.4rem", opacity: 0.7 }}>
                      Tap to view & reply
                    </div>
                  </div>
                );
              })}
          </div>
        </div>
      )}

      {/* Commitments (people only) */}
      {commitments.filter((c) => !hiddenCommitments.has(c.id || "")).length > 0 && (
        <div style={{ marginBottom: "1rem" }}>
          <div style={{ fontSize: "0.625rem", color: palette.muted, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "0.5rem" }}>
            Your Commitments
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.4rem" }}>
            {commitments
              .filter((c) => !hiddenCommitments.has(c.id || ""))
              .map((c, i) => {
                const ageMs = c.extracted_at
                  ? Date.now() - new Date(c.extracted_at).getTime()
                  : 0;
                const ageDays = Math.floor(ageMs / 86400000);
                const isStale = ageDays > 14;

                const handleAction = (status: "done" | "dismissed") => {
                  if (!c.id) return;
                  setHiddenCommitments((prev) => { const next = new Set(prev); next.add(c.id!); return next; });
                  fetch(`/api/email/commitments/${c.id}`, {
                    method: "PATCH",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ status }),
                  }).catch(() => {
                    setHiddenCommitments((prev) => {
                      const next = new Set(prev);
                      next.delete(c.id!);
                      return next;
                    });
                  });
                };

                return (
                  <div
                    key={c.id || i}
                    style={{
                      background: palette.bg,
                      borderRadius: 6,
                      padding: "0.5rem 0.6rem",
                      borderLeft: `3px solid ${isStale ? palette.chaos : palette.balanced}`,
                      display: "flex",
                      alignItems: "flex-start",
                      gap: "0.5rem",
                    }}
                  >
                    <div style={{ display: "flex", gap: "0.25rem", flexShrink: 0, paddingTop: "0.1rem" }}>
                      <button
                        onClick={() => handleAction("done")}
                        title="Mark done"
                        style={{
                          background: `${palette.balanced}22`,
                          border: `1px solid ${palette.balanced}44`,
                          color: palette.balanced,
                          borderRadius: 4,
                          width: 22,
                          height: 22,
                          fontSize: "0.7rem",
                          cursor: "pointer",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          padding: 0,
                        }}
                      >
                        ✓
                      </button>
                      <button
                        onClick={() => handleAction("dismissed")}
                        title="Dismiss"
                        style={{
                          background: `${palette.muted}15`,
                          border: `1px solid ${palette.muted}33`,
                          color: palette.muted,
                          borderRadius: 4,
                          width: 22,
                          height: 22,
                          fontSize: "0.65rem",
                          cursor: "pointer",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          padding: 0,
                        }}
                      >
                        ✕
                      </button>
                    </div>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: "0.8rem", color: palette.fg }}>{c.commitment}</div>
                      <div style={{ fontSize: "0.65rem", color: palette.muted, marginTop: "0.15rem" }}>
                        to {c.recipient}
                        {c.deadline && (
                          <span style={{ color: palette.chaos }}> · {c.deadline}</span>
                        )}
                        {isStale && (
                          <span
                            style={{
                              marginLeft: "0.35rem",
                              background: `${palette.chaos}22`,
                              color: palette.chaos,
                              padding: "0.05rem 0.3rem",
                              borderRadius: 8,
                              fontSize: "0.575rem",
                            }}
                          >
                            {ageDays}d ago
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
          </div>
        </div>
      )}

      {/* Subscriptions & Renewals (separate from people commitments) */}
      {subscriptions.filter((s) => !hiddenSubscriptions.has(s.id || "")).length > 0 && (
        <div style={{ marginBottom: "1rem" }}>
          <div style={{ fontSize: "0.625rem", color: palette.muted, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "0.5rem" }}>
            Subscriptions & Renewals
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.4rem" }}>
            {subscriptions
              .filter((s) => !hiddenSubscriptions.has(s.id || ""))
              .map((s, i) => {
                const handleSubAction = (status: "done" | "dismissed") => {
                  if (!s.id) return;
                  setHiddenSubscriptions((prev) => { const next = new Set(prev); next.add(s.id!); return next; });
                  fetch(`/api/email/subscriptions/${s.id}`, {
                    method: "PATCH",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ status }),
                  }).catch(() => {
                    setHiddenSubscriptions((prev) => {
                      const next = new Set(prev);
                      next.delete(s.id!);
                      return next;
                    });
                  });
                };

                return (
                  <div
                    key={s.id || i}
                    style={{
                      background: palette.bg,
                      borderRadius: 6,
                      padding: "0.5rem 0.6rem",
                      borderLeft: `3px solid ${palette.accent}`,
                      display: "flex",
                      alignItems: "flex-start",
                      gap: "0.5rem",
                    }}
                  >
                    <div style={{ display: "flex", gap: "0.25rem", flexShrink: 0, paddingTop: "0.1rem" }}>
                      <button
                        onClick={() => handleSubAction("done")}
                        title="Renewed / Handled"
                        style={{
                          background: `${palette.balanced}22`,
                          border: `1px solid ${palette.balanced}44`,
                          color: palette.balanced,
                          borderRadius: 4,
                          width: 22,
                          height: 22,
                          fontSize: "0.7rem",
                          cursor: "pointer",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          padding: 0,
                        }}
                      >
                        ✓
                      </button>
                      <button
                        onClick={() => handleSubAction("dismissed")}
                        title="Dismiss"
                        style={{
                          background: `${palette.muted}15`,
                          border: `1px solid ${palette.muted}33`,
                          color: palette.muted,
                          borderRadius: 4,
                          width: 22,
                          height: 22,
                          fontSize: "0.65rem",
                          cursor: "pointer",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          padding: 0,
                        }}
                      >
                        ✕
                      </button>
                    </div>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: "0.8rem", color: palette.fg }}>{s.commitment}</div>
                      <div style={{ fontSize: "0.65rem", color: palette.muted, marginTop: "0.15rem" }}>
                        {s.subject && (
                          <span>{s.subject.length > 40 ? s.subject.slice(0, 40) + "..." : s.subject}</span>
                        )}
                        {s.deadline && (
                          <span style={{ color: palette.chaos }}> · {s.deadline}</span>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
          </div>
        </div>
      )}

      {/* FYI Items (collapsible) */}
      {fyi_items.length > 0 && (
        <div style={{ marginBottom: "0.75rem" }}>
          <button
            onClick={() => setShowFyi(!showFyi)}
            style={{
              background: "transparent",
              border: "none",
              color: palette.accent,
              fontSize: "0.75rem",
              cursor: "pointer",
              padding: 0,
              marginBottom: showFyi ? "0.5rem" : 0,
            }}
          >
            {showFyi ? "Hide" : "Show"} {fyi_items.length} FYI items
          </button>
          {showFyi && (
            <div style={{ display: "flex", flexDirection: "column", gap: "0.35rem" }}>
              {fyi_items.map((item, i) => (
                <div key={i} style={{
                  background: palette.bg,
                  borderRadius: 6,
                  padding: "0.5rem 0.6rem",
                }}>
                  <div style={{ fontSize: "0.75rem", color: palette.fg }}>
                    <span style={{ fontWeight: 500 }}>{item.sender_name || item.sender}</span>
                    {" — "}
                    {item.one_line_summary || item.subject}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Noise Summary (collapsible) */}
      {noise_summary && noise_summary.count > 0 && (
        <div style={{ marginBottom: "0.75rem" }}>
          <button
            onClick={() => setShowNoise(!showNoise)}
            style={{
              background: "transparent",
              border: "none",
              color: palette.muted,
              fontSize: "0.75rem",
              cursor: "pointer",
              padding: 0,
              marginBottom: showNoise ? "0.5rem" : 0,
            }}
          >
            {noise_summary.count} routine emails {showNoise ? "(hide)" : "(details)"}
          </button>
          {showNoise && noise_summary.categories && (
            <div style={{ display: "flex", gap: "0.4rem", flexWrap: "wrap" }}>
              {Object.entries(noise_summary.categories).map(([cat, count]) => (
                <span key={cat} style={{
                  background: `${palette.muted}15`,
                  color: palette.muted,
                  padding: "0.2rem 0.5rem",
                  borderRadius: 10,
                  fontSize: "0.65rem",
                }}>
                  {cat}: {count}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Footer */}
      <div style={{ fontSize: "0.625rem", color: palette.muted, textAlign: "center", paddingTop: "0.25rem", borderTop: `1px solid ${palette.border}` }}>
        {digest.emails_analyzed} emails analyzed · Updated {timeAgo(digest.created_at)}
      </div>

      {/* Email Peek Modal */}
      {peekItem && (
        <EmailPeekModal
          item={peekItem}
          onClose={() => setPeekItem(null)}
        />
      )}
    </Card>
  );
}

// ─────────────────────────────────────────────────────────────
// Connections Card
// ─────────────────────────────────────────────────────────────
function ConnectionsCard({
  emailStatus,
  connecting,
  onConnectGmail,
  onDisconnectGmail,
}: {
  emailStatus: EmailStatus | null;
  connecting: boolean;
  onConnectGmail: () => void;
  onDisconnectGmail: () => void;
}) {
  const isConnected = emailStatus?.connected === true;

  return (
    <Card title="Connections" icon={<IconLink size={18} />}>
      {/* Gmail Connection */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "0.75rem",
          background: palette.bg,
          borderRadius: 8,
          marginBottom: "0.5rem",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <div
            style={{
              width: 40,
              height: 40,
              borderRadius: 8,
              background: isConnected ? `${palette.balanced}22` : `${palette.muted}22`,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <IconMail size={20} />
          </div>
          <div>
            <div style={{ fontWeight: 500, color: palette.fg }}>Gmail</div>
            <div style={{ fontSize: "0.75rem", color: palette.muted }}>
              {isConnected
                ? emailStatus?.email || "Connected"
                : "Connect for email insights"}
            </div>
          </div>
        </div>

        {isConnected ? (
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <span
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.25rem",
                color: palette.balanced,
                fontSize: "0.75rem",
              }}
            >
              <IconCheck size={14} />
              Connected
            </span>
            <button
              onClick={onDisconnectGmail}
              style={{
                background: "none",
                border: "none",
                color: palette.muted,
                cursor: "pointer",
                padding: "0.25rem",
                fontSize: "0.75rem",
              }}
            >
              Disconnect
            </button>
          </div>
        ) : (
          <button
            onClick={onConnectGmail}
            disabled={connecting}
            style={{
              background: palette.accent,
              border: "none",
              borderRadius: 6,
              color: palette.fg,
              padding: "0.5rem 1rem",
              fontSize: "0.875rem",
              fontWeight: 500,
              cursor: connecting ? "not-allowed" : "pointer",
              opacity: connecting ? 0.7 : 1,
              display: "flex",
              alignItems: "center",
              gap: "0.5rem",
            }}
          >
            {connecting ? (
              <>
                <IconLoader size={14} />
                Connecting...
              </>
            ) : (
              "Connect"
            )}
          </button>
        )}
      </div>

      {/* Sync status info */}
      {isConnected && emailStatus?.messages_synced !== undefined && (
        <div style={{ fontSize: "0.75rem", color: palette.muted, paddingLeft: "0.75rem" }}>
          {emailStatus.messages_synced} emails analyzed
          {emailStatus.last_sync_at && (
            <> · Last sync: {new Date(emailStatus.last_sync_at).toLocaleDateString()}</>
          )}
        </div>
      )}

      {/* Privacy note */}
      <div
        style={{
          marginTop: "1rem",
          padding: "0.75rem",
          background: `${palette.accent}11`,
          borderRadius: 8,
          fontSize: "0.75rem",
          color: palette.muted,
        }}
      >
        <strong style={{ color: palette.fg }}>Privacy:</strong> Sakhi reads email metadata
        (senders, timestamps) to detect patterns. Email content is never stored.
      </div>
    </Card>
  );
}
