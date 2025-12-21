"use client";

import { useEffect, useMemo, useState } from "react";

type Depth = "light" | "medium" | "deep";
type Verbosity = "brief" | "standard" | "detailed";

type Preferences = {
  reflection_depth: Depth;
  response_verbosity: Verbosity;
};

type TurnResponse = {
  reply?: string;
  moment_model?: { confidence?: number; recommended_companion_mode?: string };
  evidence_pack?: { anchors?: string[]; confidence?: number };
  deliberation_scaffold?: { options?: string[]; signals_used?: string[] };
};

const defaultPrefs: Preferences = {
  reflection_depth: "medium",
  response_verbosity: "standard",
};

export default function SessionPage() {
  const [input, setInput] = useState("");
  const [recognition, setRecognition] = useState<string | null>(null);
  const [insight, setInsight] = useState<string | null>(null);
  const [deliberation, setDeliberation] = useState<string[] | null>(null);
  const [prefs, setPrefs] = useState<Preferences>(defaultPrefs);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const loadPrefs = async () => {
      try {
        const res = await fetch("/api/preferences");
        if (!res.ok) return;
        const data = await res.json();
        if (!cancelled) {
          setPrefs({
            reflection_depth: data.reflection_depth ?? defaultPrefs.reflection_depth,
            response_verbosity: data.response_verbosity ?? defaultPrefs.response_verbosity,
          });
        }
      } catch {
        /* silent fallback */
      }
    };
    loadPrefs();
    return () => {
      cancelled = true;
    };
  }, []);

  const hasInsightGate = useMemo(() => {
    return (confidence?: number) => typeof confidence === "number" && confidence >= 0.7;
  }, []);

  const handleSubmit = async () => {
    if (!input.trim()) return;
    setSubmitting(true);
    setInsight(null);
    setDeliberation(null);
    try {
      const res = await fetch("/api/turn-v2", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: input,
          reflection_depth: prefs.reflection_depth,
          response_verbosity: prefs.response_verbosity,
        }),
      });
      const data = (await res.json()) as TurnResponse;
      const replyText = (data.reply || "").trim();
      setRecognition(replyText || null);

      if (hasInsightGate(data.moment_model?.confidence) && (data.evidence_pack?.anchors?.length ?? 0) > 0) {
        const firstAnchor = data.evidence_pack?.anchors?.[0];
        if (firstAnchor) {
          setInsight(`A thread that surfaced: ${firstAnchor}`);
        }
      }

      const mode = data.moment_model?.recommended_companion_mode;
      const hasUncertainty =
        /\?/.test(input) ||
        /\b(should|decide|whether|choose|unsure|uncertain|torn)\b/i.test(input);
      const scaffold = data.deliberation_scaffold;
      const options = Array.isArray(scaffold?.options) ? scaffold?.options : [];
      if (scaffold && options.length > 0 && mode && (mode === "clarify" || mode === "expand") && hasUncertainty) {
        setDeliberation(options);
      }
    } catch {
      setRecognition(null);
    } finally {
      setSubmitting(false);
    }
  };

  const handleFits = () => {
    // Recognition acknowledged; nothing further for now.
  };

  const handleNotQuite = () => {
    setRecognition(null);
    setInsight(null);
    setDeliberation(null);
    setInput("");
  };

  return (
    <main
      className="min-h-screen w-full flex items-center justify-center px-6 py-16"
      style={{ backgroundColor: "#F6F4F0", color: "#2F2F2F" }}
    >
      <section className="w-full max-w-xl space-y-10 text-left">
        <h1 className="text-3xl font-light tracking-tight">What feels unfinished right now?</h1>

        <div className="space-y-4">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={submitting}
            className="w-full min-h-[140px] border border-black/10 bg-transparent p-3 text-base leading-relaxed focus:outline-none focus:ring-0"
            aria-label="Your words"
          />
          <button
            type="button"
            onClick={handleSubmit}
            disabled={submitting}
            className="border border-black/10 text-sm font-medium px-6 py-2 rounded-sm hover:opacity-80 focus:outline-none focus:ring-0 disabled:opacity-50"
            aria-label="Send"
          >
            {submitting ? "..." : "Send"}
          </button>
        </div>

        {recognition && (
          <div className="space-y-4 pt-4">
            <p className="text-base leading-relaxed" style={{ color: "#2F2F2F" }}>
              {recognition}
            </p>

            <div className="flex gap-3">
              <button
                type="button"
                onClick={handleFits}
                className="border border-black/10 text-sm font-medium px-4 py-2 rounded-sm hover:opacity-80 focus:outline-none focus:ring-0"
              >
                Fits
              </button>
              <button
                type="button"
                onClick={handleNotQuite}
                className="border border-black/10 text-sm font-medium px-4 py-2 rounded-sm hover:opacity-80 focus:outline-none focus:ring-0"
              >
                Not quite
              </button>
            </div>

            {insight && (
              <p className="text-sm leading-relaxed" style={{ color: "#2F2F2F" }}>
                {insight}
              </p>
            )}

            {deliberation && (
              <div className="space-y-2 pt-2">
                {deliberation.map((line, idx) => (
                  <p key={`${line}-${idx}`} className="text-sm leading-relaxed" style={{ color: "#2F2F2F" }}>
                    {line}
                  </p>
                ))}
              </div>
            )}
          </div>
        )}
      </section>
    </main>
  );
}
