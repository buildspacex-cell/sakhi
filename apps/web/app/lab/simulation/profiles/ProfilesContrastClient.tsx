"use client";

import { govPalette } from "../governance/theme";
import ProfilesContrast from "./ProfilesContrast";

export default function ProfilesContrastClient() {
  return (
    <div
      style={{
        minHeight: "100vh",
        background: govPalette.bg,
        padding: "40px 24px",
      }}
    >
      <div style={{ maxWidth: 1100, margin: "0 auto" }}>
        <ProfilesContrast />
      </div>
    </div>
  );
}
