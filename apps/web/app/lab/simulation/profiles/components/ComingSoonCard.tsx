"use client";

import type { PersonProfile } from "../profilesConfig";
import { govPalette } from "../../governance/theme";

export default function ComingSoonCard({ profile }: { profile: PersonProfile }) {
  return (
    <div
      style={{
        flex: 1,
        minWidth: 0,
        minHeight: 300,
        padding: 12,
        borderRadius: 12,
        border: `2px dashed ${govPalette.border}`,
        background: govPalette.card,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 12,
        opacity: 0.6,
      }}
    >
      <div
        style={{
          width: 10,
          height: 10,
          borderRadius: "50%",
          background: profile.color,
          opacity: 0.5,
        }}
      />
      <div
        style={{
          fontSize: 14,
          fontWeight: 600,
          color: govPalette.muted,
        }}
      >
        Coming Soon
      </div>
      <div
        style={{
          fontSize: 12,
          color: govPalette.veryDim,
          textAlign: "center",
          maxWidth: 180,
          lineHeight: 1.4,
        }}
      >
        A new profile will appear here
      </div>
    </div>
  );
}
