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

type TaskWeaverDetails = {
  person_id: string;
  tasks: any[];
};

function TaskWeaverDetailsClient() {
  "use client";

  const params = useSearchParams();
  const [data, setData] = useState<TaskWeaverDetails | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const personId = params?.get("person_id") || "";

  useEffect(() => {
    if (!personId) return;
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const url = new URL("/api/lab/task-weaver-details", window.location.origin);
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
        <h1 style={{ margin: 0, fontSize: 22 }}>Task Weaver Details (Lab)</h1>
        <div style={{ color: palette.muted, fontSize: 13 }}>Person: {personId || "—"}</div>
        {loading && <div style={{ color: palette.muted }}>Loading…</div>}
        {error && <div style={{ color: "#f87171" }}>{error}</div>}

        {data && (
          <Card title="Tasks (energy / auto_priority)">
            {data.tasks?.length ? (
              <ul style={{ paddingLeft: 16, margin: 0, display: "flex", flexDirection: "column", gap: 6 }}>
                {data.tasks.map((t: any) => (
                  <li key={t.id} style={{ color: palette.text }}>
                    <div style={{ fontSize: 12, color: palette.muted }}>{t.updated_at}</div>
                    <div>{t.title}</div>
                    <div style={{ fontSize: 12, color: palette.muted }}>
                      status: {t.status} • horizon: {t.inferred_time_horizon || "today"} • auto_priority: {t.auto_priority} • energy_cost: {t.energy_cost} • emotional_fit: {t.emotional_fit || "—"}
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <div style={{ color: palette.muted }}>None</div>
            )}
          </Card>
        )}
      </div>
    </div>
  );
}

export default function TaskWeaverDetailsPage() {
  return <TaskWeaverDetailsClient />;
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ background: palette.card, border: `1px solid ${palette.border}`, borderRadius: 12, padding: 12, display: "flex", flexDirection: "column", gap: 8 }}>
      <div style={{ fontWeight: 600 }}>{title}</div>
      {children}
    </div>
  );
}
