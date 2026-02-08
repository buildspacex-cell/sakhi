// =============================================================================
// HealthKit Connect — Onboarding step after prakriti assessment
// =============================================================================
// Asks the user to connect Apple Health. Fully optional — app works without it.

import React, { useState } from "react";
import {
  View,
  Text,
  Pressable,
  StyleSheet,
  SafeAreaView,
  StatusBar,
  Platform,
  ActivityIndicator,
} from "react-native";
import { useRouter, useLocalSearchParams } from "expo-router";
import { useHealthKit } from "../../hooks/useHealthKit";

export default function HealthConnectScreen() {
  const router = useRouter();
  const params = useLocalSearchParams();
  const personId = params.personId as string | undefined;
  const { available, connect, syncing } = useHealthKit(personId);
  const [connecting, setConnecting] = useState(false);
  const [connected, setConnected] = useState(false);

  const handleConnect = async () => {
    setConnecting(true);
    const granted = await connect();
    setConnecting(false);
    if (granted) {
      setConnected(true);
      // Brief pause to show success, then navigate
      setTimeout(() => router.replace("/voice" as never), 1200);
    }
  };

  const handleSkip = () => {
    router.replace("/voice" as never);
  };

  // Non-iOS or no HealthKit: skip this screen
  if (Platform.OS !== "ios" || !available) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.center}>
          <ActivityIndicator size="small" color="#6366f1" />
        </View>
        {/* Auto-skip after brief render */}
        <AutoSkip onSkip={handleSkip} />
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" />

      <View style={styles.content}>
        {/* Icon */}
        <Text style={styles.icon}>♡</Text>

        {/* Title */}
        <Text style={styles.title}>Connect Apple Health</Text>

        {/* Description */}
        <Text style={styles.description}>
          Sakhi can read your sleep, heart rate, and activity data to give you
          deeper, more personalized wellness guidance.
        </Text>

        {/* What we read */}
        <View style={styles.card}>
          <Text style={styles.cardTitle}>What Sakhi reads</Text>
          <DataRow label="Sleep" detail="Duration, quality, stages" />
          <DataRow label="Heart Rate" detail="Resting HR, HRV" />
          <DataRow label="Activity" detail="Steps, active energy" />
          <DataRow label="Mindfulness" detail="Meditation sessions" />
        </View>

        {/* Privacy note */}
        <Text style={styles.privacy}>
          Your health data is processed on-device and used only for your
          personalized insights. It is never sold or shared.
        </Text>
      </View>

      {/* Footer */}
      <View style={styles.footer}>
        {connected ? (
          <View style={styles.successButton}>
            <Text style={styles.successText}>Connected</Text>
          </View>
        ) : (
          <Pressable
            style={[styles.connectButton, (connecting || syncing) && styles.buttonDisabled]}
            onPress={handleConnect}
            disabled={connecting || syncing}
          >
            {connecting || syncing ? (
              <ActivityIndicator size="small" color="#fff" />
            ) : (
              <Text style={styles.connectButtonText}>Connect Apple Health</Text>
            )}
          </Pressable>
        )}

        <Pressable style={styles.skipButton} onPress={handleSkip}>
          <Text style={styles.skipButtonText}>Skip for now</Text>
        </Pressable>
      </View>
    </SafeAreaView>
  );
}

// Helper: auto-skip for non-iOS
function AutoSkip({ onSkip }: { onSkip: () => void }) {
  React.useEffect(() => {
    const t = setTimeout(onSkip, 100);
    return () => clearTimeout(t);
  }, [onSkip]);
  return null;
}

function DataRow({ label, detail }: { label: string; detail: string }) {
  return (
    <View style={styles.dataRow}>
      <Text style={styles.dataLabel}>{label}</Text>
      <Text style={styles.dataDetail}>{detail}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#0a0a0a",
  },
  center: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  content: {
    flex: 1,
    padding: 24,
    paddingTop: 60,
    alignItems: "center",
  },
  icon: {
    fontSize: 48,
    marginBottom: 24,
  },
  title: {
    fontSize: 28,
    fontWeight: "600",
    color: "#f4f4f5",
    textAlign: "center",
    marginBottom: 16,
    letterSpacing: -0.5,
  },
  description: {
    fontSize: 16,
    color: "#a1a1aa",
    textAlign: "center",
    lineHeight: 24,
    marginBottom: 32,
    paddingHorizontal: 16,
  },
  card: {
    width: "100%",
    backgroundColor: "#18191d",
    borderRadius: 16,
    padding: 20,
    marginBottom: 24,
  },
  cardTitle: {
    fontSize: 13,
    fontWeight: "600",
    color: "#71717a",
    letterSpacing: 1,
    textTransform: "uppercase",
    marginBottom: 16,
  },
  dataRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingVertical: 10,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: "#27272a",
  },
  dataLabel: {
    fontSize: 14,
    fontWeight: "500",
    color: "#f4f4f5",
  },
  dataDetail: {
    fontSize: 14,
    color: "#71717a",
  },
  privacy: {
    fontSize: 12,
    color: "#52525b",
    textAlign: "center",
    lineHeight: 18,
    paddingHorizontal: 24,
  },
  footer: {
    padding: 20,
    paddingBottom: 40,
    gap: 12,
  },
  connectButton: {
    backgroundColor: "#6366f1",
    paddingVertical: 18,
    borderRadius: 14,
    alignItems: "center",
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  connectButtonText: {
    fontSize: 16,
    fontWeight: "600",
    color: "#fff",
  },
  successButton: {
    backgroundColor: "#22c55e",
    paddingVertical: 18,
    borderRadius: 14,
    alignItems: "center",
  },
  successText: {
    fontSize: 16,
    fontWeight: "600",
    color: "#fff",
  },
  skipButton: {
    paddingVertical: 12,
    alignItems: "center",
  },
  skipButtonText: {
    fontSize: 14,
    color: "#71717a",
  },
});
