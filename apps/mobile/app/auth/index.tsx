import React, { useState, useEffect, useRef } from "react";
import {
  View,
  Text,
  StyleSheet,
  ActivityIndicator,
  TextInput,
  Alert,
  KeyboardAvoidingView,
  Platform,
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
// Supports Google and Email magic link authentication.

export default function AuthScreen() {
  const router = useRouter();
  const {
    signInWithGoogle,
    signInWithEmail,
    user,
    session,
  } = useAuth();

  const [isGoogleLoading, setIsGoogleLoading] = useState(false);
  const [isEmailLoading, setIsEmailLoading] = useState(false);
  const [showEmailInput, setShowEmailInput] = useState(false);
  const [email, setEmail] = useState("");
  const [emailSent, setEmailSent] = useState(false);
  const [waitingForSession, setWaitingForSession] = useState(false);
  const [isRoutingAuthenticatedUser, setIsRoutingAuthenticatedUser] = useState(false);
  const lastBootstrapKeyRef = useRef<string | null>(null);

  // Resolve the post-login route once auth is present.
  useEffect(() => {
    if (!session?.access_token || !user) {
      setIsRoutingAuthenticatedUser(false);
      return;
    }
    if (emailSent || showEmailInput) {
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
  }, [emailSent, router, session?.access_token, showEmailInput, user]);

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

  const handleEmailLogin = async () => {
    if (!email.trim()) {
      Alert.alert("Email Required", "Please enter your email address.");
      return;
    }

    // Basic email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email.trim())) {
      Alert.alert("Invalid Email", "Please enter a valid email address.");
      return;
    }

    setIsEmailLoading(true);
    try {
      await signInWithEmail(email.trim());
      setEmailSent(true);
    } catch (error: unknown) {
      console.error("Email login failed:", error);
      const errorMessage = error instanceof Error ? error.message : "Could not send magic link.";
      Alert.alert("Sign In Failed", errorMessage);
    } finally {
      setIsEmailLoading(false);
    }
  };

  const handleBack = () => {
    if (showEmailInput) {
      setShowEmailInput(false);
      setEmail("");
      setEmailSent(false);
    } else {
      router.back();
    }
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

  // Email sent confirmation screen
  if (emailSent) {
    return (
      <Screen>
        <IconButton
          style={styles.backButton}
          onPress={handleBack}
          icon={<Ionicons name="chevron-back" size={24} color={theme.colors.textSubtle} />}
        />
        <View style={styles.content}>
          <View style={styles.iconContainer}>
            <Ionicons name="mail-outline" size={48} color={theme.colors.accent} />
          </View>
          <Text style={styles.title}>Check your email</Text>
          <Text style={styles.subtitle}>
            We sent a magic link to{"\n"}
            <Text style={styles.emailHighlight}>{email}</Text>
          </Text>
          <Button
            variant="ghost"
            label="Use a different email"
            style={styles.secondaryButton}
            textStyle={styles.secondaryButtonText}
            onPress={() => {
              setEmailSent(false);
              setEmail("");
            }}
          />
        </View>
      </Screen>
    );
  }

  // Email input screen
  if (showEmailInput) {
    return (
      <Screen>
        <IconButton
          style={styles.backButton}
          onPress={handleBack}
          icon={<Ionicons name="chevron-back" size={24} color={theme.colors.textSubtle} />}
        />
        <KeyboardAvoidingView
          style={styles.keyboardView}
          behavior={Platform.OS === "ios" ? "padding" : "height"}
        >
          <View style={styles.content}>
            <Text style={styles.title}>Enter your email</Text>
            <Text style={styles.subtitle}>
              We'll send you a magic link to sign in.
            </Text>
            <TextInput
              style={styles.emailInput}
              placeholder="your@email.com"
              placeholderTextColor={theme.colors.textFaint}
              value={email}
              onChangeText={setEmail}
              keyboardType="email-address"
              autoCapitalize="none"
              autoCorrect={false}
              autoFocus
            />
            <Button
              label="Send magic link"
              variant="primary"
              style={[styles.primaryButton, isEmailLoading && styles.buttonLoading]}
              onPress={handleEmailLogin}
              disabled={isEmailLoading}
              busy={isEmailLoading}
            />
          </View>
        </KeyboardAvoidingView>
      </Screen>
    );
  }

  // Main auth screen
  return (
    <Screen>
      <IconButton
        style={styles.backButton}
        onPress={handleBack}
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

          <Button
            variant="secondary"
            style={[styles.authButton, styles.emailButton]}
            onPress={() => setShowEmailInput(true)}
            label="Continue with email"
            leftIcon={<Ionicons name="mail-outline" size={20} color={theme.colors.textMuted} />}
            textStyle={styles.emailButtonText}
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
  keyboardView: {
    flex: 1,
  },
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
  iconContainer: {
    marginBottom: theme.spacing["2xl"],
  },
  textContainer: {
    marginBottom: theme.spacing["6xl"],
  },
  title: {
    fontSize: theme.typography.hero.fontSize,
    fontWeight: "500",
    color: theme.colors.white,
    textAlign: "center",
    marginBottom: theme.spacing.md,
  },
  subtitle: {
    fontSize: 16,
    color: theme.colors.textMuted,
    textAlign: "center",
    lineHeight: 24,
    marginBottom: theme.spacing["4xl"],
  },
  emailHighlight: {
    color: theme.colors.accent,
    fontWeight: "500",
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
    gap: 14,
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
  emailButton: {
    backgroundColor: "transparent",
    borderWidth: 1,
    borderColor: theme.colors.border,
  },
  emailButtonText: {
    fontSize: 16,
    fontWeight: "500",
    color: theme.colors.textMuted,
  },
  emailInput: {
    backgroundColor: theme.colors.surface,
    borderWidth: 1,
    borderColor: theme.colors.border,
    borderRadius: theme.radii.sm + 2,
    paddingVertical: 18,
    paddingHorizontal: 18,
    fontSize: 16,
    color: theme.colors.text,
    width: "100%",
    maxWidth: 320,
    marginBottom: theme.spacing.xl,
    minHeight: 56,
  },
  primaryButton: {
    paddingHorizontal: 28,
    width: "100%",
    maxWidth: 320,
  },
  secondaryButton: {
    minHeight: 48,
  },
  secondaryButtonText: {
    fontSize: 14,
    color: theme.colors.accent,
  },
  privacyNote: {
    marginTop: theme.spacing["4xl"],
    fontSize: 13,
    color: theme.colors.textFaint,
    textAlign: "center",
  },
});
