"use client";

import Link from "next/link";
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
  maxWidth: "680px",
  width: "100%",
  textAlign: "center",
};

const brandStyle: React.CSSProperties = {
  fontSize: "16px",
  letterSpacing: "0.12em",
  textTransform: "uppercase",
  color: palette.muted,
  marginBottom: "40px",
};

const cardStyle: React.CSSProperties = {
  border: "1px solid rgba(229, 231, 235, 0.2)",
  borderRadius: "16px",
  padding: "40px 32px",
  background: "rgba(255, 255, 255, 0.02)",
};

const textStyle: React.CSSProperties = {
  fontSize: "20px",
  lineHeight: 1.6,
  color: palette.accent,
};

const continueStyle: React.CSSProperties = {
  marginTop: "56px",
  display: "inline-block",
  padding: "14px 36px",
  borderRadius: "999px",
  border: `1px solid ${palette.accent}`,
  color: palette.fg,
  textDecoration: "none",
  fontSize: "15px",
  letterSpacing: "0.04em",
  transition: "background 0.25s ease, color 0.25s ease",
};

export default function MemoryPage() {
  return (
    <div style={pageStyle}>
      <div style={containerStyle}>
        <div style={brandStyle}>Sakhi</div>

        <div style={cardStyle}>
          <div style={textStyle}>
            Earlier this week, you mentioned feeling guilty when you rested.
            <br />
            <br />
            That came up again when you cancelled dinner — even though you were
            exhausted.
          </div>
        </div>

        <Link href="/journal/model" style={continueStyle}>
          Continue
        </Link>
      </div>
    </div>
  );
}
