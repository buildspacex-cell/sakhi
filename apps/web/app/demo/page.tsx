"use client";

import Link from "next/link";
import { useState, useEffect } from "react";

/**
 * Sakhi Demo - A Story in Four Acts
 * ----------------------------------
 * This is not a feature showcase. This is a story.
 *
 * The story of how life changes when you have a Sakhi.
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

export default function DemoStory() {
  const [currentSection, setCurrentSection] = useState(0);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    setIsVisible(true);
  }, []);

  return (
    <main style={styles.container}>
      {/* Hero - The Vision */}
      <section style={styles.hero}>
        <div style={{ ...styles.heroContent, opacity: isVisible ? 1 : 0, transform: isVisible ? "translateY(0)" : "translateY(20px)", transition: "all 0.8s ease" }}>
          <p style={styles.heroTagline}>A Story in Four Acts</p>
          <h1 style={styles.heroTitle}>
            What if you never had to <span style={styles.highlight}>chase</span> again?
          </h1>
          <p style={styles.heroSubtitle}>
            Not chase information. Not chase appointments. Not chase recommendations.
            <br />
            What if everything you needed came to you — understood, personalized, ready?
          </p>
        </div>
      </section>

      {/* The Problem - Before/After */}
      <section style={styles.problemSection}>
        <div style={styles.problemContent}>
          <h2 style={styles.problemTitle}>The friction you live with every day</h2>

          <div style={styles.contrastGrid}>
            {/* Row 1 */}
            <div style={styles.contrastRow}>
              <div style={styles.beforeCard}>
                <span style={styles.beforeLabel}>Today</span>
                <p style={styles.beforeText}>
                  <strong>20 minutes on Amazon.</strong> Reading reviews. "Is this one good?"
                  "Will I like this scent?" Decision fatigue for a $15 purchase.
                </p>
              </div>
              <div style={styles.contrastArrow}>→</div>
              <div style={styles.afterCard}>
                <span style={styles.afterLabel}>With Sakhi</span>
                <p style={styles.afterText}>
                  "Find me a car perfume." <strong>Done.</strong> Sakhi already knows you love woody scents.
                </p>
              </div>
            </div>

            {/* Row 2 */}
            <div style={styles.contrastRow}>
              <div style={styles.beforeCard}>
                <span style={styles.beforeLabel}>Today</span>
                <p style={styles.beforeText}>
                  <strong>12 texts to plan dinner with Mom.</strong> "Does Tuesday work?"
                  "Actually Thursday is better." "Wait, I have a thing Thursday."
                </p>
              </div>
              <div style={styles.contrastArrow}>→</div>
              <div style={styles.afterCard}>
                <span style={styles.afterLabel}>With Sakhi</span>
                <p style={styles.afterText}>
                  "Plan something with Mom." Your Sakhi talks to her Sakhi. <strong>Saturday 3pm. Done.</strong>
                </p>
              </div>
            </div>

            {/* Row 3 */}
            <div style={styles.contrastRow}>
              <div style={styles.beforeCard}>
                <span style={styles.beforeLabel}>Today</span>
                <p style={styles.beforeText}>
                  <strong>Explaining yourself. Again.</strong> "I'm avoiding dairy." "Less spicy please."
                  "Do you have anything lighter?" Every. Single. Time.
                </p>
              </div>
              <div style={styles.contrastArrow}>→</div>
              <div style={styles.afterCard}>
                <span style={styles.afterLabel}>With Sakhi</span>
                <p style={styles.afterText}>
                  The restaurant already knows. Your preferences travel with you. <strong>No explaining.</strong>
                </p>
              </div>
            </div>

            {/* Row 4 */}
            <div style={styles.contrastRow}>
              <div style={styles.beforeCard}>
                <span style={styles.beforeLabel}>Today</span>
                <p style={styles.beforeText}>
                  <strong>Googling symptoms.</strong> "Why am I anxious?" Generic articles.
                  No connection to YOUR life, YOUR patterns.
                </p>
              </div>
              <div style={styles.contrastArrow}>→</div>
              <div style={styles.afterCard}>
                <span style={styles.afterLabel}>With Sakhi</span>
                <p style={styles.afterText}>
                  Sakhi connects the dots: late dinner + skipped walk. <strong>Your patterns. Your history.</strong>
                </p>
              </div>
            </div>
          </div>

          <p style={styles.problemSummary}>
            Hours lost. Energy drained. For things that should just... work.
          </p>
        </div>
      </section>

      {/* The Vision */}
      <section style={styles.visionSection}>
        <div style={styles.visionContent}>
          <p style={styles.visionLabel}>The Sakhi Vision</p>
          <h2 style={styles.visionTitle}>
            The world comes through <span style={styles.highlightGold}>your</span> Sakhi.
          </h2>
          <p style={styles.visionText}>
            You don't search. Sakhi finds what matches your taste.
            <br />
            You don't coordinate. Sakhi talks to their Sakhi.
            <br />
            You don't explain. Your preferences travel with you.
            <br />
            You don't wonder. Sakhi connects the patterns.
          </p>
          <p style={styles.visionCta}>
            You live your life. Sakhi handles the friction.
          </p>
        </div>
      </section>

      {/* The Story - Four Acts */}
      <section style={styles.actsSection}>
        <h2 style={styles.actsTitle}>The Story</h2>
        <p style={styles.actsSubtitle}>Four moments that show how life changes with Sakhi</p>

        {/* Act 1 */}
        <div style={styles.actCard}>
          <div style={styles.actHeader}>
            <span style={{ ...styles.actBadge, background: palette.accentDim, color: palette.accent }}>Act 1</span>
            <span style={styles.actTime}>Morning</span>
          </div>
          <h3 style={styles.actTitle}>The Search That Wasn't</h3>
          <div style={styles.actStory}>
            <p style={styles.storyText}>
              Alex's car needs a new air freshener. In the old world, this means 20 minutes on Amazon,
              reading reviews, wondering if "ocean breeze" will be too strong or "vanilla" too sweet.
            </p>
            <p style={styles.storyText}>
              With Sakhi, Alex just says: <span style={styles.userSays}>"Find me a car perfume."</span>
            </p>
            <p style={styles.storyText}>
              Sakhi already knows: Alex loves woody scents (cedar, sandalwood), likes citrus,
              avoids floral. Sakhi browses Amazon, evaluates options against these preferences,
              and returns with one recommendation — the right one.
            </p>
            <div style={styles.storyHighlight}>
              <span style={styles.highlightIcon}>✨</span>
              <p>No searching. No reading reviews. No decision fatigue. Just the right answer.</p>
            </div>
          </div>
          <Link href="/demo/search" style={styles.actLink}>
            <span>Watch Sakhi Find It</span>
            <span style={styles.linkArrow}>→</span>
          </Link>
        </div>

        {/* Act 2 */}
        <div style={styles.actCard}>
          <div style={styles.actHeader}>
            <span style={{ ...styles.actBadge, background: palette.emeraldDim, color: palette.emerald }}>Act 2</span>
            <span style={styles.actTime}>Afternoon</span>
          </div>
          <h3 style={styles.actTitle}>The Coordination That Happened Itself</h3>
          <div style={styles.actStory}>
            <p style={styles.storyText}>
              Alex wants to see Mom this week. In the old world, this means texting,
              waiting for replies, back-and-forth about times, forgetting to account for
              Mom's evening tiredness or Alex's Thursday deadline.
            </p>
            <p style={styles.storyText}>
              With Sakhi, Alex just says: <span style={styles.userSays}>"Plan something with Mom this week."</span>
            </p>
            <p style={styles.storyText}>
              Alex's Sakhi reaches out to Mom's Sakhi. They coordinate in seconds — checking
              calendars, considering that Mom's energy is lower in evenings, knowing they
              both love cooking together. The result: Saturday 3pm, cooking at Mom's.
            </p>
            <div style={styles.storyHighlight}>
              <span style={styles.highlightIcon}>✨</span>
              <p>No texting back-and-forth. No "does this time work?" Both calendars updated. Done.</p>
            </div>
          </div>
          <Link href="/demo/coordination" style={styles.actLink}>
            <span>Watch the Sakhis Coordinate</span>
            <span style={styles.linkArrow}>→</span>
          </Link>
        </div>

        {/* Act 3 */}
        <div style={styles.actCard}>
          <div style={styles.actHeader}>
            <span style={{ ...styles.actBadge, background: palette.amberDim, color: palette.amber }}>Act 3</span>
            <span style={styles.actTime}>Evening</span>
          </div>
          <h3 style={styles.actTitle}>The Restaurant That Already Knew</h3>
          <div style={styles.actStory}>
            <p style={styles.storyText}>
              Alex orders dinner from Annapurna Kitchen. In the old world, Alex would
              browse the menu, try to remember "am I avoiding dairy this week?", wonder
              if the spicy option is too much after a heavy lunch.
            </p>
            <p style={styles.storyText}>
              With Sakhi, the restaurant's Sakhi receives Alex's order coordination — along
              with relevant context: regular customer, avoiding dairy this week, had a heavy
              lunch (needs something lighter), Pitta is slightly elevated (needs cooling foods).
            </p>
            <p style={styles.storyText}>
              The restaurant suggests: Dal Khichdi (Alex's favorite, no ghee today) with
              Cucumber Raita (oat-based for dairy-free, cooling for Pitta).
            </p>
            <div style={styles.storyHighlight}>
              <span style={styles.highlightIcon}>✨</span>
              <p>No menu browsing. No explaining preferences. Food that's right for you TODAY.</p>
            </div>
          </div>
          <Link href="/demo/dine" style={styles.actLink}>
            <span>See the Restaurant's View</span>
            <span style={styles.linkArrow}>→</span>
          </Link>
        </div>

        {/* Act 4 */}
        <div style={styles.actCard}>
          <div style={styles.actHeader}>
            <span style={{ ...styles.actBadge, background: palette.roseDim, color: palette.rose }}>Act 4</span>
            <span style={styles.actTime}>Night</span>
          </div>
          <h3 style={styles.actTitle}>The Understanding</h3>
          <div style={styles.actStory}>
            <p style={styles.storyText}>
              It's late. Alex feels scattered, unfocused, mind racing. In the old world,
              Alex would Google "why do I feel anxious" and get generic advice about stress.
            </p>
            <p style={styles.storyText}>
              With Sakhi, Alex asks: <span style={styles.userSays}>"Why am I feeling scattered?"</span>
            </p>
            <p style={styles.storyText}>
              Sakhi connects the dots: Late dinner at 10pm last night (disrupts Vata),
              skipped the morning walk (usually grounds you), cold drinks yesterday
              (aggravates Vata). Sakhi remembers: "Last time you felt this way, morning
              walks and warm meals helped within 2 days."
            </p>
            <div style={styles.storyHighlight}>
              <span style={styles.highlightIcon}>✨</span>
              <p>Not generic advice. YOUR patterns. YOUR history. What works for YOU.</p>
            </div>
          </div>
          <Link href="/demo/reflect" style={styles.actLink}>
            <span>See How Sakhi Knows</span>
            <span style={styles.linkArrow}>→</span>
          </Link>
        </div>

        {/* Act 5 */}
        <div style={styles.actCard}>
          <div style={styles.actHeader}>
            <span style={{ ...styles.actBadge, background: palette.amberDim, color: palette.amber }}>Act 5</span>
            <span style={styles.actTime}>Tomorrow</span>
          </div>
          <h3 style={styles.actTitle}>The Mission</h3>
          <div style={styles.actStory}>
            <p style={styles.storyText}>
              Alex has a big goal: build a Twitter presence for the side project. In the old world,
              this means endless planning, forgotten intentions, and guilt about not making progress.
            </p>
            <p style={styles.storyText}>
              With Sakhi, Alex just says: <span style={styles.userSays}>"Help me grow my Twitter to 1000 followers."</span>
            </p>
            <p style={styles.storyText}>
              Sakhi breaks this into phases: Week 1-2 is profile optimization and content strategy.
              Week 3-4 focuses on consistent posting. Later phases add engagement and analytics.
              Each day, Alex gets 2-3 specific actions. Weekly reviews adapt the plan.
            </p>
            <div style={styles.storyHighlight}>
              <span style={styles.highlightIcon}>✨</span>
              <p>Big goals become daily actions. Sakhi tracks progress and adapts the plan as you learn.</p>
            </div>
          </div>
          <Link href="/demo/mission" style={styles.actLink}>
            <span>Create a Mission</span>
            <span style={styles.linkArrow}>→</span>
          </Link>
        </div>
      </section>

      {/* The Core Insight */}
      <section style={styles.insightSection}>
        <div style={styles.insightContent}>
          <h2 style={styles.insightTitle}>The Mesh</h2>
          <p style={styles.insightText}>
            This is not just AI assistance. This is a new infrastructure.
          </p>
          <div style={styles.meshDiagram}>
            <div style={styles.meshNode}>
              <span style={styles.meshIcon}>👤</span>
              <span style={styles.meshLabel}>Your Sakhi</span>
            </div>
            <div style={styles.meshConnector}>
              <div style={styles.meshLine} />
            </div>
            <div style={styles.meshNode}>
              <span style={styles.meshIcon}>👩</span>
              <span style={styles.meshLabel}>Mom's Sakhi</span>
            </div>
            <div style={styles.meshSpacer} />
            <div style={styles.meshNode}>
              <span style={styles.meshIcon}>👤</span>
              <span style={styles.meshLabel}>Your Sakhi</span>
            </div>
            <div style={styles.meshConnector}>
              <div style={styles.meshLine} />
            </div>
            <div style={styles.meshNode}>
              <span style={styles.meshIcon}>🏪</span>
              <span style={styles.meshLabel}>Business Sakhi</span>
            </div>
          </div>
          <p style={styles.insightSubtext}>
            Your Sakhi talks to their Sakhi. Your preferences travel with you.
            <br />
            Businesses connect to customers who actually match.
            <br />
            No more cold starts. No more explaining yourself.
          </p>
        </div>
      </section>

      {/* The Close */}
      <section style={styles.closeSection}>
        <div style={styles.closeContent}>
          <h2 style={styles.closeTitle}>Infrastructure for Humans</h2>
          <p style={styles.closeSubtitle}>To reclaim their lives.</p>
          <div style={styles.closePoints}>
            <p><strong>Health</strong> — Sakhi knows your body, your patterns, what works for you</p>
            <p><strong>Joy</strong> — Sakhi finds what you'll love, not what's popular</p>
            <p><strong>Connection</strong> — Sakhi coordinates your relationships without the friction</p>
          </div>
          <p style={styles.closeTagline}>
            You don't chase the world anymore.
            <br />
            The world comes through your Sakhi.
          </p>
        </div>
      </section>

      {/* Footer */}
      <footer style={styles.footer}>
        <p style={styles.footerText}>Focus on what matters. Sakhi handles the rest.</p>
      </footer>
    </main>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    minHeight: "100vh",
    background: palette.bg,
    color: palette.fg,
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  },
  // Hero
  hero: {
    minHeight: "80vh",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: "60px 24px",
    textAlign: "center",
    borderBottom: `1px solid ${palette.divider}`,
  },
  heroContent: {
    maxWidth: 800,
  },
  heroTagline: {
    fontSize: 14,
    color: palette.accent,
    textTransform: "uppercase",
    letterSpacing: "0.1em",
    marginBottom: 24,
  },
  heroTitle: {
    fontSize: 56,
    fontWeight: 700,
    lineHeight: 1.1,
    margin: "0 0 32px 0",
  },
  highlight: {
    color: palette.accent,
  },
  highlightGold: {
    color: palette.amber,
  },
  heroSubtitle: {
    fontSize: 20,
    color: palette.muted,
    lineHeight: 1.6,
    margin: 0,
  },
  // Problem - Contrast Grid
  problemSection: {
    padding: "80px 24px",
    background: palette.cardBg,
  },
  problemContent: {
    maxWidth: 1000,
    margin: "0 auto",
  },
  problemTitle: {
    fontSize: 32,
    fontWeight: 600,
    textAlign: "center",
    marginBottom: 48,
  },
  contrastGrid: {
    display: "flex",
    flexDirection: "column",
    gap: 24,
  },
  contrastRow: {
    display: "grid",
    gridTemplateColumns: "1fr auto 1fr",
    gap: 16,
    alignItems: "center",
  },
  beforeCard: {
    padding: 24,
    background: "rgba(239, 68, 68, 0.08)",
    borderRadius: 12,
    borderLeft: "3px solid #ef4444",
  },
  beforeLabel: {
    display: "block",
    fontSize: 11,
    fontWeight: 600,
    color: "#ef4444",
    textTransform: "uppercase",
    letterSpacing: "0.1em",
    marginBottom: 8,
  },
  beforeText: {
    margin: 0,
    fontSize: 15,
    lineHeight: 1.6,
    color: palette.muted,
  },
  contrastArrow: {
    fontSize: 24,
    color: palette.accent,
    fontWeight: 300,
  },
  afterCard: {
    padding: 24,
    background: palette.accentDim,
    borderRadius: 12,
    borderLeft: `3px solid ${palette.accent}`,
  },
  afterLabel: {
    display: "block",
    fontSize: 11,
    fontWeight: 600,
    color: palette.accent,
    textTransform: "uppercase",
    letterSpacing: "0.1em",
    marginBottom: 8,
  },
  afterText: {
    margin: 0,
    fontSize: 15,
    lineHeight: 1.6,
    color: palette.fg,
  },
  problemSummary: {
    textAlign: "center",
    marginTop: 48,
    fontSize: 20,
    color: palette.muted,
    fontStyle: "italic",
  },
  // Vision
  visionSection: {
    padding: "100px 24px",
    textAlign: "center",
  },
  visionContent: {
    maxWidth: 700,
    margin: "0 auto",
  },
  visionLabel: {
    fontSize: 14,
    color: palette.amber,
    textTransform: "uppercase",
    letterSpacing: "0.1em",
    marginBottom: 16,
  },
  visionTitle: {
    fontSize: 40,
    fontWeight: 700,
    marginBottom: 32,
  },
  visionText: {
    fontSize: 20,
    lineHeight: 2,
    color: palette.muted,
    marginBottom: 32,
  },
  visionCta: {
    fontSize: 24,
    fontWeight: 600,
    color: palette.fg,
    margin: 0,
  },
  // Acts
  actsSection: {
    padding: "80px 24px",
    background: palette.cardBg,
  },
  actsTitle: {
    fontSize: 32,
    fontWeight: 600,
    textAlign: "center",
    marginBottom: 8,
  },
  actsSubtitle: {
    fontSize: 16,
    color: palette.muted,
    textAlign: "center",
    marginBottom: 48,
  },
  actCard: {
    maxWidth: 800,
    margin: "0 auto 48px",
    padding: 32,
    background: palette.bg,
    borderRadius: 16,
    border: `1px solid ${palette.divider}`,
  },
  actHeader: {
    display: "flex",
    alignItems: "center",
    gap: 12,
    marginBottom: 16,
  },
  actBadge: {
    padding: "6px 12px",
    borderRadius: 20,
    fontSize: 12,
    fontWeight: 600,
  },
  actTime: {
    fontSize: 13,
    color: palette.muted,
  },
  actTitle: {
    fontSize: 24,
    fontWeight: 600,
    marginBottom: 20,
  },
  actStory: {
    marginBottom: 24,
  },
  storyText: {
    fontSize: 16,
    lineHeight: 1.8,
    color: palette.muted,
    marginBottom: 16,
  },
  userSays: {
    color: palette.fg,
    fontStyle: "italic",
  },
  storyHighlight: {
    display: "flex",
    alignItems: "flex-start",
    gap: 12,
    padding: 16,
    background: palette.accentDim,
    borderRadius: 8,
    marginTop: 20,
  },
  highlightIcon: {
    fontSize: 20,
  },
  actLink: {
    display: "inline-flex",
    alignItems: "center",
    gap: 8,
    padding: "12px 24px",
    background: palette.accent,
    color: "#fff",
    borderRadius: 8,
    textDecoration: "none",
    fontWeight: 500,
    transition: "opacity 0.2s",
  },
  linkArrow: {
    fontSize: 18,
  },
  // Insight
  insightSection: {
    padding: "100px 24px",
    textAlign: "center",
  },
  insightContent: {
    maxWidth: 800,
    margin: "0 auto",
  },
  insightTitle: {
    fontSize: 40,
    fontWeight: 700,
    marginBottom: 16,
  },
  insightText: {
    fontSize: 20,
    color: palette.muted,
    marginBottom: 48,
  },
  meshDiagram: {
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    gap: 8,
    flexWrap: "wrap",
    marginBottom: 40,
  },
  meshNode: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: 8,
    padding: 20,
    background: palette.cardBg,
    borderRadius: 12,
    minWidth: 100,
  },
  meshIcon: {
    fontSize: 32,
  },
  meshLabel: {
    fontSize: 12,
    color: palette.muted,
  },
  meshConnector: {
    display: "flex",
    alignItems: "center",
  },
  meshLine: {
    width: 40,
    height: 2,
    background: `linear-gradient(90deg, ${palette.accent}, ${palette.accentDim})`,
  },
  meshSpacer: {
    width: 40,
  },
  insightSubtext: {
    fontSize: 18,
    lineHeight: 1.8,
    color: palette.muted,
  },
  // Close
  closeSection: {
    padding: "100px 24px",
    background: palette.cardBg,
    textAlign: "center",
  },
  closeContent: {
    maxWidth: 600,
    margin: "0 auto",
  },
  closeTitle: {
    fontSize: 40,
    fontWeight: 700,
    marginBottom: 8,
  },
  closeSubtitle: {
    fontSize: 24,
    color: palette.amber,
    marginBottom: 40,
  },
  closePoints: {
    textAlign: "left",
    marginBottom: 40,
    lineHeight: 2,
    fontSize: 18,
  },
  closeTagline: {
    fontSize: 24,
    fontWeight: 600,
    lineHeight: 1.6,
  },
  // Footer
  footer: {
    padding: "40px 24px",
    textAlign: "center",
    borderTop: `1px solid ${palette.divider}`,
  },
  footerText: {
    fontSize: 16,
    color: palette.muted,
    margin: 0,
    fontStyle: "italic",
  },
};
