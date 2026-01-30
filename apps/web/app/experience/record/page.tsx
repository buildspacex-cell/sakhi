"use client";

import Link from "next/link";
import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import type React from "react";

const palette = {
  bg: "#0e0f12",
  fg: "#f4f4f5",
  muted: "#a1a1aa",
  accent: "#e5e7eb",
};

const pageStyle: React.CSSProperties = {
  minHeight: "100vh",
  background: palette.bg,
  color: palette.fg,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  padding: "48px 32px",
  fontFamily:
    '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Inter, Helvetica, Arial, sans-serif',
};

const containerStyle: React.CSSProperties = {
  maxWidth: "420px",
  textAlign: "center",
};

const brandStyle: React.CSSProperties = {
  fontSize: "14px",
  letterSpacing: "0.14em",
  textTransform: "uppercase",
  color: palette.muted,
  marginBottom: "24px",
};

const statusStyle: React.CSSProperties = {
  fontSize: "15px",
  color: palette.muted,
  marginBottom: "12px",
};

const micWrapperStyle: React.CSSProperties = {
  margin: "0 auto 48px",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
};

const micButtonStyle: React.CSSProperties = {
  width: "48px",
  height: "48px",
  borderRadius: "50%",
  border: `1px solid ${palette.muted}`,
  background: "transparent",
  color: palette.fg,
  cursor: "pointer",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
};

const promptStyle: React.CSSProperties = {
  fontSize: "16px",
  lineHeight: 1.5,
  color: palette.accent,
  marginBottom: "32px",
};

const altInputStyle: React.CSSProperties = {
  fontSize: "13px",
  color: palette.muted,
  textDecoration: "underline",
  cursor: "pointer",
  marginBottom: "24px",
};

const safetyStyle: React.CSSProperties = {
  fontSize: "12px",
  color: palette.muted,
  marginTop: "8px",
};

export default function ExperienceRecordPage() {
  return (
    <Suspense fallback={null}>
      <ExperiencePageContent />
    </Suspense>
  );
}

function ExperiencePageContent() {
  const searchParams = useSearchParams();
  const fallbackUser = searchParams.get("user");
  const [authUser, setAuthUser] = useState<{ person_id: string; full_name?: string | null } | null>(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadAuth = async () => {
      try {
        const res = await fetch("/api/auth/me");
        if (!res.ok) {
          setError("Unable to load account. Please re-login.");
          return;
        }
        const data = await res.json();
        setAuthUser({ person_id: data.person_id, full_name: data.full_name });
      } catch {
        setError("Unable to load account. Please re-login.");
      } finally {
        setAuthLoading(false);
      }
    };
    loadAuth();
  }, []);

  const personId = authUser?.person_id || fallbackUser || "";
  const displayName = authUser?.full_name || null;

  return (
    <div style={pageStyle}>
      <div style={containerStyle}>
        <div style={brandStyle}>Sakhi</div>

        <div style={statusStyle}>
          {authLoading ? "Loading account…" : `Listening${displayName ? `, ${displayName}` : ""}`}
        </div>
        <div style={micWrapperStyle}>
          <Link
            href={`/experience/listening?user=${encodeURIComponent(personId)}`}
            style={{ textDecoration: "none", pointerEvents: personId ? "auto" : "none", opacity: personId ? 1 : 0.6 }}
          >
            <button type="button" style={micButtonStyle} aria-label="Start recording">
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                style={{ width: 20, height: 20 }}
              >
                <rect x="9" y="3" width="6" height="11" rx="3"></rect>
                <path d="M5 10v2a7 7 0 0 0 14 0v-2"></path>
                <line x1="12" y1="19" x2="12" y2="22"></line>
              </svg>
            </button>
          </Link>
        </div>

        <div style={promptStyle}>
          Whenever you’re ready,
          <br />
          tell me what’s been on your mind.
        </div>

        <Link
          href={`/experience/type?user=${encodeURIComponent(personId)}`}
          style={{ textDecoration: "none", pointerEvents: personId ? "auto" : "none", opacity: personId ? 1 : 0.6 }}
        >
          <div style={altInputStyle}>Type instead</div>
        </Link>

        <div style={safetyStyle}>{error || "Only you and Sakhi see this."}</div>
      </div>
    </div>
  );
}
