import React, { useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Platform,
  Pressable,
  ScrollView,
  Share,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import Constants from "expo-constants";

import { useAuth } from "../../lib/auth/AuthContext";
import { config } from "../../lib/config";
import { Analytics } from "../../lib/analytics/events";
import { useAppHaptics } from "../../lib/feedback/useAppHaptics";
import { theme } from "../../lib/theme/tokens";
import {
  clearActiveSupportDebugSession,
  getActiveSupportDebugSession,
  startSupportDebugSession,
  stopSupportDebugSession,
  type SupportDebugSession,
} from "../../lib/support/debugTelemetry";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { IconButton } from "../../components/ui/IconButton";
import { Screen } from "../../components/ui/Screen";

const palette = {
  bg: theme.colors.bg,
  fg: theme.colors.text,
  muted: theme.colors.textMuted,
  subtle: theme.colors.textSubtle,
  border: theme.colors.border,
  cardBg: theme.colors.surface,
  accent: theme.colors.accent,
  warning: theme.colors.warning,
  warningBg: theme.colors.warningSurface,
  success: theme.colors.success,
  successBg: theme.colors.successSurface,
};

function redactPersonId(value: string): string {
  const raw = String(value || "").trim();
  if (!raw) return "none";
  if (raw.length <= 10) return raw;
  return `${raw.slice(0, 6)}...${raw.slice(-4)}`;
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

export default function SupportConsoleScreen() {
  const router = useRouter();
  const { user, session } = useAuth();
  const haptics = useAppHaptics();
  const inputRef = useRef<TextInput>(null);

  // Form state
  const [issueText, setIssueText] = useState("");
  const [shareDiagnostics, setShareDiagnostics] = useState(true);

  // Submission state
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [supportCode, setSupportCode] = useState("");
  const [supportExpiresAt, setSupportExpiresAt] = useState("");

  // Advanced panel
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [isRevoking, setIsRevoking] = useState(false);
  const [revoked, setRevoked] = useState(false);

  // Live debug session (advanced)
  const [debugSession, setDebugSession] = useState<SupportDebugSession | null>(null);
  const [isStartingDebugSession, setIsStartingDebugSession] = useState(false);
  const [isStoppingDebugSession, setIsStoppingDebugSession] = useState(false);

  const BACKEND_URL = (config.backendUrl || "").replace(/\/+$/, "");
  const authToken = session?.access_token;
  const personId = user?.personId || "";

  const appVersion =
    Constants.expoConfig?.version
    || Constants.expoConfig?.ios?.buildNumber
    || "unknown";

  const debugSessionActive = Boolean(debugSession && debugSession.status.toLowerCase() === "active");
  const supportCodeActive = Boolean(supportCode && !revoked);

  useEffect(() => {
    let cancelled = false;
    const loadSession = async () => {
      const stored = await getActiveSupportDebugSession();
      if (cancelled || !stored) return;
      if (personId && stored.personId !== personId) return;
      setDebugSession(stored);
      if (!supportCode) setSupportCode(stored.supportCode);
    };
    void loadSession();
    return () => { cancelled = true; };
  }, [personId, supportCode]);

  // Auto-focus input
  useEffect(() => {
    const timer = setTimeout(() => inputRef.current?.focus(), 300);
    return () => clearTimeout(timer);
  }, []);

  const handleSubmit = async () => {
    if (!issueText.trim()) {
      Alert.alert("What happened?", "Add a brief description before sending.");
      return;
    }
    if (!personId) {
      Alert.alert("Not signed in", "Sign in again to send a report.");
      return;
    }
    if (!BACKEND_URL) {
      Alert.alert("Configuration error", "Backend URL is not set.");
      return;
    }

    try {
      setIsSubmitting(true);
      const response = await fetch(`${BACKEND_URL}/support/report`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
        },
        body: JSON.stringify({
          person_id: personId,
          issue_summary: issueText.trim(),
          diagnostics: {
            enabled: shareDiagnostics,
            include_conversation_metadata: false,
          },
          client_context: {
            appVersion,
            platform: `${Platform.OS} ${String(Platform.Version)}`,
            profile: redactPersonId(personId),
            source: "support_simple",
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
      Analytics.supportReportCreated({ diagnostics_enabled: shareDiagnostics });
      haptics.success();
      setSupportCode(code);
      setSupportExpiresAt(expires);
      setSubmitted(true);
    } catch (error) {
      Alert.alert(
        "Could not send",
        error instanceof Error ? error.message : "Please try again.",
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRevoke = async () => {
    if (!supportCode || !personId || !BACKEND_URL) return;
    try {
      setIsRevoking(true);
      const response = await fetch(`${BACKEND_URL}/support/report/revoke`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
        },
        body: JSON.stringify({ person_id: personId, support_code: supportCode }),
      });
      if (!response.ok) throw new Error("revoke_failed");
      await clearActiveSupportDebugSession();
      haptics.success();
      setDebugSession(null);
      setRevoked(true);
    } catch {
      Alert.alert("Could not revoke", "Try again or the code will expire automatically.");
    } finally {
      setIsRevoking(false);
    }
  };

  const handleCopyCode = async () => {
    if (!supportCode) return;
    try { await Share.share({ message: supportCode }); } catch { /* noop */ }
  };

  const handleStartDebugSession = async () => {
    if (!supportCodeActive || !supportCode || !personId || !BACKEND_URL) return;
    try {
      setIsStartingDebugSession(true);
      const sessionPayload = await startSupportDebugSession({
        backendUrl: BACKEND_URL,
        authToken,
        personId,
        supportCode,
        durationMinutes: 30,
        clientContext: { appVersion, platform: `${Platform.OS} ${String(Platform.Version)}` },
      });
      Analytics.supportDebugSessionStarted();
      haptics.success();
      setDebugSession(sessionPayload);
    } catch (error) {
      Alert.alert("Could not start live debug", error instanceof Error ? error.message : "Try again.");
    } finally {
      setIsStartingDebugSession(false);
    }
  };

  const handleStopDebugSession = async () => {
    if (!debugSession || !personId || !supportCode || !BACKEND_URL) return;
    try {
      setIsStoppingDebugSession(true);
      await stopSupportDebugSession({
        backendUrl: BACKEND_URL,
        authToken,
        personId,
        supportCode,
        sessionId: debugSession.sessionId,
      });
      haptics.success();
      setDebugSession(null);
    } catch (error) {
      Alert.alert("Could not stop session", error instanceof Error ? error.message : "Try again.");
    } finally {
      setIsStoppingDebugSession(false);
    }
  };

  return (
    <Screen>
      <View style={styles.header}>
        <IconButton
          icon={<Ionicons name="chevron-back" size={20} color={palette.fg} />}
          onPress={() => router.back()}
        />
        <View style={styles.headerTextWrap}>
          <Text style={styles.kicker}>Beta</Text>
          <Text style={styles.title}>Something wrong?</Text>
        </View>
      </View>

      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
        keyboardShouldPersistTaps="handled"
      >
        {!submitted ? (
          <>
            <TextInput
              ref={inputRef}
              style={styles.input}
              placeholder="What happened? Describe the issue and what you were doing."
              placeholderTextColor={palette.subtle}
              value={issueText}
              onChangeText={setIssueText}
              multiline
              numberOfLines={5}
              textAlignVertical="top"
            />

            <View style={styles.toggleRow}>
              <View style={styles.toggleCopy}>
                <Text style={styles.toggleTitle}>Include app diagnostics</Text>
                <Text style={styles.toggleSubtitle}>
                  App version and platform only — never your journal or messages
                </Text>
              </View>
              <Switch
                value={shareDiagnostics}
                onValueChange={setShareDiagnostics}
                trackColor={{ false: "#3b4558", true: "rgba(52, 155, 169, 0.4)" }}
                thumbColor={shareDiagnostics ? palette.accent : "#c2cad6"}
                ios_backgroundColor="#3b4558"
              />
            </View>

            <Button
              label={isSubmitting ? "Sending..." : "Send to team"}
              busy={isSubmitting}
              disabled={!issueText.trim() || isSubmitting}
              onPress={() => void handleSubmit()}
              style={styles.sendButton}
              leftIcon={<Ionicons name="paper-plane-outline" size={16} color="#e6f7fa" />}
            />

            <Text style={styles.privacyNote}>
              Your journal and conversation content is never included.
            </Text>
          </>
        ) : (
          <>
            <Card style={styles.successCard}>
              <Ionicons name="checkmark-circle" size={36} color={palette.success} />
              <Text style={styles.successTitle}>Sent</Text>
              <Text style={styles.successBody}>
                We'll look into it. If we need more context, we'll reach out directly.
              </Text>
            </Card>

            {!revoked ? (
              <Pressable
                style={styles.revokeLink}
                onPress={() => void handleRevoke()}
                disabled={isRevoking}
              >
                {isRevoking
                  ? <ActivityIndicator size="small" color={palette.subtle} />
                  : <Text style={styles.revokeLinkText}>Revoke access anytime</Text>
                }
              </Pressable>
            ) : (
              <Text style={styles.revokedNote}>Access revoked — the team can no longer view this report.</Text>
            )}

            {supportCode && !revoked && (
              <View style={styles.advancedWrap}>
                <Pressable
                  style={styles.advancedToggle}
                  onPress={() => setAdvancedOpen((v) => !v)}
                >
                  <Text style={styles.advancedToggleText}>Advanced</Text>
                  <Ionicons
                    name={advancedOpen ? "chevron-up" : "chevron-down"}
                    size={14}
                    color={palette.subtle}
                  />
                </Pressable>

                {advancedOpen && (
                  <View style={styles.advancedPanel}>
                    {/* Support code */}
                    <View style={styles.codeRow}>
                      <View>
                        <Text style={styles.codeLabel}>Support code</Text>
                        <Text style={styles.codeValue}>{supportCode}</Text>
                        {supportExpiresAt
                          ? <Text style={styles.codeMeta}>{formatExpiry(supportExpiresAt)}</Text>
                          : null}
                      </View>
                      <Pressable style={styles.copyButton} onPress={() => void handleCopyCode()}>
                        <Ionicons name="copy-outline" size={15} color={palette.accent} />
                        <Text style={styles.copyButtonText}>Copy</Text>
                      </Pressable>
                    </View>

                    {/* Live debug session */}
                    <View style={styles.debugSection}>
                      <Text style={styles.debugLabel}>Live debug timeline</Text>
                      <Text style={styles.debugHint}>
                        Captures screen and API metadata only. Use when the team asks.
                      </Text>
                      {debugSessionActive ? (
                        <View style={styles.debugActiveRow}>
                          <View style={styles.debugActiveDot} />
                          <Text style={styles.debugActiveText}>Session active</Text>
                          <Pressable
                            style={styles.debugStopButton}
                            onPress={() => void handleStopDebugSession()}
                            disabled={isStoppingDebugSession}
                          >
                            {isStoppingDebugSession
                              ? <ActivityIndicator size="small" color={palette.warning} />
                              : <Text style={styles.debugStopText}>Stop</Text>
                            }
                          </Pressable>
                        </View>
                      ) : (
                        <Pressable
                          style={styles.debugStartButton}
                          onPress={() => void handleStartDebugSession()}
                          disabled={isStartingDebugSession}
                        >
                          {isStartingDebugSession
                            ? <ActivityIndicator size="small" color={palette.accent} />
                            : <Text style={styles.debugStartText}>Start live debug</Text>
                          }
                        </Pressable>
                      )}
                    </View>
                  </View>
                )}
              </View>
            )}
          </>
        )}
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: palette.bg,
  },
  header: {
    paddingHorizontal: 18,
    paddingTop: Platform.OS === "android" ? 16 : 12,
    paddingBottom: 10,
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    borderBottomWidth: 1,
    borderBottomColor: palette.border,
  },
  headerTextWrap: { gap: 2 },
  kicker: {
    color: palette.muted,
    fontSize: 11,
    textTransform: "uppercase",
    letterSpacing: 1.2,
  },
  title: {
    color: palette.fg,
    fontSize: 22,
    fontWeight: "600",
  },
  scroll: { flex: 1 },
  scrollContent: {
    paddingHorizontal: 16,
    paddingTop: 20,
    paddingBottom: 40,
    gap: 14,
  },
  input: {
    borderRadius: 16,
    borderWidth: 1,
    borderColor: "rgba(176, 196, 228, 0.2)",
    backgroundColor: "rgba(18, 28, 43, 0.72)",
    color: palette.fg,
    fontSize: 15,
    lineHeight: 22,
    paddingHorizontal: 14,
    paddingVertical: 12,
    minHeight: 130,
  },
  toggleRow: {
    borderRadius: 14,
    borderWidth: 1,
    borderColor: "rgba(176, 196, 228, 0.15)",
    backgroundColor: "rgba(22, 34, 52, 0.74)",
    paddingHorizontal: 14,
    paddingVertical: 12,
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
  },
  toggleCopy: { flex: 1, gap: 3 },
  toggleTitle: {
    color: palette.fg,
    fontSize: 14,
    fontWeight: "500",
  },
  toggleSubtitle: {
    color: palette.subtle,
    fontSize: 12,
    lineHeight: 17,
  },
  sendButton: {
    marginTop: 4,
  },
  privacyNote: {
    color: palette.subtle,
    fontSize: 12,
    textAlign: "center",
    lineHeight: 17,
  },
  // Success state
  successCard: {
    borderRadius: 20,
    borderWidth: 1,
    borderColor: "rgba(52, 211, 153, 0.25)",
    backgroundColor: palette.successBg,
    paddingHorizontal: 20,
    paddingVertical: 28,
    alignItems: "center",
    gap: 10,
    marginTop: 12,
  },
  successTitle: {
    color: palette.success,
    fontSize: 24,
    fontWeight: "700",
  },
  successBody: {
    color: "#a8d8c8",
    fontSize: 14,
    lineHeight: 21,
    textAlign: "center",
  },
  revokeLink: {
    alignSelf: "center",
    paddingVertical: 6,
    paddingHorizontal: 12,
  },
  revokeLinkText: {
    color: palette.subtle,
    fontSize: 13,
    textDecorationLine: "underline",
  },
  revokedNote: {
    color: palette.subtle,
    fontSize: 13,
    textAlign: "center",
    lineHeight: 18,
  },
  // Advanced panel
  advancedWrap: {
    marginTop: 8,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: palette.border,
    overflow: "hidden",
  },
  advancedToggle: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 14,
    paddingVertical: 12,
    backgroundColor: "rgba(21, 28, 40, 0.5)",
  },
  advancedToggleText: {
    color: palette.subtle,
    fontSize: 13,
    fontWeight: "500",
  },
  advancedPanel: {
    paddingHorizontal: 14,
    paddingVertical: 12,
    gap: 16,
    borderTopWidth: 1,
    borderTopColor: palette.border,
  },
  codeRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 8,
  },
  codeLabel: {
    color: palette.subtle,
    fontSize: 11,
    textTransform: "uppercase",
    letterSpacing: 0.8,
    marginBottom: 2,
  },
  codeValue: {
    color: palette.fg,
    fontSize: 16,
    fontWeight: "700",
    letterSpacing: 0.5,
  },
  codeMeta: {
    color: palette.muted,
    fontSize: 12,
    marginTop: 2,
  },
  copyButton: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "rgba(52, 155, 169, 0.4)",
    backgroundColor: "rgba(33, 103, 113, 0.25)",
  },
  copyButtonText: {
    color: palette.accent,
    fontSize: 12,
    fontWeight: "600",
  },
  debugSection: { gap: 6 },
  debugLabel: {
    color: palette.muted,
    fontSize: 13,
    fontWeight: "500",
  },
  debugHint: {
    color: palette.subtle,
    fontSize: 12,
    lineHeight: 17,
  },
  debugActiveRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginTop: 4,
  },
  debugActiveDot: {
    width: 7,
    height: 7,
    borderRadius: 4,
    backgroundColor: palette.success,
  },
  debugActiveText: {
    color: palette.success,
    fontSize: 13,
    flex: 1,
  },
  debugStopButton: {
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "rgba(248, 221, 181, 0.4)",
    backgroundColor: "rgba(72, 53, 29, 0.45)",
  },
  debugStopText: {
    color: palette.warning,
    fontSize: 12,
    fontWeight: "600",
  },
  debugStartButton: {
    marginTop: 4,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: "rgba(52, 155, 169, 0.35)",
    backgroundColor: "rgba(33, 103, 113, 0.2)",
    alignSelf: "flex-start",
  },
  debugStartText: {
    color: palette.accent,
    fontSize: 13,
    fontWeight: "500",
  },
});
