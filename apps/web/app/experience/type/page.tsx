"use client";

import Link from "next/link";
import { Suspense, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import type React from "react";
import type { Route } from "next";

const palette = {
  bg: "#0e0f12",
  fg: "#f4f4f5",
  muted: "#a1a1aa",
  accent: "#e5e7eb",
  divider: "#27272a",
};

const turnApiPath = "/api/turn-v2";
const DEV_USERS = {
  a: { label: "Vidhya" },
  b: { label: "Ravi" },
};

type Ack = {
  entry_id?: string;
  turn_id?: string;
  sessionId?: string;
  session_id?: string;
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
  maxWidth: "520px",
  width: "100%",
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
  marginBottom: "24px",
};

const promptStyle: React.CSSProperties = {
  fontSize: "16px",
  lineHeight: 1.6,
  color: palette.accent,
  marginBottom: "24px",
};

const textareaStyle: React.CSSProperties = {
  width: "100%",
  minHeight: "160px",
  background: "transparent",
  border: `1px solid ${palette.accent}`,
  borderRadius: "12px",
  padding: "16px",
  color: palette.fg,
  fontSize: "16px",
  fontFamily:
    '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Inter, Helvetica, Arial, sans-serif',
  resize: "none",
};

const submitStyle: React.CSSProperties = {
  marginTop: "24px",
  padding: "12px 28px",
  borderRadius: "999px",
  border: `1px solid ${palette.accent}`,
  background: "transparent",
  color: palette.fg,
  fontSize: "15px",
  letterSpacing: "0.04em",
  cursor: "pointer",
};

const safetyStyle: React.CSSProperties = {
  marginTop: "16px",
  fontSize: "12px",
  color: palette.muted,
};

const capturedCardStyle: React.CSSProperties = {
  width: "100%",
  background: "#141518",
  border: `1px solid ${palette.divider}`,
  borderRadius: "12px",
  padding: "16px",
  color: palette.accent,
  fontSize: "16px",
  lineHeight: 1.6,
  textAlign: "left",
};

const actionRowStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "center",
  gap: "12px",
  marginTop: "12px",
  flexWrap: "wrap",
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

const navRowStyle: React.CSSProperties = {
  marginTop: "16px",
  display: "flex",
  justifyContent: "center",
};

const errorStyle: React.CSSProperties = {
  color: "#f87171",
  fontSize: "13px",
  marginTop: "12px",
};

const mutedSmall: React.CSSProperties = {
  fontSize: "12px",
  color: palette.muted,
  marginBottom: "12px",
};

const devSelectStyle: React.CSSProperties = {
  padding: "8px 12px",
  borderRadius: "10px",
  border: `1px solid ${palette.divider}`,
  background: "transparent",
  color: palette.accent,
  fontSize: "13px",
  fontFamily:
    '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Inter, Helvetica, Arial, sans-serif',
};

export default function ExperienceTypePage() {
  return (
    <Suspense fallback={null}>
      <ExperienceTypePageContent />
    </Suspense>
  );
}

function ExperienceTypePageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const searchUser = searchParams.get("user");
  const initialUser: "a" | "b" = searchUser === "b" ? "b" : "a";
  const [devUser, setDevUser] = useState<"a" | "b">(initialUser);

  const [text, setText] = useState("");
  const [captured, setCaptured] = useState(false);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const [ack, setAck] = useState<Ack | null>(null);
  const [debugData, setDebugData] = useState<DebugPayload | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [weekly, setWeekly] = useState<WeeklyItem | null>(null);
  const [weeklyLoading, setWeeklyLoading] = useState(false);
  const [entryId, setEntryId] = useState<string | null>(null);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const stored = window.localStorage.getItem("dev_user");
      if (!searchUser && stored && (stored === "a" || stored === "b") && stored !== devUser) {
        setDevUser(stored);
        return;
      }
      window.localStorage.setItem("dev_user", devUser);
      const url = new URL(window.location.href);
      url.searchParams.set("user", devUser);
      window.history.replaceState({}, "", url.toString());
    }
  }, [devUser, searchUser]);

  const devLabel = DEV_USERS[devUser]?.label || devUser;

  const fetchWeekly = async () => {
    setWeeklyLoading(true);
    try {
      const res = await fetch(`/api/memory/weekly?user=${encodeURIComponent(devUser)}&limit=1`);
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      let item = Array.isArray(data?.items) && data.items.length ? data.items[0] : null;
      if (!item && data?.reflection && typeof data.reflection === "object") {
        item = {
          week_start: data.week_start,
          week_end: data.week_end,
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
  };

  const submitToApi = async (bodyText: string) => {
    if (!bodyText.trim()) return;
    setLoading(true);
    setError(null);
    setDebugData(null);
    try {
      const res = await fetch(`${turnApiPath}?user=${encodeURIComponent(devUser)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: bodyText, capture_only: true }),
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
      setDraft(bodyText);
      setText(bodyText);
      setDebugData(data.debug ?? null);
      fetchWeekly();
      const entryId = data.entry_id || data.turn_id || data.sessionId || data.session_id || data.person_id;
      if (entryId) {
        setEntryId(entryId);
        const next = `/experience/feedback?entry_id=${encodeURIComponent(entryId)}&user=${encodeURIComponent(devUser)}` as Route;
        router.replace(next);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    submitToApi(text);
  };

  const startEdit = () => {
    setDraft(text);
    setEditing(true);
  };

  const goToWeeklyPage = () => {
    window.location.href = `/experience/weekly?user=${encodeURIComponent(devUser)}`;
  };

  const saveEdit = () => {
    submitToApi(draft.trim() ? draft : text);
  };

  const typeAnother = () => {
    setEditing(false);
    setCaptured(false);
    setText("");
    setDraft("");
    setAck(null);
    setDebugData(null);
  };

  return (
    <div style={pageStyle}>
      <div style={outerStyle}>
        <div style={containerStyle}>
        <div style={brandStyle}>Sakhi</div>
          <div style={{ marginBottom: 12, color: palette.muted }}>Dev slot: {devLabel}</div>
          <div style={{ marginBottom: 16 }}>
            <select
              value={devUser}
              onChange={(e) => setDevUser(e.target.value === "b" ? "b" : "a")}
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
          <div style={promptStyle}>Prefer typing? Share what&apos;s on your mind.</div>

          {captured ? (
            <>
              <div style={mutedSmall}>I’m holding this.</div>
              <div style={{ ...mutedSmall, color: "#22c55e" }}>
                Recorded.
              </div>
              {editing ? (
                <textarea
                  style={textareaStyle}
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  aria-label="Edit captured note"
                />
              ) : (
                <div style={capturedCardStyle}>{text}</div>
              )}
              <div style={actionRowStyle}>
                {editing ? (
                  <button type="button" style={submitStyle} onClick={saveEdit} disabled={loading}>
                    {loading ? "Saving…" : "Done"}
                  </button>
                ) : (
                  <>
                    <button type="button" style={actionButtonStyle} onClick={startEdit}>
                      <span aria-hidden="true">✏️</span>
                      Edit
                    </button>
                    <Link href={`/experience/listening?user=${encodeURIComponent(devUser)}`} style={{ textDecoration: "none" }}>
                      <button type="button" style={actionButtonStyle}>
                        <span aria-hidden="true">🎙️</span>
                        Record instead
                      </button>
                    </Link>
                    <button type="button" style={actionButtonStyle} onClick={typeAnother}>
                      <span aria-hidden="true">📝</span>
                      Type another
                    </button>
                    <Link
                      href={
                        entryId
                          ? (`/experience/feedback?entry_id=${encodeURIComponent(entryId)}&user=${encodeURIComponent(devUser)}` as Route)
                          : "#"
                      }
                      style={{
                        ...actionButtonStyle,
                        textDecoration: "none",
                        pointerEvents: entryId ? "auto" : "none",
                        opacity: entryId ? 1 : 0.5,
                      }}
                    >
                      Feedback
                    </Link>
                  </>
                )}
              </div>
              <div style={navRowStyle}>
                <Link href={`/experience?user=${encodeURIComponent(devUser)}`} style={{ ...actionButtonStyle, textDecoration: "none" }}>
                  <span aria-hidden="true">🏠</span>
                  Home
                </Link>
              </div>
            </>
          ) : (
            <form onSubmit={handleSubmit}>
              <textarea
                style={textareaStyle}
                placeholder="What’s been on your mind lately?"
                aria-label="What’s been on your mind lately?"
                value={text}
                onChange={(e) => setText(e.target.value)}
              />
              <button type="submit" style={submitStyle} disabled={loading}>
                {loading ? "Submitting…" : "Submit"}
              </button>
            </form>
          )}
          {error && <div style={errorStyle}>{error}</div>}
          <div style={safetyStyle}>Only you and Sakhi see this.</div>
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
                <button type="button" style={{ ...submitStyle, padding: "8px 14px", marginTop: 0 }} onClick={goToWeeklyPage}>
                  View weekly page
                </button>
                <button type="button" style={{ ...submitStyle, padding: "8px 14px", marginTop: 0 }} onClick={fetchWeekly} disabled={weeklyLoading}>
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
