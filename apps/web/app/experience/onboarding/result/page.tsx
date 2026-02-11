"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import type { Route } from "next";

export const dynamic = "force-dynamic";

/**
 * Legacy result page — OS results are now shown inline during onboarding.
 * Redirects to onboarding if someone hits this URL directly.
 */
export default function OnboardingResultPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/experience/onboarding" as Route);
  }, [router]);

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#0a0a0a",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <p style={{ color: "#a1a1aa", fontSize: "16px" }}>Redirecting...</p>
    </div>
  );
}
