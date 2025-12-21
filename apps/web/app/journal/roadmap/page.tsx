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
  maxWidth: "720px",
  textAlign: "center",
};

const brandStyle: React.CSSProperties = {
  fontSize: "16px",
  letterSpacing: "0.12em",
  textTransform: "uppercase",
  color: palette.muted,
  marginBottom: "32px",
};

const titleStyle: React.CSSProperties = {
  fontSize: "24px",
  fontWeight: 500,
  marginBottom: "32px",
};

const listStyle: React.CSSProperties = {
  listStyle: "none",
  padding: 0,
  margin: "0 0 48px 0",
};

const itemStyle: React.CSSProperties = {
  fontSize: "18px",
  lineHeight: 1.6,
  color: palette.accent,
  marginBottom: "20px",
};

const askStyle: React.CSSProperties = {
  fontSize: "18px",
  color: palette.fg,
  marginBottom: "48px",
};

const ctaStyle: React.CSSProperties = {
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

export default function RoadmapPage() {
  return (
    <div style={pageStyle}>
      <div style={containerStyle}>
        <div style={brandStyle}>Sakhi</div>

        <h1 style={titleStyle}>What gets this to 100%</h1>

        <ul style={listStyle}>
          <li style={itemStyle}>Make the personal model clearer and more confidence-calibrated for users.</li>
          <li style={itemStyle}>Validate weekly retention and depth of reflection as a habit.</li>
          <li style={itemStyle}>Test willingness to pay with early users who feel this become irreplaceable.</li>
        </ul>

        <div style={askStyle}>
          We’re raising a <strong>$2M seed</strong> to turn this from a powerful demo into a daily personal intelligence product.
        </div>

        <Link href="/journal/next" style={ctaStyle}>
          What happens next
        </Link>
      </div>
    </div>
  );
}
