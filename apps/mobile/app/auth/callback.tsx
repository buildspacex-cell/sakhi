import { useEffect } from "react";
import { View, Text, ActivityIndicator, StyleSheet } from "react-native";
import { useRouter, useLocalSearchParams } from "expo-router";
import { supabase } from "../../lib/supabase";
import { bootstrapMobileAuthProfile } from "../../lib/auth/mobileBootstrap";
import { useAuth } from "../../lib/auth/AuthContext";
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
  const { hydrateLinkedProfile } = useAuth();

  useEffect(() => {
    handleCallback();
  }, []);

  const handleCallback = async () => {
    try {
      // The tokens might be in the URL hash or as query params
      const accessToken = params.access_token as string;
      const refreshToken = params.refresh_token as string;
      const code = params.code as string;

      const finalizeRoute = async (tokenHint?: string) => {
        const {
          data: { user },
          error: userError,
        } = await supabase.auth.getUser();

        if (userError || !user) {
          console.error("Could not load authenticated user:", userError);
          router.replace("/auth" as never);
          return;
        }

        const {
          data: { session },
        } = await supabase.auth.getSession();
        const authToken = tokenHint || session?.access_token || "";
        if (!authToken) {
          router.replace("/auth" as never);
          return;
        }

        const profile = await bootstrapMobileAuthProfile(authToken, {
          email: user.email || "",
          full_name: user.user_metadata?.full_name || user.user_metadata?.name,
          avatar_url: user.user_metadata?.avatar_url || user.user_metadata?.picture,
        }, { supabaseUserId: user.id });

        await hydrateLinkedProfile({
          personId: profile.person_id,
          email: profile.email,
          fullName: profile.full_name,
          avatarUrl: profile.avatar_url,
        }, { supabaseUserId: user.id });

        const routeName = encodeURIComponent(profile.full_name || "");
        const routeUser = encodeURIComponent(profile.person_id);
        if (profile.needs_name) {
          router.replace(`/onboarding?user=${routeUser}&name=${routeName}` as never);
          return;
        }
        router.replace(`/experience/converse?user=${routeUser}&name=${routeName}` as never);
      };

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

        await finalizeRoute(accessToken);
      } else if (code) {
        // Exchange the code for a session
        const { data, error } = await supabase.auth.exchangeCodeForSession(code);

        if (error) {
          console.error("Code exchange error:", error);
          router.replace("/auth" as never);
          return;
        }

        await finalizeRoute(data.session?.access_token);
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
