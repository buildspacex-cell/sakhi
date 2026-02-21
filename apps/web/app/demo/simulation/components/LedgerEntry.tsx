"use client";

import type { LedgerEvent } from "../types";

interface LedgerEntryProps {
  event: LedgerEvent;
  profileColor?: string;
}

const EVENT_TYPE_STYLES: Record<string, { color: string; icon: string }> = {
  proposed: { color: "#71717a", icon: "\u25b6" },
  committed: { color: "#22c55e", icon: "\u2713" },
  validated: { color: "#f59e0b", icon: "\u2713" },
  rejected: { color: "#ef4444", icon: "\u2717" },
  reconciled: { color: "#a855f7", icon: "\u21c4" },
};

export default function LedgerEntry({ event, profileColor }: LedgerEntryProps) {
  const style = EVENT_TYPE_STYLES[event.event_type] || EVENT_TYPE_STYLES.proposed;
  const time = formatTime(event.timestamp);

  return (
    <div
      style={{
        display: "flex",
        alignItems: "flex-start",
        gap: 8,
        padding: "6px 0",
        fontSize: 11,
      }}
    >
      {/* Timeline dot */}
      <div
        style={{
          width: 6,
          height: 6,
          borderRadius: "50%",
          background: profileColor || style.color,
          marginTop: 4,
          flexShrink: 0,
        }}
      />

      {/* Content */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span style={{ fontFamily: "monospace", color: "#52525b", fontSize: 10 }}>
            {time}
          </span>
          <span style={{ fontFamily: "monospace", color: style.color, fontWeight: 600 }}>
            {style.icon} {event.event_type}
          </span>
        </div>
        <div
          style={{
            color: "#a1a1aa",
            marginTop: 2,
            fontFamily: "monospace",
            fontSize: 10,
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          {event.action}
          {event.reason && (
            <span style={{ color: "#52525b" }}> — {event.reason}</span>
          )}
        </div>
      </div>
    </div>
  );
}

function formatTime(ts: string): string {
  try {
    const d = new Date(ts);
    return d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", hour12: true });
  } catch {
    return ts;
  }
}
