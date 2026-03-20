"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import type React from "react";

export const dynamic = "force-dynamic";

const palette = {
  bg: "#0a0a0a",
  fg: "#f4f4f5",
  muted: "#a1a1aa",
  dimText: "#52525b",
  border: "#27272a",
  cardBg: "#18191d",
};

const fontFamily =
  '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Inter, Helvetica, Arial, sans-serif';

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

  const [isGoogleLoading, setIsGoogleLoading] = useState(false);
  const [isEmailLoading, setIsEmailLoading] = useState(false);
  const [showEmailInput, setShowEmailInput] = useState(false);
  const [email, setEmail] = useState("");
  const [emailSent, setEmailSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
  background: palette.bg,
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
  color: "#71717a",
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
  color: "#ffffff",
  textAlign: "center",
  lineHeight: "34px",
  margin: 0,
};

const titleStyle: React.CSSProperties = {
  fontSize: "24px",
  fontWeight: 400,
  color: "#ffffff",
  textAlign: "center",
  lineHeight: "34px",
  margin: 0,
};

const subtitleStyle: React.CSSProperties = {
  fontSize: "16px",
  fontWeight: 400,
  color: palette.muted,
  textAlign: "center",
  lineHeight: "24px",
  margin: "16px 0 0",
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
  padding: "18px 28px",
  borderRadius: "14px",
  width: "100%",
  gap: "14px",
  minHeight: "56px",
  fontFamily,
  fontSize: "16px",
  fontWeight: 500,
  cursor: "pointer",
  transition: "opacity 150ms ease",
};

const googleButtonStyle: React.CSSProperties = {
  backgroundColor: palette.cardBg,
  border: `1px solid ${palette.border}`,
  color: palette.fg,
};

const googleIconContainerStyle: React.CSSProperties = {
  width: "22px",
  height: "22px",
  borderRadius: "11px",
  backgroundColor: "#ffffff",
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
  fontSize: "16px",
  fontWeight: 500,
  color: palette.fg,
};

const emailButtonStyle: React.CSSProperties = {
  backgroundColor: "transparent",
  border: `1px solid ${palette.border}`,
  color: palette.muted,
};

const emailButtonTextStyle: React.CSSProperties = {
  fontSize: "16px",
  fontWeight: 500,
  color: palette.muted,
};

const emailInputStyle: React.CSSProperties = {
  width: "100%",
  minHeight: "56px",
  borderRadius: "14px",
  border: `1px solid ${palette.border}`,
  backgroundColor: palette.cardBg,
  color: palette.fg,
  padding: "16px 18px",
  fontFamily,
  fontSize: "16px",
  outline: "none",
};

const errorStyle: React.CSSProperties = {
  marginTop: "20px",
  padding: "12px 16px",
  background: "#ef444420",
  border: "1px solid #ef4444",
  borderRadius: "8px",
  color: "#fca5a5",
  fontSize: "14px",
  textAlign: "center",
  width: "100%",
  maxWidth: "320px",
};

const privacyNoteStyle: React.CSSProperties = {
  marginTop: "40px",
  fontSize: "14px",
  color: palette.dimText,
  textAlign: "center",
  lineHeight: "20px",
};

const iconContainerStyle: React.CSSProperties = {
  width: "72px",
  height: "72px",
  borderRadius: "36px",
  border: `1px solid ${palette.border}`,
  backgroundColor: palette.cardBg,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  fontSize: "28px",
  marginBottom: "24px",
  color: "#6366f1",
};

const emailHighlightStyle: React.CSSProperties = {
  color: "#ffffff",
};
