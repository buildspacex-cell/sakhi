import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  View,
  Text,
  Pressable,
  ScrollView,
  StyleSheet,
  SafeAreaView,
  StatusBar,
  ActivityIndicator,
} from "react-native";
import { useRouter } from "expo-router";
import { useAuth } from "../../../lib/auth/AuthContext";
import { config } from "../../../lib/config";
import { theme } from "../../../lib/theme/tokens";

const BACKEND_URL = (config.backendUrl || "").replace(/\/+$/, "");

interface OpenLoop {
  id: string;
  loop_type: string;
  topic: string;
  first_raised_at?: string;
}

interface WhatChanged {
  from: string;
  to: string;
  confidence: number;
  topic_key?: string;
}

interface MorningReview {
  date: string;
  time_of_day: "morning" | "afternoon" | "evening";
  what_changed: WhatChanged | null;
  one_thing: (OpenLoop & { days_open: number }) | null;
  think: OpenLoop[];
  act: OpenLoop[];
  total_open: number;
}

const palette = {
  bg: theme.colors.bg,
  bgElevated: theme.colors.bgElevated,
  fg: theme.colors.text,
  muted: theme.colors.textMuted,
  border: theme.colors.border,
  surfaceStrong: theme.colors.surfaceStrong,
  surfaceMuted: theme.colors.surfaceMuted,
  accent: theme.colors.accent,
  accentText: theme.colors.accentText,
  accentInk: theme.colors.accentInk,
  accentBorder: theme.colors.accentBorder,
  accentSoft: theme.colors.accentSoft,
  danger: theme.colors.danger,
};

export default function ReviewScreen() {
  const router = useRouter();
  const { user, session } = useAuth();
  const personId = user?.personId || "";
  const authToken = session?.access_token || "";

  const [review, setReview] = useState<MorningReview | null>(null);
  const [loading, setLoading] = useState(true);
  const [dismissedIds, setDismissedIds] = useState<Set<string>>(new Set());
  const [showUpgradeCta, setShowUpgradeCta] = useState(false);
  const paywallCheckedRef = useRef(false);

  useEffect(() => {
    if (!personId || !BACKEND_URL) {
      setLoading(false);
      return;
    }
    const fetchReview = async () => {
      try {
        const res = await fetch(
          `${BACKEND_URL}/continuity/morning-review?person_id=${encodeURIComponent(personId)}`,
          { headers: authToken ? { Authorization: `Bearer ${authToken}` } : undefined },
        );
        if (res.ok) {
          const data = (await res.json()) as MorningReview;
          setReview(data);
        }
      } catch {
        // best-effort
      } finally {
        setLoading(false);
      }
    };
    void fetchReview();
  }, [authToken, personId]);

  useEffect(() => {
    if (!personId || !BACKEND_URL || paywallCheckedRef.current) return;
    paywallCheckedRef.current = true;
    const checkPaywall = async () => {
      try {
        const res = await fetch(
          `${BACKEND_URL}/continuity/paywall-status?person_id=${encodeURIComponent(personId)}`,
          { headers: authToken ? { Authorization: `Bearer ${authToken}` } : undefined },
        );
        if (res.ok) {
          const data = await res.json();
          setShowUpgradeCta(Boolean(data.show_upgrade_cta));
        }
      } catch {
        // best-effort
      }
    };
    void checkPaywall();
  }, [authToken, personId]);

  const handleDismiss = useCallback((loopId: string) => {
    setDismissedIds((prev) => new Set(Array.from(prev).concat(loopId)));
    if (BACKEND_URL) {
      void fetch(`${BACKEND_URL}/continuity/open-loops/${loopId}/resolve`, {
        method: "POST",
        headers: authToken ? { Authorization: `Bearer ${authToken}` } : undefined,
      });
    }
  }, [authToken]);

  const greetingWord = (() => {
    const tod = review?.time_of_day;
    if (tod === "morning") return "Good morning";
    if (tod === "afternoon") return "Good afternoon";
    return "Good evening";
  })();

  const formattedDate = review?.date
    ? new Date(review.date + "T00:00:00").toLocaleDateString("en-US", {
        weekday: "long",
        month: "long",
        day: "numeric",
      })
    : "";

  const visibleThink = review?.think.filter((l) => !dismissedIds.has(l.id)) ?? [];
  const visibleAct = review?.act.filter((l) => !dismissedIds.has(l.id)) ?? [];
  const hasContent =
    review?.what_changed ||
    (review?.one_thing && !dismissedIds.has(review.one_thing.id)) ||
    visibleThink.length > 0 ||
    visibleAct.length > 0;

  if (loading) {
    return (
      <SafeAreaView style={styles.container}>
        <StatusBar barStyle="light-content" />
        <View style={styles.loadingState}>
          <ActivityIndicator color={palette.muted} />
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" />
      <View style={styles.header}>
        <View>
          <Text style={styles.dateLabel}>{formattedDate}</Text>
          <Text style={styles.greeting}>{greetingWord}</Text>
        </View>
        <Pressable
          style={styles.converseButton}
          onPress={() => router.push("/experience/converse" as never)}
        >
          <Text style={styles.converseButtonText}>Think →</Text>
        </Pressable>
      </View>

      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        {showUpgradeCta ? (
          <View style={styles.upgradeCard}>
            <Text style={styles.upgradeEyebrow}>Sakhi Pro</Text>
            <Text style={styles.upgradeHeadline}>Keep access to Morning Review</Text>
            <Text style={styles.upgradeBody}>
              Open decisions, stance shifts, and one thing to confront — free chat continues either way.
            </Text>
            <Pressable onPress={() => router.push("/experience/upgrade" as never)}>
              <Text style={styles.upgradeLink}>See upgrade options →</Text>
            </Pressable>
          </View>
        ) : null}

        {!hasContent ? (
          <View style={styles.emptyState}>
            <Text style={styles.emptyHeading}>Nothing open right now.</Text>
            <Text style={styles.emptyHint}>
              Open threads and decisions appear here as you talk with Sakhi.
            </Text>
          </View>
        ) : (
          <>
            {review?.what_changed ? (
              <View style={styles.section}>
                <Text style={styles.sectionLabel}>What changed</Text>
                <View style={styles.whatChangedCard}>
                  <Text style={styles.whatChangedLine}>
                    <Text style={styles.stanceFrom}>{review.what_changed.from}</Text>
                    <Text style={styles.stanceArrow}> → </Text>
                    <Text style={styles.stanceTo}>{review.what_changed.to}</Text>
                  </Text>
                  {review.what_changed.topic_key ? (
                    <Text style={styles.whatChangedTopic}>
                      on {review.what_changed.topic_key.replace(/_/g, " ")}
                    </Text>
                  ) : null}
                  <Text style={styles.whatChangedSubtext}>
                    Your optimization target has shifted. Notice it before you act.
                  </Text>
                </View>
              </View>
            ) : null}

            {review?.one_thing && !dismissedIds.has(review.one_thing.id) ? (
              <View style={styles.section}>
                <Text style={styles.sectionLabel}>One thing to confront today</Text>
                <View style={styles.oneThingCard}>
                  <Text style={styles.oneThingTopic}>{review.one_thing.topic}</Text>
                  {review.one_thing.days_open > 0 ? (
                    <Text style={styles.oneThingAge}>
                      Open for {review.one_thing.days_open} day{review.one_thing.days_open !== 1 ? "s" : ""}
                    </Text>
                  ) : null}
                  <View style={styles.oneThingActions}>
                    <Pressable onPress={() => router.push("/experience/converse" as never)}>
                      <Text style={styles.converseOnThis}>Think it through →</Text>
                    </Pressable>
                    <Pressable onPress={() => handleDismiss(review.one_thing!.id)}>
                      <Text style={styles.dismissLink}>Resolved</Text>
                    </Pressable>
                  </View>
                </View>
              </View>
            ) : null}

            {visibleThink.length > 0 ? (
              <View style={styles.section}>
                <Text style={styles.sectionLabel}>Think</Text>
                {visibleThink.map((loop) => (
                  <View key={loop.id} style={styles.loopItem}>
                    <Text style={styles.loopTopic}>{loop.topic}</Text>
                    <Pressable onPress={() => handleDismiss(loop.id)} hitSlop={10}>
                      <Text style={styles.loopCheck}>✓</Text>
                    </Pressable>
                  </View>
                ))}
              </View>
            ) : null}

            {visibleAct.length > 0 ? (
              <View style={styles.section}>
                <Text style={styles.sectionLabel}>Act</Text>
                {visibleAct.map((loop) => (
                  <View key={loop.id} style={styles.loopItem}>
                    <Text style={styles.loopTopic}>{loop.topic}</Text>
                    <Pressable onPress={() => handleDismiss(loop.id)} hitSlop={10}>
                      <Text style={styles.loopCheck}>✓</Text>
                    </Pressable>
                  </View>
                ))}
              </View>
            ) : null}
          </>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: palette.bg,
  },
  loadingState: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-end",
    paddingHorizontal: 22,
    paddingVertical: 20,
    borderBottomWidth: 1,
    borderBottomColor: palette.border,
  },
  dateLabel: {
    fontSize: 11,
    letterSpacing: 1.1,
    textTransform: "uppercase",
    color: palette.muted,
    marginBottom: 4,
  },
  greeting: {
    fontSize: 30,
    fontWeight: "600",
    letterSpacing: -0.5,
    color: palette.fg,
  },
  converseButton: {
    borderRadius: 999,
    borderWidth: 1,
    borderColor: palette.border,
    backgroundColor: palette.surfaceMuted,
    paddingVertical: 10,
    paddingHorizontal: 16,
  },
  converseButtonText: {
    fontSize: 14,
    fontWeight: "600",
    color: palette.fg,
  },
  scroll: {
    flex: 1,
  },
  scrollContent: {
    padding: 20,
    gap: 24,
    paddingBottom: 48,
  },
  emptyState: {
    marginTop: 48,
    alignItems: "center",
    gap: 10,
  },
  emptyHeading: {
    fontSize: 24,
    fontWeight: "500",
    letterSpacing: -0.3,
    color: palette.fg,
    textAlign: "center",
  },
  emptyHint: {
    fontSize: 15,
    lineHeight: 22,
    color: palette.muted,
    textAlign: "center",
    maxWidth: 320,
  },
  upgradeCard: {
    borderRadius: 14,
    borderWidth: 1,
    borderColor: palette.accentBorder,
    backgroundColor: palette.accentSoft,
    padding: 16,
    gap: 6,
  },
  upgradeEyebrow: {
    fontSize: 11,
    textTransform: "uppercase",
    letterSpacing: 1.1,
    color: palette.accentText,
    fontWeight: "600",
  },
  upgradeHeadline: {
    fontSize: 16,
    fontWeight: "600",
    color: palette.fg,
  },
  upgradeBody: {
    fontSize: 14,
    lineHeight: 20,
    color: palette.muted,
  },
  upgradeLink: {
    fontSize: 14,
    fontWeight: "600",
    color: palette.accentText,
    marginTop: 4,
  },
  section: {
    gap: 10,
  },
  sectionLabel: {
    fontSize: 11,
    textTransform: "uppercase",
    letterSpacing: 1.1,
    color: palette.muted,
    fontWeight: "600",
  },
  whatChangedCard: {
    borderRadius: 14,
    borderWidth: 1,
    borderColor: palette.accentBorder,
    backgroundColor: palette.accentSoft,
    padding: 16,
    gap: 6,
  },
  whatChangedLine: {
    fontSize: 22,
    fontWeight: "600",
    letterSpacing: -0.3,
  },
  stanceFrom: {
    color: palette.muted,
    textDecorationLine: "line-through",
  },
  stanceArrow: {
    color: palette.muted,
  },
  stanceTo: {
    color: palette.accentText,
  },
  whatChangedTopic: {
    fontSize: 13,
    color: palette.muted,
  },
  whatChangedSubtext: {
    fontSize: 14,
    lineHeight: 20,
    color: palette.fg,
    opacity: 0.8,
  },
  oneThingCard: {
    borderRadius: 14,
    borderWidth: 1,
    borderColor: palette.border,
    backgroundColor: palette.surfaceStrong,
    padding: 16,
    gap: 8,
  },
  oneThingTopic: {
    fontSize: 17,
    fontWeight: "500",
    lineHeight: 24,
    color: palette.fg,
  },
  oneThingAge: {
    fontSize: 12,
    color: palette.muted,
    letterSpacing: 0.3,
  },
  oneThingActions: {
    flexDirection: "row",
    gap: 16,
    alignItems: "center",
    marginTop: 4,
  },
  converseOnThis: {
    fontSize: 14,
    fontWeight: "600",
    color: palette.accent,
  },
  dismissLink: {
    fontSize: 13,
    color: palette.muted,
  },
  loopItem: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 10,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: palette.border,
    backgroundColor: palette.surfaceMuted,
    paddingVertical: 11,
    paddingHorizontal: 14,
  },
  loopTopic: {
    flex: 1,
    fontSize: 15,
    lineHeight: 21,
    color: palette.fg,
  },
  loopCheck: {
    fontSize: 15,
    color: palette.muted,
    paddingHorizontal: 4,
  },
});
