"use client";

export const dynamic = "force-dynamic";
export const revalidate = 0;

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

const palette = {
  bg: "#0b1220",
  card: "#0f172a",
  border: "#1f2a44",
  text: "#e2e8f0",
  muted: "#94a3b8",
};

type MemorySpineDetails = {
  person_id: string;
  weekly_summaries: any[];
  weekly_signals: any[];
  personal_model_long_term: any;
  personal_model_updated_at?: string;
};

export default function MemorySpineDetailsPage() {
  const params = useSearchParams();
  const [data, setData] = useState<MemorySpineDetails | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const personId = params.get("person_id") || "";

  useEffect(() => {
    if (!personId) return;
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const url = new URL("/api/lab/memory-spine-details", window.location.origin);
        url.searchParams.set("person_id", personId);
        const res = await fetch(url.toString());
        const payload = await res.json();
        if (!res.ok) throw new Error(payload?.error || res.statusText || "Failed to load");
        setData(payload);
      } catch (err: any) {
        setError(err?.message || "Failed to load");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [personId]);

  return (
    <div style={{ minHeight: "100vh", background: palette.bg, color: palette.text, padding: 20, fontFamily: "Inter, system-ui, -apple-system, sans-serif" }}>
      <div style={{ maxWidth: 1100, margin: "0 auto", display: "flex", flexDirection: "column", gap: 12 }}>
        <h1 style={{ margin: 0, fontSize: 22 }}>Memory Spine Details (Lab)</h1>
        <div style={{ color: palette.muted, fontSize: 13 }}>Person: {personId || "—"}</div>
        {loading && <div style={{ color: palette.muted }}>Loading…</div>}
        {error && <div style={{ color: "#f87171" }}>{error}</div>}

        {data && (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <Card title="Weekly summaries">
              {data.weekly_summaries?.length ? (
                <ul style={{ paddingLeft: 16, margin: 0, display: "flex", flexDirection: "column", gap: 6 }}>
                  {data.weekly_summaries.map((row: any) => (
                    <li key={`${row.week_start}-${row.week_end}`} style={{ color: palette.text }}>
                      <div style={{ fontSize: 12, color: palette.muted }}>{row.created_at}</div>
                      <div>
                        {row.week_start} → {row.week_end}
                      </div>
                      <div style={{ fontSize: 12, color: palette.muted }}>{JSON.stringify(row.summary)}</div>
                    </li>
                  ))}
                </ul>
              ) : (
                <div style={{ color: palette.muted }}>None</div>
              )}
            </Card>

            <Card title="Weekly signals">
              {data.weekly_signals?.length ? (
                <ul style={{ paddingLeft: 16, margin: 0, display: "flex", flexDirection: "column", gap: 6 }}>
                  {data.weekly_signals.map((row: any) => (
                    <li key={`${row.week_start}-${row.week_end}`} style={{ color: palette.text }}>
                      <div style={{ fontSize: 12, color: palette.muted }}>{row.created_at}</div>
                      <div>
                        {row.week_start} → {row.week_end}
                      </div>
                      <div style={{ fontSize: 12, color: palette.muted }}>Confidence: {row.confidence}</div>
                    </li>
                  ))}
                </ul>
              ) : (
                <div style={{ color: palette.muted }}>None</div>
              )}
            </Card>

            <Card title="Personal model long-term">
              <pre style={{ background: "#0b1220", border: `1px solid ${palette.border}`, borderRadius: 10, padding: 10, fontSize: 12, color: palette.text, whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
                {JSON.stringify({ updated_at: data.personal_model_updated_at, long_term: data.personal_model_long_term }, null, 2)}
              </pre>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ background: palette.card, border: `1px solid ${palette.border}`, borderRadius: 12, padding: 12, display: "flex", flexDirection: "column", gap: 8 }}>
      <div style={{ fontWeight: 600 }}>{title}</div>
      {children}
    </div>
  );
}
