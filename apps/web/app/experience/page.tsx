"use client";

import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import type React from "react";
import type { Route } from "next";
import { editorialFontFamily as fontFamily, midnightEditorial as palette } from "@/lib/theme/midnightEditorial";

export const dynamic = "force-dynamic";

const FADE_DURATION_MS = 400;

interface AuthUser {
  person_id: string;
  email: string;
  full_name: string | null;
  needs_name: boolean;
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
  const [isFading, setIsFading] = useState(false);
  const [isHoveringBegin, setIsHoveringBegin] = useState(false);
  const [authUser, setAuthUser] = useState<AuthUser | null>(null);
  const [authChecked, setAuthChecked] = useState(false);
  const hasNavigated = useRef(false);

  useEffect(() => {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 3000);

    const fetchUser = async () => {
      try {
        const res = await fetch("/api/auth/me", {
          signal: controller.signal,
          cache: "no-store",
        });
        if (!res.ok) {
          return;
        }

        const data = await res.json();
        setAuthUser({
          person_id: data.person_id,
          email: data.email,
          full_name: data.full_name,
          needs_name: Boolean(data.needs_name),
        });
      } catch (err) {
        if ((err as Error).name !== "AbortError") {
          console.error("Error fetching auth user:", err);
        }
      } finally {
        clearTimeout(timeout);
        setAuthChecked(true);
      }
    };

    void fetchUser();

    return () => {
      clearTimeout(timeout);
      controller.abort();
    };
  }, []);

  const nextPath = useMemo(() => {
    if (!authUser) {
      return `/auth/login?redirect=${encodeURIComponent("/experience/converse")}`;
    }

    const encodedUser = encodeURIComponent(authUser.person_id);
    const encodedName = encodeURIComponent(authUser.full_name || "");
    if (authUser.needs_name || !authUser.full_name?.trim()) {
      return `/experience/onboarding?user=${encodedUser}&name=${encodedName}`;
    }
    return `/experience/converse?user=${encodedUser}&name=${encodedName}`;
  }, [authUser]);

  useEffect(() => {
    if (!authChecked || hasNavigated.current) {
      return;
    }
    if (authUser && !authUser.needs_name && authUser.full_name?.trim()) {
      hasNavigated.current = true;
      setIsFading(true);
      window.setTimeout(() => {
        router.replace(nextPath as Route);
      }, FADE_DURATION_MS);
    }
  }, [authChecked, authUser, nextPath, router]);

  const handleBegin = useCallback(() => {
    if (!authChecked || hasNavigated.current) {
      return;
    }
    hasNavigated.current = true;
    setIsFading(true);
    window.setTimeout(() => {
      router.replace(nextPath as Route);
    }, FADE_DURATION_MS);
  }, [authChecked, nextPath, router]);

  return (
    <main
      style={{ ...containerStyle, opacity: isFading ? 0 : 1 }}
    >
      <div style={contentStyle}>
        <div style={textContainerStyle}>
          <h1 style={headlineStyle}>
            This is a quiet space to unload your mind.
          </h1>
          <p style={subheadlineStyle}>
            You can talk, or hand something off.
          </p>
        </div>

        <button
          style={{
            ...beginButtonStyle,
            color: !authChecked
              ? palette.dim
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
      </div>
    </main>
  );
}

const containerStyle: React.CSSProperties = {
  minHeight: "100vh",
  background: `radial-gradient(circle at top right, ${palette.auroraCool} 0%, transparent 32%), radial-gradient(circle at bottom left, ${palette.auroraWarm} 0%, transparent 28%), ${palette.bg}`,
  color: palette.fg,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  padding: "40px 28px",
  fontFamily,
  transition: `opacity ${FADE_DURATION_MS}ms ease`,
};

const contentStyle: React.CSSProperties = {
  width: "100%",
  maxWidth: "640px",
  display: "flex",
  flexDirection: "column",
  alignItems: "center",
  justifyContent: "center",
};

const textContainerStyle: React.CSSProperties = {
  textAlign: "center",
  marginBottom: "44px",
};

const headlineStyle: React.CSSProperties = {
  fontSize: "24px",
  fontWeight: 400,
  color: palette.white,
  textAlign: "center",
  lineHeight: "32px",
  margin: "0 0 16px 0",
  letterSpacing: "-0.02em",
};

const subheadlineStyle: React.CSSProperties = {
  fontSize: "15px",
  fontWeight: 400,
  color: palette.muted,
  textAlign: "center",
  lineHeight: "22px",
  margin: 0,
};

const beginButtonStyle: React.CSSProperties = {
  background: "transparent",
  border: "none",
  padding: "16px 36px",
  marginBottom: "32px",
  minHeight: "52px",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  fontFamily,
  fontSize: "15px",
  fontWeight: 500,
  letterSpacing: "0.14em",
  transition: "color 150ms ease",
};
