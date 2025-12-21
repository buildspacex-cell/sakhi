"use client";

import { useEffect, useMemo, useState } from "react";

const LAYER_COLORS: Record<string, string> = {
  journal: "text-rose-600",
  reflection: "text-blue-600",
  rhythm: "text-amber-600",
  analytics: "text-green-600",
  breath: "text-violet-600",
};

export function DebugPanel({ personId }: { personId: string }) {
  const [events, setEvents] = useState<any[]>([]);
  const apiBase = useMemo(() => {
    const base =
      process.env.NEXT_PUBLIC_API_URL ??
      process.env.NEXT_PUBLIC_API_BASE_URL ??
      "";
    return base.endsWith("/") ? base.slice(0, -1) : base;
  }, []);

  useEffect(() => {
    if (!personId) return;
    const streamUrl = apiBase
      ? `${apiBase}/events/stream/${personId}`
      : `/api/events/stream/${personId}`;
    const source = new EventSource(streamUrl);
    source.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        setEvents((prev) => [payload, ...prev].slice(0, 100));
      } catch {
        // ignore malformed payloads
      }
    };
    return () => source.close();
    return () => source.close();
  }, [personId, apiBase]);

  return (
    <div className="bg-gray-50 border-t mt-3 p-2 rounded max-h-80 overflow-y-auto text-xs font-mono">
      {events.length === 0 && (
        <div className="text-gray-400">Listening for events…</div>
      )}
      {events.map((event, idx) => (
        <div key={`${event.id}-${idx}`} className="mb-2">
          <div>
            <span className={`${LAYER_COLORS[event.layer] ?? "text-gray-700"} font-semibold`}>
              {event.layer || "system"}
            </span>{" "}
            <span className="text-gray-600">{event.event}</span>
          </div>
          {event.payload && (
            <pre className="bg-white rounded p-1 text-[10px] text-gray-500 overflow-x-auto">
              {JSON.stringify(event.payload, null, 2)}
            </pre>
          )}
        </div>
      ))}
    </div>
  );
}

export default DebugPanel;
