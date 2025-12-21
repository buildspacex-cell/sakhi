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
  fontFamily:
    '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Inter, Helvetica, Arial, sans-serif',
};

const containerStyle: React.CSSProperties = {
  maxWidth: "760px",
  margin: "0 auto",
  padding: "48px 32px 96px",
};

const headerStyle: React.CSSProperties = {
  textAlign: "center",
  marginBottom: "56px",
};

const brandStyle: React.CSSProperties = {
  fontSize: "16px",
  letterSpacing: "0.12em",
  textTransform: "uppercase",
  color: palette.muted,
  marginBottom: "16px",
};

const titleStyle: React.CSSProperties = {
  fontSize: "24px",
  fontWeight: 500,
  lineHeight: 1.4,
};

const modelStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "36px",
};

const sectionStyle: React.CSSProperties = {
  paddingBottom: "28px",
  borderBottom: `1px solid ${palette.divider}`,
};

const sectionTitleStyle: React.CSSProperties = {
  fontSize: "14px",
  letterSpacing: "0.08em",
  textTransform: "uppercase",
  color: palette.muted,
  marginBottom: "12px",
};

const sectionTextStyle: React.CSSProperties = {
  fontSize: "18px",
  lineHeight: 1.6,
  color: palette.accent,
  maxWidth: "680px",
};

const confidenceStyle: React.CSSProperties = {
  marginTop: "8px",
  fontSize: "13px",
  color: palette.muted,
};

const footerStyle: React.CSSProperties = {
  marginTop: "56px",
  fontSize: "14px",
  color: palette.muted,
  textAlign: "center",
};

const nextStyle: React.CSSProperties = {
  position: "fixed",
  bottom: "24px",
  left: "50%",
  transform: "translateX(-50%)",
  padding: "14px 36px",
  borderRadius: "999px",
  border: `1px solid ${palette.accent}`,
  background: "transparent",
  color: palette.fg,
  fontSize: "15px",
  letterSpacing: "0.04em",
  cursor: "pointer",
  transition: "background 0.25s ease, color 0.25s ease",
  textDecoration: "none",
};

type Section = {
  title: string;
  text: React.ReactNode;
  confidence?: string;
  borderless?: boolean;
};

const sections: Section[] = [
  {
    title: "Energy & Rhythm",
    text: "You tend to take on responsibility early and carry it for long stretches. When that happens without pause, your energy drops noticeably.",
    confidence: "Confidence: High",
  },
  {
    title: "Emotional Posture",
    text: "You often hold things together quietly. Even when you’re exhausted, stepping away can bring up guilt rather than relief.",
    confidence: "Confidence: Medium",
  },
  {
    title: "Work Pattern",
    text: "You regularly assume ownership beyond what’s strictly required of you, especially when things feel uncertain or unfinished.",
    confidence: "Confidence: High",
  },
  {
    title: "Recovery Signals",
    text: "Quiet, unstructured time appears to restore you more effectively than social distraction or stimulation.",
    confidence: "Confidence: Low (still learning)",
  },
  {
    title: "What’s Changing",
    text: (
      <>
        You’ve recently started noticing and naming exhaustion earlier, instead of pushing through it automatically.
        <br />
        <br />
        Two weeks ago, Sakhi believed pushing through fatigue helped you stay steady. Based on repeated signals, that belief has shifted.
      </>
    ),
    borderless: true,
  },
];

export default function ModelPage() {
  return (
    <div style={pageStyle}>
      <div style={containerStyle}>
        <div style={headerStyle}>
          <div style={brandStyle}>Sakhi</div>
          <div style={titleStyle}>What Sakhi Currently Understands</div>
        </div>

        <div style={modelStyle}>
          {sections.map((section) => (
            <div
              key={section.title}
              style={{
                ...sectionStyle,
                borderBottom: section.borderless
                  ? "none"
                  : sectionStyle.borderBottom,
              }}
            >
              <div style={sectionTitleStyle}>{section.title}</div>
              <div style={sectionTextStyle}>{section.text}</div>
              {section.confidence ? (
                <div style={confidenceStyle}>{section.confidence}</div>
              ) : null}
            </div>
          ))}
        </div>

        <div style={footerStyle}>This model updates as Sakhi learns more.</div>
      </div>

      <Link href="/journal/why" style={nextStyle}>
        Continue
      </Link>
    </div>
  );
}
