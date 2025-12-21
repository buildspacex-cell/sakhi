"use client";

import Link from "next/link";

const palette = {
  bg: "#0e0f12",
  fg: "#f4f4f5",
  muted: "#a1a1aa",
  accent: "#e5e7eb",
};

const containerStyle: React.CSSProperties = {
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

const innerStyle: React.CSSProperties = {
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

const questionStyle: React.CSSProperties = {
  marginTop: "28px",
  fontSize: "18px",
  color: palette.fg,
};

const actionsStyle: React.CSSProperties = {
  marginTop: "36px",
  display: "flex",
  justifyContent: "center",
  gap: "16px",
  flexWrap: "wrap",
};

const buttonStyle: React.CSSProperties = {
  padding: "10px 22px",
  borderRadius: "999px",
  border: `1px solid ${palette.accent}`,
  background: "transparent",
  color: palette.fg,
  fontSize: "14px",
  letterSpacing: "0.04em",
  cursor: "pointer",
};

const continueStyle: React.CSSProperties = {
  marginTop: "48px",
  display: "inline-block",
  padding: "14px 36px",
  borderRadius: "999px",
  border: `1px solid ${palette.accent}`,
  color: palette.fg,
  textDecoration: "none",
  fontSize: "15px",
  letterSpacing: "0.04em",
};

export default function ReflectionPage() {
  return (
    <div style={containerStyle}>
      <div style={innerStyle}>
        <div style={brandStyle}>Sakhi</div>

        <div style={cardStyle}>
          <div style={textStyle}>
            Looking across the last few days, I&apos;m noticing a pattern.
            <br />
            <br />
            Your energy seems to dip after long stretches of responsibility
            without pause.
          </div>

          <div style={questionStyle}>
            I might be wrong — but does that feel accurate?
          </div>

          <div style={actionsStyle}>
            <button type="button" style={buttonStyle}>
              Yes
            </button>
            <button type="button" style={buttonStyle}>
              Not sure
            </button>
            <button type="button" style={buttonStyle}>
              No
            </button>
          </div>
        </div>

        <Link href="/journal/memory" style={continueStyle}>
          Continue
        </Link>
      </div>
    </div>
  );
}
