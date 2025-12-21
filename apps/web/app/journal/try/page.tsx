"use client";

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
  marginBottom: "32px",
};

const headingStyle: React.CSSProperties = {
  fontSize: "24px",
  fontWeight: 500,
  marginBottom: "24px",
};

const paragraphStyle: React.CSSProperties = {
  fontSize: "18px",
  lineHeight: 1.6,
  color: palette.accent,
  marginBottom: "48px",
};

const storesStyle: React.CSSProperties = {
  display: "flex",
  gap: "24px",
  justifyContent: "center",
  flexWrap: "wrap",
};

const storeStyle: React.CSSProperties = {
  display: "inline-block",
  padding: "14px 28px",
  borderRadius: "14px",
  border: `1px solid ${palette.accent}`,
  color: palette.fg,
  textDecoration: "none",
  fontSize: "15px",
  letterSpacing: "0.04em",
  minWidth: "220px",
  transition: "background 0.25s ease, color 0.25s ease",
};

const storeSpanStyle: React.CSSProperties = {
  display: "block",
  fontSize: "12px",
  color: palette.muted,
  marginBottom: "4px",
};

const noteStyle: React.CSSProperties = {
  marginTop: "40px",
  fontSize: "14px",
  color: palette.muted,
};

export default function TryPage() {
  return (
    <div style={pageStyle}>
      <div style={containerStyle}>
        <div style={brandStyle}>Sakhi</div>

        <h1 style={headingStyle}>Available soon</h1>

        <p style={paragraphStyle}>
          Sakhi is being prepared for early access.
          <br />
          We’re starting with a small group to ensure the experience remains thoughtful, safe, and deeply personal.
        </p>

        <div style={storesStyle}>
          <a href="#" style={storeStyle}>
            <span style={storeSpanStyle}>Download on the</span>
            App Store
          </a>

          <a href="#" style={storeStyle}>
            <span style={storeSpanStyle}>Get it on</span>
            Google Play
          </a>
        </div>

        <div style={noteStyle}>Early access invitations will be shared privately.</div>
      </div>
    </div>
  );
}
