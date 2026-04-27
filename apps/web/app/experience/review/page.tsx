"use client";

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import type React from "react";
import type { Route } from "next";
import { editorialFontFamily, midnightEditorial as palette } from "@/lib/theme/midnightEditorial";

export const dynamic = "force-dynamic";

interface OpenLoop {
  id: string;
  loop_type: string;
  topic: string;
  days_open?: number;
  first_raised_at?: string;
}

interface WhatChanged {
  from: string;
  to: string;
  confidence: number;
  topic_key?: string;
}

interface MorningReview {
  date: string;
  time_of_day: "morning" | "afternoon" | "evening";
  what_changed: WhatChanged | null;
  one_thing: (OpenLoop & { days_open: number }) | null;
  think: OpenLoop[];
  act: OpenLoop[];
  total_open: number;
}

export default function ReviewPage() {
  return (
    <Suspense fallback={null}>
      <ReviewContent />
    </Suspense>
  );
}

function ReviewContent() {
  const router = useRouter();
  const [personId, setPersonId] = useState<string | null>(null);
  const [review, setReview] = useState<MorningReview | null>(null);
  const [loading, setLoading] = useState(true);
  const [dismissedIds, setDismissedIds] = useState<Set<string>>(new Set());
  const [showUpgradeCta, setShowUpgradeCta] = useState(false);
  const paywallCheckedRef = useRef(false);

  useEffect(() => {
    const loadAuth = async () => {
      try {
        const res = await fetch("/api/auth/me", { cache: "no-store" });
        if (res.ok) {
          const data = await res.json();
          setPersonId(data.person_id);
        } else if (res.status === 401) {
          router.replace("/auth/login?redirect=/experience/review" as Route);
        }
      } catch {
        // fall through
      }
    };
    void loadAuth();
  }, [router]);

  useEffect(() => {
    if (!personId || paywallCheckedRef.current) return;
    paywallCheckedRef.current = true;
    const checkPaywall = async () => {
      try {
        const res = await fetch(
          `/api/continuity/paywall-status?person_id=${encodeURIComponent(personId)}`,
          { cache: "no-store" },
        );
        if (res.ok) {
          const data = await res.json();
          setShowUpgradeCta(Boolean(data.show_upgrade_cta));
        }
      } catch {
        // best-effort
      }
    };
    void checkPaywall();
  }, [personId]);

  useEffect(() => {
    if (!personId) return;
    const fetchReview = async () => {
      try {
        const res = await fetch(
          `/api/continuity/morning-review?person_id=${encodeURIComponent(personId)}`,
          { cache: "no-store" },
        );
        if (res.ok) {
          const data = (await res.json()) as MorningReview;
          setReview(data);
        }
      } catch {
        // best-effort
      } finally {
        setLoading(false);
      }
    };
    void fetchReview();
  }, [personId]);

  const handleDismiss = useCallback((loopId: string) => {
    setDismissedIds((prev) => new Set(Array.from(prev).concat(loopId)));
    void fetch(`/api/continuity/open-loops/${loopId}/resolve`, { method: "POST" });
  }, []);

  const greetingWord = (() => {
    const tod = review?.time_of_day;
    if (tod === "morning") return "Good morning";
    if (tod === "afternoon") return "Good afternoon";
    return "Good evening";
  })();

  const formattedDate = review?.date
    ? new Date(review.date + "T00:00:00").toLocaleDateString("en-US", {
        weekday: "long",
        month: "long",
        day: "numeric",
      })
    : "";

  const visibleThink = review?.think.filter((l) => !dismissedIds.has(l.id)) ?? [];
  const visibleAct = review?.act.filter((l) => !dismissedIds.has(l.id)) ?? [];
  const hasContent =
    review?.what_changed ||
    (review?.one_thing && !dismissedIds.has(review.one_thing.id)) ||
    visibleThink.length > 0 ||
    visibleAct.length > 0;

  if (loading) {
    return (
      <div style={styles.container}>
        <p style={{ color: palette.muted, margin: "auto" }}>Loading...</p>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <header style={styles.header}>
        <div>
          <p style={styles.dateLabel}>{formattedDate}</p>
          <h1 style={styles.greeting}>{greetingWord}</h1>
        </div>
        <button
          style={styles.converseButton}
          onClick={() => router.push("/experience/converse" as Route)}
        >
          Start thinking →
        </button>
      </header>

      <main style={styles.main}>
        {showUpgradeCta ? (
          <div style={styles.upgradeCard}>
            <p style={styles.upgradeEyebrow}>Sakhi Pro</p>
            <p style={styles.upgradeHeadline}>Keep access to Morning Review</p>
            <p style={styles.upgradeBody}>
              This view — your open decisions, stance shifts, and one thing to
              confront — is part of Active Context. Free chat continues either way.
            </p>
            <button
              style={styles.upgradeButton}
              onClick={() => router.push("/experience/upgrade" as Route)}
            >
              See upgrade options →
            </button>
          </div>
        ) : null}
        {!hasContent ? (
          <div style={styles.emptyState}>
            <p style={styles.emptyHeading}>Nothing open right now.</p>
            <p style={styles.emptyHint}>
              Open threads and decisions will appear here as you talk with Sakhi.
            </p>
          </div>
        ) : (
          <>
            {review?.what_changed ? (
              <section style={styles.section}>
                <p style={styles.sectionLabel}>What changed</p>
                <div style={styles.whatChangedCard}>
                  <p style={styles.whatChangedLine}>
                    <span style={styles.stanceFrom}>{review.what_changed.from}</span>
                    <span style={styles.stanceArrow}> → </span>
                    <span style={styles.stanceTo}>{review.what_changed.to}</span>
                  </p>
                  {review.what_changed.topic_key ? (
                    <p style={styles.whatChangedTopic}>on {review.what_changed.topic_key.replace(/_/g, " ")}</p>
                  ) : null}
                  <p style={styles.whatChangedSubtext}>
                    Your optimization target has shifted. Notice it before you act.
                  </p>
                </div>
              </section>
            ) : null}

            {review?.one_thing && !dismissedIds.has(review.one_thing.id) ? (
              <section style={styles.section}>
                <p style={styles.sectionLabel}>One thing to confront today</p>
                <div style={styles.oneThingCard}>
                  <p style={styles.oneThingTopic}>{review.one_thing.topic}</p>
                  {review.one_thing.days_open > 0 ? (
                    <p style={styles.oneThingAge}>Open for {review.one_thing.days_open} day{review.one_thing.days_open !== 1 ? "s" : ""}</p>
                  ) : null}
                  <div style={styles.oneThingActions}>
                    <button
                      style={styles.converseOnThis}
                      onClick={() => router.push("/experience/converse" as Route)}
                    >
                      Think it through →
                    </button>
                    <button
                      style={styles.dismissButton}
                      onClick={() => handleDismiss(review.one_thing!.id)}
                    >
                      Resolved
                    </button>
                  </div>
                </div>
              </section>
            ) : null}

            {visibleThink.length > 0 ? (
              <section style={styles.section}>
                <p style={styles.sectionLabel}>Think</p>
                <div style={styles.loopList}>
                  {visibleThink.map((loop) => (
                    <div key={loop.id} style={styles.loopItem}>
                      <span style={styles.loopTopic}>{loop.topic}</span>
                      <button
                        style={styles.loopDismiss}
                        onClick={() => handleDismiss(loop.id)}
                        title="Mark resolved"
                      >
                        ✓
                      </button>
                    </div>
                  ))}
                </div>
              </section>
            ) : null}

            {visibleAct.length > 0 ? (
              <section style={styles.section}>
                <p style={styles.sectionLabel}>Act</p>
                <div style={styles.loopList}>
                  {visibleAct.map((loop) => (
                    <div key={loop.id} style={styles.loopItem}>
                      <span style={styles.loopTopic}>{loop.topic}</span>
                      <button
                        style={styles.loopDismiss}
                        onClick={() => handleDismiss(loop.id)}
                        title="Mark done"
                      >
                        ✓
                      </button>
                    </div>
                  ))}
                </div>
              </section>
            ) : null}
          </>
        )}
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
    padding: "28px 24px 20px",
    borderBottom: `1px solid ${palette.border}`,
    display: "flex",
    alignItems: "flex-end",
    justifyContent: "space-between",
    gap: 16,
  },
  dateLabel: {
    margin: 0,
    fontSize: 12,
    letterSpacing: "0.1em",
    textTransform: "uppercase",
    color: palette.muted,
    marginBottom: 6,
  },
  greeting: {
    margin: 0,
    fontSize: 36,
    fontWeight: 560,
    letterSpacing: "-0.03em",
    lineHeight: 1.06,
    color: palette.fg,
  },
  converseButton: {
    borderRadius: 999,
    border: `1px solid ${palette.border}`,
    background: palette.glassMuted,
    color: palette.fg,
    padding: "10px 18px",
    fontSize: 14,
    fontWeight: 600,
    cursor: "pointer",
    whiteSpace: "nowrap",
    flexShrink: 0,
  },
  main: {
    flex: 1,
    padding: "24px 24px 40px",
    display: "flex",
    flexDirection: "column",
    gap: 28,
    maxWidth: 640,
    width: "100%",
    margin: "0 auto",
  },
  emptyState: {
    margin: "60px auto 0",
    textAlign: "center",
    maxWidth: 480,
  },
  emptyHeading: {
    margin: 0,
    fontSize: 28,
    fontWeight: 520,
    letterSpacing: "-0.02em",
    color: palette.fg,
  },
  emptyHint: {
    margin: "12px auto 0",
    fontSize: 16,
    lineHeight: 1.5,
    color: palette.muted,
  },
  section: {
    display: "flex",
    flexDirection: "column",
    gap: 10,
  },
  sectionLabel: {
    margin: 0,
    fontSize: 11,
    textTransform: "uppercase",
    letterSpacing: "0.12em",
    color: palette.muted,
    fontWeight: 600,
  },
  whatChangedCard: {
    borderRadius: 14,
    border: `1px solid ${palette.accentBorder}`,
    background: palette.accentSoft,
    padding: "16px 18px",
    display: "flex",
    flexDirection: "column",
    gap: 6,
  },
  whatChangedLine: {
    margin: 0,
    fontSize: 22,
    fontWeight: 560,
    letterSpacing: "-0.02em",
    lineHeight: 1.2,
  },
  stanceFrom: {
    color: palette.muted,
    textDecoration: "line-through",
  },
  stanceArrow: {
    color: palette.muted,
  },
  stanceTo: {
    color: palette.accentText,
  },
  whatChangedTopic: {
    margin: 0,
    fontSize: 13,
    color: palette.muted,
  },
  whatChangedSubtext: {
    margin: "4px 0 0",
    fontSize: 14,
    lineHeight: 1.5,
    color: palette.fg,
    opacity: 0.8,
  },
  oneThingCard: {
    borderRadius: 14,
    border: `1px solid ${palette.border}`,
    background: palette.glassStrong,
    padding: "18px 18px 14px",
    display: "flex",
    flexDirection: "column",
    gap: 8,
  },
  oneThingTopic: {
    margin: 0,
    fontSize: 18,
    fontWeight: 520,
    lineHeight: 1.35,
    letterSpacing: "-0.01em",
    color: palette.fg,
  },
  oneThingAge: {
    margin: 0,
    fontSize: 12,
    color: palette.muted,
    letterSpacing: "0.04em",
  },
  oneThingActions: {
    display: "flex",
    gap: 12,
    alignItems: "center",
    marginTop: 4,
  },
  converseOnThis: {
    background: "none",
    border: "none",
    padding: 0,
    fontSize: 14,
    fontWeight: 600,
    color: palette.accent,
    cursor: "pointer",
  },
  dismissButton: {
    background: "none",
    border: "none",
    padding: 0,
    fontSize: 13,
    color: palette.muted,
    cursor: "pointer",
  },
  loopList: {
    display: "flex",
    flexDirection: "column",
    gap: 8,
  },
  loopItem: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 10,
    borderRadius: 10,
    border: `1px solid ${palette.border}`,
    background: palette.glassMuted,
    padding: "11px 14px",
  },
  loopTopic: {
    fontSize: 15,
    lineHeight: 1.4,
    color: palette.fg,
    flex: 1,
  },
  upgradeCard: {
    borderRadius: 14,
    border: `1px solid ${palette.accentBorder}`,
    background: palette.accentSoft,
    padding: "16px 18px",
    display: "flex",
    flexDirection: "column",
    gap: 8,
  },
  upgradeEyebrow: {
    margin: 0,
    fontSize: 11,
    textTransform: "uppercase" as const,
    letterSpacing: "0.12em",
    color: palette.accentText,
    fontWeight: 600,
  },
  upgradeHeadline: {
    margin: 0,
    fontSize: 17,
    fontWeight: 600,
    color: palette.fg,
    letterSpacing: "-0.01em",
  },
  upgradeBody: {
    margin: 0,
    fontSize: 14,
    lineHeight: 1.5,
    color: palette.muted,
  },
  upgradeButton: {
    background: "none",
    border: "none",
    padding: 0,
    fontSize: 14,
    fontWeight: 600,
    color: palette.accentText,
    cursor: "pointer",
    textAlign: "left" as const,
    marginTop: 4,
  },
  loopDismiss: {
    background: "none",
    border: "none",
    color: palette.muted,
    fontSize: 15,
    cursor: "pointer",
    padding: "0 4px",
    flexShrink: 0,
  },
};
