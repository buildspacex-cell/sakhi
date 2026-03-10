import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ActivityIndicator,
  Animated,
  Modal,
  NativeScrollEvent,
  NativeSyntheticEvent,
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
  surface?: {
    mirror_allowed?: boolean;
    detail_allowed?: boolean;
  };
  arc?: {
    element_count?: number;
    span_days?: number;
    phase_count?: number;
    features?: {
      direction?: string;
    };
  };
  included_moments?: ContinuityMoment[];
}

const BACKEND_URL = config.backendUrl || "https://sakhi-production-930f.up.railway.app";
const REFLECT_POLL_INTERVAL_MS = 2000;
const REFLECT_POLL_MAX_ATTEMPTS = 70;
const MIN_DEEP_MOMENTS = 8;
const MOMENT_CARD_WIDTH = 246;
const MOMENT_CARD_GAP = 12;
const FLOW_CARD_WIDTH = 184;

type MomentDensity = "focus" | "flow" | "atlas";

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

function shortDate(input?: string): string {
  if (!input) return "";
  const parsed = new Date(input);
  if (Number.isNaN(parsed.getTime())) return "";
  return parsed.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function monthYearLabel(input?: string): string {
  if (!input) return "Undated";
  const parsed = new Date(input);
  if (Number.isNaN(parsed.getTime())) return "Undated";
  return parsed.toLocaleDateString(undefined, { month: "short", year: "numeric" });
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function toFiniteNumber(value: unknown, fallback = 0): number {
  const num = Number(value);
  return Number.isFinite(num) ? num : fallback;
}

function formatTopicReflectionResult(payload: Record<string, unknown>): string {
  const result = (payload.result as Record<string, unknown> | undefined) || {};
  const chatResponse = String(result.chat_response || "").trim();
  if (chatResponse) {
    return chatResponse;
  }

  const originStory = String(result.origin_story || "").trim();
  const currentStage = String(result.current_stage || "").trim();
  const keyPivots = Array.isArray(result.key_pivots) ? result.key_pivots : [];
  const recurring = Array.isArray(result.recurring_tensions) ? result.recurring_tensions : [];

  return [
    originStory,
    typeof keyPivots[0] === "string" ? String(keyPivots[0]).trim() : "",
    currentStage,
    typeof recurring[0] === "string" ? String(recurring[0]).trim() : "",
  ]
    .filter((item) => item.length > 0)
    .join(" ");
}

function buildMomentObservation(moment: ContinuityMoment): string {
  const facet = String(moment.facet || "").trim().replace(/_/g, " ");
  const stance = String(moment.stance || "").trim().toLowerCase();

  if (facet) {
    return `Sakhi noticed this moment was tied to your ${facet} thread.`;
  }
  if (stance === "toward") {
    return "Sakhi noticed you were moving toward this direction.";
  }
  if (stance === "away") {
    return "Sakhi noticed a pull away from this direction.";
  }
  return "Sakhi noticed this added important context to your ongoing story.";
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
  const [threadOpen, setThreadOpen] = useState(false);
  const [selectedMoment, setSelectedMoment] = useState<ContinuityMoment | null>(null);
  const [deepReflectLoading, setDeepReflectLoading] = useState(false);
  const [, setDeepReflectStatus] = useState("");
  const [deepReflectText, setDeepReflectText] = useState("");
  const [deepReflectError, setDeepReflectError] = useState("");
  const [activeMomentMonth, setActiveMomentMonth] = useState("Timeline");
  const [momentOpening, setMomentOpening] = useState(false);
  const threadZoom = useRef(new Animated.Value(0)).current;
  const momentOpenTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const loadArc = useCallback(
    async (anchor: string) => {
      if (!personId || !anchor) return;
      setLoadingArc(true);
      setSelectedMoment(null);
      setDeepReflectText("");
      setDeepReflectError("");
      setDeepReflectStatus("");
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

  const pollTopicReflection = useCallback(
    async (reflectionId: string, person: string): Promise<string | null> => {
      const fetchResult = async (): Promise<string | null> => {
        const params = new URLSearchParams({
          id: reflectionId,
          person_id: person,
          t: String(Date.now()),
        });
        const resultRes = await fetch(`${BACKEND_URL}/continuity/reflection/result?${params.toString()}`, {
          cache: "no-store",
          headers: authToken ? { Authorization: `Bearer ${authToken}` } : undefined,
        });
        if (!resultRes.ok) return null;
        const resultData = (await resultRes.json()) as Record<string, unknown>;
        if (String(resultData.status || "queued") !== "done") return null;
        return formatTopicReflectionResult(resultData);
      };

      for (let attempt = 0; attempt < REFLECT_POLL_MAX_ATTEMPTS; attempt += 1) {
        try {
          const statusParams = new URLSearchParams({
            id: reflectionId,
            person_id: person,
            t: String(Date.now()),
          });
          const statusRes = await fetch(`${BACKEND_URL}/continuity/reflection/status?${statusParams.toString()}`, {
            cache: "no-store",
            headers: authToken ? { Authorization: `Bearer ${authToken}` } : undefined,
          });
          if (!statusRes.ok) break;
          const statusData = (await statusRes.json()) as Record<string, unknown>;
          const status = String(statusData.status || "queued");
          setDeepReflectStatus(status);

          if (status === "done") {
            return await fetchResult();
          }
          if (status === "failed") {
            return null;
          }

          if (attempt % 3 === 0) {
            const optimistic = await fetchResult();
            if (optimistic) return optimistic;
          }
        } catch (err) {
          console.error("[topic-reflection] deep poll error", err);
          break;
        }

        await sleep(REFLECT_POLL_INTERVAL_MS);
      }

      try {
        return await fetchResult();
      } catch {
        return null;
      }
    },
    [authToken],
  );

  const runDeepReflect = useCallback(async () => {
    if (!personId || !selectedAnchor || deepReflectLoading) return;

    setDeepReflectLoading(true);
    setDeepReflectStatus("queued");
    setDeepReflectError("");

    try {
      const res = await fetch(`${BACKEND_URL}/continuity/reflection/run`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
        },
        body: JSON.stringify({
          person_id: personId,
          topic_key: selectedAnchor,
          window: "3650d",
          mode: "topic_reflection",
        }),
      });

      if (!res.ok) {
        throw new Error(`Deep Reflect request failed (${res.status})`);
      }

      const data = (await res.json()) as Record<string, unknown>;
      const reflectionId = String(data.reflection_id || "");
      if (!reflectionId) {
        throw new Error("Deep Reflect response missing reflection id");
      }

      const deepText = await pollTopicReflection(reflectionId, personId);
      if (deepText) {
        setDeepReflectText(deepText);
      } else {
        setDeepReflectError("Whole-story summary did not complete this time. Please try again.");
      }
    } catch (err) {
      console.error("[topic-reflection] deep run error", err);
      setDeepReflectError("Could not summarize this story right now.");
    } finally {
      setDeepReflectLoading(false);
      setDeepReflectStatus("");
    }
  }, [authToken, deepReflectLoading, personId, pollTopicReflection, selectedAnchor]);

  const openThread = useCallback(
    (anchor: string) => {
      setSelectedAnchor(anchor);
      setThreadOpen(true);
      threadZoom.setValue(0);
      Animated.spring(threadZoom, {
        toValue: 1,
        damping: 20,
        mass: 0.9,
        stiffness: 180,
        useNativeDriver: true,
      }).start();
      void loadArc(anchor);
    },
    [loadArc, threadZoom],
  );

  const closeThread = useCallback(() => {
    Animated.timing(threadZoom, {
      toValue: 0,
      duration: 220,
      useNativeDriver: true,
    }).start(({ finished }) => {
      if (finished) {
        setThreadOpen(false);
      }
    });
  }, [threadZoom]);

  const openMoment = useCallback((moment: ContinuityMoment) => {
    if (momentOpenTimerRef.current) {
      clearTimeout(momentOpenTimerRef.current);
      momentOpenTimerRef.current = null;
    }
    setMomentOpening(true);
    setSelectedMoment(moment);
    momentOpenTimerRef.current = setTimeout(() => {
      setMomentOpening(false);
      momentOpenTimerRef.current = null;
    }, 220);
  }, []);

  const closeMoment = useCallback(() => {
    if (momentOpenTimerRef.current) {
      clearTimeout(momentOpenTimerRef.current);
      momentOpenTimerRef.current = null;
    }
    setMomentOpening(false);
    setSelectedMoment(null);
  }, []);

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

  useEffect(() => {
    return () => {
      if (momentOpenTimerRef.current) {
        clearTimeout(momentOpenTimerRef.current);
        momentOpenTimerRef.current = null;
      }
    };
  }, []);

  const totalTopicWeight = useMemo(
    () => topics.reduce((sum, topic) => sum + Math.max(0, topic.selected_count), 0),
    [topics],
  );

  const selectedTopic = useMemo(
    () => topics.find((topic) => topic.anchor === selectedAnchor) || null,
    [selectedAnchor, topics],
  );

  const moments = useMemo(
    () =>
      [...(arc?.included_moments || [])].sort((a, b) => {
        const aTs = new Date(String(a.ts || "")).getTime();
        const bTs = new Date(String(b.ts || "")).getTime();
        return aTs - bTs;
      }),
    [arc?.included_moments],
  );

  const depthMomentCount = useMemo(() => {
    const topicCount = toFiniteNumber(selectedTopic?.selected_count, 0);
    const arcCount = toFiniteNumber(arc?.arc?.element_count, 0);
    const includedCount = moments.length;
    return Math.max(topicCount, arcCount, includedCount);
  }, [arc?.arc?.element_count, moments.length, selectedTopic?.selected_count]);

  const momentDensity = useMemo<MomentDensity>(() => {
    if (depthMomentCount <= 8) return "focus";
    if (depthMomentCount <= 24) return "flow";
    return "atlas";
  }, [depthMomentCount]);

  const horizontalCardWidth = momentDensity === "flow" ? FLOW_CARD_WIDTH : MOMENT_CARD_WIDTH;
  const horizontalSnapInterval = horizontalCardWidth + MOMENT_CARD_GAP;

  const monthGroups = useMemo(() => {
    const groups: { month: string; items: ContinuityMoment[] }[] = [];
    for (const moment of moments) {
      const month = monthYearLabel(moment.ts);
      const last = groups[groups.length - 1];
      if (!last || last.month !== month) {
        groups.push({ month, items: [moment] });
      } else {
        last.items.push(moment);
      }
    }
    return groups;
  }, [moments]);

  const updateActiveMonthFromOffset = useCallback(
    (offsetX: number) => {
      if (momentDensity === "atlas" || moments.length === 0) return;
      const rawIndex = Math.round(offsetX / Math.max(horizontalSnapInterval, 1));
      const index = clamp(rawIndex, 0, moments.length - 1);
      const nextMonth = monthYearLabel(moments[index]?.ts);
      setActiveMomentMonth((previous) => (previous === nextMonth ? previous : nextMonth));
    },
    [horizontalSnapInterval, momentDensity, moments],
  );

  const handleMomentLaneScroll = useCallback(
    (event: NativeSyntheticEvent<NativeScrollEvent>) => {
      updateActiveMonthFromOffset(event.nativeEvent.contentOffset.x);
    },
    [updateActiveMonthFromOffset],
  );

  useEffect(() => {
    if (momentDensity === "atlas") {
      setActiveMomentMonth(monthGroups[0]?.month || "Timeline");
      return;
    }
    setActiveMomentMonth(monthYearLabel(moments[0]?.ts));
  }, [momentDensity, monthGroups, moments]);

  const deepReflectReady = useMemo(() => {
    return depthMomentCount >= MIN_DEEP_MOMENTS;
  }, [depthMomentCount]);

  const threadLabel = selectedTopic?.label || arc?.label || selectedAnchor || "Thread";
  const threadLoadingText = deepReflectLoading
    ? "Building story..."
    : loadingArc
      ? "Loading moments..."
      : "Opening moment...";

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
          <Text style={styles.title}>Reflection</Text>
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
                    onPress={() => void openThread(topic.anchor)}
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
          {error ? <Text style={styles.errorText}>{error}</Text> : null}
        </View>
      </ScrollView>

      <Modal
        visible={threadOpen}
        animationType="none"
        transparent={false}
        onRequestClose={closeThread}
      >
        <Animated.View
          style={[
            styles.threadScreen,
            {
              opacity: threadZoom.interpolate({
                inputRange: [0, 1],
                outputRange: [0.35, 1],
              }),
              transform: [
                {
                  scale: threadZoom.interpolate({
                    inputRange: [0, 1],
                    outputRange: [0.93, 1],
                  }),
                },
                {
                  translateY: threadZoom.interpolate({
                    inputRange: [0, 1],
                    outputRange: [28, 0],
                  }),
                },
              ],
            },
          ]}
        >
          <SafeAreaView style={styles.threadScreenFill}>
            <View pointerEvents="none" style={styles.auroraA} />
            <View pointerEvents="none" style={styles.auroraB} />

            <View style={styles.header}>
              <Pressable style={styles.iconButton} onPress={closeThread}>
                <Ionicons name="chevron-back" size={18} color={palette.fg} />
              </Pressable>
              <View style={styles.headerTitleWrap}>
                <Text style={styles.kicker}>Reflection</Text>
                <Text style={styles.title}>{threadLabel}</Text>
              </View>
              <Pressable style={styles.iconButton} onPress={() => void loadArc(selectedAnchor)}>
                <Ionicons name="refresh-outline" size={18} color={palette.fg} />
              </Pressable>
            </View>

            <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
              <View style={styles.glassCard}>
                <View style={styles.arcHeader}>
                  <View>
                    <Text style={styles.cardTitle}>Moments</Text>
                    <Text style={styles.cardSubtitle}>Tap a moment to open the full snapshot.</Text>
                  </View>
                  {loadingArc && <ActivityIndicator size="small" color={palette.muted} />}
                </View>

                {!loadingArc && moments.length === 0 ? (
                  <Text style={styles.emptyText}>No moments yet for this thread.</Text>
                ) : (
                  <>
                    <View style={styles.momentLaneHeader}>
                      <View style={styles.monthReflectorPill}>
                        <Text style={styles.monthReflectorText}>
                          {momentDensity === "atlas" ? "Timeline by month" : activeMomentMonth}
                        </Text>
                      </View>
                      <Text style={styles.momentLaneHint}>
                        {momentDensity === "atlas" ? "Scroll memories" : "Swipe memories"}
                      </Text>
                    </View>

                    {momentDensity === "atlas" ? (
                      <View style={styles.atlasList}>
                        {monthGroups.map((group, groupIndex) => (
                          <View key={`month-group-${group.month}-${groupIndex}`} style={styles.monthBlock}>
                            <View style={styles.monthStickyWrap}>
                              <Text style={styles.monthStickyText}>{group.month}</Text>
                            </View>
                            <View style={styles.photoGrid}>
                              {group.items.map((moment, itemIndex) => {
                                const snippet = String(moment.short_snippet || "Moment").trim();
                                return (
                                  <Pressable
                                    key={`${group.month}-${moment.source_ref || "moment"}-${itemIndex}`}
                                    style={styles.photoCard}
                                    onPress={() => openMoment(moment)}
                                  >
                                    <Text style={styles.photoDate}>{shortDate(moment.ts) || "Undated"}</Text>
                                    <Text numberOfLines={3} style={styles.photoText}>
                                      {snippet}
                                    </Text>
                                  </Pressable>
                                );
                              })}
                            </View>
                          </View>
                        ))}
                      </View>
                    ) : (
                      <ScrollView
                        horizontal
                        showsHorizontalScrollIndicator={false}
                        contentContainerStyle={styles.momentRow}
                        decelerationRate="fast"
                        snapToAlignment="start"
                        snapToInterval={horizontalSnapInterval}
                        disableIntervalMomentum
                        onScroll={handleMomentLaneScroll}
                        scrollEventThrottle={16}
                      >
                        {moments.map((moment, index) => {
                          const snippet = String(moment.short_snippet || "Moment").trim();
                          return (
                            <Pressable
                              key={`${moment.source_ref || "moment"}-${index}`}
                              style={[
                                styles.momentCard,
                                momentDensity === "flow" && styles.momentCardFlow,
                                { width: horizontalCardWidth },
                              ]}
                              onPress={() => openMoment(moment)}
                            >
                              <View style={styles.momentHeaderRow}>
                                <Text style={styles.momentIndex}>Moment {index + 1}</Text>
                                <View style={styles.momentDatePill}>
                                  <Text style={styles.momentDate}>{shortDate(moment.ts) || "Undated"}</Text>
                                </View>
                              </View>
                              <Text
                                numberOfLines={momentDensity === "flow" ? 4 : 5}
                                style={[styles.momentTextLeft, momentDensity === "flow" && styles.momentTextFlow]}
                              >
                                {snippet}
                              </Text>
                              <View style={styles.momentMetaRow}>
                                <Text style={styles.momentMetaLeft}>
                                  {(moment.facet || moment.stance || "thread").toString().replace(/_/g, " ")}
                                </Text>
                                <Ionicons name="expand-outline" size={15} color="#cfe1ff" />
                              </View>
                            </Pressable>
                          );
                        })}
                      </ScrollView>
                    )}
                  </>
                )}
              </View>

              <View style={styles.glassCard}>
                <Pressable
                  style={[
                    styles.deepReflectButton,
                    (!deepReflectReady || deepReflectLoading) && styles.deepReflectButtonDisabled,
                  ]}
                  onPress={() => void runDeepReflect()}
                  disabled={!deepReflectReady || deepReflectLoading}
                >
                  {deepReflectLoading ? (
                    <View style={styles.deepReflectButtonContent}>
                      <ActivityIndicator size="small" color="#f5dcb2" />
                      <Text style={styles.deepReflectButtonText}>Building Story...</Text>
                    </View>
                  ) : (
                    <View style={styles.deepReflectButtonContent}>
                      <Ionicons name="sparkles" size={15} color="#ffe6bf" />
                      <Text style={styles.deepReflectButtonText}>{`${threadLabel} Story`}</Text>
                    </View>
                  )}
                </Pressable>
                {!deepReflectReady ? (
                  <Text style={styles.depthHint}>{`${threadLabel} needs more depth for a story...`}</Text>
                ) : null}
                {deepReflectError ? <Text style={styles.errorText}>{deepReflectError}</Text> : null}
                {deepReflectText ? <Text style={styles.deepReflectText}>{deepReflectText}</Text> : null}
              </View>
            </ScrollView>
            {(loadingArc || momentOpening || deepReflectLoading) ? (
              <View style={styles.threadLoadingOverlay}>
                <ActivityIndicator size="large" color="#f5dcb2" />
                <Text style={styles.threadLoadingText}>{threadLoadingText}</Text>
              </View>
            ) : null}
          </SafeAreaView>
        </Animated.View>
      </Modal>

      <Modal
        visible={Boolean(selectedMoment)}
        animationType="fade"
        transparent
        onRequestClose={closeMoment}
      >
        <View style={styles.momentModalBackdrop}>
          <View style={styles.momentModalCard}>
            <Text style={styles.cardTitle}>{shortDate(selectedMoment?.ts) || "Moment"}</Text>
            {momentOpening ? (
              <View style={styles.momentLoadingRow}>
                <ActivityIndicator size="small" color="#f5dcb2" />
                <Text style={styles.momentLoadingText}>Opening moment...</Text>
              </View>
            ) : (
              <>
                <Text style={styles.momentDetailText}>
                  {String(selectedMoment?.short_snippet || "").trim() || "No details available for this moment yet."}
                </Text>
                <Text style={styles.momentDetailMeta}>
                  Tag: {String(selectedMoment?.facet || selectedMoment?.stance || "thread").replace(/_/g, " ")}
                </Text>
                <Text style={styles.momentObservation}>
                  {selectedMoment ? buildMomentObservation(selectedMoment) : ""}
                </Text>
              </>
            )}
            <Pressable style={styles.momentClose} onPress={closeMoment}>
              <Text style={styles.momentCloseText}>Close</Text>
            </Pressable>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const palette = {
  bg: "#060a13",
  fg: "#f5f7fb",
  muted: "#a7b0c0",
  border: "rgba(231, 239, 255, 0.16)",
  glass: "rgba(20, 28, 40, 0.7)",
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: palette.bg,
  },
  threadScreen: {
    flex: 1,
    backgroundColor: palette.bg,
  },
  threadScreenFill: {
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
  arcHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  momentLaneHeader: {
    marginTop: 10,
    marginBottom: 8,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  monthReflectorPill: {
    borderRadius: 999,
    borderWidth: 1,
    borderColor: "rgba(207, 222, 244, 0.35)",
    backgroundColor: "rgba(223, 234, 255, 0.12)",
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  monthReflectorText: {
    color: "#dbe8ff",
    fontSize: 11,
    fontWeight: "600",
    textTransform: "uppercase",
    letterSpacing: 0.4,
  },
  momentLaneHint: {
    color: palette.muted,
    fontSize: 11,
    letterSpacing: 0.2,
  },
  momentRow: {
    paddingTop: 2,
    paddingRight: 8,
    gap: MOMENT_CARD_GAP,
  },
  momentCard: {
    minHeight: 214,
    borderRadius: 24,
    borderWidth: 1,
    borderColor: "rgba(206, 227, 255, 0.34)",
    backgroundColor: "rgba(39, 58, 84, 0.5)",
    paddingHorizontal: 14,
    paddingVertical: 15,
    shadowColor: "#0c1d36",
    shadowOpacity: 0.32,
    shadowRadius: 14,
    shadowOffset: { width: 0, height: 8 },
  },
  momentCardFlow: {
    minHeight: 170,
    borderRadius: 20,
    paddingHorizontal: 12,
    paddingVertical: 12,
  },
  momentHeaderRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 10,
  },
  momentIndex: {
    color: "#c5d7f5",
    fontSize: 12,
    fontWeight: "600",
    letterSpacing: 0.3,
  },
  momentDatePill: {
    borderRadius: 999,
    borderWidth: 1,
    borderColor: "rgba(207, 222, 244, 0.35)",
    backgroundColor: "rgba(223, 234, 255, 0.12)",
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  momentDate: {
    color: "#dbe8ff",
    fontSize: 11,
    fontWeight: "600",
  },
  momentTextLeft: {
    color: palette.fg,
    fontSize: 19,
    lineHeight: 27,
    fontWeight: "500",
  },
  momentTextFlow: {
    fontSize: 15,
    lineHeight: 22,
  },
  momentMetaRow: {
    marginTop: 12,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  momentMetaLeft: {
    color: "#b9c9e4",
    fontSize: 13,
    textTransform: "lowercase",
    flex: 1,
    marginRight: 8,
  },
  atlasList: {
    marginTop: 4,
    paddingBottom: 6,
  },
  monthBlock: {
    marginBottom: 6,
  },
  monthStickyWrap: {
    alignSelf: "flex-start",
    borderRadius: 999,
    borderWidth: 1,
    borderColor: "rgba(207, 222, 244, 0.35)",
    backgroundColor: "rgba(223, 234, 255, 0.12)",
    paddingHorizontal: 10,
    paddingVertical: 4,
    marginTop: 8,
    marginBottom: 8,
  },
  monthStickyText: {
    color: "#dbe8ff",
    fontSize: 11,
    fontWeight: "600",
    textTransform: "uppercase",
    letterSpacing: 0.4,
  },
  photoGrid: {
    width: "100%",
    flexDirection: "row",
    flexWrap: "wrap",
    justifyContent: "space-between",
    alignItems: "flex-start",
    marginBottom: 2,
  },
  photoCard: {
    width: "48%",
    minHeight: 88,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: "rgba(198, 219, 252, 0.3)",
    backgroundColor: "rgba(39, 58, 84, 0.5)",
    paddingHorizontal: 10,
    paddingVertical: 9,
    marginBottom: 8,
    alignSelf: "flex-start",
  },
  photoDate: {
    color: "#dbe8ff",
    fontSize: 10,
    fontWeight: "600",
  },
  photoText: {
    marginTop: 6,
    color: palette.fg,
    fontSize: 12,
    lineHeight: 16,
  },
  deepReflectButton: {
    marginTop: 0,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: "rgba(243, 214, 164, 0.58)",
    backgroundColor: "rgba(117, 86, 42, 0.62)",
    paddingVertical: 12,
    paddingHorizontal: 14,
    alignItems: "center",
    justifyContent: "center",
    shadowColor: "#c98f45",
    shadowOpacity: 0.32,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 6 },
  },
  deepReflectButtonDisabled: {
    opacity: 0.5,
    shadowOpacity: 0.08,
  },
  deepReflectButtonContent: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },
  deepReflectButtonText: {
    color: "#fce7c3",
    fontSize: 14,
    fontWeight: "700",
    letterSpacing: 0.2,
  },
  deepReflectText: {
    color: palette.fg,
    fontSize: 14,
    lineHeight: 21,
    marginTop: 12,
  },
  depthHint: {
    color: palette.muted,
    fontSize: 12,
    marginTop: 10,
    lineHeight: 17,
  },
  threadLoadingOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: "rgba(4, 10, 18, 0.62)",
    alignItems: "center",
    justifyContent: "center",
    gap: 10,
  },
  threadLoadingText: {
    color: "#fce7c3",
    fontSize: 13,
    fontWeight: "600",
    letterSpacing: 0.2,
  },
  momentModalBackdrop: {
    flex: 1,
    backgroundColor: "rgba(2, 6, 14, 0.72)",
    justifyContent: "center",
    paddingHorizontal: 18,
  },
  momentModalCard: {
    borderRadius: 20,
    borderWidth: 1,
    borderColor: "rgba(231, 239, 255, 0.24)",
    backgroundColor: "rgba(17, 26, 42, 0.94)",
    padding: 16,
  },
  momentDetailText: {
    color: palette.fg,
    fontSize: 16,
    lineHeight: 24,
    marginTop: 10,
  },
  momentLoadingRow: {
    marginTop: 14,
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  momentLoadingText: {
    color: "#fce7c3",
    fontSize: 13,
    fontWeight: "600",
    letterSpacing: 0.2,
  },
  momentDetailMeta: {
    color: palette.muted,
    fontSize: 13,
    marginTop: 12,
    textTransform: "lowercase",
  },
  momentObservation: {
    color: "#d9e8ff",
    fontSize: 13,
    lineHeight: 20,
    marginTop: 12,
  },
  momentClose: {
    marginTop: 16,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "rgba(231, 239, 255, 0.24)",
    alignItems: "center",
    paddingVertical: 9,
    backgroundColor: "rgba(255, 255, 255, 0.06)",
  },
  momentCloseText: {
    color: palette.fg,
    fontSize: 13,
    fontWeight: "600",
  },
});
