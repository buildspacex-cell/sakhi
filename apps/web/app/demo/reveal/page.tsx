"use client";

import { useState, useCallback } from "react";
import Link from "next/link";
import DemoModeBadge from "../components/DemoModeBadge";

/**
 * The Reveal Demo - Act 4
 * ------------------------
 * Shows HOW Sakhi knows you:
 * - Causal reasoning (Why am I feeling X?)
 * - Pattern matching
 * - Ayurvedic intelligence
 * - Memory connections
 *
 * Uses the backend API: POST /api/demo/run/reflection
 */

export const dynamic = "force-dynamic";

// Color palette
const palette = {
  bg: "#0e0f12",
  cardBg: "#1a1b1e",
  fg: "#f4f4f5",
  muted: "#71717a",
  accent: "#f43f5e", // Rose for this act
  accentDim: "rgba(244, 63, 94, 0.15)",
  vata: "#818cf8",
  pitta: "#f97316",
  kapha: "#22c55e",
  success: "#22c55e",
  divider: "#27272a",
};

interface Cause {
  cause: string;
  correlation: number;
  explanation: string;
}

interface ReflectionResult {
  symptom: string;
  dosha_context: string;
  primary_causes: Cause[];
  contributing_factors: Cause[];
  seasonal_influence: string | null;
  personal_pattern_match: boolean;
  explanation: string;
}

// Symptoms for demo
const symptoms = [
  { value: "scattered", label: "Scattered", icon: "🌀", dosha: "vata" },
  { value: "anxious", label: "Anxious", icon: "😰", dosha: "vata" },
  { value: "irritable", label: "Irritable", icon: "😤", dosha: "pitta" },
  { value: "sluggish", label: "Sluggish", icon: "😴", dosha: "kapha" },
];

export default function RevealDemo() {
  const [selectedSymptom, setSelectedSymptom] = useState("scattered");
  const [result, setResult] = useState<ReflectionResult | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showArchitecture, setShowArchitecture] = useState(false);

  const runReflection = useCallback(async () => {
    if (isRunning) return;
    setIsRunning(true);
    setResult(null);
    setError(null);

    try {
      const response = await fetch(`/api/demo/run/reflection?symptom=${selectedSymptom}`, {
        method: "POST",
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }

      const data = await response.json();
      setResult(data.result);
    } catch (err) {
      console.error("Reflection error:", err);
      setError(err instanceof Error ? err.message : "Failed to run reflection");
      // Fallback to simulated result
      setResult(getSimulatedResult(selectedSymptom));
    } finally {
      setIsRunning(false);
    }
  }, [isRunning, selectedSymptom]);

  const getDoshaColor = (dosha: string) => {
    switch (dosha?.toLowerCase()) {
      case "vata": return palette.vata;
      case "pitta": return palette.pitta;
      case "kapha": return palette.kapha;
      default: return palette.accent;
    }
  };

  return (
    <main style={styles.container}>
      {/* Header */}
      <header style={styles.header}>
        <Link href="/demo" style={styles.backLink}>← Back to Demo</Link>
        <h1 style={styles.title}>The Reveal: How Sakhi Knows</h1>
        <p style={styles.subtitle}>
          The secret behind Sakhi's deep understanding: Ayurveda + patterns + memory
        </p>
        <DemoModeBadge
          mode="partial"
          detail="Reflection runs against real APIs and falls back to simulated output if unavailable."
        />
      </header>

      {/* Symptom Selector */}
      <div style={styles.symptomSection}>
        <h3 style={styles.sectionTitle}>How are you feeling?</h3>
        <div style={styles.symptomGrid}>
          {symptoms.map((s) => (
            <button
              key={s.value}
              onClick={() => setSelectedSymptom(s.value)}
              style={{
                ...styles.symptomCard,
                borderColor: selectedSymptom === s.value ? getDoshaColor(s.dosha) : palette.divider,
                background: selectedSymptom === s.value ? `${getDoshaColor(s.dosha)}15` : palette.cardBg,
              }}
            >
              <span style={styles.symptomIcon}>{s.icon}</span>
              <span style={styles.symptomLabel}>{s.label}</span>
              <span style={{ ...styles.doshaBadge, color: getDoshaColor(s.dosha) }}>
                {s.dosha}
              </span>
            </button>
          ))}
        </div>

        <button
          onClick={runReflection}
          disabled={isRunning}
          style={isRunning ? styles.buttonDisabled : styles.button}
        >
          {isRunning ? "Analyzing..." : "Why am I feeling this?"}
        </button>
      </div>

      {error && (
        <div style={styles.errorMessage}>
          {error} (using simulated data)
        </div>
      )}

      {/* Results */}
      {result && (
        <div style={styles.resultsSection}>
          {/* Dosha Context */}
          <div style={styles.doshaCard}>
            <div style={styles.doshaHeader}>
              <span style={styles.doshaIcon}>🔥</span>
              <div>
                <h4 style={styles.doshaTitle}>Dosha Context</h4>
                <p style={styles.doshaText}>{result.dosha_context}</p>
              </div>
            </div>
          </div>

          {/* Primary Causes */}
          <div style={styles.causesCard}>
            <h4 style={styles.causesTitle}>Likely Causes</h4>
            <p style={styles.causesSubtitle}>Based on your patterns from the last 48 hours</p>

            {result.primary_causes.map((cause, i) => (
              <div key={i} style={styles.causeItem}>
                <div style={styles.causeHeader}>
                  <span style={styles.causeName}>{formatCauseName(cause.cause)}</span>
                  <div style={styles.correlationBar}>
                    <div
                      style={{
                        ...styles.correlationFill,
                        width: `${cause.correlation * 100}%`,
                        background: palette.accent,
                      }}
                    />
                  </div>
                  <span style={styles.correlationValue}>
                    {Math.round(cause.correlation * 100)}%
                  </span>
                </div>
                <p style={styles.causeExplanation}>{cause.explanation}</p>
              </div>
            ))}

            {result.contributing_factors.length > 0 && (
              <>
                <h5 style={styles.contributingTitle}>Contributing Factors</h5>
                {result.contributing_factors.map((factor, i) => (
                  <div key={i} style={styles.factorItem}>
                    <span style={styles.factorName}>{formatCauseName(factor.cause)}</span>
                    <span style={styles.factorCorrelation}>
                      {Math.round(factor.correlation * 100)}%
                    </span>
                  </div>
                ))}
              </>
            )}
          </div>

          {/* Explanation */}
          <div style={styles.explanationCard}>
            <h4 style={styles.explCardTitle}>Sakhi's Analysis</h4>
            <p style={styles.explCardText}>{result.explanation}</p>

            {result.personal_pattern_match && (
              <div style={styles.patternMatch}>
                <span style={styles.patternIcon}>🔄</span>
                <span>This matches a pattern we've seen before in your history</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Architecture Toggle */}
      <div style={styles.archToggle}>
        <button
          onClick={() => setShowArchitecture(!showArchitecture)}
          style={styles.archToggleButton}
        >
          {showArchitecture ? "Hide" : "Show"} How It Works
        </button>
      </div>

      {/* Architecture Explanation */}
      {showArchitecture && (
        <div style={styles.architectureSection}>
          <h3 style={styles.archTitle}>The Intelligence Stack</h3>

          <div style={styles.archDiagram}>
            <div style={styles.archLayer}>
              <span style={styles.archLayerIcon}>🧠</span>
              <div style={styles.archLayerContent}>
                <h4 style={styles.archLayerTitle}>Pattern Recognition</h4>
                <p style={styles.archLayerDesc}>
                  Sakhi learns correlations: "When you do X, you tend to feel Y"
                </p>
              </div>
            </div>

            <div style={styles.archArrow}>↓</div>

            <div style={styles.archLayer}>
              <span style={styles.archLayerIcon}>📚</span>
              <div style={styles.archLayerContent}>
                <h4 style={styles.archLayerTitle}>Ayurvedic Knowledge</h4>
                <p style={styles.archLayerDesc}>
                  5,000 years of wisdom about doshas, foods, behaviors, and balance
                </p>
              </div>
            </div>

            <div style={styles.archArrow}>↓</div>

            <div style={styles.archLayer}>
              <span style={styles.archLayerIcon}>💾</span>
              <div style={styles.archLayerContent}>
                <h4 style={styles.archLayerTitle}>Personal Memory</h4>
                <p style={styles.archLayerDesc}>
                  Recent behaviors, meal history, past episodes, what helped
                </p>
              </div>
            </div>

            <div style={styles.archArrow}>↓</div>

            <div style={styles.archLayer}>
              <span style={styles.archLayerIcon}>💡</span>
              <div style={styles.archLayerContent}>
                <h4 style={styles.archLayerTitle}>Causal Reasoning</h4>
                <p style={styles.archLayerDesc}>
                  Combines all layers to explain "why" and suggest "what helps"
                </p>
              </div>
            </div>
          </div>

          <div style={styles.archNote}>
            <strong>The result:</strong> Sakhi doesn't just know facts about you — Sakhi understands
            the connections between your behaviors, constitution, and how you feel.
          </div>
        </div>
      )}
    </main>
  );
}

function formatCauseName(cause: string): string {
  return cause
    .replace(/_/g, " ")
    .replace(/\b\w/g, (l) => l.toUpperCase());
}

function getSimulatedResult(symptom: string): ReflectionResult {
  const results: Record<string, ReflectionResult> = {
    scattered: {
      symptom: "scattered",
      dosha_context: "Feeling scattered is a classic sign of elevated Vata. Vata governs movement and when aggravated, the mind becomes restless and unfocused.",
      primary_causes: [
        {
          cause: "late_dinner",
          correlation: 0.75,
          explanation: "You had dinner at 10pm last night. Eating late disturbs Vata, disrupting sleep and mental clarity the next day.",
        },
        {
          cause: "skipped_exercise",
          correlation: 0.65,
          explanation: "You haven't exercised in 2 days. Regular movement helps ground Vata energy.",
        },
      ],
      contributing_factors: [
        {
          cause: "cold_drinks",
          correlation: 0.5,
          explanation: "Cold drinks can aggravate Vata, especially in the evening.",
        },
      ],
      seasonal_influence: "Late winter can naturally elevate Vata",
      personal_pattern_match: true,
      explanation: "Based on your patterns, this scattered feeling is likely from the late dinner last night combined with skipping your usual morning movement. Last time this happened, grounding activities like morning walks helped within 2 days.",
    },
    anxious: {
      symptom: "anxious",
      dosha_context: "Anxiety is one of the primary manifestations of excess Vata. The air element creates instability in the mind.",
      primary_causes: [
        {
          cause: "irregular_sleep",
          correlation: 0.8,
          explanation: "Your sleep schedule has been inconsistent this week, which destabilizes Vata.",
        },
        {
          cause: "too_much_caffeine",
          correlation: 0.6,
          explanation: "Higher coffee intake noted recently, which can overstimulate the nervous system.",
        },
      ],
      contributing_factors: [],
      seasonal_influence: null,
      personal_pattern_match: true,
      explanation: "Your anxiety correlates strongly with irregular sleep patterns. This matches a pattern from 3 weeks ago when you had similar symptoms before a big deadline.",
    },
    irritable: {
      symptom: "irritable",
      dosha_context: "Irritability is a Pitta imbalance. The fire element is running high, creating heat in the mind and emotions.",
      primary_causes: [
        {
          cause: "working_through_lunch",
          correlation: 0.85,
          explanation: "You skipped proper lunch yesterday. Pitta is highest between 10am-2pm, and skipping meals during this time causes heat buildup.",
        },
      ],
      contributing_factors: [
        {
          cause: "spicy_dinner",
          correlation: 0.55,
          explanation: "The spicy meal last night added more heat to an already elevated Pitta.",
        },
      ],
      seasonal_influence: null,
      personal_pattern_match: true,
      explanation: "This irritability likely stems from skipping lunch during peak Pitta hours. Your pattern shows this happens when you get absorbed in work and forget to eat.",
    },
    sluggish: {
      symptom: "sluggish",
      dosha_context: "Sluggishness indicates Kapha accumulation. The earth and water elements are creating heaviness and inertia.",
      primary_causes: [
        {
          cause: "heavy_breakfast",
          correlation: 0.7,
          explanation: "A heavy breakfast during Kapha time (6-10am) increases sluggishness throughout the day.",
        },
        {
          cause: "no_exercise",
          correlation: 0.8,
          explanation: "No physical activity in 2 days allows Kapha to accumulate.",
        },
      ],
      contributing_factors: [],
      seasonal_influence: "Late winter/early spring is Kapha season",
      personal_pattern_match: true,
      explanation: "The sluggishness is from the combination of heavy morning meals and lack of movement. Light breakfast and a brisk walk usually helps you feel better within a day.",
    },
  };

  return results[symptom] || results.scattered;
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    minHeight: "100vh",
    background: palette.bg,
    color: palette.fg,
    padding: "40px 24px",
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  },
  header: {
    maxWidth: 700,
    margin: "0 auto 40px",
    textAlign: "center",
  },
  backLink: {
    color: palette.muted,
    textDecoration: "none",
    fontSize: 14,
    display: "inline-block",
    marginBottom: 16,
  },
  title: {
    fontSize: 32,
    fontWeight: 700,
    marginBottom: 8,
    background: `linear-gradient(135deg, ${palette.fg} 0%, ${palette.accent} 100%)`,
    WebkitBackgroundClip: "text",
    WebkitTextFillColor: "transparent",
  },
  subtitle: {
    fontSize: 16,
    color: palette.muted,
    margin: 0,
  },
  symptomSection: {
    maxWidth: 600,
    margin: "0 auto 40px",
    textAlign: "center",
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 600,
    marginBottom: 20,
  },
  symptomGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(4, 1fr)",
    gap: 12,
    marginBottom: 24,
  },
  symptomCard: {
    padding: 16,
    background: palette.cardBg,
    border: "2px solid",
    borderRadius: 12,
    cursor: "pointer",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: 8,
    transition: "all 0.2s ease",
  },
  symptomIcon: {
    fontSize: 28,
  },
  symptomLabel: {
    fontSize: 13,
    fontWeight: 500,
  },
  doshaBadge: {
    fontSize: 10,
    textTransform: "uppercase",
    letterSpacing: "0.05em",
  },
  button: {
    padding: "14px 32px",
    fontSize: 16,
    fontWeight: 500,
    background: palette.accent,
    color: "#fff",
    border: "none",
    borderRadius: 12,
    cursor: "pointer",
  },
  buttonDisabled: {
    padding: "14px 32px",
    fontSize: 16,
    fontWeight: 500,
    background: palette.divider,
    color: palette.muted,
    border: "none",
    borderRadius: 12,
    cursor: "not-allowed",
  },
  errorMessage: {
    maxWidth: 600,
    margin: "0 auto 24px",
    padding: 12,
    background: "rgba(234, 179, 8, 0.15)",
    borderRadius: 8,
    textAlign: "center",
    color: "#eab308",
    fontSize: 13,
  },
  resultsSection: {
    maxWidth: 700,
    margin: "0 auto 40px",
    display: "flex",
    flexDirection: "column",
    gap: 20,
  },
  doshaCard: {
    padding: 20,
    background: palette.accentDim,
    borderRadius: 12,
    border: `1px solid ${palette.accent}30`,
  },
  doshaHeader: {
    display: "flex",
    gap: 16,
  },
  doshaIcon: {
    fontSize: 32,
  },
  doshaTitle: {
    margin: "0 0 8px 0",
    fontSize: 14,
    fontWeight: 600,
    color: palette.accent,
  },
  doshaText: {
    margin: 0,
    fontSize: 14,
    lineHeight: 1.6,
    color: palette.fg,
  },
  causesCard: {
    padding: 24,
    background: palette.cardBg,
    borderRadius: 12,
    border: `1px solid ${palette.divider}`,
  },
  causesTitle: {
    margin: "0 0 4px 0",
    fontSize: 18,
    fontWeight: 600,
  },
  causesSubtitle: {
    margin: "0 0 20px 0",
    fontSize: 13,
    color: palette.muted,
  },
  causeItem: {
    marginBottom: 20,
    paddingBottom: 20,
    borderBottom: `1px solid ${palette.divider}`,
  },
  causeHeader: {
    display: "flex",
    alignItems: "center",
    gap: 12,
    marginBottom: 8,
  },
  causeName: {
    fontWeight: 600,
    fontSize: 15,
    minWidth: 150,
  },
  correlationBar: {
    flex: 1,
    height: 6,
    background: palette.divider,
    borderRadius: 3,
    overflow: "hidden",
  },
  correlationFill: {
    height: "100%",
    borderRadius: 3,
    transition: "width 0.5s ease",
  },
  correlationValue: {
    fontSize: 13,
    fontWeight: 600,
    color: palette.accent,
    minWidth: 40,
    textAlign: "right",
  },
  causeExplanation: {
    margin: 0,
    fontSize: 13,
    color: palette.muted,
    lineHeight: 1.5,
  },
  contributingTitle: {
    margin: "0 0 12px 0",
    fontSize: 14,
    fontWeight: 600,
    color: palette.muted,
  },
  factorItem: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "8px 0",
  },
  factorName: {
    fontSize: 13,
    color: palette.muted,
  },
  factorCorrelation: {
    fontSize: 12,
    color: palette.muted,
  },
  explanationCard: {
    padding: 24,
    background: palette.cardBg,
    borderRadius: 12,
    border: `1px solid ${palette.divider}`,
  },
  explCardTitle: {
    margin: "0 0 12px 0",
    fontSize: 16,
    fontWeight: 600,
  },
  explCardText: {
    margin: 0,
    fontSize: 15,
    lineHeight: 1.7,
    color: palette.fg,
  },
  patternMatch: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    marginTop: 16,
    padding: 12,
    background: palette.accentDim,
    borderRadius: 8,
    fontSize: 13,
    color: palette.accent,
  },
  patternIcon: {
    fontSize: 18,
  },
  archToggle: {
    maxWidth: 700,
    margin: "0 auto 24px",
    textAlign: "center",
  },
  archToggleButton: {
    padding: "10px 20px",
    background: "transparent",
    color: palette.muted,
    border: `1px solid ${palette.divider}`,
    borderRadius: 8,
    fontSize: 14,
    cursor: "pointer",
  },
  architectureSection: {
    maxWidth: 700,
    margin: "0 auto",
    padding: 32,
    background: palette.cardBg,
    borderRadius: 16,
    border: `1px solid ${palette.divider}`,
  },
  archTitle: {
    margin: "0 0 24px 0",
    fontSize: 20,
    fontWeight: 600,
    textAlign: "center",
  },
  archDiagram: {
    display: "flex",
    flexDirection: "column",
    gap: 8,
    marginBottom: 24,
  },
  archLayer: {
    display: "flex",
    alignItems: "center",
    gap: 16,
    padding: 16,
    background: palette.bg,
    borderRadius: 12,
  },
  archLayerIcon: {
    fontSize: 28,
  },
  archLayerContent: {
    flex: 1,
  },
  archLayerTitle: {
    margin: "0 0 4px 0",
    fontSize: 15,
    fontWeight: 600,
  },
  archLayerDesc: {
    margin: 0,
    fontSize: 13,
    color: palette.muted,
  },
  archArrow: {
    textAlign: "center",
    color: palette.accent,
    fontSize: 20,
  },
  archNote: {
    padding: 16,
    background: palette.accentDim,
    borderRadius: 8,
    fontSize: 14,
    lineHeight: 1.6,
    color: palette.fg,
  },
};
