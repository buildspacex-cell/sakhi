import React from "react";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ??
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  "http://localhost:8000";

type SystemAudit = {
  audit_time: string | null;
  journal_latest: string | null;
  journal_count: number | null;
  embedding_latest: string | null;
  embedding_count: number | null;
  reflections_latest: string | null;
  reflections_count: number | null;
  meta_latest: string | null;
  meta_count: number | null;
  personal_model_latest: string | null;
  forecast_latest: string | null;
  forecast_count: number | null;
  theme_links_latest: string | null;
  theme_links_count: number | null;
  presence_latest: string | null;
  presence_count: number | null;
  dialog_latest: string | null;
  dialog_count: number | null;
  analytics_latest: string | null;
  analytics_count: number | null;
  system_event_latest: string | null;
  system_event_count: number | null;
  debug_latest: string | null;
  debug_count: number | null;
};

type MetricKey = keyof SystemAudit;

type MetricDescriptor = {
  label: string;
  key: MetricKey;
  type: "datetime" | "count";
};

const GROUPS: Array<{
  title: string;
  description: string;
  metrics: MetricDescriptor[];
}> = [
  {
    title: "Journals & Embeddings",
    description: "Freshness of written reflections and their vector indexes.",
    metrics: [
      { label: "Journal Latest", key: "journal_latest", type: "datetime" },
      { label: "Journal Count", key: "journal_count", type: "count" },
      { label: "Embedding Latest", key: "embedding_latest", type: "datetime" },
      { label: "Embedding Count", key: "embedding_count", type: "count" },
    ],
  },
  {
    title: "Reflections & Meta Scores",
    description: "LLM reflection outputs and coherence scoring cadence.",
    metrics: [
      { label: "Reflection Latest", key: "reflections_latest", type: "datetime" },
      { label: "Reflection Count", key: "reflections_count", type: "count" },
      { label: "Meta Score Latest", key: "meta_latest", type: "datetime" },
      { label: "Meta Score Count", key: "meta_count", type: "count" },
      { label: "Personal Model Latest", key: "personal_model_latest", type: "datetime" },
    ],
  },
  {
    title: "Forecasts & Themes",
    description: "Weekly rhythm predictions and downstream linkages.",
    metrics: [
      { label: "Forecast Latest", key: "forecast_latest", type: "datetime" },
      { label: "Forecast Count", key: "forecast_count", type: "count" },
      { label: "Theme Links Latest", key: "theme_links_latest", type: "datetime" },
      { label: "Theme Links Count", key: "theme_links_count", type: "count" },
    ],
  },
  {
    title: "Presence & Dialog State",
    description: "Continuity layers that keep conversations grounded.",
    metrics: [
      { label: "Presence Latest", key: "presence_latest", type: "datetime" },
      { label: "Presence Count", key: "presence_count", type: "count" },
      { label: "Dialog Latest", key: "dialog_latest", type: "datetime" },
      { label: "Dialog Count", key: "dialog_count", type: "count" },
    ],
  },
  {
    title: "System Telemetry",
    description: "High-level signals for analytics, events, and debug traces.",
    metrics: [
      { label: "Analytics Latest", key: "analytics_latest", type: "datetime" },
      { label: "Analytics Count", key: "analytics_count", type: "count" },
      { label: "System Event Latest", key: "system_event_latest", type: "datetime" },
      { label: "System Event Count", key: "system_event_count", type: "count" },
      { label: "Debug Latest", key: "debug_latest", type: "datetime" },
      { label: "Debug Count", key: "debug_count", type: "count" },
    ],
  },
];

async function fetchSystemAudit(): Promise<SystemAudit | null> {
  if (!API_BASE) {
    console.error("Missing NEXT_PUBLIC_API_URL");
    return null;
  }

  try {
    const response = await fetch(`${API_BASE}/system/audit`, {
      cache: "no-store",
    });

    if (!response.ok) {
      const body = await response.text().catch(() => response.statusText);
      console.error("system/audit failed", response.status, body);
      return null;
    }

    return (await response.json()) as SystemAudit;
  } catch (error) {
    console.error("system/audit request error", error);
    return null;
  }
}

const dateFormatter = new Intl.DateTimeFormat("en-US", {
  year: "numeric",
  month: "short",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
});

function formatMetric(value: string | number | null, type: MetricDescriptor["type"]) {
  if (value === null || value === undefined) {
    return "—";
  }

  if (type === "count") {
    return new Intl.NumberFormat("en-US").format(Number(value));
  }

  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? String(value) : dateFormatter.format(parsed);
}

export default async function SystemAuditPage() {
  const data = await fetchSystemAudit();

  return (
    <div className="min-h-screen bg-slate-50 p-8">
      <div className="mx-auto max-w-5xl space-y-6">
        <header className="space-y-2">
          <p className="text-sm uppercase tracking-[0.2em] text-slate-500">Observability</p>
          <h1 className="text-3xl font-semibold text-slate-900">System Audit</h1>
          <p className="text-slate-600">
            Snapshot of the latest journal, reflection, and telemetry activity pulled from
            the `/system/audit` endpoint.
          </p>
          <p className="text-sm text-slate-500">
            Last refreshed:{" "}
            <span className="font-medium text-slate-800">
              {data ? formatMetric(data.audit_time ?? null, "datetime") : "Unavailable"}
            </span>
          </p>
        </header>

        {!data && (
          <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-rose-800">
            Unable to load audit data. Confirm the API is reachable and try again.
          </div>
        )}

        {data && (
          <div className="grid gap-6 md:grid-cols-2">
            {GROUPS.map((group) => (
              <section key={group.title} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                <div className="mb-4">
                  <h2 className="text-lg font-semibold text-slate-900">{group.title}</h2>
                  <p className="text-sm text-slate-500">{group.description}</p>
                </div>
                <dl className="space-y-3">
                  {group.metrics.map((metric) => (
                    <div key={metric.key} className="flex items-baseline justify-between border-b border-slate-100 pb-2 last:border-b-0 last:pb-0">
                      <dt className="text-sm text-slate-500">{metric.label}</dt>
                      <dd className="text-sm font-medium text-slate-900">
                        {formatMetric(data[metric.key], metric.type)}
                      </dd>
                    </div>
                  ))}
                </dl>
              </section>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
