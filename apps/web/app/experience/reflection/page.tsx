"use client";

import Link from "next/link";
import type React from "react";

const palette = {
  bg: "#0e0f12",
  fg: "#f4f4f5",
  muted: "#a1a1aa",
  accent: "#e5e7eb",
  divider: "#27272a",
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
  maxWidth: "520px",
  textAlign: "center",
};

const brandStyle: React.CSSProperties = {
  fontSize: "14px",
  letterSpacing: "0.14em",
  textTransform: "uppercase",
  color: palette.muted,
  marginBottom: "40px",
};

const reflectionStyle: React.CSSProperties = {
  fontSize: "20px",
  lineHeight: 1.6,
  color: palette.accent,
  marginBottom: "56px",
};

const choicesStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "center",
  gap: "20px",
  flexWrap: "wrap",
};

const choiceStyle: React.CSSProperties = {
  padding: "12px 24px",
  borderRadius: "999px",
  border: `1px solid ${palette.divider}`,
  background: "transparent",
  color: palette.fg,
  fontSize: "15px",
  letterSpacing: "0.04em",
  cursor: "pointer",
  transition: "background 0.25s ease, color 0.25s ease",
};

const hintStyle: React.CSSProperties = {
  marginTop: "32px",
  fontSize: "13px",
  color: palette.muted,
};

const confidenceStyle: React.CSSProperties = {
  marginTop: "12px",
  fontSize: "12px",
  color: palette.muted,
};

export default function ExperienceReflectionPage() {
  return (
    <div style={pageStyle}>
      <div style={containerStyle}>
        <div style={brandStyle}>Sakhi</div>

        <div style={reflectionStyle}>
          When responsibility stretches for long periods without pause, your energy seems to dip — and guilt often shows up when you rest.
          <br />
          <br />
          Does that feel accurate?
        </div>

        <div style={choicesStyle}>
          <Link href="/experience/memory" style={{ textDecoration: "none" }}>
            <button type="button" style={choiceStyle}>
              Yes
            </button>
          </Link>
          <Link href="/experience/memory" style={{ textDecoration: "none" }}>
            <button type="button" style={choiceStyle}>
              Not sure
            </button>
          </Link>
          <Link href="/experience/memory" style={{ textDecoration: "none" }}>
            <button type="button" style={choiceStyle}>
              No
            </button>
          </Link>
        </div>

        <div style={hintStyle}>Your response helps Sakhi understand you more clearly.</div>

        <div style={confidenceStyle}>Sakhi is still learning this.</div>
      </div>
    </div>
  );
}
