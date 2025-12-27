"use client";

import { useMemo, useState } from "react";
import { getApiBase } from "@/lib/api-base";

type Reflection = {
  text?: string;
  confidence_note?: string;
};

type Scenario = {
  // Frontend-only scenario model (does not replace backend test cases)
  id: string;
  scenario_name: string;
  notes: string;
  journal_input: string; // multiline pasted journals
  expected_reflection: string; // JSON or structured text
  last_run_at: string | null;
  last_result: "pass" | "fail" | null;
  user: string;
  weekStart?: string;
  running?: boolean;
  parsed_journals?: ParsedJournal[] | null;
  parse_error?: string | null;
  result?: Reflection;
  raw?: any;
  error?: string | null;
  eval?: EvalNotes;
  snapshot?: Snapshot | null;
};
type ParsedJournal = { created_at: string; content: string };

type EvalNotes = {
  grounded?: boolean;
  no_invention?: boolean;
  no_advice?: boolean;
  caring_witness?: boolean;
  emotional_shape?: boolean;
  off_notes?: string;
};

type Snapshot = {
  journals: Array<{ id: string; text: string; full_text: string; layer?: string; mood?: string; tags?: any[]; created_at?: string }>;
  short_term_memory: Array<{ id: string; text?: string; tags?: any[]; created_at?: string }>;
  episodic_memory: Array<{ id: string; text?: string; tags?: any[]; layer?: string; created_at?: string }>;
  personal_model: { updated_at?: string; long_term?: any } | any;
  planner_summary?: any;
  rhythm_state?: any;
  rhythm_curve?: any;
  soul_summary?: any;
  memory_weekly?: any;
  memory_monthly?: any;
};

const palette = {
  bg: "#0e0f12",
  card: "#141518",
  border: "#1f2937",
  text: "#e5e7eb",
  muted: "#9ca3af",
  accent: "#22d3ee",
};

const cardStyle: React.CSSProperties = {
  border: `1px solid ${palette.border}`,
  borderRadius: 10,
  padding: 14,
  background: palette.card,
  color: palette.text,
  display: "flex",
  flexDirection: "column",
  gap: 8,
};

const labelStyle: React.CSSProperties = {
  fontSize: 12,
  color: palette.muted,
  letterSpacing: "0.02em",
};

const API_BASE = getApiBase();

function formatTimestamp(value?: string) {
  if (!value) return "Unknown";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

function toDisplay(value: any): string {
  if (value == null) return "";
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") return String(value);
  if (Array.isArray(value)) return value.map((item) => toDisplay(item)).filter(Boolean).join(", ");
  if (typeof value === "object") {
    if ("text" in value && typeof (value as any).text === "string") return (value as any).text;
    return JSON.stringify(value);
  }
  return "";
}

const inputStyle: React.CSSProperties = {
  width: "100%",
  padding: "8px 10px",
  borderRadius: 8,
  border: `1px solid ${palette.border}`,
  background: palette.bg,
  color: palette.text,
  fontSize: 13,
};

const textareaStyle: React.CSSProperties = {
  ...inputStyle,
  minHeight: 96,
  fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
};

const buttonStyle: React.CSSProperties = {
  padding: "10px 14px",
  borderRadius: 8,
  border: `1px solid ${palette.border}`,
  background: palette.accent,
  color: "#0b1220",
  fontSize: 13,
  cursor: "pointer",
};

const secondaryButtonStyle: React.CSSProperties = {
  ...buttonStyle,
  background: "transparent",
  color: palette.text,
};

const defaultScenario: Scenario = {
  id: crypto.randomUUID(),
  scenario_name: "Scenario A",
  notes: "",
  journal_input:
    "2024-03-18 | Felt bloated in the evening\n2024-03-19 | Work felt heavy and fragmented\n2024-03-20 | Played badminton with family\n2024-03-21 | Happy about progress on the startup plan",
  expected_reflection:
    "{\n  \"overview\": \"Work pressure with light family moments\",\n  \"body\": \"Some discomfort showed up\",\n  \"emotion\": \"Family time lifted the mood\",\n  \"energy\": \"Energy mixed / up and down\",\n  \"work\": \"Pressure and fragmentation\"\n}",
  last_run_at: null,
  last_result: null,
  user: "c10fbd98-25fa-4445-8aba-e5243bc01564",
  weekStart: "",
  eval: {},
};

function extractReflection(payload: any): Reflection | undefined {
  if (!payload) return undefined;
  const pick = (candidate: any) => {
    if (!candidate || typeof candidate !== "object") return undefined;
    const ref = candidate.reflection || candidate;
    if (!ref) return undefined;
    return {
      text:
        ref.text ??
        ref.overview ??
        ref.highlights ??
        [
          ref.body,
          ref.emotion,
          ref.energy,
          ref.work,
          ref.mind,
          ref.recovery,
          ref.changes,
        ]
          .filter(Boolean)
          .join("\n\n"),
      confidence_note: ref.confidence_note ?? "",
    };
  };
  if (payload.reflection) return pick(payload);
  if (Array.isArray(payload.weekly) && payload.weekly.length > 0) return pick(payload.weekly[0]);
  if (payload.weekly) return pick(payload.weekly);
  return pick(payload);
}

function parseJournalInput(input: string): ParsedJournal[] {
  const rawLines = input.split("\n").map((l) => l.trim());
  const entries: ParsedJournal[] = [];
  const dateRegex = /^(\d{4}-\d{2}-\d{2})(?:\s*[:|]\s*(.*))?$/; // accept "YYYY-MM-DD: text", "YYYY-MM-DD | text", or multiline starting with date

  let currentDate: string | null = null;
  let buffer: string[] = [];

  const flush = () => {
    if (!currentDate) return;
    const content = buffer.join(" ").trim();
    entries.push({ created_at: new Date(currentDate).toISOString(), content });
    currentDate = null;
    buffer = [];
  };

  for (const line of rawLines) {
    if (!line) {
      // blank line: end current entry
      flush();
      continue;
    }
    const match = dateRegex.exec(line);
    if (match) {
      // starting a new entry; flush previous if any
      flush();
      const [, dateStr, firstContent] = match;
      const dateObj = new Date(dateStr);
      if (Number.isNaN(dateObj.getTime())) {
        throw new Error(`Invalid date: "${dateStr}"`);
      }
      currentDate = dateStr;
      if (firstContent && firstContent.trim()) {
        buffer.push(firstContent.trim());
      }
      continue;
    }
    if (!currentDate) {
      throw new Error(`Invalid line (expected YYYY-MM-DD start): "${line}"`);
    }
    buffer.push(line);
  }
  flush();

  if (entries.length > 0) {
    const timestamps = entries.map((e) => new Date(e.created_at).getTime());
    const minTs = Math.min(...timestamps);
    const maxTs = Math.max(...timestamps);
    const diffDays = Math.abs(maxTs - minTs) / (1000 * 60 * 60 * 24);
    if (diffDays > 7) {
      throw new Error("Journals span more than one week");
    }
  }
  return entries;
}

export default function ReflectionLabPage() {
  const [scenarios, setScenarios] = useState<Scenario[]>([defaultScenario]);
  const [runAllLoading, setRunAllLoading] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [resetMessage, setResetMessage] = useState<string | null>(null);
  const [resetError, setResetError] = useState<string | null>(null);
  const [snapshotLoading, setSnapshotLoading] = useState(false);
  const [snapshotError, setSnapshotError] = useState<string | null>(null);

  const updateScenario = (id: string, updates: Partial<Scenario>) => {
    setScenarios((prev) => prev.map((s) => (s.id === id ? { ...s, ...updates } : s)));
  };

  const addScenario = () => {
    setScenarios((prev) => [
      ...prev,
      {
        ...defaultScenario,
        id: crypto.randomUUID(),
        scenario_name: `Scenario ${String.fromCharCode(65 + prev.length)}`,
      },
    ]);
  };

  const removeScenario = (id: string) => {
    setScenarios((prev) => prev.filter((s) => s.id !== id));
  };

  const runScenario = async (scenario: Scenario) => {
    let parsed: ParsedJournal[] = [];
    try {
      parsed = parseJournalInput(scenario.journal_input || "");
      updateScenario(scenario.id, { parsed_journals: parsed, parse_error: null });
    } catch (parseErr: any) {
      updateScenario(scenario.id, { parse_error: parseErr?.message || "Invalid journal input", parsed_journals: null });
      return;
    }

    updateScenario(scenario.id, { running: true, error: null });
    try {
      // Prefer explicit weekStart; otherwise derive from earliest parsed journal date.
      let weekToUse = scenario.weekStart;
      if (!weekToUse && parsed.length) {
        const minDate = parsed
          .map((p) => new Date(p.created_at))
          .reduce((a, b) => (a.getTime() <= b.getTime() ? a : b));
        const monday = new Date(minDate);
        monday.setUTCDate(minDate.getUTCDay() === 0 ? minDate.getUTCDate() - 6 : minDate.getUTCDate() - (minDate.getUTCDay() - 1));
        weekToUse = monday.toISOString().slice(0, 10);
      }

      const payload = {
        user: scenario.user || "a",
        week_start: weekToUse,
        journals: parsed.map((p) => ({
          content: p.content,
          created_at: p.created_at,
        })),
      };
      const res = await fetch("/api/memory/dev/weekly/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const text = await res.text();
      const data = text ? JSON.parse(text) : {};
      if (!res.ok) {
        throw new Error((data && data.error) || res.statusText || "Failed to run weekly reflection");
      }
      const reflection = extractReflection(data);
      updateScenario(scenario.id, {
        result: reflection,
        raw: data,
        last_run_at: new Date().toISOString(),
        last_result: reflection?.text ? "pass" : "fail",
        parsed_journals: parsed,
      });
    } catch (err: any) {
      updateScenario(scenario.id, { error: err?.message || "Failed to run scenario" });
    } finally {
      updateScenario(scenario.id, { running: false });
    }
  };

  const runAll = async () => {
    setRunAllLoading(true);
    for (const scenario of scenarios) {
      // Run sequentially to avoid overwhelming the API.
      // eslint-disable-next-line no-await-in-loop
      await runScenario(scenario);
    }
    setRunAllLoading(false);
  };

  const loadSnapshot = async () => {
    const targetUser = scenarios[0]?.user || "a";
    setSnapshotLoading(true);
    setSnapshotError(null);
    try {
      const res = await fetch(`/api/debug/full_snapshot?person_id=${encodeURIComponent(targetUser)}&prime=true`);
      const data = await res.json();
      if (!res.ok || data?.error) {
        throw new Error(data?.error || res.statusText || "Failed to load snapshot");
      }
      setScenarios((prev) => prev.map((s, idx) => (idx === 0 ? { ...s, snapshot: data } : s)));
    } catch (err: any) {
      setSnapshotError(err?.message || "Failed to load snapshot");
    } finally {
      setSnapshotLoading(false);
    }
  };

  const resetData = async () => {
    const targetUser = scenarios[0]?.user || "a";
    const targetWeek = scenarios[0]?.weekStart;
    let startDate = targetWeek;
    let endDate = targetWeek;

    // Derive a week window from pasted journals if weekStart is empty.
    if (!startDate && scenarios[0]?.parsed_journals?.length) {
      const minDate = scenarios[0].parsed_journals
        .map((p) => new Date(p.created_at))
        .reduce((a, b) => (a.getTime() <= b.getTime() ? a : b));
      startDate = minDate.toISOString().slice(0, 10);
      const end = new Date(minDate);
      end.setUTCDate(minDate.getUTCDate() + 6);
      endDate = end.toISOString().slice(0, 10);
    }

    if (!startDate) {
      setResetError("Set Week start or paste journals so we can derive a window before resetting.");
      return;
    }

    const confirmed = window.confirm(
      `Reset data for user "${targetUser}" between ${startDate} and ${endDate || startDate}? This deletes journals and weekly artifacts for that window.`,
    );
    if (!confirmed) return;
    setResetting(true);
    setResetError(null);
    setResetMessage(null);
    try {
      const res = await fetch("/api/memory/dev/reset", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user: targetUser, start_date: startDate, end_date: endDate }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data?.error || res.statusText || "Reset failed");
      }
      setResetMessage(`Reset complete for user ${targetUser} (${startDate} → ${endDate || startDate}).`);
      // Clear any cached results in the UI.
      setScenarios((prev) =>
        prev.map((s) => ({
          ...s,
          result: undefined,
          last_run_at: null,
          last_result: null,
          parsed_journals: null,
          error: null,
          parse_error: null,
        })),
      );
    } catch (err: any) {
      setResetError(err?.message || "Reset failed");
    } finally {
      setResetting(false);
    }
  };

  const warningBanner = (
    <div
      style={{
        background: "#312e81",
        color: "#e0e7ff",
        padding: 10,
        border: "1px solid #4338ca",
        borderRadius: 8,
        textAlign: "center",
      }}
    >
      Internal Evaluation Tool
    </div>
  );

  const header = useMemo(
    () => (
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        <div style={{ fontSize: 12, letterSpacing: "0.06em", textTransform: "uppercase", color: "#4b5563" }}>
          Reflection Lab UI (Weekly Reflection Regression Suite)
        </div>
      </div>
    ),
    [],
  );

  return (
    <div style={{ minHeight: "100vh", background: palette.bg, padding: 16, color: palette.text, fontFamily: 'Inter, system-ui, -apple-system, sans-serif' }}>
      <div style={{ maxWidth: 1200, margin: "0 auto", display: "flex", flexDirection: "column", gap: 12 }}>
        {warningBanner}
        {header}
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <button style={buttonStyle} onClick={runAll} disabled={runAllLoading}>
            {runAllLoading ? "Running..." : "Run all scenarios"}
          </button>
          <button style={secondaryButtonStyle} onClick={addScenario}>
            Add scenario
          </button>
          <button
            style={{ ...secondaryButtonStyle, borderColor: "#b91c1c", color: "#fca5a5" }}
            onClick={resetData}
            disabled={resetting}
          >
            {resetting ? "Resetting..." : "Reset user data"}
          </button>
          <button
            style={{ ...secondaryButtonStyle, borderColor: "#10b981", color: "#34d399" }}
            onClick={loadSnapshot}
            disabled={snapshotLoading}
          >
            {snapshotLoading ? "Loading snapshot..." : "Load snapshot"}
          </button>
          {(resetMessage || resetError) && (
            <span style={{ color: resetError ? "#f87171" : "#4ade80", fontSize: 13 }}>
              {resetError || resetMessage}
            </span>
          )}
          {snapshotError && <span style={{ color: "#f87171", fontSize: 13 }}>{snapshotError}</span>}
        </div>
        <div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
          <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 12 }}>
            {scenarios.map((scenario) => (
              <div key={scenario.id} style={cardStyle}>
                <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                  <input
                    style={{ ...inputStyle, maxWidth: 200 }}
                  value={scenario.scenario_name}
                  onChange={(e) => updateScenario(scenario.id, { scenario_name: e.target.value })}
                  placeholder="Scenario name"
                />
                  <input
                    style={{ ...inputStyle, maxWidth: 200 }}
                    value={scenario.user}
                    onChange={(e) => updateScenario(scenario.id, { user: e.target.value })}
                    placeholder="User (person id or dev key)"
                  />
                  <input
                    style={{ ...inputStyle, maxWidth: 200 }}
                    value={scenario.weekStart || ""}
                    onChange={(e) => updateScenario(scenario.id, { weekStart: e.target.value })}
                    placeholder="Week start (YYYY-MM-DD)"
                  />
                  <button
                    style={secondaryButtonStyle}
                    onClick={() => removeScenario(scenario.id)}
                    disabled={scenarios.length === 1}
                  >
                    Remove
                  </button>
                </div>
                <div>
                  <div style={labelStyle}>Journals (paste with dates for reference)</div>
                  <textarea
                    style={textareaStyle}
                    value={scenario.journal_input}
                    onChange={(e) => updateScenario(scenario.id, { journal_input: e.target.value })}
                  />
                </div>
                <div>
                  <div style={labelStyle}>Expected reflection (JSON or plain text)</div>
                  <textarea
                    style={textareaStyle}
                    value={scenario.expected_reflection}
                    onChange={(e) => updateScenario(scenario.id, { expected_reflection: e.target.value })}
                  />
                </div>
                <div>
                  <div style={labelStyle}>Notes</div>
                  <textarea
                    style={textareaStyle}
                    value={scenario.notes}
                    onChange={(e) => updateScenario(scenario.id, { notes: e.target.value })}
                  />
                </div>
                <div style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 4 }}>
                  <button style={buttonStyle} onClick={() => runScenario(scenario)} disabled={scenario.running}>
                    {scenario.running ? "Running..." : "Run scenario"}
                  </button>
                  {scenario.parse_error && <span style={{ color: "#b91c1c", fontSize: 13 }}>{scenario.parse_error}</span>}
                  {scenario.error && <span style={{ color: "#b91c1c", fontSize: 13 }}>{scenario.error}</span>}
                </div>
              </div>
            ))}
          </div>
          <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 12 }}>
            {scenarios.map((scenario) => {
              if (!scenario.result && !scenario.snapshot) return null;
              return (
                <div key={`${scenario.id}-out`} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                  {scenario.result && (
                    <>
                      <div style={cardStyle}>
                        <div style={{ ...labelStyle, fontSize: 13 }}>
                          Generated Reflection {scenario.last_run_at ? `(last run: ${scenario.last_run_at})` : ""}
                          {scenario.last_result ? ` • ${scenario.last_result}` : ""}
                        </div>
                        <div style={{ ...textareaStyle, whiteSpace: "pre-wrap" }}>
                          {scenario.result.text || ""}
                          {scenario.result.confidence_note ? (
                            <div style={{ marginTop: 8, color: "#9ca3af", fontSize: 12 }}>
                              {scenario.result.confidence_note}
                            </div>
                          ) : null}
                        </div>
                      </div>

                      <div style={cardStyle}>
                        <div style={labelStyle}>Expected Reflection (read-only)</div>
                        <pre style={{ ...textareaStyle, minHeight: 120, whiteSpace: "pre-wrap" }}>
                          {scenario.expected_reflection || ""}
                        </pre>
                      </div>

                      <div style={cardStyle}>
                        <div style={labelStyle}>Evaluation (internal)</div>
                        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                          {[
                            { key: "grounded", label: "Feels grounded in my week" },
                            { key: "no_invention", label: "No invention" },
                            { key: "no_advice", label: "No advice" },
                            { key: "caring_witness", label: "Feels like a caring witness" },
                            { key: "emotional_shape", label: "Emotional shape feels right" },
                          ].map((item) => (
                            <label key={item.key} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13 }}>
                              <input
                                type="checkbox"
                                checked={Boolean(scenario.eval?.[item.key as keyof EvalNotes])}
                                onChange={(e) =>
                                  updateScenario(scenario.id, {
                                    eval: { ...(scenario.eval || {}), [item.key]: e.target.checked },
                                  })
                                }
                              />
                              <span>{item.label}</span>
                            </label>
                          ))}
                          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                            <div style={labelStyle}>What felt off?</div>
                            <textarea
                              style={textareaStyle}
                              value={scenario.eval?.off_notes || ""}
                              onChange={(e) => updateScenario(scenario.id, { eval: { ...(scenario.eval || {}), off_notes: e.target.value } })}
                              placeholder="Optional notes"
                            />
                          </div>
                        </div>
                      </div>

                      <div style={cardStyle}>
                        <div style={labelStyle}>Debug (local only)</div>
                        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                          <div>
                            <div style={labelStyle}>Selected episodes</div>
                            <ul style={{ paddingLeft: 16, margin: "4px 0", color: palette.muted }}>
                              {(scenario.parsed_journals || []).slice(0, 6).map((j, idx) => (
                                <li key={`${scenario.id}-j-${idx}`} style={{ marginBottom: 4 }}>
                                  {j.content}
                                </li>
                              ))}
                              {!(scenario.parsed_journals || []).length && <li>None</li>}
                            </ul>
                          </div>
                          <div>
                            <div style={labelStyle}>Raw payload (truncated)</div>
                            <pre style={{ ...textareaStyle, maxHeight: 200, overflow: "auto", whiteSpace: "pre-wrap" }}>
                              {JSON.stringify(scenario.raw?.debug || scenario.raw?.reflection || scenario.result, null, 2)}
                            </pre>
                          </div>
                        </div>
                      </div>
                    </>
                  )}

                  {scenario.snapshot && (
                    <div style={cardStyle}>
                      <div style={{ ...labelStyle, fontSize: 13 }}>
                        Person Snapshot (debug/person_snapshot) {scenario.snapshot.warnings?.length ? `• warnings: ${scenario.snapshot.warnings.join(", ")}` : ""}
                      </div>
                      {snapshotLoading && <div style={{ color: palette.muted }}>Loading snapshot…</div>}
                      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                        <div>
                          <div style={labelStyle}>Planner summary</div>
                          <pre style={{ ...textareaStyle, maxHeight: 180, overflow: "auto", whiteSpace: "pre-wrap" }}>
                            {JSON.stringify(scenario.snapshot.planner_summary || {}, null, 2)}
                          </pre>
                        </div>
                        <div>
                          <div style={labelStyle}>Rhythm state / curve</div>
                          <pre style={{ ...textareaStyle, maxHeight: 180, overflow: "auto", whiteSpace: "pre-wrap" }}>
                            {JSON.stringify({ state: scenario.snapshot.rhythm_state, curve: scenario.snapshot.rhythm_curve }, null, 2)}
                          </pre>
                        </div>
                        <div>
                          <div style={labelStyle}>Soul summary</div>
                          <pre style={{ ...textareaStyle, maxHeight: 180, overflow: "auto", whiteSpace: "pre-wrap" }}>
                            {JSON.stringify(scenario.snapshot.soul_summary || {}, null, 2)}
                          </pre>
                        </div>
                        <div style={{ display: "grid", gap: 8, gridTemplateColumns: "repeat(auto-fit,minmax(240px,1fr))" }}>
                          <div>
                            <div style={labelStyle}>Weekly memory</div>
                            <pre style={{ ...textareaStyle, maxHeight: 180, overflow: "auto", whiteSpace: "pre-wrap" }}>
                              {JSON.stringify(scenario.snapshot.memory_weekly || {}, null, 2)}
                            </pre>
                          </div>
                          <div>
                            <div style={labelStyle}>Monthly memory</div>
                            <pre style={{ ...textareaStyle, maxHeight: 180, overflow: "auto", whiteSpace: "pre-wrap" }}>
                              {JSON.stringify(scenario.snapshot.memory_monthly || {}, null, 2)}
                            </pre>
                          </div>
                        </div>
                        <div>
                          <div style={labelStyle}>Recent journals</div>
                          {scenario.snapshot.journals?.length ? (
                            <ul style={{ display: "grid", gap: 6, paddingLeft: 0, listStyle: "none" }}>
                              {scenario.snapshot.journals.map((j) => (
                                <li key={j.id} style={{ padding: 8, border: `1px solid ${palette.border}`, borderRadius: 8 }}>
                                  <div style={{ fontSize: 12, color: palette.muted }}>
                                    {formatTimestamp(j.created_at)} • {toDisplay(j.layer || "journal")}
                                  </div>
                                  <div style={{ marginTop: 4 }}>{toDisplay(j.text)}</div>
                                  <div style={{ fontSize: 12, color: palette.muted }}>
                                    {j.mood ? `Mood: ${toDisplay(j.mood)}` : null}
                                    {j.tags?.length ? ` • Tags: ${j.tags.map(toDisplay).join(", ")}` : ""}
                                  </div>
                                </li>
                              ))}
                            </ul>
                          ) : (
                            <div style={{ color: palette.muted }}>None</div>
                          )}
                        </div>

                        <div>
                          <div style={labelStyle}>Short-term memory</div>
                          {scenario.snapshot.short_term_memory?.length ? (
                            <ul style={{ display: "grid", gap: 6, paddingLeft: 0, listStyle: "none" }}>
                              {scenario.snapshot.short_term_memory.map((m) => (
                                <li key={m.id} style={{ padding: 8, border: `1px solid ${palette.border}`, borderRadius: 8 }}>
                                  <div style={{ fontSize: 12, color: palette.muted }}>{formatTimestamp(m.created_at)}</div>
                                  <div>{toDisplay(m.text)}</div>
                                  {m.tags?.length ? <div style={{ fontSize: 12, color: palette.muted }}>Tags: {m.tags.map(toDisplay).join(", ")}</div> : null}
                                </li>
                              ))}
                            </ul>
                          ) : (
                            <div style={{ color: palette.muted }}>None</div>
                          )}
                        </div>

                        <div>
                          <div style={labelStyle}>Episodic memory</div>
                          {scenario.snapshot.episodic_memory?.length ? (
                            <ul style={{ display: "grid", gap: 6, paddingLeft: 0, listStyle: "none" }}>
                              {scenario.snapshot.episodic_memory.map((e) => (
                                <li key={e.id} style={{ padding: 8, border: `1px solid ${palette.border}`, borderRadius: 8 }}>
                                  <div style={{ fontSize: 12, color: palette.muted }}>
                                    {formatTimestamp(e.created_at)} • {toDisplay(e.layer || "episode")}
                                  </div>
                                  <div>{toDisplay(e.text)}</div>
                                  {e.tags?.length ? <div style={{ fontSize: 12, color: palette.muted }}>Tags: {e.tags.map(toDisplay).join(", ")}</div> : null}
                                </li>
                              ))}
                            </ul>
                          ) : (
                            <div style={{ color: palette.muted }}>None</div>
                          )}
                        </div>

                        <div>
                          <div style={labelStyle}>Personal model</div>
                          <div style={{ fontSize: 12, color: palette.muted }}>
                            Updated {formatTimestamp(scenario.snapshot.personal_model?.updated_at)}
                          </div>
                          <pre style={{ ...textareaStyle, maxHeight: 200, overflow: "auto", whiteSpace: "pre-wrap" }}>
                            {JSON.stringify(scenario.snapshot.personal_model?.long_term || {}, null, 2)}
                          </pre>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
