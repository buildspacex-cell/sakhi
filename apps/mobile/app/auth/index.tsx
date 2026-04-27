import { useState, useEffect, useRef } from "react";
import {
  View,
  Text,
  StyleSheet,
  ActivityIndicator,
  Alert,
  ScrollView,
  Share,
} from "react-native";
import { useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { useAuth } from "../../lib/auth/AuthContext";
import {
  clearAuthDebug,
  formatAuthDebugEntries,
  getAuthDebugEntries,
  recordAuthDebug,
  subscribeAuthDebug,
  type AuthDebugEntry,
} from "../../lib/auth/authDebug";
import { bootstrapMobileAuthProfile } from "../../lib/auth/mobileBootstrap";
import { config } from "../../lib/config";
import { Screen } from "../../components/ui/Screen";
import { Button } from "../../components/ui/Button";
import { IconButton } from "../../components/ui/IconButton";
import { theme } from "../../lib/theme/tokens";

function getReadableErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message.trim()) {
    return error.message.trim();
  }
  return fallback;
}

function describeTarget(url: string): string {
  try {
    const parsed = new URL(url);
    return `${parsed.host}${parsed.pathname === "/" ? "" : parsed.pathname}`;
  } catch {
    return url || "not-set";
  }
}

// =============================================================================
// AUTH SCREEN
// =============================================================================
// Soft, calm authentication that feels like a natural step, not a barrier.

export default function AuthScreen() {
  const router = useRouter();
  const { signInWithGoogle, user, session, hydrateLinkedProfile } = useAuth();

  const [isGoogleLoading, setIsGoogleLoading] = useState(false);
  const [waitingForSession, setWaitingForSession] = useState(false);
  const [isRoutingAuthenticatedUser, setIsRoutingAuthenticatedUser] = useState(false);
  const [showDiagnostics, setShowDiagnostics] = useState(false);
  const [authDebugEntries, setAuthDebugEntries] = useState<AuthDebugEntry[]>(() => getAuthDebugEntries());
  const lastBootstrapKeyRef = useRef<string | null>(null);

  useEffect(() => subscribeAuthDebug(setAuthDebugEntries), []);

  useEffect(() => {
    if (authDebugEntries.some((entry) => entry.level === "error")) {
      setShowDiagnostics(true);
    }
  }, [authDebugEntries]);

  useEffect(() => {
    if (!waitingForSession) {
      return;
    }

    if (session?.access_token && user) {
      void recordAuthDebug("Session became available while waiting for sign-in", {
        userId: user.id,
        hasPersonId: !!user.personId,
      });
      return;
    }

    const timeout = setTimeout(() => {
      void recordAuthDebug("Timed out waiting for sign-in session", undefined, "error");
      setWaitingForSession(false);
      setIsGoogleLoading(false);
      Alert.alert("Sign In Failed", "Sakhi did not receive the sign-in session. Please try again.");
    }, 12000);

    return () => clearTimeout(timeout);
  }, [session?.access_token, user, waitingForSession]);

  // Resolve the post-login route once auth is present.
  useEffect(() => {
    if (!session?.access_token || !user) {
      setIsRoutingAuthenticatedUser(false);
      return;
    }

    const bootstrapKey = `${user.id}:${session.access_token}`;
    if (lastBootstrapKeyRef.current === bootstrapKey) {
      return;
    }
    lastBootstrapKeyRef.current = bootstrapKey;

    let cancelled = false;
    setIsRoutingAuthenticatedUser(true);
    void recordAuthDebug("Starting authenticated-user bootstrap", {
      userId: user.id,
      email: user.email,
      hasPersonId: !!user.personId,
    });

    const routeAuthenticatedUser = async () => {
      try {
        const profile = await bootstrapMobileAuthProfile(session.access_token, {
          email: user.email || "",
          full_name: user.fullName,
          avatar_url: user.avatarUrl,
        }, { supabaseUserId: user.id });

        await hydrateLinkedProfile({
          personId: profile.person_id,
          email: profile.email,
          fullName: profile.full_name,
          avatarUrl: profile.avatar_url,
        }, { supabaseUserId: user.id });

        if (cancelled) {
          return;
        }

        const routeName = encodeURIComponent(profile.full_name || user.fullName || "");
        const routeUser = encodeURIComponent(profile.person_id);
        if (profile.needs_name) {
          await recordAuthDebug("Routing authenticated user to onboarding", {
            personId: profile.person_id,
          });
          router.replace(`/onboarding?user=${routeUser}&name=${routeName}` as never);
          return;
        }
        await recordAuthDebug("Routing authenticated user to home", {
          personId: profile.person_id,
        });
        router.replace("/" as never);
      } catch (error) {
        if (cancelled) {
          return;
        }
        await recordAuthDebug("Auth screen bootstrap handler failed", {
          message: getReadableErrorMessage(error, "unknown bootstrap error"),
        }, "error");
        lastBootstrapKeyRef.current = null;
        setIsGoogleLoading(false);
        setWaitingForSession(false);
        setIsRoutingAuthenticatedUser(false);
        Alert.alert(
          "Sign In Failed",
          getReadableErrorMessage(error, "Could not finish setting up your account. Please try again."),
        );
      }
    };

    void routeAuthenticatedUser();

    return () => {
      cancelled = true;
    };
  }, [hydrateLinkedProfile, router, session?.access_token, user]);

  const handleGoogleLogin = async () => {
    setIsGoogleLoading(true);
    try {
      await recordAuthDebug("User tapped Continue with Google");
      const outcome = await signInWithGoogle();
      if (outcome === "cancelled") {
        await recordAuthDebug("Google login returned cancelled");
        setIsGoogleLoading(false);
        setWaitingForSession(false);
        return;
      }
      // setSession fires in background - show waiting state until auth resolves.
      await recordAuthDebug("Google login returned success, waiting for session");
      setWaitingForSession(true);
    } catch (error) {
      await recordAuthDebug("Google login failed", {
        message: getReadableErrorMessage(error, "unknown Google login error"),
      }, "error");
      Alert.alert(
        "Sign In Failed",
        getReadableErrorMessage(error, "Could not sign in with Google. Please try again."),
      );
      setIsGoogleLoading(false);
      setWaitingForSession(false);
    }
    // Don't clear loading - keep spinner until the post-auth route is resolved.
  };

  const handleShareDiagnostics = async () => {
    const summary = [
      `Backend: ${describeTarget(config.backendUrl)}`,
      `Supabase: ${describeTarget(config.supabaseUrl)}`,
      `Build profile: ${config.easBuildProfile || "unknown"}`,
      `Has session: ${session?.access_token ? "yes" : "no"}`,
      `User id: ${user?.id || "none"}`,
      `Person id: ${user?.personId || "none"}`,
      "",
      formatAuthDebugEntries(authDebugEntries),
    ].join("\n");

    try {
      await Share.share({ message: summary });
    } catch {
      // noop
    }
  };

  const handleClearDiagnostics = async () => {
    await clearAuthDebug();
  };

  const visibleEntries = authDebugEntries.slice(-8).reverse();
  const authErrorCount = authDebugEntries.filter((entry) => entry.level === "error").length;

  // Waiting for session to be set (after OAuth callback)
  if (waitingForSession || isRoutingAuthenticatedUser) {
    return (
      <Screen>
        <View style={styles.content}>
          <ActivityIndicator size="large" color={theme.colors.accent} />
          <Text style={[styles.subtitle, { marginTop: 24 }]}>Signing you in...</Text>
        </View>
      </Screen>
    );
  }

  // Main auth screen
  return (
    <Screen>
      <IconButton
        style={styles.backButton}
        onPress={() => router.back()}
        icon={<Ionicons name="chevron-back" size={24} color={theme.colors.textSubtle} />}
      />

      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.content}>
          <View style={styles.textContainer}>
            <Text style={styles.explanation}>So Sakhi can stay with you.</Text>
          </View>

          <View style={styles.authButtonsContainer}>
            <Button
              variant="secondary"
              style={[styles.authButton, styles.googleButton, isGoogleLoading && styles.buttonLoading]}
              onPress={handleGoogleLogin}
              disabled={isGoogleLoading}
              busy={isGoogleLoading}
              label="Continue with Google"
              leftIcon={
                <View style={styles.googleIconContainer}>
                  <GoogleIcon />
                </View>
              }
              textStyle={styles.googleButtonText}
            />
          </View>

          <Text style={styles.privacyNote}>
            This space is only between you and Sakhi.
          </Text>

          <View style={styles.diagnosticsToggleRow}>
            <Button
              variant="ghost"
              style={styles.diagnosticsToggle}
              onPress={() => setShowDiagnostics((prev) => !prev)}
              label={showDiagnostics ? "Hide diagnostics" : "Show diagnostics"}
            />
          </View>

          {showDiagnostics ? (
            <View style={styles.diagnosticsCard}>
              <View style={styles.diagnosticsHeader}>
                <Text style={styles.diagnosticsTitle}>Auth diagnostics</Text>
                <Text style={styles.diagnosticsBadge}>
                  {authErrorCount > 0 ? `${authErrorCount} error${authErrorCount === 1 ? "" : "s"}` : "no errors"}
                </Text>
              </View>

              <View style={styles.diagnosticsMetaBlock}>
                <Text style={styles.diagnosticsMeta}>Backend: {describeTarget(config.backendUrl)}</Text>
                <Text style={styles.diagnosticsMeta}>Supabase: {describeTarget(config.supabaseUrl)}</Text>
                <Text style={styles.diagnosticsMeta}>Build: {config.easBuildProfile || "unknown"}</Text>
                <Text style={styles.diagnosticsMeta}>Session: {session?.access_token ? "present" : "missing"}</Text>
                <Text style={styles.diagnosticsMeta}>User: {user?.id || "none"}</Text>
                <Text style={styles.diagnosticsMeta}>Person: {user?.personId || "none"}</Text>
              </View>

              <View style={styles.diagnosticsActions}>
                <Button
                  variant="secondary"
                  style={styles.diagnosticsActionButton}
                  onPress={handleShareDiagnostics}
                  label="Share trace"
                />
                <Button
                  variant="ghost"
                  style={styles.diagnosticsActionButton}
                  onPress={handleClearDiagnostics}
                  label="Clear"
                />
              </View>

              <View style={styles.diagnosticsTimeline}>
                {visibleEntries.length === 0 ? (
                  <Text style={styles.diagnosticsEmpty}>No auth events captured yet.</Text>
                ) : visibleEntries.map((entry) => (
                  <View
                    key={entry.id}
                    style={[
                      styles.diagnosticsEntry,
                      entry.level === "error" && styles.diagnosticsEntryError,
                    ]}
                  >
                    <Text style={styles.diagnosticsEntryTime}>{entry.at}</Text>
                    <Text style={styles.diagnosticsEntryMessage}>{entry.message}</Text>
                    {entry.details ? (
                      <Text style={styles.diagnosticsEntryDetails} selectable>
                        {JSON.stringify(entry.details)}
                      </Text>
                    ) : null}
                  </View>
                ))}
              </View>
            </View>
          ) : null}
        </View>
      </ScrollView>
    </Screen>
  );
}

// =============================================================================
// GOOGLE ICON
// =============================================================================

function GoogleIcon() {
  return (
    <View style={styles.googleIcon}>
      <Text style={styles.googleIconText}>G</Text>
    </View>
  );
}

// =============================================================================
// STYLES
// =============================================================================

const styles = StyleSheet.create({
  backButton: {
    position: "absolute",
    top: 56,
    left: 12,
    zIndex: 10,
    width: 48,
    height: 48,
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    flexGrow: 1,
  },
  content: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    paddingHorizontal: theme.spacing["5xl"],
    paddingTop: 104,
    paddingBottom: theme.spacing["5xl"],
  },
  textContainer: {
    marginBottom: theme.spacing["6xl"],
  },
  subtitle: {
    fontSize: 16,
    color: theme.colors.textMuted,
    textAlign: "center",
    lineHeight: 24,
    marginBottom: theme.spacing["4xl"],
  },
  explanation: {
    fontSize: theme.typography.hero.fontSize,
    fontWeight: "400",
    color: theme.colors.white,
    textAlign: "center",
    lineHeight: theme.typography.hero.lineHeight,
  },
  authButtonsContainer: {
    width: "100%",
    maxWidth: 320,
  },
  authButton: {
    paddingHorizontal: 28,
    width: "100%",
  },
  buttonLoading: {
    opacity: 0.7,
  },
  googleButton: {
    backgroundColor: theme.colors.surface,
    borderWidth: 1,
    borderColor: theme.colors.border,
  },
  googleIconContainer: {
    width: 26,
    height: 26,
    alignItems: "center",
    justifyContent: "center",
  },
  googleIcon: {
    width: 22,
    height: 22,
    borderRadius: 11,
    backgroundColor: theme.colors.white,
    alignItems: "center",
    justifyContent: "center",
  },
  googleIconText: {
    fontSize: 13,
    fontWeight: "700",
    color: "#4285F4",
  },
  googleButtonText: {
    fontSize: 16,
    fontWeight: "500",
    color: theme.colors.text,
  },
  privacyNote: {
    marginTop: theme.spacing["4xl"],
    fontSize: 13,
    color: theme.colors.textFaint,
    textAlign: "center",
  },
  diagnosticsToggleRow: {
    width: "100%",
    maxWidth: 320,
    marginTop: theme.spacing.xl,
  },
  diagnosticsToggle: {
    width: "100%",
  },
  diagnosticsCard: {
    width: "100%",
    maxWidth: 360,
    marginTop: theme.spacing.lg,
    padding: theme.spacing.lg,
    borderRadius: theme.radii.lg,
    backgroundColor: theme.colors.surfaceStrong,
    borderWidth: 1,
    borderColor: theme.colors.borderStrong,
    gap: theme.spacing.md,
  },
  diagnosticsHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: theme.spacing.sm,
  },
  diagnosticsTitle: {
    color: theme.colors.text,
    fontSize: theme.typography.bodyStrong.fontSize,
    lineHeight: theme.typography.bodyStrong.lineHeight,
    fontWeight: "600",
  },
  diagnosticsBadge: {
    color: theme.colors.accentText,
    fontSize: theme.typography.label.fontSize,
    lineHeight: theme.typography.label.lineHeight,
  },
  diagnosticsMetaBlock: {
    gap: theme.spacing.xs,
    padding: theme.spacing.sm,
    borderRadius: theme.radii.md,
    backgroundColor: theme.colors.bgElevated,
    borderWidth: 1,
    borderColor: theme.colors.border,
  },
  diagnosticsMeta: {
    color: theme.colors.textSubtle,
    fontSize: theme.typography.label.fontSize,
    lineHeight: theme.typography.label.lineHeight,
  },
  diagnosticsActions: {
    flexDirection: "row",
    gap: theme.spacing.sm,
  },
  diagnosticsActionButton: {
    flex: 1,
  },
  diagnosticsTimeline: {
    gap: theme.spacing.sm,
  },
  diagnosticsEmpty: {
    color: theme.colors.textFaint,
    fontSize: theme.typography.body.fontSize,
    lineHeight: theme.typography.body.lineHeight,
  },
  diagnosticsEntry: {
    padding: theme.spacing.sm,
    borderRadius: theme.radii.md,
    backgroundColor: theme.colors.bgElevated,
    borderWidth: 1,
    borderColor: theme.colors.border,
    gap: theme.spacing.xxs,
  },
  diagnosticsEntryError: {
    borderColor: theme.colors.dangerStrong,
    backgroundColor: theme.colors.dangerSurface,
  },
  diagnosticsEntryTime: {
    color: theme.colors.textFaint,
    fontSize: 11,
    lineHeight: 14,
  },
  diagnosticsEntryMessage: {
    color: theme.colors.text,
    fontSize: theme.typography.body.fontSize,
    lineHeight: theme.typography.body.lineHeight,
    fontWeight: "600",
  },
  diagnosticsEntryDetails: {
    color: theme.colors.textSubtle,
    fontSize: 12,
    lineHeight: 17,
  },
});
