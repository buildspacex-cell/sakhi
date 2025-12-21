"use client";

import Link from "next/link";
import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import type React from "react";

const palette = {
  bg: "#0e0f12",
  fg: "#f4f4f5",
  muted: "#a1a1aa",
  accent: "#e5e7eb",
  pulse: "rgba(244, 244, 245, 0.45)",
  divider: "#27272a",
};

const turnApiPath = "/api/turn-v2";

type Ack = {
  entry_id?: string;
  turn_id?: string;
  sessionId?: string;
  person_id?: string;
  created_at?: string;
  normalized?: string;
  text_echo?: string;
  content_hash?: string;
  reply?: string;
  status?: string;
  queued_jobs?: string[];
  triage?: Record<string, any>;
  layer?: string;
};

type DebugPayload = Record<string, any>;

type WeeklyItem = {
  week_start?: string;
  week_end?: string;
  highlights?: string;
  drift_score?: number | null;
  top_themes?: { theme?: string; weight?: number }[];
};

const redactLargeArrays = (_key: string, value: unknown) => {
  if (Array.isArray(value) && value.length > 40) {
    return `[${value.length} items omitted]`;
  }
  return value;
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

const outerStyle: React.CSSProperties = {
  display: "flex",
  gap: "24px",
  width: "100%",
  maxWidth: "1080px",
  alignItems: "flex-start",
  flexWrap: "wrap",
};

const containerStyle: React.CSSProperties = {
  maxWidth: "420px",
  textAlign: "center",
  flex: "1 1 320px",
};

const debugStyle: React.CSSProperties = {
  flex: "1 1 320px",
  minWidth: "320px",
  background: "#141518",
  border: `1px solid ${palette.divider}`,
  borderRadius: "16px",
  padding: "16px",
  color: palette.accent,
  fontSize: "13px",
  lineHeight: 1.5,
};

const debugTitleStyle: React.CSSProperties = {
  marginBottom: "8px",
  fontSize: "14px",
  fontWeight: 600,
};

const brandStyle: React.CSSProperties = {
  fontSize: "14px",
  letterSpacing: "0.14em",
  textTransform: "uppercase",
  color: palette.muted,
  marginBottom: "32px",
};

const statusStyle: React.CSSProperties = {
  fontSize: "15px",
  color: palette.muted,
  marginBottom: "32px",
};

const micWrapperStyle: React.CSSProperties = {
  position: "relative",
  width: "120px",
  height: "120px",
  margin: "0 auto 56px",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
};

const capturedCardStyle: React.CSSProperties = {
  margin: "0 auto 32px",
  padding: "16px",
  borderRadius: "14px",
  border: `1px solid ${palette.divider}`,
  background: "#141518",
  color: palette.accent,
  fontSize: "15px",
  lineHeight: 1.6,
  textAlign: "left",
};

const capturedLabelStyle: React.CSSProperties = {
  textAlign: "center",
  fontSize: "13px",
  color: palette.muted,
  marginBottom: "12px",
};

const editActionsStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "center",
  gap: "12px",
  marginTop: "8px",
};

const actionButtonStyle: React.CSSProperties = {
  padding: "8px 14px",
  borderRadius: "999px",
  border: `1px solid ${palette.divider}`,
  background: "transparent",
  color: palette.fg,
  fontSize: "13px",
  letterSpacing: "0.04em",
  cursor: "pointer",
  display: "inline-flex",
  alignItems: "center",
  gap: "6px",
};

const voiceButtonStyle: React.CSSProperties = {
  padding: "10px 18px",
  borderRadius: "999px",
  border: `1px solid ${palette.divider}`,
  background: "transparent",
  color: palette.fg,
  fontSize: "13px",
  letterSpacing: "0.04em",
  cursor: "pointer",
  fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Inter, Helvetica, Arial, sans-serif',
};

const voiceButtonSecondaryStyle: React.CSSProperties = {
  ...voiceButtonStyle,
  color: palette.muted,
};

const devSelectStyle: React.CSSProperties = {
  padding: "8px 12px",
  borderRadius: "10px",
  border: `1px solid ${palette.divider}`,
  background: "#141518",
  color: palette.accent,
  fontSize: "13px",
  fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Inter, Helvetica, Arial, sans-serif',
};

const navRowStyle: React.CSSProperties = {
  marginTop: "16px",
  display: "flex",
  justifyContent: "center",
};

const editTextareaStyle: React.CSSProperties = {
  width: "100%",
  minHeight: "120px",
  background: "#141518",
  border: `1px solid ${palette.divider}`,
  borderRadius: "12px",
  padding: "12px",
  color: palette.fg,
  fontSize: "15px",
  lineHeight: 1.5,
  resize: "none",
};

const pulseRingStyle: React.CSSProperties = {
  position: "absolute",
  width: "140px",
  height: "140px",
  borderRadius: "50%",
  background: `radial-gradient(circle, ${palette.pulse} 0%, rgba(244,244,245,0.25) 40%, transparent 70%)`,
  animation: "breathe 4.5s ease-in-out infinite",
  filter: "blur(2px)",
};

const micButtonStyle: React.CSSProperties = {
  position: "relative",
  width: "48px",
  height: "48px",
  borderRadius: "50%",
  border: `1px solid ${palette.accent}`,
  background: "transparent",
  color: palette.fg,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
};

const promptStyle: React.CSSProperties = {
  fontSize: "16px",
  lineHeight: 1.6,
  color: palette.accent,
  marginBottom: "24px",
};

const stopHintStyle: React.CSSProperties = {
  fontSize: "13px",
  color: palette.muted,
  marginTop: "12px",
};

const weeklyReminderStyle: React.CSSProperties = {
  fontSize: "12px",
  color: palette.muted,
  marginTop: "28px",
};

const mutedSmall: React.CSSProperties = {
  fontSize: "12px",
  color: palette.muted,
  marginBottom: "12px",
};

const errorStyle: React.CSSProperties = {
  color: "#f87171",
  fontSize: "13px",
  marginTop: "12px",
};

const breathingKeyframes = `
  @keyframes breathe {
    0% { transform: scale(0.85); opacity: 0.4; }
    50% { transform: scale(1.15); opacity: 0.9; }
    100% { transform: scale(0.85); opacity: 0.4; }
  }
`;

export default function ListeningPage() {
  return (
    <Suspense fallback={null}>
      <ListeningPageContent />
    </Suspense>
  );
}

function ListeningPageContent() {
  const searchParams = useSearchParams();
  const [captured, setCaptured] = useState(false);
  const [transcript, setTranscript] = useState<string>(
    "Today I pushed through work even though I was exhausted, and I felt guilty when I considered resting."
  );
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(transcript);
  const [ack, setAck] = useState<Ack | null>(null);
  const [debugData, setDebugData] = useState<DebugPayload | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [weekly, setWeekly] = useState<WeeklyItem | null>(null);
  const [weeklyLoading, setWeeklyLoading] = useState(false);

  const DEV_USERS = useMemo(
    () => ({
      a: { label: "Vidhya" },
      b: { label: "Ravi" },
    }),
    []
  );
  const searchUser = searchParams.get("user");
  const initialDevUser = searchUser === "b" ? ("b" as const) : ("a" as const);
  const [devUser, setDevUser] = useState<keyof typeof DEV_USERS>(initialDevUser);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const stored = window.localStorage.getItem("dev_user");
      if (!searchUser && stored && stored !== devUser) {
        setDevUser(stored as keyof typeof DEV_USERS);
        return;
      }
      window.localStorage.setItem("dev_user", devUser);
      const url = new URL(window.location.href);
      url.searchParams.set("user", devUser);
      window.history.replaceState({}, "", url.toString());
    }
  }, [devUser, searchUser, DEV_USERS]);

  const fetchWeekly = useCallback(async () => {
    setWeeklyLoading(true);
    try {
      const res = await fetch(`/api/memory/weekly?user=${encodeURIComponent(devUser)}&limit=1`);
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      let item: WeeklyItem | null = null;
      if (Array.isArray(data?.items) && data.items.length) {
        item = data.items[0] as WeeklyItem;
      } else if (data?.reflection && typeof data.reflection === "object") {
        const windowStr = typeof data?.window === "string" ? data.window : "";
        const windowParts = windowStr.includes("→") ? windowStr.split("→").map((p: string) => p.trim()) : [];
        item = {
          week_start: data.week_start || windowParts[0],
          week_end: data.week_end || windowParts[1],
          highlights: data.reflection.overview || "",
          drift_score: null,
          top_themes: [],
        };
      }
      setWeekly(item || null);
    } catch (err) {
      console.warn("weekly fetch failed", err);
    } finally {
      setWeeklyLoading(false);
    }
  }, [devUser]);

  useEffect(() => {
    fetchWeekly();
  }, [devUser, fetchWeekly]);

  const submitToApi = async (text: string) => {
    if (!text.trim()) return;
    setLoading(true);
    setError(null);
    setDebugData(null);
    try {
      const res = await fetch(`${turnApiPath}?user=${encodeURIComponent(devUser)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, capture_only: true }),
      });
      if (!res.ok) {
        const message = await res.text();
        throw new Error(message || "Unable to save entry");
      }
      const isJson = res.headers.get("content-type")?.includes("application/json");
      if (!isJson) {
        const payload = await res.text();
        throw new Error(payload || "Unexpected response from API");
      }
      const data = (await res.json()) as Ack & { debug?: DebugPayload };
      setAck(data);
      setCaptured(true);
      setEditing(false);
      setDraft(text);
      setTranscript(text);
      setDebugData(data.debug ?? null);
      fetchWeekly();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  const handleCapture = () => {
    submitToApi(transcript);
  };

  const goToWeeklyPage = () => {
    window.location.href = `/experience/weekly?user=${encodeURIComponent(devUser)}`;
  };

  const startEdit = () => {
    setDraft(transcript);
    setEditing(true);
  };

  const saveEdit = () => {
    submitToApi(draft.trim() ? draft : transcript);
  };

  const recordAnother = () => {
    setEditing(false);
    setCaptured(false);
    setDebugData(null);
    setAck(null);
    setError(null);
  };

  return (
    <div style={pageStyle}>
      <style>{breathingKeyframes}</style>
      <div style={outerStyle}>
        <div style={containerStyle}>
          <div style={brandStyle}>Sakhi</div>

          <div style={statusStyle}>
            {captured ? "Captured" : "Listening…"} — {DEV_USERS[devUser]?.label || devUser} (dev slot)
          </div>

          <div style={{ marginBottom: 16 }}>
            <select
              value={devUser}
              onChange={(e) => setDevUser(e.target.value as keyof typeof DEV_USERS)}
              style={devSelectStyle}
              aria-label="Select dev user"
            >
              {Object.entries(DEV_USERS).map(([key, value]) => (
                <option value={key} key={key}>
                  {value.label}
                </option>
              ))}
            </select>
          </div>

          {captured ? (
            <>
              <div style={capturedLabelStyle}>I’m holding this.</div>
              <div style={{ ...capturedLabelStyle, color: "#22c55e" }}>
                Recorded. Background memory + reflection pipelines will update shortly.
              </div>
              {editing ? (
                <div style={capturedCardStyle}>
                  <textarea
                    style={editTextareaStyle}
                    value={draft}
                    onChange={(e) => setDraft(e.target.value)}
                    aria-label="Edit captured note"
                  />
                  <div style={editActionsStyle}>
                    <button type="button" style={actionButtonStyle} onClick={saveEdit} disabled={loading}>
                      {loading ? "Saving…" : "Done"}
                    </button>
                  </div>
                </div>
              ) : (
                <div style={capturedCardStyle}>{transcript}</div>
              )}
              {!editing && (
                <div style={editActionsStyle}>
                  <button type="button" style={actionButtonStyle} onClick={startEdit}>
                    <span aria-hidden="true">✏️</span>
                    Edit
                  </button>
                  <button type="button" style={actionButtonStyle} onClick={recordAnother}>
                    <span aria-hidden="true">🎙️</span>
                    Record another
                  </button>
                </div>
              )}
              <div style={navRowStyle}>
                <Link
                  href={`/experience?user=${encodeURIComponent(devUser)}`}
                  style={{ ...actionButtonStyle, textDecoration: "none" }}
                >
                  <span aria-hidden="true">🏠</span>
                  Home
                </Link>
              </div>
            </>
          ) : (
            <>
              <div style={micWrapperStyle} onClick={handleCapture}>
                <div style={pulseRingStyle}></div>
                <div style={micButtonStyle} aria-hidden="true">
                  <svg
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    style={{ width: 20, height: 20 }}
                  >
                    <rect x="9" y="3" width="6" height="11" rx="3"></rect>
                    <path d="M5 10v2a7 7 0 0 0 14 0v-2"></path>
                    <line x1="12" y1="19" x2="12" y2="22"></line>
                  </svg>
                </div>
              </div>

              <div style={promptStyle}>
                Take your time.
                <br />
                I’m here.
              </div>

              <div style={stopHintStyle}>Tap the mic to stop</div>

              <div style={weeklyReminderStyle}>This reflection contributes to your week.</div>
            </>
          )}
          {error && <div style={errorStyle}>{error}</div>}
        </div>

        {captured && (
          <div style={debugStyle}>
            <div style={debugTitleStyle}>Debug: /v2/turn</div>
            {ack && (
              <div style={{ marginBottom: 12 }}>
                <div style={mutedSmall}>Turn / entry id</div>
                <div style={{ fontWeight: 600 }}>{ack.entry_id || ack.turn_id || "—"}</div>
                <div style={{ marginTop: 10, display: "grid", gap: 6 }}>
                  <div>
                    <div style={mutedSmall}>Status</div>
                    <div>{ack.status || "—"}</div>
                  </div>
                  <div>
                    <div style={mutedSmall}>Session / person id</div>
                    <div style={{ fontWeight: 600 }}>{ack.sessionId || ack.person_id || "—"}</div>
                  </div>
                  <div>
                    <div style={mutedSmall}>Layer</div>
                    <div>{ack.layer || "conversation"}</div>
                  </div>
                  <div>
                    <div style={mutedSmall}>Queued jobs</div>
                    <div>{ack.queued_jobs?.length ? ack.queued_jobs.join(", ") : "—"}</div>
                  </div>
                </div>
                {ack.reply && (
                  <div style={{ marginTop: 8 }}>
                    <div style={mutedSmall}>Reply</div>
                    <div>{ack.reply}</div>
                  </div>
                )}
                {ack.triage && (
                  <pre style={{ whiteSpace: "pre-wrap", background: "#0f1115", padding: 8, borderRadius: 8 }}>
                    {JSON.stringify(ack.triage, null, 2)}
                  </pre>
                )}
              </div>
            )}
            <div style={{ marginTop: 12 }}>
              <div style={mutedSmall}>Weekly reflection (latest)</div>
              {weeklyLoading ? (
                <div>Loading…</div>
              ) : weekly ? (
                <div style={{ display: "grid", gap: 4 }}>
                  <div>{weekly.week_start} → {weekly.week_end}</div>
                  <div>{weekly.highlights || "Highlights pending."}</div>
                  <div style={{ color: palette.muted, fontSize: "12px" }}>
                    Drift {weekly.drift_score != null ? Math.round(Number(weekly.drift_score) * 100) + "%" : "n/a"}
                    {Array.isArray(weekly.top_themes) && weekly.top_themes.length
                      ? ` • Themes: ${weekly.top_themes.map(t => t?.theme).filter(Boolean).join(", ")}`
                      : ""}
                  </div>
                </div>
              ) : (
                <div style={{ color: palette.muted }}>Weekly reflection pending.</div>
              )}
              <div style={{ marginTop: 8, display: "flex", gap: 8 }}>
                <button type="button" style={{ ...voiceButtonStyle, padding: "8px 14px" }} onClick={goToWeeklyPage}>
                  View weekly page
                </button>
                <button type="button" style={{ ...voiceButtonStyle, padding: "8px 14px" }} onClick={fetchWeekly} disabled={weeklyLoading}>
                  {weeklyLoading ? "Loading…" : "Refresh"}
                </button>
              </div>
            </div>
            {debugData && (
              <div style={{ display: "grid", gap: 10 }}>
                <div>
                  <div style={mutedSmall}>debug</div>
                  <pre style={{ whiteSpace: "pre-wrap", background: "#0f1115", padding: 8, borderRadius: 8 }}>
                    {JSON.stringify(debugData, redactLargeArrays, 2)}
                  </pre>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
