"use client";

import { useEffect, useMemo, useState } from "react";
import type { CSSProperties } from "react";
import Link from "next/link";

export const dynamic = "force-dynamic";

type AuthUser = {
  person_id: string;
  full_name?: string | null;
};

type ProtocolOption = {
  id: string;
  title: string;
  category: string;
  duration_minutes: number;
  related_dosha?: string | null;
  expected_effect: string;
  safety_note: string;
  steps: string[];
};

type CheckinResponse = {
  checkin_id: string;
  symptom: string;
  dosha_hint?: string | null;
  urgency: string;
  confidence: number;
  uncertainty: number;
  dosha_context?: string | null;
  explanation: string;
  evidence: Array<{
    factor_type: string;
    description: string;
    confidence: number;
    evidence?: string | null;
  }>;
  protocols: ProtocolOption[];
};

const palette = {
  bg: "#0e0f12",
  card: "#1a1b1e",
  border: "#2a2b30",
  fg: "#f4f4f5",
  muted: "#a1a1aa",
  accent: "#22c55e",
  accentSoft: "rgba(34, 197, 94, 0.14)",
  warning: "#f59e0b",
  danger: "#ef4444",
};

const symptomOptions = [
  "anxious",
  "scattered",
  "irritable",
  "sluggish",
  "overwhelmed",
];

export default function ExperienceCheckinPage() {
  const [authUser, setAuthUser] = useState<AuthUser | null>(null);
  const [authLoading, setAuthLoading] = useState(true);

  const [symptom, setSymptom] = useState("anxious");
  const [energy, setEnergy] = useState(0.5);
  const [note, setNote] = useState("");
  const [bodyCuesText, setBodyCuesText] = useState("");

  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<CheckinResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);

  useEffect(() => {
    const loadAuth = async () => {
      try {
        const res = await fetch("/api/auth/me");
        if (!res.ok) return;
        const data = await res.json();
        if (data?.person_id) {
          setAuthUser({ person_id: data.person_id, full_name: data.full_name });
        }
      } catch {
        // intentionally silent
      } finally {
        setAuthLoading(false);
      }
    };
    loadAuth();
  }, []);

  const bodyCues = useMemo(
    () =>
      bodyCuesText
        .split(",")
        .map((v) => v.trim())
        .filter(Boolean),
    [bodyCuesText]
  );

  const runCheckin = async () => {
    if (!authUser?.person_id || !symptom.trim()) return;

    setRunning(true);
    setError(null);
    setStatusMsg(null);
    setResult(null);
    try {
      const res = await fetch("/api/learning/companion/checkin", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          person_id: authUser.person_id,
          symptom: symptom.trim(),
          energy_level: energy,
          body_cues: bodyCues,
          note: note.trim() || undefined,
        }),
      });

      if (!res.ok) {
        const payload = await res.json().catch(() => ({}));
        throw new Error(payload?.detail || payload?.error || "Check-in failed");
      }

      const payload = (await res.json()) as CheckinResponse;
      setResult(payload);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Check-in failed");
    } finally {
      setRunning(false);
    }
  };

  const createFollowupPlan = async (protocol: ProtocolOption) => {
    if (!authUser?.person_id || !result) return;
    setStatusMsg(null);
    setError(null);
    try {
      const res = await fetch("/api/learning/companion/followup/plan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          person_id: authUser.person_id,
          symptom: result.symptom,
          protocol_id: protocol.id,
          target_days: 7,
          target_per_day: 1,
          checkin_id: result.checkin_id,
        }),
      });
      const payload = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(payload?.detail || payload?.error || "Failed to create plan");
      }
      setStatusMsg(`Tracking started: ${payload.intervention_name}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create follow-up plan");
    }
  };

  const markProtocolDone = async (protocol: ProtocolOption) => {
    if (!authUser?.person_id || !result) return;
    setStatusMsg(null);
    setError(null);
    try {
      const res = await fetch("/api/learning/companion/protocol/complete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          person_id: authUser.person_id,
          symptom: result.symptom,
          protocol_id: protocol.id,
          was_effective: true,
          effectiveness_score: 0.8,
        }),
      });
      const payload = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(payload?.detail || payload?.error || "Failed to log completion");
      }
      setStatusMsg(`Completion logged for ${protocol.title}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to log completion");
    }
  };

  return (
    <main style={styles.page}>
      <div style={styles.container}>
        <div style={styles.headerRow}>
          <div>
            <p style={styles.kicker}>Ayurvedic Companion</p>
            <h1 style={styles.title}>Quick Check-In</h1>
            <p style={styles.subtitle}>
              Find likely causes now and choose a 2, 5, or 10 minute action.
            </p>
          </div>
          <Link href="/experience" style={styles.backLink}>
            Back
          </Link>
        </div>

        {!authLoading && !authUser?.person_id && (
          <div style={{ ...styles.notice, borderColor: palette.warning }}>
            Sign in to use live check-ins.
          </div>
        )}

        <section style={styles.card}>
          <label style={styles.label}>What are you feeling?</label>
          <div style={styles.symptomRow}>
            {symptomOptions.map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => setSymptom(s)}
                style={{
                  ...styles.pill,
                  ...(symptom === s ? styles.pillActive : {}),
                }}
              >
                {s}
              </button>
            ))}
          </div>

          <label style={styles.label}>Energy: {Math.round(energy * 100)}%</label>
          <input
            type="range"
            min={0}
            max={1}
            step={0.05}
            value={energy}
            onChange={(e) => setEnergy(Number(e.target.value))}
            style={{ width: "100%" }}
          />

          <label style={styles.label}>Body cues (optional, comma separated)</label>
          <input
            type="text"
            value={bodyCuesText}
            onChange={(e) => setBodyCuesText(e.target.value)}
            placeholder="dry mouth, heavy chest, shallow breath"
            style={styles.input}
          />

          <label style={styles.label}>Note (optional)</label>
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            rows={3}
            style={styles.textarea}
            placeholder="What happened before this feeling started?"
          />

          <button
            type="button"
            disabled={running || !authUser?.person_id}
            onClick={runCheckin}
            style={running ? styles.ctaDisabled : styles.cta}
          >
            {running ? "Analyzing..." : "Understand This Moment"}
          </button>
        </section>

        {error && <div style={{ ...styles.notice, borderColor: palette.danger }}>{error}</div>}
        {statusMsg && <div style={{ ...styles.notice, borderColor: palette.accent }}>{statusMsg}</div>}

        {result && (
          <>
            <section style={styles.card}>
              <h2 style={styles.sectionTitle}>Why This Might Be Happening</h2>
              <p style={styles.explanation}>{result.explanation}</p>
              <div style={styles.metrics}>
                <span>Dosha: {result.dosha_hint || "unknown"}</span>
                <span>Confidence: {Math.round(result.confidence * 100)}%</span>
                <span>Uncertainty: {Math.round(result.uncertainty * 100)}%</span>
              </div>
              {result.dosha_context && (
                <p style={styles.context}>Context: {result.dosha_context}</p>
              )}
              {result.evidence?.length > 0 && (
                <div style={styles.evidenceList}>
                  {result.evidence.map((item, idx) => (
                    <div key={`${item.description}-${idx}`} style={styles.evidenceItem}>
                      <strong>{Math.round(item.confidence * 100)}%</strong> {item.description}
                    </div>
                  ))}
                </div>
              )}
            </section>

            <section style={styles.card}>
              <h2 style={styles.sectionTitle}>Choose Your Protocol</h2>
              <div style={styles.protocolList}>
                {result.protocols.map((protocol) => (
                  <article key={protocol.id} style={styles.protocolCard}>
                    <div style={styles.protocolHeader}>
                      <h3 style={styles.protocolTitle}>{protocol.title}</h3>
                      <span style={styles.duration}>{protocol.duration_minutes}m</span>
                    </div>
                    <p style={styles.protocolEffect}>{protocol.expected_effect}</p>
                    <ul style={styles.stepList}>
                      {protocol.steps.map((step, idx) => (
                        <li key={`${protocol.id}-step-${idx}`}>{step}</li>
                      ))}
                    </ul>
                    <p style={styles.safety}>Safety: {protocol.safety_note}</p>
                    <div style={styles.protocolActions}>
                      <button type="button" style={styles.secondaryBtn} onClick={() => createFollowupPlan(protocol)}>
                        Track 7 Days
                      </button>
                      <button type="button" style={styles.secondaryBtn} onClick={() => markProtocolDone(protocol)}>
                        Mark Done
                      </button>
                    </div>
                  </article>
                ))}
              </div>
            </section>
          </>
        )}
      </div>
    </main>
  );
}

const styles: Record<string, CSSProperties> = {
  page: {
    minHeight: "100vh",
    background: palette.bg,
    color: palette.fg,
    padding: "32px 20px 48px",
  },
  container: {
    maxWidth: 780,
    margin: "0 auto",
    display: "grid",
    gap: 16,
  },
  headerRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "flex-start",
    gap: 12,
  },
  kicker: {
    margin: 0,
    color: palette.muted,
    letterSpacing: "0.08em",
    textTransform: "uppercase",
    fontSize: 12,
  },
  title: { margin: "6px 0 4px", fontSize: 28 },
  subtitle: { margin: 0, color: palette.muted, fontSize: 14 },
  backLink: { color: palette.muted, textDecoration: "underline", fontSize: 14 },
  card: {
    background: palette.card,
    border: `1px solid ${palette.border}`,
    borderRadius: 14,
    padding: 16,
    display: "grid",
    gap: 10,
  },
  label: { fontSize: 13, color: palette.muted },
  symptomRow: { display: "flex", flexWrap: "wrap", gap: 8 },
  pill: {
    padding: "8px 12px",
    borderRadius: 999,
    border: `1px solid ${palette.border}`,
    background: "transparent",
    color: palette.fg,
    cursor: "pointer",
  },
  pillActive: {
    borderColor: palette.accent,
    background: palette.accentSoft,
  },
  input: {
    borderRadius: 10,
    border: `1px solid ${palette.border}`,
    background: "#111216",
    color: palette.fg,
    padding: "10px 12px",
  },
  textarea: {
    borderRadius: 10,
    border: `1px solid ${palette.border}`,
    background: "#111216",
    color: palette.fg,
    padding: "10px 12px",
    resize: "vertical",
  },
  cta: {
    borderRadius: 10,
    border: `1px solid ${palette.accent}`,
    background: palette.accentSoft,
    color: palette.fg,
    fontWeight: 600,
    padding: "11px 14px",
    cursor: "pointer",
  },
  ctaDisabled: {
    borderRadius: 10,
    border: `1px solid ${palette.border}`,
    background: "#1c1d21",
    color: palette.muted,
    fontWeight: 600,
    padding: "11px 14px",
    cursor: "not-allowed",
  },
  notice: {
    border: `1px solid ${palette.border}`,
    borderRadius: 10,
    padding: "10px 12px",
    color: palette.fg,
  },
  sectionTitle: { margin: 0, fontSize: 18 },
  explanation: { margin: 0, color: palette.fg, lineHeight: 1.5 },
  metrics: {
    display: "flex",
    flexWrap: "wrap",
    gap: 12,
    color: palette.muted,
    fontSize: 13,
  },
  context: { margin: 0, color: palette.muted, fontSize: 13 },
  evidenceList: { display: "grid", gap: 6 },
  evidenceItem: {
    fontSize: 13,
    color: palette.fg,
    borderLeft: `2px solid ${palette.border}`,
    paddingLeft: 10,
  },
  protocolList: { display: "grid", gap: 10 },
  protocolCard: {
    border: `1px solid ${palette.border}`,
    borderRadius: 12,
    padding: 12,
    display: "grid",
    gap: 8,
    background: "#141519",
  },
  protocolHeader: { display: "flex", justifyContent: "space-between", gap: 8 },
  protocolTitle: { margin: 0, fontSize: 16 },
  duration: {
    color: palette.accent,
    fontSize: 12,
    border: `1px solid ${palette.accent}`,
    borderRadius: 999,
    padding: "2px 8px",
    alignSelf: "center",
  },
  protocolEffect: { margin: 0, color: palette.muted, fontSize: 13 },
  stepList: { margin: 0, paddingLeft: 18, color: palette.fg, fontSize: 13, lineHeight: 1.5 },
  safety: { margin: 0, color: palette.warning, fontSize: 12 },
  protocolActions: { display: "flex", flexWrap: "wrap", gap: 8 },
  secondaryBtn: {
    borderRadius: 9,
    border: `1px solid ${palette.border}`,
    background: "transparent",
    color: palette.fg,
    padding: "8px 10px",
    fontSize: 13,
    cursor: "pointer",
  },
};
