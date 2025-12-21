"use client";

import useSWR from "swr";
import Link from "next/link";

const fetcher = (url: string) => fetch(url).then((r) => r.json());

export default function SoulNarrativePage() {
  const { data } = useSWR("/soul/narrative/demo", fetcher);

  return (
    <main className="mx-auto max-w-5xl px-6 py-8 space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <p className="text-sm uppercase tracking-wide text-stone-500">Soul Narrative</p>
          <h1 className="text-2xl font-semibold">Story & Arc</h1>
        </div>
        <Link href="/soul" className="text-blue-600 underline text-sm">
          ← Back
        </Link>
      </header>

      <Card title="Identity Arc" text={data?.identity_arc} />
      <Card title="Archetype" text={data?.soul_archetype} />
      <Card title="Life Phase" text={data?.life_phase} />
      <Card title="Value Conflicts">
        <List items={data?.value_conflicts} />
      </Card>
      <Card title="Healing Direction">
        <List items={data?.healing_direction} />
      </Card>
      <Card title="Narrative Tension" text={data?.narrative_tension} />
    </main>
  );
}

function Card({ title, text, children }: { title: string; text?: string | null; children?: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-stone-200 bg-white p-4 shadow-sm">
      <div className="mb-2 text-sm font-medium text-stone-600">{title}</div>
      {children ? children : <p className="text-sm text-stone-700">{text || "No data yet."}</p>}
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
