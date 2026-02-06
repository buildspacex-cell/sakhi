import { useEffect } from "react";
import { View, Text, ActivityIndicator, StyleSheet } from "react-native";
import { useRouter, useLocalSearchParams } from "expo-router";
import { supabase } from "../../lib/supabase";

// =============================================================================
// AUTH CALLBACK SCREEN
// =============================================================================
// Handles the OAuth redirect callback from Google/Supabase.
// This screen processes the auth tokens and redirects to the appropriate page.

export default function AuthCallback() {
  const router = useRouter();
  const params = useLocalSearchParams();

  useEffect(() => {
    handleCallback();
  }, []);

  const handleCallback = async () => {
    try {
      // The tokens might be in the URL hash or as query params
      const accessToken = params.access_token as string;
      const refreshToken = params.refresh_token as string;
      const code = params.code as string;

      if (accessToken && refreshToken) {
        // Set the session with the tokens
        const { error } = await supabase.auth.setSession({
          access_token: accessToken,
          refresh_token: refreshToken,
        });

        if (error) {
          console.error("Session error:", error);
          router.replace("/auth" as never);
          return;
        }

        // Session set successfully, redirect to check onboarding
        router.replace("/onboarding" as never);
      } else if (code) {
        // Exchange the code for a session
        const { error } = await supabase.auth.exchangeCodeForSession(code);

        if (error) {
          console.error("Code exchange error:", error);
          router.replace("/auth" as never);
          return;
        }

        router.replace("/onboarding" as never);
      } else {
        // No valid auth data, go back to auth
        console.error("No auth tokens or code found in callback");
        router.replace("/auth" as never);
      }
    } catch (err) {
      console.error("Callback error:", err);
      router.replace("/auth" as never);
    }
  };

  return (
    <View style={styles.container}>
      <ActivityIndicator size="large" color="#6366f1" />
      <Text style={styles.text}>Completing sign in...</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#0a0a0a",
    alignItems: "center",
    justifyContent: "center",
    gap: 16,
  },
  text: {
    color: "#71717a",
    fontSize: 16,
  },
});
