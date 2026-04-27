import { useCallback, useEffect } from "react";
import { View, Text, ActivityIndicator, StyleSheet } from "react-native";
import { useRouter, useLocalSearchParams } from "expo-router";
import { recordAuthDebug } from "../../lib/auth/authDebug";
import { completeMobileAuthRedirect } from "../../lib/auth/oauthRedirect";
import { Screen } from "../../components/ui/Screen";
import { theme } from "../../lib/theme/tokens";

// =============================================================================
// AUTH CALLBACK SCREEN
// =============================================================================
// Handles the OAuth redirect callback from Google/Supabase.
// This screen processes the auth tokens and redirects to the appropriate page.

export default function AuthCallback() {
  const router = useRouter();
  const params = useLocalSearchParams();

  const handleCallback = useCallback(async () => {
    try {
      await recordAuthDebug("Entered /auth/callback route", {
        hasAccessToken: typeof params.access_token === "string",
        hasRefreshToken: typeof params.refresh_token === "string",
        hasCode: typeof params.code === "string",
        hasErrorDescription: typeof params.error_description === "string",
      });
      await completeMobileAuthRedirect({
        accessToken: typeof params.access_token === "string" ? params.access_token : null,
        refreshToken: typeof params.refresh_token === "string" ? params.refresh_token : null,
        code: typeof params.code === "string" ? params.code : null,
        errorDescription: typeof params.error_description === "string" ? params.error_description : null,
      });
      // Hand off to the auth screen, which owns bootstrap + post-auth routing.
      await recordAuthDebug("/auth/callback completed session setup, returning to /auth");
      router.replace("/auth" as never);
    } catch (err) {
      await recordAuthDebug("Callback route failed", {
        message: err instanceof Error ? err.message : String(err),
      }, "error");
      router.replace("/auth" as never);
    }
  }, [params.access_token, params.code, params.error_description, params.refresh_token, router]);

  useEffect(() => {
    void handleCallback();
  }, [handleCallback]);

  return (
    <Screen>
      <View style={styles.container}>
        <ActivityIndicator size="large" color={theme.colors.accent} />
        <Text style={styles.text}>Completing sign in...</Text>
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    gap: 16,
  },
  text: {
    color: theme.colors.textSubtle,
    fontSize: 16,
  },
});
