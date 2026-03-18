"use client";

import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import type { Route } from "next";

export const dynamic = "force-dynamic";

interface AuthUser {
  person_id: string;
  full_name: string | null;
  email: string;
}

const palette = {
  bg: "#060a13",
  fg: "#f5f7fb",
  muted: "#a7b0c0",
  border: "rgba(231, 239, 255, 0.16)",
  glass: "rgba(20, 28, 40, 0.72)",
  accent: "#d08b4e",
  danger: "#f0b8c0",
};

function formatMaskedId(personId: string): string {
  const raw = String(personId || "").trim();
  if (!raw) return "Not linked yet";
  if (raw.length <= 12) return raw;
  return `${raw.slice(0, 8)}...${raw.slice(-4)}`;
}

export default function SettingsPage() {
  return (
    <Suspense fallback={<PageFallback />}>
      <SettingsPageContent />
    </Suspense>
  );
}

function SettingsPageContent() {
  const router = useRouter();
  const search = useSearchParams();

  const [authUser, setAuthUser] = useState<AuthUser | null>(null);
  const [authLoading, setAuthLoading] = useState(true);

  const [pushEnabled, setPushEnabled] = useState(true);
  const [compactMode, setCompactMode] = useState(false);
  const [analyticsEnabled, setAnalyticsEnabled] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const res = await fetch("/api/auth/me", { cache: "no-store" });
        if (res.ok) {
          const data = await res.json();
          setAuthUser({
            person_id: data.person_id,
            full_name: data.full_name,
            email: data.email,
          });
        }
      } finally {
        setAuthLoading(false);
      }
    };
    void load();
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const push = window.localStorage.getItem("sakhi_settings_push");
    const compact = window.localStorage.getItem("sakhi_settings_compact");
    const analytics = window.localStorage.getItem("sakhi_settings_analytics");
    if (push != null) setPushEnabled(push === "1");
    if (compact != null) setCompactMode(compact === "1");
    if (analytics != null) setAnalyticsEnabled(analytics === "1");
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    window.localStorage.setItem("sakhi_settings_push", pushEnabled ? "1" : "0");
  }, [pushEnabled]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    window.localStorage.setItem("sakhi_settings_compact", compactMode ? "1" : "0");
  }, [compactMode]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    window.localStorage.setItem("sakhi_settings_analytics", analyticsEnabled ? "1" : "0");
  }, [analyticsEnabled]);

  const personId = useMemo(() => {
    const fromAuth = String(authUser?.person_id || "").trim();
    if (fromAuth) return fromAuth;
    return String(search?.get("user") || "").trim();
  }, [authUser?.person_id, search]);

  const backPath = `/experience/converse${personId ? `?user=${encodeURIComponent(personId)}` : ""}`;
  const maskedPersonId = formatMaskedId(personId);

  const handleSignOut = useCallback(async () => {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.replace("/experience" as Route);
  }, [router]);

  if (authLoading) {
    return (
      <div style={{ minHeight: "100vh", display: "grid", placeItems: "center", background: palette.bg, color: palette.muted }}>
        Loading...
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <header style={styles.header}>
        <button style={styles.iconButton} onClick={() => router.push(backPath as Route)}>←</button>
        <div>
          <div style={styles.kicker}>Account</div>
          <h1 style={styles.title}>Settings</h1>
        </div>
      </header>

      <main style={styles.content}>
        <section style={styles.card}>
          <h2 style={styles.cardTitle}>App</h2>
          <p style={styles.cardHint}>Local device settings for your Sakhi experience.</p>

          <label style={styles.settingRow}>
            <div>
              <div style={styles.settingTitle}>Push notifications</div>
              <div style={styles.settingHint}>Daily reminders and response follow-ups</div>
            </div>
            <input type="checkbox" checked={pushEnabled} onChange={(e) => setPushEnabled(e.target.checked)} />
          </label>

          <label style={styles.settingRow}>
            <div>
              <div style={styles.settingTitle}>Compact chat bubbles</div>
              <div style={styles.settingHint}>Show tighter spacing in conversation view</div>
            </div>
            <input type="checkbox" checked={compactMode} onChange={(e) => setCompactMode(e.target.checked)} />
          </label>
        </section>

        <section style={styles.card}>
          <h2 style={styles.cardTitle}>Privacy & Data</h2>
          <p style={styles.cardHint}>Support access stays off by default and only includes what you explicitly allow.</p>

          <label style={styles.settingRow}>
            <div>
              <div style={styles.settingTitle}>Share anonymous usage data</div>
              <div style={styles.settingHint}>Helps improve Sakhi — no message content</div>
            </div>
            <input type="checkbox" checked={analyticsEnabled} onChange={(e) => setAnalyticsEnabled(e.target.checked)} />
          </label>
        </section>

        <section style={styles.card}>
          <h2 style={styles.cardTitle}>Account</h2>
          <div style={styles.identityRow}>Email: {authUser?.email || "Not available"}</div>
          <div style={styles.identityRow}>Profile ID: {maskedPersonId}</div>

          <button style={styles.signOutButton} onClick={() => void handleSignOut()}>
            Sign out
          </button>
        </section>
      </main>
    </div>
  );
}

function PageFallback() {
  return (
    <div style={{ minHeight: "100vh", display: "grid", placeItems: "center", background: palette.bg, color: palette.muted }}>
      Loading...
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    minHeight: "100vh",
    background: palette.bg,
    color: palette.fg,
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Inter, sans-serif',
  },
  header: {
    borderBottom: `1px solid ${palette.border}`,
    padding: "12px 16px",
    display: "flex",
    alignItems: "center",
    gap: 12,
  },
  iconButton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    border: `1px solid ${palette.border}`,
    background: "rgba(255,255,255,0.06)",
    color: palette.fg,
    cursor: "pointer",
  },
  kicker: {
    color: palette.muted,
    fontSize: 11,
    letterSpacing: "0.11em",
    textTransform: "uppercase",
  },
  title: {
    margin: "2px 0 0",
    fontSize: 30,
  },
  content: {
    padding: 16,
    display: "grid",
    gap: 14,
  },
  card: {
    borderRadius: 20,
    border: `1px solid ${palette.border}`,
    background: palette.glass,
    padding: 14,
    display: "grid",
    gap: 10,
  },
  cardTitle: {
    margin: 0,
    fontSize: 24,
  },
  cardHint: {
    margin: 0,
    color: palette.muted,
    fontSize: 14,
  },
  settingRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    gap: 12,
    borderRadius: 12,
    border: `1px solid rgba(176, 196, 228, 0.2)`,
    background: "rgba(22, 34, 52, 0.74)",
    padding: "10px 12px",
  },
  settingTitle: {
    fontSize: 15,
    color: palette.fg,
  },
  settingHint: {
    fontSize: 13,
    color: palette.muted,
    marginTop: 2,
  },
  identityRow: {
    fontSize: 14,
    color: palette.muted,
  },
  signOutButton: {
    marginTop: 6,
    borderRadius: 12,
    border: `1px solid rgba(240, 184, 192, 0.5)`,
    background: "rgba(64, 25, 33, 0.4)",
    color: palette.danger,
    padding: "11px 14px",
    fontSize: 15,
    cursor: "pointer",
  },
};
