"use client";

import { useState, useCallback } from "react";

/**
 * Personalized Search Demo
 * -------------------------
 * ACT 1: Sakhi Searches AS You
 *
 * Three modes:
 * - Quick Search: Fast product matching (car freshener)
 * - Deep Research: Long-running autonomous research (laptop)
 * - Recurring Tasks: Background automation (Gmail organization)
 */

export const dynamic = "force-dynamic";

type DemoMode = "quick" | "research" | "recurring";

// Demo persona
const USER = {
  name: "Alex",
  handle: "@alex",
  avatar: "A",
};

// User's scent preferences (for quick search)
const SCENT_PREFERENCES = {
  loves: ["Woody", "Cedar", "Sandalwood"],
  likes: ["Citrus", "Fresh", "Clean"],
  avoids: ["Floral", "Sweet", "Vanilla"],
};

// User's tech preferences (for deep research)
const TECH_PREFERENCES = {
  priorities: ["Battery Life", "Build Quality", "Display"],
  uses: ["Coding", "Writing", "Light Gaming"],
  avoids: ["Bulky", "Poor Trackpad", "Noisy Fans"],
  budget: "$1,500 - $2,000",
};

// Research progress steps
const RESEARCH_STEPS = [
  { id: "understanding", label: "Understanding your needs", icon: "🧠", duration: 2000 },
  { id: "gathering", label: "Gathering laptop options", icon: "🔍", duration: 2500 },
  { id: "reading_reviews", label: "Reading expert reviews", icon: "📖", duration: 3000 },
  { id: "user_reviews", label: "Analyzing user feedback", icon: "👥", duration: 2500 },
  { id: "comparing", label: "Comparing specifications", icon: "⚖️", duration: 2000 },
  { id: "matching", label: "Matching to your priorities", icon: "🎯", duration: 2000 },
  { id: "finalizing", label: "Preparing recommendations", icon: "✨", duration: 1500 },
];

// Research findings (laptop)
const RESEARCH_FINDINGS = {
  topPick: {
    name: "MacBook Pro 14\" M3 Pro",
    price: "$1,999",
    image: "💻",
    matchScore: 94,
    verdict: "Best overall for your coding + writing workflow",
    pros: [
      "18hr battery life (your #1 priority)",
      "Exceptional build quality (aluminum unibody)",
      "Best-in-class display (ProMotion 120Hz)",
      "Silent operation — no fan noise during normal use",
    ],
    cons: [
      "At top of budget",
      "Gaming limited to casual titles",
    ],
  },
  alternatives: [
    {
      name: "ThinkPad X1 Carbon Gen 11",
      price: "$1,649",
      matchScore: 87,
      note: "Better keyboard, $350 cheaper, but 12hr battery",
    },
    {
      name: "Dell XPS 15",
      price: "$1,799",
      matchScore: 82,
      note: "Great display, but trackpad not as refined",
    },
  ],
  sourcesAnalyzed: 47,
  reviewsRead: 234,
  timeSpent: "~12 minutes of research, done in background",
};

// Subscription tracking preferences (for recurring tasks)
const SUBSCRIPTION_PREFERENCES = {
  trackFrom: ["Gmail", "Bank Statements", "Credit Cards"],
  categories: ["Entertainment", "Productivity", "Cloud Services"],
  alerts: ["Price increases", "Unused subscriptions", "Renewals"],
  schedule: "1st of every month",
};

// Subscription audit steps
const SUBSCRIPTION_STEPS = [
  { id: "opening", label: "Opening Gmail...", icon: "📬", duration: 1500 },
  { id: "scanning", label: "Scanning for receipts & invoices", icon: "👁️", duration: 2000 },
  { id: "bank", label: "Checking bank statements", icon: "🏦", duration: 2500 },
  { id: "detecting", label: "Detecting recurring charges", icon: "🔄", duration: 2000 },
  { id: "categorizing", label: "Categorizing subscriptions", icon: "📊", duration: 1500 },
  { id: "calculating", label: "Calculating monthly spend", icon: "💰", duration: 2000 },
  { id: "flagging", label: "Flagging unused services", icon: "⚠️", duration: 1500 },
  { id: "complete", label: "Audit complete!", icon: "✨", duration: 1000 },
];

// Subscription audit results
const SUBSCRIPTION_RESULTS = {
  totalMonthly: 847,
  totalAnnual: 10164,
  activeCount: 23,
  unusedCount: 4,
  subscriptions: [
    { name: "Netflix", cost: 22.99, category: "Entertainment", status: "Active" },
    { name: "Spotify Family", cost: 16.99, category: "Entertainment", status: "Active" },
    { name: "ChatGPT Plus", cost: 20.00, category: "Productivity", status: "Active" },
    { name: "Figma", cost: 15.00, category: "Productivity", status: "Active" },
    { name: "AWS", cost: 127.43, category: "Cloud Services", status: "Active" },
    { name: "Adobe CC", cost: 54.99, category: "Productivity", status: "Unused 3mo" },
    { name: "Headspace", cost: 12.99, category: "Wellness", status: "Unused 6mo" },
  ],
  savings: 67.98,
  nextRun: "March 1, 2026",
};

// Demo search results (quick search)
const DEMO_RESULTS = [
  {
    rank: 1,
    title: "Woody Cedar Car Freshener",
    price: 15.99,
    rating: 4.5,
    reviews: 1234,
    matchScore: 0.92,
    matchLevel: "perfect" as const,
    reasons: ["Strong woody cedar notes you love", "No floral ingredients"],
    warnings: [],
    image: "🌲",
  },
  {
    rank: 2,
    title: "Fresh Citrus Vent Clip",
    price: 12.99,
    rating: 4.2,
    reviews: 892,
    matchScore: 0.78,
    matchLevel: "good" as const,
    reasons: ["Citrus notes you like", "Fresh, clean scent"],
    warnings: ["Some users report faint floral undertones"],
    image: "🍋",
  },
  {
    rank: 3,
    title: "Sandalwood Luxury Diffuser",
    price: 28.99,
    rating: 4.8,
    reviews: 2341,
    matchScore: 0.95,
    matchLevel: "perfect" as const,
    reasons: ["Premium sandalwood you love", "Long-lasting"],
    warnings: [],
    isPremium: true,
    image: "✨",
  },
];

// Quick search steps
type QuickDemoStep =
  | "idle"
  | "user_request"
  | "sakhi_analyzing"
  | "checking_preferences"
  | "searching"
  | "matching"
  | "results";

// Research steps
type ResearchDemoStep =
  | "idle"
  | "user_request"
  | "accepted"
  | "researching"
  | "complete";

// Recurring tasks steps (Gmail)
type RecurringDemoStep =
  | "idle"
  | "user_request"
  | "configuring"
  | "scheduled"
  | "running"
  | "complete";

interface Message {
  sender: "user" | "sakhi" | "system";
  content: string;
  thinking?: boolean;
}

// Color palette
const palette = {
  bg: "#0e0f12",
  cardBg: "#1a1b1e",
  fg: "#f4f4f5",
  muted: "#71717a",
  accent: "#6366f1",
  accentDim: "rgba(99, 102, 241, 0.2)",
  success: "#22c55e",
  successDim: "rgba(34, 197, 94, 0.2)",
  warning: "#f59e0b",
  warningDim: "rgba(245, 158, 11, 0.2)",
  divider: "#27272a",
  rose: "#f43f5e",
  roseDim: "rgba(244, 63, 94, 0.2)",
};

export default function SearchDemo() {
  const [mode, setMode] = useState<DemoMode>("quick");
  const [quickStep, setQuickStep] = useState<QuickDemoStep>("idle");
  const [researchStep, setResearchStep] = useState<ResearchDemoStep>("idle");
  const [messages, setMessages] = useState<Message[]>([]);
  const [showResults, setShowResults] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [currentResearchStep, setCurrentResearchStep] = useState(0);
  const [showResearchResults, setShowResearchResults] = useState(false);
  const [recurringStep, setRecurringStep] = useState<RecurringDemoStep>("idle");
  const [currentSubStep, setCurrentSubStep] = useState(0);
  const [showSubResults, setShowSubResults] = useState(false);

  // Quick Search Demo
  const runQuickDemo = useCallback(async () => {
    if (isRunning) return;
    setIsRunning(true);
    setShowResults(false);
    setMessages([]);

    // Step 1: User makes request
    setQuickStep("user_request");
    setMessages([{ sender: "user", content: "Find me a car air freshener under $20" }]);
    await delay(1500);

    // Step 2: Sakhi starts
    setQuickStep("sakhi_analyzing");
    setMessages((prev) => [
      ...prev,
      { sender: "sakhi", content: "Looking for car fresheners...", thinking: true },
    ]);
    await delay(1000);

    // Step 3: Check preferences
    setQuickStep("checking_preferences");
    setMessages((prev) => [
      ...prev,
      {
        sender: "system",
        content: `I know your scent preferences:
❤️ Love: Woody, Cedar, Sandalwood
👍 Like: Citrus, Fresh, Clean
👎 Avoid: Floral, Sweet, Vanilla

Searching with YOUR taste in mind...`,
      },
    ]);
    await delay(2000);

    // Step 4: Searching
    setQuickStep("searching");
    setMessages((prev) => [
      ...prev,
      { sender: "sakhi", content: "Searching Amazon... found 47 products. Matching to your preferences...", thinking: true },
    ]);
    await delay(2000);

    // Step 5: Matching
    setQuickStep("matching");
    await delay(1500);

    // Step 6: Results
    setQuickStep("results");
    setMessages((prev) => [
      ...prev,
      {
        sender: "sakhi",
        content: `Found 3 perfect matches for you!

🏆 #1: Woody Cedar Car Freshener
$15.99 · ⭐ 4.5 (1,234 reviews)
✅ Perfect match: Strong woody notes you love

I also found a premium option worth considering...`,
      },
    ]);
    setShowResults(true);
    await delay(1000);

    setIsRunning(false);
  }, [isRunning]);

  // Deep Research Demo
  const runResearchDemo = useCallback(async () => {
    if (isRunning) return;
    setIsRunning(true);
    setShowResearchResults(false);
    setCurrentResearchStep(0);
    setMessages([]);

    // Step 1: User makes request
    setResearchStep("user_request");
    setMessages([{ sender: "user", content: "Research the best laptop for me" }]);
    await delay(1500);

    // Step 2: Sakhi understands and asks for confirmation
    setMessages((prev) => [
      ...prev,
      {
        sender: "sakhi",
        content: `I'll research laptops matching your profile:

📋 Your priorities: Battery, Build, Display
💼 Your uses: Coding, Writing, Light Gaming
💰 Your budget: $1,500 - $2,000

This is a deep research task. I'll analyze reviews, compare specs, and find your perfect match. This runs in the background — I'll notify you when done.

Should I proceed?`,
      },
    ]);
    await delay(2500);

    // Step 3: User confirms (simulated)
    setMessages((prev) => [
      ...prev,
      { sender: "user", content: "Yes, research it" },
    ]);
    await delay(1000);

    // Step 4: Sakhi accepts and starts
    setResearchStep("accepted");
    setMessages((prev) => [
      ...prev,
      {
        sender: "sakhi",
        content: `Got it! Starting deep research now...

📱 You can close this — I'll work in the background.
🔔 I'll notify you when I find your perfect laptop.`,
      },
    ]);
    await delay(1500);

    // Step 5: Research progress (show each step)
    setResearchStep("researching");
    for (let i = 0; i < RESEARCH_STEPS.length; i++) {
      setCurrentResearchStep(i);
      await delay(RESEARCH_STEPS[i].duration);
    }

    // Step 6: Complete
    setResearchStep("complete");
    setMessages((prev) => [
      ...prev,
      {
        sender: "sakhi",
        content: `🎉 Research complete!

I analyzed 47 sources and 234 user reviews to find your ideal laptop.

My top recommendation: MacBook Pro 14" M3 Pro

This matches your priorities perfectly — exceptional battery life, premium build quality, and a stunning display. Check the detailed findings →`,
      },
    ]);
    setShowResearchResults(true);
    await delay(1000);

    setIsRunning(false);
  }, [isRunning]);

  // Recurring Tasks Demo (Subscription Tracking)
  const runRecurringDemo = useCallback(async () => {
    if (isRunning) return;
    setIsRunning(true);
    setShowSubResults(false);
    setCurrentSubStep(0);
    setMessages([]);

    // Step 1: User makes request
    setRecurringStep("user_request");
    setMessages([{ sender: "user", content: "Track all my subscriptions and what I'm paying" }]);
    await delay(1500);

    // Step 2: Sakhi understands and shows configuration
    setRecurringStep("configuring");
    setMessages((prev) => [
      ...prev,
      {
        sender: "sakhi",
        content: `I'll audit your subscriptions by checking:

📬 Gmail for receipts & invoices
🏦 Bank statements for recurring charges
💳 Credit card transactions

I'll track:
• Monthly/annual costs per service
• Unused subscriptions (no logins)
• Price increases

Run this monthly on the 1st?`,
      },
    ]);
    await delay(3000);

    // Step 3: User confirms recurring
    setMessages((prev) => [
      ...prev,
      { sender: "user", content: "Yes, run it monthly" },
    ]);
    await delay(1000);

    // Step 4: Scheduled
    setRecurringStep("scheduled");
    setMessages((prev) => [
      ...prev,
      {
        sender: "sakhi",
        content: `✅ Monthly subscription audit scheduled!

📅 1st of every month
🔔 I'll send you a spending report

Running first audit now...`,
      },
    ]);
    await delay(1500);

    // Step 5: Running through audit steps
    setRecurringStep("running");
    for (let i = 0; i < SUBSCRIPTION_STEPS.length; i++) {
      setCurrentSubStep(i);
      await delay(SUBSCRIPTION_STEPS[i].duration);
    }

    // Step 6: Complete
    setRecurringStep("complete");
    setMessages((prev) => [
      ...prev,
      {
        sender: "sakhi",
        content: `🎉 Subscription audit complete!

💰 Monthly spend: $847
📊 23 active subscriptions
⚠️ 4 unused (potential savings: $67.98/mo)

I found Adobe CC unused for 3 months and Headspace unused for 6 months. Want me to cancel these?

Next audit: March 1, 2026`,
      },
    ]);
    setShowSubResults(true);
    await delay(1000);

    setIsRunning(false);
  }, [isRunning]);

  const resetDemo = () => {
    setQuickStep("idle");
    setResearchStep("idle");
    setRecurringStep("idle");
    setMessages([]);
    setShowResults(false);
    setShowResearchResults(false);
    setShowSubResults(false);
    setIsRunning(false);
    setCurrentResearchStep(0);
    setCurrentSubStep(0);
  };

  const switchMode = (newMode: DemoMode) => {
    if (isRunning) return;
    setMode(newMode);
    resetDemo();
  };

  const isQuickMode = mode === "quick";
  const isResearchMode = mode === "research";
  const isRecurringMode = mode === "recurring";
  const currentStep = isQuickMode ? quickStep : isResearchMode ? researchStep : recurringStep;

  return (
    <main style={styles.container}>
      {/* Header */}
      <header style={styles.header}>
        <h1 style={styles.title}>Sakhi Searches AS You</h1>
        <p style={styles.subtitle}>
          {isQuickMode
            ? "Not just search results — results matched to YOUR preferences"
            : isResearchMode
              ? "Deep research that runs in the background while you live your life"
              : "Recurring tasks that run automatically on your schedule"
          }
        </p>
      </header>

      {/* Mode Tabs */}
      <div style={styles.tabContainer}>
        <button
          onClick={() => switchMode("quick")}
          style={mode === "quick" ? styles.tabActive : styles.tab}
          disabled={isRunning}
        >
          <span style={styles.tabIcon}>⚡</span>
          Quick Search
        </button>
        <button
          onClick={() => switchMode("research")}
          style={mode === "research" ? styles.tabActive : styles.tab}
          disabled={isRunning}
        >
          <span style={styles.tabIcon}>🔬</span>
          Deep Research
        </button>
        <button
          onClick={() => switchMode("recurring")}
          style={mode === "recurring" ? styles.tabActive : styles.tab}
          disabled={isRunning}
        >
          <span style={styles.tabIcon}>🔄</span>
          Recurring Tasks
        </button>
      </div>

      {/* Main Content */}
      <div style={styles.mainContent}>
        {/* Left: Preferences Panel */}
        <div style={styles.preferencesPanel}>
          {isQuickMode ? (
            // Scent preferences for quick search
            <>
              <h3 style={styles.panelTitle}>Your Scent Profile</h3>
              <p style={styles.panelSubtitle}>What Sakhi knows about you</p>

              <div style={styles.prefSection}>
                <div style={styles.prefHeader}>
                  <span style={styles.prefIcon}>❤️</span>
                  <span style={styles.prefLabel}>Love</span>
                </div>
                <div style={styles.prefTags}>
                  {SCENT_PREFERENCES.loves.map((tag) => (
                    <span key={tag} style={styles.tagLove}>{tag}</span>
                  ))}
                </div>
              </div>

              <div style={styles.prefSection}>
                <div style={styles.prefHeader}>
                  <span style={styles.prefIcon}>👍</span>
                  <span style={styles.prefLabel}>Like</span>
                </div>
                <div style={styles.prefTags}>
                  {SCENT_PREFERENCES.likes.map((tag) => (
                    <span key={tag} style={styles.tagLike}>{tag}</span>
                  ))}
                </div>
              </div>

              <div style={styles.prefSection}>
                <div style={styles.prefHeader}>
                  <span style={styles.prefIcon}>👎</span>
                  <span style={styles.prefLabel}>Avoid</span>
                </div>
                <div style={styles.prefTags}>
                  {SCENT_PREFERENCES.avoids.map((tag) => (
                    <span key={tag} style={styles.tagAvoid}>{tag}</span>
                  ))}
                </div>
              </div>

              <div style={styles.prefNote}>
                <span style={styles.noteIcon}>💡</span>
                <span style={styles.noteText}>Learned from your past choices and conversations</span>
              </div>
            </>
          ) : isResearchMode ? (
            // Tech preferences for deep research
            <>
              <h3 style={styles.panelTitle}>Your Tech Profile</h3>
              <p style={styles.panelSubtitle}>What Sakhi knows about you</p>

              <div style={styles.prefSection}>
                <div style={styles.prefHeader}>
                  <span style={styles.prefIcon}>🎯</span>
                  <span style={styles.prefLabel}>Priorities</span>
                </div>
                <div style={styles.prefTags}>
                  {TECH_PREFERENCES.priorities.map((tag) => (
                    <span key={tag} style={styles.tagLove}>{tag}</span>
                  ))}
                </div>
              </div>

              <div style={styles.prefSection}>
                <div style={styles.prefHeader}>
                  <span style={styles.prefIcon}>💼</span>
                  <span style={styles.prefLabel}>Uses</span>
                </div>
                <div style={styles.prefTags}>
                  {TECH_PREFERENCES.uses.map((tag) => (
                    <span key={tag} style={styles.tagLike}>{tag}</span>
                  ))}
                </div>
              </div>

              <div style={styles.prefSection}>
                <div style={styles.prefHeader}>
                  <span style={styles.prefIcon}>👎</span>
                  <span style={styles.prefLabel}>Avoids</span>
                </div>
                <div style={styles.prefTags}>
                  {TECH_PREFERENCES.avoids.map((tag) => (
                    <span key={tag} style={styles.tagAvoid}>{tag}</span>
                  ))}
                </div>
              </div>

              <div style={styles.prefSection}>
                <div style={styles.prefHeader}>
                  <span style={styles.prefIcon}>💰</span>
                  <span style={styles.prefLabel}>Budget</span>
                </div>
                <span style={styles.budgetTag}>{TECH_PREFERENCES.budget}</span>
              </div>

              <div style={styles.prefNote}>
                <span style={styles.noteIcon}>💡</span>
                <span style={styles.noteText}>Sakhi learns from your past purchases and conversations</span>
              </div>
            </>
          ) : (
            // Subscription tracking preferences
            <>
              <h3 style={styles.panelTitle}>Subscription Tracking</h3>
              <p style={styles.panelSubtitle}>How Sakhi audits your spending</p>

              <div style={styles.prefSection}>
                <div style={styles.prefHeader}>
                  <span style={styles.prefIcon}>📬</span>
                  <span style={styles.prefLabel}>Data Sources</span>
                </div>
                <div style={styles.prefTags}>
                  {SUBSCRIPTION_PREFERENCES.trackFrom.map((tag) => (
                    <span key={tag} style={styles.tagLove}>{tag}</span>
                  ))}
                </div>
              </div>

              <div style={styles.prefSection}>
                <div style={styles.prefHeader}>
                  <span style={styles.prefIcon}>📊</span>
                  <span style={styles.prefLabel}>Categories</span>
                </div>
                <div style={styles.prefTags}>
                  {SUBSCRIPTION_PREFERENCES.categories.map((tag) => (
                    <span key={tag} style={styles.tagLike}>{tag}</span>
                  ))}
                </div>
              </div>

              <div style={styles.prefSection}>
                <div style={styles.prefHeader}>
                  <span style={styles.prefIcon}>🚨</span>
                  <span style={styles.prefLabel}>Alert Me About</span>
                </div>
                <div style={styles.prefTags}>
                  {SUBSCRIPTION_PREFERENCES.alerts.map((tag) => (
                    <span key={tag} style={styles.tagAvoid}>{tag}</span>
                  ))}
                </div>
              </div>

              <div style={styles.prefSection}>
                <div style={styles.prefHeader}>
                  <span style={styles.prefIcon}>📅</span>
                  <span style={styles.prefLabel}>Schedule</span>
                </div>
                <span style={styles.budgetTag}>{SUBSCRIPTION_PREFERENCES.schedule}</span>
              </div>

              <div style={styles.prefNote}>
                <span style={styles.noteIcon}>👁️</span>
                <span style={styles.noteText}>Sakhi uses vision to read emails and bank statements</span>
              </div>
            </>
          )}
        </div>

        {/* Center: Phone */}
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

            {/* Research Progress Indicator */}
            {isResearchMode && researchStep === "researching" && (
              <div style={styles.researchProgress}>
                <div style={styles.progressHeader}>
                  <span style={styles.progressTitle}>🔬 Researching...</span>
                  <span style={styles.progressSubtitle}>Running in background</span>
                </div>
                <div style={styles.progressSteps}>
                  {RESEARCH_STEPS.map((step, i) => (
                    <div
                      key={step.id}
                      style={{
                        ...styles.progressStep,
                        opacity: i <= currentResearchStep ? 1 : 0.3,
                      }}
                    >
                      <span style={{
                        ...styles.progressIcon,
                        ...(i < currentResearchStep ? styles.progressIconDone : {}),
                        ...(i === currentResearchStep ? styles.progressIconActive : {}),
                      }}>
                        {i < currentResearchStep ? "✓" : step.icon}
                      </span>
                      <span style={styles.progressLabel}>{step.label}</span>
                      {i === currentResearchStep && (
                        <span style={styles.progressSpinner}>●</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Subscription Audit Progress Indicator */}
            {isRecurringMode && recurringStep === "running" && (
              <div style={styles.subProgress}>
                <div style={styles.progressHeader}>
                  <span style={styles.progressTitle}>💰 Auditing Subscriptions...</span>
                  <span style={styles.visionBadge}>👁️ Vision Loop</span>
                </div>
                <div style={styles.progressSteps}>
                  {SUBSCRIPTION_STEPS.map((step, i) => (
                    <div
                      key={step.id}
                      style={{
                        ...styles.progressStep,
                        opacity: i <= currentSubStep ? 1 : 0.3,
                      }}
                    >
                      <span style={{
                        ...styles.progressIcon,
                        ...(i < currentSubStep ? styles.progressIconDone : {}),
                        ...(i === currentSubStep ? styles.progressIconActive : {}),
                      }}>
                        {i < currentSubStep ? "✓" : step.icon}
                      </span>
                      <span style={styles.progressLabel}>{step.label}</span>
                      {i === currentSubStep && (
                        <span style={styles.progressSpinner}>●</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {currentStep === "idle" && (
              <div style={styles.inputHint}>
                <span style={styles.hintText}>Tap "Start Demo" to begin</span>
              </div>
            )}
          </div>
        </div>

        {/* Right: Results Panel */}
        <div style={styles.resultsPanel}>
          {isQuickMode ? (
            // Quick search results
            <>
              <h3 style={styles.panelTitle}>Results For You</h3>
              <p style={styles.panelSubtitle}>Ranked by preference match</p>

              {!showResults ? (
                <div style={styles.waitingResults}>
                  <span style={styles.waitingIcon}>{quickStep === "idle" ? "🔍" : "⏳"}</span>
                  <span style={styles.waitingText}>
                    {quickStep === "idle" ? "Waiting to search..." : "Searching..."}
                  </span>
                </div>
              ) : (
                <div style={styles.resultsList}>
                  {DEMO_RESULTS.map((result) => (
                    <div
                      key={result.rank}
                      style={{
                        ...styles.resultCard,
                        ...(result.isPremium ? styles.resultCardPremium : {}),
                      }}
                    >
                      <div style={styles.resultHeader}>
                        <span style={styles.resultImage}>{result.image}</span>
                        <div style={styles.resultInfo}>
                          <span style={styles.resultTitle}>
                            {result.isPremium && <span style={styles.premiumBadge}>💎 Premium</span>}
                            {result.title}
                          </span>
                          <span style={styles.resultMeta}>
                            ${result.price} · ⭐ {result.rating} ({result.reviews.toLocaleString()})
                          </span>
                        </div>
                      </div>

                      <div style={matchBadgeStyle(result.matchLevel)}>
                        {result.matchLevel === "perfect" ? "✅ Perfect Match" : "👍 Good Match"}
                        <span style={styles.matchScore}>{Math.round(result.matchScore * 100)}%</span>
                      </div>

                      <div style={styles.reasons}>
                        {result.reasons.map((reason, i) => (
                          <div key={i} style={styles.reason}>
                            <span style={styles.reasonIcon}>✓</span>
                            <span>{reason}</span>
                          </div>
                        ))}
                        {result.warnings.map((warning, i) => (
                          <div key={i} style={styles.warning}>
                            <span style={styles.warningIcon}>⚠️</span>
                            <span>{warning}</span>
                          </div>
                        ))}
                      </div>

                      {result.isPremium && (
                        <div style={styles.premiumNote}>
                          +$13 over budget but highest match score
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </>
          ) : isResearchMode ? (
            // Deep research results
            <>
              <h3 style={styles.panelTitle}>Research Findings</h3>
              <p style={styles.panelSubtitle}>Deep analysis results</p>

              {!showResearchResults ? (
                <div style={styles.waitingResults}>
                  <span style={styles.waitingIcon}>
                    {researchStep === "idle" ? "🔬" : researchStep === "researching" ? "⏳" : "📋"}
                  </span>
                  <span style={styles.waitingText}>
                    {researchStep === "idle"
                      ? "Waiting to start research..."
                      : researchStep === "researching"
                        ? "Researching in background..."
                        : "Analyzing..."}
                  </span>
                  {researchStep === "researching" && (
                    <div style={styles.researchStats}>
                      <span>Sources: {Math.min(Math.floor((currentResearchStep + 1) * 7), 47)}/47</span>
                      <span>Reviews: {Math.min(Math.floor((currentResearchStep + 1) * 35), 234)}/234</span>
                    </div>
                  )}
                </div>
              ) : (
                <div style={styles.researchResultsList}>
                  {/* Top Pick */}
                  <div style={styles.topPickCard}>
                    <div style={styles.topPickHeader}>
                      <span style={styles.topPickBadge}>🏆 Top Pick</span>
                      <span style={styles.topPickScore}>{RESEARCH_FINDINGS.topPick.matchScore}% match</span>
                    </div>
                    <div style={styles.topPickMain}>
                      <span style={styles.topPickImage}>{RESEARCH_FINDINGS.topPick.image}</span>
                      <div style={styles.topPickInfo}>
                        <span style={styles.topPickName}>{RESEARCH_FINDINGS.topPick.name}</span>
                        <span style={styles.topPickPrice}>{RESEARCH_FINDINGS.topPick.price}</span>
                      </div>
                    </div>
                    <p style={styles.topPickVerdict}>{RESEARCH_FINDINGS.topPick.verdict}</p>

                    <div style={styles.prosConsList}>
                      {RESEARCH_FINDINGS.topPick.pros.map((pro, i) => (
                        <div key={i} style={styles.proItem}>
                          <span style={styles.proIcon}>✓</span>
                          <span>{pro}</span>
                        </div>
                      ))}
                      {RESEARCH_FINDINGS.topPick.cons.map((con, i) => (
                        <div key={i} style={styles.conItem}>
                          <span style={styles.conIcon}>•</span>
                          <span>{con}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Alternatives */}
                  <div style={styles.alternativesSection}>
                    <span style={styles.alternativesTitle}>Alternatives</span>
                    {RESEARCH_FINDINGS.alternatives.map((alt, i) => (
                      <div key={i} style={styles.altCard}>
                        <div style={styles.altHeader}>
                          <span style={styles.altName}>{alt.name}</span>
                          <span style={styles.altScore}>{alt.matchScore}%</span>
                        </div>
                        <div style={styles.altMeta}>
                          <span>{alt.price}</span>
                          <span style={styles.altNote}>{alt.note}</span>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Research Stats */}
                  <div style={styles.researchStatsFinal}>
                    <span>📊 {RESEARCH_FINDINGS.sourcesAnalyzed} sources analyzed</span>
                    <span>💬 {RESEARCH_FINDINGS.reviewsRead} reviews read</span>
                    <span>⏱️ {RESEARCH_FINDINGS.timeSpent}</span>
                  </div>
                </div>
              )}
            </>
          ) : (
            // Subscription audit results
            <>
              <h3 style={styles.panelTitle}>Subscription Report</h3>
              <p style={styles.panelSubtitle}>Your monthly spending breakdown</p>

              {!showSubResults ? (
                <div style={styles.waitingResults}>
                  <span style={styles.waitingIcon}>
                    {recurringStep === "idle" ? "💰" : recurringStep === "running" ? "⏳" : "📋"}
                  </span>
                  <span style={styles.waitingText}>
                    {recurringStep === "idle"
                      ? "Waiting to start..."
                      : recurringStep === "running"
                        ? "Auditing subscriptions..."
                        : "Processing..."}
                  </span>
                  {recurringStep === "running" && (
                    <div style={styles.researchStats}>
                      <span>Step {currentSubStep + 1} of {SUBSCRIPTION_STEPS.length}</span>
                    </div>
                  )}
                </div>
              ) : (
                <div style={styles.subResultsList}>
                  {/* Summary Stats */}
                  <div style={styles.subSummary}>
                    <div style={styles.subStatMain}>
                      <span style={styles.subStatValue}>${SUBSCRIPTION_RESULTS.totalMonthly}</span>
                      <span style={styles.subStatLabel}>Monthly Spend</span>
                    </div>
                    <div style={styles.subStatRow}>
                      <div style={styles.subStatSmall}>
                        <span style={styles.subStatSmallValue}>{SUBSCRIPTION_RESULTS.activeCount}</span>
                        <span style={styles.subStatSmallLabel}>Active</span>
                      </div>
                      <div style={styles.subStatSmall}>
                        <span style={{ ...styles.subStatSmallValue, color: palette.warning }}>{SUBSCRIPTION_RESULTS.unusedCount}</span>
                        <span style={styles.subStatSmallLabel}>Unused</span>
                      </div>
                      <div style={styles.subStatSmall}>
                        <span style={{ ...styles.subStatSmallValue, color: palette.success }}>${SUBSCRIPTION_RESULTS.savings}</span>
                        <span style={styles.subStatSmallLabel}>Savings</span>
                      </div>
                    </div>
                  </div>

                  {/* Subscriptions List */}
                  <div style={styles.subListSection}>
                    <span style={styles.subListTitle}>Subscriptions</span>
                    {SUBSCRIPTION_RESULTS.subscriptions.map((sub, i) => (
                      <div key={i} style={styles.subRow}>
                        <span style={styles.subName}>{sub.name}</span>
                        <span style={styles.subCost}>${sub.cost.toFixed(2)}</span>
                        <span style={{
                          ...styles.subStatus,
                          color: sub.status === "Active" ? palette.success : palette.warning,
                          background: sub.status === "Active" ? palette.successDim : palette.warningDim,
                        }}>{sub.status}</span>
                      </div>
                    ))}
                  </div>

                  {/* Next Run */}
                  <div style={styles.nextRunCard}>
                    <span style={styles.nextRunIcon}>🔄</span>
                    <div style={styles.nextRunInfo}>
                      <span style={styles.nextRunLabel}>Next audit</span>
                      <span style={styles.nextRunTime}>{SUBSCRIPTION_RESULTS.nextRun}</span>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* Controls */}
      <div style={styles.controls}>
        <button
          onClick={isQuickMode ? runQuickDemo : isResearchMode ? runResearchDemo : runRecurringDemo}
          disabled={isRunning}
          style={isRunning ? styles.buttonDisabled : styles.button}
        >
          {isRunning
            ? isQuickMode ? "Searching..." : isResearchMode ? "Researching..." : "Organizing..."
            : currentStep === "results" || currentStep === "complete"
              ? "Run Again"
              : "Start Demo"
          }
        </button>
        {currentStep !== "idle" && (
          <button onClick={resetDemo} style={styles.buttonSecondary}>
            Reset
          </button>
        )}
      </div>

      {/* Explanation */}
      <div style={styles.explanation}>
        <h3 style={styles.explainTitle}>What's Different</h3>
        {isQuickMode ? (
          <div style={styles.comparisonGrid}>
            <div style={styles.comparisonCard}>
              <span style={styles.comparisonHeader}>❌ Regular Search</span>
              <ul style={styles.comparisonList}>
                <li>Returns 47 random products</li>
                <li>You scroll, compare, guess</li>
                <li>20 minutes later...</li>
                <li>Still not sure it's right</li>
              </ul>
            </div>
            <div style={styles.comparisonCardGood}>
              <span style={styles.comparisonHeader}>✅ Sakhi Search</span>
              <ul style={styles.comparisonList}>
                <li>Knows your preferences</li>
                <li>Scores each product FOR you</li>
                <li>Warns about mismatches</li>
                <li>Suggests premium if worth it</li>
              </ul>
            </div>
          </div>
        ) : isResearchMode ? (
          <div style={styles.comparisonGrid}>
            <div style={styles.comparisonCard}>
              <span style={styles.comparisonHeader}>❌ DIY Research</span>
              <ul style={styles.comparisonList}>
                <li>Open 15 browser tabs</li>
                <li>Read conflicting reviews</li>
                <li>Hours of comparison</li>
                <li>Analysis paralysis</li>
              </ul>
            </div>
            <div style={styles.comparisonCardGood}>
              <span style={styles.comparisonHeader}>✅ Sakhi Research</span>
              <ul style={styles.comparisonList}>
                <li>Runs in background</li>
                <li>Reads 234 reviews FOR you</li>
                <li>Matches to YOUR priorities</li>
                <li>Clear recommendation</li>
              </ul>
            </div>
          </div>
        ) : (
          <div style={styles.comparisonGrid}>
            <div style={styles.comparisonCard}>
              <span style={styles.comparisonHeader}>❌ Manual Tracking</span>
              <ul style={styles.comparisonList}>
                <li>Spreadsheets you forget to update</li>
                <li>Miss price increases</li>
                <li>Pay for unused services</li>
                <li>No idea what you actually spend</li>
              </ul>
            </div>
            <div style={styles.comparisonCardGood}>
              <span style={styles.comparisonHeader}>✅ Sakhi Subscription Audit</span>
              <ul style={styles.comparisonList}>
                <li>Auto-detects from email & bank</li>
                <li>Flags unused subscriptions</li>
                <li>Tracks every price change</li>
                <li>Monthly report, zero effort</li>
              </ul>
            </div>
          </div>
        )}
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
const matchBadgeStyle = (level: string): React.CSSProperties => ({
  display: "inline-flex",
  alignItems: "center",
  gap: 8,
  padding: "6px 12px",
  borderRadius: 8,
  fontSize: 13,
  fontWeight: 500,
  background: level === "perfect" ? palette.successDim : palette.accentDim,
  color: level === "perfect" ? palette.success : palette.accent,
  marginBottom: 12,
});

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
    marginBottom: 32,
  },
  title: {
    fontSize: 32,
    fontWeight: 600,
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 16,
    color: palette.muted,
  },
  mainContent: {
    display: "flex",
    justifyContent: "center",
    alignItems: "flex-start",
    gap: 24,
    marginBottom: 40,
  },
  // Preferences Panel
  preferencesPanel: {
    width: 280,
    background: palette.cardBg,
    borderRadius: 16,
    border: `1px solid ${palette.divider}`,
    padding: 20,
  },
  panelTitle: {
    fontSize: 16,
    fontWeight: 600,
    marginBottom: 4,
  },
  panelSubtitle: {
    fontSize: 13,
    color: palette.muted,
    marginBottom: 20,
  },
  prefSection: {
    marginBottom: 16,
  },
  prefHeader: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    marginBottom: 8,
  },
  prefIcon: {
    fontSize: 14,
  },
  prefLabel: {
    fontSize: 13,
    fontWeight: 500,
    color: palette.muted,
  },
  prefTags: {
    display: "flex",
    flexWrap: "wrap",
    gap: 6,
  },
  tagLove: {
    padding: "4px 10px",
    borderRadius: 12,
    fontSize: 12,
    fontWeight: 500,
    background: palette.roseDim,
    color: palette.rose,
  },
  tagLike: {
    padding: "4px 10px",
    borderRadius: 12,
    fontSize: 12,
    fontWeight: 500,
    background: palette.accentDim,
    color: palette.accent,
  },
  tagAvoid: {
    padding: "4px 10px",
    borderRadius: 12,
    fontSize: 12,
    fontWeight: 500,
    background: "rgba(113, 113, 122, 0.2)",
    color: palette.muted,
    textDecoration: "line-through",
  },
  prefNote: {
    marginTop: 20,
    padding: 12,
    background: "rgba(99, 102, 241, 0.1)",
    borderRadius: 8,
    display: "flex",
    alignItems: "flex-start",
    gap: 8,
  },
  noteIcon: {
    fontSize: 14,
  },
  noteText: {
    fontSize: 12,
    color: palette.muted,
    lineHeight: 1.4,
  },
  // Phone Frame
  phoneFrame: {
    width: 340,
    minHeight: 500,
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
  // Messages
  messageList: {
    display: "flex",
    flexDirection: "column",
    gap: 12,
  },
  message: {
    padding: "12px 16px",
    borderRadius: 16,
    maxWidth: "85%",
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
  // Results Panel
  resultsPanel: {
    width: 320,
    background: palette.cardBg,
    borderRadius: 16,
    border: `1px solid ${palette.divider}`,
    padding: 20,
  },
  waitingResults: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    padding: 40,
    gap: 12,
  },
  waitingIcon: {
    fontSize: 32,
    opacity: 0.5,
  },
  waitingText: {
    color: palette.muted,
    fontSize: 14,
  },
  resultsList: {
    display: "flex",
    flexDirection: "column",
    gap: 12,
  },
  resultCard: {
    padding: 14,
    background: "rgba(39, 39, 42, 0.5)",
    borderRadius: 12,
    border: `1px solid ${palette.divider}`,
  },
  resultCardPremium: {
    border: `1px solid ${palette.warning}`,
    background: palette.warningDim,
  },
  resultHeader: {
    display: "flex",
    alignItems: "flex-start",
    gap: 12,
    marginBottom: 10,
  },
  resultImage: {
    fontSize: 28,
    lineHeight: 1,
  },
  resultInfo: {
    flex: 1,
    display: "flex",
    flexDirection: "column",
    gap: 2,
  },
  resultTitle: {
    fontSize: 14,
    fontWeight: 500,
    lineHeight: 1.3,
  },
  premiumBadge: {
    fontSize: 11,
    color: palette.warning,
    display: "block",
    marginBottom: 2,
  },
  resultMeta: {
    fontSize: 12,
    color: palette.muted,
  },
  matchScore: {
    marginLeft: "auto",
    opacity: 0.8,
  },
  reasons: {
    display: "flex",
    flexDirection: "column",
    gap: 4,
  },
  reason: {
    display: "flex",
    alignItems: "flex-start",
    gap: 6,
    fontSize: 12,
    color: palette.muted,
  },
  reasonIcon: {
    color: palette.success,
    fontSize: 10,
    marginTop: 2,
  },
  warning: {
    display: "flex",
    alignItems: "flex-start",
    gap: 6,
    fontSize: 12,
    color: palette.warning,
  },
  warningIcon: {
    fontSize: 10,
    marginTop: 2,
  },
  premiumNote: {
    marginTop: 10,
    padding: "8px 10px",
    background: "rgba(245, 158, 11, 0.1)",
    borderRadius: 6,
    fontSize: 11,
    color: palette.warning,
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
    border: `1px solid rgba(244, 63, 94, 0.2)`,
  },
  comparisonCardGood: {
    padding: 16,
    background: "rgba(34, 197, 94, 0.1)",
    borderRadius: 12,
    border: `1px solid rgba(34, 197, 94, 0.2)`,
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
  // Tab styles
  tabContainer: {
    display: "flex",
    justifyContent: "center",
    gap: 8,
    marginBottom: 32,
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
  // Budget tag
  budgetTag: {
    display: "inline-block",
    padding: "6px 12px",
    background: palette.successDim,
    color: palette.success,
    borderRadius: 8,
    fontSize: 13,
    fontWeight: 500,
  },
  // Research progress styles
  researchProgress: {
    marginTop: 16,
    padding: 16,
    background: "rgba(99, 102, 241, 0.1)",
    borderRadius: 12,
    border: `1px solid rgba(99, 102, 241, 0.2)`,
  },
  progressHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 16,
  },
  progressTitle: {
    fontSize: 14,
    fontWeight: 600,
  },
  progressSubtitle: {
    fontSize: 12,
    color: palette.muted,
  },
  progressSteps: {
    display: "flex",
    flexDirection: "column",
    gap: 8,
  },
  progressStep: {
    display: "flex",
    alignItems: "center",
    gap: 10,
    padding: "6px 0",
    transition: "opacity 0.3s",
  },
  progressIcon: {
    width: 24,
    height: 24,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: 12,
    background: palette.divider,
    borderRadius: "50%",
  },
  progressIconDone: {
    background: palette.successDim,
    color: palette.success,
  },
  progressIconActive: {
    background: palette.accentDim,
    color: palette.accent,
  },
  progressLabel: {
    fontSize: 13,
    flex: 1,
  },
  progressSpinner: {
    color: palette.accent,
    animation: "pulse 1s infinite",
    fontSize: 10,
  },
  // Research stats
  researchStats: {
    display: "flex",
    flexDirection: "column",
    gap: 4,
    marginTop: 12,
    fontSize: 12,
    color: palette.muted,
    textAlign: "center",
  },
  // Research results styles
  researchResultsList: {
    display: "flex",
    flexDirection: "column",
    gap: 16,
  },
  topPickCard: {
    padding: 16,
    background: "rgba(34, 197, 94, 0.1)",
    borderRadius: 12,
    border: `1px solid ${palette.success}`,
  },
  topPickHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 12,
  },
  topPickBadge: {
    fontSize: 13,
    fontWeight: 600,
    color: palette.success,
  },
  topPickScore: {
    fontSize: 12,
    padding: "4px 8px",
    background: palette.successDim,
    color: palette.success,
    borderRadius: 6,
    fontWeight: 500,
  },
  topPickMain: {
    display: "flex",
    alignItems: "center",
    gap: 12,
    marginBottom: 12,
  },
  topPickImage: {
    fontSize: 32,
  },
  topPickInfo: {
    display: "flex",
    flexDirection: "column",
  },
  topPickName: {
    fontSize: 14,
    fontWeight: 600,
    marginBottom: 2,
  },
  topPickPrice: {
    fontSize: 13,
    color: palette.success,
    fontWeight: 500,
  },
  topPickVerdict: {
    fontSize: 12,
    color: palette.muted,
    marginBottom: 12,
    fontStyle: "italic",
  },
  prosConsList: {
    display: "flex",
    flexDirection: "column",
    gap: 4,
  },
  proItem: {
    display: "flex",
    alignItems: "flex-start",
    gap: 6,
    fontSize: 11,
    color: palette.fg,
  },
  proIcon: {
    color: palette.success,
    fontSize: 10,
    marginTop: 2,
  },
  conItem: {
    display: "flex",
    alignItems: "flex-start",
    gap: 6,
    fontSize: 11,
    color: palette.muted,
  },
  conIcon: {
    fontSize: 10,
    marginTop: 2,
  },
  alternativesSection: {
    display: "flex",
    flexDirection: "column",
    gap: 8,
  },
  alternativesTitle: {
    fontSize: 12,
    fontWeight: 500,
    color: palette.muted,
    textTransform: "uppercase",
    letterSpacing: 0.5,
  },
  altCard: {
    padding: 12,
    background: "rgba(39, 39, 42, 0.5)",
    borderRadius: 8,
    border: `1px solid ${palette.divider}`,
  },
  altHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 4,
  },
  altName: {
    fontSize: 13,
    fontWeight: 500,
  },
  altScore: {
    fontSize: 11,
    padding: "2px 6px",
    background: palette.accentDim,
    color: palette.accent,
    borderRadius: 4,
  },
  altMeta: {
    display: "flex",
    flexDirection: "column",
    gap: 2,
    fontSize: 11,
    color: palette.muted,
  },
  altNote: {
    fontStyle: "italic",
  },
  researchStatsFinal: {
    display: "flex",
    flexDirection: "column",
    gap: 4,
    padding: 12,
    background: "rgba(99, 102, 241, 0.1)",
    borderRadius: 8,
    fontSize: 11,
    color: palette.muted,
  },
  // Subscription audit styles
  subProgress: {
    marginTop: 16,
    padding: 16,
    background: "rgba(34, 197, 94, 0.1)",
    borderRadius: 12,
    border: `1px solid rgba(34, 197, 94, 0.2)`,
  },
  visionBadge: {
    fontSize: 11,
    padding: "4px 8px",
    background: "rgba(245, 158, 11, 0.2)",
    color: palette.warning,
    borderRadius: 6,
    fontWeight: 500,
  },
  subResultsList: {
    display: "flex",
    flexDirection: "column",
    gap: 16,
  },
  subSummary: {
    padding: 16,
    background: "rgba(34, 197, 94, 0.1)",
    borderRadius: 12,
    border: `1px solid ${palette.success}`,
  },
  subStatMain: {
    textAlign: "center",
    marginBottom: 12,
    paddingBottom: 12,
    borderBottom: `1px solid rgba(34, 197, 94, 0.2)`,
  },
  subStatValue: {
    fontSize: 32,
    fontWeight: 700,
    color: palette.fg,
    display: "block",
  },
  subStatLabel: {
    fontSize: 12,
    color: palette.muted,
    textTransform: "uppercase",
    letterSpacing: 0.5,
  },
  subStatRow: {
    display: "flex",
    justifyContent: "space-around",
  },
  subStatSmall: {
    textAlign: "center",
  },
  subStatSmallValue: {
    fontSize: 18,
    fontWeight: 600,
    color: palette.fg,
    display: "block",
  },
  subStatSmallLabel: {
    fontSize: 10,
    color: palette.muted,
    textTransform: "uppercase",
  },
  subListSection: {
    display: "flex",
    flexDirection: "column",
    gap: 6,
  },
  subListTitle: {
    fontSize: 12,
    fontWeight: 500,
    color: palette.muted,
    textTransform: "uppercase",
    letterSpacing: 0.5,
    marginBottom: 4,
  },
  subRow: {
    display: "flex",
    alignItems: "center",
    padding: "8px 12px",
    background: "rgba(39, 39, 42, 0.3)",
    borderRadius: 6,
    gap: 8,
  },
  subName: {
    flex: 1,
    fontSize: 13,
    color: palette.fg,
  },
  subCost: {
    fontSize: 13,
    fontWeight: 500,
    color: palette.fg,
  },
  subStatus: {
    fontSize: 10,
    fontWeight: 500,
    padding: "2px 6px",
    borderRadius: 4,
  },
  nextRunCard: {
    display: "flex",
    alignItems: "center",
    gap: 12,
    padding: 12,
    background: palette.accentDim,
    borderRadius: 8,
    border: `1px solid ${palette.accent}`,
  },
  nextRunIcon: {
    fontSize: 20,
  },
  nextRunInfo: {
    display: "flex",
    flexDirection: "column",
    gap: 2,
  },
  nextRunLabel: {
    fontSize: 11,
    color: palette.muted,
  },
  nextRunTime: {
    fontSize: 13,
    fontWeight: 500,
    color: palette.accent,
  },
};
