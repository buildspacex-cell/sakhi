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

type AnalyticsDetails = {
  person_id: string;
  analytics_cache: any[];
  system_events: any[];
};

function AnalyticsCalibrationDetailsClient() {
  "use client";

  const params = useSearchParams();
  const [data, setData] = useState<AnalyticsDetails | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const personId = params?.get("person_id") || "";

  useEffect(() => {
    if (!personId) return;
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const url = new URL("/api/lab/analytics-calibration-details", window.location.origin);
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
        <h1 style={{ margin: 0, fontSize: 22 }}>Analytics / Calibration Details (Lab)</h1>
        <div style={{ color: palette.muted, fontSize: 13 }}>Person: {personId || "—"}</div>
        {loading && <div style={{ color: palette.muted }}>Loading…</div>}
        {error && <div style={{ color: "#f87171" }}>{error}</div>}

        {data && (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <Card title="Analytics cache">
              {data.analytics_cache?.length ? (
                <ul style={{ paddingLeft: 16, margin: 0, display: "flex", flexDirection: "column", gap: 6 }}>
                  {data.analytics_cache.map((row: any, idx: number) => (
                    <li key={idx} style={{ color: palette.text }}>
                      <div style={{ fontSize: 12, color: palette.muted }}>{row.computed_at}</div>
                      <div>Key: {row.key}</div>
                      <div style={{ fontSize: 12, color: palette.muted }}>{JSON.stringify(row.payload)}</div>
                    </li>
                  ))}
                </ul>
              ) : (
                <div style={{ color: palette.muted }}>None</div>
              )}
            </Card>

            <Card title="System events">
              {data.system_events?.length ? (
                <ul style={{ paddingLeft: 16, margin: 0, display: "flex", flexDirection: "column", gap: 6 }}>
                  {data.system_events.map((row: any, idx: number) => (
                    <li key={idx} style={{ color: palette.text }}>
                      <div style={{ fontSize: 12, color: palette.muted }}>{row.ts}</div>
                      <div>Kind: {row.kind}</div>
                      <div style={{ fontSize: 12, color: palette.muted }}>{JSON.stringify(row.payload)}</div>
                    </li>
                  ))}
                </ul>
              ) : (
                <div style={{ color: palette.muted }}>None</div>
              )}
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}

export default function AnalyticsCalibrationDetailsPage() {
  return <AnalyticsCalibrationDetailsClient />;
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ background: palette.card, border: `1px solid ${palette.border}`, borderRadius: 12, padding: 12, display: "flex", flexDirection: "column", gap: 8 }}>
      <div style={{ fontWeight: 600 }}>{title}</div>
      {children}
    </div>
  );
}
