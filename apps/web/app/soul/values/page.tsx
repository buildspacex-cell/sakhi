"use client";

import useSWR from "swr";
import Link from "next/link";
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
} from "recharts";
import React from "react";
import { normalizeSoulState } from "@ui/soulViewModel";

const fetcher = (url: string) => fetch(url).then((r) => r.json());
const swrOpts = { fetcher, dedupingInterval: 60_000, revalidateOnFocus: false };

export default function SoulValuesPage() {
  const { data: state } = useSWR("/soul/state/demo", swrOpts);
  const normalized = normalizeSoulState(state || {});
  const valuesData = (normalized.core_values || []).map((v, idx) => ({
    name: v,
    value: 1,
    fill: `hsl(${(idx * 60) % 360} 80% 60%)`,
  }));
  const aversionVsLonging = [
    { name: "Longing", value: (normalized.longing || []).length },
    { name: "Aversions", value: (normalized.aversions || []).length },
    { name: "Commitments", value: (normalized.commitments || []).length },
  ];
  const heat = buildValueHeatmap(normalized);

  return (
    <main className="mx-auto max-w-5xl px-6 py-8 space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <p className="text-sm uppercase tracking-wide text-stone-500">Soul Analytics</p>
          <h1 className="text-2xl font-semibold">Values & Commitments</h1>
        </div>
        <Link href="/soul" className="text-blue-600 underline text-sm">
          ← Back
        </Link>
      </header>
      <div className="grid gap-4 md:grid-cols-2">
        <Card title="Values Wheel">
          {valuesData.length ? (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={valuesData} dataKey="value" nameKey="name" innerRadius="50%" outerRadius="80%" label>
                    {valuesData.map((slice, idx) => (
                      <Cell key={idx} fill={slice.fill} />
                    ))}
                  </Pie>
                  <Legend />
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="text-sm text-stone-400">No values yet.</p>
          )}
        </Card>
        <Card title="Longing vs Aversions">
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={aversionVsLonging}>
                <XAxis dataKey="name" />
                <YAxis allowDecimals={false} />
                <Tooltip />
                <Bar dataKey="value" fill="#0ea5e9" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      <Card title="You care about">
        <TagList items={normalized.core_values} />
      </Card>
      <Card title="You long for">
        <TagList items={normalized.longing} />
      </Card>
      <Card title="You avoid">
        <TagList items={normalized.aversions} />
      </Card>
      <Card title="Identity Themes">
        <TagList items={normalized.identity_themes} />
      </Card>
      <Card title="Commitments">
        <TagList items={normalized.commitments} />
      </Card>
      <Card title="Values Heatmap">
        {heat.length ? <HeatmapGrid data={heat} columns={normalized.core_values || []} /> : <p className="text-sm text-stone-400">No values yet.</p>}
      </Card>
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

function TagList({ items }: { items?: string[] }) {
  if (!items?.length) return <p className="text-sm text-stone-400">No data yet.</p>;
  return (
    <div className="flex flex-wrap gap-2">
      {items.map((item) => (
        <span key={item} className="rounded-full bg-stone-100 px-3 py-1 text-xs font-semibold text-stone-700">
          {item}
        </span>
      ))}
    </div>
  );
}

function buildValueHeatmap(state: any) {
  const values = state.core_values || [];
  const longing = new Set(state.longing || []);
  const aversions = new Set(state.aversions || []);
  const commitments = new Set(state.commitments || []);
  const rows = ["Longing", "Aversions", "Commitments"];
  return rows.flatMap((row) =>
    values.map((val: string) => {
      const key =
        row === "Longing" ? longing.has(val) : row === "Aversions" ? aversions.has(val) : commitments.has(val);
      return { row, col: val, value: key ? 1 : 0 };
    })
  );
}

function HeatmapGrid({ data, columns }: { data: { row: string; col: string; value: number }[]; columns: string[] }) {
  const rows = Array.from(new Set(data.map((d) => d.row)));
  const max = Math.max(...data.map((d) => d.value), 1);
  return (
    <div className="space-y-2">
      <div className="grid text-xs text-stone-600" style={{ gridTemplateColumns: `120px repeat(${columns.length}, 1fr)` }}>
        <div />
        {columns.map((c) => (
          <div key={c} className="text-center font-semibold">
            {c}
          </div>
        ))}
        {rows.map((r) => (
          <React.Fragment key={r}>
            <div className="font-medium">{r}</div>
            {columns.map((c) => {
              const cell = data.find((d) => d.row === r && d.col === c);
              const val = cell?.value || 0;
              const alpha = 0.15 + (val / max) * 0.65;
              return <div key={`${r}-${c}`} className="h-8 rounded" style={{ backgroundColor: `rgba(37, 99, 235, ${alpha})` }} />;
            })}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}
