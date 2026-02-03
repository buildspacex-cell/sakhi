"use client";

import Link from "next/link";
import { useState } from "react";

/**
 * Mission Demo - Life Goals Become Structured Plans
 * -------------------------------------------------
 * Shows how Sakhi decomposes a life goal into actionable phases,
 * weeks, and daily actions.
 */

export const dynamic = "force-dynamic";

const palette = {
  bg: "#0e0f12",
  cardBg: "#1a1b1e",
  fg: "#f4f4f5",
  muted: "#71717a",
  accent: "#6366f1",
  accentDim: "rgba(99, 102, 241, 0.15)",
  amber: "#f59e0b",
  amberDim: "rgba(245, 158, 11, 0.15)",
  emerald: "#10b981",
  emeraldDim: "rgba(16, 185, 129, 0.15)",
  rose: "#f43f5e",
  roseDim: "rgba(244, 63, 94, 0.15)",
  divider: "#27272a",
};

interface Phase {
  phase_number: number;
  name: string;
  objective: string;
  duration_weeks: number;
  expected_outcomes: string[];
}

interface Action {
  action_type: string;
  description: string;
  scheduled_day: string;
  scheduled_time?: string;
}

interface MissionResult {
  id: string;
  title: string;
  description: string;
  category: string;
  plan_document: string;
  phases_count: number;
  first_week_actions: number;
}

// Demo user ID - matches the seeded demo data
const DEMO_PERSON_ID = "d290f1ee-6c54-4b01-90e6-d701748f0851";

const exampleGoals = [
  {
    goal: "Build my Twitter brand and grow to 1000 followers",
    category: "creative",
    icon: "X",
  },
  {
    goal: "Save $5000 for emergency fund by cutting expenses",
    category: "finance",
    icon: "$",
  },
  {
    goal: "Learn Python and build 3 portfolio projects",
    category: "learning",
    icon: "</>"
  },
  {
    goal: "Run a 5K in under 30 minutes",
    category: "health",
    icon: "Run",
  },
];

export default function MissionDemo() {
  const [selectedGoal, setSelectedGoal] = useState<string | null>(null);
  const [customGoal, setCustomGoal] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<MissionResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showPlan, setShowPlan] = useState(false);

  const handleCreateMission = async () => {
    const goalText = customGoal || selectedGoal;
    if (!goalText) return;

    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await fetch(`/api/missions?person_id=${DEMO_PERSON_ID}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          goal: goalText,
          target_weeks: 8,
        }),
      });

      if (!response.ok) {
        throw new Error(`Failed to create mission: ${response.statusText}`);
      }

      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main style={styles.container}>
      {/* Header */}
      <header style={styles.header}>
        <Link href="/demo" style={styles.backLink}>
          ← Back to Demo
        </Link>
        <h1 style={styles.title}>Life Missions</h1>
        <p style={styles.subtitle}>
          Tell Sakhi your goal. Watch it transform into a structured, actionable plan.
        </p>
      </header>

      {/* Goal Selection */}
      <section style={styles.section}>
        <h2 style={styles.sectionTitle}>What do you want to achieve?</h2>

        <div style={styles.goalGrid}>
          {exampleGoals.map((item) => (
            <button
              key={item.goal}
              onClick={() => {
                setSelectedGoal(item.goal);
                setCustomGoal("");
              }}
              style={{
                ...styles.goalCard,
                ...(selectedGoal === item.goal ? styles.goalCardSelected : {}),
              }}
            >
              <span style={styles.goalIcon}>{item.icon}</span>
              <p style={styles.goalText}>{item.goal}</p>
              <span style={styles.goalCategory}>{item.category}</span>
            </button>
          ))}
        </div>

        <div style={styles.customGoalContainer}>
          <p style={styles.orDivider}>— or enter your own goal —</p>
          <input
            type="text"
            placeholder="I want to..."
            value={customGoal}
            onChange={(e) => {
              setCustomGoal(e.target.value);
              setSelectedGoal(null);
            }}
            style={styles.customGoalInput}
          />
        </div>

        <button
          onClick={handleCreateMission}
          disabled={isLoading || (!selectedGoal && !customGoal)}
          style={{
            ...styles.createButton,
            opacity: isLoading || (!selectedGoal && !customGoal) ? 0.5 : 1,
          }}
        >
          {isLoading ? (
            <span style={styles.loadingText}>
              Sakhi is planning your mission...
            </span>
          ) : (
            "Create My Mission Plan"
          )}
        </button>
      </section>

      {/* Loading Animation */}
      {isLoading && (
        <section style={styles.loadingSection}>
          <div style={styles.loadingSteps}>
            <LoadingStep text="Understanding your goal..." delay={0} />
            <LoadingStep text="Breaking into phases..." delay={800} />
            <LoadingStep text="Planning your first week..." delay={1600} />
            <LoadingStep text="Scheduling actions..." delay={2400} />
          </div>
        </section>
      )}

      {/* Error */}
      {error && (
        <section style={styles.errorSection}>
          <p style={styles.errorText}>{error}</p>
        </section>
      )}

      {/* Result */}
      {result && (
        <section style={styles.resultSection}>
          <div style={styles.resultHeader}>
            <div style={styles.resultBadge}>Mission Created</div>
            <h2 style={styles.resultTitle}>{result.title}</h2>
            <p style={styles.resultDescription}>{result.description}</p>
          </div>

          <div style={styles.statsGrid}>
            <div style={styles.statCard}>
              <span style={styles.statValue}>{result.phases_count}</span>
              <span style={styles.statLabel}>Phases</span>
            </div>
            <div style={styles.statCard}>
              <span style={styles.statValue}>8</span>
              <span style={styles.statLabel}>Weeks</span>
            </div>
            <div style={styles.statCard}>
              <span style={styles.statValue}>{result.first_week_actions}</span>
              <span style={styles.statLabel}>First Week Actions</span>
            </div>
          </div>

          <button
            onClick={() => setShowPlan(!showPlan)}
            style={styles.togglePlanButton}
          >
            {showPlan ? "Hide Full Plan" : "View Full Plan"}
          </button>

          {showPlan && result.plan_document && (
            <div style={styles.planDocument}>
              <pre style={styles.planText}>{result.plan_document}</pre>
            </div>
          )}

          <div style={styles.nextSteps}>
            <h3 style={styles.nextStepsTitle}>What Happens Next</h3>
            <ul style={styles.nextStepsList}>
              <li>Sakhi will remind you of scheduled actions each day</li>
              <li>Track your progress and adjust the plan as you learn</li>
              <li>Weekly reviews help refine the approach</li>
              <li>Phase transitions require your approval</li>
            </ul>
          </div>
        </section>
      )}

      {/* How It Works */}
      <section style={styles.howItWorks}>
        <h2 style={styles.howItWorksTitle}>How Missions Work</h2>

        <div style={styles.processFlow}>
          <div style={styles.processStep}>
            <div style={{ ...styles.processIcon, background: palette.accentDim }}>
              <span>1</span>
            </div>
            <h4 style={styles.processStepTitle}>Decompose</h4>
            <p style={styles.processStepText}>
              Your goal is broken into 2-4 phases, each with clear objectives
            </p>
          </div>

          <div style={styles.processArrow}>→</div>

          <div style={styles.processStep}>
            <div style={{ ...styles.processIcon, background: palette.emeraldDim }}>
              <span>2</span>
            </div>
            <h4 style={styles.processStepTitle}>Plan Weekly</h4>
            <p style={styles.processStepText}>
              Each week has specific objectives and 2-4 daily actions
            </p>
          </div>

          <div style={styles.processArrow}>→</div>

          <div style={styles.processStep}>
            <div style={{ ...styles.processIcon, background: palette.amberDim }}>
              <span>3</span>
            </div>
            <h4 style={styles.processStepTitle}>Execute</h4>
            <p style={styles.processStepText}>
              Sakhi reminds you, tracks outcomes, and learns what works
            </p>
          </div>

          <div style={styles.processArrow}>→</div>

          <div style={styles.processStep}>
            <div style={{ ...styles.processIcon, background: palette.roseDim }}>
              <span>4</span>
            </div>
            <h4 style={styles.processStepTitle}>Adapt</h4>
            <p style={styles.processStepText}>
              Weekly reviews refine the plan based on real progress
            </p>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer style={styles.footer}>
        <p style={styles.footerText}>
          Life goals become achievable when broken into daily actions.
        </p>
      </footer>
    </main>
  );
}

function LoadingStep({ text, delay }: { text: string; delay: number }) {
  const [visible, setVisible] = useState(false);

  useState(() => {
    const timer = setTimeout(() => setVisible(true), delay);
    return () => clearTimeout(timer);
  });

  return (
    <div
      style={{
        ...styles.loadingStep,
        opacity: visible ? 1 : 0.3,
        transform: visible ? "translateX(0)" : "translateX(-10px)",
      }}
    >
      <span style={styles.loadingDot}>{visible ? "✓" : "○"}</span>
      <span>{text}</span>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    minHeight: "100vh",
    background: palette.bg,
    color: palette.fg,
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    padding: "40px 24px",
  },
  header: {
    maxWidth: 800,
    margin: "0 auto 48px",
    textAlign: "center",
  },
  backLink: {
    color: palette.muted,
    textDecoration: "none",
    fontSize: 14,
    display: "inline-block",
    marginBottom: 24,
  },
  title: {
    fontSize: 48,
    fontWeight: 700,
    marginBottom: 16,
  },
  subtitle: {
    fontSize: 18,
    color: palette.muted,
    margin: 0,
  },
  section: {
    maxWidth: 800,
    margin: "0 auto 48px",
  },
  sectionTitle: {
    fontSize: 24,
    fontWeight: 600,
    marginBottom: 24,
    textAlign: "center",
  },
  goalGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
    gap: 16,
    marginBottom: 24,
  },
  goalCard: {
    background: palette.cardBg,
    border: `1px solid ${palette.divider}`,
    borderRadius: 12,
    padding: 20,
    textAlign: "left",
    cursor: "pointer",
    transition: "all 0.2s",
  },
  goalCardSelected: {
    border: `2px solid ${palette.accent}`,
    background: palette.accentDim,
  },
  goalIcon: {
    display: "inline-block",
    fontSize: 14,
    fontWeight: 600,
    padding: "4px 10px",
    background: palette.accentDim,
    color: palette.accent,
    borderRadius: 6,
    marginBottom: 12,
  },
  goalText: {
    fontSize: 16,
    lineHeight: 1.5,
    marginBottom: 8,
    color: palette.fg,
  },
  goalCategory: {
    fontSize: 12,
    color: palette.muted,
    textTransform: "capitalize",
  },
  customGoalContainer: {
    marginBottom: 24,
  },
  orDivider: {
    textAlign: "center",
    color: palette.muted,
    fontSize: 14,
    marginBottom: 16,
  },
  customGoalInput: {
    width: "100%",
    padding: "16px 20px",
    fontSize: 16,
    background: palette.cardBg,
    border: `1px solid ${palette.divider}`,
    borderRadius: 12,
    color: palette.fg,
    outline: "none",
  },
  createButton: {
    display: "block",
    width: "100%",
    padding: "16px 32px",
    fontSize: 16,
    fontWeight: 600,
    background: palette.accent,
    color: "#fff",
    border: "none",
    borderRadius: 12,
    cursor: "pointer",
    transition: "opacity 0.2s",
  },
  loadingText: {
    display: "inline-flex",
    alignItems: "center",
    gap: 8,
  },
  loadingSection: {
    maxWidth: 400,
    margin: "0 auto 48px",
    padding: 32,
    background: palette.cardBg,
    borderRadius: 16,
  },
  loadingSteps: {
    display: "flex",
    flexDirection: "column",
    gap: 16,
  },
  loadingStep: {
    display: "flex",
    alignItems: "center",
    gap: 12,
    fontSize: 16,
    transition: "all 0.3s ease",
  },
  loadingDot: {
    width: 24,
    height: 24,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    background: palette.accentDim,
    borderRadius: "50%",
    fontSize: 12,
    color: palette.accent,
  },
  errorSection: {
    maxWidth: 600,
    margin: "0 auto 48px",
    padding: 24,
    background: palette.roseDim,
    borderRadius: 12,
    textAlign: "center",
  },
  errorText: {
    color: palette.rose,
    margin: 0,
  },
  resultSection: {
    maxWidth: 800,
    margin: "0 auto 48px",
  },
  resultHeader: {
    textAlign: "center",
    marginBottom: 32,
  },
  resultBadge: {
    display: "inline-block",
    padding: "8px 16px",
    background: palette.emeraldDim,
    color: palette.emerald,
    borderRadius: 20,
    fontSize: 14,
    fontWeight: 600,
    marginBottom: 16,
  },
  resultTitle: {
    fontSize: 32,
    fontWeight: 700,
    marginBottom: 8,
  },
  resultDescription: {
    fontSize: 18,
    color: palette.muted,
    margin: 0,
  },
  statsGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(3, 1fr)",
    gap: 16,
    marginBottom: 24,
  },
  statCard: {
    background: palette.cardBg,
    borderRadius: 12,
    padding: 24,
    textAlign: "center",
  },
  statValue: {
    display: "block",
    fontSize: 36,
    fontWeight: 700,
    color: palette.accent,
    marginBottom: 4,
  },
  statLabel: {
    fontSize: 14,
    color: palette.muted,
  },
  togglePlanButton: {
    display: "block",
    width: "100%",
    padding: "12px 24px",
    fontSize: 14,
    background: "transparent",
    border: `1px solid ${palette.divider}`,
    borderRadius: 8,
    color: palette.fg,
    cursor: "pointer",
    marginBottom: 24,
  },
  planDocument: {
    background: palette.cardBg,
    borderRadius: 12,
    padding: 24,
    marginBottom: 24,
    maxHeight: 500,
    overflow: "auto",
  },
  planText: {
    fontFamily: "monospace",
    fontSize: 13,
    lineHeight: 1.6,
    color: palette.fg,
    whiteSpace: "pre-wrap",
    margin: 0,
  },
  nextSteps: {
    background: palette.accentDim,
    borderRadius: 12,
    padding: 24,
  },
  nextStepsTitle: {
    fontSize: 18,
    fontWeight: 600,
    marginBottom: 16,
  },
  nextStepsList: {
    margin: 0,
    paddingLeft: 20,
    lineHeight: 2,
    color: palette.muted,
  },
  howItWorks: {
    maxWidth: 1000,
    margin: "0 auto 48px",
    padding: "48px 24px",
    background: palette.cardBg,
    borderRadius: 16,
  },
  howItWorksTitle: {
    fontSize: 28,
    fontWeight: 600,
    textAlign: "center",
    marginBottom: 40,
  },
  processFlow: {
    display: "flex",
    alignItems: "flex-start",
    justifyContent: "center",
    flexWrap: "wrap",
    gap: 16,
  },
  processStep: {
    flex: "1 1 180px",
    maxWidth: 200,
    textAlign: "center",
  },
  processIcon: {
    width: 48,
    height: 48,
    borderRadius: "50%",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    margin: "0 auto 12px",
    fontSize: 18,
    fontWeight: 700,
    color: palette.fg,
  },
  processStepTitle: {
    fontSize: 16,
    fontWeight: 600,
    marginBottom: 8,
  },
  processStepText: {
    fontSize: 14,
    color: palette.muted,
    lineHeight: 1.5,
    margin: 0,
  },
  processArrow: {
    fontSize: 24,
    color: palette.muted,
    alignSelf: "center",
    marginTop: 16,
  },
  footer: {
    textAlign: "center",
    padding: "40px 24px",
    borderTop: `1px solid ${palette.divider}`,
  },
  footerText: {
    fontSize: 16,
    color: palette.muted,
    margin: 0,
    fontStyle: "italic",
  },
};
