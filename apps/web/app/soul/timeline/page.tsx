"use client";

import useSWR from "swr";
import { timelineSeries } from "@ui/soulViewModel";
import Link from "next/link";
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, Legend } from "recharts";

const fetcher = (url: string) => fetch(url).then((r) => r.json());
const swrOpts = { fetcher, dedupingInterval: 60_000, revalidateOnFocus: false };

export default function SoulTimelinePage() {
  const { data } = useSWR("/soul/timeline/demo", swrOpts);
  const series = timelineSeries(data || []);
  return (
    <main className="mx-auto max-w-5xl px-6 py-8 space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <p className="text-sm uppercase tracking-wide text-stone-500">Soul Analytics</p>
          <h1 className="text-2xl font-semibold">Timeline</h1>
        </div>
        <Link href="/soul" className="text-blue-600 underline text-sm">
          ← Back
        </Link>
      </header>
      <section className="space-y-3">
        {series.length ? (
          <div className="h-72 rounded-lg border border-stone-200 bg-white p-3 shadow-sm">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={series}>
                <XAxis dataKey="ts" hide />
                <YAxis />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="shadow" stroke="#b91c1c" />
                <Line type="monotone" dataKey="light" stroke="#047857" />
                <Line type="monotone" dataKey="conflict" stroke="#6b21a8" />
                <Line type="monotone" dataKey="friction" stroke="#0ea5e9" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <p className="text-sm text-stone-400">No episodic data yet.</p>
        )}
      </section>
    </main>
  );
}
