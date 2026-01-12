"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

const palette = {
  bg: "#0b1220",
  card: "#0f172a",
  border: "#1f2a44",
  text: "#e2e8f0",
  muted: "#94a3b8",
};

type MicroFlowsDetails = {
  person_id: string;
  mini_flows: any[];
  personal_model: any;
};

export default function MicroFlowsDetailsPage() {
  const params = useSearchParams();
  const [data, setData] = useState<MicroFlowsDetails | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const personId = params.get("person_id") || "";

  useEffect(() => {
    if (!personId) return;
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const url = new URL("/api/lab/micro-flows-details", window.location.origin);
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
        <h1 style={{ margin: 0, fontSize: 22 }}>Daily / Micro Flows Details (Lab)</h1>
        <div style={{ color: palette.muted, fontSize: 13 }}>Person: {personId || "—"}</div>
        {loading && <div style={{ color: palette.muted }}>Loading…</div>}
        {error && <div style={{ color: "#f87171" }}>{error}</div>}

        {data && (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <Card title="Mini flows (recent)">
              {data.mini_flows?.length ? (
                <ul style={{ paddingLeft: 16, margin: 0, display: "flex", flexDirection: "column", gap: 6 }}>
                  {data.mini_flows.map((row: any) => (
                    <li key={`${row.flow_date}-${row.created_at}`} style={{ color: palette.text }}>
                      <div style={{ fontSize: 12, color: palette.muted }}>{row.created_at}</div>
                      <div>Flow date: {row.flow_date}</div>
                      <div style={{ fontSize: 12, color: palette.muted }}>
                        Warmup: {row.warmup_step} • Focus: {row.focus_block_step} • Closure: {row.closure_step} • Reward: {row.optional_reward || "—"}
                      </div>
                      <div style={{ fontSize: 12, color: palette.muted }}>Rhythm slot: {row.rhythm_slot} • Source: {row.source}</div>
                    </li>
                  ))}
                </ul>
              ) : (
                <div style={{ color: palette.muted }}>None</div>
              )}
            </Card>

            <Card title="Personal model (mini flow state)">
              <pre style={{ background: "#0b1220", border: `1px solid ${palette.border}`, borderRadius: 10, padding: 10, fontSize: 12, color: palette.text, whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
                {JSON.stringify(data.personal_model || {}, null, 2)}
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
