"use client";

import { Suspense } from "react";
import MePageContent from "./client";

export default function MePage() {
  return (
    <Suspense
      fallback={
        <div
          style={{
            minHeight: "100vh",
            background: "#0e0f12",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "#a1a1aa",
          }}
        >
          Loading...
        </div>
      }
    >
      <MePageContent />
    </Suspense>
  );
}
