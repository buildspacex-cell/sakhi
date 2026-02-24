"use client";

import type { LedgerEvent } from "@/app/demo/simulation/types";
import { GOV_PROFILES, govPalette } from "../theme";
import LedgerEntry from "./LedgerEntry";

interface GovernanceLedgerProps {
  events: LedgerEvent[];
}

export default function GovernanceLedger({ events }: GovernanceLedgerProps) {
  if (events.length === 0) {
    return (
      <div style={{ padding: 24, textAlign: "center", color: govPalette.veryDim, fontSize: 13 }}>
        No governance events yet.
      </div>
    );
  }

  const profileColorMap: Record<string, string> = {};
  for (const p of GOV_PROFILES) {
    profileColorMap[p.id] = p.color;
  }

  return (
    <div>
      <h3 style={{ fontSize: 16, fontWeight: 700, margin: "0 0 12px", color: govPalette.text }}>
        Governance Ledger
      </h3>
      <p style={{ fontSize: 11, color: govPalette.veryDim, margin: "0 0 16px" }}>
        Every governance decision, logged immutably. Append-only audit trail.
      </p>
      <div
        style={{
          maxHeight: 400,
          overflowY: "auto",
          padding: "0 4px",
          borderLeft: `2px solid ${govPalette.border}`,
          marginLeft: 8,
        }}
      >
        {events.map((event) => {
          const profile = (event.data as Record<string, unknown>)?.profile as string | undefined;
          const color = profile ? profileColorMap[profile] : undefined;
          return <LedgerEntry key={event.id} event={event} profileColor={color} />;
        })}
      </div>
    </div>
  );
}
