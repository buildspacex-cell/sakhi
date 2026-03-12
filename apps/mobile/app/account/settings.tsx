import React, { useMemo, useState, useEffect } from "react";
import {
  SafeAreaView,
  StatusBar,
  StyleSheet,
  Text,
  View,
  Pressable,
  ScrollView,
  Switch,
  Platform,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useRouter } from "expo-router";

import { useAuth } from "../../lib/auth/AuthContext";
import { isAnalyticsOptedOut, optInAnalytics, optOutAnalytics } from "../../lib/analytics/client";

const palette = {
  bg: "#070b14",
  fg: "#f6f7fb",
  muted: "#a4adbc",
  subtle: "#7d8899",
  border: "rgba(228, 236, 250, 0.14)",
  cardBg: "rgba(21, 28, 40, 0.74)",
  accent: "#349ba9",
  danger: "#f0b8c0",
};

function formatMaskedId(personId: string): string {
  const raw = String(personId || "").trim();
  if (!raw) return "Not linked yet";
  if (raw.length <= 12) return raw;
  return `${raw.slice(0, 8)}...${raw.slice(-4)}`;
}

export default function SettingsScreen() {
  const router = useRouter();
  const { user, signOut } = useAuth();

  const [pushEnabled, setPushEnabled] = useState(true);
  const [hapticsEnabled, setHapticsEnabled] = useState(true);
  const [compactMode, setCompactMode] = useState(false);
  const [analyticsEnabled, setAnalyticsEnabled] = useState(!isAnalyticsOptedOut());

  useEffect(() => {
    if (analyticsEnabled) {
      optInAnalytics();
    } else {
      optOutAnalytics();
    }
  }, [analyticsEnabled]);

  const maskedPersonId = useMemo(
    () => formatMaskedId(user?.personId || ""),
    [user?.personId],
  );

  const handleSignOut = async () => {
    await signOut();
    router.replace("/" as never);
  };

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" />
      <View pointerEvents="none" style={styles.auroraA} />

      <View style={styles.header}>
        <Pressable style={styles.iconButton} onPress={() => router.back()}>
          <Ionicons name="chevron-back" size={20} color={palette.fg} />
        </Pressable>
        <View style={styles.headerTextWrap}>
          <Text style={styles.kicker}>Account</Text>
          <Text style={styles.title}>Settings</Text>
        </View>
      </View>

      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>App</Text>
          <Text style={styles.sectionHint}>Local device settings for your Sakhi experience.</Text>

          <View style={styles.row}>
            <View style={styles.rowCopy}>
              <Text style={styles.rowTitle}>Push notifications</Text>
              <Text style={styles.rowSubtitle}>Daily reminders and response follow-ups</Text>
            </View>
            <Switch
              value={pushEnabled}
              onValueChange={setPushEnabled}
              trackColor={{ false: "#3b4558", true: "rgba(52, 155, 169, 0.4)" }}
              thumbColor={pushEnabled ? palette.accent : "#c2cad6"}
              ios_backgroundColor="#3b4558"
            />
          </View>

          <View style={styles.row}>
            <View style={styles.rowCopy}>
              <Text style={styles.rowTitle}>Haptics</Text>
              <Text style={styles.rowSubtitle}>Subtle touch feedback while using chat</Text>
            </View>
            <Switch
              value={hapticsEnabled}
              onValueChange={setHapticsEnabled}
              trackColor={{ false: "#3b4558", true: "rgba(52, 155, 169, 0.4)" }}
              thumbColor={hapticsEnabled ? palette.accent : "#c2cad6"}
              ios_backgroundColor="#3b4558"
            />
          </View>

          <View style={styles.row}>
            <View style={styles.rowCopy}>
              <Text style={styles.rowTitle}>Compact chat bubbles</Text>
              <Text style={styles.rowSubtitle}>Show tighter spacing in conversation view</Text>
            </View>
            <Switch
              value={compactMode}
              onValueChange={setCompactMode}
              trackColor={{ false: "#3b4558", true: "rgba(52, 155, 169, 0.4)" }}
              thumbColor={compactMode ? palette.accent : "#c2cad6"}
              ios_backgroundColor="#3b4558"
            />
          </View>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Privacy & Data</Text>
          <Text style={styles.sectionHint}>
            Support access stays off by default and only includes what you explicitly allow.
          </Text>
          <View style={styles.row}>
            <View style={styles.rowCopy}>
              <Text style={styles.rowTitle}>Share anonymous usage data</Text>
              <Text style={styles.rowSubtitle}>Helps improve Sakhi — no message content, ever</Text>
            </View>
            <Switch
              value={analyticsEnabled}
              onValueChange={setAnalyticsEnabled}
              trackColor={{ false: "#3b4558", true: "rgba(52, 155, 169, 0.4)" }}
              thumbColor={analyticsEnabled ? palette.accent : "#c2cad6"}
              ios_backgroundColor="#3b4558"
            />
          </View>
          <View style={styles.infoCard}>
            <Text style={styles.infoText}>Use "Report an issue" to send the team a bug report.</Text>
            <Text style={styles.infoText}>Journal content is never included. You can revoke access anytime.</Text>
          </View>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Account</Text>
          <View style={styles.infoCard}>
            <Text style={styles.identityLine}>Email: {user?.email || "Not available"}</Text>
            <Text style={styles.identityLine}>Profile ID: {maskedPersonId}</Text>
          </View>
          <Pressable style={styles.signOutButton} onPress={handleSignOut}>
            <Ionicons name="log-out-outline" size={16} color={palette.danger} />
            <Text style={styles.signOutButtonText}>Sign out</Text>
          </Pressable>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: palette.bg,
  },
  auroraA: {
    position: "absolute",
    top: -120,
    right: -100,
    width: 250,
    height: 250,
    borderRadius: 140,
    backgroundColor: "rgba(89, 214, 226, 0.14)",
  },
  header: {
    paddingHorizontal: 18,
    paddingTop: Platform.OS === "android" ? 16 : 12,
    paddingBottom: 10,
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    borderBottomWidth: 1,
    borderBottomColor: palette.border,
  },
  iconButton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: palette.border,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "rgba(255,255,255,0.06)",
  },
  headerTextWrap: {
    gap: 2,
  },
  kicker: {
    color: palette.muted,
    fontSize: 11,
    textTransform: "uppercase",
    letterSpacing: 1.2,
  },
  title: {
    color: palette.fg,
    fontSize: 22,
    fontWeight: "600",
  },
  scroll: {
    flex: 1,
  },
  scrollContent: {
    paddingHorizontal: 16,
    paddingTop: 14,
    paddingBottom: 34,
    gap: 14,
  },
  section: {
    borderRadius: 20,
    borderWidth: 1,
    borderColor: palette.border,
    backgroundColor: palette.cardBg,
    paddingHorizontal: 14,
    paddingVertical: 14,
    gap: 10,
  },
  sectionTitle: {
    color: palette.fg,
    fontSize: 19,
    fontWeight: "600",
  },
  sectionHint: {
    color: palette.muted,
    fontSize: 13,
    lineHeight: 18,
  },
  row: {
    borderRadius: 14,
    borderWidth: 1,
    borderColor: "rgba(176, 196, 228, 0.2)",
    backgroundColor: "rgba(22, 34, 52, 0.74)",
    paddingHorizontal: 12,
    paddingVertical: 10,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 12,
  },
  rowCopy: {
    flex: 1,
    gap: 3,
  },
  rowTitle: {
    color: palette.fg,
    fontSize: 15,
    fontWeight: "500",
  },
  rowSubtitle: {
    color: palette.subtle,
    fontSize: 12,
    lineHeight: 16,
  },
  infoCard: {
    borderRadius: 14,
    borderWidth: 1,
    borderColor: "rgba(176, 196, 228, 0.2)",
    backgroundColor: "rgba(18, 28, 43, 0.72)",
    paddingHorizontal: 12,
    paddingVertical: 11,
    gap: 7,
  },
  infoText: {
    color: palette.muted,
    fontSize: 13,
    lineHeight: 18,
  },
  identityLine: {
    color: palette.fg,
    fontSize: 13,
    lineHeight: 19,
  },
  signOutButton: {
    marginTop: 2,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: "rgba(239, 111, 126, 0.35)",
    backgroundColor: "rgba(88, 33, 44, 0.35)",
    minHeight: 46,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
  },
  signOutButtonText: {
    color: palette.danger,
    fontSize: 15,
    fontWeight: "600",
  },
});

