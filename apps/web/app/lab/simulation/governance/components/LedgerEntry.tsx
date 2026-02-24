"use client";

import type { LedgerEvent } from "@/app/demo/simulation/types";
import { govPalette } from "../theme";

interface LedgerEntryProps {
  event: LedgerEvent;
  profileColor?: string;
}

const EVENT_TYPE_STYLES: Record<string, { color: string; icon: string }> = {
  proposed: { color: govPalette.dim, icon: "\u25b6" },
  committed: { color: govPalette.allow, icon: "\u2713" },
  validated: { color: govPalette.warn, icon: "\u2713" },
  rejected: { color: govPalette.block, icon: "\u2717" },
  reconciled: { color: govPalette.reconcile, icon: "\u21c4" },
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
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span style={{ fontFamily: "monospace", color: govPalette.veryDim, fontSize: 10 }}>
            {time}
          </span>
          <span style={{ fontFamily: "monospace", color: style.color, fontWeight: 600 }}>
            {style.icon} {event.event_type}
          </span>
        </div>
        <div
          style={{
            color: govPalette.muted,
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
            <span style={{ color: govPalette.veryDim }}> — {event.reason}</span>
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
