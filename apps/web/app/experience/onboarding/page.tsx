"use client";

import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import type React from "react";
import type { Route } from "next";

export const dynamic = "force-dynamic";

const palette = {
  bg: "#0a0a0a",
  fg: "#f4f4f5",
  muted: "#a1a1aa",
  dimText: "#52525b",
  border: "#27272a",
  cardBg: "#18191d",
};

const fontFamily =
  '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Inter, Helvetica, Arial, sans-serif';

interface AuthUser {
  person_id: string;
  full_name: string | null;
  email: string;
  needs_name: boolean;
}

export default function OnboardingPage() {
  return (
    <Suspense fallback={null}>
      <SlimNameOnboarding />
    </Suspense>
  );
}

function SlimNameOnboarding() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const routeName = searchParams?.get("name") || "";
  const routeUser = searchParams?.get("user") || "";

  const [name, setName] = useState(routeName);
  const [personId, setPersonId] = useState(routeUser);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadAuth = async () => {
      try {
        const response = await fetch("/api/auth/me", { cache: "no-store" });
        if (response.status === 401) {
          router.replace("/auth/login?redirect=/experience/converse" as Route);
          return;
        }
        if (!response.ok) {
          throw new Error(`Failed to load auth user (${response.status})`);
        }

        const data = (await response.json()) as AuthUser;
        const fullName = data.full_name?.trim() || "";
        const resolvedPersonId = data.person_id || routeUser;

        setPersonId(resolvedPersonId);
        setName((current) => current.trim() || fullName);

        if (!data.needs_name && fullName) {
          const nextPath = `/experience/converse?user=${encodeURIComponent(resolvedPersonId)}&name=${encodeURIComponent(fullName)}`;
          router.replace(nextPath as Route);
        }
      } catch (err) {
        console.error("Failed to load onboarding auth state:", err);
        setError("Could not load your profile. Please try again.");
      } finally {
        setIsLoading(false);
      }
    };

    void loadAuth();
  }, [routeUser, router]);

  const canContinue = useMemo(
    () => name.trim().length > 0 && personId.trim().length > 0 && !isSaving,
    [isSaving, name, personId],
  );

  const handleContinue = useCallback(async () => {
    const trimmedName = name.trim();
    const trimmedPersonId = personId.trim();
    if (!trimmedName || !trimmedPersonId) {
      return;
    }

    setIsSaving(true);
    setError(null);

    try {
      const response = await fetch("/api/auth/update-name", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: trimmedName }),
      });

      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(String(payload.error || "Failed to save name"));
      }

      const supabase = createClient();
      void supabase.auth.updateUser({
        data: {
          full_name: trimmedName,
          name: trimmedName,
        },
      }).catch(() => {});

      const nextPath = `/experience/converse?user=${encodeURIComponent(trimmedPersonId)}&name=${encodeURIComponent(trimmedName)}`;
      router.replace(nextPath as Route);
    } catch (err) {
      console.error("Name setup failed:", err);
      setError(err instanceof Error ? err.message : "Please try again.");
    } finally {
      setIsSaving(false);
    }
  }, [name, personId, router]);

  return (
    <main style={containerStyle}>
      <div style={contentStyle}>
        <div style={textContainerStyle}>
          <h1 style={titleStyle}>What should I call you?</h1>
          <p style={subtitleStyle}>Whatever feels natural to you.</p>
        </div>

        {isLoading ? (
          <div style={loadingStyle}>Loading...</div>
        ) : (
          <div style={formStyle}>
            <input
              type="text"
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="Your name (or a nickname)"
              autoFocus
              style={textInputStyle}
            />

            <button
              type="button"
              onClick={() => void handleContinue()}
              disabled={!canContinue}
              style={{
                ...primaryButtonStyle,
                ...(!canContinue ? primaryButtonDisabledStyle : {}),
              }}
            >
              {isSaving ? "Continuing..." : "Continue"}
            </button>

            {error ? <div style={errorStyle}>{error}</div> : null}
          </div>
        )}
      </div>
    </main>
  );
}

const containerStyle: React.CSSProperties = {
  minHeight: "100vh",
  background: palette.bg,
  color: palette.fg,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  padding: "40px",
  fontFamily,
};

const contentStyle: React.CSSProperties = {
  width: "100%",
  maxWidth: "420px",
  display: "flex",
  flexDirection: "column",
  alignItems: "center",
};

const textContainerStyle: React.CSSProperties = {
  marginBottom: "40px",
  textAlign: "center",
};

const titleStyle: React.CSSProperties = {
  fontSize: "28px",
  lineHeight: 1.2,
  fontWeight: 400,
  color: "#ffffff",
  margin: 0,
};

const subtitleStyle: React.CSSProperties = {
  fontSize: "16px",
  lineHeight: "24px",
  fontWeight: 400,
  color: palette.muted,
  margin: "12px 0 0",
};

const formStyle: React.CSSProperties = {
  width: "100%",
  display: "flex",
  flexDirection: "column",
  gap: "16px",
};

const textInputStyle: React.CSSProperties = {
  width: "100%",
  minHeight: "56px",
  borderRadius: "14px",
  border: `1px solid ${palette.border}`,
  backgroundColor: palette.cardBg,
  color: palette.fg,
  padding: "16px 18px",
  fontFamily,
  fontSize: "16px",
  outline: "none",
};

const primaryButtonStyle: React.CSSProperties = {
  width: "100%",
  minHeight: "56px",
  borderRadius: "14px",
  border: `1px solid ${palette.border}`,
  backgroundColor: palette.cardBg,
  color: palette.fg,
  fontFamily,
  fontSize: "16px",
  fontWeight: 500,
  cursor: "pointer",
};

const primaryButtonDisabledStyle: React.CSSProperties = {
  opacity: 0.5,
  cursor: "not-allowed",
};

const loadingStyle: React.CSSProperties = {
  color: palette.muted,
  fontSize: "14px",
};

const errorStyle: React.CSSProperties = {
  padding: "12px 16px",
  background: "#ef444420",
  border: "1px solid #ef4444",
  borderRadius: "8px",
  color: "#fca5a5",
  fontSize: "14px",
  textAlign: "center",
};
