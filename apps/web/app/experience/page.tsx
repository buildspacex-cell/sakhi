"use client";

import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import type React from "react";
import type { Route } from "next";

export const dynamic = "force-dynamic";

const palette = {
  bg: "#0e0f12",
  fg: "#f4f4f5",
  muted: "#a1a1aa",
};

const FADE_DURATION_MS = 400;

interface AuthUser {
  person_id: string;
  email: string;
  full_name: string | null;
  onboarding_completed: boolean;
}

export default function ExperienceGate() {
  return (
    <Suspense fallback={null}>
      <ExperienceGateContent />
    </Suspense>
  );
}

function ExperienceGateContent() {
  const router = useRouter();
  const search = useSearchParams();
  const [isFading, setIsFading] = useState(false);
  const [isHoveringBegin, setIsHoveringBegin] = useState(false);
  const [authUser, setAuthUser] = useState<AuthUser | null>(null);
  const [authLoading, setAuthLoading] = useState(true);
  const hasNavigated = useRef(false);

  // Fetch authenticated user on mount
  useEffect(() => {
    const fetchUser = async () => {
      try {
        const res = await fetch("/api/auth/me");
        if (res.ok) {
          const data = await res.json();
          setAuthUser(data);

          // If onboarding already completed, skip to conversation page
          if (data.onboarding_completed) {
            router.replace(`/experience/converse?user=${encodeURIComponent(data.person_id)}` as Route);
            return;
          }
        }
      } catch (err) {
        console.error("Error fetching auth user:", err);
      } finally {
        setAuthLoading(false);
      }
    };

    fetchUser();
  }, [router]);

  // Use authenticated user's person_id, or fall back to query param for dev
  const user = authUser?.person_id || search?.get("user");

  const nextPath = useMemo(() => {
    // Route to onboarding flow first
    const base = "/experience/onboarding";
    if (!user) return base;
    return `${base}?user=${encodeURIComponent(user)}`;
  }, [user]);

  const dismiss = useCallback(() => {
    if (hasNavigated.current) return;
    hasNavigated.current = true;
    setIsFading(true);
    window.setTimeout(() => {
      router.replace(nextPath as Route);
    }, FADE_DURATION_MS);
  }, [nextPath, router]);

  const containerStyle: React.CSSProperties = {
    minHeight: "100vh",
    background: palette.bg,
    color: palette.fg,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: "48px 32px",
    fontFamily:
      '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Inter, Helvetica, Arial, sans-serif',
    transition: `opacity ${FADE_DURATION_MS}ms ease`,
    opacity: isFading ? 0 : 1,
  };

  const textWrapperStyle: React.CSSProperties = {
    width: "100%",
    maxWidth: "720px",
    display: "flex",
    flexDirection: "column",
    gap: "12px",
  };

  const lineOneStyle: React.CSSProperties = {
    fontSize: "22px",
    lineHeight: 1.5,
    letterSpacing: "0.01em",
    textAlign: "left",
  };

  const lineTwoStyle: React.CSSProperties = {
    fontSize: "18px",
    lineHeight: 1.5,
    letterSpacing: "0.01em",
    color: palette.muted,
    textAlign: "left",
  };

  const beginStyle: React.CSSProperties = {
    marginTop: "32px",
    fontSize: "13px",
    color: isHoveringBegin ? palette.fg : palette.muted,
    letterSpacing: "0.08em",
    textTransform: "uppercase",
    cursor: "pointer",
    display: "inline-block",
    transition: "color 160ms ease, opacity 160ms ease",
  };

  // Show loading state while fetching auth
  if (authLoading) {
    return (
      <main style={{ ...containerStyle, justifyContent: "center" }}>
        <p style={{ color: palette.muted, fontSize: "16px" }}>Loading...</p>
      </main>
    );
  }

  // Personalized greeting if we have the user's name
  const greeting = authUser?.full_name
    ? `Welcome, ${authUser.full_name.split(" ")[0]}.`
    : null;

  return (
    <main style={containerStyle} onClick={dismiss}>
      <section style={textWrapperStyle}>
        {greeting && (
          <p style={{ ...lineOneStyle, fontSize: "16px", color: palette.muted, marginBottom: "8px" }}>
            {greeting}
          </p>
        )}
        <p style={lineOneStyle}>This is a quiet space to unload your mind.</p>
        <p style={lineTwoStyle}>Say whatever is present - you don&apos;t need to sort it.</p>
        <span
          style={beginStyle}
          onMouseEnter={() => setIsHoveringBegin(true)}
          onMouseLeave={() => setIsHoveringBegin(false)}
        >
          Begin
        </span>
      </section>
    </main>
  );
}
