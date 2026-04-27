import React from "react";
import {
  View,
  Text,
  Pressable,
  ScrollView,
  StyleSheet,
  SafeAreaView,
  StatusBar,
  Alert,
} from "react-native";
import { useRouter } from "expo-router";
import { theme } from "../../../lib/theme/tokens";

const palette = {
  bg: theme.colors.bg,
  bgElevated: theme.colors.bgElevated,
  fg: theme.colors.text,
  muted: theme.colors.textMuted,
  border: theme.colors.border,
  surfaceMuted: theme.colors.surfaceMuted,
  accent: theme.colors.accent,
  accentText: theme.colors.accentText,
  accentInk: theme.colors.accentInk,
  accentBorder: theme.colors.accentBorder,
  accentSoft: theme.colors.accentSoft,
};

const FEATURES = [
  {
    label: "Morning Review",
    description: "Start every day knowing exactly what's unresolved and what shifted.",
  },
  {
    label: "What Changed",
    description: "See when your optimization target has quietly drifted — before it costs you.",
  },
  {
    label: "Open Loops Ledger",
    description: "Every decision and commitment you've made, tracked and surfaced automatically.",
  },
  {
    label: "One Thing to Confront",
    description: "Every morning, Sakhi tells you the single most overdue thing to face today.",
  },
];

export default function UpgradeScreen() {
  const router = useRouter();

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" />
      <View style={styles.header}>
        <Pressable onPress={() => router.back()} hitSlop={12}>
          <Text style={styles.backButton}>← Back</Text>
        </Pressable>
        <Text style={styles.brand}>Sakhi</Text>
      </View>

      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.hero}>
          <Text style={styles.eyebrow}>Sakhi Pro</Text>
          <Text style={styles.headline}>
            {"Your open decisions.\nYour thinking shifts.\nYours to keep."}
          </Text>
          <Text style={styles.subheadline}>
            Sakhi tracks what stays unresolved across every conversation and shows
            you what changed before you act. That's Active Context — and it's
            what separates good decisions from ones you regret.
          </Text>
        </View>

        <View style={styles.featureList}>
          {FEATURES.map((f) => (
            <View key={f.label} style={styles.featureItem}>
              <Text style={styles.featureLabel}>{f.label}</Text>
              <Text style={styles.featureDesc}>{f.description}</Text>
            </View>
          ))}
        </View>

        <View style={styles.ctaBlock}>
          <Text style={styles.pricingAmount}>$12 / month</Text>
          <Text style={styles.pricingDetail}>Cancel anytime. No data locked in.</Text>
          <Pressable
            style={styles.ctaButton}
            onPress={() => Alert.alert("Coming soon", "Payment will be available shortly. We'll notify you when it's ready.")}
          >
            <Text style={styles.ctaButtonText}>Upgrade to Pro</Text>
          </Pressable>
          <Pressable onPress={() => router.push("/experience/converse" as never)}>
            <Text style={styles.continueFreeLink}>Continue with free chat →</Text>
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
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: 20,
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderBottomColor: palette.border,
  },
  backButton: {
    fontSize: 14,
    color: palette.muted,
  },
  brand: {
    fontSize: 12,
    letterSpacing: 2,
    textTransform: "uppercase",
    color: palette.muted,
  },
  scroll: {
    flex: 1,
  },
  scrollContent: {
    padding: 24,
    gap: 36,
    paddingBottom: 56,
  },
  hero: {
    gap: 14,
  },
  eyebrow: {
    fontSize: 12,
    textTransform: "uppercase",
    letterSpacing: 1.4,
    color: palette.accentText,
    fontWeight: "600",
  },
  headline: {
    fontSize: 34,
    lineHeight: 40,
    fontWeight: "600",
    letterSpacing: -0.5,
    color: palette.fg,
  },
  subheadline: {
    fontSize: 15,
    lineHeight: 23,
    color: palette.muted,
  },
  featureList: {
    gap: 12,
  },
  featureItem: {
    borderRadius: 12,
    borderWidth: 1,
    borderColor: palette.border,
    backgroundColor: palette.surfaceMuted,
    padding: 14,
    gap: 4,
  },
  featureLabel: {
    fontSize: 15,
    fontWeight: "600",
    color: palette.fg,
  },
  featureDesc: {
    fontSize: 14,
    lineHeight: 20,
    color: palette.muted,
  },
  ctaBlock: {
    alignItems: "center",
    gap: 12,
  },
  pricingAmount: {
    fontSize: 28,
    fontWeight: "600",
    letterSpacing: -0.3,
    color: palette.fg,
  },
  pricingDetail: {
    fontSize: 13,
    color: palette.muted,
  },
  ctaButton: {
    width: "100%",
    height: 56,
    borderRadius: 999,
    backgroundColor: palette.accent,
    alignItems: "center",
    justifyContent: "center",
    marginTop: 4,
  },
  ctaButtonText: {
    fontSize: 17,
    fontWeight: "700",
    color: palette.accentInk,
  },
  continueFreeLink: {
    fontSize: 14,
    color: palette.muted,
  },
});
