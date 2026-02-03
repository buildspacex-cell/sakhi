"use client";

import { useState, useCallback } from "react";
import MeshConnection, { type ConnectionState } from "../components/MeshConnection";

/**
 * Family Coordination Demo
 * ------------------------
 * ACT 2: Sakhi-to-Sakhi Coordination
 *
 * Two scenarios:
 * 1. Weekend Plans - Simple coordination (visit parents)
 * 2. The 3pm Problem - Complex multi-party negotiation (school pickup)
 *
 * Shows: Seamless coordination, conflict resolution, human-in-the-loop
 */

export const dynamic = "force-dynamic";

type DemoMode = "simple" | "complex";

// Demo personas
const ALEX = {
  name: "Alex",
  handle: "@alex",
  avatar: "A",
  role: "You",
};

const MOM = {
  name: "Mom",
  handle: "@sunita",
  avatar: "S",
  role: "Grandma",
};

const PRIYA = {
  name: "Priya",
  handle: "@priya",
  avatar: "P",
  role: "Wife",
};

// ===============================
// SIMPLE SCENARIO: Weekend Plans
// ===============================
type SimpleStep =
  | "idle"
  | "user_request"
  | "sakhi_thinking"
  | "connecting"
  | "checking_mom"
  | "mom_responds"
  | "found_time"
  | "confirming"
  | "complete";

// ===============================
// COMPLEX SCENARIO: 3pm Problem
// ===============================
type ComplexStep =
  | "idle"
  | "alert"
  | "alex_conflict"
  | "sakhis_connecting"
  | "priya_checking"
  | "priya_conflict"
  | "negotiating"
  | "options_found"
  | "user_decides"
  | "resolution"
  | "complete";

interface Message {
  sender: "user" | "sakhi" | "system" | "alert";
  content: string;
  thinking?: boolean;
  options?: { id: string; label: string; desc: string }[];
}

// Color palette
const palette = {
  bg: "#0e0f12",
  cardBg: "#1a1b1e",
  fg: "#f4f4f5",
  muted: "#71717a",
  accent: "#6366f1",
  accentDim: "rgba(99, 102, 241, 0.2)",
  emerald: "#10b981",
  emeraldDim: "rgba(16, 185, 129, 0.2)",
  amber: "#f59e0b",
  amberDim: "rgba(245, 158, 11, 0.2)",
  rose: "#f43f5e",
  roseDim: "rgba(244, 63, 94, 0.2)",
  success: "#22c55e",
  divider: "#27272a",
};

// Connection state helpers for SIMPLE scenario
function getSimpleConnectionState(step: SimpleStep): ConnectionState {
  switch (step) {
    case "idle": return "idle";
    case "user_request": return "idle";
    case "sakhi_thinking": return "connecting";
    case "connecting": return "connecting";
    case "checking_mom": return "coordinating";
    case "mom_responds": return "coordinating";
    case "found_time": return "active";
    case "confirming": return "confirmed";
    case "complete": return "complete";
    default: return "idle";
  }
}

function getSimpleConnectionStatusText(step: SimpleStep): string {
  switch (step) {
    case "sakhi_thinking": return "Thinking...";
    case "connecting": return "Connecting to Mom's Sakhi...";
    case "checking_mom": return "Checking schedule...";
    case "mom_responds": return "Negotiating...";
    case "found_time": return "Time found!";
    case "confirming": return "Confirming...";
    case "complete": return "All set!";
    default: return "";
  }
}

// Connection state helpers for COMPLEX scenario
function getComplexConnectionState(step: ComplexStep): ConnectionState {
  switch (step) {
    case "idle": return "idle";
    case "alert": return "idle";
    case "alex_conflict": return "connecting";
    case "sakhis_connecting": return "connecting";
    case "priya_checking": return "coordinating";
    case "priya_conflict": return "coordinating";
    case "negotiating": return "coordinating";
    case "options_found": return "active";
    case "user_decides": return "active";
    case "resolution": return "confirmed";
    case "complete": return "complete";
    default: return "idle";
  }
}

function getComplexConnectionStatusText(step: ComplexStep): string {
  switch (step) {
    case "sakhis_connecting": return "Connecting...";
    case "priya_checking": return "Checking Priya's schedule...";
    case "priya_conflict": return "Conflict detected";
    case "negotiating": return "Finding solutions...";
    case "options_found": return "Options ready";
    case "user_decides": return "Waiting for decision...";
    case "resolution": return "Resolved!";
    case "complete": return "All set";
    default: return "";
  }
}

export default function CoordinationDemo() {
  const [mode, setMode] = useState<DemoMode>("simple");
  const [simpleStep, setSimpleStep] = useState<SimpleStep>("idle");
  const [complexStep, setComplexStep] = useState<ComplexStep>("idle");
  const [leftMessages, setLeftMessages] = useState<Message[]>([]);
  const [rightMessages, setRightMessages] = useState<Message[]>([]);
  const [selectedOption, setSelectedOption] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);

  // ===============================
  // SIMPLE DEMO: Weekend Plans
  // ===============================
  const runSimpleDemo = useCallback(async () => {
    if (isRunning) return;
    setIsRunning(true);
    setLeftMessages([]);
    setRightMessages([]);

    // Step 1: User makes request
    setSimpleStep("user_request");
    setLeftMessages([
      { sender: "user", content: "I want to visit Mom this weekend" },
    ]);
    await delay(1500);

    // Step 2: Sakhi thinks
    setSimpleStep("sakhi_thinking");
    setLeftMessages((prev) => [
      ...prev,
      {
        sender: "sakhi",
        content: "Let me coordinate with Mom's Sakhi to find a good time.",
        thinking: true,
      },
    ]);
    await delay(1200);

    // Step 3: Connecting
    setSimpleStep("connecting");
    await delay(1000);

    // Step 4: Checking Mom's schedule
    setSimpleStep("checking_mom");
    setRightMessages([
      {
        sender: "sakhi",
        content: "Alex's Sakhi is asking about a weekend visit. Let me check your schedule...",
        thinking: true,
      },
    ]);
    await delay(1500);

    // Step 5: Mom's Sakhi responds
    setSimpleStep("mom_responds");
    setRightMessages((prev) => [
      ...prev,
      {
        sender: "system",
        content: `Weekend Schedule:
━━━━━━━━━━━━━━━━
📅 Saturday: Temple in morning, free after 2pm
📅 Sunday: Free all day
🍳 Note: Mom mentioned wanting to cook biryani for Alex`,
      },
    ]);
    setLeftMessages((prev) => [
      ...prev,
      {
        sender: "system",
        content: `Mom's Sakhi reports:
✓ Saturday after 2pm works
✓ Sunday all day works
💡 She's been wanting to make biryani for you!`,
      },
    ]);
    await delay(2500);

    // Step 6: Found a time
    setSimpleStep("found_time");
    setLeftMessages((prev) => [
      ...prev,
      {
        sender: "sakhi",
        content: `Found the perfect time!

📅 **Sunday Brunch**
⏰ 11am - Come hungry!
🍚 Mom is planning biryani
🏠 Her place

Should I confirm this?`,
      },
    ]);
    setRightMessages((prev) => [
      ...prev,
      {
        sender: "sakhi",
        content: `Alex wants to visit Sunday for brunch. I suggested 11am so you have time to prepare biryani. Waiting for confirmation...`,
      },
    ]);
    await delay(2500);

    // Step 7: Auto-confirm (in real app, user would tap)
    setLeftMessages((prev) => [
      ...prev,
      { sender: "user", content: "Yes, confirm it!" },
    ]);
    await delay(1000);

    // Step 8: Confirming
    setSimpleStep("confirming");
    setLeftMessages((prev) => [
      ...prev,
      {
        sender: "sakhi",
        content: `Done! 🎉

✅ **Sunday Brunch confirmed**
📍 Mom's place at 11am
🍚 Biryani is happening!

📅 Added to your calendar
📱 Mom has been notified

I also set a reminder for Saturday evening to pick up flowers on the way.`,
      },
    ]);
    setRightMessages((prev) => [
      ...prev,
      {
        sender: "sakhi",
        content: `Confirmed! Alex is coming Sunday at 11am.

📅 Added to your calendar
🛒 I've added biryani ingredients to your shopping list
⏰ Reminder set for Sunday 9am to start cooking`,
      },
    ]);
    await delay(2000);

    setSimpleStep("complete");
    setIsRunning(false);
  }, [isRunning]);

  // ===============================
  // COMPLEX DEMO: 3pm Problem
  // ===============================
  const runComplexDemo = useCallback(async () => {
    if (isRunning) return;
    setIsRunning(true);
    setSelectedOption(null);
    setLeftMessages([]);
    setRightMessages([]);

    // Step 1: Alert - Meeting conflict detected
    setComplexStep("alert");
    setLeftMessages([
      {
        sender: "alert",
        content: `⚠️ Schedule Conflict Detected

Your 2:30pm meeting just moved to 3pm.
But Aanya's school pickup is at 3pm.`,
      },
    ]);
    await delay(2500);

    // Step 2: Alex's Sakhi identifies the problem
    setComplexStep("alex_conflict");
    setLeftMessages((prev) => [
      ...prev,
      {
        sender: "sakhi",
        content: "I see the conflict. Let me check with Priya's Sakhi to coordinate pickup.",
        thinking: true,
      },
    ]);
    await delay(1500);

    // Step 3: Sakhis connecting
    setComplexStep("sakhis_connecting");
    await delay(1200);

    // Step 4: Priya's side - checking
    setComplexStep("priya_checking");
    setRightMessages([
      {
        sender: "sakhi",
        content: "Alex's Sakhi is reaching out about Aanya's pickup today. Checking your schedule...",
        thinking: true,
      },
    ]);
    await delay(1500);

    // Step 5: Priya also has a conflict
    setComplexStep("priya_conflict");
    setRightMessages((prev) => [
      ...prev,
      {
        sender: "system",
        content: `Schedule Check:
━━━━━━━━━━━━━━━━
📅 3:00 PM - Client call with Acme Corp
⏱️ Duration: 45 min (can't be moved)
🚗 School is 15 min away

❌ Direct pickup not possible`,
      },
    ]);
    setLeftMessages((prev) => [
      ...prev,
      {
        sender: "system",
        content: `Priya's Sakhi reports:
She has a client call at 3pm that can't be moved.`,
      },
    ]);
    await delay(2500);

    // Step 6: Sakhis negotiate and find options
    setComplexStep("negotiating");
    setLeftMessages((prev) => [
      ...prev,
      {
        sender: "sakhi",
        content: "Both schedules have conflicts. Analyzing options...",
        thinking: true,
      },
    ]);
    setRightMessages((prev) => [
      ...prev,
      {
        sender: "sakhi",
        content: "Working with Alex's Sakhi to find solutions...",
        thinking: true,
      },
    ]);
    await delay(2000);

    // Show what Sakhis are considering
    setLeftMessages((prev) => [
      ...prev,
      {
        sender: "system",
        content: `Considering:
• Alex's meeting importance (internal, movable?)
• Priya's call (external client, fixed)
• Grandma Sunita's availability
• After-school program option
• Traffic at 3pm (12 min, not 15)`,
      },
    ]);
    await delay(2500);

    // Step 7: Options found
    setComplexStep("options_found");
    setLeftMessages((prev) => [
      ...prev,
      {
        sender: "sakhi",
        content: `Found 3 options:

**Option A: You leave meeting 10 min early**
Your meeting is internal. I can message your team that you need to leave by 2:50pm. You'd reach school at 3:02pm.
→ Impact: Miss last 10 min of meeting

**Option B: Grandma Sunita picks up**
She's free this afternoon (checked her calendar). Lives 8 min from school.
→ Impact: None to your schedules

**Option C: After-school program**
Aanya can stay until 4pm. You'd pick up after your meeting.
→ Impact: Aanya waits 45 min`,
      },
    ]);
    setRightMessages((prev) => [
      ...prev,
      {
        sender: "sakhi",
        content: `Alex's Sakhi found 3 options. Here's the summary:

A. Alex leaves meeting early
B. Grandma Sunita picks up
C. After-school program

Waiting for one of you to decide...`,
      },
    ]);
    await delay(3000);

    // Step 8: User decision required
    setComplexStep("user_decides");
    setLeftMessages((prev) => [
      ...prev,
      {
        sender: "sakhi",
        content: "Which option works best?",
        options: [
          { id: "A", label: "I'll leave early", desc: "You handle it" },
          { id: "B", label: "Ask Grandma", desc: "Best for schedules" },
          { id: "C", label: "After-school", desc: "Aanya waits" },
        ],
      },
    ]);
    await delay(1000);

    // Wait for user selection (simulated after delay)
    await delay(3000);

    // Simulate user selecting Option B
    setSelectedOption("B");
    setLeftMessages((prev) => [
      ...prev,
      { sender: "user", content: "Let's ask Grandma" },
    ]);
    await delay(1000);

    // Step 9: Resolution
    setComplexStep("resolution");
    setLeftMessages((prev) => [
      ...prev,
      {
        sender: "sakhi",
        content: `Done! Here's what I arranged:

✅ **Grandma Sunita confirmed**
   She'll pick up Aanya at 3pm

📱 **Notified everyone:**
   • Messaged Grandma with school address
   • Told school office (Sunita is authorized)
   • Aanya knows Grandma is coming

📅 **Your calendar updated:**
   Meeting stays at 3pm, no changes needed

💡 **For next time:**
   I'll add Grandma as backup option when you both have afternoon conflicts.`,
      },
    ]);
    setRightMessages((prev) => [
      ...prev,
      {
        sender: "sakhi",
        content: `Resolved! Alex chose Option B.

✅ Grandma Sunita will pick up Aanya
📞 I've updated your mom that she's on pickup duty
📅 Your client call is unaffected

Aanya is covered. Focus on your call!`,
      },
    ]);
    await delay(2000);

    setComplexStep("complete");
    setIsRunning(false);
  }, [isRunning]);

  const resetDemo = () => {
    setSimpleStep("idle");
    setComplexStep("idle");
    setLeftMessages([]);
    setRightMessages([]);
    setSelectedOption(null);
    setIsRunning(false);
  };

  const switchMode = (newMode: DemoMode) => {
    if (isRunning) return;
    setMode(newMode);
    resetDemo();
  };

  const isSimpleMode = mode === "simple";
  const currentStep = isSimpleMode ? simpleStep : complexStep;

  // Get the right personas for each mode
  const leftPerson = ALEX;
  const rightPerson = isSimpleMode ? MOM : PRIYA;
  const leftRole = isSimpleMode ? "You" : "Dad";
  const rightRole = isSimpleMode ? "Mom" : "Mom";

  return (
    <main style={styles.container}>
      {/* Header */}
      <header style={styles.header}>
        <h1 style={styles.title}>
          {isSimpleMode ? "Weekend Plans" : "The 3pm Problem"}
        </h1>
        <p style={styles.subtitle}>
          {isSimpleMode
            ? "Sakhi coordinates with Mom's Sakhi to find the perfect time"
            : "When both parents have conflicts, Sakhis find a solution"
          }
        </p>
      </header>

      {/* Mode Tabs */}
      <div style={styles.tabContainer}>
        <button
          onClick={() => switchMode("simple")}
          style={mode === "simple" ? styles.tabActive : styles.tab}
          disabled={isRunning}
        >
          <span style={styles.tabIcon}>💬</span>
          Simple
        </button>
        <button
          onClick={() => switchMode("complex")}
          style={mode === "complex" ? styles.tabActive : styles.tab}
          disabled={isRunning}
        >
          <span style={styles.tabIcon}>🔀</span>
          Complex
        </button>
      </div>

      {/* Context Bar */}
      <div style={styles.contextBar}>
        {isSimpleMode ? (
          <>
            <div style={styles.contextItem}>
              <span style={styles.contextIcon}>📅</span>
              <span style={styles.contextText}>Planning a weekend visit</span>
            </div>
            <div style={styles.contextItem}>
              <span style={styles.contextIcon}>👩</span>
              <span style={styles.contextText}>Mom lives 30 min away</span>
            </div>
          </>
        ) : (
          <>
            <div style={styles.contextItem}>
              <span style={styles.contextIcon}>👧</span>
              <span style={styles.contextText}>Aanya (age 7) · School pickup at 3pm</span>
            </div>
            <div style={styles.contextItem}>
              <span style={styles.contextIcon}>⏰</span>
              <span style={styles.contextText}>Current time: 2:15pm</span>
            </div>
          </>
        )}
      </div>

      {/* Split Screen */}
      <div style={styles.splitContainer}>
        {/* Left Phone - Alex */}
        <div style={styles.phoneFrame}>
          <div style={styles.phoneHeader}>
            <div style={{ ...styles.avatarCircle, background: palette.accentDim, color: palette.accent }}>
              {leftPerson.avatar}
            </div>
            <div style={styles.phoneHeaderText}>
              <span style={styles.phoneTitle}>{leftPerson.name}</span>
              <span style={styles.phoneSubtitle}>{leftRole}</span>
            </div>
            <div style={styles.phoneStatus}>
              <span style={styles.statusDot} />
              <span style={styles.statusText}>Online</span>
            </div>
          </div>
          <div style={styles.phoneContent}>
            <MessageList
              messages={leftMessages}
              accentColor={palette.accent}
              selectedOption={selectedOption}
              showOptions={!isSimpleMode && complexStep === "user_decides"}
            />
            {currentStep === "idle" && (
              <div style={styles.inputHint}>
                <span style={styles.hintText}>Tap "Start Demo" to begin</span>
              </div>
            )}
          </div>
        </div>

        {/* Center Connection */}
        <div style={styles.connectionArea}>
          <MeshConnection
            state={isSimpleMode ? getSimpleConnectionState(simpleStep) : getComplexConnectionState(complexStep)}
            leftLabel={`${leftPerson.name}'s Sakhi`}
            rightLabel={`${rightPerson.name}'s Sakhi`}
            statusText={isSimpleMode ? getSimpleConnectionStatusText(simpleStep) : getComplexConnectionStatusText(complexStep)}
          />
          {!isSimpleMode && complexStep === "negotiating" && (
            <div style={styles.negotiatingBadge}>
              <span>🤝 Negotiating...</span>
            </div>
          )}
        </div>

        {/* Right Phone - Mom/Priya */}
        <div style={styles.phoneFrame}>
          <div style={styles.phoneHeader}>
            <div style={{ ...styles.avatarCircle, background: palette.emeraldDim, color: palette.emerald }}>
              {rightPerson.avatar}
            </div>
            <div style={styles.phoneHeaderText}>
              <span style={styles.phoneTitle}>{rightPerson.name}</span>
              <span style={styles.phoneSubtitle}>{rightRole}</span>
            </div>
            <div style={styles.phoneStatus}>
              <span style={styles.statusDot} />
              <span style={styles.statusText}>Online</span>
            </div>
          </div>
          <div style={styles.phoneContent}>
            {rightMessages.length === 0 && currentStep !== "idle" && (
              <div style={styles.waitingState}>
                <span style={styles.waitingDot}>•</span>
                <span style={styles.waitingText}>Waiting...</span>
              </div>
            )}
            <MessageList
              messages={rightMessages}
              accentColor={palette.emerald}
              selectedOption={null}
              showOptions={false}
            />
          </div>
        </div>
      </div>

      {/* Controls */}
      <div style={styles.controls}>
        <button
          onClick={isSimpleMode ? runSimpleDemo : runComplexDemo}
          disabled={isRunning}
          style={isRunning ? styles.buttonDisabled : styles.button}
        >
          {isRunning ? "In Progress..." : currentStep === "complete" ? "Run Again" : "Start Demo"}
        </button>
        {currentStep !== "idle" && (
          <button onClick={resetDemo} style={styles.buttonSecondary}>
            Reset
          </button>
        )}
      </div>

      {/* Explanation */}
      <div style={styles.explanation}>
        <h3 style={styles.explainTitle}>What Just Happened</h3>
        {isSimpleMode ? (
          <>
            <div style={styles.timelineGrid}>
              <div style={styles.timelineItem}>
                <span style={styles.timelineIcon}>💬</span>
                <div style={styles.timelineContent}>
                  <span style={styles.timelineTitle}>Request Made</span>
                  <span style={styles.timelineDesc}>You said "visit Mom this weekend"</span>
                </div>
              </div>
              <div style={styles.timelineItem}>
                <span style={styles.timelineIcon}>🔗</span>
                <div style={styles.timelineContent}>
                  <span style={styles.timelineTitle}>Sakhis Connected</span>
                  <span style={styles.timelineDesc}>Checked both schedules automatically</span>
                </div>
              </div>
              <div style={styles.timelineItem}>
                <span style={styles.timelineIcon}>✨</span>
                <div style={styles.timelineContent}>
                  <span style={styles.timelineTitle}>Perfect Time Found</span>
                  <span style={styles.timelineDesc}>Sunday brunch with biryani!</span>
                </div>
              </div>
              <div style={styles.timelineItem}>
                <span style={styles.timelineIcon}>✅</span>
                <div style={styles.timelineContent}>
                  <span style={styles.timelineTitle}>Everything Handled</span>
                  <span style={styles.timelineDesc}>Calendars, reminders, shopping list</span>
                </div>
              </div>
            </div>
            <div style={styles.keyInsight}>
              <span style={styles.keyIcon}>💡</span>
              <p style={styles.keyText}>
                <strong>The key:</strong> One simple request → calendars checked, time negotiated,
                everyone notified, reminders set. No back-and-forth texts needed.
              </p>
            </div>
          </>
        ) : (
          <>
            <div style={styles.timelineGrid}>
              <div style={styles.timelineItem}>
                <span style={styles.timelineIcon}>⚠️</span>
                <div style={styles.timelineContent}>
                  <span style={styles.timelineTitle}>Conflict Detected</span>
                  <span style={styles.timelineDesc}>Alex's meeting moved, overlaps with pickup</span>
                </div>
              </div>
              <div style={styles.timelineItem}>
                <span style={styles.timelineIcon}>🔗</span>
                <div style={styles.timelineContent}>
                  <span style={styles.timelineTitle}>Sakhis Connected</span>
                  <span style={styles.timelineDesc}>Checked Priya's schedule — also blocked</span>
                </div>
              </div>
              <div style={styles.timelineItem}>
                <span style={styles.timelineIcon}>🤝</span>
                <div style={styles.timelineContent}>
                  <span style={styles.timelineTitle}>Options Generated</span>
                  <span style={styles.timelineDesc}>Considered grandma, after-school, meeting flexibility</span>
                </div>
              </div>
              <div style={styles.timelineItem}>
                <span style={styles.timelineIcon}>👆</span>
                <div style={styles.timelineContent}>
                  <span style={styles.timelineTitle}>Human Decides</span>
                  <span style={styles.timelineDesc}>Alex chose grandma — Sakhis executed</span>
                </div>
              </div>
            </div>
            <div style={styles.keyInsight}>
              <span style={styles.keyIcon}>💡</span>
              <p style={styles.keyText}>
                <strong>The key:</strong> Sakhis handle the complexity (checking schedules, finding options,
                coordinating execution). Humans make the final call. No 47 texts. No forgotten details.
              </p>
            </div>
          </>
        )}
      </div>
    </main>
  );
}

// Message List Component
function MessageList({
  messages,
  accentColor,
  selectedOption,
  showOptions,
}: {
  messages: Message[];
  accentColor: string;
  selectedOption: string | null;
  showOptions: boolean;
}) {
  return (
    <div style={styles.messageList}>
      {messages.map((msg, i) => (
        <div
          key={i}
          style={{
            ...styles.message,
            ...(msg.sender === "user"
              ? { ...styles.messageUser, background: accentColor }
              : msg.sender === "alert"
                ? styles.messageAlert
                : msg.sender === "system"
                  ? styles.messageSystem
                  : styles.messageSakhi),
          }}
        >
          {msg.thinking && <span style={styles.thinkingDot}>•••</span>}
          <span style={styles.messageText}>{msg.content}</span>

          {/* Options buttons */}
          {msg.options && showOptions && !selectedOption && (
            <div style={styles.optionsContainer}>
              {msg.options.map((opt) => (
                <button key={opt.id} style={styles.optionButton}>
                  <span style={styles.optionLabel}>{opt.label}</span>
                  <span style={styles.optionDesc}>{opt.desc}</span>
                </button>
              ))}
            </div>
          )}
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
    marginBottom: 16,
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
  // Tab styles
  tabContainer: {
    display: "flex",
    justifyContent: "center",
    gap: 8,
    marginBottom: 24,
  },
  tab: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    padding: "12px 24px",
    fontSize: 14,
    fontWeight: 500,
    background: "transparent",
    color: palette.muted,
    border: `1px solid ${palette.divider}`,
    borderRadius: 12,
    cursor: "pointer",
    transition: "all 0.2s",
  },
  tabActive: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    padding: "12px 24px",
    fontSize: 14,
    fontWeight: 500,
    background: palette.accentDim,
    color: palette.accent,
    border: `1px solid ${palette.accent}`,
    borderRadius: 12,
    cursor: "pointer",
  },
  tabIcon: {
    fontSize: 16,
  },
  // Context Bar
  contextBar: {
    display: "flex",
    justifyContent: "center",
    gap: 32,
    marginBottom: 32,
    padding: "12px 24px",
    background: palette.cardBg,
    borderRadius: 12,
    maxWidth: 600,
    margin: "0 auto 32px",
  },
  contextItem: {
    display: "flex",
    alignItems: "center",
    gap: 8,
  },
  contextIcon: {
    fontSize: 18,
  },
  contextText: {
    fontSize: 14,
    color: palette.muted,
  },
  // Split Container
  splitContainer: {
    display: "flex",
    justifyContent: "center",
    alignItems: "flex-start",
    gap: 24,
    marginBottom: 40,
    flexWrap: "wrap",
  },
  phoneFrame: {
    width: 360,
    minHeight: 520,
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
  connectionArea: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    minWidth: 200,
    minHeight: 200,
    padding: "0 16px",
  },
  negotiatingBadge: {
    marginTop: 12,
    padding: "6px 12px",
    background: palette.amberDim,
    color: palette.amber,
    borderRadius: 12,
    fontSize: 12,
    fontWeight: 500,
  },
  // Messages
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
    color: "#fff",
    alignSelf: "flex-end",
    borderBottomRightRadius: 4,
  },
  messageSakhi: {
    background: palette.divider,
    alignSelf: "flex-start",
    borderBottomLeftRadius: 4,
  },
  messageAlert: {
    background: palette.roseDim,
    border: `1px solid ${palette.rose}`,
    alignSelf: "stretch",
    maxWidth: "100%",
    whiteSpace: "pre-line",
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
  // Options
  optionsContainer: {
    display: "flex",
    flexDirection: "column",
    gap: 8,
    marginTop: 12,
  },
  optionButton: {
    padding: "10px 14px",
    background: palette.accentDim,
    border: `1px solid ${palette.accent}`,
    borderRadius: 10,
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    cursor: "pointer",
    transition: "all 0.2s",
  },
  optionLabel: {
    fontSize: 13,
    fontWeight: 500,
    color: palette.fg,
  },
  optionDesc: {
    fontSize: 11,
    color: palette.muted,
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
  waitingState: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: 40,
    gap: 8,
  },
  waitingDot: {
    color: palette.muted,
    fontSize: 24,
  },
  waitingText: {
    color: palette.muted,
    fontSize: 14,
  },
  // Controls
  controls: {
    display: "flex",
    justifyContent: "center",
    gap: 16,
    marginBottom: 40,
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
  // Explanation
  explanation: {
    maxWidth: 800,
    margin: "0 auto",
    padding: 24,
    background: palette.cardBg,
    borderRadius: 16,
    border: `1px solid ${palette.divider}`,
  },
  explainTitle: {
    fontSize: 16,
    fontWeight: 600,
    marginBottom: 20,
    textAlign: "center",
  },
  timelineGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(4, 1fr)",
    gap: 16,
    marginBottom: 24,
  },
  timelineItem: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    textAlign: "center",
    gap: 8,
  },
  timelineIcon: {
    fontSize: 24,
    marginBottom: 4,
  },
  timelineContent: {
    display: "flex",
    flexDirection: "column",
    gap: 4,
  },
  timelineTitle: {
    fontSize: 13,
    fontWeight: 600,
  },
  timelineDesc: {
    fontSize: 11,
    color: palette.muted,
    lineHeight: 1.4,
  },
  keyInsight: {
    display: "flex",
    alignItems: "flex-start",
    gap: 12,
    padding: 16,
    background: palette.accentDim,
    borderRadius: 12,
  },
  keyIcon: {
    fontSize: 20,
    flexShrink: 0,
  },
  keyText: {
    margin: 0,
    fontSize: 14,
    lineHeight: 1.6,
    color: palette.muted,
  },
};
