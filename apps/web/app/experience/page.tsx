"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
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

const weeklyCueStyle: React.CSSProperties = {
  fontSize: "13px",
  color: palette.muted,
  marginBottom: "36px",
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

const devSelectStyle: React.CSSProperties = {
  padding: "8px 12px",
  borderRadius: "10px",
  border: `1px solid ${palette.muted}`,
  background: "transparent",
  color: palette.accent,
  fontSize: "13px",
  fontFamily:
    '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Inter, Helvetica, Arial, sans-serif',
};

export default function ExperiencePage() {
  const searchParams = useSearchParams();
  const DEV_USERS = useMemo(
    () => ({
      a: { label: "Vidhya" },
      b: { label: "Ravi" },
    }),
    []
  );
  const searchUser = searchParams.get("user");
  const [devUser, setDevUser] = useState<string>(searchUser || "a");

  useEffect(() => {
    if (typeof window !== "undefined") {
      const stored = window.localStorage.getItem("dev_user");
      if (!searchUser && stored && stored !== devUser) {
        setDevUser(stored);
        return;
      }
      window.localStorage.setItem("dev_user", devUser);
      const url = new URL(window.location.href);
      url.searchParams.set("user", devUser);
      window.history.replaceState({}, "", url.toString());
    }
  }, [devUser, searchUser]);

  const devLabel = DEV_USERS[devUser]?.label || devUser;
  const withUser = (path: string) => `${path}?user=${encodeURIComponent(devUser)}`;

  return (
    <div style={pageStyle}>
      <div style={containerStyle}>
        <div style={brandStyle}>Sakhi</div>

        <div style={statusStyle}>Listening — {devLabel} (dev slot)</div>
        <div style={weeklyCueStyle}>This reflection contributes to your week.</div>

        <div style={{ marginBottom: 16 }}>
          <select
            value={devUser}
            onChange={(e) => setDevUser(e.target.value)}
            style={devSelectStyle}
            aria-label="Select dev user"
          >
            {Object.entries(DEV_USERS).map(([key, value]) => (
              <option value={key} key={key}>
                {value.label}
              </option>
            ))}
          </select>
        </div>

        <div style={micWrapperStyle}>
          <Link href={withUser("/experience/listening")} style={{ textDecoration: "none" }}>
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

        <Link href={withUser("/experience/type")} style={{ textDecoration: "none" }}>
          <div style={altInputStyle}>Type instead</div>
        </Link>

        <div style={safetyStyle}>Only you and Sakhi see this.</div>
      </div>
    </div>
  );
}
