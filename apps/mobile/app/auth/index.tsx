import React, { useState, useEffect, useRef } from "react";
import {
  View,
  Text,
  Pressable,
  StyleSheet,
  SafeAreaView,
  StatusBar,
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
      <SafeAreaView style={styles.container}>
        <StatusBar barStyle="light-content" />
        <View style={styles.content}>
          <ActivityIndicator size="large" color="#6366f1" />
          <Text style={[styles.subtitle, { marginTop: 24 }]}>Signing you in...</Text>
        </View>
      </SafeAreaView>
    );
  }

  // Email sent confirmation screen
  if (emailSent) {
    return (
      <SafeAreaView style={styles.container}>
        <StatusBar barStyle="light-content" />
        <Pressable style={styles.backButton} onPress={handleBack}>
          <Ionicons name="chevron-back" size={24} color="#71717a" />
        </Pressable>
        <View style={styles.content}>
          <View style={styles.iconContainer}>
            <Ionicons name="mail-outline" size={48} color="#6366f1" />
          </View>
          <Text style={styles.title}>Check your email</Text>
          <Text style={styles.subtitle}>
            We sent a magic link to{"\n"}
            <Text style={styles.emailHighlight}>{email}</Text>
          </Text>
          <Pressable
            style={styles.secondaryButton}
            onPress={() => {
              setEmailSent(false);
              setEmail("");
            }}
          >
            <Text style={styles.secondaryButtonText}>Use a different email</Text>
          </Pressable>
        </View>
      </SafeAreaView>
    );
  }

  // Email input screen
  if (showEmailInput) {
    return (
      <SafeAreaView style={styles.container}>
        <StatusBar barStyle="light-content" />
        <Pressable style={styles.backButton} onPress={handleBack}>
          <Ionicons name="chevron-back" size={24} color="#71717a" />
        </Pressable>
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
              placeholderTextColor="#52525b"
              value={email}
              onChangeText={setEmail}
              keyboardType="email-address"
              autoCapitalize="none"
              autoCorrect={false}
              autoFocus
            />
            <Pressable
              style={[styles.primaryButton, isEmailLoading && styles.buttonLoading]}
              onPress={handleEmailLogin}
              disabled={isEmailLoading}
            >
              {isEmailLoading ? (
                <ActivityIndicator color="#ffffff" size="small" />
              ) : (
                <Text style={styles.primaryButtonText}>Send magic link</Text>
              )}
            </Pressable>
          </View>
        </KeyboardAvoidingView>
      </SafeAreaView>
    );
  }

  // Main auth screen
  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" />

      {/* Back button */}
      <Pressable style={styles.backButton} onPress={handleBack}>
        <Ionicons name="chevron-back" size={24} color="#71717a" />
      </Pressable>

      {/* Content */}
      <View style={styles.content}>
        {/* Explanation */}
        <View style={styles.textContainer}>
          <Text style={styles.explanation}>So Sakhi can stay with you.</Text>
        </View>

        {/* Auth buttons */}
        <View style={styles.authButtonsContainer}>
          {/* Google Sign In */}
          <Pressable
            style={[styles.authButton, styles.googleButton, isGoogleLoading && styles.buttonLoading]}
            onPress={handleGoogleLogin}
            disabled={isGoogleLoading}
          >
            {isGoogleLoading ? (
              <ActivityIndicator color="#ffffff" size="small" />
            ) : (
              <>
                <View style={styles.googleIconContainer}>
                  <GoogleIcon />
                </View>
                <Text style={styles.googleButtonText}>Continue with Google</Text>
              </>
            )}
          </Pressable>

          {/* Email Sign In */}
          <Pressable
            style={[styles.authButton, styles.emailButton]}
            onPress={() => setShowEmailInput(true)}
          >
            <Ionicons name="mail-outline" size={20} color="#a1a1aa" />
            <Text style={styles.emailButtonText}>Continue with email</Text>
          </Pressable>
        </View>

        {/* Privacy note */}
        <Text style={styles.privacyNote}>
          This space is only between you and Sakhi.
        </Text>
      </View>
    </SafeAreaView>
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
  container: {
    flex: 1,
    backgroundColor: "#0a0a0a",
  },
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
    alignItems: "center",
    justifyContent: "center",
  },
  content: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    paddingHorizontal: 40,
  },
  iconContainer: {
    marginBottom: 24,
  },
  textContainer: {
    marginBottom: 56,
  },
  title: {
    fontSize: 24,
    fontWeight: "500",
    color: "#ffffff",
    textAlign: "center",
    marginBottom: 12,
  },
  subtitle: {
    fontSize: 16,
    color: "#a1a1aa",
    textAlign: "center",
    lineHeight: 24,
    marginBottom: 32,
  },
  emailHighlight: {
    color: "#6366f1",
    fontWeight: "500",
  },
  explanation: {
    fontSize: 24,
    fontWeight: "400",
    color: "#ffffff",
    textAlign: "center",
    lineHeight: 34,
  },
  authButtonsContainer: {
    width: "100%",
    maxWidth: 320,
    gap: 14,
  },
  authButton: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: 18,
    paddingHorizontal: 28,
    borderRadius: 14,
    width: "100%",
    gap: 14,
    minHeight: 56,
  },
  buttonLoading: {
    opacity: 0.7,
  },
  appleButton: {
    backgroundColor: "#ffffff",
  },
  appleButtonText: {
    fontSize: 16,
    fontWeight: "500",
    color: "#000000",
  },
  googleButton: {
    backgroundColor: "#18191d",
    borderWidth: 1,
    borderColor: "#27272a",
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
    backgroundColor: "#ffffff",
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
    color: "#f4f4f5",
  },
  emailButton: {
    backgroundColor: "transparent",
    borderWidth: 1,
    borderColor: "#27272a",
  },
  emailButtonText: {
    fontSize: 16,
    fontWeight: "500",
    color: "#a1a1aa",
  },
  emailInput: {
    backgroundColor: "#18191d",
    borderWidth: 1,
    borderColor: "#27272a",
    borderRadius: 14,
    paddingVertical: 18,
    paddingHorizontal: 18,
    fontSize: 16,
    color: "#f4f4f5",
    width: "100%",
    maxWidth: 320,
    marginBottom: 20,
    minHeight: 56,
  },
  primaryButton: {
    backgroundColor: "#6366f1",
    paddingVertical: 18,
    paddingHorizontal: 28,
    borderRadius: 14,
    width: "100%",
    maxWidth: 320,
    alignItems: "center",
    justifyContent: "center",
    minHeight: 56,
  },
  primaryButtonText: {
    fontSize: 16,
    fontWeight: "500",
    color: "#ffffff",
  },
  secondaryButton: {
    paddingVertical: 14,
    paddingHorizontal: 24,
    minHeight: 48,
  },
  secondaryButtonText: {
    fontSize: 14,
    color: "#6366f1",
  },
  privacyNote: {
    marginTop: 32,
    fontSize: 13,
    color: "#52525b",
    textAlign: "center",
  },
});
