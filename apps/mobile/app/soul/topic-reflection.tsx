import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useRouter } from "expo-router";

import { useAuth } from "../../lib/auth/AuthContext";
import { config } from "../../lib/config";

interface ContinuityTopicSummary {
  anchor: string;
  label: string;
  confidence: number;
  selected_count: number;
  span_days: number;
  direction: string;
}

interface ContinuityMoment {
  source_ref?: string;
  ts?: string;
  short_snippet?: string;
  confidence?: number;
  facet?: string;
  stance?: string;
}

interface ContinuityArcResponse {
  label?: string;
  topic_confidence?: number;
  arc?: {
    phase_count?: number;
    features?: {
      direction?: string;
    };
  };
  included_moments?: ContinuityMoment[];
}

const BACKEND_URL = config.backendUrl || "https://sakhi-production-930f.up.railway.app";

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

function shortDate(input?: string): string {
  if (!input) return "";
  const parsed = new Date(input);
  if (Number.isNaN(parsed.getTime())) return "";
  return parsed.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export default function TopicReflectionScreen() {
  const router = useRouter();
  const { user, session } = useAuth();

  const personId = user?.personId || "";
  const authToken = session?.access_token || "";

  const [topics, setTopics] = useState<ContinuityTopicSummary[]>([]);
  const [selectedAnchor, setSelectedAnchor] = useState("");
  const [arc, setArc] = useState<ContinuityArcResponse | null>(null);
  const [loadingTopics, setLoadingTopics] = useState(false);
  const [loadingArc, setLoadingArc] = useState(false);
  const [error, setError] = useState("");

  const loadArc = useCallback(
    async (anchor: string) => {
      if (!personId || !anchor) return;
      setLoadingArc(true);
      try {
        const params = new URLSearchParams({
          person_id: personId,
          anchor,
          window: "3650d",
        });
        const res = await fetch(`${BACKEND_URL}/continuity/arc?${params.toString()}`, {
          cache: "no-store",
          headers: authToken ? { Authorization: `Bearer ${authToken}` } : undefined,
        });

        if (!res.ok) {
          throw new Error(`Arc fetch failed (${res.status})`);
        }

        const payload = (await res.json()) as ContinuityArcResponse;
        setArc(payload);
      } catch (err) {
        console.error("[topic-reflection] arc load error", err);
        setArc(null);
      } finally {
        setLoadingArc(false);
      }
    },
    [authToken, personId],
  );

  const ensureContinuityPolicyEnabled = useCallback(async (): Promise<boolean> => {
    if (!personId) return false;
    try {
      const res = await fetch(`${BACKEND_URL}/continuity/policy/enable`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
        },
        body: JSON.stringify({ person_id: personId }),
      });
      return res.ok;
    } catch {
      return false;
    }
  }, [authToken, personId]);

  const fetchTopics = useCallback(async (): Promise<ContinuityTopicSummary[]> => {
    const params = new URLSearchParams({ person_id: personId, window: "3650d" });
    const res = await fetch(`${BACKEND_URL}/continuity/topics?${params.toString()}`, {
      cache: "no-store",
      headers: authToken ? { Authorization: `Bearer ${authToken}` } : undefined,
    });
    if (!res.ok) {
      const error = new Error(`Topics fetch failed (${res.status})`) as Error & {
        status?: number;
      };
      error.status = res.status;
      throw error;
    }
    const payload = (await res.json()) as { topics?: ContinuityTopicSummary[] };
    return payload.topics || [];
  }, [authToken, personId]);

  const loadTopics = useCallback(async () => {
    if (!personId) return;

    setLoadingTopics(true);
    setError("");

    try {
      let topicItems: ContinuityTopicSummary[] = [];
      try {
        topicItems = await fetchTopics();
      } catch (err) {
        const status = Number((err as { status?: number })?.status || 0);
        if (status === 403) {
          const enabled = await ensureContinuityPolicyEnabled();
          if (enabled) {
            topicItems = await fetchTopics();
          } else {
            throw err;
          }
        } else {
          throw err;
        }
      }
      const sorted = [...topicItems].sort((a, b) => {
        if (b.selected_count !== a.selected_count) {
          return b.selected_count - a.selected_count;
        }
        return b.confidence - a.confidence;
      });

      setTopics(sorted);

      if (sorted.length > 0) {
        const initialAnchor = sorted[0].anchor;
        setSelectedAnchor(initialAnchor);
        await loadArc(initialAnchor);
      } else {
        setSelectedAnchor("");
        setArc(null);
      }
    } catch (err) {
      console.error("[topic-reflection] topics load error", err);
      setTopics([]);
      setSelectedAnchor("");
      setArc(null);
      setError("Could not load continuity topics yet. Try sending a few chat turns first.");
    } finally {
      setLoadingTopics(false);
    }
  }, [ensureContinuityPolicyEnabled, fetchTopics, loadArc, personId]);

  useEffect(() => {
    void loadTopics();
  }, [loadTopics]);

  const totalTopicWeight = useMemo(
    () => topics.reduce((sum, topic) => sum + Math.max(0, topic.selected_count), 0),
    [topics],
  );

  const topTopics = useMemo(() => topics.slice(0, 5), [topics]);
  const moments = arc?.included_moments || [];

  return (
    <SafeAreaView style={styles.container}>
      <View pointerEvents="none" style={styles.auroraA} />
      <View pointerEvents="none" style={styles.auroraB} />

      <View style={styles.header}>
        <Pressable style={styles.iconButton} onPress={() => router.back()}>
          <Ionicons name="chevron-back" size={18} color={palette.fg} />
        </Pressable>
        <View style={styles.headerTitleWrap}>
          <Text style={styles.kicker}>Profile</Text>
          <Text style={styles.title}>Topic Reflection</Text>
        </View>
        <Pressable style={styles.iconButton} onPress={() => void loadTopics()}>
          <Ionicons name="refresh-outline" size={18} color={palette.fg} />
        </Pressable>
      </View>

      <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        <View style={styles.glassCard}>
          <Text style={styles.cardTitle}>Life Occupancy</Text>
          <Text style={styles.cardSubtitle}>
            Bubble size reflects how much each thread has occupied your attention.
          </Text>

          {loadingTopics ? (
            <View style={styles.loadingRow}>
              <ActivityIndicator size="small" color={palette.muted} />
            </View>
          ) : topics.length === 0 ? (
            <Text style={styles.emptyText}>
              No topic arcs yet. Add more conversation turns and return here.
            </Text>
          ) : (
            <View style={styles.topicCloud}>
              {topics.map((topic, index) => {
                const weight = totalTopicWeight > 0 ? topic.selected_count / totalTopicWeight : 0;
                const diameter = Math.round(clamp(88 + weight * 180 + topic.confidence * 16, 92, 196));
                const isActive = topic.anchor === selectedAnchor;

                return (
                  <Pressable
                    key={`${topic.anchor}-${index}`}
                    onPress={() => {
                      setSelectedAnchor(topic.anchor);
                      void loadArc(topic.anchor);
                    }}
                    style={[
                      styles.topicBubble,
                      isActive && styles.topicBubbleActive,
                      {
                        width: diameter,
                        height: diameter,
                        backgroundColor: isActive
                          ? "rgba(203, 233, 255, 0.25)"
                          : `rgba(255, 255, 255, ${0.07 + weight * 0.18})`,
                      },
                    ]}
                  >
                    <Text style={styles.topicLabel}>{topic.label || topic.anchor}</Text>
                    <Text style={styles.topicShare}>{Math.max(1, Math.round(weight * 100))}%</Text>
                    <Text style={styles.topicCount}>{topic.selected_count} moments</Text>
                  </Pressable>
                );
              })}
            </View>
          )}
        </View>

        {topTopics.length > 0 && (
          <View style={styles.glassCard}>
            <Text style={styles.cardTitle}>What Is Occupying You Most</Text>
            <View style={styles.occupancyList}>
              {topTopics.map((topic, index) => {
                const percent = totalTopicWeight > 0
                  ? Math.round((topic.selected_count / totalTopicWeight) * 100)
                  : 0;
                return (
                  <View key={`${topic.anchor}-row-${index}`} style={styles.occupancyRow}>
                    <View style={styles.occupancyHead}>
                      <Text style={styles.occupancyTopic}>{topic.label || topic.anchor}</Text>
                      <Text style={styles.occupancyPercent}>{percent}%</Text>
                    </View>
                    <View style={styles.occupancyTrack}>
                      <View style={[styles.occupancyFill, { width: `${Math.max(5, percent)}%` }]} />
                    </View>
                  </View>
                );
              })}
            </View>
          </View>
        )}

        <View style={styles.glassCard}>
          <View style={styles.arcHeader}>
            <View>
              <Text style={styles.cardTitle}>Selected Thread</Text>
              <Text style={styles.cardSubtitle}>
                {arc?.label || selectedAnchor || "Pick a topic bubble"}
              </Text>
            </View>
            {loadingArc && <ActivityIndicator size="small" color={palette.muted} />}
          </View>

          {error ? <Text style={styles.errorText}>{error}</Text> : null}

          {!loadingArc && moments.length === 0 ? (
            <Text style={styles.emptyText}>No detailed arc moments available for this thread yet.</Text>
          ) : (
            <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.momentRow}>
              {moments.map((moment, index) => {
                const snippet = String(moment.short_snippet || "Moment").trim();
                const confidence = Number(moment.confidence || 0);
                const diameter = Math.round(clamp(86 + snippet.length * 0.18 + confidence * 24, 90, 170));
                return (
                  <View key={`${moment.source_ref || "moment"}-${index}`} style={styles.momentWrap}>
                    <View
                      style={[
                        styles.momentBubble,
                        { width: diameter, height: diameter },
                      ]}
                    >
                      <Text style={styles.momentDate}>{shortDate(moment.ts)}</Text>
                      <Text numberOfLines={4} style={styles.momentText}>
                        {snippet}
                      </Text>
                      <Text style={styles.momentMeta}>
                        {moment.facet || moment.stance || "thread"}
                      </Text>
                    </View>
                  </View>
                );
              })}
            </ScrollView>
          )}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const palette = {
  bg: "#060a13",
  fg: "#f5f7fb",
  muted: "#a7b0c0",
  border: "rgba(231, 239, 255, 0.16)",
  glass: "rgba(20, 28, 40, 0.7)",
  track: "rgba(255, 255, 255, 0.12)",
  fill: "#6ac6d3",
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: palette.bg,
  },
  auroraA: {
    position: "absolute",
    top: -90,
    left: -70,
    width: 260,
    height: 260,
    borderRadius: 140,
    backgroundColor: "rgba(120, 210, 239, 0.16)",
  },
  auroraB: {
    position: "absolute",
    bottom: 120,
    right: -80,
    width: 220,
    height: 220,
    borderRadius: 120,
    backgroundColor: "rgba(255, 192, 128, 0.14)",
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: palette.border,
  },
  iconButton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 1,
    borderColor: palette.border,
    backgroundColor: "rgba(255, 255, 255, 0.08)",
  },
  headerTitleWrap: {
    alignItems: "center",
  },
  kicker: {
    color: palette.muted,
    fontSize: 11,
    letterSpacing: 1.2,
    textTransform: "uppercase",
  },
  title: {
    color: palette.fg,
    fontSize: 20,
    fontWeight: "600",
    marginTop: 2,
  },
  content: {
    paddingHorizontal: 14,
    paddingTop: 14,
    paddingBottom: 24,
    gap: 12,
  },
  glassCard: {
    borderRadius: 24,
    borderWidth: 1,
    borderColor: palette.border,
    backgroundColor: palette.glass,
    padding: 14,
    shadowColor: "#000",
    shadowOpacity: 0.25,
    shadowRadius: 14,
    shadowOffset: { width: 0, height: 8 },
  },
  cardTitle: {
    color: palette.fg,
    fontSize: 17,
    fontWeight: "600",
  },
  cardSubtitle: {
    color: palette.muted,
    fontSize: 13,
    marginTop: 4,
    lineHeight: 18,
  },
  loadingRow: {
    paddingVertical: 22,
    alignItems: "center",
  },
  emptyText: {
    color: palette.muted,
    fontSize: 13,
    marginTop: 12,
    lineHeight: 18,
  },
  errorText: {
    color: "#f4b3a5",
    fontSize: 13,
    marginTop: 10,
  },
  topicCloud: {
    marginTop: 14,
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 10,
  },
  topicBubble: {
    borderRadius: 140,
    borderWidth: 1,
    borderColor: palette.border,
    paddingHorizontal: 10,
    paddingVertical: 12,
    alignItems: "center",
    justifyContent: "center",
  },
  topicBubbleActive: {
    borderColor: "rgba(215, 244, 255, 0.7)",
  },
  topicLabel: {
    color: palette.fg,
    fontSize: 13,
    textAlign: "center",
    fontWeight: "600",
  },
  topicShare: {
    color: "#d8f5ff",
    fontSize: 16,
    fontWeight: "700",
    marginTop: 4,
  },
  topicCount: {
    color: palette.muted,
    fontSize: 11,
    marginTop: 3,
  },
  occupancyList: {
    marginTop: 12,
    gap: 10,
  },
  occupancyRow: {
    gap: 6,
  },
  occupancyHead: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  occupancyTopic: {
    color: palette.fg,
    fontSize: 13,
    fontWeight: "500",
  },
  occupancyPercent: {
    color: palette.muted,
    fontSize: 12,
  },
  occupancyTrack: {
    height: 8,
    borderRadius: 999,
    backgroundColor: palette.track,
    overflow: "hidden",
  },
  occupancyFill: {
    height: "100%",
    borderRadius: 999,
    backgroundColor: palette.fill,
  },
  arcHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  momentRow: {
    marginTop: 12,
    paddingRight: 6,
    gap: 10,
  },
  momentWrap: {
    justifyContent: "center",
    alignItems: "center",
  },
  momentBubble: {
    borderRadius: 120,
    borderWidth: 1,
    borderColor: "rgba(232, 239, 255, 0.23)",
    backgroundColor: "rgba(255, 255, 255, 0.09)",
    paddingHorizontal: 10,
    paddingVertical: 12,
    justifyContent: "center",
    alignItems: "center",
  },
  momentDate: {
    color: "#d8e2f4",
    fontSize: 11,
    marginBottom: 6,
  },
  momentText: {
    color: palette.fg,
    fontSize: 12,
    textAlign: "center",
    lineHeight: 16,
  },
  momentMeta: {
    color: palette.muted,
    fontSize: 11,
    marginTop: 6,
    textTransform: "lowercase",
  },
});
