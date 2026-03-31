import { useState, useEffect, useRef } from "react";
import {
  View,
  Text,
  StyleSheet,
  ActivityIndicator,
  Alert,
} from "react-native";
import { useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { useAuth } from "../../lib/auth/AuthContext";
import { bootstrapMobileAuthProfile } from "../../lib/auth/mobileBootstrap";
import { Screen } from "../../components/ui/Screen";
import { Button } from "../../components/ui/Button";
import { IconButton } from "../../components/ui/IconButton";
import { theme } from "../../lib/theme/tokens";

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
  const lastBootstrapKeyRef = useRef<string | null>(null);

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
          router.replace(`/onboarding?user=${routeUser}&name=${routeName}` as never);
          return;
        }
        router.replace(`/experience/converse?user=${routeUser}&name=${routeName}` as never);
      } catch (error) {
        if (cancelled) {
          return;
        }
        console.error("Mobile auth bootstrap failed:", error);
        lastBootstrapKeyRef.current = null;
        setIsGoogleLoading(false);
        setWaitingForSession(false);
        setIsRoutingAuthenticatedUser(false);
        Alert.alert("Sign In Failed", "Could not finish setting up your account. Please try again.");
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
      await signInWithGoogle();
      // setSession fires in background - show waiting state until auth resolves.
      setWaitingForSession(true);
    } catch (error) {
      console.error("Google login failed:", error);
      Alert.alert("Sign In Failed", "Could not sign in with Google. Please try again.");
      setIsGoogleLoading(false);
    }
    // Don't clear loading - keep spinner until the post-auth route is resolved.
  };

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
      </View>
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
  content: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    paddingHorizontal: theme.spacing["5xl"],
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
});
