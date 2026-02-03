"use client";

import { useState, useCallback } from "react";
import Link from "next/link";

/**
 * Vision Loop Demo - Act 1
 * -------------------------
 * Shows Sakhi browsing the web autonomously to find products
 * that match the user's taste preferences.
 *
 * Uses the backend API: POST /api/demo/run/vision
 */

export const dynamic = "force-dynamic";

// Color palette
const palette = {
  bg: "#0e0f12",
  cardBg: "#1a1b1e",
  fg: "#f4f4f5",
  muted: "#71717a",
  accent: "#6366f1",
  accentDim: "rgba(99, 102, 241, 0.15)",
  success: "#22c55e",
  warning: "#eab308",
  divider: "#27272a",
};

interface VisionStep {
  step: number;
  screenshot: string | null;
  analysis: {
    description?: string;
    page_type?: string;
    url?: string;
    elements?: Array<{ type: string; text: string; x: number; y: number }>;
    text?: string;
    task_relevant?: { found_target?: boolean };
  };
  action: {
    type?: string;
    parameters?: { text?: string; x?: number; y?: number; key?: string };
    description?: string;
  } | null;
  reasoning: string;
  complete: boolean;
}

export default function VisionDemo() {
  const [steps, setSteps] = useState<VisionStep[]>([]);
  const [currentStep, setCurrentStep] = useState(0);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [task, setTask] = useState("Find a car perfume on Amazon");

  const runDemo = useCallback(async () => {
    if (isRunning) return;
    setIsRunning(true);
    setSteps([]);
    setCurrentStep(0);
    setError(null);

    try {
      const response = await fetch(`/api/demo/run/vision?task=${encodeURIComponent(task)}&mode=simulated`, {
        method: "POST",
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }

      const data = await response.json();
      const demoSteps: VisionStep[] = data.steps || [];

      // Animate steps one by one
      for (let i = 0; i < demoSteps.length; i++) {
        setSteps((prev) => [...prev, demoSteps[i]]);
        setCurrentStep(i + 1);
        await delay(1500);
      }
    } catch (err) {
      console.error("Demo error:", err);
      setError(err instanceof Error ? err.message : "Failed to run demo");
      // Fall back to simulated demo if API fails
      await runSimulatedDemo();
    } finally {
      setIsRunning(false);
    }
  }, [isRunning, task]);

  // Fallback simulated demo if API is unavailable
  const runSimulatedDemo = async () => {
    const simulatedSteps: VisionStep[] = [
      {
        step: 1,
        screenshot: null,
        analysis: { description: "Amazon homepage with search bar", page_type: "home" },
        action: { type: "click", parameters: { x: 500, y: 50 }, description: "Click search bar" },
        reasoning: "Need to search for car perfume. Clicking on the search bar.",
        complete: false,
      },
      {
        step: 2,
        screenshot: null,
        analysis: { description: "Search bar focused, ready for input" },
        action: { type: "type", parameters: { text: "car perfume woody scent" }, description: "Type search query" },
        reasoning: "User prefers woody scents (from preferences). Searching for 'car perfume woody scent'.",
        complete: false,
      },
      {
        step: 3,
        screenshot: null,
        analysis: { description: "Search query typed" },
        action: { type: "key", parameters: { key: "enter" }, description: "Submit search" },
        reasoning: "Search query is entered. Pressing Enter to search.",
        complete: false,
      },
      {
        step: 4,
        screenshot: null,
        analysis: {
          description: "Search results for car perfume",
          elements: [
            { type: "link", text: "Premium Car Air Freshener - Woody Cedar", x: 400, y: 300 },
            { type: "text", text: "4.5 stars, $24.99", x: 400, y: 340 },
          ],
        },
        action: { type: "click", parameters: { x: 400, y: 300 }, description: "Click first result" },
        reasoning: "Found 'Woody Cedar' car perfume. This matches user's woody scent preference.",
        complete: false,
      },
      {
        step: 5,
        screenshot: null,
        analysis: {
          description: "Product detail page",
          text: "Premium Car Air Freshener - Woody Cedar. Scent notes: Cedarwood, Sandalwood, hint of Citrus. $24.99",
          task_relevant: { found_target: true },
        },
        action: null,
        reasoning: "Found excellent match! 'Woody Cedar' with cedarwood and sandalwood (user loves woody scents), hint of citrus (user likes citrus). 4.5 stars. $24.99. This matches your preferences perfectly.",
        complete: true,
      },
    ];

    for (const step of simulatedSteps) {
      setSteps((prev) => [...prev, step]);
      setCurrentStep(step.step);
      await delay(1500);
    }
  };

  const resetDemo = () => {
    setSteps([]);
    setCurrentStep(0);
    setIsRunning(false);
    setError(null);
  };

  return (
    <main style={styles.container}>
      {/* Header */}
      <header style={styles.header}>
        <Link href="/demo" style={styles.backLink}>← Back to Demo</Link>
        <h1 style={styles.title}>Vision Loop Demo</h1>
        <p style={styles.subtitle}>
          Sakhi browses the web autonomously, using your preferences to find products YOU'll love
        </p>
      </header>

      {/* Task Input */}
      <div style={styles.taskSection}>
        <label style={styles.taskLabel}>Task:</label>
        <input
          type="text"
          value={task}
          onChange={(e) => setTask(e.target.value)}
          style={styles.taskInput}
          disabled={isRunning}
        />
      </div>

      {/* Preferences Context */}
      <div style={styles.preferencesCard}>
        <h3 style={styles.prefTitle}>Your Preferences (from memory)</h3>
        <div style={styles.prefGrid}>
          <div style={styles.prefItem}>
            <span style={styles.prefLabel}>Loves</span>
            <span style={styles.prefValue}>Woody, Cedar, Sandalwood, Musk</span>
          </div>
          <div style={styles.prefItem}>
            <span style={styles.prefLabel}>Likes</span>
            <span style={styles.prefValue}>Citrus</span>
          </div>
          <div style={styles.prefItem}>
            <span style={styles.prefLabel}>Avoids</span>
            <span style={styles.prefValue}>Floral, Sweet</span>
          </div>
        </div>
      </div>

      {/* Vision Loop Visualization */}
      <div style={styles.visionContainer}>
        <div style={styles.browserFrame}>
          <div style={styles.browserHeader}>
            <div style={styles.browserDots}>
              <span style={styles.dot} />
              <span style={styles.dot} />
              <span style={styles.dot} />
            </div>
            <div style={styles.browserUrl}>
              {steps.length > 0 && steps[steps.length - 1].analysis.url
                ? steps[steps.length - 1].analysis.url
                : "amazon.com"}
            </div>
          </div>

          <div style={styles.browserContent}>
            {steps.length === 0 ? (
              <div style={styles.emptyState}>
                <span style={styles.emptyIcon}>🖥️</span>
                <p>Click "Start Demo" to see Sakhi browse</p>
              </div>
            ) : (
              <div style={styles.screenAnalysis}>
                <h4 style={styles.analysisTitle}>Screen Analysis</h4>
                <p style={styles.analysisText}>
                  {steps[steps.length - 1].analysis.description || steps[steps.length - 1].analysis.text}
                </p>
                {steps[steps.length - 1].analysis.elements && (
                  <div style={styles.elementsFound}>
                    {steps[steps.length - 1].analysis.elements?.slice(0, 3).map((el, i) => (
                      <div key={i} style={styles.elementTag}>
                        {el.type}: {el.text}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Steps Timeline */}
        <div style={styles.stepsPanel}>
          <h3 style={styles.stepsPanelTitle}>Steps</h3>
          <div style={styles.stepsList}>
            {steps.map((step, i) => (
              <div
                key={i}
                style={{
                  ...styles.stepItem,
                  borderColor: step.complete ? palette.success : i === steps.length - 1 ? palette.accent : palette.divider,
                }}
              >
                <div style={styles.stepHeader}>
                  <span style={styles.stepNumber}>Step {step.step}</span>
                  {step.action && (
                    <span style={styles.actionBadge}>
                      {step.action.type}: {step.action.description}
                    </span>
                  )}
                  {step.complete && (
                    <span style={styles.completeBadge}>✓ Complete</span>
                  )}
                </div>
                <p style={styles.stepReasoning}>{step.reasoning}</p>
              </div>
            ))}
            {isRunning && (
              <div style={styles.thinkingStep}>
                <span style={styles.thinkingDots}>•••</span>
                <span>Sakhi is thinking...</span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Controls */}
      <div style={styles.controls}>
        <button
          onClick={runDemo}
          disabled={isRunning}
          style={isRunning ? styles.buttonDisabled : styles.button}
        >
          {isRunning ? "Running..." : steps.length > 0 ? "Run Again" : "Start Demo"}
        </button>
        {steps.length > 0 && (
          <button onClick={resetDemo} style={styles.buttonSecondary}>
            Reset
          </button>
        )}
      </div>

      {error && (
        <div style={styles.errorMessage}>
          {error} (using simulated fallback)
        </div>
      )}

      {/* Explanation */}
      <div style={styles.explanation}>
        <h3 style={styles.explainTitle}>How It Works</h3>
        <div style={styles.loopDiagram}>
          <div style={styles.loopStep}>
            <span style={styles.loopIcon}>📸</span>
            <span style={styles.loopLabel}>Capture</span>
          </div>
          <span style={styles.loopArrow}>→</span>
          <div style={styles.loopStep}>
            <span style={styles.loopIcon}>🔍</span>
            <span style={styles.loopLabel}>Analyze</span>
          </div>
          <span style={styles.loopArrow}>→</span>
          <div style={styles.loopStep}>
            <span style={styles.loopIcon}>🤔</span>
            <span style={styles.loopLabel}>Decide</span>
          </div>
          <span style={styles.loopArrow}>→</span>
          <div style={styles.loopStep}>
            <span style={styles.loopIcon}>⚡</span>
            <span style={styles.loopLabel}>Execute</span>
          </div>
          <span style={styles.loopArrow}>→</span>
          <span style={styles.loopRepeat}>↺</span>
        </div>
        <ul style={styles.explainList}>
          <li><strong>Screenshot</strong>: Desktop agent captures the screen</li>
          <li><strong>Analyze</strong>: Claude Vision identifies elements and understands context</li>
          <li><strong>Decide</strong>: Claude decides next action based on task + your preferences</li>
          <li><strong>Execute</strong>: Desktop agent performs click/type/scroll</li>
          <li><strong>Repeat</strong>: Until task is complete</li>
        </ul>
      </div>
    </main>
  );
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
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
    maxWidth: 900,
    margin: "0 auto 32px",
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
  },
  subtitle: {
    fontSize: 16,
    color: palette.muted,
    margin: 0,
  },
  taskSection: {
    maxWidth: 900,
    margin: "0 auto 24px",
    display: "flex",
    alignItems: "center",
    gap: 12,
  },
  taskLabel: {
    fontSize: 14,
    fontWeight: 500,
  },
  taskInput: {
    flex: 1,
    padding: "12px 16px",
    background: palette.cardBg,
    border: `1px solid ${palette.divider}`,
    borderRadius: 8,
    color: palette.fg,
    fontSize: 14,
  },
  preferencesCard: {
    maxWidth: 900,
    margin: "0 auto 32px",
    padding: 20,
    background: palette.accentDim,
    borderRadius: 12,
    border: `1px solid ${palette.accent}30`,
  },
  prefTitle: {
    margin: "0 0 16px 0",
    fontSize: 14,
    fontWeight: 600,
    color: palette.accent,
  },
  prefGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(3, 1fr)",
    gap: 16,
  },
  prefItem: {
    display: "flex",
    flexDirection: "column",
    gap: 4,
  },
  prefLabel: {
    fontSize: 11,
    color: palette.muted,
    textTransform: "uppercase",
  },
  prefValue: {
    fontSize: 14,
  },
  visionContainer: {
    maxWidth: 1100,
    margin: "0 auto 32px",
    display: "grid",
    gridTemplateColumns: "1fr 400px",
    gap: 24,
  },
  browserFrame: {
    background: palette.cardBg,
    borderRadius: 12,
    border: `1px solid ${palette.divider}`,
    overflow: "hidden",
  },
  browserHeader: {
    display: "flex",
    alignItems: "center",
    gap: 16,
    padding: "12px 16px",
    background: palette.bg,
    borderBottom: `1px solid ${palette.divider}`,
  },
  browserDots: {
    display: "flex",
    gap: 6,
  },
  dot: {
    width: 10,
    height: 10,
    borderRadius: "50%",
    background: palette.divider,
  },
  browserUrl: {
    flex: 1,
    padding: "6px 12px",
    background: palette.cardBg,
    borderRadius: 6,
    fontSize: 12,
    color: palette.muted,
  },
  browserContent: {
    minHeight: 400,
    padding: 24,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  },
  emptyState: {
    textAlign: "center",
    color: palette.muted,
  },
  emptyIcon: {
    fontSize: 48,
    display: "block",
    marginBottom: 16,
  },
  screenAnalysis: {
    width: "100%",
  },
  analysisTitle: {
    margin: "0 0 12px 0",
    fontSize: 14,
    fontWeight: 600,
    color: palette.accent,
  },
  analysisText: {
    fontSize: 16,
    lineHeight: 1.6,
    margin: "0 0 16px 0",
  },
  elementsFound: {
    display: "flex",
    flexWrap: "wrap",
    gap: 8,
  },
  elementTag: {
    padding: "6px 12px",
    background: palette.bg,
    borderRadius: 6,
    fontSize: 12,
    color: palette.muted,
  },
  stepsPanel: {
    background: palette.cardBg,
    borderRadius: 12,
    border: `1px solid ${palette.divider}`,
    padding: 20,
    maxHeight: 500,
    overflowY: "auto",
  },
  stepsPanelTitle: {
    margin: "0 0 16px 0",
    fontSize: 16,
    fontWeight: 600,
  },
  stepsList: {
    display: "flex",
    flexDirection: "column",
    gap: 12,
  },
  stepItem: {
    padding: 16,
    background: palette.bg,
    borderRadius: 8,
    borderLeft: "3px solid",
  },
  stepHeader: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    marginBottom: 8,
    flexWrap: "wrap",
  },
  stepNumber: {
    fontSize: 12,
    fontWeight: 600,
    color: palette.accent,
  },
  actionBadge: {
    padding: "4px 8px",
    background: palette.accentDim,
    borderRadius: 4,
    fontSize: 11,
    color: palette.accent,
  },
  completeBadge: {
    padding: "4px 8px",
    background: "rgba(34, 197, 94, 0.15)",
    borderRadius: 4,
    fontSize: 11,
    color: palette.success,
  },
  stepReasoning: {
    margin: 0,
    fontSize: 13,
    color: palette.muted,
    lineHeight: 1.5,
  },
  thinkingStep: {
    padding: 16,
    background: palette.bg,
    borderRadius: 8,
    display: "flex",
    alignItems: "center",
    gap: 8,
    color: palette.muted,
    fontSize: 13,
  },
  thinkingDots: {
    animation: "pulse 1s infinite",
  },
  controls: {
    display: "flex",
    justifyContent: "center",
    gap: 16,
    marginBottom: 32,
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
  buttonSecondary: {
    padding: "14px 32px",
    fontSize: 16,
    fontWeight: 500,
    background: "transparent",
    color: palette.muted,
    border: `1px solid ${palette.divider}`,
    borderRadius: 12,
    cursor: "pointer",
  },
  errorMessage: {
    maxWidth: 600,
    margin: "0 auto 24px",
    padding: 12,
    background: "rgba(234, 179, 8, 0.15)",
    borderRadius: 8,
    textAlign: "center",
    color: palette.warning,
    fontSize: 13,
  },
  explanation: {
    maxWidth: 700,
    margin: "0 auto",
    padding: 24,
    background: palette.cardBg,
    borderRadius: 16,
    border: `1px solid ${palette.divider}`,
  },
  explainTitle: {
    margin: "0 0 20px 0",
    fontSize: 16,
    fontWeight: 600,
  },
  loopDiagram: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: 12,
    marginBottom: 24,
    flexWrap: "wrap",
  },
  loopStep: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: 4,
    padding: 12,
    background: palette.bg,
    borderRadius: 8,
  },
  loopIcon: {
    fontSize: 24,
  },
  loopLabel: {
    fontSize: 11,
    color: palette.muted,
  },
  loopArrow: {
    color: palette.muted,
    fontSize: 20,
  },
  loopRepeat: {
    color: palette.accent,
    fontSize: 24,
  },
  explainList: {
    margin: 0,
    paddingLeft: 20,
    lineHeight: 1.8,
    color: palette.muted,
  },
};
