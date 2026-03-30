import React, { useMemo, useState, useEffect } from "react";
import {
  StyleSheet,
  Text,
  View,
  ScrollView,
  Switch,
  Platform,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useRouter } from "expo-router";

import { useAuth } from "../../lib/auth/AuthContext";
import { isAnalyticsOptedOut, optInAnalytics, optOutAnalytics } from "../../lib/analytics/client";
import { useAppPreferences } from "../../lib/preferences/AppPreferencesContext";
import { theme } from "../../lib/theme/tokens";
import { IconButton } from "../../components/ui/IconButton";
import { Card } from "../../components/ui/Card";
import { Button } from "../../components/ui/Button";
import { Screen } from "../../components/ui/Screen";

function formatMaskedId(personId: string): string {
  const raw = String(personId || "").trim();
  if (!raw) return "Not linked yet";
  if (raw.length <= 12) return raw;
  return `${raw.slice(0, 8)}...${raw.slice(-4)}`;
}

export default function SettingsScreen() {
  const router = useRouter();
  const { user, signOut } = useAuth();
  const {
    preferences,
    setPushEnabled,
    setHapticsEnabled,
    setCompactMode,
  } = useAppPreferences();

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

  const [isSigningOut, setIsSigningOut] = useState(false);
  const handleSignOut = async () => {
    if (isSigningOut) return;
    setIsSigningOut(true);
    try {
      await signOut();
    } finally {
      setIsSigningOut(false);
    }
  };

  return (
    <Screen>
      <View style={styles.header}>
        <IconButton
          icon={<Ionicons name="chevron-back" size={20} color={theme.colors.text} />}
          onPress={() => router.back()}
        />
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
        <Card style={styles.section}>
          <Text style={styles.sectionTitle}>App</Text>
          <Text style={styles.sectionHint}>Local device settings for your Sakhi experience.</Text>

          <View style={styles.row}>
            <View style={styles.rowCopy}>
              <Text style={styles.rowTitle}>Push notifications</Text>
              <Text style={styles.rowSubtitle}>Daily reminders and response follow-ups</Text>
            </View>
            <Switch
              value={preferences.pushEnabled}
              onValueChange={setPushEnabled}
              trackColor={{ false: "#3b4558", true: theme.colors.accentSoft }}
              thumbColor={preferences.pushEnabled ? theme.colors.accent : "#c2cad6"}
              ios_backgroundColor="#3b4558"
            />
          </View>

          <View style={styles.row}>
            <View style={styles.rowCopy}>
              <Text style={styles.rowTitle}>Haptics</Text>
              <Text style={styles.rowSubtitle}>Subtle touch feedback while using chat</Text>
            </View>
            <Switch
              value={preferences.hapticsEnabled}
              onValueChange={setHapticsEnabled}
              trackColor={{ false: "#3b4558", true: theme.colors.accentSoft }}
              thumbColor={preferences.hapticsEnabled ? theme.colors.accent : "#c2cad6"}
              ios_backgroundColor="#3b4558"
            />
          </View>

          <View style={styles.row}>
            <View style={styles.rowCopy}>
              <Text style={styles.rowTitle}>Compact chat bubbles</Text>
              <Text style={styles.rowSubtitle}>Show tighter spacing in conversation view</Text>
            </View>
            <Switch
              value={preferences.compactMode}
              onValueChange={setCompactMode}
              trackColor={{ false: "#3b4558", true: theme.colors.accentSoft }}
              thumbColor={preferences.compactMode ? theme.colors.accent : "#c2cad6"}
              ios_backgroundColor="#3b4558"
            />
          </View>
        </Card>

        <Card style={styles.section}>
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
              trackColor={{ false: "#3b4558", true: theme.colors.accentSoft }}
              thumbColor={analyticsEnabled ? theme.colors.accent : "#c2cad6"}
              ios_backgroundColor="#3b4558"
            />
          </View>
          <Card style={styles.infoCard} variant="muted">
            <Text style={styles.infoText}>Use "Report an issue" to send the team a bug report.</Text>
            <Text style={styles.infoText}>Journal content is never included. You can revoke access anytime.</Text>
          </Card>
        </Card>

        <Card style={styles.section}>
          <Text style={styles.sectionTitle}>Account</Text>
          <Card style={styles.infoCard} variant="muted">
            <Text style={styles.identityLine}>Email: {user?.email || "Not available"}</Text>
            <Text style={styles.identityLine}>Profile ID: {maskedPersonId}</Text>
          </Card>
          <Button
            label="Sign out"
            variant="danger"
            onPress={() => void handleSignOut()}
            busy={isSigningOut}
            disabled={isSigningOut}
            leftIcon={<Ionicons name="log-out-outline" size={16} color={theme.colors.danger} />}
          />
        </Card>
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: {
    paddingHorizontal: theme.spacing.lg + 2,
    paddingTop: Platform.OS === "android" ? 16 : 12,
    paddingBottom: theme.spacing.sm,
    flexDirection: "row",
    alignItems: "center",
    gap: theme.spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: theme.colors.border,
  },
  headerTextWrap: {
    gap: 2,
  },
  kicker: {
    color: theme.colors.textMuted,
    fontSize: theme.typography.kicker.fontSize,
    textTransform: "uppercase",
    letterSpacing: theme.typography.kicker.letterSpacing,
  },
  title: {
    color: theme.colors.text,
    fontSize: 22,
    fontWeight: "600",
  },
  scroll: {
    flex: 1,
  },
  scrollContent: {
    paddingHorizontal: theme.spacing.lg,
    paddingTop: theme.spacing.md + 2,
    paddingBottom: theme.spacing["4xl"] + 2,
    gap: theme.spacing.md + 2,
  },
  section: {
    gap: 10,
  },
  sectionTitle: {
    color: theme.colors.text,
    fontSize: 19,
    fontWeight: "600",
  },
  sectionHint: {
    color: theme.colors.textMuted,
    fontSize: 13,
    lineHeight: 18,
  },
  row: {
    borderRadius: theme.radii.sm + 2,
    borderWidth: 1,
    borderColor: theme.colors.borderStrong,
    backgroundColor: theme.colors.surfaceMuted,
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
    color: theme.colors.text,
    fontSize: 15,
    fontWeight: "500",
  },
  rowSubtitle: {
    color: theme.colors.textSubtle,
    fontSize: 12,
    lineHeight: 16,
  },
  infoCard: {
    gap: 7,
    paddingHorizontal: 12,
    paddingVertical: 11,
    ...theme.shadow.soft,
  },
  infoText: {
    color: theme.colors.textMuted,
    fontSize: 13,
    lineHeight: 18,
  },
  identityLine: {
    color: theme.colors.text,
    fontSize: 13,
    lineHeight: 19,
  },
});
