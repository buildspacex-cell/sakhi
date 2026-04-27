"use client";

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import type React from "react";
import type { Route } from "next";
import { editorialFontFamily as fontFamily, midnightEditorial as palette } from "@/lib/theme/midnightEditorial";

export const dynamic = "force-dynamic";

const FADE_DURATION_MS = 400;
const LAST_MODE_KEY = "sakhi.web.lastEntryMode";

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
  const [authUser, setAuthUser] = useState<AuthUser | null>(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [showModeChooser, setShowModeChooser] = useState(false);
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
        if (!res.ok) return;

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

  useEffect(() => {
    if (!authChecked || hasNavigated.current) return;

    if (!authUser) return; // Not logged in — stay on landing

    if (authUser.needs_name || !authUser.full_name?.trim()) {
      // Need onboarding
      hasNavigated.current = true;
      const encodedUser = encodeURIComponent(authUser.person_id);
      const encodedName = encodeURIComponent(authUser.full_name || "");
      setIsFading(true);
      window.setTimeout(() => {
        router.replace(`/experience/onboarding?user=${encodedUser}&name=${encodedName}` as Route);
      }, FADE_DURATION_MS);
      return;
    }

    // Check if they have a saved mode preference
    let savedMode: string | null = null;
    try { savedMode = localStorage.getItem(LAST_MODE_KEY); } catch { /* noop */ }

    if (savedMode === "talk" || savedMode === "offload") {
      // Resume their last mode directly
      hasNavigated.current = true;
      setIsFading(true);
      window.setTimeout(() => {
        router.replace(`/experience/converse?mode=${savedMode}` as Route);
      }, FADE_DURATION_MS);
    } else {
      // First time — show mode chooser
      setShowModeChooser(true);
    }
  }, [authChecked, authUser, router]);

  const navigateTo = useCallback((path: string) => {
    if (hasNavigated.current) return;
    hasNavigated.current = true;
    setIsFading(true);
    window.setTimeout(() => {
      router.replace(path as Route);
    }, FADE_DURATION_MS);
  }, [router]);

  const handleBegin = useCallback(() => {
    if (!authChecked || hasNavigated.current) return;
    const dest = authUser
      ? "/experience/converse"
      : `/auth/login?redirect=${encodeURIComponent("/experience")}`;
    navigateTo(dest);
  }, [authChecked, authUser, navigateTo]);

  const startMode = useCallback((mode: "talk" | "offload") => {
    try { localStorage.setItem(LAST_MODE_KEY, mode); } catch { /* noop */ }
    navigateTo(`/experience/converse?mode=${mode}`);
  }, [navigateTo]);

  if (showModeChooser && authUser) {
    const displayName = authUser.full_name?.split(" ")[0] || "";

    return (
      <main style={{ ...containerStyle, opacity: isFading ? 0 : 1 }}>
        <div style={contentStyle}>
          <div style={textContainerStyle}>
            <h1 style={headlineStyle}>
              This is a quiet space to unload your mind.
            </h1>
            <p style={subheadlineStyle}>
              {displayName ? `Welcome back, ${displayName}. ` : ""}What do you need right now?
            </p>
          </div>

          <div style={modeCardsStyle}>
            <button style={modeCardStyle} onClick={() => startMode("talk")}>
              <div style={modeCardHeaderStyle}>
                <span style={modeIconStyle}>◉</span>
                <span style={modeTitleStyle}>Talk to Sakhi</span>
              </div>
              <p style={modeBodyStyle}>Have a conversation. Get a response.</p>
              <span style={modeCtaStyle}>Start Talking</span>
            </button>

            <button style={modeCardStyle} onClick={() => startMode("offload")}>
              <div style={modeCardHeaderStyle}>
                <span style={modeIconStyle}>↓</span>
                <span style={modeTitleStyle}>Drop</span>
              </div>
              <p style={modeBodyStyle}>Drop it here. No response. Works offline too.</p>
              <span style={modeCtaStyle}>Drop Something</span>
            </button>
          </div>

          <p style={modeHintStyle}>You can switch anytime. Sakhi will remember what you used last.</p>
        </div>
      </main>
    );
  }

  return (
    <main style={{ ...containerStyle, opacity: isFading ? 0 : 1 }}>
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
            color: !authChecked ? palette.dim : palette.muted,
            cursor: authChecked ? "pointer" : "default",
          }}
          onClick={handleBegin}
          onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.color = palette.fg; }}
          onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.color = palette.muted; }}
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
  maxWidth: "560px",
  display: "flex",
  flexDirection: "column",
  alignItems: "center",
  justifyContent: "center",
};

const textContainerStyle: React.CSSProperties = {
  textAlign: "center",
  marginBottom: "40px",
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
  cursor: "pointer",
};

const modeCardsStyle: React.CSSProperties = {
  width: "100%",
  display: "flex",
  flexDirection: "column",
  gap: "12px",
};

const modeCardStyle: React.CSSProperties = {
  width: "100%",
  borderRadius: "16px",
  border: `1px solid ${palette.border}`,
  background: "rgba(21, 28, 40, 0.78)",
  padding: "20px",
  display: "flex",
  flexDirection: "column",
  gap: "8px",
  textAlign: "left",
  cursor: "pointer",
  fontFamily,
  transition: "border-color 150ms ease, background 150ms ease",
};

const modeCardHeaderStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "12px",
};

const modeIconStyle: React.CSSProperties = {
  fontSize: "20px",
  color: palette.muted,
  lineHeight: 1,
};

const modeTitleStyle: React.CSSProperties = {
  fontSize: "18px",
  fontWeight: 600,
  color: palette.fg,
};

const modeBodyStyle: React.CSSProperties = {
  margin: 0,
  fontSize: "14px",
  lineHeight: "21px",
  color: palette.muted,
};

const modeCtaStyle: React.CSSProperties = {
  marginTop: "4px",
  fontSize: "13px",
  fontWeight: 600,
  letterSpacing: "0.4px",
  color: palette.accent,
};

const modeHintStyle: React.CSSProperties = {
  marginTop: "20px",
  fontSize: "13px",
  color: palette.dim,
  textAlign: "center",
  lineHeight: "20px",
  maxWidth: "340px",
};
