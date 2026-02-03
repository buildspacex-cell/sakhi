"use client";

import { useState, useCallback } from "react";

/**
 * Self-Understanding Demo
 * ------------------------
 * ACT 4: Know Your Why
 *
 * Shows how Sakhi connects your patterns to explain
 * why you feel a certain way — and what helped last time.
 */

export const dynamic = "force-dynamic";

const USER = {
  name: "Alex",
  handle: "@alex",
  avatar: "A",
};

// Symptoms with dosha mapping
const SYMPTOMS = [
  { id: "scattered", label: "Scattered", dosha: "Vata", color: "#818cf8", bg: "rgba(129, 140, 248, 0.2)" },
  { id: "anxious", label: "Anxious", dosha: "Vata", color: "#818cf8", bg: "rgba(129, 140, 248, 0.2)" },
  { id: "irritable", label: "Irritable", dosha: "Pitta", color: "#f59e0b", bg: "rgba(245, 158, 11, 0.2)" },
  { id: "sluggish", label: "Sluggish", dosha: "Kapha", color: "#22c55e", bg: "rgba(34, 197, 94, 0.2)" },
];

// Analysis results per symptom
const ANALYSES: Record<string, {
  causes: { factor: string; percent: number }[];
  explanation: string;
  pattern: string;
  recovery: string[];
  actions: { task: string; why: string }[];
}> = {
  scattered: {
    causes: [
      { factor: "Late dinner (10pm)", percent: 75 },
      { factor: "Skipped morning walk", percent: 65 },
      { factor: "Screen time after 9pm", percent: 55 },
      { factor: "Irregular sleep", percent: 45 },
    ],
    explanation: "Your Vata is elevated. Late eating and screen time disrupt your natural grounding rhythms, leading to scattered thoughts and difficulty focusing.",
    pattern: "This matches what happened 3 weeks ago when you had similar symptoms.",
    recovery: ["2 days of early dinners", "Morning walks resumed", "Full recovery in 3 days"],
    actions: [
      { task: "Dinner by 7pm", why: "Grounding for Vata" },
      { task: "10-min evening walk", why: "Gentle movement calms" },
      { task: "Screens off by 9pm", why: "Protect sleep rhythm" },
    ],
  },
  anxious: {
    causes: [
      { factor: "Coffee after 2pm", percent: 70 },
      { factor: "Skipped lunch", percent: 60 },
      { factor: "Work deadline stress", percent: 55 },
      { factor: "Less time outdoors", percent: 40 },
    ],
    explanation: "Your Vata is aggravated by irregular eating and stimulants. This creates nervous energy that manifests as anxiety.",
    pattern: "Last month you felt this way during the Q3 deadline — same pattern.",
    recovery: ["Regular meals helped", "Switched to decaf after noon", "Back to normal in 4 days"],
    actions: [
      { task: "No caffeine after 12pm", why: "Calms nervous system" },
      { task: "Eat lunch at regular time", why: "Stabilizes Vata" },
      { task: "15-min outdoor break", why: "Grounding in nature" },
    ],
  },
  irritable: {
    causes: [
      { factor: "Spicy dinner last night", percent: 80 },
      { factor: "Intense workout", percent: 60 },
      { factor: "Less sleep than usual", percent: 50 },
      { factor: "Skipped cooling foods", percent: 45 },
    ],
    explanation: "Your Pitta is running high. Heat-generating foods and intense exercise without cooling balance leads to irritability.",
    pattern: "You felt this way after that Thai food last month — same trigger.",
    recovery: ["Cooling foods for 2 days", "Lighter exercise", "Resolved in 2 days"],
    actions: [
      { task: "Cucumber or coconut water", why: "Cooling for Pitta" },
      { task: "Light yoga instead of HIIT", why: "Reduce internal heat" },
      { task: "Earlier bedtime", why: "10pm sleep cools Pitta" },
    ],
  },
  sluggish: {
    causes: [
      { factor: "Heavy dinner, late", percent: 75 },
      { factor: "No morning movement", percent: 65 },
      { factor: "More screen time", percent: 50 },
      { factor: "Rainy weather", percent: 40 },
    ],
    explanation: "Your Kapha is accumulated. Heavy foods and lack of movement create stagnation that manifests as sluggishness.",
    pattern: "This happens every time you skip workouts for more than 3 days.",
    recovery: ["Morning walks helped most", "Lighter dinners", "Energy back in 3 days"],
    actions: [
      { task: "10-min morning walk", why: "Moves stagnant Kapha" },
      { task: "Lighter dinner by 7pm", why: "Easier to digest" },
      { task: "Warm ginger tea", why: "Stimulates digestion" },
    ],
  },
};

type DemoStep =
  | "idle"
  | "user_question"
  | "analyzing"
  | "checking_patterns"
  | "results";

interface Message {
  sender: "user" | "sakhi" | "system";
  content: string;
  thinking?: boolean;
}

// Color palette - rose for reflection
const palette = {
  bg: "#0e0f12",
  cardBg: "#1a1b1e",
  fg: "#f4f4f5",
  muted: "#71717a",
  accent: "#f43f5e", // Rose for reflection
  accentDim: "rgba(244, 63, 94, 0.2)",
  accentIndigo: "#6366f1",
  accentIndigoDim: "rgba(99, 102, 241, 0.2)",
  success: "#22c55e",
  successDim: "rgba(34, 197, 94, 0.2)",
  divider: "#27272a",
  warning: "#f59e0b",
};

export default function ReflectDemo() {
  const [step, setStep] = useState<DemoStep>("idle");
  const [messages, setMessages] = useState<Message[]>([]);
  const [selectedSymptom, setSelectedSymptom] = useState<string | null>(null);
  const [showAnalysis, setShowAnalysis] = useState(false);
  const [isRunning, setIsRunning] = useState(false);

  const runDemo = useCallback(async (symptomId: string) => {
    if (isRunning) return;
    setIsRunning(true);
    setShowAnalysis(false);
    setSelectedSymptom(symptomId);

    const symptom = SYMPTOMS.find(s => s.id === symptomId)!;
    const analysis = ANALYSES[symptomId];

    // Reset
    setMessages([]);

    // Step 1: User asks
    setStep("user_question");
    setMessages([{ sender: "user", content: `Why am I feeling ${symptom.label.toLowerCase()}?` }]);
    await delay(1500);

    // Step 2: Analyzing
    setStep("analyzing");
    setMessages((prev) => [
      ...prev,
      { sender: "sakhi", content: "Let me check your patterns...", thinking: true },
    ]);
    await delay(1000);

    // Step 3: Checking patterns
    setStep("checking_patterns");
    setMessages((prev) => [
      ...prev,
      {
        sender: "system",
        content: `Analyzing your recent data:
📊 Sleep patterns (7 days)
🍽️ Meal timing
🏃 Exercise history
📱 Screen time
🌡️ Your ${symptom.dosha} markers`,
      },
    ]);
    await delay(2000);

    // Step 4: Results
    setStep("results");
    setMessages((prev) => [
      ...prev,
      {
        sender: "sakhi",
        content: `I found a pattern.

${analysis.explanation}

${analysis.pattern}`,
      },
    ]);
    setShowAnalysis(true);
    await delay(500);

    setIsRunning(false);
  }, [isRunning]);

  const resetDemo = () => {
    setStep("idle");
    setMessages([]);
    setSelectedSymptom(null);
    setShowAnalysis(false);
    setIsRunning(false);
  };

  const analysis = selectedSymptom ? ANALYSES[selectedSymptom] : null;
  const symptom = selectedSymptom ? SYMPTOMS.find(s => s.id === selectedSymptom) : null;

  return (
    <main style={styles.container}>
      {/* Header */}
      <header style={styles.header}>
        <h1 style={styles.title}>Know Your Why</h1>
        <p style={styles.subtitle}>Sakhi connects your patterns to explain how you feel</p>
      </header>

      {/* Symptom Selector */}
      <div style={styles.symptomSelector}>
        <p style={styles.selectorLabel}>How are you feeling?</p>
        <div style={styles.symptomGrid}>
          {SYMPTOMS.map((s) => (
            <button
              key={s.id}
              onClick={() => !isRunning && runDemo(s.id)}
              disabled={isRunning}
              style={{
                ...styles.symptomButton,
                background: selectedSymptom === s.id ? s.bg : "transparent",
                borderColor: selectedSymptom === s.id ? s.color : palette.divider,
                color: selectedSymptom === s.id ? s.color : palette.muted,
                cursor: isRunning ? "not-allowed" : "pointer",
              }}
            >
              <span style={styles.symptomLabel}>{s.label}</span>
              <span style={{ ...styles.doshaTag, background: s.bg, color: s.color }}>
                {s.dosha}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Main Content */}
      <div style={styles.mainContent}>
        {/* Phone */}
        <div style={styles.phoneFrame}>
          <div style={styles.phoneHeader}>
            <div style={styles.avatarCircle}>{USER.avatar}</div>
            <div style={styles.phoneHeaderText}>
              <span style={styles.phoneTitle}>{USER.name}</span>
              <span style={styles.phoneSubtitle}>{USER.handle}</span>
            </div>
            <div style={styles.phoneStatus}>
              <span style={styles.statusDot} />
              <span style={styles.statusText}>Online</span>
            </div>
          </div>
          <div style={styles.phoneContent}>
            <MessageList messages={messages} />
            {step === "idle" && (
              <div style={styles.inputHint}>
                <span style={styles.hintText}>Select a feeling above to start</span>
              </div>
            )}
          </div>
        </div>

        {/* Analysis Panel */}
        <div style={styles.analysisPanel}>
          {!showAnalysis ? (
            <div style={styles.waitingAnalysis}>
              <span style={styles.waitingIcon}>🔮</span>
              <span style={styles.waitingText}>
                {step === "idle" ? "Select how you're feeling" : "Analyzing..."}
              </span>
            </div>
          ) : analysis && symptom && (
            <>
              {/* Causes */}
              <div style={styles.causesSection}>
                <h3 style={styles.sectionTitle}>What's Contributing</h3>
                {analysis.causes.map((cause, i) => (
                  <div key={i} style={styles.causeRow}>
                    <span style={styles.causeFactor}>{cause.factor}</span>
                    <div style={styles.causeBar}>
                      <div style={{ ...styles.causeBarFill, width: `${cause.percent}%`, background: symptom.color }} />
                    </div>
                    <span style={styles.causePercent}>{cause.percent}%</span>
                  </div>
                ))}
              </div>

              {/* Pattern Match */}
              <div style={styles.patternSection}>
                <h3 style={styles.sectionTitle}>Your Pattern</h3>
                <div style={styles.patternCard}>
                  <span style={styles.patternIcon}>📊</span>
                  <div style={styles.patternContent}>
                    <p style={styles.patternText}>{analysis.pattern}</p>
                    <p style={styles.recoveryText}>Last time, you felt better after:</p>
                    <ul style={styles.recoveryList}>
                      {analysis.recovery.map((item, i) => (
                        <li key={i}>{item}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div style={styles.actionsSection}>
                <h3 style={styles.sectionTitle}>What To Do Today</h3>
                {analysis.actions.map((action, i) => (
                  <div key={i} style={styles.actionRow}>
                    <span style={styles.actionCheck}>☐</span>
                    <div style={styles.actionContent}>
                      <span style={styles.actionTask}>{action.task}</span>
                      <span style={styles.actionWhy}>{action.why}</span>
                    </div>
                  </div>
                ))}
                <div style={styles.trackPrompt}>
                  <span style={styles.trackIcon}>💡</span>
                  <span style={styles.trackText}>This worked for you before. Want me to remind you?</span>
                </div>
                <div style={styles.actionButtons}>
                  <button style={styles.trackButton}>Track for 1 week</button>
                  <button style={styles.dismissButton}>Just show me</button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Reset */}
      {step !== "idle" && (
        <div style={styles.controls}>
          <button onClick={resetDemo} style={styles.buttonSecondary}>
            Try Another Feeling
          </button>
        </div>
      )}

      {/* Explanation */}
      <div style={styles.explanation}>
        <h3 style={styles.explainTitle}>The Difference</h3>
        <div style={styles.comparisonGrid}>
          <div style={styles.comparisonCard}>
            <span style={styles.comparisonHeader}>❌ Generic AI</span>
            <ul style={styles.comparisonList}>
              <li>"Try getting more sleep"</li>
              <li>"Exercise regularly"</li>
              <li>"Eat healthy foods"</li>
              <li>Same advice for everyone</li>
            </ul>
          </div>
          <div style={styles.comparisonCardGood}>
            <span style={styles.comparisonHeader}>✅ Sakhi</span>
            <ul style={styles.comparisonList}>
              <li>Connects YOUR patterns</li>
              <li>"Last time this happened..."</li>
              <li>"This worked for YOU before"</li>
              <li>Tracks if it actually helps</li>
            </ul>
          </div>
        </div>
      </div>
    </main>
  );
}

// Message List Component
function MessageList({ messages }: { messages: Message[] }) {
  return (
    <div style={styles.messageList}>
      {messages.map((msg, i) => (
        <div
          key={i}
          style={{
            ...styles.message,
            ...(msg.sender === "user"
              ? styles.messageUser
              : msg.sender === "system"
                ? styles.messageSystem
                : styles.messageSakhi),
          }}
        >
          {msg.thinking && <span style={styles.thinkingDot}>•••</span>}
          <span style={styles.messageText}>{msg.content}</span>
        </div>
      ))}
    </div>
  );
}

// Utility
function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// Styles
const styles: Record<string, React.CSSProperties> = {
  container: {
    minHeight: "100vh",
    background: palette.bg,
    color: palette.fg,
    padding: "40px 24px",
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  },
  header: {
    textAlign: "center",
    marginBottom: 24,
  },
  title: {
    fontSize: 28,
    fontWeight: 600,
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 16,
    color: palette.muted,
  },
  // Symptom Selector
  symptomSelector: {
    maxWidth: 700,
    margin: "0 auto 32px",
    textAlign: "center",
  },
  selectorLabel: {
    fontSize: 14,
    color: palette.muted,
    marginBottom: 16,
  },
  symptomGrid: {
    display: "flex",
    justifyContent: "center",
    gap: 12,
    flexWrap: "wrap",
  },
  symptomButton: {
    padding: "12px 20px",
    borderRadius: 12,
    border: "1px solid",
    background: "transparent",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: 6,
    transition: "all 0.2s",
  },
  symptomLabel: {
    fontSize: 14,
    fontWeight: 500,
  },
  doshaTag: {
    padding: "2px 8px",
    borderRadius: 8,
    fontSize: 11,
    fontWeight: 500,
  },
  // Main Content
  mainContent: {
    display: "flex",
    justifyContent: "center",
    alignItems: "flex-start",
    gap: 24,
    marginBottom: 40,
    flexWrap: "wrap",
  },
  // Phone
  phoneFrame: {
    width: 340,
    minHeight: 400,
    background: palette.cardBg,
    borderRadius: 24,
    border: `1px solid ${palette.divider}`,
    overflow: "hidden",
    display: "flex",
    flexDirection: "column",
  },
  phoneHeader: {
    padding: "16px 20px",
    borderBottom: `1px solid ${palette.divider}`,
    display: "flex",
    alignItems: "center",
    gap: 12,
  },
  avatarCircle: {
    width: 40,
    height: 40,
    borderRadius: "50%",
    background: palette.accentDim,
    color: palette.accent,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontWeight: 600,
    fontSize: 16,
  },
  phoneHeaderText: {
    flex: 1,
    display: "flex",
    flexDirection: "column",
  },
  phoneTitle: {
    fontSize: 16,
    fontWeight: 600,
  },
  phoneSubtitle: {
    fontSize: 13,
    color: palette.muted,
  },
  phoneStatus: {
    display: "flex",
    alignItems: "center",
    gap: 6,
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: "50%",
    background: palette.success,
  },
  statusText: {
    fontSize: 12,
    color: palette.muted,
  },
  phoneContent: {
    flex: 1,
    padding: 16,
    overflowY: "auto",
  },
  messageList: {
    display: "flex",
    flexDirection: "column",
    gap: 12,
  },
  message: {
    padding: "12px 16px",
    borderRadius: 16,
    maxWidth: "90%",
    lineHeight: 1.5,
  },
  messageUser: {
    background: palette.accent,
    color: "#fff",
    alignSelf: "flex-end",
    borderBottomRightRadius: 4,
  },
  messageSakhi: {
    background: palette.divider,
    alignSelf: "flex-start",
    borderBottomLeftRadius: 4,
  },
  messageSystem: {
    background: "transparent",
    border: `1px dashed ${palette.divider}`,
    fontSize: 13,
    color: palette.muted,
    alignSelf: "stretch",
    maxWidth: "100%",
    whiteSpace: "pre-line",
  },
  messageText: {
    fontSize: 14,
    whiteSpace: "pre-line",
  },
  thinkingDot: {
    opacity: 0.5,
    marginRight: 4,
  },
  inputHint: {
    marginTop: "auto",
    padding: 16,
    textAlign: "center",
  },
  hintText: {
    color: palette.muted,
    fontSize: 14,
  },
  // Analysis Panel
  analysisPanel: {
    width: 380,
    background: palette.cardBg,
    borderRadius: 16,
    border: `1px solid ${palette.divider}`,
    padding: 20,
    minHeight: 400,
  },
  waitingAnalysis: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    height: 300,
    gap: 12,
  },
  waitingIcon: {
    fontSize: 40,
    opacity: 0.5,
  },
  waitingText: {
    color: palette.muted,
    fontSize: 14,
  },
  // Causes Section
  causesSection: {
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 14,
    fontWeight: 600,
    marginBottom: 12,
    color: palette.muted,
  },
  causeRow: {
    display: "flex",
    alignItems: "center",
    gap: 12,
    marginBottom: 8,
  },
  causeFactor: {
    fontSize: 13,
    width: 160,
    flexShrink: 0,
  },
  causeBar: {
    flex: 1,
    height: 8,
    background: palette.divider,
    borderRadius: 4,
    overflow: "hidden",
  },
  causeBarFill: {
    height: "100%",
    borderRadius: 4,
    transition: "width 0.5s ease",
  },
  causePercent: {
    fontSize: 12,
    color: palette.muted,
    width: 36,
    textAlign: "right",
  },
  // Pattern Section
  patternSection: {
    marginBottom: 24,
  },
  patternCard: {
    display: "flex",
    gap: 12,
    padding: 14,
    background: "rgba(244, 63, 94, 0.1)",
    borderRadius: 12,
    border: `1px solid ${palette.accentDim}`,
  },
  patternIcon: {
    fontSize: 24,
  },
  patternContent: {
    flex: 1,
  },
  patternText: {
    fontSize: 13,
    marginBottom: 10,
    lineHeight: 1.5,
  },
  recoveryText: {
    fontSize: 12,
    color: palette.muted,
    marginBottom: 6,
  },
  recoveryList: {
    margin: 0,
    paddingLeft: 16,
    fontSize: 12,
    color: palette.success,
    lineHeight: 1.6,
  },
  // Actions Section
  actionsSection: {},
  actionRow: {
    display: "flex",
    alignItems: "flex-start",
    gap: 10,
    padding: "10px 0",
    borderBottom: `1px solid ${palette.divider}`,
  },
  actionCheck: {
    fontSize: 16,
    color: palette.muted,
    marginTop: 2,
  },
  actionContent: {
    flex: 1,
    display: "flex",
    flexDirection: "column",
    gap: 2,
  },
  actionTask: {
    fontSize: 14,
    fontWeight: 500,
  },
  actionWhy: {
    fontSize: 12,
    color: palette.muted,
  },
  trackPrompt: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    marginTop: 16,
    padding: 12,
    background: palette.accentDim,
    borderRadius: 8,
  },
  trackIcon: {
    fontSize: 16,
  },
  trackText: {
    fontSize: 12,
    color: palette.accent,
  },
  actionButtons: {
    display: "flex",
    gap: 8,
    marginTop: 12,
  },
  trackButton: {
    flex: 1,
    padding: "10px 16px",
    background: palette.accent,
    color: "#fff",
    border: "none",
    borderRadius: 8,
    fontSize: 13,
    fontWeight: 500,
    cursor: "pointer",
  },
  dismissButton: {
    padding: "10px 16px",
    background: "transparent",
    color: palette.muted,
    border: `1px solid ${palette.divider}`,
    borderRadius: 8,
    fontSize: 13,
    cursor: "pointer",
  },
  // Controls
  controls: {
    display: "flex",
    justifyContent: "center",
    marginBottom: 40,
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
  // Explanation
  explanation: {
    maxWidth: 700,
    margin: "0 auto",
    padding: 24,
    background: palette.cardBg,
    borderRadius: 16,
    border: `1px solid ${palette.divider}`,
  },
  explainTitle: {
    fontSize: 16,
    fontWeight: 600,
    marginBottom: 16,
    textAlign: "center",
  },
  comparisonGrid: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: 16,
  },
  comparisonCard: {
    padding: 16,
    background: "rgba(244, 63, 94, 0.1)",
    borderRadius: 12,
    border: "1px solid rgba(244, 63, 94, 0.2)",
  },
  comparisonCardGood: {
    padding: 16,
    background: "rgba(34, 197, 94, 0.1)",
    borderRadius: 12,
    border: "1px solid rgba(34, 197, 94, 0.2)",
  },
  comparisonHeader: {
    display: "block",
    fontSize: 14,
    fontWeight: 600,
    marginBottom: 12,
  },
  comparisonList: {
    margin: 0,
    paddingLeft: 16,
    fontSize: 13,
    lineHeight: 1.8,
    color: palette.muted,
  },
};
