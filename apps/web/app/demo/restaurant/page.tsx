"use client";

import { useState, useCallback } from "react";

/**
 * Restaurant Sakhi Dashboard Demo
 * --------------------------------
 * ACT 3: Your Sakhi ↔ Restaurant's Sakhi
 *
 * Shows the restaurant's perspective:
 * - Receives coordination requests from customers' Sakhis
 * - Sees customer preferences (shared via mesh)
 * - Suggests personalized orders
 * - Handles the transaction
 */

export const dynamic = "force-dynamic";

// Demo customer profile (what the restaurant's Sakhi receives)
const GUEST_PROFILE = {
  name: "Alex",
  handle: "@alex",
  visitHistory: {
    totalVisits: 8,
    lastVisit: "2 weeks ago",
    favoriteItems: ["Dal Khichdi", "Cucumber Raita", "Masala Chai"],
  },
  preferences: {
    spiceLevel: "Mild to Medium",
    dietary: ["Avoiding dairy this week"],
    portions: "Regular",
    packaging: "Minimal plastic please",
  },
  currentState: {
    pitta: "Slightly elevated",
    recentMeals: "Heavy lunch today",
    mood: "Tired, seeking comfort food",
  },
};

// Demo states
type DemoStep =
  | "idle"
  | "incoming_request"
  | "analyzing_profile"
  | "suggesting_order"
  | "staff_review"
  | "confirmed"
  | "preparing";

interface OrderItem {
  name: string;
  price: number;
  customizations: string[];
  reason: string;
}

// Color palette
const palette = {
  bg: "#0e0f12",
  cardBg: "#1a1b1e",
  fg: "#f4f4f5",
  muted: "#71717a",
  accent: "#f59e0b", // Warm amber for restaurant theme
  accentDim: "rgba(245, 158, 11, 0.15)",
  success: "#22c55e",
  warning: "#eab308",
  divider: "#27272a",
  tagBg: "#27272a",
};

export default function RestaurantDashboard() {
  const [step, setStep] = useState<DemoStep>("idle");
  const [suggestedOrder, setSuggestedOrder] = useState<OrderItem[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [showProfile, setShowProfile] = useState(false);

  const runDemo = useCallback(async () => {
    if (isRunning) return;
    setIsRunning(true);

    // Reset
    setSuggestedOrder([]);
    setShowProfile(false);

    // Step 1: Incoming request
    setStep("incoming_request");
    await delay(1500);

    // Step 2: Profile appears
    setStep("analyzing_profile");
    setShowProfile(true);
    await delay(2000);

    // Step 3: Sakhi suggests order
    setStep("suggesting_order");
    setSuggestedOrder([
      {
        name: "Dal Khichdi",
        price: 180,
        customizations: ["No ghee", "Less spicy"],
        reason: "Their usual favorite - ordered 3 times last month",
      },
      {
        name: "Cucumber Raita",
        price: 60,
        customizations: ["Oat-based (no dairy)"],
        reason: "Cooling for elevated Pitta + dairy-free this week",
      },
    ]);
    await delay(2500);

    // Step 4: Staff sees it
    setStep("staff_review");
    await delay(2000);

    // Step 5: Confirmed
    setStep("confirmed");
    await delay(1500);

    // Step 6: Preparing
    setStep("preparing");
    setIsRunning(false);
  }, [isRunning]);

  const resetDemo = () => {
    setStep("idle");
    setSuggestedOrder([]);
    setShowProfile(false);
    setIsRunning(false);
  };

  const totalPrice = suggestedOrder.reduce((sum, item) => sum + item.price, 0);

  return (
    <main style={styles.container}>
      {/* Header */}
      <header style={styles.header}>
        <div style={styles.restaurantBrand}>
          <span style={styles.restaurantIcon}>🍲</span>
          <div>
            <h1 style={styles.restaurantName}>Annapurna Kitchen</h1>
            <span style={styles.restaurantTagline}>Restaurant Sakhi Dashboard</span>
          </div>
        </div>
        <div style={styles.statusBadge}>
          <span style={styles.statusDot} />
          <span>Mesh Active</span>
        </div>
      </header>

      {/* Main Dashboard */}
      <div style={styles.dashboard}>
        {/* Left Panel - Orders */}
        <div style={styles.ordersPanel}>
          <div style={styles.panelHeader}>
            <h2 style={styles.panelTitle}>Incoming Orders</h2>
            {step !== "idle" && (
              <span style={styles.newBadge}>NEW</span>
            )}
          </div>

          {step === "idle" ? (
            <div style={styles.emptyState}>
              <span style={styles.emptyIcon}>📭</span>
              <p>Waiting for order coordination...</p>
              <button onClick={runDemo} style={styles.demoButton}>
                Simulate Incoming Order
              </button>
            </div>
          ) : (
            <div style={styles.orderCard}>
              <div style={styles.orderHeader}>
                <div style={styles.orderCustomer}>
                  <span style={styles.customerAvatar}>A</span>
                  <div>
                    <span style={styles.customerName}>{GUEST_PROFILE.name}</span>
                    <span style={styles.customerHandle}>{GUEST_PROFILE.handle}</span>
                  </div>
                </div>
                <div style={styles.orderMeta}>
                  <span style={styles.visitCount}>{GUEST_PROFILE.visitHistory.totalVisits} visits</span>
                  <span style={styles.regularBadge}>Regular</span>
                </div>
              </div>

              {/* Status indicator */}
              <div style={styles.orderStatus}>
                <span style={styles.statusIcon}>
                  {step === "incoming_request" && "📥"}
                  {step === "analyzing_profile" && "🔍"}
                  {step === "suggesting_order" && "💡"}
                  {step === "staff_review" && "👀"}
                  {step === "confirmed" && "✓"}
                  {step === "preparing" && "🍳"}
                </span>
                <span style={styles.statusText}>
                  {step === "incoming_request" && "Order coordination incoming..."}
                  {step === "analyzing_profile" && "Analyzing guest preferences..."}
                  {step === "suggesting_order" && "Sakhi suggesting order..."}
                  {step === "staff_review" && "Ready for staff review"}
                  {step === "confirmed" && "Order confirmed!"}
                  {step === "preparing" && "Preparing order • 35 mins"}
                </span>
              </div>

              {/* Suggested Order */}
              {suggestedOrder.length > 0 && (
                <div style={styles.suggestedOrder}>
                  <h4 style={styles.suggestedTitle}>Sakhi Suggested Order</h4>
                  {suggestedOrder.map((item, i) => (
                    <div key={i} style={styles.orderItem}>
                      <div style={styles.itemHeader}>
                        <span style={styles.itemName}>{item.name}</span>
                        <span style={styles.itemPrice}>₹{item.price}</span>
                      </div>
                      <div style={styles.itemCustomizations}>
                        {item.customizations.map((c, j) => (
                          <span key={j} style={styles.customTag}>{c}</span>
                        ))}
                      </div>
                      <p style={styles.itemReason}>{item.reason}</p>
                    </div>
                  ))}
                  <div style={styles.orderTotal}>
                    <span>Total</span>
                    <span style={styles.totalPrice}>₹{totalPrice}</span>
                  </div>
                </div>
              )}

              {/* Action buttons */}
              {step === "staff_review" && (
                <div style={styles.orderActions}>
                  <button
                    onClick={() => setStep("confirmed")}
                    style={styles.confirmButton}
                  >
                    Confirm & Prepare
                  </button>
                  <button style={styles.modifyButton}>
                    Modify Order
                  </button>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Right Panel - Guest Profile */}
        <div style={styles.profilePanel}>
          <div style={styles.panelHeader}>
            <h2 style={styles.panelTitle}>Guest Profile</h2>
            <span style={styles.meshBadge}>via Mesh</span>
          </div>

          {showProfile ? (
            <div style={styles.profileCard}>
              {/* Visit History */}
              <div style={styles.profileSection}>
                <h4 style={styles.sectionTitle}>Visit History</h4>
                <div style={styles.statRow}>
                  <span style={styles.statLabel}>Total visits</span>
                  <span style={styles.statValue}>{GUEST_PROFILE.visitHistory.totalVisits}</span>
                </div>
                <div style={styles.statRow}>
                  <span style={styles.statLabel}>Last visit</span>
                  <span style={styles.statValue}>{GUEST_PROFILE.visitHistory.lastVisit}</span>
                </div>
                <div style={styles.favoritesSection}>
                  <span style={styles.statLabel}>Favorites</span>
                  <div style={styles.tagContainer}>
                    {GUEST_PROFILE.visitHistory.favoriteItems.map((item, i) => (
                      <span key={i} style={styles.favoriteTag}>{item}</span>
                    ))}
                  </div>
                </div>
              </div>

              {/* Preferences */}
              <div style={styles.profileSection}>
                <h4 style={styles.sectionTitle}>Preferences</h4>
                <div style={styles.prefGrid}>
                  <div style={styles.prefItem}>
                    <span style={styles.prefIcon}>🌶️</span>
                    <span style={styles.prefLabel}>Spice</span>
                    <span style={styles.prefValue}>{GUEST_PROFILE.preferences.spiceLevel}</span>
                  </div>
                  <div style={styles.prefItem}>
                    <span style={styles.prefIcon}>🥛</span>
                    <span style={styles.prefLabel}>Dietary</span>
                    <span style={styles.prefValue}>{GUEST_PROFILE.preferences.dietary[0]}</span>
                  </div>
                </div>
              </div>

              {/* Current State (Ayurvedic) */}
              <div style={styles.profileSection}>
                <h4 style={styles.sectionTitle}>Current State</h4>
                <div style={styles.stateNote}>
                  <span style={styles.stateIcon}>🔥</span>
                  <div>
                    <span style={styles.stateLabel}>Pitta {GUEST_PROFILE.currentState.pitta}</span>
                    <span style={styles.stateHint}>Needs cooling balance</span>
                  </div>
                </div>
                <div style={styles.stateNote}>
                  <span style={styles.stateIcon}>🍽️</span>
                  <div>
                    <span style={styles.stateLabel}>{GUEST_PROFILE.currentState.recentMeals}</span>
                    <span style={styles.stateHint}>Lighter dinner recommended</span>
                  </div>
                </div>
              </div>

              {/* Privacy Note */}
              <div style={styles.privacyNote}>
                <span style={styles.privacyIcon}>🔒</span>
                <span>Shared with consent via Sakhi Mesh</span>
              </div>
            </div>
          ) : (
            <div style={styles.profileEmpty}>
              <span style={styles.emptyIcon}>👤</span>
              <p>Guest profile will appear when order coordination starts</p>
            </div>
          )}
        </div>
      </div>

      {/* Controls */}
      <div style={styles.controls}>
        {step !== "idle" && (
          <button onClick={resetDemo} style={styles.resetButton}>
            Reset Demo
          </button>
        )}
      </div>

      {/* Explanation */}
      <div style={styles.explanation}>
        <h3 style={styles.explainTitle}>Business Sakhi in Action</h3>
        <p style={styles.explainText}>
          This shows the restaurant's view during Sakhi-to-Sakhi coordination:
        </p>
        <ul style={styles.explainList}>
          <li><strong>Guest profile arrives via mesh</strong> — preferences shared with consent</li>
          <li><strong>Sakhi suggests personalized order</strong> — based on history + current state</li>
          <li><strong>Staff can review and confirm</strong> — human stays in control</li>
          <li><strong>Order includes context</strong> — "no dairy this week", "Pitta elevated"</li>
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
    padding: "24px",
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 32,
    paddingBottom: 24,
    borderBottom: `1px solid ${palette.divider}`,
  },
  restaurantBrand: {
    display: "flex",
    alignItems: "center",
    gap: 16,
  },
  restaurantIcon: {
    fontSize: 40,
  },
  restaurantName: {
    fontSize: 24,
    fontWeight: 700,
    margin: 0,
  },
  restaurantTagline: {
    fontSize: 14,
    color: palette.muted,
  },
  statusBadge: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    padding: "8px 16px",
    background: palette.accentDim,
    borderRadius: 20,
    fontSize: 13,
    color: palette.accent,
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: "50%",
    background: palette.success,
  },
  dashboard: {
    display: "grid",
    gridTemplateColumns: "1fr 380px",
    gap: 24,
    marginBottom: 32,
  },
  ordersPanel: {
    background: palette.cardBg,
    borderRadius: 16,
    border: `1px solid ${palette.divider}`,
    overflow: "hidden",
  },
  profilePanel: {
    background: palette.cardBg,
    borderRadius: 16,
    border: `1px solid ${palette.divider}`,
    overflow: "hidden",
  },
  panelHeader: {
    padding: "16px 20px",
    borderBottom: `1px solid ${palette.divider}`,
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
  },
  panelTitle: {
    margin: 0,
    fontSize: 16,
    fontWeight: 600,
  },
  newBadge: {
    padding: "4px 10px",
    background: palette.accent,
    color: "#000",
    borderRadius: 12,
    fontSize: 11,
    fontWeight: 600,
  },
  meshBadge: {
    padding: "4px 10px",
    background: palette.accentDim,
    color: palette.accent,
    borderRadius: 12,
    fontSize: 11,
  },
  emptyState: {
    padding: 60,
    textAlign: "center",
    color: palette.muted,
  },
  emptyIcon: {
    fontSize: 48,
    display: "block",
    marginBottom: 16,
  },
  demoButton: {
    marginTop: 24,
    padding: "14px 28px",
    background: palette.accent,
    color: "#000",
    border: "none",
    borderRadius: 12,
    fontSize: 14,
    fontWeight: 600,
    cursor: "pointer",
  },
  orderCard: {
    padding: 20,
  },
  orderHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "flex-start",
    marginBottom: 16,
  },
  orderCustomer: {
    display: "flex",
    alignItems: "center",
    gap: 12,
  },
  customerAvatar: {
    width: 44,
    height: 44,
    borderRadius: "50%",
    background: palette.accentDim,
    color: palette.accent,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontWeight: 600,
    fontSize: 18,
  },
  customerName: {
    display: "block",
    fontWeight: 600,
    fontSize: 16,
  },
  customerHandle: {
    display: "block",
    fontSize: 13,
    color: palette.muted,
  },
  orderMeta: {
    display: "flex",
    alignItems: "center",
    gap: 8,
  },
  visitCount: {
    fontSize: 13,
    color: palette.muted,
  },
  regularBadge: {
    padding: "4px 10px",
    background: palette.tagBg,
    borderRadius: 12,
    fontSize: 11,
    color: palette.success,
  },
  orderStatus: {
    display: "flex",
    alignItems: "center",
    gap: 12,
    padding: "12px 16px",
    background: palette.accentDim,
    borderRadius: 12,
    marginBottom: 20,
  },
  statusIcon: {
    fontSize: 20,
  },
  statusText: {
    fontSize: 14,
    color: palette.fg,
  },
  suggestedOrder: {
    background: palette.bg,
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
  },
  suggestedTitle: {
    margin: "0 0 16px 0",
    fontSize: 14,
    fontWeight: 600,
    color: palette.accent,
  },
  orderItem: {
    marginBottom: 16,
    paddingBottom: 16,
    borderBottom: `1px solid ${palette.divider}`,
  },
  itemHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 8,
  },
  itemName: {
    fontWeight: 600,
    fontSize: 15,
  },
  itemPrice: {
    fontWeight: 600,
    color: palette.accent,
  },
  itemCustomizations: {
    display: "flex",
    gap: 8,
    marginBottom: 8,
    flexWrap: "wrap",
  },
  customTag: {
    padding: "4px 10px",
    background: palette.tagBg,
    borderRadius: 12,
    fontSize: 12,
    color: palette.muted,
  },
  itemReason: {
    margin: 0,
    fontSize: 13,
    color: palette.muted,
    fontStyle: "italic",
  },
  orderTotal: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    paddingTop: 16,
    fontWeight: 600,
  },
  totalPrice: {
    fontSize: 18,
    color: palette.accent,
  },
  orderActions: {
    display: "flex",
    gap: 12,
  },
  confirmButton: {
    flex: 1,
    padding: "14px 24px",
    background: palette.success,
    color: "#fff",
    border: "none",
    borderRadius: 12,
    fontSize: 14,
    fontWeight: 600,
    cursor: "pointer",
  },
  modifyButton: {
    padding: "14px 24px",
    background: "transparent",
    color: palette.muted,
    border: `1px solid ${palette.divider}`,
    borderRadius: 12,
    fontSize: 14,
    cursor: "pointer",
  },
  profileCard: {
    padding: 20,
  },
  profileSection: {
    marginBottom: 24,
    paddingBottom: 20,
    borderBottom: `1px solid ${palette.divider}`,
  },
  sectionTitle: {
    margin: "0 0 12px 0",
    fontSize: 13,
    fontWeight: 600,
    color: palette.muted,
    textTransform: "uppercase",
    letterSpacing: "0.05em",
  },
  statRow: {
    display: "flex",
    justifyContent: "space-between",
    marginBottom: 8,
  },
  statLabel: {
    color: palette.muted,
    fontSize: 14,
  },
  statValue: {
    fontWeight: 500,
  },
  favoritesSection: {
    marginTop: 12,
  },
  tagContainer: {
    display: "flex",
    flexWrap: "wrap",
    gap: 8,
    marginTop: 8,
  },
  favoriteTag: {
    padding: "6px 12px",
    background: palette.accentDim,
    color: palette.accent,
    borderRadius: 16,
    fontSize: 12,
  },
  prefGrid: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: 12,
  },
  prefItem: {
    padding: 12,
    background: palette.bg,
    borderRadius: 12,
    display: "flex",
    flexDirection: "column",
    gap: 4,
  },
  prefIcon: {
    fontSize: 20,
  },
  prefLabel: {
    fontSize: 11,
    color: palette.muted,
    textTransform: "uppercase",
  },
  prefValue: {
    fontSize: 13,
    fontWeight: 500,
  },
  stateNote: {
    display: "flex",
    alignItems: "flex-start",
    gap: 12,
    padding: 12,
    background: palette.bg,
    borderRadius: 12,
    marginBottom: 8,
  },
  stateIcon: {
    fontSize: 20,
  },
  stateLabel: {
    display: "block",
    fontSize: 14,
    fontWeight: 500,
  },
  stateHint: {
    display: "block",
    fontSize: 12,
    color: palette.muted,
  },
  privacyNote: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    padding: 12,
    background: palette.accentDim,
    borderRadius: 12,
    fontSize: 12,
    color: palette.muted,
  },
  privacyIcon: {
    fontSize: 16,
  },
  profileEmpty: {
    padding: 60,
    textAlign: "center",
    color: palette.muted,
  },
  controls: {
    display: "flex",
    justifyContent: "center",
    marginBottom: 32,
  },
  resetButton: {
    padding: "12px 24px",
    background: "transparent",
    color: palette.muted,
    border: `1px solid ${palette.divider}`,
    borderRadius: 12,
    fontSize: 14,
    cursor: "pointer",
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
    margin: "0 0 12px 0",
    fontSize: 16,
    fontWeight: 600,
  },
  explainText: {
    margin: "0 0 16px 0",
    color: palette.muted,
    lineHeight: 1.6,
  },
  explainList: {
    margin: 0,
    paddingLeft: 20,
    lineHeight: 1.8,
    color: palette.muted,
  },
};
