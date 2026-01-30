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
  accentHover: "#818cf8",
  cardBg: "#18191d",
  border: "#27272a",
  success: "#22c55e",
  vata: "#e8c547",    // Warm yellow for Adaptive
  pitta: "#ef6461",   // Warm red for Performance
  kapha: "#4ecdc4",   // Teal for Conservation
};

// =============================================================================
// TYPES
// =============================================================================

interface OperatingSystemResult {
  operating_system: string;
  primary: string;
  secondary: string | null;
  dosha_baseline: {
    vata: number;
    pitta: number;
    kapha: number;
  };
  life_context: Record<string, unknown>;
  decision_profile: Record<string, unknown>;
  stored: boolean;
}

// Operating System descriptions and content
const OS_CONTENT: Record<string, {
  tagline: string;
  description: string;
  strengths: string[];
  watchFor: string[];
  color: string;
}> = {
  "Adaptive": {
    tagline: "Quick-thinking & Creative",
    description: "You thrive on variety and change. Your mind moves quickly, making connections others miss. You're naturally creative and adaptable.",
    strengths: ["Quick thinking", "Creative problem-solving", "Adaptable to change", "Enthusiastic starter"],
    watchFor: ["Scattered energy", "Difficulty with routine", "Overcommitting", "Sleep disruption under stress"],
    color: palette.vata,
  },
  "Performance": {
    tagline: "Driven & Focused",
    description: "You're naturally goal-oriented with strong focus and drive. You transform ideas into reality and thrive when there's a clear target.",
    strengths: ["Strong focus", "Natural leadership", "Decisive action", "Results-oriented"],
    watchFor: ["Pushing past limits", "Impatience with others", "Burnout from intensity", "Difficulty relaxing"],
    color: palette.pitta,
  },
  "Conservation": {
    tagline: "Steady & Grounded",
    description: "You bring stability and endurance to everything you do. Your calm presence and reliability make you a natural anchor for others.",
    strengths: ["Steady energy", "Patient & reliable", "Strong memory", "Calm under pressure"],
    watchFor: ["Resistance to change", "Holding on too long", "Low energy dips", "Comfort zone attachment"],
    color: palette.kapha,
  },
  "Adaptive-Performance": {
    tagline: "Creative Drive",
    description: "You blend creativity with execution. Ideas flow easily, and you have the drive to make them real. You're both innovative and goal-oriented.",
    strengths: ["Innovation + execution", "Quick adaptation", "Passionate pursuit", "Natural problem solver"],
    watchFor: ["Burnout from intensity", "Scattered focus", "Impatience with slow progress", "Difficulty with routine"],
    color: palette.vata,
  },
  "Performance-Conservation": {
    tagline: "Driven Endurance",
    description: "You combine ambition with staying power. You can push hard and sustain effort over time. A powerful combination for long-term goals.",
    strengths: ["Sustained focus", "Patient ambition", "Reliable execution", "Strategic thinking"],
    watchFor: ["Stubbornness", "Over-controlling", "Difficulty delegating", "Slow to pivot"],
    color: palette.pitta,
  },
  "Adaptive-Conservation": {
    tagline: "Creative Stability",
    description: "You blend imagination with groundedness. You can dream big while staying practical. This makes you both visionary and dependable.",
    strengths: ["Grounded creativity", "Flexible stability", "Patient innovation", "Calm adaptability"],
    watchFor: ["Analysis paralysis", "Slow starts", "Comfort zone creativity", "Difficulty with urgency"],
    color: palette.kapha,
  },
  "Balanced": {
    tagline: "Natural Equilibrium",
    description: "You have a naturally balanced constitution with no single dominant tendency. This gives you flexibility across different situations.",
    strengths: ["Situational flexibility", "Even temperament", "Broad adaptability", "Natural balance"],
    watchFor: ["Lack of specialization", "Difficulty with extremes", "May need more structure", "Can drift without focus"],
    color: palette.accent,
  },
};

// =============================================================================
// COMPONENT
// =============================================================================

export default function OnboardingResultPage() {
  return (
    <Suspense fallback={null}>
      <OnboardingResultContent />
    </Suspense>
  );
}

function OnboardingResultContent() {
  const router = useRouter();
  const search = useSearchParams();
  const user = search?.get("user");

  const [result, setResult] = useState<OperatingSystemResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showDetails, setShowDetails] = useState(false);

  // Parse result from URL params (passed from onboarding)
  useEffect(() => {
    const resultParam = search?.get("result");
    if (resultParam) {
      try {
        const parsed = JSON.parse(decodeURIComponent(resultParam));
        setResult(parsed);
        setLoading(false);
      } catch {
        setError("Failed to load your results");
        setLoading(false);
      }
    } else {
      // If no result param, try fetching from API
      if (user) {
        fetchOperatingSystem(user);
      } else {
        setError("No user found");
        setLoading(false);
      }
    }
  }, [search, user]);

  const fetchOperatingSystem = async (userId: string) => {
    try {
      const response = await fetch(`/api/profile/operating-system?user=${userId}`);
      if (response.ok) {
        const data = await response.json();
        setResult(data);
      } else {
        setError("Could not load your Operating System");
      }
    } catch {
      setError("Failed to connect to server");
    } finally {
      setLoading(false);
    }
  };

  const handleContinue = useCallback(() => {
    const nextPath = user
      ? `/experience/converse?user=${encodeURIComponent(user)}`
      : "/experience/converse";
    router.push(nextPath as Route);
  }, [user, router]);

  // Get content for this OS type
  const osType = result?.operating_system || "Balanced";
  const content = OS_CONTENT[osType] || OS_CONTENT["Balanced"];
  const doshaBaseline = result?.dosha_baseline || { vata: 0.33, pitta: 0.33, kapha: 0.34 };

  // Styles
  const containerStyle: React.CSSProperties = {
    minHeight: "100vh",
    background: palette.bg,
    color: palette.fg,
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Inter, sans-serif',
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    padding: "60px 24px 120px",
  };

  const mainStyle: React.CSSProperties = {
    maxWidth: "560px",
    width: "100%",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
  };

  const labelStyle: React.CSSProperties = {
    fontSize: "13px",
    textTransform: "uppercase",
    letterSpacing: "0.1em",
    color: palette.muted,
    marginBottom: "12px",
  };

  const osTypeStyle: React.CSSProperties = {
    fontSize: "36px",
    fontWeight: 600,
    color: content.color,
    marginBottom: "8px",
    textAlign: "center",
    letterSpacing: "-0.02em",
  };

  const taglineStyle: React.CSSProperties = {
    fontSize: "18px",
    color: palette.muted,
    marginBottom: "32px",
  };

  const descriptionStyle: React.CSSProperties = {
    fontSize: "16px",
    lineHeight: 1.7,
    color: palette.fg,
    textAlign: "center",
    marginBottom: "40px",
    opacity: 0.9,
  };

  const doshaBarContainerStyle: React.CSSProperties = {
    width: "100%",
    marginBottom: "40px",
  };

  const doshaRowStyle: React.CSSProperties = {
    display: "flex",
    alignItems: "center",
    marginBottom: "16px",
    gap: "12px",
  };

  const doshaLabelStyle: React.CSSProperties = {
    width: "100px",
    fontSize: "14px",
    color: palette.muted,
  };

  const doshaBarBgStyle: React.CSSProperties = {
    flex: 1,
    height: "8px",
    background: palette.border,
    borderRadius: "4px",
    overflow: "hidden",
  };

  const cardStyle: React.CSSProperties = {
    width: "100%",
    background: palette.cardBg,
    borderRadius: "16px",
    padding: "24px",
    marginBottom: "20px",
  };

  const cardTitleStyle: React.CSSProperties = {
    fontSize: "14px",
    fontWeight: 600,
    color: palette.fg,
    marginBottom: "16px",
    display: "flex",
    alignItems: "center",
    gap: "8px",
  };

  const listStyle: React.CSSProperties = {
    listStyle: "none",
    padding: 0,
    margin: 0,
  };

  const listItemStyle: React.CSSProperties = {
    fontSize: "14px",
    color: palette.muted,
    padding: "8px 0",
    display: "flex",
    alignItems: "flex-start",
    gap: "10px",
  };

  const footerStyle: React.CSSProperties = {
    position: "fixed",
    bottom: 0,
    left: 0,
    right: 0,
    padding: "20px 24px 32px",
    background: `linear-gradient(transparent, ${palette.bg} 30%)`,
    display: "flex",
    justifyContent: "center",
  };

  const buttonStyle: React.CSSProperties = {
    padding: "16px 48px",
    borderRadius: "12px",
    border: "none",
    background: palette.accent,
    color: "#fff",
    fontSize: "16px",
    fontWeight: 500,
    cursor: "pointer",
    transition: "all 150ms ease",
  };

  const toggleStyle: React.CSSProperties = {
    fontSize: "14px",
    color: palette.accent,
    cursor: "pointer",
    marginBottom: "24px",
    display: "flex",
    alignItems: "center",
    gap: "6px",
  };

  if (loading) {
    return (
      <div style={containerStyle}>
        <div style={mainStyle}>
          <p style={{ color: palette.muted }}>Analyzing your responses...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={containerStyle}>
        <div style={mainStyle}>
          <p style={{ color: "#ef4444", marginBottom: "24px" }}>{error}</p>
          <button style={buttonStyle} onClick={handleContinue}>
            Continue anyway
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={containerStyle}>
      <main style={mainStyle}>
        {/* Label */}
        <p style={labelStyle}>Your Operating System</p>

        {/* OS Type */}
        <h1 style={osTypeStyle}>{osType}</h1>
        <p style={taglineStyle}>{content.tagline}</p>

        {/* Description */}
        <p style={descriptionStyle}>{content.description}</p>

        {/* Dosha Breakdown */}
        <div style={doshaBarContainerStyle}>
          <div style={doshaRowStyle}>
            <span style={doshaLabelStyle}>Adaptive</span>
            <div style={doshaBarBgStyle}>
              <div
                style={{
                  width: `${doshaBaseline.vata * 100}%`,
                  height: "100%",
                  background: palette.vata,
                  borderRadius: "4px",
                  transition: "width 600ms ease",
                }}
              />
            </div>
            <span style={{ ...doshaLabelStyle, width: "40px", textAlign: "right" }}>
              {Math.round(doshaBaseline.vata * 100)}%
            </span>
          </div>
          <div style={doshaRowStyle}>
            <span style={doshaLabelStyle}>Performance</span>
            <div style={doshaBarBgStyle}>
              <div
                style={{
                  width: `${doshaBaseline.pitta * 100}%`,
                  height: "100%",
                  background: palette.pitta,
                  borderRadius: "4px",
                  transition: "width 600ms ease",
                }}
              />
            </div>
            <span style={{ ...doshaLabelStyle, width: "40px", textAlign: "right" }}>
              {Math.round(doshaBaseline.pitta * 100)}%
            </span>
          </div>
          <div style={doshaRowStyle}>
            <span style={doshaLabelStyle}>Conservation</span>
            <div style={doshaBarBgStyle}>
              <div
                style={{
                  width: `${doshaBaseline.kapha * 100}%`,
                  height: "100%",
                  background: palette.kapha,
                  borderRadius: "4px",
                  transition: "width 600ms ease",
                }}
              />
            </div>
            <span style={{ ...doshaLabelStyle, width: "40px", textAlign: "right" }}>
              {Math.round(doshaBaseline.kapha * 100)}%
            </span>
          </div>
        </div>

        {/* Toggle for details */}
        <div style={toggleStyle} onClick={() => setShowDetails(!showDetails)}>
          <span>{showDetails ? "Hide details" : "See your strengths & patterns"}</span>
          <svg
            width="16"
            height="16"
            viewBox="0 0 16 16"
            fill="none"
            style={{
              transform: showDetails ? "rotate(180deg)" : "rotate(0deg)",
              transition: "transform 200ms ease",
            }}
          >
            <path d="M4 6L8 10L12 6" stroke={palette.accent} strokeWidth="2" strokeLinecap="round" />
          </svg>
        </div>

        {/* Strengths & Watch For Cards */}
        {showDetails && (
          <>
            <div style={cardStyle}>
              <h3 style={cardTitleStyle}>
                <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
                  <path
                    d="M9 1L11.5 6.5L17 7.5L13 11.5L14 17L9 14.5L4 17L5 11.5L1 7.5L6.5 6.5L9 1Z"
                    stroke={palette.success}
                    strokeWidth="1.5"
                    fill="none"
                  />
                </svg>
                Your Strengths
              </h3>
              <ul style={listStyle}>
                {content.strengths.map((strength, i) => (
                  <li key={i} style={listItemStyle}>
                    <span style={{ color: palette.success }}>+</span>
                    <span>{strength}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div style={cardStyle}>
              <h3 style={cardTitleStyle}>
                <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
                  <circle cx="9" cy="9" r="7" stroke={palette.vata} strokeWidth="1.5" />
                  <path d="M9 5V9" stroke={palette.vata} strokeWidth="1.5" strokeLinecap="round" />
                  <circle cx="9" cy="12" r="1" fill={palette.vata} />
                </svg>
                Patterns to Watch
              </h3>
              <ul style={listStyle}>
                {content.watchFor.map((pattern, i) => (
                  <li key={i} style={listItemStyle}>
                    <span style={{ color: palette.vata }}>~</span>
                    <span>{pattern}</span>
                  </li>
                ))}
              </ul>
            </div>
          </>
        )}

        {/* Note about soft constraints */}
        <p
          style={{
            fontSize: "13px",
            color: palette.muted,
            textAlign: "center",
            lineHeight: 1.6,
            marginTop: "8px",
            opacity: 0.7,
          }}
        >
          This is your baseline tendency, not a fixed identity.
          <br />
          Sakhi will learn and adapt as you share more over time.
        </p>
      </main>

      {/* Footer */}
      <footer style={footerStyle}>
        <button
          style={buttonStyle}
          onClick={handleContinue}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = palette.accentHover;
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = palette.accent;
          }}
        >
          Start a Conversation
        </button>
      </footer>
    </div>
  );
}
