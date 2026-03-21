import React, { useEffect } from "react";
import {
  View,
  Text,
  StyleSheet,
  ActivityIndicator,
} from "react-native";
import { useRouter } from "expo-router";
import { useAuth } from "../lib/auth/AuthContext";
import { Screen } from "../components/ui/Screen";
import { Button } from "../components/ui/Button";
import { theme } from "../lib/theme/tokens";

// =============================================================================
// HOME SCREEN
// =============================================================================

export default function Index() {
  const router = useRouter();
  const { isAuthenticated, isLoading } = useAuth();

  // Auto-redirect returning users to the main app
  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      router.replace("/experience/converse" as never);
    }
  }, [isLoading, isAuthenticated, router]);

  // Show loading while checking auth state
  if (isLoading || isAuthenticated) {
    return (
      <Screen>
        <View style={styles.content}>
          <ActivityIndicator size="large" color={theme.colors.accent} />
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
});
