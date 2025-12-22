"use client";

import { useCallback, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import type React from "react";
import type { Route } from "next";

const palette = {
  bg: "#0e0f12",
  fg: "#f4f4f5",
  muted: "#a1a1aa",
};

const FADE_DURATION_MS = 400;

export default function QuietSpace() {
  const router = useRouter();
  const search = useSearchParams();
  const [isFading, setIsFading] = useState(false);
  const hasNavigated = useRef(false);

  const user = search?.get("user");
  const nextPath = useMemo(() => {
    const base = "/experience/record";
    if (!user) return base;
    return `${base}?user=${encodeURIComponent(user)}`;
  }, [user]);

  const dismiss = useCallback(() => {
    if (hasNavigated.current) return;
    hasNavigated.current = true;
    setIsFading(true);
    window.setTimeout(() => {
      router.replace(nextPath as Route);
    }, FADE_DURATION_MS);
  }, [nextPath, router]);

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
    transition: `opacity ${FADE_DURATION_MS}ms ease`,
    opacity: isFading ? 0 : 1,
  };

  const textWrapperStyle: React.CSSProperties = {
    width: "100%",
    maxWidth: "720px",
    display: "flex",
    flexDirection: "column",
    gap: "12px",
  };

  const lineOneStyle: React.CSSProperties = {
    fontSize: "22px",
    lineHeight: 1.5,
    letterSpacing: "0.01em",
    textAlign: "left",
  };

  const lineTwoStyle: React.CSSProperties = {
    fontSize: "18px",
    lineHeight: 1.5,
    letterSpacing: "0.01em",
    color: palette.muted,
    textAlign: "left",
  };

  const beginStyle: React.CSSProperties = {
    marginTop: "32px",
    fontSize: "13px",
    color: palette.muted,
    letterSpacing: "0.08em",
    textTransform: "uppercase",
  };

  return (
    <main style={containerStyle} onClick={dismiss}>
      <section style={textWrapperStyle}>
        <p style={lineOneStyle}>This is a quiet space to unload your mind.</p>
        <p style={lineTwoStyle}>Say whatever is present - you don’t need to sort it.</p>
        <span style={beginStyle}>Begin</span>
      </section>
    </main>
  );
}
