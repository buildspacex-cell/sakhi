"use client";

import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import type React from "react";

type WeeklyItem = {
  week_start?: string;
  week_end?: string;
  highlights?: string;
  drift_score?: number;
  top_themes?: { theme?: string; weight?: number }[] | string;
  notes_count?: number;
  dominant_mood?: string;
  overview?: string;
  recovery?: string;
  changes?: string;
  body?: string;
  mind?: string;
  emotion?: string;
  energy?: string;
  work?: string;
  confidence_note?: string;
  reflection?: {
    overview: string;
    recovery?: string;
    changes?: string;
    body?: string;
    mind?: string;
    emotion?: string;
    energy?: string;
    work?: string;
    confidence_note?: string;
  };
  episodic_stats?: { episode_count?: number; distinct_days?: number };
  confidence?: number;
  delta_stats?: Record<string, any>;
  contrast_stats?: Record<string, any>;
};

const DEFAULT_SYSTEM_PROMPT = `You are a reflective companion helping a person gently look back on their week.

Your role is not to analyze or judge, but to mirror what seems to have happened in a grounded, human way.

Write as one thoughtful human speaking to another.
Natural. Warm. Clear. Not clinical. Not instructional.

You are working from structured weekly signals — not raw text.
You must stay faithful to the signals provided.

Tone guidelines:
- Speak plainly and conversationally.
- Avoid phrases like “suggesting”, “indicating”, “dimension”, “trajectory”.
- Prefer simple human phrasing: “It felt like…”, “There was a sense that…”, “The week carried…”.
- Be calm and steady, not enthusiastic or dramatic.
- Do not hedge excessively (“it may be”, “it appears”) unless confidence is explicitly low.

Constraints (do not violate):
- Do not give advice.
- Do not speculate on causes.
- Do not use identity or trait language.
- Do not invent experiences.
- Do not refer to metrics, scores, or dimensions explicitly.

The goal is for the reader to feel:
“Yes — that sounds like my week.”`;

const DEFAULT_USER_PROMPT = `You are given structured, language-free weekly signals.
- Week window: {week_window}
- Weekly signals JSON: {signals_json}
- High-confidence longitudinal trends JSON: {longitudinal_json}

Write:
- One short opening reflection on the week as a whole.
- If specific areas stand out (body, mind, emotion, energy, work), reflect on them naturally in separate short paragraphs.
- If nothing stands out for an area, leave it empty.

Do not label sections in the text. The structure will be applied outside the language.

Constraints:
- Do NOT add insights beyond the provided signals.
- Do NOT give advice or speculate on causes.
- Do NOT use bullet points.
- Do NOT use identity or trait language.

Return JSON only:
{
  "period": "weekly",
  "window": "{week_window}",
  "overview": "...",
  "body": "...",
  "mind": "...",
  "emotion": "...",
  "energy": "...",
  "work": "...",
  "confidence_note": "..."
}
`;

const palette = {
  bg: "#0e0f12",
  fg: "#f4f4f5",
  muted: "#a1a1aa",
  accent: "#e5e7eb",
  divider: "#27272a",
  card: "#141518",
  cardSoft: "#16181d",
};

const baseFont = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Inter, Helvetica, Arial, sans-serif';

const pageStyle: React.CSSProperties = {
  minHeight: "100vh",
  background: palette.bg,
  color: palette.fg,
  display: "flex",
  justifyContent: "center",
  padding: "32px 32px 96px",
  fontFamily: baseFont,
};

const containerStyle: React.CSSProperties = {
  maxWidth: "800px",
  width: "100%",
  textAlign: "left",
};

const brandStyle: React.CSSProperties = {
  textAlign: "center",
  fontSize: "14px",
  letterSpacing: "0.14em",
  textTransform: "uppercase",
  color: palette.muted,
  marginBottom: "40px",
};

const headerRowStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  gap: "16px",
  marginBottom: "20px",
};

const metaStyle: React.CSSProperties = {
  fontSize: "13px",
  color: palette.muted,
};

const voiceControlStyle: React.CSSProperties = {
  display: "flex",
  gap: "10px",
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
  fontFamily: baseFont,
};

const voiceButtonSecondaryStyle: React.CSSProperties = {
  ...voiceButtonStyle,
  color: palette.muted,
};

const devSelectStyle: React.CSSProperties = {
  padding: "8px 12px",
  borderRadius: "10px",
  border: `1px solid ${palette.divider}`,
  background: palette.card,
  color: palette.accent,
  fontSize: "13px",
  fontFamily: baseFont,
};

const promptContainerStyle: React.CSSProperties = {
  marginTop: "12px",
  marginBottom: "26px",
  padding: "18px",
  borderRadius: "14px",
  border: `1px dashed ${palette.divider}`,
  background: palette.cardSoft,
  color: palette.accent,
};

const promptLabelStyle: React.CSSProperties = {
  fontSize: "13px",
  letterSpacing: "0.05em",
  textTransform: "uppercase",
  color: palette.muted,
  marginBottom: "8px",
};

const promptTextareaStyle: React.CSSProperties = {
  width: "100%",
  minHeight: "140px",
  borderRadius: "10px",
  border: `1px solid ${palette.divider}`,
  padding: "10px 12px",
  fontSize: "14px",
  lineHeight: 1.5,
  background: "#0b0c0f",
  color: palette.accent,
  resize: "vertical",
  fontFamily: baseFont,
};

const summaryCardStyle: React.CSSProperties = {
  background: palette.card,
  border: `1px solid ${palette.divider}`,
  borderRadius: "18px",
  padding: "28px",
  fontSize: "14px",
  lineHeight: 1.5,
  color: palette.accent,
  textAlign: "center",
  marginBottom: "26px",
  fontFamily: baseFont,
};

const summaryIntroStyle: React.CSSProperties = {
  fontSize: "13px",
  color: palette.muted,
  textAlign: "center",
  marginBottom: "10px",
  fontFamily: baseFont,
};

const tabsRowStyle: React.CSSProperties = {
  display: "flex",
  gap: "8px",
  flexWrap: "wrap",
  marginBottom: "10px",
};

const tabStyle: React.CSSProperties = {
  padding: "8px 14px",
  borderRadius: "999px",
  border: `1px solid ${palette.divider}`,
  background: "transparent",
  color: palette.accent,
  fontSize: "13px",
  cursor: "pointer",
  fontFamily: baseFont,
};

const tabActiveStyle: React.CSSProperties = {
  ...tabStyle,
  background: palette.card,
  borderColor: "#3b82f6",
  color: palette.fg,
};

const tabDisabledStyle: React.CSSProperties = {
  ...tabStyle,
  color: palette.muted,
  borderColor: palette.divider,
  cursor: "not-allowed",
  opacity: 0.7,
};

const dimensionPanelStyle: React.CSSProperties = {
  background: palette.card,
  border: `1px solid ${palette.divider}`,
  borderRadius: "14px",
  padding: "18px 20px",
  fontSize: "14px",
  lineHeight: 1.5,
  color: palette.accent,
  minHeight: "120px",
  marginBottom: "24px",
  fontFamily: baseFont,
};

const lowEvidenceBannerStyle: React.CSSProperties = {
  marginBottom: "18px",
  padding: "12px 14px",
  borderRadius: "12px",
  border: `1px solid ${palette.divider}`,
  background: palette.cardSoft,
  color: palette.accent,
  fontSize: "13px",
  lineHeight: 1.5,
  fontFamily: baseFont,
};

export default function ExperienceWeeklyPage() {
  const searchParams = useSearchParams();
  const [weekly, setWeekly] = useState<WeeklyItem | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [systemPrompt, setSystemPrompt] = useState<string>(DEFAULT_SYSTEM_PROMPT);
  const [userPrompt, setUserPrompt] = useState<string>(DEFAULT_USER_PROMPT);
  const [activeTab, setActiveTab] = useState<string | null>(null);
  const [showDebugPanel, setShowDebugPanel] = useState<boolean>(
    process.env.NODE_ENV !== "production" && (searchParams.get("debug") === "true" || process.env.NODE_ENV !== "production")
  );
  const DEV_USERS = useMemo(
    () => ({
      a: { label: "Vidhya" },
      b: { label: "Ravi" },
    }),
    []
  );
  const searchUser = searchParams.get("user");
  const [devUser, setDevUser] = useState<string>(searchUser || "a");

  const debugEnabled = useMemo(
    () => searchParams.get("debug") === "true" || process.env.NODE_ENV !== "production",
    [searchParams]
  );

  useEffect(() => {
    if (typeof window !== "undefined") {
      const stored = window.localStorage.getItem("dev_user");
      if (!searchUser && stored && stored !== devUser) {
        setDevUser(stored);
        return;
      }
      window.localStorage.setItem("dev_user", devUser);
      const url = new URL(window.location.href);
      url.searchParams.set("user", devUser);
      window.history.replaceState({}, "", url.toString());
    }
  }, [devUser, searchUser]);

  const toDate = (value?: string) => {
    if (!value) return "—";
    const d = new Date(value);
    return Number.isNaN(d.getTime()) ? value : d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
  };

  const fetchWeekly = async () => {
    setError(null);
    setLoading(true);
    try {
      const url = `/api/memory/weekly?user=${encodeURIComponent(devUser)}&limit=1`;
      if (typeof window !== "undefined") {
        // Client-side debug: see exactly what we call and receive.
        console.log("WEEKLY_UI_DEBUG: fetchUrl", url);
      }
      const res = await fetch(url);
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      if (typeof window !== "undefined") {
        console.log("WEEKLY_UI_DEBUG: weeklyResponse", data);
      }
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
          recovery: data.reflection.recovery,
          changes: data.reflection.changes,
          drift_score: undefined,
          top_themes: data.theme_stats,
          notes_count: undefined,
          dominant_mood: undefined,
          reflection: data.reflection,
        };
      }
      setWeekly(item || null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load weekly reflection");
    } finally {
      setLoading(false);
    }
  };

  const triggerWeekly = async () => {
    setError(null);
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.set("user", devUser);
      params.set("limit", "1");
      params.set("debug", "true");
      if (systemPrompt) params.set("system_prompt_override", systemPrompt);
      if (userPrompt) params.set("user_prompt_override", userPrompt);

      const res = await fetch(`/api/memory/weekly?${params.toString()}`, {
        method: "GET",
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      if (typeof window !== "undefined") {
        console.log("WEEKLY_UI_DEBUG: synthesisResponse", data);
      }
      let next: WeeklyItem | null = null;
      if (data?.reflection && typeof data.reflection === "object") {
        const windowStr = typeof data?.window === "string" ? data.window : "";
        const windowParts = windowStr.includes("→") ? windowStr.split("→").map((p: string) => p.trim()) : [];
        next = {
          week_start: data.week_start || windowParts[0],
          week_end: data.week_end || windowParts[1],
          highlights: data.reflection.overview || "",
          recovery: data.reflection.recovery,
          changes: data.reflection.changes,
          drift_score: undefined,
          top_themes: data.theme_stats,
          notes_count: undefined,
          dominant_mood: undefined,
          reflection: data.reflection,
        };
      } else if (Array.isArray(data?.items) && data.items.length) {
        next = data.items[0] as WeeklyItem;
      }
      setWeekly(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate weekly reflection");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (devUser) fetchWeekly();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [devUser]);

  const reflection = useMemo(() => {
    const refCandidate = weekly?.reflection;
    if (refCandidate && typeof refCandidate === "object") {
      return {
        overview: refCandidate.overview || weekly?.highlights || "",
        recovery: refCandidate.recovery || "",
        changes: refCandidate.changes || "",
        body: refCandidate.body || "",
        mind: refCandidate.mind || "",
        emotion: refCandidate.emotion || "",
        energy: refCandidate.energy || "",
        work: refCandidate.work || "",
        confidence_note: refCandidate.confidence_note || "",
      };
    }
    return {
      overview: weekly?.overview || weekly?.highlights || "",
      recovery: weekly?.recovery || "",
      changes: weekly?.changes || "",
      body: weekly?.body || "",
      mind: weekly?.mind || "",
      emotion: weekly?.emotion || "",
      energy: weekly?.energy || "",
      work: weekly?.work || "",
      confidence_note: weekly?.confidence_note || "",
    };
  }, [weekly]);

  const episodicStats = useMemo(() => {
    const stats = weekly?.episodic_stats;
    if (stats && typeof stats === "object") return stats as Record<string, any>;
    if (typeof stats === "string") {
      try {
        const parsed = JSON.parse(stats);
        if (parsed && typeof parsed === "object") return parsed as Record<string, any>;
      } catch {
        return {};
      }
    }
    return {};
  }, [weekly]);

  const weeklyConfidence = useMemo(() => {
    const c = weekly?.confidence;
    const asNum = typeof c === "number" ? c : Number(c);
    return Number.isFinite(asNum) ? Number(asNum) : 0;
  }, [weekly]);

  const deltaStats = useMemo(() => (weekly?.delta_stats && typeof weekly.delta_stats === "object" ? weekly.delta_stats : {}), [weekly]);
  const contrastStats = useMemo(
    () => (weekly?.contrast_stats && typeof weekly.contrast_stats === "object" ? weekly.contrast_stats : {}),
    [weekly]
  );

  const lowEvidence = useMemo(() => {
    const episodes = Number(episodicStats?.episode_count ?? 0);
    const distinct = Number(episodicStats?.distinct_days ?? 0);
    return episodes < 3 || distinct < 2 || weeklyConfidence < 0.3;
  }, [episodicStats, weeklyConfidence]);

  const hasMeaningfulChange = useMemo(() => {
    const deltaValues = Object.values(deltaStats || {}).map((v) => (typeof v === "string" ? v.toLowerCase() : String(v || "").toLowerCase()));
    const anyDelta = deltaValues.some((v) => v && v !== "flat");
    const anyContrast = Boolean((contrastStats as any)?.work_overload || Object.keys(contrastStats || {}).length);
    return anyDelta || anyContrast || weeklyConfidence >= 0.35;
  }, [deltaStats, contrastStats, weeklyConfidence]);

  const changeText = useMemo(() => reflection.changes?.trim() || "", [reflection.changes]);

  const tabs = useMemo(
    () =>
      [
        { key: "body", label: "Body", content: reflection.body },
        { key: "mind", label: "Mind", content: reflection.mind },
        { key: "emotion", label: "Emotion", content: reflection.emotion },
        { key: "energy", label: "Energy", content: reflection.energy },
        { key: "work", label: "Work", content: reflection.work },
      ],
    [reflection]
  );

  useEffect(() => {
    if (!activeTab || !tabs.some((t) => t.key === activeTab)) {
      setActiveTab(tabs[0].key);
    }
  }, [tabs, activeTab]);

  const devLabel = DEV_USERS[devUser]?.label || devUser;

  return (
    <div style={pageStyle}>
      <div style={containerStyle}>
        <div style={brandStyle}>Sakhi</div>

        <div style={headerRowStyle}>
          <div>
            <div style={{ fontSize: "18px", fontWeight: 600, color: palette.fg }}>
              Weekly Reflection — {devLabel} (dev slot)
            </div>
            <div style={metaStyle}>
              {weekly ? `${toDate(weekly.week_start)} → ${toDate(weekly.week_end)}` : "Pending window"}
              {weekly?.notes_count ? ` • ${weekly.notes_count} notes` : ""}
              {weekly?.dominant_mood ? ` • Mood ${weekly.dominant_mood}` : ""}
              {weekly?.drift_score != null ? ` • Drift ${Math.round(Number(weekly.drift_score) * 100)}%` : ""}
            </div>
          </div>
          <div style={voiceControlStyle}>
            <select
              value={devUser}
              onChange={(e) => setDevUser(e.target.value)}
              style={devSelectStyle}
            >
              {Object.entries(DEV_USERS).map(([key, value]) => (
                <option value={key} key={key}>
                  {value.label}
                </option>
              ))}
            </select>
            <button type="button" style={voiceButtonStyle} onClick={triggerWeekly} disabled={loading}>
              {loading ? "Working…" : "Generate weekly now"}
            </button>
          </div>
        </div>

        {debugEnabled && (
          <>
            <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: "8px" }}>
              <button
                type="button"
                style={voiceButtonSecondaryStyle}
                onClick={() => setShowDebugPanel((prev) => !prev)}
              >
                {showDebugPanel ? "Hide debug prompts" : "Show debug prompts"}
              </button>
            </div>
            {showDebugPanel && (
              <div style={promptContainerStyle}>
                <div style={promptLabelStyle}>Debug / Testing (prompts are not saved)</div>
                <div style={{ display: "flex", justifyContent: "space-between", gap: "12px", flexWrap: "wrap" }}>
                  <div style={{ flex: "1 1 280px" }}>
                    <div style={promptLabelStyle}>LLM System Prompt (editable)</div>
                    <textarea
                      style={promptTextareaStyle}
                      value={systemPrompt}
                      onChange={(e) => setSystemPrompt(e.target.value)}
                    />
                  </div>
                  <div style={{ flex: "1 1 280px" }}>
                    <div style={promptLabelStyle}>
                      User Prompt Template (supports {"{week_window}, {signals_json}, {longitudinal_json}"})
                    </div>
                    <textarea
                      style={promptTextareaStyle}
                      value={userPrompt}
                      onChange={(e) => setUserPrompt(e.target.value)}
                    />
                  </div>
                </div>
              </div>
            )}
          </>
        )}

        {lowEvidence && (
          <div style={lowEvidenceBannerStyle}>
            From the few notes you shared this week…
          </div>
        )}

        {reflection?.overview?.trim() && (
          <>
            <div style={summaryIntroStyle}>Here’s how Sakhi sees your week right now.</div>
            <div style={summaryCardStyle}>
              {reflection.overview}
            </div>
          </>
        )}

        {hasMeaningfulChange && changeText && (
          <div style={{ ...dimensionPanelStyle, marginBottom: "20px" }}>
            <div style={{ fontSize: "12px", letterSpacing: "0.08em", textTransform: "uppercase", color: palette.muted, marginBottom: "6px" }}>
              What’s Changing
            </div>
            <div>{changeText}</div>
          </div>
        )}

        <div style={tabsRowStyle}>
          {tabs.map((tab) => {
            const enabled = Boolean(tab.content && tab.content.trim().length > 0);
            const active = activeTab === tab.key;
            return (
              <button
                key={tab.key}
                type="button"
                style={active ? (enabled ? tabActiveStyle : tabDisabledStyle) : enabled ? tabStyle : tabDisabledStyle}
                onClick={() => setActiveTab(tab.key)}
                disabled={!enabled}
              >
                {tab.label}
              </button>
            );
          })}
        </div>
        <div style={dimensionPanelStyle}>
          {(() => {
            const current = tabs.find((t) => t.key === activeTab);
            const enabled = Boolean(current?.content && current.content.trim().length > 0);
            if (enabled) return current?.content;
            return (
              <div>
                There isn’t enough signal here yet to reflect on this area.
                <div style={{ marginTop: "6px", color: palette.muted, fontSize: "12px" }}>
                  More notes over time help this take shape.
                </div>
              </div>
            );
          })()}
        </div>
      </div>
    </div>
  );
}
