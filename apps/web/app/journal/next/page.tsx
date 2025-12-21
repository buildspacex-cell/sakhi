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
  maxWidth: "760px",
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
  marginBottom: "32px",
};

const sectionStyle: React.CSSProperties = {
  marginBottom: "48px",
};

const sectionTitleStyle: React.CSSProperties = {
  fontSize: "14px",
  letterSpacing: "0.08em",
  textTransform: "uppercase",
  color: palette.muted,
  marginBottom: "16px",
};

const listStyle: React.CSSProperties = {
  listStyle: "none",
  padding: 0,
  margin: 0,
};

const itemStyle: React.CSSProperties = {
  fontSize: "18px",
  lineHeight: 1.6,
  color: palette.accent,
  marginBottom: "18px",
};

const askStyle: React.CSSProperties = {
  fontSize: "18px",
  color: palette.fg,
  marginTop: "24px",
};

const ctaStyle: React.CSSProperties = {
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

export default function NextPage() {
  return (
    <div style={pageStyle}>
      <div style={containerStyle}>
        <div style={brandStyle}>Sakhi</div>

        <h1 style={headingStyle}>What happens next</h1>

        <div style={sectionStyle}>
          <div style={sectionTitleStyle}>Next 30 days</div>
          <ul style={listStyle}>
            <li style={itemStyle}>
              Make the personal model clearer and more confidence-calibrated so users can recognize themselves in it.
            </li>
            <li style={itemStyle}>
              Validate weekly retention and depth of reflection as a repeatable habit.
            </li>
            <li style={itemStyle}>
              Run early willingness-to-pay experiments with users who feel Sakhi becoming personally irreplaceable.
            </li>
          </ul>
        </div>

        <div style={sectionStyle}>
          <div style={sectionTitleStyle}>Path to revenue</div>
          <ul style={listStyle}>
            <li style={itemStyle}>Monetization follows clarity and retention — not feature count.</li>
            <li style={itemStyle}>
              Initial experiments will focus on paid access for individuals who build a consistent weekly reflection habit.
            </li>
            <li style={itemStyle}>
              Premium offerings will be tied to deeper personal modeling, continuity, and long-term insight.
            </li>
            <li style={itemStyle}>Pricing will be tested carefully to reflect long-term value, not short-term usage.</li>
          </ul>
        </div>

        <div style={askStyle}>
          We’re raising a <strong>$2M seed</strong> to turn this from a powerful demo into a daily personal intelligence product.
        </div>

        <Link href="/journal/try" style={ctaStyle}>
          Continue
        </Link>
      </div>
    </div>
  );
}
