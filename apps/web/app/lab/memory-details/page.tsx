"use client";

import { useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { getApiBase } from "@/lib/api-base";

type MemoryDetails = {
  person_id: string;
  entry_id?: string | null;
  updated_at?: string;
  short_term: any[];
  episodic: any[];
  recalls: any[];
  embedding: any;
  context_cache: any;
  entry: any;
  narrative?: any;
  soul?: any;
  identity_momentum?: any;
  identity_momentum_v2?: any;
  rhythm?: any;
  rhythm_soul?: any;
  longitudinal?: any;
  emotion?: any;
  emotion_soul_rhythm?: any;
  decision_graph?: any;
  esr?: any;
  goals_themes?: any[];
  elemental_stm?: any[];
  elemental_weekly?: any[];
  elemental_monthly?: any[];
  personal_model_elemental?: any;
  energy_weekly?: any[];
  energy_monthly?: any[];
  personal_model_energy?: any;
};

const palette = {
  // Softer, airy palette inspired by pickle.com/os
  bg: "#f6f4f0",
  card: "#ffffff",
  border: "#dcd8d0",
  text: "#1f2a33",
  muted: "#6f7b83",
  accent: "#1f8a70",
  surface: "#eef1f4",
};

export default function MemoryDetailsPage() {
  const params = useSearchParams();
  const [data, setData] = useState<MemoryDetails | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [episodicOpen, setEpisodicOpen] = useState(false);
  const [stmOpen, setStmOpen] = useState(false);
  const [soulOpen, setSoulOpen] = useState(false);
  const [momentumOpen, setMomentumOpen] = useState(false);
  const [rhythmOpen, setRhythmOpen] = useState(false);
  const [emotionOpen, setEmotionOpen] = useState(false);
  const [emotionSoulRhythmOpen, setEmotionSoulRhythmOpen] = useState(false);
  const [longitudinalOpen, setLongitudinalOpen] = useState(false);
  const [narrationOpen, setNarrationOpen] = useState(false);
  const [narrationWindow, setNarrationWindow] = useState(1500);
  const [narrationStatus, setNarrationStatus] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [narrationData, setNarrationData] = useState<any>(null);
  const [narrationError, setNarrationError] = useState<string | null>(null);
  const [inquiryQuestion, setInquiryQuestion] = useState("");
  const [inquiryAnswer, setInquiryAnswer] = useState<any>(null);
  const [inquiryStatus, setInquiryStatus] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [inquiryError, setInquiryError] = useState<string | null>(null);
  const [hasFetched, setHasFetched] = useState(false);
  const [showSources, setShowSources] = useState(false);
  const [piOpen, setPiOpen] = useState(false);
  const [piWindow, setPiWindow] = useState(1500);
  const [piStatus, setPiStatus] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [piData, setPiData] = useState<any>(null);
  const [piError, setPiError] = useState<string | null>(null);
  const [elementalOpen, setElementalOpen] = useState(false);
  const [trendsOpen, setTrendsOpen] = useState(false);
  const [baselineOpen, setBaselineOpen] = useState(false);
  const [energyOpen, setEnergyOpen] = useState(false);
  const [energyBaselineOpen, setEnergyBaselineOpen] = useState(false);
  const [ayurAnchorDays, setAyurAnchorDays] = useState(1500);
  const [ayurStatus, setAyurStatus] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [ayurReflection, setAyurReflection] = useState<string | null>(null);
  const [ayurError, setAyurError] = useState<string | null>(null);
  const soulState = useMemo(() => {
    const raw = data?.soul?.soul_state;
    if (!raw) return {};
    if (typeof raw === "string") {
      try {
        return JSON.parse(raw);
      } catch {
        return { raw };
      }
    }
    return raw;
  }, [data]);

  const rhythmState = useMemo(() => {
    const raw = data?.rhythm?.rhythm_state;
    if (!raw) return {};
    if (typeof raw === "string") {
      try {
        return JSON.parse(raw);
      } catch {
        return { raw };
      }
    }
    return raw;
  }, [data]);

  const longitudinalState = useMemo(() => {
    const raw =
      data?.longitudinal?.longitudinal_state ||
      // fallback in case API payload is flattened
      (data as any)?.longitudinal_state;
    if (!raw) return {};
    if (typeof raw === "string") {
      try {
        return JSON.parse(raw);
      } catch {
        return { raw };
      }
    }
    return raw;
  }, [data]);

  const emotionState = useMemo(() => {
    const raw =
      data?.esr?.emotion_state ||
      data?.emotion?.emotion_state ||
      data?.esr?.esr_state ||
      {};
    if (typeof raw === "string") {
      try {
        return JSON.parse(raw);
      } catch {
        return { raw };
      }
    }
    return raw;
  }, [data]);

  const emotionSoulRhythmState = useMemo(() => {
    const raw = data?.emotion_soul_rhythm?.emotion_soul_rhythm_state || {};
    if (typeof raw === "string") {
      try {
        return JSON.parse(raw);
      } catch {
        return { raw };
      }
    }
    return raw;
  }, [data]);

  const personId = params.get("person_id") || "";
  const entryId = params.get("entry_id") || "";

  const loadData = async () => {
    if (!personId || loading) return;
    setLoading(true);
    setError(null);
    try {
      const url = new URL("/api/lab/memory-details", window.location.origin);
      url.searchParams.set("person_id", personId);
      url.searchParams.set("limit", "10");
      if (entryId) url.searchParams.set("entry_id", entryId);
      const res = await fetch(url.toString());
      const payload = await res.json();
      if (!res.ok) {
        throw new Error(payload?.error || res.statusText || "Failed to load");
      }
      setData(payload);
      setHasFetched(true);
      // Debug: check if elemental data is present
      console.log("[memory-details] elemental_stm:", payload?.elemental_stm?.length || 0);
      console.log("[memory-details] elemental_weekly:", payload?.elemental_weekly?.length || 0);
      console.log("[memory-details] elemental_monthly:", payload?.elemental_monthly?.length || 0);
    } catch (err: any) {
      setError(err?.message || "Failed to load");
    } finally {
      setLoading(false);
    }
  };

  const loadPersonalIntelligence = async () => {
    if (!personId) return;
    setPiStatus("loading");
    setPiError(null);
    try {
      const url = new URL("/api/lab/personal-intelligence", window.location.origin);
      url.searchParams.set("person_id", personId);
      url.searchParams.set("anchor_days", String(piWindow || 1500));
      const res = await fetch(url.toString());
      const payload = await res.json();
      if (!res.ok) {
        throw new Error(payload?.detail || payload?.error || res.statusText || "Failed to load snapshot");
      }
      setPiData(payload);
      setPiStatus("ready");
    } catch (err: any) {
      setPiStatus("error");
      setPiError(err?.message || "Failed to load snapshot");
    }
  };

  const loadNarration = async () => {
    if (!personId) return;
    setNarrationStatus("loading");
    setNarrationError(null);
    try {
      const url = new URL("/api/lab/reflection/narration", window.location.origin);
      url.searchParams.set("person_id", personId);
      url.searchParams.set("window_days", String(narrationWindow || 7));
      url.searchParams.set("debug", "1");
      const res = await fetch(url.toString());
      const text = await res.text();
      let data: any = {};
      try {
        data = text ? JSON.parse(text) : {};
      } catch {
        throw new Error(text?.slice(0, 120) || "Non-JSON response");
      }
      if (!res.ok) {
        throw new Error(data?.detail || data?.error || res.statusText || "Failed to render narration");
      }
      setNarrationData(data);
      setNarrationStatus("ready");
    } catch (err: any) {
      setNarrationStatus("error");
      setNarrationError(err?.message || "Narration fetch failed");
    }
  };

  const generateAyurvedicReflection = async () => {
    if (!personId) return;
    setAyurStatus("loading");
    setAyurError(null);
    setAyurReflection(null);
    try {
      const res = await fetch(`${getApiBase()}/lab/ayurvedic-reflection`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ person_id: personId, anchor_days: ayurAnchorDays || 1500 }),
      });
      const text = await res.text();
      const data = text ? JSON.parse(text) : {};
      if (!res.ok) {
        throw new Error(data?.error || res.statusText || "Failed to generate reflection");
      }
      setAyurReflection(data?.reflection || "");
      setAyurStatus("ready");
    } catch (err: any) {
      setAyurError(err?.message || "Failed to generate reflection");
      setAyurStatus("error");
    }
  };

  const submitInquiry = async () => {
    if (!personId || !inquiryQuestion.trim()) {
      return;
    }
    setInquiryStatus("loading");
    setInquiryError(null);
    setShowSources(false);
    try {
      const res = await fetch("/api/lab/reflection/inquiry", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          person_id: personId,
          reflection_id: "foundation",
          window_days: narrationWindow || 1500,
          question_text: inquiryQuestion,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data?.detail || data?.error || "Inquiry failed");
      }
      setInquiryAnswer(data);
      setInquiryStatus("ready");
      setShowSources(true);
    } catch (err: any) {
      setInquiryStatus("error");
      setInquiryError(err?.message || "Inquiry failed");
    }
  };

  const ensureData = async () => {
    if (!hasFetched && !loading) {
      await loadData();
    }
  };

  return (
    <div style={{ minHeight: "100vh", background: palette.surface, color: palette.text, padding: 20, fontFamily: "Inter, system-ui, -apple-system, sans-serif" }}>
      <div style={{ maxWidth: 1100, margin: "0 auto", display: "flex", flexDirection: "column", gap: 12 }}>
        <h1 style={{ margin: 0, fontSize: 22 }}>Person Snapshot</h1>
        <div style={{ color: palette.muted, fontSize: 13 }}>
          Person: {personId || "—"} {entryId ? `• Entry: ${entryId}` : ""}
        </div>
        {loading && <div style={{ color: palette.muted }}>Loading…</div>}
        {error && <div style={{ color: "#f87171" }}>{error}</div>}

        <>
            <div style={{ display: "flex", flexDirection: "column", gap: 12, border: `1px solid ${palette.border}`, borderRadius: 12, padding: 12 }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: palette.muted, textTransform: "uppercase", letterSpacing: 0.6 }}>
                Memory
              </div>

              <Card
                title="Short-term Memory"
                extra={
                  <button
                    onClick={async () => {
                      const next = !stmOpen;
                      setStmOpen(next);
                      if (next) {
                        await loadData();
                      }
                    }}
                    style={{
                      background: "#0f1115",
                      color: "#ffffff",
                      border: "1px solid #0f1115",
                      borderRadius: 6,
                      padding: "4px 8px",
                      cursor: "pointer",
                    }}
                  >
                    {stmOpen ? "Collapse" : "Expand"}
                  </button>
                }
              >
                {stmOpen ? (
                  (data?.short_term?.length || 0) > 0 ? (
                    <ul style={{ paddingLeft: 16, margin: 0, display: "flex", flexDirection: "column", gap: 6 }}>
                      {(data?.short_term || []).map((row: any) => (
                        <li key={row.id} style={{ color: palette.text }}>
                          <div style={{ fontSize: 12, color: palette.muted }}>
                            {row.created_at || "—"}
                          </div>
                          {row.entry_id ? (
                            <div style={{ fontSize: 12, color: palette.muted }}>entry_id: {row.entry_id}</div>
                          ) : null}
                          <div style={{ fontSize: 14, color: palette.text, fontFamily: "Inter, system-ui, -apple-system, sans-serif", marginTop: 4 }}>
                            {row.text || "—"}
                          </div>
                          {row.tags && Array.isArray(row.tags) && row.tags.length > 0 ? (
                            <pre style={{ background: palette.surface, border: `1px solid ${palette.border}`, borderRadius: 8, padding: 8, fontSize: 12, whiteSpace: "pre-wrap", wordBreak: "break-word", marginTop: 6 }}>
                              {JSON.stringify(row.tags || {}, null, 2)}
                            </pre>
                          ) : null}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <div style={{ color: palette.muted }}>{hasFetched ? "None" : "Expand to load"}</div>
                  )
                ) : null}
              </Card>

              <Card
                title="Episodic (long-term)"
                extra={
                  <button
                    onClick={async () => {
                      const next = !episodicOpen;
                      setEpisodicOpen(next);
                      if (next) {
                        await loadData();
                      }
                    }}
                    style={{
                      background: "#0f1115",
                      color: "#ffffff",
                      border: "1px solid #0f1115",
                      borderRadius: 6,
                      padding: "4px 8px",
                      cursor: "pointer",
                    }}
                  >
                    {episodicOpen ? "Collapse" : "Expand"}
                  </button>
                }
              >
                {episodicOpen ? (
                  (data?.episodic?.length || 0) > 0 ? (
                    <ul style={{ paddingLeft: 16, margin: 0, display: "flex", flexDirection: "column", gap: 6 }}>
                      {(data?.episodic || []).map((row: any) => (
                        <li key={row.id} style={{ color: palette.text }}>
                          <div style={{ fontSize: 12, color: palette.muted }}>
                            {row.ts || row.created_at || "—"} • has_vec: {row.has_vec ? "yes" : "no"}
                          </div>
                          <div style={{ fontSize: 12, color: palette.accent, fontWeight: 600, marginTop: 4 }}>text</div>
                          <div style={{ fontSize: 14, color: palette.text, fontFamily: "Inter, system-ui, -apple-system, sans-serif" }}>
                            {row.text || "—"}
                          </div>
                          <div style={{ fontSize: 12, color: palette.muted, marginTop: 4 }}>soul:</div>
                          <pre style={{ background: palette.surface, border: `1px solid ${palette.border}`, borderRadius: 8, padding: 8, fontSize: 12, whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
                            {JSON.stringify(
                              {
                                soul: row.soul,
                                soul_shadow: row.soul_shadow,
                                soul_light: row.soul_light,
                                soul_conflict: row.soul_conflict,
                                soul_friction: row.soul_friction,
                              },
                              null,
                              2,
                            )}
                          </pre>
                          <div style={{ fontSize: 12, color: palette.muted, marginTop: 4 }}>emotion_loop:</div>
                          <pre style={{ background: palette.surface, border: `1px solid ${palette.border}`, borderRadius: 8, padding: 8, fontSize: 12, whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
                            {JSON.stringify(row.emotion_loop || {}, null, 2)}
                          </pre>
                          <div style={{ fontSize: 12, color: palette.muted, marginTop: 4 }}>rhythm_state:</div>
                          <pre style={{ background: palette.surface, border: `1px solid ${palette.border}`, borderRadius: 8, padding: 8, fontSize: 12, whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
                            {JSON.stringify(row.rhythm_state || {}, null, 2)}
                          </pre>
                          <div style={{ fontSize: 12, color: palette.muted, marginTop: 4 }}>emotional_state:</div>
                          <pre style={{ background: palette.surface, border: `1px solid ${palette.border}`, borderRadius: 8, padding: 8, fontSize: 12, whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
                            {JSON.stringify(row.emotional_state || {}, null, 2)}
                          </pre>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <div style={{ color: palette.muted }}>{hasFetched ? "None" : "Expand to load"}</div>
                  )
                ) : null}
              </Card>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 12, border: `1px solid ${palette.border}`, borderRadius: 12, padding: 12 }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: palette.muted, textTransform: "uppercase", letterSpacing: 0.6 }}>
                Deterministic Intelligence
              </div>

              <Card
                title="Soul"
                extra={
                  <button
                    onClick={async () => {
                      const next = !soulOpen;
                      setSoulOpen(next);
                      if (next) {
                        await loadData();
                      }
                    }}
                    style={{
                      background: "#0f1115",
                      color: "#ffffff",
                      border: "1px solid #0f1115",
                      borderRadius: 6,
                      padding: "4px 8px",
                      cursor: "pointer",
                    }}
                  >
                    {soulOpen ? "Collapse" : "Expand"}
                  </button>
                }
              >
                {data?.soul?.updated_at && (
                  <div style={{ fontSize: 12, color: palette.muted, marginBottom: 8 }}>Updated: {data.soul.updated_at}</div>
                )}
                {soulOpen ? (
                  <pre style={{ background: palette.surface, border: `1px solid ${palette.border}`, borderRadius: 10, padding: 10, fontSize: 12, color: palette.text, whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
                    {JSON.stringify(soulState || {}, null, 2)}
                  </pre>
                ) : null}
              </Card>

              <Card
                title="Identity Momentum"
                extra={
                  <button
                    onClick={async () => {
                      const next = !momentumOpen;
                      setMomentumOpen(next);
                      if (next) {
                        await loadData();
                      }
                    }}
                    style={{
                      background: "#0f1115",
                      color: "#ffffff",
                      border: "1px solid #0f1115",
                      borderRadius: 6,
                      padding: "4px 8px",
                      cursor: "pointer",
                    }}
                  >
                    {momentumOpen ? "Collapse" : "Expand"}
                  </button>
                }
              >
                {data?.identity_momentum_v2?.updated_at && (
                  <div style={{ fontSize: 12, color: palette.muted, marginBottom: 8 }}>Updated: {data.identity_momentum_v2.updated_at}</div>
                )}
                {momentumOpen ? (
                  <pre style={{ background: palette.surface, border: `1px solid ${palette.border}`, borderRadius: 10, padding: 10, fontSize: 12, color: palette.text, whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
                    {JSON.stringify(
                      (() => {
                        const raw = data?.identity_momentum_v2?.identity_momentum_state || data?.identity_momentum?.identity_momentum_state || {};
                        if (typeof raw === "string") {
                          try {
                            return JSON.parse(raw);
                          } catch {
                            return { raw };
                          }
                        }
                        return raw;
                      })(),
                      null,
                      2,
                    )}
                  </pre>
                ) : null}
              </Card>

              <Card
                title="Rhythm"
                extra={
                  <button
                    onClick={async () => {
                      const next = !rhythmOpen;
                      setRhythmOpen(next);
                      if (next) {
                        await loadData();
                      }
                    }}
                    style={{
                      background: "#0f1115",
                      color: "#ffffff",
                      border: "1px solid #0f1115",
                      borderRadius: 6,
                      padding: "4px 8px",
                      cursor: "pointer",
                    }}
                  >
                    {rhythmOpen ? "Collapse" : "Expand"}
                  </button>
                }
              >
                {data?.rhythm?.updated_at && (
                  <div style={{ fontSize: 12, color: palette.muted, marginBottom: 8 }}>Updated: {data?.rhythm?.updated_at}</div>
                )}
                {rhythmOpen ? (
                  <pre style={{ background: palette.surface, border: `1px solid ${palette.border}`, borderRadius: 10, padding: 10, fontSize: 12, color: palette.text, whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
                    {JSON.stringify(rhythmState || {}, null, 2)}
                  </pre>
                ) : null}
              </Card>

              <Card
                title="Emotion State (ESR)"
                extra={
                  <button
                    onClick={async () => {
                      const next = !emotionOpen;
                      setEmotionOpen(next);
                      if (next) {
                        await loadData();
                      }
                    }}
                    style={{
                      background: "#0f1115",
                      color: "#ffffff",
                      border: "1px solid #0f1115",
                      borderRadius: 6,
                      padding: "4px 8px",
                      cursor: "pointer",
                    }}
                  >
                    {emotionOpen ? "Collapse" : "Expand"}
                  </button>
                }
              >
                {data?.esr?.updated_at && (
                  <div style={{ fontSize: 12, color: palette.muted, marginBottom: 8 }}>Updated: {data?.esr?.updated_at}</div>
                )}
                {emotionOpen ? (
                  <pre style={{ background: palette.surface, border: `1px solid ${palette.border}`, borderRadius: 10, padding: 10, fontSize: 12, color: palette.text, whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
                    {JSON.stringify(emotionState || {}, null, 2)}
                  </pre>
                ) : null}
              </Card>

              <Card
                title="Emotion × Soul × Rhythm"
                extra={
                  <button
                    onClick={async () => {
                      const next = !emotionSoulRhythmOpen;
                      setEmotionSoulRhythmOpen(next);
                      if (next) {
                        await loadData();
                      }
                    }}
                    style={{
                      background: "#0f1115",
                      color: "#ffffff",
                      border: "1px solid #0f1115",
                      borderRadius: 6,
                      padding: "4px 8px",
                      cursor: "pointer",
                    }}
                  >
                    {emotionSoulRhythmOpen ? "Collapse" : "Expand"}
                  </button>
                }
              >
                {data?.emotion_soul_rhythm?.updated_at && (
                  <div style={{ fontSize: 12, color: palette.muted, marginBottom: 8 }}>Updated: {data?.emotion_soul_rhythm?.updated_at}</div>
                )}
                {emotionSoulRhythmOpen ? (
                  <pre style={{ background: palette.surface, border: `1px solid ${palette.border}`, borderRadius: 10, padding: 10, fontSize: 12, color: palette.text, whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
                    {JSON.stringify(emotionSoulRhythmState || {}, null, 2)}
                  </pre>
                ) : null}
              </Card>

              <Card
                title="Longitudinal State"
                extra={
                  <button
                    onClick={async () => {
                      const next = !longitudinalOpen;
                      setLongitudinalOpen(next);
                      if (next) {
                        await loadData();
                      }
                    }}
                    style={{
                      background: "#0f1115",
                      color: "#ffffff",
                      border: "1px solid #0f1115",
                      borderRadius: 6,
                      padding: "4px 8px",
                      cursor: "pointer",
                    }}
                  >
                    {longitudinalOpen ? "Collapse" : "Expand"}
                  </button>
                }
              >
                {data?.longitudinal?.updated_at && (
                  <div style={{ fontSize: 12, color: palette.muted, marginBottom: 8 }}>Updated: {data?.longitudinal?.updated_at}</div>
                )}
                {(data as any)?.longitudinal_state && !data?.longitudinal?.updated_at && (
                  <div style={{ fontSize: 12, color: palette.muted, marginBottom: 8 }}>Updated: {data?.updated_at || "—"}</div>
                )}
                {longitudinalOpen ? (
                  <pre style={{ background: palette.surface, border: `1px solid ${palette.border}`, borderRadius: 10, padding: 10, fontSize: 12, color: palette.text, whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
                    {JSON.stringify(longitudinalState || {}, null, 2)}
                  </pre>
                ) : null}
              </Card>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 12, border: `1px solid ${palette.border}`, borderRadius: 12, padding: 12 }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: palette.muted, textTransform: "uppercase", letterSpacing: 0.6 }}>
                Ayurvedic & Energy Lens (NEW)
              </div>
              <div style={{ color: palette.muted, fontSize: 12 }}>
                An additional, optional interpretive layer derived from elemental and energy dynamics. This lens complements other system views. It does not replace them.
              </div>

              <Card
                title="Elemental Activity (Recent) — Short-term elemental projections (volatile)"
                extra={
                  <button
                    onClick={async () => {
                      await ensureData();
                      setElementalOpen(!elementalOpen);
                    }}
                    style={{
                      background: "#0f1115",
                      color: "#ffffff",
                      border: "1px solid #0f1115",
                      borderRadius: 6,
                      padding: "4px 8px",
                      cursor: "pointer",
                    }}
                  >
                    {elementalOpen ? "Collapse" : "Expand"}
                  </button>
                }
              >
                {elementalOpen ? (
                  (data?.elemental_stm?.length || 0) > 0 ? (
                    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                      {(data?.elemental_stm || []).map((row: any) => (
                        <div key={row.id} style={{ borderBottom: `1px solid ${palette.border}`, paddingBottom: 8 }}>
                          <div style={{ fontSize: 12, color: palette.muted }}>
                            dimension: {row.dimension} • created: {row.created_at} • expires: {row.expires_at}
                          </div>
                          <div style={{ fontSize: 12, color: palette.muted }}>
                            source: {row.source_type} • signal_id: {row.source_signal_id}
                          </div>
                          <div style={{ fontSize: 12, color: palette.text }}>
                            magnitude: {row.magnitude} • confidence: {row.confidence}
                          </div>
                          <div style={{ fontSize: 12, color: palette.muted }}>distribution:</div>
                          <div style={{ display: "flex", gap: 12, fontSize: 12 }}>
                            {["earth", "water", "fire", "air", "ether"].map((el) => (
                              <span key={el}>
                                {el}: {row[el] ?? 0}
                              </span>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div style={{ color: palette.muted }}>Not enough data yet (non-expired elemental STM).</div>
                  )
                ) : null}
              </Card>

              <Card
                title="Elemental Trends — Aggregated elemental patterns over time"
                extra={
                  <button
                    onClick={async () => {
                      await ensureData();
                      setTrendsOpen(!trendsOpen);
                    }}
                    style={{
                      background: "#0f1115",
                      color: "#ffffff",
                      border: "1px solid #0f1115",
                      borderRadius: 6,
                      padding: "4px 8px",
                      cursor: "pointer",
                    }}
                  >
                    {trendsOpen ? "Collapse" : "Expand"}
                  </button>
                }
              >
                <div style={{ color: palette.muted, fontSize: 12, marginBottom: 6 }}>
                  This lens complements other system views. It does not replace them.
                </div>
                {trendsOpen ? (
                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    <div>
                      <div style={{ fontWeight: 600, fontSize: 13 }}>Weekly</div>
                      {(data?.elemental_weekly?.length || 0) > 0 ? (
                        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                          {(data?.elemental_weekly || []).map((row: any) => (
                            <div key={`${row.person_id}-${row.week_start}-${row.dimension}`} style={{ borderBottom: `1px solid ${palette.border}`, paddingBottom: 6 }}>
                              <div style={{ fontSize: 12, color: palette.muted }}>
                                {row.week_start} • dimension: {row.dimension} • volatility: {row.volatility} • signals: {row.signal_count}
                              </div>
                              <div style={{ display: "flex", gap: 10, fontSize: 12 }}>
                                {["earth", "water", "fire", "air", "ether"].map((el) => (
                                  <span key={el}>
                                    {el}: {row[`${el}_avg`] ?? 0}
                                  </span>
                                ))}
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div style={{ color: palette.muted }}>Not enough data yet (weekly elemental summaries).</div>
                      )}
                    </div>
                    <div>
                      <div style={{ fontWeight: 600, fontSize: 13 }}>Monthly</div>
                      {(data?.elemental_monthly?.length || 0) > 0 ? (
                        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                          {(data?.elemental_monthly || []).map((row: any) => (
                            <div key={`${row.person_id}-${row.month_start}-${row.dimension}`} style={{ borderBottom: `1px solid ${palette.border}`, paddingBottom: 6 }}>
                              <div style={{ fontSize: 12, color: palette.muted }}>
                                {row.month_start} • dimension: {row.dimension} • volatility: {row.volatility} • weeks: {row.week_count}
                              </div>
                              <div style={{ display: "flex", gap: 10, fontSize: 12 }}>
                                {["earth", "water", "fire", "air", "ether"].map((el) => (
                                  <span key={el}>
                                    {el}: {row[`${el}_avg`] ?? 0}
                                  </span>
                                ))}
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div style={{ color: palette.muted }}>Not enough data yet (monthly elemental summaries).</div>
                      )}
                    </div>
                  </div>
                ) : null}
              </Card>

              <Card
                title="Elemental Baseline — Learned over time; subject to revision"
                extra={
                  <button
                    onClick={async () => {
                      await ensureData();
                      setBaselineOpen(!baselineOpen);
                    }}
                    style={{
                      background: "#0f1115",
                      color: "#ffffff",
                      border: "1px solid #0f1115",
                      borderRadius: 6,
                      padding: "4px 8px",
                      cursor: "pointer",
                    }}
                  >
                    {baselineOpen ? "Collapse" : "Expand"}
                  </button>
                }
              >
                <div style={{ color: palette.muted, fontSize: 12, marginBottom: 6 }}>
                  This lens complements other system views. It does not replace them.
                </div>
                {baselineOpen ? (
                  data?.personal_model_elemental && Object.keys(data.personal_model_elemental || {}).length > 0 ? (
                    <div style={{ display: "flex", flexDirection: "column", gap: 8, fontSize: 12 }}>
                      <div>confidence: {data.personal_model_elemental.confidence ?? "—"}</div>
                      <div>updated_at: {data.personal_model_elemental.updated_at ?? "—"}</div>
                      <div style={{ fontWeight: 600 }}>baseline</div>
                      <pre style={{ background: palette.surface, border: `1px solid ${palette.border}`, borderRadius: 8, padding: 8, fontSize: 12, whiteSpace: "pre-wrap" }}>
                        {JSON.stringify(data.personal_model_elemental.baseline || {}, null, 2)}
                      </pre>
                      <div style={{ fontWeight: 600 }}>volatility</div>
                      <pre style={{ background: palette.surface, border: `1px solid ${palette.border}`, borderRadius: 8, padding: 8, fontSize: 12, whiteSpace: "pre-wrap" }}>
                        {JSON.stringify(data.personal_model_elemental.volatility || {}, null, 2)}
                      </pre>
                      <div style={{ fontWeight: 600 }}>recovery_rate</div>
                      <pre style={{ background: palette.surface, border: `1px solid ${palette.border}`, borderRadius: 8, padding: 8, fontSize: 12, whiteSpace: "pre-wrap" }}>
                        {JSON.stringify(data.personal_model_elemental.recovery_rate || {}, null, 2)}
                      </pre>
                      <div style={{ fontWeight: 600 }}>coupling</div>
                      <pre style={{ background: palette.surface, border: `1px solid ${palette.border}`, borderRadius: 8, padding: 8, fontSize: 12, whiteSpace: "pre-wrap" }}>
                        {JSON.stringify(data.personal_model_elemental.coupling || {}, null, 2)}
                      </pre>
                    </div>
                  ) : (
                    <div style={{ color: palette.muted }}>Not enough data yet (personal_model_elemental).</div>
                  )
                ) : null}
              </Card>

              <Card
                title="Energy Metrics — Derived from aggregated elemental patterns"
                extra={
                  <button
                    onClick={async () => {
                      await ensureData();
                      setEnergyOpen(!energyOpen);
                    }}
                    style={{
                      background: "#0f1115",
                      color: "#ffffff",
                      border: "1px solid #0f1115",
                      borderRadius: 6,
                      padding: "4px 8px",
                      cursor: "pointer",
                    }}
                  >
                    {energyOpen ? "Collapse" : "Expand"}
                  </button>
                }
              >
                {energyOpen ? (
                  <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                    <div style={{ fontSize: 12, color: palette.muted }}>
                      This lens complements other system views. It does not replace them.
                    </div>
                    <div>
                      <div style={{ fontWeight: 600, fontSize: 13 }}>Recent (weekly)</div>
                      {(data?.energy_weekly?.length || 0) > 0 ? (
                        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                          {(data?.energy_weekly || []).map((row: any) => (
                            <div key={`${row.person_id}-${row.week_start}`} style={{ borderBottom: `1px solid ${palette.border}`, paddingBottom: 6 }}>
                              <div style={{ fontSize: 12, color: palette.muted }}>
                                {row.week_start} • confidence: {row.confidence}
                              </div>
                              <div style={{ display: "flex", gap: 10, fontSize: 12 }}>
                                <span>activation_load: {row.activation_load}</span>
                                <span>grounding: {row.grounding}</span>
                                <span>circulation: {row.circulation}</span>
                                <span>recovery_efficiency: {row.recovery_efficiency}</span>
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div style={{ color: palette.muted }}>Not enough data yet (weekly energy summaries).</div>
                      )}
                    </div>
                    <div>
                      <div style={{ fontWeight: 600, fontSize: 13 }}>Trends (monthly smoothing)</div>
                      {(data?.energy_monthly?.length || 0) > 0 ? (
                        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                          {(data?.energy_monthly || []).map((row: any) => (
                            <div key={`${row.person_id}-${row.month_start}`} style={{ borderBottom: `1px solid ${palette.border}`, paddingBottom: 6 }}>
                              <div style={{ fontSize: 12, color: palette.muted }}>
                                {row.month_start} • confidence: {row.confidence}
                              </div>
                              <div style={{ display: "flex", gap: 10, fontSize: 12 }}>
                                <span>activation_load: {row.activation_load}</span>
                                <span>grounding: {row.grounding}</span>
                                <span>circulation: {row.circulation}</span>
                                <span>recovery_efficiency: {row.recovery_efficiency}</span>
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div style={{ color: palette.muted }}>Not enough data yet (monthly energy summaries).</div>
                      )}
                    </div>
                  </div>
                ) : null}
              </Card>

              <Card
                title="Energy Baseline — Learned patterns; subject to revision"
                extra={
                  <button
                    onClick={async () => {
                      await ensureData();
                      setEnergyBaselineOpen(!energyBaselineOpen);
                    }}
                    style={{
                      background: "#0f1115",
                      color: "#ffffff",
                      border: "1px solid #0f1115",
                      borderRadius: 6,
                      padding: "4px 8px",
                      cursor: "pointer",
                    }}
                  >
                    {energyBaselineOpen ? "Collapse" : "Expand"}
                  </button>
                }
              >
                <div style={{ color: palette.muted, fontSize: 12, marginBottom: 6 }}>
                  This lens complements other system views. It does not replace them.
                </div>
                {energyBaselineOpen ? (
                  data?.personal_model_energy && Object.keys(data.personal_model_energy || {}).length > 0 ? (
                    <div style={{ display: "flex", flexDirection: "column", gap: 8, fontSize: 12 }}>
                      <div>confidence: {data.personal_model_energy.confidence ?? "—"}</div>
                      <div>updated_at: {data.personal_model_energy.updated_at ?? "—"}</div>
                      <div style={{ fontWeight: 600 }}>baseline</div>
                      <pre style={{ background: palette.surface, border: `1px solid ${palette.border}`, borderRadius: 8, padding: 8, fontSize: 12, whiteSpace: "pre-wrap" }}>
                        {JSON.stringify(data.personal_model_energy.baseline || {}, null, 2)}
                      </pre>
                      <div style={{ fontWeight: 600 }}>volatility</div>
                      <pre style={{ background: palette.surface, border: `1px solid ${palette.border}`, borderRadius: 8, padding: 8, fontSize: 12, whiteSpace: "pre-wrap" }}>
                        {JSON.stringify(data.personal_model_energy.volatility || {}, null, 2)}
                      </pre>
                      <div style={{ fontWeight: 600 }}>recovery_profile</div>
                      <pre style={{ background: palette.surface, border: `1px solid ${palette.border}`, borderRadius: 8, padding: 8, fontSize: 12, whiteSpace: "pre-wrap" }}>
                        {JSON.stringify(data.personal_model_energy.recovery_profile || {}, null, 2)}
                      </pre>
                      <div style={{ fontWeight: 600 }}>circulation_stability</div>
                      <pre style={{ background: palette.surface, border: `1px solid ${palette.border}`, borderRadius: 8, padding: 8, fontSize: 12, whiteSpace: "pre-wrap" }}>
                        {JSON.stringify(data.personal_model_energy.circulation_stability || {}, null, 2)}
                      </pre>
                    </div>
                  ) : (
                    <div style={{ color: palette.muted }}>Not enough data yet (personal_model_energy).</div>
                  )
                ) : null}
              </Card>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 12, border: `1px solid ${palette.border}`, borderRadius: 12, padding: 12 }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: palette.muted, textTransform: "uppercase", letterSpacing: 0.6 }}>
                Foundational Reflection (Internal)
              </div>
              <Card
                title="Human Narration (Foundation Mode)"
                extra={
                  <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                    <label style={{ color: palette.muted, fontSize: 12 }}>
                      Anchor (days)
                      <select
                        value={narrationWindow}
                        onChange={(e) => setNarrationWindow(Number(e.target.value) || 7)}
                        style={{
                          marginLeft: 6,
                          padding: "4px 6px",
                          borderRadius: 6,
                          border: `1px solid ${palette.border}`,
                          background: "#0f1115",
                          color: "#ffffff",
                        }}
                      >
                        {[1500, 7, 14, 30].map((v) => (
                          <option key={v} value={v} style={{ color: palette.text }}>
                            {v}
                          </option>
                        ))}
                      </select>
                    </label>
                    <button
                      onClick={async () => {
                        const next = !narrationOpen;
                        setNarrationOpen(next);
                        if (next) {
                          await loadNarration();
                        }
                      }}
                      style={{
                        background: "#0f1115",
                      color: "#ffffff",
                      border: "1px solid #0f1115",
                        borderRadius: 6,
                        padding: "4px 8px",
                        cursor: "pointer",
                      }}
                    >
                      {narrationOpen ? "Collapse" : "Generate"}
                    </button>
                  </div>
                }
              >
                {narrationStatus === "error" && <div style={{ color: "#f87171", fontSize: 12 }}>{narrationError}</div>}
                {narrationOpen ? (
                  narrationData ? (
                    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                      <div style={{ color: palette.muted, fontSize: 12 }}>
                        Mode: {narrationData?.mode || "foundation_narration"} • Anchor:{" "}
                        {narrationData?.timeframe?.anchor_days ?? narrationWindow} days (rolling)
                      </div>
                      <div style={{ fontWeight: 600 }}>Narration</div>
                      <div style={{ whiteSpace: "pre-wrap", lineHeight: 1.6 }}>
                        {narrationData?.reflection_text?.trim()
                          ? narrationData.reflection_text
                          : "Reflection could not be generated. This usually indicates missing journals or narration guardrails blocking output."}
                      </div>
                        <div style={{ borderTop: `1px solid ${palette.border}`, paddingTop: 10, marginTop: 6, display: "flex", flexDirection: "column", gap: 10 }}>
                        <div style={{ fontWeight: 600 }}>Ask about this reflection</div>
                        <div style={{ background: palette.surface, border: `1px solid ${palette.border}`, borderRadius: 12, padding: 10, display: "flex", flexDirection: "column", gap: 8 }}>
                          <textarea
                            value={inquiryQuestion}
                            onChange={(e) => setInquiryQuestion(e.target.value)}
                            placeholder="Example: Why did you mention evenings carrying more load?"
                            style={{
                              width: "100%",
                              minHeight: 110,
                              borderRadius: 10,
                              border: `1px solid ${palette.border}`,
                              padding: 12,
                              background: palette.card,
                              color: palette.text,
                              fontSize: 14,
                              fontFamily: "Inter, system-ui, -apple-system, sans-serif",
                            }}
                          />
                          <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
                            <button
                              onClick={submitInquiry}
                              disabled={inquiryStatus === "loading"}
                              style={{
                                background: palette.accent,
                                color: "#fff",
                                border: "none",
                                borderRadius: 10,
                                padding: "10px 16px",
                                cursor: "pointer",
                                opacity: inquiryStatus === "loading" ? 0.7 : 1,
                                boxShadow: "0 6px 16px rgba(31,138,112,0.18)",
                              }}
                            >
                              {inquiryStatus === "loading" ? "Sending…" : "Send question"}
                            </button>
                            {inquiryAnswer?.answer_mode ? (
                              <span
                                style={{
                                  fontSize: 12,
                                  background: palette.card,
                                  borderRadius: 999,
                                  padding: "6px 12px",
                                  border: `1px solid ${palette.border}`,
                                }}
                              >
                                Mode: {inquiryAnswer.answer_mode}
                              </span>
                            ) : null}
                            {inquiryStatus === "error" && (
                              <span style={{ color: "#f87171", fontSize: 12 }}>{inquiryError}</span>
                            )}
                          </div>
                        </div>
                        {inquiryStatus === "ready" && inquiryAnswer ? (
                          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                            <div style={{ fontSize: 14, lineHeight: 1.5, whiteSpace: "pre-wrap" }}>
                              {inquiryAnswer.answer_text}
                            </div>
                            {inquiryAnswer.sources_json ? (
                              <details open={showSources} onToggle={(e) => setShowSources((e.target as HTMLDetailsElement).open)}>
                                <summary style={{ cursor: "pointer", color: palette.muted, fontSize: 12 }}>Sources used</summary>
                                <pre
                                  style={{
                                    background: palette.surface,
                                    border: `1px solid ${palette.border}`,
                                    borderRadius: 10,
                                    padding: 10,
                                    fontSize: 12,
                                    color: palette.text,
                                    maxHeight: 220,
                                    overflow: "auto",
                                  }}
                                >
                                  {JSON.stringify(inquiryAnswer.sources_json, null, 2)}
                                </pre>
                              </details>
                            ) : null}
                          </div>
                        ) : null}
                      </div>
                      {narrationData?.debug ? (
                        <>
                          <button
                            onClick={() => setNarrationStatus((prev) => (prev === "ready" ? "ready" : "ready"))}
                            style={{ display: "none" }}
                          />
                          <details style={{ marginTop: 4 }}>
                            <summary style={{ cursor: "pointer", color: palette.muted, fontSize: 12 }}>Internal Debug (counts & presence only)</summary>
                            <pre
                              style={{
                                background: palette.surface,
                                border: `1px solid ${palette.border}`,
                                borderRadius: 10,
                                padding: 10,
                                fontSize: 12,
                                color: palette.text,
                                maxHeight: 220,
                                overflow: "auto",
                              }}
                            >
                              {JSON.stringify(narrationData?.debug || {}, null, 2)}
                            </pre>
                          </details>
                        </>
                      ) : null}
                    </div>
                  ) : narrationStatus === "loading" ? (
                    <div style={{ color: palette.muted }}>Rendering…</div>
                  ) : (
                    <div style={{ color: palette.muted }}>No narration yet.</div>
                  )
                ) : (
                  <div style={{ color: palette.muted }}>Expand to generate human narration (lab-only, no advice).</div>
                )}
              </Card>

              <div style={{ fontSize: 13, fontWeight: 600, color: palette.muted, textTransform: "uppercase", letterSpacing: 0.6 }}>
                Ayurvedic Reflection (Internal)
              </div>
              <Card
                title="Ayurvedic Reflection — Human Interpretation of Elemental & Energy Patterns"
                extra={
                  <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                    <label style={{ color: palette.muted, fontSize: 12 }}>
                      Anchor (days)
                      <select
                        value={ayurAnchorDays}
                        onChange={(e) => setAyurAnchorDays(Number(e.target.value) || 1500)}
                        style={{
                          marginLeft: 6,
                          padding: "4px 6px",
                          borderRadius: 6,
                          border: `1px solid ${palette.border}`,
                          background: "#0f1115",
                          color: "#ffffff",
                        }}
                      >
                        {[1500, 30, 14, 7].map((v) => (
                          <option key={v} value={v} style={{ color: palette.text }}>
                            {v}
                          </option>
                        ))}
                      </select>
                    </label>
                    <button
                      onClick={generateAyurvedicReflection}
                      disabled={ayurStatus === "loading"}
                      style={{
                        background: "#0f1115",
                        color: "#ffffff",
                        border: "1px solid #0f1115",
                        borderRadius: 6,
                        padding: "4px 8px",
                        cursor: "pointer",
                        opacity: ayurStatus === "loading" ? 0.7 : 1,
                      }}
                    >
                      {ayurStatus === "loading" ? "Generating…" : ayurStatus === "ready" ? "Regenerate" : "Generate"}
                    </button>
                  </div>
                }
              >
                <div style={{ color: palette.muted, fontSize: 12, marginBottom: 8 }}>
                  This reflection uses an additional interpretive lens to describe patterns in body, mind, and energy.
                  It is exploratory and does not offer advice or recommendations.
                </div>
                {ayurStatus === "error" && <div style={{ color: "#f87171", fontSize: 12 }}>{ayurError}</div>}
                {ayurStatus === "ready" && ayurReflection ? (
                  <div style={{ whiteSpace: "pre-wrap", lineHeight: 1.6 }}>{ayurReflection}</div>
                ) : ayurStatus === "loading" ? (
                  <div style={{ color: palette.muted, fontSize: 12 }}>Generating reflection…</div>
                ) : (
                  <div style={{ color: palette.muted, fontSize: 12 }}>No reflection yet. Click Generate to create one.</div>
                )}
              </Card>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 12, border: `1px solid ${palette.border}`, borderRadius: 12, padding: 12 }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: palette.muted, textTransform: "uppercase", letterSpacing: 0.6 }}>
                Personal Intelligence Snapshot
              </div>
              <Card
                title="Recognitions"
                extra={
                  <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                    <label style={{ color: palette.muted, fontSize: 12 }}>
                      Anchor (days)
                      <select
                        value={piWindow}
                        onChange={(e) => setPiWindow(Number(e.target.value) || 7)}
                        style={{
                          marginLeft: 6,
                          padding: "4px 6px",
                          borderRadius: 6,
                          border: `1px solid ${palette.border}`,
                          background: "#0f1115",
                          color: "#ffffff",
                        }}
                      >
                        {[1500, 30, 14, 7].map((v) => (
                          <option key={v} value={v} style={{ color: palette.text }}>
                            {v}
                          </option>
                        ))}
                      </select>
                    </label>
                    <button
                      onClick={async () => {
                        const next = !piOpen;
                        setPiOpen(next);
                        if (next) {
                          await loadPersonalIntelligence();
                        }
                      }}
                      style={{
                        background: "#0f1115",
                        color: "#ffffff",
                        border: "1px solid #0f1115",
                        borderRadius: 6,
                        padding: "4px 8px",
                        cursor: "pointer",
                      }}
                    >
                      {piOpen ? "Collapse" : "Expand"}
                    </button>
                  </div>
                }
              >
                {piStatus === "error" && <div style={{ color: "#f87171", fontSize: 12 }}>{piError}</div>}
                {piOpen ? (
                  piStatus === "loading" ? (
                    <div style={{ color: palette.muted }}>Loading recognitions…</div>
                  ) : piData ? (
                    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                      {/* Framing sentence */}
                      <div style={{ fontSize: 13, lineHeight: 1.6, color: palette.text }}>
                        These are stable patterns Sakhi has learned to recognize about you over time. They reflect continuity rather than momentary states.
                      </div>

                      {/* Anchor window display - human language */}
                      <div style={{ color: palette.muted, fontSize: 12 }}>
                        {piData?.timeframe?.anchor_days >= 365
                          ? "Anchor: long-term, rolling (spanning multiple years)"
                          : `Anchor: ${piData?.timeframe?.anchor_days ?? piWindow} days (rolling)`}
                      </div>
                      {piData?.timeframe?.anchor_days >= 365 && (
                        <div style={{ color: palette.muted, fontSize: 11, marginTop: -6 }}>
                          These patterns are not based on a single week.
                        </div>
                      )}

                      {/* Recognitions list */}
                      {(piData?.recognitions || []).length > 0 ? (
                        <ul style={{ paddingLeft: 18, margin: 0, display: "flex", flexDirection: "column", gap: 8 }}>
                          {(piData?.recognitions || []).map((line: string, idx: number) => (
                            <li key={idx} style={{ lineHeight: 1.6, color: palette.text }}>{line}</li>
                          ))}
                        </ul>
                      ) : (
                        <div style={{ color: palette.muted }}>No recognitions available for this window.</div>
                      )}

                      {/* Restraint signal */}
                      {(piData?.recognitions || []).length > 0 && (
                        <div style={{
                          color: palette.muted,
                          fontSize: 12,
                          fontStyle: "italic",
                          marginTop: 4,
                          paddingTop: 12,
                          borderTop: `1px solid ${palette.border}`
                        }}>
                          This is recognition, not advice. You can ask questions or request suggestions if you want.
                        </div>
                      )}
                      {(piData?.raw_recognitions || piData?.debug) && (
                        <details>
                          <summary style={{ cursor: "pointer", color: palette.muted, fontSize: 12 }}>How this recognition was formed</summary>
                          <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 6 }}>
                            {piData?.raw_recognitions ? (
                              <pre
                                style={{
                                  background: palette.surface,
                                  border: `1px solid ${palette.border}`,
                                  borderRadius: 10,
                                  padding: 10,
                                  fontSize: 12,
                                  color: palette.text,
                                  maxHeight: 220,
                                  overflow: "auto",
                                }}
                              >
                                {JSON.stringify(piData.raw_recognitions, null, 2)}
                              </pre>
                            ) : null}
                            {piData?.debug ? (
                              <pre
                                style={{
                                  background: palette.surface,
                                  border: `1px solid ${palette.border}`,
                                  borderRadius: 10,
                                  padding: 10,
                                  fontSize: 12,
                                  color: palette.text,
                                  maxHeight: 220,
                                  overflow: "auto",
                                }}
                              >
                                {JSON.stringify(piData.debug, null, 2)}
                              </pre>
                            ) : null}
                          </div>
                        </details>
                      )}
                    </div>
                  ) : (
                    <div style={{ color: palette.muted }}>No snapshot yet.</div>
                  )
                ) : (
                  <div style={{ color: palette.muted }}>Expand to load a personal intelligence snapshot (lab-only).</div>
                )}
              </Card>
            </div>

        </>
      </div>
    </div>
  );
}

function Card({
  title,
  children,
  extra,
}: {
  title: string;
  children: React.ReactNode;
  extra?: React.ReactNode;
}) {
  return (
    <div style={{ background: palette.card, border: `1px solid ${palette.border}`, borderRadius: 12, padding: 12, display: "flex", flexDirection: "column", gap: 8 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
        <div style={{ fontWeight: 600 }}>{title}</div>
        {extra ? <div style={{ fontSize: 12 }}>{extra}</div> : null}
      </div>
      {children}
    </div>
  );
}
