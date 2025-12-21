'use client';

import { useState } from 'react';

export default function LoopDebugPage() {
  const [text, setText] = useState('');
  const [resp, setResp] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  async function send() {
    setLoading(true);
    try {
      const r = await fetch('/api/turn-v2', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      });
      const data = await r.json();
      setResp(data);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="p-6 max-w-2xl mx-auto space-y-4">
      <h1 className="text-xl font-semibold">Conversation Loop Debug</h1>

      <textarea
        className="w-full rounded border p-3"
        rows={4}
        placeholder="Type a message… e.g., I want to join a gym"
        value={text}
        onChange={(e) => setText(e.target.value)}
      />

      <button
        onClick={send}
        disabled={loading || !text.trim()}
        className="px-4 py-2 rounded bg-blue-600 text-white disabled:opacity-50"
      >
        {loading ? 'Sending…' : 'Send'}
      </button>

      {resp && (
        <div className="space-y-3">
          <section className="p-3 rounded border">
            <h2 className="font-medium">Assistant Reply</h2>
            <p className="mt-2 whitespace-pre-wrap">{resp.reply ?? '—'}</p>
          </section>

          <section className="p-3 rounded border">
            <h2 className="font-medium">Topic Session</h2>
            <p className="mt-2 text-sm">{resp.sessionSlug ?? resp.session ?? 'journal'}</p>
            {resp.switch?.switched ? (
              <p className="mt-1 text-xs text-orange-600">Switched to {resp.switch?.to}</p>
            ) : resp.topicShift?.hint ? (
              <p className="mt-1 text-xs text-slate-500">Possible new topic detected.</p>
            ) : null}
            {resp.switch?.reason && (
              <p className="mt-1 text-xs text-slate-500">Reason: {resp.switch?.reason}</p>
            )}
          </section>

          <section className="p-3 rounded border">
            <h2 className="font-medium">Confirmations</h2>
            <ul className="list-disc ml-5">
              {(resp.confirmations ?? []).map((c: string, i: number) => (
                <li key={i}>{c}</li>
              ))}
            </ul>
          </section>

          <section className="p-3 rounded border">
            <h2 className="font-medium">Suggestions (Frontier Top 3)</h2>
            <ul className="list-disc ml-5">
              {(resp.frontierTop3 ?? resp.suggestions ?? []).map((s: string, i: number) => (
                <li key={i}>{s}</li>
              ))}
            </ul>
          </section>

          <section className="p-3 rounded border">
            <h2 className="font-medium">Last Objective</h2>
            <code className="block mt-2 text-sm">{resp.lastObjective}</code>
          </section>

          <section className="p-3 rounded border grid grid-cols-1 sm:grid-cols-3 gap-2 text-sm">
            <div>
              <span className="font-medium">Tone:</span> {resp.tone ?? '—'}
            </div>
            <div>
              <span className="font-medium">Mood:</span> {resp.mood ?? '—'}
            </div>
            <div>
              <span className="font-medium">Archetype:</span> {resp.archetype ?? '—'}
            </div>
          </section>

          <section className="p-3 rounded border">
            <h2 className="font-medium">Raw JSON</h2>
            <pre className="mt-2 text-xs overflow-auto">{JSON.stringify(resp, null, 2)}</pre>
          </section>
        </div>
      )}
    </div>
  );
}
