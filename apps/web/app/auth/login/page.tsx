"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { createClient } from "@/lib/supabase/client";

export const dynamic = "force-dynamic";

const palette = {
  bg: "#0e0f12",
  fg: "#f4f4f5",
  muted: "#a1a1aa",
  accent: "#6366f1",
  accentHover: "#818cf8",
  cardBg: "#18191d",
  border: "#27272a",
  google: "#4285f4",
  googleHover: "#5a95f5",
};

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginContent />
    </Suspense>
  );
}

function LoginContent() {
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
      // If successful, user is redirected to Google
    } catch (err) {
      setError("Failed to initiate login. Please try again.");
      setIsLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        background: palette.bg,
        color: palette.fg,
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Inter, sans-serif',
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "24px",
      }}
    >
      <main
        style={{
          maxWidth: "400px",
          width: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
        }}
      >
        {/* Logo / Brand */}
        <div
          style={{
            width: "64px",
            height: "64px",
            borderRadius: "16px",
            background: `linear-gradient(135deg, ${palette.accent}, #a855f7)`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            marginBottom: "24px",
          }}
        >
          <span style={{ fontSize: "28px", fontWeight: 700, color: "#fff" }}>S</span>
        </div>

        <h1
          style={{
            fontSize: "28px",
            fontWeight: 600,
            marginBottom: "8px",
            letterSpacing: "-0.02em",
          }}
        >
          Welcome to Sakhi
        </h1>

        <p
          style={{
            fontSize: "16px",
            color: palette.muted,
            textAlign: "center",
            marginBottom: "40px",
            lineHeight: 1.5,
          }}
        >
          Your personal companion for self-awareness and growth
        </p>

        {/* Google Sign In Button */}
        <button
          onClick={handleGoogleLogin}
          disabled={isLoading}
          style={{
            width: "100%",
            padding: "14px 24px",
            borderRadius: "12px",
            border: "none",
            background: palette.google,
            color: "#fff",
            fontSize: "16px",
            fontWeight: 500,
            cursor: isLoading ? "not-allowed" : "pointer",
            opacity: isLoading ? 0.7 : 1,
            transition: "all 150ms ease",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: "12px",
          }}
          onMouseEnter={(e) => {
            if (!isLoading) {
              e.currentTarget.style.background = palette.googleHover;
            }
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = palette.google;
          }}
        >
          {/* Google Icon */}
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
            <path
              d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
              fill="#fff"
            />
            <path
              d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              fill="#fff"
            />
            <path
              d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
              fill="#fff"
            />
            <path
              d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
              fill="#fff"
            />
          </svg>
          {isLoading ? "Signing in..." : "Continue with Google"}
        </button>

        {/* Error Message */}
        {error && (
          <div
            style={{
              marginTop: "20px",
              padding: "12px 16px",
              background: "#ef444420",
              border: "1px solid #ef4444",
              borderRadius: "8px",
              color: "#fca5a5",
              fontSize: "14px",
              textAlign: "center",
              width: "100%",
            }}
          >
            {error}
          </div>
        )}

        {/* Terms note */}
        <p
          style={{
            marginTop: "32px",
            fontSize: "13px",
            color: palette.muted,
            textAlign: "center",
            lineHeight: 1.5,
            opacity: 0.7,
          }}
        >
          By continuing, you agree to Sakhi&apos;s Terms of Service and Privacy Policy
        </p>
      </main>
    </div>
  );
}
