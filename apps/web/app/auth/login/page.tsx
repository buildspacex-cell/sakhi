"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import type React from "react";
import { editorialFontFamily as fontFamily, midnightEditorial as palette } from "@/lib/theme/midnightEditorial";

export const dynamic = "force-dynamic";

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginContent />
    </Suspense>
  );
}

function LoginContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirectTo = searchParams?.get("redirect") || "/experience/converse";

  const [isBypassChecking, setIsBypassChecking] = useState(true);
  const [isGoogleLoading, setIsGoogleLoading] = useState(false);
  const [isEmailLoading, setIsEmailLoading] = useState(false);
  const [showEmailInput, setShowEmailInput] = useState(false);
  const [email, setEmail] = useState("");
  const [emailSent, setEmailSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const tryLocalhostBypass = async () => {
      try {
        const res = await fetch("/api/auth/me", {
          cache: "no-store",
          credentials: "same-origin",
        });

        if (!res.ok) {
          return;
        }

        const data = await res.json();
        if (cancelled || data?.email !== "sakhi.vidhya.demo@gmail.com") {
          return;
        }

        router.replace("/experience/me");
      } catch {
        // Ignore and fall through to normal login UI.
      } finally {
        if (!cancelled) {
          setIsBypassChecking(false);
        }
      }
    };

    void tryLocalhostBypass();

    return () => {
      cancelled = true;
    };
  }, [router]);

  const handleGoogleLogin = async () => {
    setIsGoogleLoading(true);
    setError(null);

    try {
      const supabase = createClient();
      const { error: authError } = await supabase.auth.signInWithOAuth({
        provider: "google",
        options: {
          redirectTo: `${window.location.origin}/auth/callback?redirect=${encodeURIComponent(redirectTo)}`,
          queryParams: {
            access_type: "offline",
            prompt: "consent",
          },
        },
      });

      if (authError) {
        setError(authError.message);
        setIsGoogleLoading(false);
      }
    } catch (err: unknown) {
      console.error("Google login error:", err);
      setError(err instanceof Error ? err.message : "Failed to initiate login. Please try again.");
      setIsGoogleLoading(false);
    }
  };

  const handleEmailLogin = async () => {
    const trimmedEmail = email.trim();
    if (!trimmedEmail) {
      setError("Please enter your email address.");
      return;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(trimmedEmail)) {
      setError("Please enter a valid email address.");
      return;
    }

    setIsEmailLoading(true);
    setError(null);

    try {
      const supabase = createClient();
      const { error: authError } = await supabase.auth.signInWithOtp({
        email: trimmedEmail,
        options: {
          emailRedirectTo: `${window.location.origin}/auth/callback?redirect=${encodeURIComponent(redirectTo)}`,
        },
      });

      if (authError) {
        setError(authError.message);
        return;
      }

      setEmailSent(true);
    } catch (err: unknown) {
      console.error("Email login error:", err);
      setError(err instanceof Error ? err.message : "Could not send magic link.");
    } finally {
      setIsEmailLoading(false);
    }
  };

  const handleBack = () => {
    if (emailSent) {
      setEmailSent(false);
      setEmail("");
      return;
    }
    if (showEmailInput) {
      setShowEmailInput(false);
      setEmail("");
      setError(null);
      return;
    }
    router.back();
  };

  if (isBypassChecking) {
    return (
      <div style={containerStyle}>
        <main style={contentStyle}>
          <div style={textContainerStyle}>
            <h1 style={titleStyle}>Opening your space…</h1>
            <p style={subtitleStyle}>Checking local access.</p>
          </div>
        </main>
      </div>
    );
  }

  if (emailSent) {
    return (
      <div style={containerStyle}>
        <button style={backButtonStyle} onClick={handleBack}>
          &#8592;
        </button>
        <main style={contentStyle}>
          <div style={iconContainerStyle}>✉</div>
          <h1 style={titleStyle}>Check your email</h1>
          <p style={subtitleStyle}>
            We sent a magic link to
            <br />
            <span style={emailHighlightStyle}>{email}</span>
          </p>
          <button
            style={{ ...authButtonStyle, ...emailButtonStyle }}
            onClick={() => {
              setEmailSent(false);
              setEmail("");
            }}
          >
            <span style={emailButtonTextStyle}>Use a different email</span>
          </button>
        </main>
      </div>
    );
  }

  if (showEmailInput) {
    return (
      <div style={containerStyle}>
        <button style={backButtonStyle} onClick={handleBack}>
          &#8592;
        </button>
        <main style={contentStyle}>
          <div style={textContainerStyle}>
            <h1 style={titleStyle}>Enter your email</h1>
            <p style={subtitleStyle}>We&apos;ll send you a magic link to sign in.</p>
          </div>

          <div style={authButtonsStyle}>
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="your@email.com"
              autoFocus
              style={emailInputStyle}
            />
            <button
              onClick={() => void handleEmailLogin()}
              disabled={isEmailLoading}
              style={{
                ...authButtonStyle,
                ...googleButtonStyle,
                opacity: isEmailLoading ? 0.7 : 1,
                cursor: isEmailLoading ? "not-allowed" : "pointer",
              }}
            >
              <span style={googleButtonTextStyle}>
                {isEmailLoading ? "Sending..." : "Send magic link"}
              </span>
            </button>
          </div>

          {error ? <div style={errorStyle}>{error}</div> : null}
        </main>
      </div>
    );
  }

  return (
    <div style={containerStyle}>
      <button style={backButtonStyle} onClick={handleBack}>
        &#8592;
      </button>

      <main style={contentStyle}>
        <div style={textContainerStyle}>
          <h1 style={explanationStyle}>So Sakhi can stay with you.</h1>
        </div>

        <div style={authButtonsStyle}>
          <button
            onClick={() => void handleGoogleLogin()}
            disabled={isGoogleLoading}
            style={{
              ...authButtonStyle,
              ...googleButtonStyle,
              opacity: isGoogleLoading ? 0.7 : 1,
              cursor: isGoogleLoading ? "not-allowed" : "pointer",
            }}
          >
            {isGoogleLoading ? (
              <span style={googleButtonTextStyle}>Signing in...</span>
            ) : (
              <>
                <div style={googleIconContainerStyle}>
                  <span style={googleIconTextStyle}>G</span>
                </div>
                <span style={googleButtonTextStyle}>Continue with Google</span>
              </>
            )}
          </button>

          <button
            style={{ ...authButtonStyle, ...emailButtonStyle }}
            onClick={() => {
              setShowEmailInput(true);
              setError(null);
            }}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={palette.muted} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="2" y="4" width="20" height="16" rx="2" />
              <path d="M22 7l-8.97 5.7a1.94 1.94 0 01-2.06 0L2 7" />
            </svg>
            <span style={emailButtonTextStyle}>Continue with email</span>
          </button>
        </div>

        {error ? <div style={errorStyle}>{error}</div> : null}

        <p style={privacyNoteStyle}>
          This space is only between you and Sakhi.
        </p>
      </main>
    </div>
  );
}

const containerStyle: React.CSSProperties = {
  minHeight: "100vh",
  background: `radial-gradient(circle at top right, ${palette.auroraCool} 0%, transparent 30%), radial-gradient(circle at bottom left, ${palette.auroraWarm} 0%, transparent 24%), ${palette.bg}`,
  color: palette.fg,
  fontFamily,
  position: "relative",
};

const backButtonStyle: React.CSSProperties = {
  position: "absolute",
  top: "24px",
  left: "12px",
  zIndex: 10,
  width: "48px",
  height: "48px",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  background: "none",
  border: "none",
  color: palette.subtle,
  fontSize: "22px",
  cursor: "pointer",
  fontFamily,
};

const contentStyle: React.CSSProperties = {
  minHeight: "100vh",
  display: "flex",
  flexDirection: "column",
  justifyContent: "center",
  alignItems: "center",
  padding: "0 40px",
};

const textContainerStyle: React.CSSProperties = {
  marginBottom: "40px",
};

const explanationStyle: React.CSSProperties = {
  fontSize: "24px",
  fontWeight: 400,
  color: palette.white,
  textAlign: "center",
  lineHeight: "32px",
  margin: 0,
  letterSpacing: "-0.02em",
};

const titleStyle: React.CSSProperties = {
  fontSize: "24px",
  fontWeight: 400,
  color: palette.white,
  textAlign: "center",
  lineHeight: "32px",
  margin: 0,
  letterSpacing: "-0.02em",
};

const subtitleStyle: React.CSSProperties = {
  fontSize: "15px",
  fontWeight: 400,
  color: palette.muted,
  textAlign: "center",
  lineHeight: "22px",
  margin: "14px 0 0",
};

const authButtonsStyle: React.CSSProperties = {
  width: "100%",
  maxWidth: "320px",
  display: "flex",
  flexDirection: "column",
  gap: "14px",
};

const authButtonStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "row",
  alignItems: "center",
  justifyContent: "center",
  padding: "16px 24px",
  borderRadius: "14px",
  width: "100%",
  gap: "14px",
  minHeight: "52px",
  fontFamily,
  fontSize: "15px",
  fontWeight: 500,
  cursor: "pointer",
  transition: "opacity 150ms ease",
};

const googleButtonStyle: React.CSSProperties = {
  backgroundColor: palette.glass,
  border: `1px solid ${palette.border}`,
  color: palette.fg,
  boxShadow: "0 12px 24px rgba(0,0,0,0.18)",
};

const googleIconContainerStyle: React.CSSProperties = {
  width: "22px",
  height: "22px",
  borderRadius: "11px",
  backgroundColor: "rgba(255,255,255,0.92)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
};

const googleIconTextStyle: React.CSSProperties = {
  fontSize: "13px",
  fontWeight: 700,
  color: "#4285F4",
};

const googleButtonTextStyle: React.CSSProperties = {
  fontSize: "15px",
  fontWeight: 500,
  color: palette.fg,
};

const emailButtonStyle: React.CSSProperties = {
  backgroundColor: palette.accentSoft,
  border: `1px solid ${palette.accentBorder}`,
  color: palette.muted,
};

const emailButtonTextStyle: React.CSSProperties = {
  fontSize: "15px",
  fontWeight: 500,
  color: palette.muted,
};

const emailInputStyle: React.CSSProperties = {
  width: "100%",
  minHeight: "52px",
  borderRadius: "14px",
  border: `1px solid ${palette.border}`,
  backgroundColor: palette.glass,
  color: palette.fg,
  padding: "14px 16px",
  fontFamily,
  fontSize: "15px",
  outline: "none",
  boxShadow: "0 10px 18px rgba(0,0,0,0.12)",
};

const errorStyle: React.CSSProperties = {
  marginTop: "20px",
  padding: "12px 16px",
  background: palette.dangerBg,
  border: `1px solid ${palette.danger}`,
  borderRadius: "8px",
  color: palette.danger,
  fontSize: "14px",
  textAlign: "center",
  width: "100%",
  maxWidth: "320px",
};

const privacyNoteStyle: React.CSSProperties = {
  marginTop: "34px",
  fontSize: "13px",
  color: palette.dim,
  textAlign: "center",
  lineHeight: "18px",
};

const iconContainerStyle: React.CSSProperties = {
  width: "64px",
  height: "64px",
  borderRadius: "32px",
  border: `1px solid ${palette.border}`,
  backgroundColor: palette.glass,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  fontSize: "24px",
  marginBottom: "20px",
  color: palette.accent,
};

const emailHighlightStyle: React.CSSProperties = {
  color: "#ffffff",
};
