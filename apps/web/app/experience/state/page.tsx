"use client";

import { Suspense, useState, useEffect, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import type React from "react";
import type { Route } from "next";

export const dynamic = "force-dynamic";

const palette = {
  bg: "#0e0f12",
  fg: "#f4f4f5",
  muted: "#a1a1aa",
  accent: "#6366f1",
  cardBg: "#18191d",
  border: "#27272a",
  // Friction state colors
  chaos: "#e8c547",
  intensity: "#ef6461",
  stagnation: "#4787e8",
  balanced: "#22c55e",
  // Mode colors
  clarity: "#22c55e",
  activation: "#f59e0b",
  recovery: "#6366f1",
};

// =============================================================================
// TYPES
// =============================================================================

interface CurrentState {
  timestamp: string;
  operating_mode: {
    mode: string;
    guna_dominant: string;
    guna_scores: {
      sattva: number;
      rajas: number;
      tamas: number;
    };
    description: string;
  };
  friction_state: {
    state: string | null;
    dosha_elevated: string | null;
    severity: string;
    description: string;
  };
  baseline_drift: {
    percentage: number;
    direction: string;
    primary_contributor: string | null;
    description: string;
  };
  current_dosha: {
    vata: number;
    pitta: number;
    kapha: number;
  };
}

interface Recommendation {
  action: string;
  why: string;
  category: string;
  icon: string;
}

interface RecommendationsData {
  timestamp: string;
  friction_state: string | null;
  recommendations: Recommendation[];
  pattern_insight: {
    pattern: string;
    suggestion: string;
  } | null;
}

// =============================================================================
// COMPONENT
// =============================================================================

export default function TodayStatePage() {
  return (
    <Suspense fallback={null}>
      <TodayStateContent />
    </Suspense>
  );
}

function TodayStateContent() {
  const router = useRouter();
  const search = useSearchParams();
  const user = search?.get("user");

  const [state, setState] = useState<CurrentState | null>(null);
  const [recommendations, setRecommendations] = useState<RecommendationsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch current state and recommendations
  useEffect(() => {
    const fetchData = async () => {
      if (!user) {
        // Try to get user from auth
        try {
          const authRes = await fetch("/api/auth/me");
          if (authRes.ok) {
            const authData = await authRes.json();
            // Redirect with user param
            router.replace(`/experience/state?user=${encodeURIComponent(authData.person_id)}` as Route);
            return;
          }
        } catch {
          setError("Please sign in to view your state");
          setLoading(false);
          return;
        }
      }

      try {
        // Fetch current state
        const stateRes = await fetch(`/api/friction/state/current?user=${user}`);
        if (stateRes.ok) {
          const stateData = await stateRes.json();
          setState(stateData);
        }

        // Fetch recommendations
        const recRes = await fetch(`/api/friction/recommendations?user=${user}`);
        if (recRes.ok) {
          const recData = await recRes.json();
          setRecommendations(recData);
        }
      } catch (err) {
        console.error("Error fetching state:", err);
        setError("Could not load your current state");
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [user, router]);

  const goBack = useCallback(() => {
    const path = user
      ? `/experience/converse?user=${encodeURIComponent(user)}`
      : "/experience/converse";
    router.push(path as Route);
  }, [router, user]);

  // Get friction state color
  const getFrictionColor = (frictionState: string | null) => {
    if (!frictionState) return palette.balanced;
    if (frictionState.includes("Chaos")) return palette.chaos;
    if (frictionState.includes("Intensity")) return palette.intensity;
    if (frictionState.includes("Stagnation")) return palette.stagnation;
    return palette.balanced;
  };

  // Get mode color
  const getModeColor = (mode: string) => {
    switch (mode) {
      case "Clarity":
        return palette.clarity;
      case "Activation":
        return palette.activation;
      case "Recovery":
        return palette.recovery;
      default:
        return palette.muted;
    }
  };

  // Get icon for recommendation
  const getRecIcon = (icon: string) => {
    const icons: Record<string, string> = {
      breath: "🌬️",
      movement: "🚶",
      drink: "☕",
      food: "🍵",
      rest: "😴",
      focus: "🎯",
      connect: "💬",
      nature: "🌿",
      clock: "⏰",
      heart: "💚",
      pause: "⏸️",
      delegate: "👋",
      start: "▶️",
      plan: "📋",
      check: "✓",
    };
    return icons[icon] || "•";
  };

  // =============================================================================
  // STYLES
  // =============================================================================

  const containerStyle: React.CSSProperties = {
    minHeight: "100vh",
    background: palette.bg,
    color: palette.fg,
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Inter, sans-serif',
    padding: "24px",
    paddingBottom: "100px",
  };

  const headerStyle: React.CSSProperties = {
    display: "flex",
    alignItems: "center",
    gap: "12px",
    marginBottom: "32px",
  };

  const backButtonStyle: React.CSSProperties = {
    width: "40px",
    height: "40px",
    borderRadius: "50%",
    border: `1px solid ${palette.border}`,
    background: "transparent",
    color: palette.fg,
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  };

  const titleStyle: React.CSSProperties = {
    fontSize: "20px",
    fontWeight: 600,
  };

  const sectionStyle: React.CSSProperties = {
    marginBottom: "32px",
  };

  const sectionTitleStyle: React.CSSProperties = {
    fontSize: "13px",
    textTransform: "uppercase",
    letterSpacing: "0.08em",
    color: palette.muted,
    marginBottom: "16px",
  };

  const cardStyle: React.CSSProperties = {
    background: palette.cardBg,
    borderRadius: "16px",
    padding: "20px",
    marginBottom: "16px",
  };

  const frictionBadgeStyle = (frictionState: string | null): React.CSSProperties => ({
    display: "inline-block",
    padding: "8px 16px",
    borderRadius: "20px",
    background: `${getFrictionColor(frictionState)}20`,
    color: getFrictionColor(frictionState),
    fontSize: "14px",
    fontWeight: 500,
    marginBottom: "12px",
  });

  const modeBadgeStyle = (mode: string): React.CSSProperties => ({
    display: "inline-flex",
    alignItems: "center",
    gap: "8px",
    padding: "6px 12px",
    borderRadius: "12px",
    background: `${getModeColor(mode)}15`,
    color: getModeColor(mode),
    fontSize: "13px",
  });

  const meterContainerStyle: React.CSSProperties = {
    marginTop: "16px",
  };

  const meterRowStyle: React.CSSProperties = {
    display: "flex",
    alignItems: "center",
    marginBottom: "12px",
    gap: "12px",
  };

  const meterLabelStyle: React.CSSProperties = {
    width: "80px",
    fontSize: "13px",
    color: palette.muted,
  };

  const meterBarBgStyle: React.CSSProperties = {
    flex: 1,
    height: "6px",
    background: palette.border,
    borderRadius: "3px",
    overflow: "hidden",
  };

  const recCardStyle: React.CSSProperties = {
    background: palette.cardBg,
    borderRadius: "12px",
    padding: "16px",
    marginBottom: "12px",
    display: "flex",
    gap: "14px",
  };

  const recIconStyle: React.CSSProperties = {
    fontSize: "20px",
    flexShrink: 0,
  };

  const recContentStyle: React.CSSProperties = {
    flex: 1,
  };

  const recActionStyle: React.CSSProperties = {
    fontSize: "15px",
    color: palette.fg,
    marginBottom: "4px",
    fontWeight: 500,
  };

  const recWhyStyle: React.CSSProperties = {
    fontSize: "13px",
    color: palette.muted,
    lineHeight: 1.5,
  };

  const insightCardStyle: React.CSSProperties = {
    background: `${palette.accent}15`,
    border: `1px solid ${palette.accent}40`,
    borderRadius: "12px",
    padding: "16px",
    marginTop: "20px",
  };

  const insightTitleStyle: React.CSSProperties = {
    fontSize: "13px",
    color: palette.accent,
    marginBottom: "8px",
    fontWeight: 500,
  };

  const insightTextStyle: React.CSSProperties = {
    fontSize: "14px",
    color: palette.fg,
    lineHeight: 1.6,
  };

  // =============================================================================
  // RENDER
  // =============================================================================

  if (loading) {
    return (
      <div style={{ ...containerStyle, display: "flex", alignItems: "center", justifyContent: "center" }}>
        <p style={{ color: palette.muted }}>Loading your state...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div style={containerStyle}>
        <header style={headerStyle}>
          <button style={backButtonStyle} onClick={goBack}>
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <path d="M12 15L7 10L12 5" stroke={palette.fg} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
          <h1 style={titleStyle}>Today&apos;s State</h1>
        </header>
        <p style={{ color: palette.muted, textAlign: "center", marginTop: "40px" }}>{error}</p>
      </div>
    );
  }

  const frictionState = (state?.friction_state?.state ?? null) as string | null;
  const operatingMode = state?.operating_mode?.mode || "Clarity";
  const driftPercent = state?.baseline_drift?.percentage || 0;

  return (
    <div style={containerStyle}>
      {/* Header */}
      <header style={headerStyle}>
        <button style={backButtonStyle} onClick={goBack}>
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
            <path d="M12 15L7 10L12 5" stroke={palette.fg} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
          <h1 style={titleStyle}>Today&apos;s State</h1>
      </header>

      {/* Current State Overview */}
      <section style={sectionStyle}>
        <div style={cardStyle}>
          {/* Friction State */}
          <div style={frictionBadgeStyle(frictionState)}>
            {frictionState || "Balanced"}
          </div>

          <p style={{ fontSize: "15px", color: palette.fg, marginBottom: "16px", lineHeight: 1.6 }}>
            {state?.friction_state?.description || "You're operating close to your natural baseline."}
          </p>

          {/* Operating Mode */}
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <span style={{ fontSize: "13px", color: palette.muted }}>Operating Mode</span>
            <div style={modeBadgeStyle(operatingMode)}>
              <span style={{
                width: "8px",
                height: "8px",
                borderRadius: "50%",
                background: getModeColor(operatingMode),
              }} />
              {operatingMode}
            </div>
          </div>

          {/* Baseline Drift */}
          {driftPercent > 0 && (
            <div style={{ marginTop: "16px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <span style={{ fontSize: "13px", color: palette.muted }}>Drift from baseline</span>
              <span style={{ fontSize: "14px", color: driftPercent > 30 ? palette.chaos : palette.muted }}>
                {driftPercent}%
              </span>
            </div>
          )}

          {/* Current Dosha Distribution */}
          {state?.current_dosha && (
            <div style={meterContainerStyle}>
              <div style={meterRowStyle}>
                <span style={meterLabelStyle}>Adaptive</span>
                <div style={meterBarBgStyle}>
                  <div style={{
                    width: `${state.current_dosha.vata * 100}%`,
                    height: "100%",
                    background: palette.chaos,
                    borderRadius: "3px",
                  }} />
                </div>
                <span style={{ ...meterLabelStyle, width: "40px", textAlign: "right" }}>
                  {Math.round(state.current_dosha.vata * 100)}%
                </span>
              </div>
              <div style={meterRowStyle}>
                <span style={meterLabelStyle}>Performance</span>
                <div style={meterBarBgStyle}>
                  <div style={{
                    width: `${state.current_dosha.pitta * 100}%`,
                    height: "100%",
                    background: palette.intensity,
                    borderRadius: "3px",
                  }} />
                </div>
                <span style={{ ...meterLabelStyle, width: "40px", textAlign: "right" }}>
                  {Math.round(state.current_dosha.pitta * 100)}%
                </span>
              </div>
              <div style={meterRowStyle}>
                <span style={meterLabelStyle}>Conservation</span>
                <div style={meterBarBgStyle}>
                  <div style={{
                    width: `${state.current_dosha.kapha * 100}%`,
                    height: "100%",
                    background: palette.stagnation,
                    borderRadius: "3px",
                  }} />
                </div>
                <span style={{ ...meterLabelStyle, width: "40px", textAlign: "right" }}>
                  {Math.round(state.current_dosha.kapha * 100)}%
                </span>
              </div>
            </div>
          )}
        </div>
      </section>

      {/* Recommendations */}
      {recommendations?.recommendations && recommendations.recommendations.length > 0 && (
        <section style={sectionStyle}>
          <h2 style={sectionTitleStyle}>What might help right now</h2>

          {recommendations.recommendations.map((rec, i) => (
            <div key={i} style={recCardStyle}>
              <span style={recIconStyle}>{getRecIcon(rec.icon)}</span>
              <div style={recContentStyle}>
                <div style={recActionStyle}>{rec.action}</div>
                <div style={recWhyStyle}>{rec.why}</div>
              </div>
            </div>
          ))}

          {/* Pattern Insight */}
          {recommendations.pattern_insight && (
            <div style={insightCardStyle}>
              <div style={insightTitleStyle}>Pattern noticed</div>
              <p style={insightTextStyle}>
                {recommendations.pattern_insight.pattern}
              </p>
              <p style={{ ...insightTextStyle, marginTop: "8px", color: palette.muted }}>
                <strong>Try:</strong> {recommendations.pattern_insight.suggestion}
              </p>
            </div>
          )}
        </section>
      )}

      {/* Mode Description */}
      {state?.operating_mode?.description && (
        <section style={sectionStyle}>
          <h2 style={sectionTitleStyle}>How you&apos;re running</h2>
          <div style={cardStyle}>
            <p style={{ fontSize: "14px", color: palette.fg, lineHeight: 1.7 }}>
              {state.operating_mode.description}
            </p>
          </div>
        </section>
      )}
    </div>
  );
}
