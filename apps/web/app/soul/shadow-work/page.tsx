"use client";

import useSWR from "swr";
import Link from "next/link";
import React from "react";
import { summarizeSoul, normalizeSoulState } from "@ui/soulViewModel";
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip } from "recharts";

const fetcher = (url: string) => fetch(url).then((r) => r.json());

export default function SoulShadowWorkPage() {
  const { data: state } = useSWR("/soul/state/demo", fetcher);
  const { data: summary } = useSWR("/soul/summary/demo", fetcher);

  const normalized = normalizeSoulState(state || {});
  const summarized = summarizeSoul(normalized, summary || {});
  const shadowLightBars = [
    { name: "Shadow", value: summarized.shadow?.length || 0 },
    { name: "Light", value: summarized.light?.length || 0 },
  ];

  return (
    <main className="mx-auto max-w-5xl px-6 py-8 space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <p className="text-sm uppercase tracking-wide text-stone-500">Soul Analytics</p>
          <h1 className="text-2xl font-semibold">Shadow & Light</h1>
        </div>
        <Link href="/soul" className="text-blue-600 underline text-sm">
          ← Back
        </Link>
      </header>

      <section className="grid gap-4 md:grid-cols-2">
        <Card title="Recurring Shadow Themes">
          <TagList items={summarized.shadow} tone="shadow" />
        </Card>
        <Card title="Counterbalancing Light Themes">
          <TagList items={summarized.light} tone="light" />
        </Card>
      </section>

      <section className="rounded-2xl border border-stone-200 bg-white p-4 shadow-sm">
        <div className="mb-2 text-sm font-medium text-stone-600">Inner Conflicts & Friction</div>
        <p className="text-sm text-stone-700">{summarized.friction || "No dominant friction detected."}</p>
      </section>

      <section className="rounded-2xl border border-stone-200 bg-white p-4 shadow-sm">
        <div className="mb-2 text-sm font-medium text-stone-600">Shadow vs Light Intensity</div>
        <div className="h-56">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={shadowLightBars}>
              <XAxis dataKey="name" />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="value" fill="#9333ea" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section className="rounded-2xl border border-stone-200 bg-white p-4 shadow-sm space-y-3">
        <div className="text-sm font-medium text-stone-600">Reflective Prompts</div>
        <ul className="list-disc pl-5 text-sm text-stone-700 space-y-2">
          <li>Where does this shadow show up in your week?</li>
          <li>What light pattern already balances it?</li>
          <li>Is your current friction linked to a value you care about?</li>
        </ul>
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

function TagList({ items, tone }: { items?: string[]; tone?: "shadow" | "light" }) {
  if (!items?.length) return <p className="text-sm text-stone-400">No data yet.</p>;
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
