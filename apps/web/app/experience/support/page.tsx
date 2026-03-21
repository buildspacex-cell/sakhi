"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import type { Route } from "next";
import { editorialFontFamily, midnightEditorial as palette } from "@/lib/theme/midnightEditorial";

export const dynamic = "force-dynamic";

interface AuthUser {
  person_id: string;
  full_name: string | null;
  email: string;
}

function formatExpiry(isoString: string): string {
  if (!isoString) return "";
  const parsed = Date.parse(isoString);
  if (!Number.isFinite(parsed)) return isoString;
  const diffMs = parsed - Date.now();
  if (diffMs <= 0) return "Expired";
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  if (diffHours < 1) return "Expires in less than an hour";
  if (diffHours < 24) return `Expires in ${diffHours}h`;
  const diffDays = Math.round(diffMs / (1000 * 60 * 60 * 24));
  return `Expires in ${diffDays} day${diffDays === 1 ? "" : "s"}`;
}

export default function SupportPage() {
  return (
    <Suspense fallback={<PageFallback />}>
      <SupportPageContent />
    </Suspense>
  );
}

function SupportPageContent() {
  const router = useRouter();
  const search = useSearchParams();

  const [authUser, setAuthUser] = useState<AuthUser | null>(null);
  const [authLoading, setAuthLoading] = useState(true);

  const [issueText, setIssueText] = useState("");
  const [shareDiagnostics, setShareDiagnostics] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [supportCode, setSupportCode] = useState("");
  const [supportExpiresAt, setSupportExpiresAt] = useState("");
  const [isRevoking, setIsRevoking] = useState(false);
  const [revoked, setRevoked] = useState(false);
  const [error, setError] = useState("");

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

  const personId = useMemo(() => {
    const fromAuth = String(authUser?.person_id || "").trim();
    if (fromAuth) return fromAuth;
    return String(search?.get("user") || "").trim();
  }, [authUser?.person_id, search]);

  const backPath = `/experience/converse${personId ? `?user=${encodeURIComponent(personId)}` : ""}`;

  const appVersion = process.env.NEXT_PUBLIC_VERCEL_GIT_COMMIT_SHA?.slice(0, 7) || "web";

  const handleSubmit = async () => {
    if (!issueText.trim()) {
      setError("Add a brief description before sending.");
      return;
    }
    if (!personId) {
      setError("Sign in again to send a report.");
      return;
    }

    setError("");
    setIsSubmitting(true);
    try {
      const response = await fetch(`/api/support/report`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          person_id: personId,
          issue_summary: issueText.trim(),
          diagnostics: {
            enabled: shareDiagnostics,
            include_conversation_metadata: false,
          },
          client_context: {
            appVersion,
            platform: "web",
            source: "support_simple_web",
          },
        }),
      });

      const payload = await response.json().catch(() => ({} as Record<string, unknown>));
      if (!response.ok) {
        const detail = typeof payload?.detail === "string" ? payload.detail : "Could not send report.";
        throw new Error(detail);
      }

      const code = typeof payload?.support_code === "string" ? payload.support_code : "";
      const expires = typeof payload?.expires_at === "string" ? payload.expires_at : "";
      setSupportCode(code);
      setSupportExpiresAt(expires);
      setSubmitted(true);
      setRevoked(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRevoke = async () => {
    if (!supportCode || !personId) return;
    setIsRevoking(true);
    setError("");
    try {
      const response = await fetch(`/api/support/report/revoke`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ person_id: personId, support_code: supportCode }),
      });
      if (!response.ok) {
        throw new Error("Could not revoke support code");
      }
      setRevoked(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Try again.");
    } finally {
      setIsRevoking(false);
    }
  };

  if (authLoading) {
    return (
      <div style={{ minHeight: "100vh", display: "grid", placeItems: "center", background: styles.container.background, color: palette.muted, fontFamily: editorialFontFamily }}>
        Loading...
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <header style={styles.header}>
        <button style={styles.iconButton} onClick={() => router.push(backPath as Route)}>←</button>
        <div>
          <div style={styles.kicker}>Beta</div>
          <h1 style={styles.title}>Something wrong?</h1>
        </div>
      </header>

      <main style={styles.content}>
        {!submitted ? (
          <section style={styles.card}>
            <textarea
              value={issueText}
              onChange={(event) => setIssueText(event.target.value)}
              placeholder="What happened? Describe the issue and what you were doing."
              style={styles.textArea}
            />

            <label style={styles.toggleRow}>
              <div>
                <div style={styles.toggleTitle}>Include app diagnostics</div>
                <div style={styles.toggleSubtitle}>App version and platform only — never your journal or messages</div>
              </div>
              <input
                type="checkbox"
                checked={shareDiagnostics}
                onChange={(event) => setShareDiagnostics(event.target.checked)}
                style={styles.checkbox}
              />
            </label>

            <button
              style={{ ...styles.sendButton, ...((!issueText.trim() || isSubmitting) ? styles.sendButtonDisabled : {}) }}
              disabled={!issueText.trim() || isSubmitting}
              onClick={() => void handleSubmit()}
            >
              {isSubmitting ? "Sending..." : "Send to team"}
            </button>

            <p style={styles.privacyNote}>Your journal and conversation content is never included.</p>
          </section>
        ) : (
          <section style={styles.card}>
            <h2 style={styles.cardTitle}>Support code ready</h2>
            <p style={styles.cardSubtitle}>Share this code with the Sakhi team so they can review your report metadata.</p>

            <div style={styles.codePill}>{supportCode || "—"}</div>
            <p style={styles.expiryText}>{formatExpiry(supportExpiresAt)}</p>

            <div style={styles.successBox}>Only metadata was shared. Journal/chat text was not included.</div>

            <button style={styles.copyButton} onClick={() => void navigator.clipboard?.writeText(supportCode)}>
              Copy code
            </button>

            <button
              style={{ ...styles.revokeButton, ...(isRevoking ? styles.revokeButtonDisabled : {}) }}
              onClick={() => void handleRevoke()}
              disabled={isRevoking || revoked}
            >
              {revoked ? "Access revoked" : isRevoking ? "Revoking..." : "Revoke access now"}
            </button>
          </section>
        )}

        {error ? <p style={styles.errorText}>{error}</p> : null}

        <section style={styles.cardMuted}>
          <h3 style={styles.cardMutedTitle}>What gets shared</h3>
          <ul style={styles.list}>
            <li>App metadata only (version, platform, route context)</li>
            <li>Your issue summary</li>
            <li>No journal text, no message text</li>
          </ul>
        </section>
      </main>
    </div>
  );
}

function PageFallback() {
  return (
    <div style={{ minHeight: "100vh", display: "grid", placeItems: "center", background: styles.container.background, color: palette.muted, fontFamily: editorialFontFamily }}>
      Loading...
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    minHeight: "100vh",
    background: `radial-gradient(circle at top right, ${palette.auroraCool} 0%, transparent 28%), radial-gradient(circle at bottom left, ${palette.auroraWarm} 0%, transparent 24%), ${palette.bg}`,
    color: palette.fg,
    fontFamily: editorialFontFamily,
  },
  header: {
    borderBottom: `1px solid ${palette.border}`,
    padding: "14px 18px",
    display: "flex",
    alignItems: "center",
    gap: 12,
    background: palette.glassMuted,
    backdropFilter: "blur(18px)",
  },
  iconButton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    border: `1px solid ${palette.border}`,
    background: palette.glass,
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
    fontSize: 24,
    letterSpacing: "-0.02em",
  },
  content: {
    padding: 18,
    display: "grid",
    gap: 16,
    maxWidth: 860,
    margin: "0 auto",
  },
  card: {
    borderRadius: 24,
    border: `1px solid ${palette.border}`,
    background: palette.glassStrong,
    boxShadow: "0 20px 48px rgba(3, 6, 12, 0.28)",
    padding: 16,
    display: "grid",
    gap: 14,
  },
  textArea: {
    minHeight: 130,
    borderRadius: 16,
    border: `1px solid ${palette.border}`,
    background: palette.glass,
    color: palette.fg,
    fontSize: 15,
    lineHeight: 1.5,
    padding: 14,
    resize: "vertical",
    outline: "none",
  },
  toggleRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    gap: 12,
    borderRadius: 16,
    border: `1px solid ${palette.border}`,
    background: palette.glassMuted,
    padding: "12px 14px",
  },
  toggleTitle: {
    fontSize: 14,
    fontWeight: 600,
  },
  toggleSubtitle: {
    marginTop: 2,
    fontSize: 12,
    color: palette.muted,
  },
  checkbox: {
    width: 18,
    height: 18,
    accentColor: palette.accent,
  },
  sendButton: {
    borderRadius: 14,
    border: `1px solid ${palette.accentBorder}`,
    background: palette.accentSoft,
    color: palette.accentText,
    padding: "12px 15px",
    minHeight: 48,
    fontSize: 14,
    fontWeight: 600,
    cursor: "pointer",
  },
  sendButtonDisabled: {
    opacity: 0.58,
    cursor: "default",
  },
  privacyNote: {
    margin: 0,
    fontSize: 13,
    color: palette.muted,
  },
  cardTitle: {
    margin: 0,
    fontSize: 20,
    letterSpacing: "-0.02em",
  },
  cardSubtitle: {
    margin: 0,
    color: palette.muted,
    fontSize: 13,
    lineHeight: 1.5,
  },
  codePill: {
    borderRadius: 999,
    border: `1px solid ${palette.accentBorder}`,
    background: palette.accentSoft,
    color: palette.success,
    padding: "12px 14px",
    fontFamily: "monospace",
    fontSize: 18,
    letterSpacing: "0.06em",
  },
  expiryText: {
    margin: 0,
    color: palette.warning,
    fontSize: 13,
  },
  successBox: {
    borderRadius: 12,
    border: `1px solid rgba(147, 192, 167, 0.34)`,
    background: palette.successBg,
    color: palette.fg,
    padding: "10px 12px",
    fontSize: 14,
  },
  copyButton: {
    borderRadius: 14,
    border: `1px solid ${palette.border}`,
    background: palette.glassMuted,
    color: palette.fg,
    padding: "10px 12px",
    fontSize: 14,
    cursor: "pointer",
  },
  revokeButton: {
    borderRadius: 14,
    border: `1px solid rgba(220, 198, 152, 0.42)`,
    background: palette.warningBg,
    color: palette.warning,
    padding: "10px 12px",
    fontSize: 14,
    cursor: "pointer",
  },
  revokeButtonDisabled: {
    opacity: 0.58,
    cursor: "default",
  },
  errorText: {
    margin: 0,
    color: palette.danger,
    fontSize: 14,
  },
  cardMuted: {
    borderRadius: 20,
    border: `1px solid ${palette.border}`,
    background: palette.glass,
    padding: "14px 16px",
  },
  cardMutedTitle: {
    margin: 0,
    fontSize: 14,
    color: palette.fg,
  },
  list: {
    margin: "8px 0 0",
    color: palette.muted,
    lineHeight: 1.5,
    paddingLeft: 20,
    fontSize: 14,
  },
};
