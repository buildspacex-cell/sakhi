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
  margin: 0,
};

const itemStyle: React.CSSProperties = {
  fontSize: "18px",
  lineHeight: 1.6,
  color: palette.accent,
  marginBottom: "24px",
};

const ctaStyle: React.CSSProperties = {
  marginTop: "48px",
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

export default function WhyPage() {
  return (
    <div style={pageStyle}>
      <div style={containerStyle}>
        <div style={brandStyle}>Sakhi</div>

        <h1 style={titleStyle}>Why this isn&apos;t a chatbot</h1>

        <ul style={listStyle}>
          <li style={itemStyle}>
            Sakhi maintains a <strong>stable, longitudinal personal state model</strong> that evolves over time.
          </li>
          <li style={itemStyle}>
            Language models are used only to reflect and communicate — not to decide or remember.
          </li>
          <li style={itemStyle}>
            Understanding compounds because beliefs update with evidence, not prompts.
          </li>
          <li style={itemStyle}>
            Generic LLM companions respond well in the moment, but don&apos;t hold a durable understanding of a person.
          </li>
        </ul>

        <Link href="/journal/roadmap" style={ctaStyle}>
          What happens next
        </Link>
      </div>
    </div>
  );
}
