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
  accent: "#6366f1",
  cardBg: "#18191d",
  border: "#27272a",
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
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const searchParams = useSearchParams();
  const redirectTo = searchParams?.get("redirect") || "/experience";

  const handleGoogleLogin = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const supabase = createClient();
      const { error } = await supabase.auth.signInWithOAuth({
        provider: "google",
        options: {
          redirectTo: `${window.location.origin}/auth/callback?redirect=${encodeURIComponent(redirectTo)}`,
          queryParams: {
            access_type: "offline",
            prompt: "consent",
          },
        },
      });

      if (error) {
        setError(error.message);
        setIsLoading(false);
      }
    } catch (err: any) {
      console.error("Login error:", err);
      setError(err?.message || "Failed to initiate login. Please try again.");
      setIsLoading(false);
    }
  };

  return (
    <div style={containerStyle}>
      {/* Back button */}
      <button style={backButtonStyle} onClick={() => router.back()}>
        &#8592;
      </button>

      <main style={contentStyle}>
        {/* Explanation — matches mobile */}
        <div style={textContainerStyle}>
          <h1 style={explanationStyle}>So Sakhi can stay with you.</h1>
        </div>

        {/* Auth buttons */}
        <div style={authButtonsStyle}>
          {/* Google Sign In */}
          <button
            onClick={handleGoogleLogin}
            disabled={isLoading}
            style={{
              ...authButtonStyle,
              ...googleButtonStyle,
              opacity: isLoading ? 0.7 : 1,
              cursor: isLoading ? "not-allowed" : "pointer",
            }}
          >
            {isLoading ? (
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

          {/* Email Sign In */}
          <button style={{ ...authButtonStyle, ...emailButtonStyle }}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={palette.muted} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="2" y="4" width="20" height="16" rx="2" />
              <path d="M22 7l-8.97 5.7a1.94 1.94 0 01-2.06 0L2 7" />
            </svg>
            <span style={emailButtonTextStyle}>Continue with email</span>
          </button>
        </div>

        {/* Error Message */}
        {error && (
          <div style={errorStyle}>
            {error}
          </div>
        )}

        {/* Privacy note — matches mobile */}
        <p style={privacyNoteStyle}>
          This space is only between you and Sakhi.
        </p>
      </main>
    </div>
  );
}

// =============================================================================
// STYLES
// =============================================================================

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
  marginBottom: "56px",
};

const explanationStyle: React.CSSProperties = {
  fontSize: "24px",
  fontWeight: 400,
  color: "#ffffff",
  textAlign: "center",
  lineHeight: "34px",
  margin: 0,
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
  marginTop: "32px",
  fontSize: "13px",
  color: palette.dimText,
  textAlign: "center",
};
