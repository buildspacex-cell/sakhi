import React, { useEffect } from "react";
import {
  View,
  Text,
  Pressable,
  StyleSheet,
  SafeAreaView,
  StatusBar,
  ActivityIndicator,
} from "react-native";
import { useRouter } from "expo-router";
import { useAuth } from "../lib/auth/AuthContext";

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
      <SafeAreaView style={styles.container}>
        <StatusBar barStyle="light-content" />
        <View style={styles.content}>
          <ActivityIndicator size="large" color="#6366f1" />
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" />

      <View style={styles.content}>
        {/* Centered text */}
        <View style={styles.textContainer}>
          <Text style={styles.headline}>
            This is a quiet space to unload your mind.
          </Text>
          <Text style={styles.subheadline}>
            You can talk, or hand something off.
          </Text>
        </View>

        {/* BEGIN button */}
        <Pressable
          style={styles.beginButton}
          onPress={() => router.push("/auth" as never)}
        >
          <Text style={styles.beginText}>BEGIN</Text>
        </Pressable>
      </View>
    </SafeAreaView>
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
  content: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    paddingHorizontal: 40,
  },
  textContainer: {
    alignItems: "center",
    marginBottom: 56,
  },
  headline: {
    fontSize: 24,
    fontWeight: "400",
    color: "#ffffff",
    textAlign: "center",
    lineHeight: 34,
    marginBottom: 20,
  },
  subheadline: {
    fontSize: 16,
    fontWeight: "400",
    color: "#71717a",
    textAlign: "center",
    lineHeight: 24,
  },
  beginButton: {
    paddingVertical: 16,
    paddingHorizontal: 32,
    marginBottom: 32,
    minHeight: 48,
    justifyContent: "center",
  },
  beginText: {
    fontSize: 14,
    fontWeight: "500",
    color: "#71717a",
    letterSpacing: 2,
  },
});
