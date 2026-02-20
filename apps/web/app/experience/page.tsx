"use client";

import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import type React from "react";
import type { Route } from "next";

export const dynamic = "force-dynamic";

const palette = {
  bg: "#0a0a0a",
  fg: "#f4f4f5",
  muted: "#71717a",
  mutedLight: "#a1a1aa",
  accent: "#6366f1",
  cardBg: "#18191d",
  border: "#27272a",
  dimText: "#52525b",
};

const FADE_DURATION_MS = 400;

// =============================================================================
// INTRO CARDS DATA (matches mobile exactly)
// =============================================================================

const INTRO_CARDS = [
  {
    id: 1,
    title: "Clarity is your natural state.",
    body: "But friction builds.\nInside you, and around you.",
    accent: "The way your body feels, your thoughts, emotions, decisions, and distractions.",
  },
  {
    id: 2,
    title: "Sakhi helps you see and release friction.",
    body: "Within you: the patterns clouding your clarity.\n\nAround you: the tasks and decisions pulling at your attention.",
    accent: "Less friction. More you.",
  },
  {
    id: 3,
    title: "Just talk.",
    body: "About your day. Or a decision. Or something you want off your plate.\n\nThink out loud.\n\nOr tell me what you don\u2019t want to deal with.",
    accent: "You\u2019ll start to feel the difference.",
  },
];

// =============================================================================
// TYPES
// =============================================================================

interface AuthUser {
  person_id: string;
  email: string;
  full_name: string | null;
  onboarding_completed: boolean;
}

// =============================================================================
// MAIN COMPONENT
// =============================================================================

export default function ExperienceGate() {
  return (
    <Suspense fallback={null}>
      <ExperienceGateContent />
    </Suspense>
  );
}

function ExperienceGateContent() {
  const router = useRouter();
  const [isFading, setIsFading] = useState(false);
  const [isHoveringBegin, setIsHoveringBegin] = useState(false);
  const [authUser, setAuthUser] = useState<AuthUser | null>(null);
  const [authChecked, setAuthChecked] = useState(false);
  const hasNavigated = useRef(false);

  // Intro modal state
  const [showIntro, setShowIntro] = useState(false);
  const [currentCard, setCurrentCard] = useState(0);
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  // Fetch authenticated user on mount (with timeout so page doesn't hang)
  useEffect(() => {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 3000);

    const fetchUser = async () => {
      try {
        const res = await fetch("/api/auth/me", { signal: controller.signal });
        if (res.ok) {
          const data = await res.json();
          setAuthUser(data);
        }
      } catch (err) {
        // Silently handle auth errors (user not logged in, timeout, etc.)
        if ((err as Error).name !== "AbortError") {
          console.error("Error fetching auth user:", err);
        }
      } finally {
        setAuthChecked(true);
        clearTimeout(timeout);
      }
    };

    fetchUser();

    return () => {
      clearTimeout(timeout);
      controller.abort();
    };
  }, [router]);

  const nextPath = useMemo(() => {
    if (authUser) {
      // Authenticated + onboarding done → go to conversation
      if (authUser.onboarding_completed) {
        return `/experience/converse?user=${encodeURIComponent(authUser.person_id)}`;
      }
      // Authenticated + onboarding not done → go to onboarding
      return `/experience/onboarding?user=${encodeURIComponent(authUser.person_id)}`;
    }
    // Not authenticated → login first, then redirect to onboarding
    return `/auth/login?redirect=${encodeURIComponent("/experience/onboarding")}`;
  }, [authUser]);

  // Auto-redirect onboarded users — skip the welcome screen entirely
  useEffect(() => {
    if (!authChecked || hasNavigated.current) return;
    if (authUser?.onboarding_completed) {
      hasNavigated.current = true;
      setIsFading(true);
      window.setTimeout(() => {
        router.replace(nextPath as Route);
      }, FADE_DURATION_MS);
    }
  }, [authChecked, authUser, nextPath, router]);

  const handleBegin = useCallback(() => {
    if (hasNavigated.current || !authChecked) return;
    hasNavigated.current = true;
    setIsFading(true);
    window.setTimeout(() => {
      router.replace(nextPath as Route);
    }, FADE_DURATION_MS);
  }, [nextPath, router, authChecked]);

  const handleCloseIntro = useCallback(() => {
    setShowIntro(false);
    setCurrentCard(0);
  }, []);

  const handleScroll = useCallback(() => {
    const el = scrollContainerRef.current;
    if (!el) return;
    const index = Math.round(el.scrollLeft / el.clientWidth);
    setCurrentCard(index);
  }, []);

  const isLastCard = currentCard === INTRO_CARDS.length - 1;

  // Show welcome screen even while auth loads (just hide the buttons briefly)
  // This prevents the page from appearing stuck

  return (
    <>
      <main
        style={{ ...containerStyle, opacity: isFading ? 0 : 1 }}
      >
        <div style={contentStyle}>
          {/* Centered text */}
          <div style={textContainerStyle}>
            <h1 style={headlineStyle}>
              This is a quiet space to unload your mind.
            </h1>
            <p style={subheadlineStyle}>
              You can talk, or hand something off.
            </p>
          </div>

          {/* BEGIN button */}
          <button
            style={{
              ...beginButtonStyle,
              color: !authChecked
                ? palette.dimText
                : isHoveringBegin
                  ? palette.fg
                  : palette.muted,
              cursor: authChecked ? "pointer" : "default",
            }}
            onClick={handleBegin}
            onMouseEnter={() => setIsHoveringBegin(true)}
            onMouseLeave={() => setIsHoveringBegin(false)}
          >
            BEGIN
          </button>

          {/* What is Sakhi link */}
          <button
            style={learnMoreStyle}
            onClick={() => setShowIntro(true)}
          >
            What is Sakhi?
          </button>
        </div>
      </main>

      {/* Intro Modal */}
      {showIntro && (
        <div style={modalOverlayStyle}>
          <div style={modalContainerStyle}>
            {/* Close button */}
            <button style={closeButtonStyle} onClick={handleCloseIntro}>
              &#10005;
            </button>

            {/* Swipeable cards */}
            <div
              ref={scrollContainerRef}
              style={cardsScrollStyle}
              onScroll={handleScroll}
            >
              {INTRO_CARDS.map((card) => (
                <div key={card.id} style={cardOuterStyle}>
                  <div style={cardInnerStyle}>
                    <h2 style={cardTitleStyle}>{card.title}</h2>
                    <p style={cardBodyStyle}>{card.body}</p>
                    <p style={cardAccentStyle}>{card.accent}</p>
                  </div>
                </div>
              ))}
            </div>

            {/* Pagination dots */}
            <div style={paginationStyle}>
              {INTRO_CARDS.map((_, index) => (
                <div
                  key={index}
                  style={{
                    ...dotStyle,
                    ...(currentCard === index ? dotActiveStyle : {}),
                  }}
                />
              ))}
            </div>

            {/* Reassurance text - only on last card */}
            {isLastCard && (
              <p style={reassuranceStyle}>We&apos;ll start small.</p>
            )}

            {/* Got it button */}
            <button
              style={{
                ...gotItButtonStyle,
                ...(!isLastCard ? gotItButtonDisabledStyle : {}),
              }}
              onClick={handleCloseIntro}
              disabled={!isLastCard}
            >
              <span
                style={{
                  ...gotItTextStyle,
                  ...(!isLastCard ? gotItTextDisabledStyle : {}),
                }}
              >
                {isLastCard ? "Got it" : "Swipe to continue"}
              </span>
            </button>
          </div>
        </div>
      )}
    </>
  );
}

// =============================================================================
// STYLES
// =============================================================================

const fontFamily =
  '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Inter, Helvetica, Arial, sans-serif';

const containerStyle: React.CSSProperties = {
  minHeight: "100vh",
  background: palette.bg,
  color: palette.fg,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  padding: "48px 40px",
  fontFamily,
  transition: `opacity ${FADE_DURATION_MS}ms ease`,
};

const contentStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  alignItems: "center",
  justifyContent: "center",
};

const textContainerStyle: React.CSSProperties = {
  textAlign: "center",
  marginBottom: "56px",
};

const headlineStyle: React.CSSProperties = {
  fontSize: "24px",
  fontWeight: 400,
  color: "#ffffff",
  textAlign: "center",
  lineHeight: "34px",
  marginBottom: "20px",
  margin: "0 0 20px 0",
};

const subheadlineStyle: React.CSSProperties = {
  fontSize: "16px",
  fontWeight: 400,
  color: palette.muted,
  textAlign: "center",
  lineHeight: "24px",
  margin: 0,
};

const beginButtonStyle: React.CSSProperties = {
  padding: "16px 32px",
  marginBottom: "32px",
  fontSize: "14px",
  fontWeight: 500,
  letterSpacing: "2px",
  background: "none",
  border: "none",
  cursor: "pointer",
  transition: "color 160ms ease",
  fontFamily,
};

const learnMoreStyle: React.CSSProperties = {
  padding: "14px 20px",
  fontSize: "13px",
  color: palette.accent,
  textDecoration: "underline",
  background: "none",
  border: "none",
  cursor: "pointer",
  fontFamily,
};

// Modal styles
const modalOverlayStyle: React.CSSProperties = {
  position: "fixed",
  inset: 0,
  backgroundColor: "rgba(0, 0, 0, 0.96)",
  zIndex: 1000,
  display: "flex",
  flexDirection: "column",
  justifyContent: "center",
  fontFamily,
};

const modalContainerStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  alignItems: "center",
  justifyContent: "center",
  height: "100%",
  position: "relative",
};

const closeButtonStyle: React.CSSProperties = {
  position: "absolute",
  top: "24px",
  right: "16px",
  zIndex: 10,
  width: "48px",
  height: "48px",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  fontSize: "20px",
  color: palette.dimText,
  background: "none",
  border: "none",
  cursor: "pointer",
};

const cardsScrollStyle: React.CSSProperties = {
  display: "flex",
  overflowX: "auto",
  scrollSnapType: "x mandatory",
  WebkitOverflowScrolling: "touch",
  width: "100%",
  scrollbarWidth: "none",
};

const cardOuterStyle: React.CSSProperties = {
  minWidth: "100%",
  scrollSnapAlign: "start",
  display: "flex",
  justifyContent: "center",
  padding: "0 36px",
  boxSizing: "border-box",
};

const cardInnerStyle: React.CSSProperties = {
  textAlign: "center",
  padding: "48px 0",
  maxWidth: "560px",
};

const cardTitleStyle: React.CSSProperties = {
  fontSize: "26px",
  fontWeight: 500,
  color: "#ffffff",
  textAlign: "center",
  lineHeight: "36px",
  marginBottom: "28px",
  letterSpacing: "-0.5px",
};

const cardBodyStyle: React.CSSProperties = {
  fontSize: "16px",
  color: palette.mutedLight,
  textAlign: "center",
  lineHeight: "26px",
  marginBottom: "36px",
  whiteSpace: "pre-line",
};

const cardAccentStyle: React.CSSProperties = {
  fontSize: "14px",
  color: palette.accent,
  textAlign: "center",
  fontStyle: "italic",
  lineHeight: "22px",
};

const paginationStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "center",
  alignItems: "center",
  gap: "10px",
  marginTop: "40px",
  marginBottom: "32px",
};

const dotStyle: React.CSSProperties = {
  width: "8px",
  height: "8px",
  borderRadius: "4px",
  backgroundColor: palette.border,
  transition: "all 200ms ease",
};

const dotActiveStyle: React.CSSProperties = {
  backgroundColor: palette.accent,
  width: "28px",
};

const reassuranceStyle: React.CSSProperties = {
  fontSize: "13px",
  color: palette.dimText,
  textAlign: "center",
  marginBottom: "20px",
};

const gotItButtonStyle: React.CSSProperties = {
  margin: "0 28px",
  backgroundColor: palette.cardBg,
  padding: "18px 48px",
  borderRadius: "14px",
  border: `1px solid ${palette.border}`,
  cursor: "pointer",
  minWidth: "220px",
  fontFamily,
};

const gotItButtonDisabledStyle: React.CSSProperties = {
  backgroundColor: "transparent",
  borderColor: "transparent",
  cursor: "default",
};

const gotItTextStyle: React.CSSProperties = {
  fontSize: "15px",
  fontWeight: 500,
  color: palette.fg,
};

const gotItTextDisabledStyle: React.CSSProperties = {
  color: palette.dimText,
  fontSize: "13px",
};
