"use client";

import React, { useState } from "react";
import useSWR from "swr";
import Link from "next/link";
import {
  normalizeSoulState,
  summarizeSoul,
  timelineSeries,
} from "@ui/soulViewModel";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  LineChart,
  Line,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  PieChart,
  Pie,
  Cell,
  RadialBarChart,
  RadialBar,
  Treemap,
} from "recharts";

// Recharts types can clash with React 18 JSX inference in strict TS; cast to loosen.
const ResponsiveContainerAny = ResponsiveContainer as unknown as React.ComponentType<any>;
const RadialBarChartAny = RadialBarChart as unknown as React.ComponentType<any>;
const RadialBarAny = RadialBar as unknown as React.ComponentType<any>;
const BarChartAny = BarChart as unknown as React.ComponentType<any>;
const BarAny = Bar as unknown as React.ComponentType<any>;
const PieChartAny = PieChart as unknown as React.ComponentType<any>;
const PieAny = Pie as unknown as React.ComponentType<any>;
const LineChartAny = LineChart as unknown as React.ComponentType<any>;
const LineAny = Line as unknown as React.ComponentType<any>;
const PolarGridAny = PolarGrid as unknown as React.ComponentType<any>;
const LegendAny = Legend as unknown as React.ComponentType<any>;
const TooltipAny = Tooltip as unknown as React.ComponentType<any>;
const XAxisAny = XAxis as unknown as React.ComponentType<any>;
const YAxisAny = YAxis as unknown as React.ComponentType<any>;
const PolarAngleAxisAny = PolarAngleAxis as unknown as React.ComponentType<any>;
const PolarRadiusAxisAny = PolarRadiusAxis as unknown as React.ComponentType<any>;
const RadarChartAny = RadarChart as unknown as React.ComponentType<any>;
const RadarAny = Radar as unknown as React.ComponentType<any>;
const TreemapAny = Treemap as unknown as React.ComponentType<any>;
const CellAny = Cell as unknown as React.ComponentType<any>;

const fetcher = (url: string) => fetch(url).then((r) => r.json());
const swrOpts = { fetcher, dedupingInterval: 60_000, revalidateOnFocus: false };

export default function SoulDashboard() {
  const [selectedValue, setSelectedValue] = useState<string | null>(null);
  const { data: state } = useSWR("/soul/state/demo", swrOpts);
  const { data: summary } = useSWR("/soul/summary/demo", swrOpts);
  const { data: timeline } = useSWR("/soul/timeline/demo", swrOpts);

  const normalized = normalizeSoulState(state || {});
  const summarized = summarizeSoul(normalized, summary || {});
  const series = timelineSeries(timeline || []);
  const frictionCounts = Object.entries(
    (series || []).reduce<Record<string, number>>((acc, pt) => {
      if (Array.isArray(pt.friction)) {
        pt.friction.forEach((f: any) => {
          if (!f) return;
          const key = String(f);
          acc[key] = (acc[key] || 0) + 1;
        });
      }
      return acc;
    }, {})
  ).map(([name, value]) => ({ name, value }));

  // weight values by frequency across timeline (fallback to 3) and render as a wheel
  const valueWeights = (normalized.core_values || []).reduce<Record<string, number>>((acc, v) => {
    acc[v] = (acc[v] || 0) + 1;
    return acc;
  }, {});
  const valuesWheel = Object.entries(valueWeights).map(([name, score], idx) => ({
    name,
    score: Math.min(10, score * 3),
    fill: `hsl(${(idx * 55) % 360} 75% 60%)`,
  }));
  const balancePie = [
    { name: "Shadow", value: (summarized.shadow || []).length || 0.1, color: "#b91c1c" },
    { name: "Light", value: (summarized.light || []).length || 0.1, color: "#047857" },
  ];
  const shadowLightHeat = [
    { name: "Shadow", value: (summarized.shadow || []).length },
    { name: "Light", value: (summarized.light || []).length },
  ];
  const conflictHeat = buildHeat(series);
  const matrix = buildMatrix(series);
  const coherenceGauge = [{ name: "Coherence", value: summarized.coherence || 0 }];

  return (
    <main className="mx-auto max-w-5xl px-6 py-8 space-y-8">
      <header className="flex items-center justify-between">
        <div>
          <p className="text-sm uppercase tracking-wide text-stone-500">Soul Analytics</p>
          <h1 className="text-2xl font-semibold">Identity Snapshot</h1>
        </div>
        <Link href="/soul/timeline" className="text-blue-600 underline text-sm">
          Timeline →
        </Link>
      </header>

      <section className="grid gap-4 md:grid-cols-2">
        <Card title="Values">
          <TagList items={normalized.core_values} placeholder="No values detected yet." />
        </Card>
        <Card title="Identity Themes">
          <TagList items={normalized.identity_themes} placeholder="No themes detected yet." />
        </Card>
        <Card title="Shadow Patterns">
          <TagList items={summarized.shadow} placeholder="No shadow patterns yet." tone="shadow" />
        </Card>
        <Card title="Light Patterns">
          <TagList items={summarized.light} placeholder="No light patterns yet." tone="light" />
        </Card>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        <Card title="Coherence">
          <div className="h-32">
            <ResponsiveContainerAny width="100%" height="100%">
              <RadialBarChartAny innerRadius="60%" outerRadius="100%" data={coherenceGauge} startAngle={90} endAngle={-270}>
                <RadialBarAny dataKey="value" cornerRadius={8} fill="#22c55e" />
              </RadialBarChartAny>
            </ResponsiveContainerAny>
          </div>
          <div className="text-lg font-semibold text-stone-800">{Math.round((summarized.coherence || 0) * 100)}%</div>
          <p className="text-sm text-stone-500">Higher is more aligned.</p>
        </Card>
        <Card title="Dominant Friction">
          <p className="text-base">{summarized.friction || "None detected"}</p>
        </Card>
        <Card title="Confidence">
          <p className="text-base">{(normalized.confidence ?? 0) * 100}%</p>
        </Card>
      </section>

      <section className="grid gap-4 md:grid-cols-2">
        <Card title="Values Wheel">
          {valuesWheel.length ? (
            <div className="h-64">
              <ResponsiveContainerAny width="100%" height="100%">
                <RadialBarChartAny innerRadius="30%" outerRadius="90%" data={valuesWheel} startAngle={90} endAngle={-270}>
                  <PolarGridAny gridType="circle" />
                  <RadialBarAny
                    minAngle={10}
                    background
                    clockWise
                    dataKey="score"
                    cornerRadius={6}
                    onMouseEnter={(_: unknown, idx: number) => setSelectedValue(valuesWheel[idx]?.name || null)}
                  />
                  <LegendAny />
                </RadialBarChartAny>
              </ResponsiveContainerAny>
              <p className="mt-2 text-sm text-stone-600">
                {selectedValue ? `Focused on ${selectedValue}` : "Hover a slice to highlight a value"}
              </p>
            </div>
          ) : (
            <p className="text-sm text-stone-500">No values detected yet.</p>
          )}
        </Card>

        <Card title="Friction Map">
          {frictionCounts.length ? (
            <div className="h-64">
              <ResponsiveContainerAny width="100%" height="100%">
                <BarChartAny data={frictionCounts}>
                  <XAxisAny dataKey="name" hide />
                  <YAxisAny />
                  <TooltipAny />
                  <BarAny dataKey="value" fill="#0ea5e9" />
                </BarChartAny>
              </ResponsiveContainerAny>
            </div>
          ) : (
            <p className="text-sm text-stone-500">No friction patterns yet.</p>
          )}
        </Card>
      </section>

      <section className="grid gap-4 md:grid-cols-2">
        <Card title="Shadow/Light Balance">
          <div className="h-64">
            <ResponsiveContainerAny width="100%" height="100%">
              <PieChartAny>
                <PieAny data={balancePie} dataKey="value" nameKey="name" innerRadius="50%" outerRadius="80%">
                  {balancePie.map((entry, index) => (
                    <CellAny key={`cell-${index}`} fill={entry.color} />
                  ))}
                </PieAny>
                <LegendAny />
                <TooltipAny />
              </PieChartAny>
            </ResponsiveContainerAny>
          </div>
        </Card>
        <Card title="Conflict/Friction Heatmap">
          {conflictHeat.length ? (
            <HeatmapGrid data={conflictHeat} />
          ) : (
            <p className="text-sm text-stone-500">No conflict/friction patterns yet.</p>
          )}
        </Card>
        <Card title="Timeline Matrix">
          {matrix.length ? <MatrixGrid data={matrix} /> : <p className="text-sm text-stone-500">No episodic matrix yet.</p>}
        </Card>
      </section>

      <section>
        <Card title="Shadow vs Light">
          {series.length ? (
            <div className="h-64">
              <ResponsiveContainerAny width="100%" height="100%">
                <LineChartAny data={series}>
                  <XAxisAny dataKey="ts" hide />
                  <YAxisAny />
                  <TooltipAny />
                  <LegendAny />
                  <LineAny type="monotone" dataKey="shadow" stroke="#b91c1c" />
                  <LineAny type="monotone" dataKey="light" stroke="#047857" />
                </LineChartAny>
              </ResponsiveContainerAny>
            </div>
          ) : (
            <p className="text-sm text-stone-500">No timeline data yet.</p>
          )}
        </Card>
      </section>
    </main>
  );
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-stone-200 bg-white p-4 shadow-sm">
      <div className="mb-2 text-sm font-medium text-stone-600">{title}</div>
      {children}
    </div>
  );
}

function TagList({ items, placeholder, tone }: { items?: string[]; placeholder: string; tone?: "shadow" | "light" }) {
  if (!items?.length) return <p className="text-sm text-stone-400">{placeholder}</p>;
  const color =
    tone === "shadow" ? "bg-rose-100 text-rose-700" : tone === "light" ? "bg-emerald-100 text-emerald-700" : "bg-stone-100 text-stone-700";
  return (
    <div className="flex flex-wrap gap-2">
      {items.map((item) => (
        <span key={item} className={`rounded-full px-3 py-1 text-xs font-semibold ${color}`}>
          {item}
        </span>
      ))}
    </div>
  );
}

function buildHeat(series: any[]) {
  const buckets = series.reduce<Record<string, number>>((acc, pt) => {
    ["conflict", "friction"].forEach((k) => {
      const val = pt?.[k] || 0;
      if (!val) return;
      acc[k] = (acc[k] || 0) + val;
    });
    return acc;
  }, {});
  return Object.entries(buckets).map(([label, value]) => ({ label, value }));
}

function HeatmapGrid({ data }: { data: { label: string; value: number }[] }) {
  const max = Math.max(...data.map((d) => d.value), 1);
  return (
    <div className="grid grid-cols-2 gap-3">
      {data.map((cell) => {
        const intensity = Math.min(1, cell.value / max);
        const bg = `rgba(249, 115, 22, ${0.25 + intensity * 0.6})`;
        return (
          <div key={cell.label} className="rounded-lg p-3 text-sm font-medium" style={{ background: bg }}>
            <div className="text-stone-700">{cell.label}</div>
            <div className="text-stone-900 text-lg font-semibold">{cell.value}</div>
          </div>
        );
      })}
    </div>
  );
}

function buildMatrix(series: any[]) {
  // build matrix of metrics (conflict/friction) across timeline points
  const metrics = ["conflict", "friction"];
  return metrics.flatMap((m) =>
    series.map((pt, idx) => ({
      row: m,
      col: pt.ts || `t-${idx + 1}`,
      value: pt?.[m] || 0,
    }))
  );
}

function MatrixGrid({ data }: { data: { row: string; col: string; value: number }[] }) {
  const cols = Array.from(new Set(data.map((d) => d.col)));
  const rows = Array.from(new Set(data.map((d) => d.row)));
  const max = Math.max(...data.map((d) => d.value), 1);
  return (
    <div className="space-y-2">
      <div className="grid" style={{ gridTemplateColumns: `100px repeat(${cols.length}, 1fr)` }}>
        <div />
        {cols.map((c) => (
          <div key={c} className="text-xs text-stone-500 text-center">
            {c}
          </div>
        ))}
        {rows.map((r) => (
          <React.Fragment key={r}>
            <div className="text-xs font-medium text-stone-600">{r}</div>
            {cols.map((c) => {
              const cell = data.find((d) => d.row === r && d.col === c);
              const val = cell?.value || 0;
              const alpha = 0.15 + Math.min(0.75, val / max);
              return (
                <div
                  key={`${r}-${c}`}
                  className="h-10 rounded"
                  style={{ backgroundColor: `rgba(14, 165, 233, ${alpha})` }}
                  title={`${r} @ ${c}: ${val}`}
                />
              );
            })}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}
