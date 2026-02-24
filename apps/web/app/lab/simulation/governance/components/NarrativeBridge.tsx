"use client";

import { govPalette } from "../theme";

export default function NarrativeBridge() {
  return (
    <div
      style={{
        margin: "48px 0 32px",
        padding: "32px 24px",
        background: govPalette.card,
        border: `1px solid ${govPalette.border}`,
        borderRadius: 12,
        textAlign: "center",
      }}
    >
      <div
        style={{
          fontSize: 12,
          color: govPalette.accent,
          fontWeight: 600,
          letterSpacing: 1,
          textTransform: "uppercase",
          marginBottom: 12,
        }}
      >
        Part Two
      </div>
      <h2
        style={{
          fontSize: 22,
          fontWeight: 700,
          color: govPalette.text,
          margin: "0 0 12px",
        }}
      >
        Now Watch Understanding Become Action
      </h2>
      <p
        style={{
          fontSize: 14,
          color: govPalette.muted,
          maxWidth: 600,
          margin: "0 auto",
          lineHeight: 1.6,
        }}
      >
        You just saw how Sakhi builds deep understanding from journal entries over time.
        But understanding alone isn&apos;t enough. What happens when real decisions arise &mdash;
        when the same situation meets three different constitutions? That&apos;s where
        governance enters. Same moment, different people, different right answers.
      </p>
    </div>
  );
}
