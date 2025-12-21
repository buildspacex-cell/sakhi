"use client";

import type React from "react";

const palette = {
  bg: "#0e0f12",
  fg: "#f4f4f5",
  muted: "#a1a1aa",
  accent: "#e5e7eb",
  divider: "#27272a",
  card: "#141518",
};

const pageStyle: React.CSSProperties = {
  minHeight: "100vh",
  background: palette.bg,
  color: palette.fg,
  display: "flex",
  justifyContent: "center",
  padding: "32px 32px 96px",
  fontFamily:
    '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Inter, Helvetica, Arial, sans-serif',
};

const containerStyle: React.CSSProperties = {
  maxWidth: "640px",
  width: "100%",
  textAlign: "left",
};

const brandStyle: React.CSSProperties = {
  textAlign: "center",
  fontSize: "14px",
  letterSpacing: "0.14em",
  textTransform: "uppercase",
  color: palette.muted,
  marginBottom: "40px",
};

const introStyle: React.CSSProperties = {
  fontSize: "18px",
  lineHeight: 1.6,
  color: palette.accent,
  marginBottom: "40px",
  textAlign: "center",
};

const cardStyle: React.CSSProperties = {
  background: palette.card,
  border: `1px solid ${palette.divider}`,
  borderRadius: "16px",
  padding: "22px 22px 24px",
  marginBottom: "24px",
};

const cardTitleStyle: React.CSSProperties = {
  fontSize: "13px",
  letterSpacing: "0.08em",
  textTransform: "uppercase",
  color: palette.muted,
  marginBottom: "10px",
};

const cardTextStyle: React.CSSProperties = {
  fontSize: "17px",
  lineHeight: 1.6,
  color: palette.accent,
};

const noteStyle: React.CSSProperties = {
  marginTop: "32px",
  fontSize: "13px",
  color: palette.muted,
  textAlign: "center",
};

const ctaStyle: React.CSSProperties = {
  marginTop: "32px",
  display: "inline-block",
  padding: "12px 28px",
  borderRadius: "999px",
  border: `1px solid ${palette.divider}`,
  color: palette.fg,
  textDecoration: "none",
  fontSize: "14px",
  letterSpacing: "0.04em",
  textAlign: "center",
};

export default function ExperienceMemoryPage() {
  return (
    <div style={pageStyle}>
      <div style={containerStyle}>
        <div style={brandStyle}>Sakhi</div>

        <div style={introStyle}>Here’s something I’m holding onto.</div>

      <div style={cardStyle}>
        <div style={cardTitleStyle}>Earlier this week</div>
        <div style={cardTextStyle}>
          You described staying strong and available for others, even when you were already feeling depleted.
        </div>
      </div>

      <div style={cardStyle}>
        <div style={cardTitleStyle}>What stood out</div>
        <div style={cardTextStyle}>
          Guilt appeared more than once when you considered stepping back to rest, suggesting a pattern rather than a one-off moment.
        </div>
      </div>

      <div style={noteStyle}>Sakhi keeps only what feels meaningful over time.</div>

      <div style={{ textAlign: "center" }}>
        <a href="/experience/weekly" style={ctaStyle}>
          Weekly Reflection
        </a>
      </div>
    </div>
  </div>
);
}
