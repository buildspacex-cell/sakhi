"use client";

import { Suspense, useCallback, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import type React from "react";
import type { Route } from "next";

const palette = {
  bg: "#0e0f12",
  fg: "#f4f4f5",
  muted: "#a1a1aa",
  accent: "#e5e7eb",
  border: "#27272a",
};

type EmotionalShift = "lighter" | "calmer" | "same" | "stirred_up";
type ReturnIntent = "yes" | "maybe" | "no";

export default function ExperienceFeedbackPage() {
  return (
    <Suspense fallback={null}>
      <ExperienceFeedbackContent />
    </Suspense>
  );
}

function ExperienceFeedbackContent() {
  const router = useRouter();
  const search = useSearchParams();
  const journalId = search?.get("entry_id") || "";
  const user = search?.get("user") || "";

  const [emotionalShift, setEmotionalShift] = useState<EmotionalShift | null>(null);
  const [returnIntent, setReturnIntent] = useState<ReturnIntent | null>(null);
  const [details, setDetails] = useState("");
  const [memorySignal, setMemorySignal] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const canSubmit = emotionalShift !== null && returnIntent !== null && journalId.length > 0;

  const optionStyle = useMemo(
    () => ({
      base: {
        width: "100%",
        textAlign: "left" as const,
        padding: "14px 16px",
        borderRadius: "12px",
        border: `1px solid ${palette.border}`,
        background: "rgba(255,255,255,0.02)",
        color: palette.fg,
        fontSize: "15px",
        letterSpacing: "0.01em",
        cursor: "pointer",
        transition: "border-color 160ms ease, background 160ms ease",
      },
      active: {
        border: `1px solid ${palette.accent}`,
        background: "rgba(255,255,255,0.04)",
      },
    }),
    []
  );

  const submit = useCallback(async () => {
    if (!canSubmit || submitting) return;
    setSubmitting(true);
    try {
      const res = await fetch(`/api/journal/feedback${user ? `?user=${encodeURIComponent(user)}` : ""}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          journal_id: journalId,
          emotional_shift: emotionalShift,
          shift_explained_text: details || null,
          return_intent: returnIntent,
          memory_signal_text: memorySignal || null,
        }),
      });
      if (!res.ok) {
        throw new Error(await res.text());
      }
    } catch (err) {
      console.error("feedback submit failed", err);
    } finally {
      setSubmitting(false);
      const next = (user ? `/experience?user=${encodeURIComponent(user)}` : "/experience") as Route;
      router.replace(next);
    }
  }, [canSubmit, details, emotionalShift, journalId, returnIntent, router, submitting, user]);

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

  const cardStyle: React.CSSProperties = {
    width: "100%",
    maxWidth: "720px",
    display: "flex",
    flexDirection: "column",
    gap: "28px",
  };

  const headerStyle: React.CSSProperties = {
    fontSize: "14px",
    letterSpacing: "0.08em",
    textTransform: "uppercase",
    color: palette.muted,
  };

  const questionStyle: React.CSSProperties = {
    fontSize: "15px",
    lineHeight: 1.6,
    color: palette.accent,
  };

  const subLabelStyle: React.CSSProperties = {
    fontSize: "15px",
    color: palette.fg,
    marginTop: "-8px",
  };

  const textareaStyle: React.CSSProperties = {
    width: "100%",
    minHeight: "120px",
    background: "rgba(255,255,255,0.02)",
    border: `1px solid ${palette.border}`,
    borderRadius: "12px",
    padding: "14px",
    color: palette.fg,
    fontSize: "15px",
    lineHeight: 1.6,
    resize: "vertical",
  };

  const doneStyle: React.CSSProperties = {
    alignSelf: "flex-start",
    marginTop: "12px",
    padding: "10px 18px",
    borderRadius: "999px",
    border: `1px solid ${palette.border}`,
    background: "transparent",
    color: palette.fg,
    fontSize: "14px",
    letterSpacing: "0.05em",
    textTransform: "uppercase" as const,
    opacity: canSubmit ? 1 : 0.4,
    cursor: canSubmit && !submitting ? "pointer" : "not-allowed",
    transition: "opacity 160ms ease, border-color 160ms ease",
  };

  const primaryOptions: { label: string; value: EmotionalShift }[] = [
    { label: "Lighter", value: "lighter" },
    { label: "Calmer", value: "calmer" },
    { label: "The same", value: "same" },
    { label: "More stirred up", value: "stirred_up" },
  ];

  const returnOptions: { label: string; value: ReturnIntent }[] = [
    { label: "Yes", value: "yes" },
    { label: "Maybe", value: "maybe" },
    { label: "No", value: "no" },
  ];

  return (
    <main style={containerStyle}>
      <section style={cardStyle}>
        <div style={headerStyle}>A quick check-in</div>

        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          <div style={questionStyle}>After saying things out here, do you feel any different?</div>
          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            {primaryOptions.map((opt) => (
              <button
                key={opt.value}
                type="button"
                onClick={() => setEmotionalShift(opt.value)}
                style={{
                  ...optionStyle.base,
                  ...(emotionalShift === opt.value ? optionStyle.active : {}),
                }}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        {emotionalShift && (
          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            <div style={subLabelStyle}>If you want to share more, what changed — even slightly?</div>
            <textarea
              style={textareaStyle}
              value={details}
              onChange={(e) => setDetails(e.target.value)}
              aria-label="Optional detail"
            />
          </div>
        )}

        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          <div style={questionStyle}>Would you want to come back to this space again?</div>
          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            {returnOptions.map((opt) => (
              <button
                key={opt.value}
                type="button"
                onClick={() => setReturnIntent(opt.value)}
                style={{
                  ...optionStyle.base,
                  ...(returnIntent === opt.value ? optionStyle.active : {}),
                }}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
          <div style={questionStyle}>Is there anything you’d want Sakhi to understand or remember ?</div>
          <textarea
            style={textareaStyle}
            value={memorySignal}
            onChange={(e) => setMemorySignal(e.target.value)}
            aria-label="Optional memory signal"
          />
        </div>

        <button type="button" style={doneStyle} onClick={submit} disabled={!canSubmit || submitting}>
          {submitting ? "Saving…" : "Done"}
        </button>
      </section>
    </main>
  );
}
