"use client";

import { Suspense } from "react";
import { useRouter } from "next/navigation";
import type React from "react";
import type { Route } from "next";
import { editorialFontFamily, midnightEditorial as palette } from "@/lib/theme/midnightEditorial";

export const dynamic = "force-dynamic";

export default function UpgradePage() {
  return (
    <Suspense fallback={null}>
      <UpgradeContent />
    </Suspense>
  );
}

const FEATURES = [
  {
    label: "Morning Review",
    description: "Start every day knowing exactly what's unresolved and what shifted.",
  },
  {
    label: "What Changed",
    description: "See when your optimization target has quietly drifted — before it costs you.",
  },
  {
    label: "Open Loops Ledger",
    description: "Every decision and commitment you've made, tracked and surfaced automatically.",
  },
  {
    label: "One Thing to Confront",
    description: "Every morning, Sakhi tells you the single most overdue thing to face today.",
  },
];

function UpgradeContent() {
  const router = useRouter();

  return (
    <div style={styles.container}>
      <header style={styles.header}>
        <button
          style={styles.backButton}
          onClick={() => router.back()}
        >
          ← Back
        </button>
        <div style={styles.brand}>Sakhi</div>
      </header>

      <main style={styles.main}>
        <div style={styles.hero}>
          <p style={styles.eyebrow}>Sakhi Pro</p>
          <h1 style={styles.headline}>
            Your open decisions.<br />
            Your thinking shifts.<br />
            Yours to keep.
          </h1>
          <p style={styles.subheadline}>
            Sakhi tracks what stays unresolved across every conversation and shows
            you what changed before you act. That's Active Context — and it's
            what separates good decisions from ones you regret.
          </p>
        </div>

        <div style={styles.featureList}>
          {FEATURES.map((f) => (
            <div key={f.label} style={styles.featureItem}>
              <p style={styles.featureLabel}>{f.label}</p>
              <p style={styles.featureDesc}>{f.description}</p>
            </div>
          ))}
        </div>

        <div style={styles.ctaBlock}>
          <div style={styles.pricingNote}>
            <p style={styles.pricingAmount}>$12 / month</p>
            <p style={styles.pricingDetail}>Cancel anytime. No data locked in.</p>
          </div>
          <button
            style={styles.ctaButton}
            onClick={() => {
              // Payment integration placeholder — will wire Stripe here
              alert("Payment coming soon. We'll notify you when it's ready.");
            }}
          >
            Upgrade to Pro
          </button>
          <button
            style={styles.continueFreeLinkButton}
            onClick={() => router.push("/experience/converse" as Route)}
          >
            Continue with free chat →
          </button>
        </div>
      </main>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    minHeight: "100vh",
    background: `linear-gradient(180deg, ${palette.bgElevated} 0%, ${palette.bg} 18%, ${palette.bg} 100%)`,
    color: palette.fg,
    fontFamily: editorialFontFamily,
    display: "flex",
    flexDirection: "column",
  },
  header: {
    padding: "16px 20px",
    borderBottom: `1px solid ${palette.border}`,
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
  },
  backButton: {
    background: "none",
    border: "none",
    color: palette.muted,
    fontSize: 14,
    cursor: "pointer",
    padding: 0,
  },
  brand: {
    textTransform: "uppercase",
    letterSpacing: "0.18em",
    fontSize: 12,
    color: palette.muted,
  },
  main: {
    flex: 1,
    padding: "40px 24px 60px",
    maxWidth: 540,
    width: "100%",
    margin: "0 auto",
    display: "flex",
    flexDirection: "column",
    gap: 40,
  },
  hero: {
    display: "flex",
    flexDirection: "column",
    gap: 16,
  },
  eyebrow: {
    margin: 0,
    fontSize: 12,
    textTransform: "uppercase",
    letterSpacing: "0.16em",
    color: palette.accentText,
    fontWeight: 600,
  },
  headline: {
    margin: 0,
    fontSize: 40,
    lineHeight: 1.1,
    fontWeight: 560,
    letterSpacing: "-0.03em",
    color: palette.fg,
  },
  subheadline: {
    margin: 0,
    fontSize: 16,
    lineHeight: 1.6,
    color: palette.muted,
  },
  featureList: {
    display: "flex",
    flexDirection: "column",
    gap: 16,
  },
  featureItem: {
    borderRadius: 12,
    border: `1px solid ${palette.border}`,
    background: palette.glassMuted,
    padding: "14px 18px",
    display: "flex",
    flexDirection: "column",
    gap: 4,
  },
  featureLabel: {
    margin: 0,
    fontSize: 15,
    fontWeight: 600,
    color: palette.fg,
  },
  featureDesc: {
    margin: 0,
    fontSize: 14,
    lineHeight: 1.5,
    color: palette.muted,
  },
  ctaBlock: {
    display: "flex",
    flexDirection: "column",
    gap: 14,
    alignItems: "center",
  },
  pricingNote: {
    textAlign: "center",
  },
  pricingAmount: {
    margin: 0,
    fontSize: 28,
    fontWeight: 560,
    letterSpacing: "-0.02em",
    color: palette.fg,
  },
  pricingDetail: {
    margin: "4px 0 0",
    fontSize: 13,
    color: palette.muted,
  },
  ctaButton: {
    width: "100%",
    minHeight: 56,
    borderRadius: 999,
    border: "none",
    background: palette.accent,
    color: palette.accentInk,
    fontSize: 17,
    fontWeight: 700,
    cursor: "pointer",
    letterSpacing: "-0.01em",
  },
  continueFreeLinkButton: {
    background: "none",
    border: "none",
    padding: 0,
    fontSize: 14,
    color: palette.muted,
    cursor: "pointer",
  },
};
