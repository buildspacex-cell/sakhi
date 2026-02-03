"use client";

import { useState, useCallback } from "react";
import MeshConnection, { type ConnectionState } from "../components/MeshConnection";

/**
 * Restaurant Experience Demo
 * ---------------------------
 * ACT 3: Business Knows You (With Your Consent)
 *
 * Shows split screen:
 * - Left: Customer's view (what they shared, what restaurant sees)
 * - Right: Restaurant's view (guest profile, suggested order)
 */

export const dynamic = "force-dynamic";

// Demo personas
const CUSTOMER = {
  name: "Alex",
  handle: "@alex",
  avatar: "A",
};

const RESTAURANT = {
  name: "Spice Garden",
  handle: "@spicegarden",
  avatar: "🍛",
};

// Customer profile that gets shared
const CUSTOMER_PROFILE = {
  visits: 4,
  favorites: ["Dal Makhani", "Garlic Naan"],
  spiceLevel: "Mild",
  dietary: ["Avoiding dairy this week"],
  currentState: "Pitta elevated",
  stateImplication: "Needs cooling foods",
};

// Suggested order based on profile
const SUGGESTED_ORDER = [
  {
    item: "Dal Makhani",
    modification: "Made with oat milk instead of cream",
    reason: "Your favorite — ordered 3 times",
    icon: "🍲",
  },
  {
    item: "Garlic Naan",
    modification: "No butter",
    reason: "You love this with the Dal",
    icon: "🫓",
  },
  {
    item: "Cucumber Raita",
    modification: "Coconut yogurt base",
    reason: "Cooling for your Pitta state",
    icon: "🥒",
  },
];

type DemoStep =
  | "idle"
  | "arriving"
  | "sakhi_connecting"
  | "profile_sharing"
  | "restaurant_receives"
  | "preparing_suggestion"
  | "suggestion_ready"
  | "confirmed";

interface Message {
  sender: "user" | "sakhi" | "system";
  content: string;
  thinking?: boolean;
}

// Color palette - warm amber for restaurant
const palette = {
  bg: "#0e0f12",
  cardBg: "#1a1b1e",
  fg: "#f4f4f5",
  muted: "#71717a",
  accent: "#f59e0b", // Amber for restaurant
  accentDim: "rgba(245, 158, 11, 0.2)",
  accentIndigo: "#6366f1",
  accentIndigoDim: "rgba(99, 102, 241, 0.2)",
  success: "#22c55e",
  successDim: "rgba(34, 197, 94, 0.2)",
  divider: "#27272a",
  rose: "#f43f5e",
  roseDim: "rgba(244, 63, 94, 0.2)",
};

function getConnectionState(step: DemoStep): ConnectionState {
  switch (step) {
    case "idle": return "idle";
    case "arriving": return "idle";
    case "sakhi_connecting": return "connecting";
    case "profile_sharing": return "coordinating";
    case "restaurant_receives": return "coordinating";
    case "preparing_suggestion": return "coordinating";
    case "suggestion_ready": return "confirmed";
    case "confirmed": return "complete";
    default: return "idle";
  }
}

function getConnectionStatusText(step: DemoStep): string {
  switch (step) {
    case "sakhi_connecting": return "Connecting...";
    case "profile_sharing": return "Sharing profile...";
    case "restaurant_receives": return "Preparing...";
    case "preparing_suggestion": return "Creating order...";
    case "suggestion_ready": return "Ready!";
    case "confirmed": return "Confirmed";
    default: return "";
  }
}

export default function DineDemo() {
  const [step, setStep] = useState<DemoStep>("idle");
  const [customerMessages, setCustomerMessages] = useState<Message[]>([]);
  const [restaurantMessages, setRestaurantMessages] = useState<Message[]>([]);
  const [showSuggestion, setShowSuggestion] = useState(false);
  const [isRunning, setIsRunning] = useState(false);

  const runDemo = useCallback(async () => {
    if (isRunning) return;
    setIsRunning(true);
    setShowSuggestion(false);

    // Reset
    setCustomerMessages([]);
    setRestaurantMessages([]);

    // Step 1: Customer arrives
    setStep("arriving");
    setCustomerMessages([
      { sender: "system", content: "📍 Arriving at Spice Garden" },
    ]);
    await delay(1500);

    // Step 2: Sakhi connects
    setStep("sakhi_connecting");
    setCustomerMessages((prev) => [
      ...prev,
      {
        sender: "sakhi",
        content: "I'll share your preferences with the restaurant so they can serve you better.",
        thinking: true,
      },
    ]);
    await delay(1500);

    // Step 3: Show what's being shared
    setStep("profile_sharing");
    setCustomerMessages((prev) => [
      ...prev,
      {
        sender: "system",
        content: `Sharing with Spice Garden:
✅ Spice preference: Mild
✅ Dietary: Avoiding dairy
✅ Current state: Needs cooling
✅ Past orders: Dal Makhani, Naan

🚫 NOT sharing:
• Location history
• Health details
• Financial info
• Other visits`,
      },
    ]);
    await delay(2500);

    // Step 4: Restaurant receives
    setStep("restaurant_receives");
    setRestaurantMessages([
      {
        sender: "system",
        content: "🔔 Guest arriving",
      },
      {
        sender: "sakhi",
        content: "Alex is here — 4th visit. I have their profile ready.",
      },
    ]);
    await delay(2000);

    // Step 5: Preparing suggestion
    setStep("preparing_suggestion");
    setRestaurantMessages((prev) => [
      ...prev,
      {
        sender: "system",
        content: `Guest Profile: Alex
━━━━━━━━━━━━━━━━━
🌶️ Spice: Mild only
🥛 Dietary: No dairy this week
⭐ Favorites: Dal Makhani, Naan
🔥 State: Pitta elevated
💡 Needs: Cooling foods`,
      },
    ]);
    await delay(2500);

    // Step 6: Suggestion ready
    setStep("suggestion_ready");
    setShowSuggestion(true);
    setRestaurantMessages((prev) => [
      ...prev,
      {
        sender: "sakhi",
        content: "I've prepared a personalized order suggestion based on their preferences and current state.",
      },
    ]);
    setCustomerMessages((prev) => [
      ...prev,
      {
        sender: "sakhi",
        content: `The restaurant is ready for you!

They know your preferences and have a personalized suggestion waiting.

🍽️ Your usual favorites, adapted for dairy-free
🥒 Added cooling dishes for your Pitta`,
      },
    ]);
    await delay(2000);

    // Step 7: Confirmed
    setStep("confirmed");
    setIsRunning(false);
  }, [isRunning]);

  const resetDemo = () => {
    setStep("idle");
    setCustomerMessages([]);
    setRestaurantMessages([]);
    setShowSuggestion(false);
    setIsRunning(false);
  };

  return (
    <main style={styles.container}>
      {/* Header */}
      <header style={styles.header}>
        <h1 style={styles.title}>The Restaurant Knows You</h1>
        <p style={styles.subtitle}>They're ready for you — with your consent</p>
      </header>

      {/* Split Screen */}
      <div style={styles.splitContainer}>
        {/* Left: Customer View */}
        <div style={styles.phoneFrame}>
          <div style={styles.phoneHeader}>
            <div style={{ ...styles.avatarCircle, background: palette.accentIndigoDim, color: palette.accentIndigo }}>
              {CUSTOMER.avatar}
            </div>
            <div style={styles.phoneHeaderText}>
              <span style={styles.phoneTitle}>{CUSTOMER.name}</span>
              <span style={styles.phoneSubtitle}>Your view</span>
            </div>
            <div style={styles.phoneStatus}>
              <span style={styles.statusDot} />
              <span style={styles.statusText}>At restaurant</span>
            </div>
          </div>
          <div style={styles.phoneContent}>
            <MessageList messages={customerMessages} accentColor={palette.accentIndigo} />
            {step === "idle" && (
              <div style={styles.inputHint}>
                <span style={styles.hintText}>Tap "Start Demo" to arrive</span>
              </div>
            )}
          </div>
        </div>

        {/* Center Connection */}
        <div style={styles.connectionArea}>
          <MeshConnection
            state={getConnectionState(step)}
            leftLabel="Your Sakhi"
            rightLabel="Restaurant Sakhi"
            statusText={getConnectionStatusText(step)}
          />
        </div>

        {/* Right: Restaurant View */}
        <div style={styles.phoneFrameRestaurant}>
          <div style={styles.phoneHeader}>
            <div style={{ ...styles.avatarCircle, background: palette.accentDim, fontSize: 20 }}>
              {RESTAURANT.avatar}
            </div>
            <div style={styles.phoneHeaderText}>
              <span style={styles.phoneTitle}>{RESTAURANT.name}</span>
              <span style={styles.phoneSubtitle}>Restaurant view</span>
            </div>
            <div style={styles.meshBadge}>
              <span style={styles.meshDot} />
              <span style={styles.meshText}>Mesh Active</span>
            </div>
          </div>
          <div style={styles.phoneContent}>
            {restaurantMessages.length === 0 && step !== "idle" && (
              <div style={styles.waitingState}>
                <span style={styles.waitingDot}>•</span>
                <span style={styles.waitingText}>Waiting for guest...</span>
              </div>
            )}
            <MessageList messages={restaurantMessages} accentColor={palette.accent} />

            {/* Suggested Order Card */}
            {showSuggestion && (
              <div style={styles.suggestionCard}>
                <div style={styles.suggestionHeader}>
                  <span style={styles.suggestionTitle}>Suggested Order</span>
                  <span style={styles.suggestionBadge}>Personalized</span>
                </div>
                {SUGGESTED_ORDER.map((item, i) => (
                  <div key={i} style={styles.orderItem}>
                    <span style={styles.orderIcon}>{item.icon}</span>
                    <div style={styles.orderInfo}>
                      <span style={styles.orderName}>{item.item}</span>
                      {item.modification && (
                        <span style={styles.orderMod}>→ {item.modification}</span>
                      )}
                      <span style={styles.orderReason}>{item.reason}</span>
                    </div>
                  </div>
                ))}
                <div style={styles.suggestionActions}>
                  <button style={styles.confirmButton}>✓ Confirm Order</button>
                  <button style={styles.modifyButton}>Modify</button>
                </div>
                <div style={styles.consentNote}>
                  🔒 Shared with consent via Sakhi Mesh
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Controls */}
      <div style={styles.controls}>
        <button onClick={runDemo} disabled={isRunning} style={isRunning ? styles.buttonDisabled : styles.button}>
          {isRunning ? "In Progress..." : step === "confirmed" ? "Run Again" : "Start Demo"}
        </button>
        {step !== "idle" && (
          <button onClick={resetDemo} style={styles.buttonSecondary}>
            Reset
          </button>
        )}
      </div>

      {/* Explanation */}
      <div style={styles.explanation}>
        <h3 style={styles.explainTitle}>The Magic Moment</h3>
        <div style={styles.comparisonGrid}>
          <div style={styles.comparisonCard}>
            <span style={styles.comparisonHeader}>❌ Without Sakhi</span>
            <ul style={styles.comparisonList}>
              <li>"I'm avoiding dairy this week"</li>
              <li>"Not too spicy please"</li>
              <li>"What's in the dal?"</li>
              <li>Waiter forgets, wrong order arrives</li>
            </ul>
          </div>
          <div style={styles.comparisonCardGood}>
            <span style={styles.comparisonHeader}>✅ With Sakhi</span>
            <ul style={styles.comparisonList}>
              <li>Restaurant already knows</li>
              <li>Personalized suggestion ready</li>
              <li>Adapted for your current state</li>
              <li>You control what's shared</li>
            </ul>
          </div>
        </div>
      </div>
    </main>
  );
}

// Message List Component
function MessageList({ messages, accentColor }: { messages: Message[]; accentColor: string }) {
  return (
    <div style={styles.messageList}>
      {messages.map((msg, i) => (
        <div
          key={i}
          style={{
            ...styles.message,
            ...(msg.sender === "user"
              ? { ...styles.messageUser, background: accentColor }
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
    marginBottom: 40,
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
  splitContainer: {
    display: "flex",
    justifyContent: "center",
    alignItems: "flex-start",
    gap: 24,
    marginBottom: 40,
    flexWrap: "wrap",
  },
  phoneFrame: {
    width: 340,
    minHeight: 520,
    background: palette.cardBg,
    borderRadius: 24,
    border: `1px solid ${palette.divider}`,
    overflow: "hidden",
    display: "flex",
    flexDirection: "column",
  },
  phoneFrameRestaurant: {
    width: 380,
    minHeight: 520,
    background: palette.cardBg,
    borderRadius: 24,
    border: `1px solid ${palette.accent}`,
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
  meshBadge: {
    display: "flex",
    alignItems: "center",
    gap: 6,
    padding: "4px 10px",
    background: palette.accentDim,
    borderRadius: 12,
  },
  meshDot: {
    width: 6,
    height: 6,
    borderRadius: "50%",
    background: palette.accent,
  },
  meshText: {
    fontSize: 11,
    color: palette.accent,
    fontWeight: 500,
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
  // Suggestion Card
  suggestionCard: {
    marginTop: 16,
    padding: 16,
    background: "rgba(245, 158, 11, 0.1)",
    borderRadius: 16,
    border: `1px solid ${palette.accent}`,
  },
  suggestionHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 16,
  },
  suggestionTitle: {
    fontSize: 15,
    fontWeight: 600,
  },
  suggestionBadge: {
    padding: "4px 8px",
    background: palette.accentDim,
    color: palette.accent,
    borderRadius: 8,
    fontSize: 11,
    fontWeight: 500,
  },
  orderItem: {
    display: "flex",
    alignItems: "flex-start",
    gap: 12,
    padding: "10px 0",
    borderBottom: `1px solid ${palette.divider}`,
  },
  orderIcon: {
    fontSize: 24,
    lineHeight: 1,
  },
  orderInfo: {
    flex: 1,
    display: "flex",
    flexDirection: "column",
    gap: 2,
  },
  orderName: {
    fontSize: 14,
    fontWeight: 500,
  },
  orderMod: {
    fontSize: 12,
    color: palette.accent,
  },
  orderReason: {
    fontSize: 11,
    color: palette.muted,
  },
  suggestionActions: {
    display: "flex",
    gap: 8,
    marginTop: 16,
  },
  confirmButton: {
    flex: 1,
    padding: "10px 16px",
    background: palette.accent,
    color: "#000",
    border: "none",
    borderRadius: 8,
    fontSize: 13,
    fontWeight: 600,
    cursor: "pointer",
  },
  modifyButton: {
    padding: "10px 16px",
    background: "transparent",
    color: palette.muted,
    border: `1px solid ${palette.divider}`,
    borderRadius: 8,
    fontSize: 13,
    cursor: "pointer",
  },
  consentNote: {
    marginTop: 12,
    fontSize: 11,
    color: palette.muted,
    textAlign: "center",
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
    color: "#000",
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
