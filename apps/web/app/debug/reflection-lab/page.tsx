"use client";

import { useMemo, useState } from "react";

type Reflection = {
  overview?: string;
  recovery?: string;
  changes?: string;
  body?: string;
  mind?: string;
  emotion?: string;
  energy?: string;
  work?: string;
  confidence_note?: string;
  window?: string;
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
  checklist?: ChecklistItem[];
  manual_checklist?: ManualChecklist;
};

type ChecklistItem = { label: string; passed: boolean };
type ParsedJournal = { created_at: string; content: string };

type ManualChecklist = {
  body: "present" | "missing" | "overreach" | "";
  emotion: "present" | "missing" | "overreach" | "";
  energy: "present" | "missing" | "overreach" | "";
  work: "present" | "missing" | "overreach" | "";
  mind: "present" | "missing" | "overreach" | "";
  invented_experience: boolean;
  advice_slipped: boolean;
  identity_language: boolean;
  overconfidence: boolean;
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
  user: "a",
  weekStart: "",
  manual_checklist: {
    body: "",
    emotion: "",
    energy: "",
    work: "",
    mind: "",
    invented_experience: false,
    advice_slipped: false,
    identity_language: false,
    overconfidence: false,
  },
};

function extractReflection(payload: any): Reflection | undefined {
  if (!payload) return undefined;
  const pick = (candidate: any) => {
    if (!candidate || typeof candidate !== "object") return undefined;
    const ref = candidate.reflection || candidate;
    if (!ref) return undefined;
    return {
      overview: ref.overview ?? ref.highlights ?? "",
      recovery: ref.recovery ?? "",
      changes: ref.changes ?? "",
      body: ref.body ?? "",
      mind: ref.mind ?? "",
      emotion: ref.emotion ?? "",
      energy: ref.energy ?? "",
      work: ref.work ?? "",
      confidence_note: ref.confidence_note ?? "",
      window: ref.window ?? candidate.window ?? "",
    };
  };
  if (payload.reflection) return pick(payload);
  if (Array.isArray(payload.weekly) && payload.weekly.length > 0) return pick(payload.weekly[0]);
  if (payload.weekly) return pick(payload.weekly);
  return pick(payload);
}

function buildChecklist(expected: any, actual: Reflection | undefined): ChecklistItem[] {
  const items: ChecklistItem[] = [];
  const exp = typeof expected === "object" && expected !== null ? expected : {};
  const actualText = (field: keyof Reflection) => (actual?.[field] || "").toLowerCase();

  const addFieldCheck = (field: keyof Reflection, label: string) => {
    const expVal = (exp as any)?.[field];
    if (!expVal) {
      // Presence check only
      items.push({ label, passed: Boolean(actual?.[field]?.trim()) });
    } else {
      const expectedLower = String(expVal).toLowerCase();
      items.push({ label, passed: actualText(field).includes(expectedLower) });
    }
  };

  addFieldCheck("overview", "Overview present / matches expectation");
  addFieldCheck("body", "Body covered");
  addFieldCheck("emotion", "Emotion covered");
  addFieldCheck("energy", "Energy covered");
  addFieldCheck("work", "Work covered");
  addFieldCheck("mind", "Mind (if expected)");
  return items;
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

function manualStatus(scenario: Scenario): "PASS" | "FAIL" | null {
  const mc = scenario.manual_checklist;
  if (!mc) return null;
  const dims = ["body", "emotion", "energy", "work", "mind"] as const;
  if (dims.some((d) => mc[d] === "missing" || mc[d] === "overreach")) return "FAIL";
  if (mc.invented_experience || mc.advice_slipped || mc.identity_language || mc.overconfidence) return "FAIL";
  return "PASS";
}

export default function ReflectionLabPage() {
  const [scenarios, setScenarios] = useState<Scenario[]>([defaultScenario]);
  const [runAllLoading, setRunAllLoading] = useState(false);

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
      let expectedParsed: any = {};
      try {
        expectedParsed = scenario.expected_reflection ? JSON.parse(scenario.expected_reflection) : {};
      } catch {
        expectedParsed = {};
      }
      const checklist = buildChecklist(expectedParsed, reflection);
      updateScenario(scenario.id, {
        result: reflection,
        raw: data,
        checklist,
        last_run_at: new Date().toISOString(),
        last_result: checklist.every((c) => c.passed) ? "pass" : "fail",
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
            {scenarios.map(
              (scenario) =>
                scenario.result && (
                  <div key={`${scenario.id}-out`} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                    <div style={cardStyle}>
                      <div style={labelStyle}>
                        Panel 1 — Generated Reflection {scenario.last_run_at ? `(last run: ${scenario.last_run_at})` : ""}
                        {scenario.last_result ? ` • ${scenario.last_result}` : ""}
                        {manualStatus(scenario) ? ` • ${manualStatus(scenario)}` : ""}
                      </div>
                      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                        <div>
                          <div style={labelStyle}>Overview</div>
                          <div style={textareaStyle}>{scenario.result.overview || ""}</div>
                        </div>
                        <div>
                          <div style={labelStyle}>Confidence</div>
                          <div style={textareaStyle}>{scenario.result.confidence_note || ""}</div>
                        </div>
                        <div>
                          <div style={labelStyle}>Body</div>
                          <div style={textareaStyle}>{scenario.result.body || ""}</div>
                        </div>
                        <div>
                          <div style={labelStyle}>Emotion</div>
                          <div style={textareaStyle}>{scenario.result.emotion || ""}</div>
                        </div>
                        <div>
                          <div style={labelStyle}>Energy</div>
                          <div style={textareaStyle}>{scenario.result.energy || ""}</div>
                        </div>
                        <div>
                          <div style={labelStyle}>Work</div>
                          <div style={textareaStyle}>{scenario.result.work || ""}</div>
                        </div>
                        <div>
                          <div style={labelStyle}>Mind</div>
                          <div style={textareaStyle}>{scenario.result.mind || ""}</div>
                        </div>
                      </div>
                    </div>

                    <div style={cardStyle}>
                      <div style={labelStyle}>Panel 2 — Expected Reflection (read-only)</div>
                      <pre style={{ ...textareaStyle, minHeight: 120, whiteSpace: "pre-wrap" }}>
                        {scenario.expected_reflection || ""}
                      </pre>
                    </div>

                    <div style={cardStyle}>
                      <div style={labelStyle}>Panel 3 — Checklist (expected vs generated)</div>
                      <ul style={{ listStyle: "none", padding: 0, margin: "8px 0" }}>
                        {scenario.checklist?.map((item) => (
                          <li key={item.label} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13 }}>
                            <span style={{ color: item.passed ? "#15803d" : "#b91c1c" }}>
                              {item.passed ? "✔" : "✖"}
                            </span>
                            <span>{item.label}</span>
                          </li>
                        ))}
                      </ul>
                      <div style={{ marginTop: 8, display: "flex", flexDirection: "column", gap: 6 }}>
                        <div style={{ fontSize: 13, fontWeight: 600, color: "#111827" }}>Manual checklist</div>
                        {"body,emotion,energy,work,mind".split(",").map((dim) => (
                          <div key={dim} style={{ display: "flex", gap: 8, alignItems: "center", fontSize: 13 }}>
                            <div style={{ width: 60, textTransform: "capitalize" }}>{dim}</div>
                            {"present,missing,overreach".split(",").map((status) => (
                              <label key={status} style={{ display: "flex", alignItems: "center", gap: 4 }}>
                                <input
                                  type="radio"
                                  name={`${scenario.id}-${dim}`}
                                  checked={scenario.manual_checklist?.[dim as keyof ManualChecklist] === status}
                                  onChange={() => {
                                    const base: ManualChecklist =
                                      (scenario.manual_checklist || defaultScenario.manual_checklist) as ManualChecklist;
                                    updateScenario(scenario.id, {
                                      manual_checklist: {
                                        ...base,
                                        [dim]: status as ManualChecklist[keyof ManualChecklist],
                                      } as ManualChecklist,
                                    });
                                  }}
                                />
                                <span>{status}</span>
                              </label>
                            ))}
                          </div>
                        ))}
                        <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 8 }}>
                          {["invented_experience", "advice_slipped", "identity_language", "overconfidence"].map((key) => (
                            <label key={key} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13 }}>
                              <input
                                type="checkbox"
                                checked={Boolean(scenario.manual_checklist?.[key as keyof ManualChecklist])}
                                onChange={(e) =>
                                  updateScenario(scenario.id, {
                                    manual_checklist: {
                                      ...(scenario.manual_checklist || defaultScenario.manual_checklist),
                                      [key]: e.target.checked,
                                    } as ManualChecklist,
                                  })
                                }
                              />
                              <span>{
                                key === "invented_experience"
                                  ? "Invented experience"
                                  : key === "advice_slipped"
                                    ? "Advice slipped in"
                                    : key === "identity_language"
                                      ? "Identity language"
                                      : "Overconfidence given low signals"
                              }</span>
                            </label>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                ),
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
