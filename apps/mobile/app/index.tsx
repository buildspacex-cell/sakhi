import React, { useEffect } from "react";
import {
  View,
  Text,
  StyleSheet,
  Pressable,
} from "react-native";
import { useRouter } from "expo-router";
import { useAuth } from "../lib/auth/AuthContext";
import { useAppPreferences } from "../lib/preferences/AppPreferencesContext";
import { Screen } from "../components/ui/Screen";
import { Button } from "../components/ui/Button";
import { SakhiBrandMark, SakhiWordmark } from "../components/brand/SakhiBrandMark";
import { theme } from "../lib/theme/tokens";

const MODE_META = {
  talk: {
    title: "Talk to Sakhi",
    body: "Have a conversation. Get a response.",
    cta: "Start Talking",
    mode: "talk" as const,
  },
  offload: {
    title: "Offload",
    body: "Just put it down. No response expected. Works offline too.",
    cta: "Start Offloading",
    mode: "offload" as const,
  },
};

// =============================================================================
// HOME SCREEN
// =============================================================================

export default function Index() {
  const router = useRouter();
  const { isAuthenticated, isLoading, session, user } = useAuth();
  const { preferences, isReady: preferencesReady, setLastEntryMode } = useAppPreferences();
  const hasResumableSession = !!session && !!user;
  const lastEntryMode = preferences.lastEntryMode;
  const shouldShowModeChooser = !isLoading && preferencesReady && isAuthenticated && !lastEntryMode;

  // Resume returning users from any persisted auth session.
  // If personId hydration is still catching up, the auth screen silently
  // bootstraps the linked mobile profile instead of showing a fresh sign-in.
  useEffect(() => {
    if (isLoading || !preferencesReady) {
      return;
    }

    if (isAuthenticated) {
      if (lastEntryMode) {
        router.replace(`/experience/converse?mode=${lastEntryMode}` as never);
      }
      return;
    }

    if (hasResumableSession) {
      router.replace("/auth" as never);
    }
  }, [hasResumableSession, isAuthenticated, isLoading, lastEntryMode, preferencesReady, router]);

  const startMode = (mode: "talk" | "offload") => {
    setLastEntryMode(mode);
    router.replace(`/experience/converse?mode=${mode}` as never);
  };

  // Show loading while checking auth state
  if (
    isLoading
    || (isAuthenticated && !preferencesReady)
    || (isAuthenticated && !!lastEntryMode)
    || (hasResumableSession && !isAuthenticated)
  ) {
    return (
      <Screen>
        <View style={styles.content}>
          <View style={styles.loadingMark}>
            <SakhiWordmark subtitle="Continuity for the mind" />
          </View>
        </View>
      </Screen>
    );
  }

  if (shouldShowModeChooser) {
    return (
      <Screen showAurora>
        <View style={styles.content}>
          <View style={styles.textContainer}>
            <Text style={styles.headline}>
              This is a quiet space to unload your mind.
            </Text>
            <Text style={styles.subheadline}>
              What do you need right now?
            </Text>
          </View>

          <Pressable style={styles.modeCard} onPress={() => startMode("talk")}>
            <View style={styles.modeCardHeader}>
              <View style={styles.modeIconBadge}>
                <SakhiBrandMark size={30} mode={MODE_META.talk.mode} active />
              </View>
              <Text style={styles.modeTitle}>{MODE_META.talk.title}</Text>
            </View>
            <Text style={styles.modeBody}>{MODE_META.talk.body}</Text>
            <Text style={styles.modeCta}>{MODE_META.talk.cta}</Text>
          </Pressable>

          <Pressable style={styles.modeCard} onPress={() => startMode("offload")}>
            <View style={styles.modeCardHeader}>
              <View style={styles.modeIconBadge}>
                <SakhiBrandMark size={30} mode={MODE_META.offload.mode} active />
              </View>
              <Text style={styles.modeTitle}>{MODE_META.offload.title}</Text>
            </View>
            <Text style={styles.modeBody}>{MODE_META.offload.body}</Text>
            <Text style={styles.modeCta}>{MODE_META.offload.cta}</Text>
          </Pressable>

          <Text style={styles.modeHint}>You can switch anytime. Sakhi will remember what you used last.</Text>
        </View>
      </Screen>
    );
  }

  return (
    <Screen>
      <View style={styles.content}>
        <View style={styles.textContainer}>
          <Text style={styles.headline}>
            This is a quiet space to unload your mind.
          </Text>
          <Text style={styles.subheadline}>
            You can talk, or hand something off.
          </Text>
        </View>

        <Button
          label="BEGIN"
          variant="ghost"
          size="lg"
          style={styles.beginButton}
          textStyle={styles.beginText}
          onPress={() => router.push("/auth" as never)}
        />
      </View>
    </Screen>
  );
}

// =============================================================================
// STYLES
// =============================================================================

const styles = StyleSheet.create({
  content: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    paddingHorizontal: theme.spacing["5xl"],
  },
  textContainer: {
    alignItems: "center",
    marginBottom: theme.spacing["6xl"],
  },
  loadingMark: {
    alignItems: "center",
    justifyContent: "center",
  },
  headline: {
    fontSize: theme.typography.hero.fontSize,
    fontWeight: "400",
    color: theme.colors.white,
    textAlign: "center",
    lineHeight: theme.typography.hero.lineHeight,
    marginBottom: theme.spacing.xl,
  },
  subheadline: {
    fontSize: 16,
    fontWeight: "400",
    color: theme.colors.textSubtle,
    textAlign: "center",
    lineHeight: 24,
  },
  beginButton: {
    marginBottom: theme.spacing["4xl"],
    minWidth: 144,
  },
  beginText: {
    fontSize: 14,
    fontWeight: "500",
    color: theme.colors.textMuted,
    letterSpacing: 2,
  },
  modeCard: {
    width: "100%",
    maxWidth: 360,
    borderRadius: theme.radii.lg,
    borderWidth: 1,
    borderColor: theme.colors.border,
    backgroundColor: theme.colors.surface,
    paddingHorizontal: theme.spacing.xl,
    paddingVertical: theme.spacing.xl,
    marginBottom: theme.spacing.lg,
    gap: theme.spacing.sm,
  },
  modeCardHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: theme.spacing.md,
  },
  modeIconBadge: {
    width: 42,
    height: 42,
    borderRadius: 21,
    alignItems: "center",
    justifyContent: "center",
  },
  modeTitle: {
    fontSize: 18,
    fontWeight: "600",
    color: theme.colors.text,
  },
  modeBody: {
    fontSize: 14,
    lineHeight: 21,
    color: theme.colors.textMuted,
  },
  modeCta: {
    marginTop: theme.spacing.sm,
    fontSize: 13,
    fontWeight: "600",
    letterSpacing: 0.4,
    color: theme.colors.accent,
  },
  modeHint: {
    marginTop: theme.spacing.md,
    maxWidth: 320,
    fontSize: 13,
    color: theme.colors.textFaint,
    textAlign: "center",
    lineHeight: 20,
  },
});
