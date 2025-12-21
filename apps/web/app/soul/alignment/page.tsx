"use client";

import useSWR from "swr";
import Link from "next/link";

const fetcher = (url: string) => fetch(url).then((r) => r.json());

export default function SoulAlignmentPage() {
  const { data } = useSWR("/soul/alignment/demo", fetcher);

  return (
    <main className="mx-auto max-w-5xl px-6 py-8 space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <p className="text-sm uppercase tracking-wide text-stone-500">Soul Alignment</p>
          <h1 className="text-2xl font-semibold">Alignment & Conflicts</h1>
        </div>
        <Link href="/soul" className="text-blue-600 underline text-sm">
          ← Back
        </Link>
      </header>

      <section className="grid gap-4 md:grid-cols-2">
        <Card title="Alignment Score">
          <p className="text-3xl font-semibold">{Math.round((data?.alignment_score || 0) * 100)}%</p>
        </Card>
        <Card title="Suggestions">
          <List items={data?.action_suggestions} />
        </Card>
      </section>

      <Card title="Conflict Zones">
        <List items={data?.conflict_zones} />
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

function List({ items }: { items?: string[] }) {
  if (!items?.length) return <p className="text-sm text-stone-400">No items.</p>;
  return (
    <ul className="list-disc pl-5 text-sm text-stone-700 space-y-1">
      {items.map((i) => (
        <li key={i}>{i}</li>
      ))}
    </ul>
  );
}
