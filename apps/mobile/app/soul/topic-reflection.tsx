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
import { trackSupportDebugEvent, type SupportDebugEventInput } from "../../lib/support/debugTelemetry";
import { Analytics } from "../../lib/analytics/events";
import { theme } from "../../lib/theme/tokens";
import { useAppHaptics } from "../../lib/feedback/useAppHaptics";
import { MOBILE_CONTINUITY_PLAN } from "../../lib/continuity/plan";
import { IconButton } from "../../components/ui/IconButton";
import { LoadingBlock } from "../../components/ui/LoadingBlock";

interface ArcLabels {
  arc_start_label: string;
  arc_now_label: string;
  arc_bridge: string;
  phase_labels?: string[];
}

interface ContinuityTopicSummary {
  anchor: string;
  label: string;
  confidence: number;
  selected_count: number;
  primary_selected_count?: number;
  span_days: number;
  direction: string;
  surface?: {
    mirror_allowed?: boolean;
    detail_allowed?: boolean;
  };
}

interface ContinuityMoment {
  source_ref?: string;
  ts?: string;
  short_snippet?: string;
  confidence?: number;
  facet?: string;
  stance?: string;
}

interface ArcPhase {
  index: number;
  start_ts: string;
  end_ts: string;
  start_day: number;
  end_day: number;
  element_count: number;
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
    phases?: ArcPhase[];
    features?: {
      direction?: string;
    };
  };
  included_moments?: ContinuityMoment[];
}

const BACKEND_URL = (config.backendUrl || "").replace(/\/+$/, "");
const REFLECT_POLL_INTERVAL_MS = 2000;
const REFLECT_POLL_MAX_ATTEMPTS = 70;
const MIN_TOPIC_STORY_MOMENTS = 3;  // <Topic> Story: matches backend min_len=3
const MIN_CROSS_CONTEXT_MOMENTS = 6;
const MIN_RELATED_TOPIC_MOMENTS = MIN_TOPIC_STORY_MOMENTS; // Allow lighter supporting threads once the anchor is deep enough.
const MAX_CROSS_CONTEXT_TOPICS = 3;
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

function extractArcLabels(payload: Record<string, unknown>): ArcLabels | null {
  const result = (payload.result as Record<string, unknown> | undefined) || {};
  const start = String(result.arc_start_label || "").trim();
  const now = String(result.arc_now_label || "").trim();
  const bridge = String(result.arc_bridge || "").trim();
  if (!start && !now) return null;
  const rawPhaseLabels = Array.isArray(result.phase_labels) ? result.phase_labels : [];
  const phase_labels = rawPhaseLabels
    .map((l) => String(l || "").trim())
    .filter((l) => l.length > 0);
  return { arc_start_label: start, arc_now_label: now, arc_bridge: bridge, phase_labels };
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

interface ArcScrollViewProps {
  moments: ContinuityMoment[];
  phases: ArcPhase[];
  arcLabels: ArcLabels | null;
  arcLabelsLoading: boolean;
  topicLabel: string;
  spanDays: number;
  onMomentPress: (moment: ContinuityMoment) => void;
}

function phaseLabel(index: number, total: number): string {
  const labels: Record<number, string[]> = {
    2: ["Earlier", "Recent"],
    3: ["Early", "Building", "Now"],
    4: ["Early", "Middle", "Later", "Now"],
  };
  return labels[total]?.[index] ?? `Phase ${index + 1}`;
}

function shortDateRange(startTs?: string, endTs?: string): string {
  const start = startTs ? new Date(startTs).toLocaleDateString(undefined, { month: "short", day: "numeric" }) : "";
  const end = endTs ? new Date(endTs).toLocaleDateString(undefined, { month: "short", day: "numeric" }) : "";
  if (!start) return "";
  if (!end || start === end) return start;
  return `${start} – ${end}`;
}

function assignMomentsToPhases(
  moments: ContinuityMoment[],
  phases: ArcPhase[],
): Map<number, ContinuityMoment[]> {
  const map = new Map<number, ContinuityMoment[]>();
  for (const phase of phases) {
    map.set(phase.index, []);
  }
  for (const moment of moments) {
    if (!moment.ts) continue;
    const ts = new Date(moment.ts).getTime();
    let assigned = false;
    for (const phase of phases) {
      const start = new Date(phase.start_ts).getTime();
      const end = new Date(phase.end_ts).getTime();
      if (ts >= start && ts <= end) {
        map.get(phase.index)?.push(moment);
        assigned = true;
        break;
      }
    }
    // Overflow into last phase if timestamp falls outside all phase windows
    if (!assigned && phases.length > 0) {
      map.get(phases[phases.length - 1].index)?.push(moment);
    }
  }
  return map;
}

function ArcScrollView({
  moments,
  phases,
  arcLabels,
  arcLabelsLoading,
  topicLabel,
  spanDays,
  onMomentPress,
}: ArcScrollViewProps) {
  const [expandedPhase, setExpandedPhase] = useState<number | null>(null);

  const momentCount = moments.length;
  const spanLabel = spanDays >= 365
    ? `${Math.round(spanDays / 30)} months`
    : spanDays > 0
      ? `${Math.round(spanDays)} days`
      : "";

  const startLabel = arcLabels?.arc_start_label
    || (arcLabelsLoading ? "" : `${topicLabel} thread began`);
  const nowLabel = arcLabels?.arc_now_label
    || (arcLabelsLoading ? "" : `${momentCount} moments captured`);
  const bridgeLabel = arcLabels?.arc_bridge || "";

  const hasPhasesData = phases.length >= 2;
  const momentsByPhase = useMemo(
    () => hasPhasesData ? assignMomentsToPhases(moments, phases) : new Map<number, ContinuityMoment[]>(),
    [hasPhasesData, moments, phases],
  );

  const togglePhase = (index: number) => {
    setExpandedPhase((prev) => prev === index ? null : index);
  };

  const renderMomentCard = (moment: ContinuityMoment, index: number) => {
    const snippet = String(moment.short_snippet || "Moment").trim();
    return (
      <Pressable
        key={`arc-moment-${moment.source_ref || index}`}
        style={arcStyles.arcMomentCard}
        onPress={() => onMomentPress(moment)}
      >
        <View style={arcStyles.arcMomentHeader}>
          <Text style={arcStyles.arcMomentIndex}>Moment {index + 1}</Text>
          <Text style={arcStyles.arcMomentDate}>{shortDate(moment.ts) || "Undated"}</Text>
        </View>
        <Text numberOfLines={3} style={arcStyles.arcMomentSnippet}>{snippet}</Text>
        <Text style={arcStyles.arcMomentFacet}>
          {(moment.facet || moment.stance || "thread").toString().replace(/_/g, " ")}
        </Text>
      </Pressable>
    );
  };

  return (
    <View style={arcStyles.container}>
      {/* START node */}
      <View style={arcStyles.node}>
        <View style={arcStyles.nodeMarker}>
          <View style={arcStyles.nodeDot} />
        </View>
        <View style={arcStyles.nodeContent}>
          <Text style={arcStyles.nodeKicker}>WHERE IT BEGAN</Text>
          {arcLabelsLoading && !arcLabels ? (
            <View style={arcStyles.skeletonLine} />
          ) : (
            <Text style={arcStyles.nodeLabel}>{startLabel}</Text>
          )}
        </View>
      </View>

      {hasPhasesData ? (
        // Phase-segmented connector — each phase is a named, expandable block
        phases.map((phase, phaseIdx) => {
          const phaseMoments = momentsByPhase.get(phase.index) || [];
          const label = arcLabels?.phase_labels?.[phase.index] || phaseLabel(phase.index, phases.length);
          const dateRange = shortDateRange(phase.start_ts, phase.end_ts);
          const isLast = phaseIdx === phases.length - 1;
          const isExpanded = expandedPhase === phase.index;

          return (
            <View key={`phase-${phase.index}`} style={[arcStyles.connectorColumn, { marginLeft: 10 }]}>
              <View style={arcStyles.connectorLine} />
              <Pressable
                style={[arcStyles.countPill, isLast && arcStyles.countPillLast]}
                onPress={() => togglePhase(phase.index)}
              >
                <View style={arcStyles.countPillInner}>
                  <Text style={[arcStyles.phaseLabel, isLast && arcStyles.phaseLabelAccent]}>
                    {label}
                  </Text>
                  <Text style={arcStyles.countPillCount}>
                    · {phaseMoments.length} {phaseMoments.length === 1 ? "moment" : "moments"}
                  </Text>
                  {dateRange ? (
                    <Text style={arcStyles.countPillSpan}>{dateRange}</Text>
                  ) : null}
                  <View style={arcStyles.countPillChevron}>
                    <Ionicons
                      name={isExpanded ? "chevron-up" : "chevron-down"}
                      size={11}
                      color={arcPalette.accentText}
                    />
                  </View>
                </View>
                {isLast && bridgeLabel ? (
                  <Text style={arcStyles.bridgeText}>{bridgeLabel}</Text>
                ) : null}
              </Pressable>
              {isExpanded ? (
                phaseMoments.length > 0 ? (
                  <View style={arcStyles.expandedMoments}>
                    {phaseMoments.map((moment, index) => renderMomentCard(moment, index))}
                  </View>
                ) : (
                  <Text style={arcStyles.noMomentsHint}>No moments in this phase yet.</Text>
                )
              ) : null}
            </View>
          );
        })
      ) : (
        // Fallback: flat connector when no phase data
        <View style={[arcStyles.connectorColumn, { marginLeft: 10 }]}>
          <View style={arcStyles.connectorLine} />
          <Pressable style={arcStyles.countPill} onPress={() => togglePhase(-1)}>
            <View style={arcStyles.countPillInner}>
              <Text style={arcStyles.countPillCount}>
                {momentCount} {momentCount === 1 ? "moment" : "moments"}
              </Text>
              {spanLabel ? (
                <Text style={arcStyles.countPillSpan}>across {spanLabel}</Text>
              ) : null}
              <View style={arcStyles.countPillChevron}>
                <Ionicons
                  name={expandedPhase === -1 ? "chevron-up" : "chevron-down"}
                  size={11}
                  color={arcPalette.accentText}
                />
              </View>
            </View>
            {bridgeLabel ? (
              <Text style={arcStyles.bridgeText}>{bridgeLabel}</Text>
            ) : null}
          </Pressable>
          {expandedPhase === -1 ? (
            <View style={arcStyles.expandedMoments}>
              {moments.map((moment, index) => renderMomentCard(moment, index))}
            </View>
          ) : null}
          <View style={arcStyles.connectorLine} />
        </View>
      )}

      {/* Final connector into NOW node (phases path only — fallback already includes bottom line) */}
      {hasPhasesData ? (
        <View style={[arcStyles.connectorColumn, { marginLeft: 10 }]}>
          <View style={arcStyles.connectorLine} />
        </View>
      ) : null}

      {/* NOW node */}
      <View style={arcStyles.node}>
        <View style={arcStyles.nodeMarker}>
          <View style={[arcStyles.nodeDot, arcStyles.nodeDotAccent]} />
        </View>
        <View style={arcStyles.nodeContent}>
          <Text style={arcStyles.nodeKicker}>WHERE YOU ARE NOW</Text>
          {arcLabelsLoading && !arcLabels ? (
            <View style={arcStyles.skeletonLine} />
          ) : (
            <Text style={arcStyles.nodeLabel}>{nowLabel}</Text>
          )}
        </View>
      </View>
    </View>
  );
}

export default function TopicReflectionScreen() {
  const router = useRouter();
  const { user, session } = useAuth();
  const haptics = useAppHaptics();

  const personId = user?.personId || "";
  const authToken = session?.access_token || "";
  const backendConfigured = BACKEND_URL.length > 0;

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
  const [arcLabels, setArcLabels] = useState<ArcLabels | null>(null);
  const [meStoryLoading, setMeStoryLoading] = useState(false);
  const [, setMeStoryStatus] = useState("");
  const [meStoryText, setMeStoryText] = useState("");
  const [meStoryError, setMeStoryError] = useState("");
  const [activeMomentMonth, setActiveMomentMonth] = useState("Timeline");
  const [momentOpening, setMomentOpening] = useState(false);
  const threadZoom = useRef(new Animated.Value(0)).current;
  const momentOpenTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const debugSequenceRef = useRef(0);

  const emitDebugEvent = useCallback(
    (event: SupportDebugEventInput) => {
      if (!personId || !BACKEND_URL) return;
      debugSequenceRef.current += 1;
      void trackSupportDebugEvent({
        backendUrl: BACKEND_URL,
        authToken,
        personId,
        event: {
          ...event,
          seq: debugSequenceRef.current,
        },
      });
    },
    [authToken, personId],
  );

  const loadArc = useCallback(
    async (anchor: string) => {
      if (!personId || !anchor) return;
      const requestStartedAt = Date.now();
      emitDebugEvent({
        type: "api_start",
        name: "load_topic_arc",
        screen: "reflection",
        route: "/continuity/arc",
        method: "GET",
        metadata: { anchor },
      });
      setLoadingArc(true);
      setSelectedMoment(null);
      setDeepReflectText("");
      setDeepReflectError("");
      setDeepReflectStatus("");
      try {
        const params = new URLSearchParams({
          person_id: personId,
          anchor,
          window: MOBILE_CONTINUITY_PLAN.continuityWindow,
        });
        const res = await fetch(`${BACKEND_URL}/continuity/arc?${params.toString()}`, {
          cache: "no-store",
          headers: authToken ? { Authorization: `Bearer ${authToken}` } : undefined,
        });

        if (!res.ok) {
          throw new Error(`Arc fetch failed (${res.status})`);
        }
        emitDebugEvent({
          type: "api_end",
          name: "load_topic_arc",
          screen: "reflection",
          route: "/continuity/arc",
          method: "GET",
          status: res.status,
          latencyMs: Date.now() - requestStartedAt,
          requestId: res.headers.get("x-request-id") || undefined,
          metadata: { ok: res.ok, anchor },
        });

        const payload = (await res.json()) as ContinuityArcResponse;
        setArc(payload);
      } catch (err) {
        console.error("[topic-reflection] arc load error", err);
        emitDebugEvent({
          type: "ui_error",
          name: "load_topic_arc_failed",
          screen: "reflection",
          route: "/continuity/arc",
          method: "GET",
          metadata: { anchor },
        });
        setArc(null);
      } finally {
        setLoadingArc(false);
      }
    },
    [authToken, emitDebugEvent, personId],
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
    const requestStartedAt = Date.now();
    emitDebugEvent({
      type: "api_start",
      name: "load_topics",
      screen: "reflection",
      route: "/continuity/topics",
      method: "GET",
    });
    const params = new URLSearchParams({
      person_id: personId,
      window: MOBILE_CONTINUITY_PLAN.continuityWindow,
    });
    const res = await fetch(`${BACKEND_URL}/continuity/topics?${params.toString()}`, {
      cache: "no-store",
      headers: authToken ? { Authorization: `Bearer ${authToken}` } : undefined,
    });
    emitDebugEvent({
      type: "api_end",
      name: "load_topics",
      screen: "reflection",
      route: "/continuity/topics",
      method: "GET",
      status: res.status,
      latencyMs: Date.now() - requestStartedAt,
      requestId: res.headers.get("x-request-id") || undefined,
      metadata: { ok: res.ok },
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
  }, [authToken, emitDebugEvent, personId]);

  const pollTopicReflection = useCallback(
    async (reflectionId: string, person: string): Promise<{ text: string | null; arcLabels: ArcLabels | null }> => {
      const fetchResult = async (): Promise<{ text: string | null; arcLabels: ArcLabels | null } | null> => {
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
        return {
          text: formatTopicReflectionResult(resultData),
          arcLabels: extractArcLabels(resultData),
        };
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
            return (await fetchResult()) ?? { text: null, arcLabels: null };
          }
          if (status === "failed") {
            return { text: null, arcLabels: null };
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
        return (await fetchResult()) ?? { text: null, arcLabels: null };
      } catch {
        return { text: null, arcLabels: null };
      }
    },
    [authToken],
  );

  const runDeepReflect = useCallback(async () => {
    if (!personId || !selectedAnchor || deepReflectLoading) return;
    haptics.strongPress();

    emitDebugEvent({
      type: "action",
      name: "topic_story_pressed",
      screen: "reflection",
      route: "/continuity/reflection/run",
      method: "POST",
      metadata: { anchor: selectedAnchor },
    });
    setDeepReflectLoading(true);
    setDeepReflectStatus("queued");
    setDeepReflectError("");

    try {
      const requestStartedAt = Date.now();
      emitDebugEvent({
        type: "api_start",
        name: "run_topic_reflection",
        screen: "reflection",
        route: "/continuity/reflection/run",
        method: "POST",
        metadata: { mode: "topic_reflection", anchor: selectedAnchor },
      });
      const res = await fetch(`${BACKEND_URL}/continuity/reflection/run`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
        },
        body: JSON.stringify({
          person_id: personId,
          topic_key: selectedAnchor,
          window: MOBILE_CONTINUITY_PLAN.continuityWindow,
          mode: "topic_reflection",
        }),
      });
      emitDebugEvent({
        type: "api_end",
        name: "run_topic_reflection",
        screen: "reflection",
        route: "/continuity/reflection/run",
        method: "POST",
        status: res.status,
        latencyMs: Date.now() - requestStartedAt,
        requestId: res.headers.get("x-request-id") || undefined,
        metadata: { ok: res.ok, mode: "topic_reflection", anchor: selectedAnchor },
      });

      if (!res.ok) {
        throw new Error(`Deep Reflect request failed (${res.status})`);
      }

      const data = (await res.json()) as Record<string, unknown>;
      const reflectionId = String(data.reflection_id || "");
      if (!reflectionId) {
        throw new Error("Deep Reflect response missing reflection id");
      }

      const { text: deepText, arcLabels: labels } = await pollTopicReflection(reflectionId, personId);
      if (deepText) {
        Analytics.topicStoryCompleted({
          latency_ms: Date.now() - requestStartedAt,
          request_id: res.headers.get("x-request-id") || undefined,
        });
        setDeepReflectText(deepText);
        if (labels) setArcLabels(labels);
      } else {
        emitDebugEvent({
          type: "ui_error",
          name: "topic_story_incomplete",
          screen: "reflection",
          route: "/continuity/reflection/status",
          metadata: { anchor: selectedAnchor },
        });
        setDeepReflectError("Whole-story summary did not complete this time. Please try again.");
      }
    } catch (err) {
      console.error("[topic-reflection] deep run error", err);
      emitDebugEvent({
        type: "ui_error",
        name: "topic_story_failed",
        screen: "reflection",
        route: "/continuity/reflection/run",
        method: "POST",
        metadata: { anchor: selectedAnchor },
      });
      setDeepReflectError("Could not summarize this story right now.");
    } finally {
      setDeepReflectLoading(false);
      setDeepReflectStatus("");
    }
  }, [authToken, deepReflectLoading, emitDebugEvent, haptics, personId, pollTopicReflection, selectedAnchor]);

  const openThread = useCallback(
    (anchor: string) => {
      haptics.selection();
      Analytics.topicSelected({ topic_key: anchor });
      emitDebugEvent({
        type: "action",
        name: "topic_bubble_selected",
        screen: "reflection",
        metadata: { anchor },
      });
      setSelectedAnchor(anchor);
      setArcLabels(null);
      setDeepReflectText("");
      setDeepReflectError("");
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
    [emitDebugEvent, haptics, loadArc, threadZoom],
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
    haptics.selection();
    emitDebugEvent({
      type: "action",
      name: "moment_opened",
      screen: "reflection",
      metadata: {
        ts: String(moment.ts || ""),
        facet: String(moment.facet || ""),
      },
    });
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
  }, [emitDebugEvent, haptics]);

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
    if (!backendConfigured) {
      setTopics([]);
      setSelectedAnchor("");
      setArc(null);
      setError("This build is missing EXPO_PUBLIC_BACKEND_URL.");
      return;
    }

    setLoadingTopics(true);
    setError("");
    setMeStoryError("");
    setMeStoryText("");

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
      emitDebugEvent({
        type: "ui_error",
        name: "load_topics_failed",
        screen: "reflection",
        route: "/continuity/topics",
        method: "GET",
      });
      setTopics([]);
      setSelectedAnchor("");
      setArc(null);
      setError("Could not load continuity topics yet. Try sending a few chat turns first.");
    } finally {
      setLoadingTopics(false);
    }
  }, [backendConfigured, emitDebugEvent, ensureContinuityPolicyEnabled, fetchTopics, loadArc, personId]);

  useEffect(() => {
    void loadTopics();
  }, [loadTopics]);

  useEffect(() => {
    Analytics.reflectionOpened();
    emitDebugEvent({
      type: "screen_view",
      name: "reflection_opened",
      screen: "reflection",
      route: "/mobile/reflection",
    });
    // fire once on screen mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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

  const topicStoryReady = useMemo(() => {
    return depthMomentCount >= MIN_TOPIC_STORY_MOMENTS;
  }, [depthMomentCount]);
  const myStoryEligibleTopics = useMemo(
    () =>
      topics.filter((topic) => {
        const mirrorAllowed = topic.surface?.mirror_allowed;
        if (mirrorAllowed === false) {
          return false;
        }
        // Mirror backend _topic_story_count(): prefer primary_selected_count when present
        const gatingCount = topic.primary_selected_count ?? topic.selected_count;
        return toFiniteNumber(gatingCount, 0) >= MIN_RELATED_TOPIC_MOMENTS;
      }),
    [topics],
  );
  const selectedAnchorEligibleForMyStory = useMemo(
    () =>
      myStoryEligibleTopics.some(
        (topic) => {
          // Mirror backend _topic_story_count(): prefer primary_selected_count when present
          const gatingCount = topic.primary_selected_count ?? topic.selected_count;
          return topic.anchor === selectedAnchor
            && toFiniteNumber(gatingCount, 0) >= MIN_CROSS_CONTEXT_MOMENTS;
        },
      ),
    [myStoryEligibleTopics, selectedAnchor],
  );
  const myStoryTopicKeys = useMemo(() => {
    if (!selectedAnchorEligibleForMyStory || !selectedAnchor) return [];
    const related = myStoryEligibleTopics
      .map((topic) => topic.anchor)
      .filter((anchor) => anchor && anchor !== selectedAnchor);
    return [selectedAnchor, ...related].slice(0, MAX_CROSS_CONTEXT_TOPICS);
  }, [myStoryEligibleTopics, selectedAnchor, selectedAnchorEligibleForMyStory]);
  const myStoryReady = selectedAnchorEligibleForMyStory && myStoryTopicKeys.length >= 2;
  const myStoryUnlockHint = (() => {
    const selectedLabel = selectedTopic?.label || selectedAnchor || "This thread";
    if (!selectedAnchorEligibleForMyStory) {
      return `${selectedLabel} needs more depth before My Story can anchor here.`;
    }
    if (myStoryTopicKeys.length < 2) {
      return "My Story unlocks after one more topic appears.";
    }
    return "";
  })();

  const runMeStory = useCallback(async () => {
    if (!personId || meStoryLoading || myStoryTopicKeys.length < 2) return;
    haptics.strongPress();

    const primaryTopic = myStoryTopicKeys[0];
    emitDebugEvent({
      type: "action",
      name: "me_story_pressed",
      screen: "reflection",
      route: "/continuity/reflection/run",
      method: "POST",
      metadata: {
        topic_count: myStoryTopicKeys.length,
        primary_topic: primaryTopic,
      },
    });
    setMeStoryLoading(true);
    setMeStoryStatus("queued");
    setMeStoryError("");
    setMeStoryText("");

    try {
      const requestStartedAt = Date.now();
      emitDebugEvent({
        type: "api_start",
        name: "run_cross_context_story",
        screen: "reflection",
        route: "/continuity/reflection/run",
        method: "POST",
        metadata: { mode: "cross_context", topic_count: myStoryTopicKeys.length },
      });
      const res = await fetch(`${BACKEND_URL}/continuity/reflection/run`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
        },
        body: JSON.stringify({
          person_id: personId,
          topic_key: primaryTopic,
          topic_keys: myStoryTopicKeys,
          window: MOBILE_CONTINUITY_PLAN.continuityWindow,
          mode: "cross_context",
        }),
      });
      emitDebugEvent({
        type: "api_end",
        name: "run_cross_context_story",
        screen: "reflection",
        route: "/continuity/reflection/run",
        method: "POST",
        status: res.status,
        latencyMs: Date.now() - requestStartedAt,
        requestId: res.headers.get("x-request-id") || undefined,
        metadata: { ok: res.ok, mode: "cross_context" },
      });

      if (!res.ok) {
        throw new Error(`My Story request failed (${res.status})`);
      }

      const data = (await res.json()) as Record<string, unknown>;
      const reflectionId = String(data.reflection_id || "");
      if (!reflectionId) {
        throw new Error("My Story response missing reflection id");
      }

      const { text: storyText } = await pollTopicReflection(reflectionId, personId);
      if (storyText) {
        Analytics.meStoryCompleted({
          topic_count: myStoryTopicKeys.length,
          latency_ms: Date.now() - requestStartedAt,
          request_id: res.headers.get("x-request-id") || undefined,
        });
        setMeStoryText(storyText);
      } else {
        emitDebugEvent({
          type: "ui_error",
          name: "me_story_incomplete",
          screen: "reflection",
          route: "/continuity/reflection/status",
        });
        setMeStoryError("My Story did not complete this time. Please try again.");
      }
    } catch (err) {
      console.error("[topic-reflection] me story run error", err);
      emitDebugEvent({
        type: "ui_error",
        name: "me_story_failed",
        screen: "reflection",
        route: "/continuity/reflection/run",
        method: "POST",
      });
      setMeStoryError("Could not build My Story right now.");
    } finally {
      setMeStoryLoading(false);
      setMeStoryStatus("");
    }
  }, [authToken, emitDebugEvent, haptics, meStoryLoading, myStoryTopicKeys, personId, pollTopicReflection]);

  const threadLabel = selectedTopic?.label || arc?.label || selectedAnchor || "Thread";
  const threadLoadingText = deepReflectLoading
    ? "Building story..."
    : loadingArc
      ? "Loading moments..."
      : "Opening moment...";

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <IconButton
          icon={<Ionicons name="chevron-back" size={18} color={palette.fg} />}
          onPress={() => router.back()}
        />
        <View style={styles.headerTitleWrap}>
          <Text style={styles.kicker}>Profile</Text>
          <Text style={styles.title}>Reflection</Text>
        </View>
        <IconButton
          icon={<Ionicons name="refresh-outline" size={18} color={palette.fg} />}
          onPress={() => void loadTopics()}
        />
      </View>

      <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        <View style={styles.glassCard}>
          <Text style={styles.cardTitle}>Life Occupancy</Text>
          <Text style={styles.cardSubtitle}>
            Bubble size reflects how much each thread has occupied your attention in the last {MOBILE_CONTINUITY_PLAN.continuityDays} days.
          </Text>
          <View style={styles.planBadge}>
            <Text style={styles.planBadgeText}>
              {MOBILE_CONTINUITY_PLAN.badge} · {MOBILE_CONTINUITY_PLAN.title}
            </Text>
          </View>

          {loadingTopics ? (
            <View style={styles.loadingRow}>
              <LoadingBlock
                style={styles.loadingBlock}
                lines={["92%", "76%", "68%"]}
                lineHeight={12}
              />
            </View>
          ) : topics.length === 0 ? (
            <Text style={styles.emptyText}>
              No topic arcs yet in your active {MOBILE_CONTINUITY_PLAN.continuityDays}-day window. Add more conversation turns and return here.
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
                          ? theme.colors.accentSoft
                          : `rgba(255, 255, 255, ${0.05 + weight * 0.12})`,
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

        <View style={styles.glassCard}>
          <Text style={styles.cardTitle}>My Story</Text>
          <Text style={styles.cardSubtitle}>
            Cross-context reflection across your active topics from the last {MOBILE_CONTINUITY_PLAN.continuityDays} days.
          </Text>
          <View style={styles.storyActionBlock}>
            <Pressable
              style={[
                styles.deepReflectButton,
                (!myStoryReady || meStoryLoading || loadingTopics) && styles.deepReflectButtonDisabled,
              ]}
              onPress={() => void runMeStory()}
              disabled={!myStoryReady || meStoryLoading || loadingTopics}
            >
              {meStoryLoading ? (
                <View style={styles.deepReflectButtonContent}>
                  <ActivityIndicator size="small" color={palette.accentText} />
                  <Text style={styles.deepReflectButtonText}>Building My Story...</Text>
                </View>
              ) : (
                <View style={styles.deepReflectButtonContent}>
                  <Ionicons name="sparkles" size={15} color={palette.accentText} />
                  <Text style={styles.deepReflectButtonText}>My Story</Text>
                </View>
              )}
            </Pressable>
            {!myStoryReady ? (
              <Text style={styles.depthHint}>{myStoryUnlockHint}</Text>
            ) : null}
          </View>
          {meStoryError ? <Text style={styles.errorText}>{meStoryError}</Text> : null}
          {meStoryText ? <Text style={styles.deepReflectText}>{meStoryText}</Text> : null}
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
            <View style={styles.header}>
              <IconButton
                icon={<Ionicons name="chevron-back" size={18} color={palette.fg} />}
                onPress={closeThread}
              />
              <View style={styles.headerTitleWrap}>
                <Text style={styles.kicker}>Reflection</Text>
                <Text style={styles.title}>{threadLabel}</Text>
              </View>
              <IconButton
                icon={<Ionicons name="refresh-outline" size={18} color={palette.fg} />}
                onPress={() => void loadArc(selectedAnchor)}
              />
            </View>

            <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
              <View style={styles.glassCard}>
                <View style={styles.arcHeader}>
                  <View>
                    <Text style={styles.cardTitle}>Continuity Arc</Text>
                    <Text style={styles.cardSubtitle}>
                      {moments.length > 0
                        ? "Tap the moments callout to explore. Run Topic Story for insight labels."
                        : "No moments yet for this thread."}
                    </Text>
                  </View>
                  {loadingArc && <ActivityIndicator size="small" color={palette.muted} />}
                </View>

                {!loadingArc && moments.length === 0 ? null : (
                  <ArcScrollView
                    moments={moments}
                    phases={arc?.arc?.phases || []}
                    arcLabels={arcLabels}
                    arcLabelsLoading={deepReflectLoading}
                    topicLabel={threadLabel}
                    spanDays={toFiniteNumber(arc?.arc?.span_days, 0)}
                    onMomentPress={openMoment}
                  />
                )}
              </View>

              <View style={styles.glassCard}>
                <Pressable
                  style={[
                    styles.deepReflectButton,
                    (!topicStoryReady || deepReflectLoading) && styles.deepReflectButtonDisabled,
                  ]}
                  onPress={() => void runDeepReflect()}
                  disabled={!topicStoryReady || deepReflectLoading}
                >
                  {deepReflectLoading ? (
                    <View style={styles.deepReflectButtonContent}>
                      <ActivityIndicator size="small" color={palette.accentText} />
                      <Text style={styles.deepReflectButtonText}>Building Story...</Text>
                    </View>
                  ) : (
                    <View style={styles.deepReflectButtonContent}>
                      <Ionicons name="sparkles" size={15} color={palette.accentText} />
                      <Text style={styles.deepReflectButtonText}>{`${threadLabel} Story`}</Text>
                    </View>
                  )}
                </Pressable>
                {!topicStoryReady ? (
                  <Text style={styles.depthHint}>{`${threadLabel} needs more depth for a story...`}</Text>
                ) : null}
                {deepReflectError ? <Text style={styles.errorText}>{deepReflectError}</Text> : null}
                {deepReflectText ? <Text style={styles.deepReflectText}>{deepReflectText}</Text> : null}
              </View>
            </ScrollView>
            {(loadingArc || momentOpening || deepReflectLoading) ? (
              <View style={styles.threadLoadingOverlay}>
                <LoadingBlock
                  warm
                  lineHeight={14}
                  lines={["78%", "64%"]}
                  style={styles.threadLoadingBlock}
                />
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
                <ActivityIndicator size="small" color={palette.accentText} />
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
  bg: theme.colors.bg,
  fg: theme.colors.text,
  muted: theme.colors.textMuted,
  border: theme.colors.border,
  glass: theme.colors.surface,
  accent: theme.colors.accent,
  accentText: theme.colors.accentText,
  accentBorder: theme.colors.accentBorder,
  accentSoft: theme.colors.accentSoft,
  deepBubble: theme.colors.deepBubble,
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
    backgroundColor: theme.colors.surfaceMuted,
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
  planBadge: {
    alignSelf: "flex-start",
    marginTop: 12,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: theme.colors.borderStrong,
    backgroundColor: theme.colors.surfaceMuted,
    paddingHorizontal: 10,
    paddingVertical: 6,
  },
  planBadgeText: {
    color: palette.accentText,
    fontSize: 11,
    fontWeight: "700",
    letterSpacing: 0.2,
  },
  loadingRow: {
    paddingVertical: 22,
    alignItems: "stretch",
  },
  loadingBlock: {
    width: "100%",
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
    borderColor: palette.accentBorder,
  },
  topicLabel: {
    color: palette.fg,
    fontSize: 13,
    textAlign: "center",
    fontWeight: "600",
  },
  topicShare: {
    color: palette.accentText,
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
    borderColor: theme.colors.borderStrong,
    backgroundColor: theme.colors.surfaceMuted,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  monthReflectorText: {
    color: palette.accentText,
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
    borderColor: theme.colors.borderStrong,
    backgroundColor: theme.colors.surfaceMuted,
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
    color: palette.accentText,
    fontSize: 12,
    fontWeight: "600",
    letterSpacing: 0.3,
  },
  momentDatePill: {
    borderRadius: 999,
    borderWidth: 1,
    borderColor: theme.colors.borderStrong,
    backgroundColor: theme.colors.surfaceMuted,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  momentDate: {
    color: palette.accentText,
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
    color: palette.muted,
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
    borderColor: theme.colors.borderStrong,
    backgroundColor: theme.colors.surfaceMuted,
    paddingHorizontal: 10,
    paddingVertical: 4,
    marginTop: 8,
    marginBottom: 8,
  },
  monthStickyText: {
    color: palette.accentText,
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
    borderColor: theme.colors.borderStrong,
    backgroundColor: theme.colors.surfaceMuted,
    paddingHorizontal: 10,
    paddingVertical: 9,
    marginBottom: 8,
    alignSelf: "flex-start",
  },
  photoDate: {
    color: palette.accentText,
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
    borderColor: palette.accentBorder,
    backgroundColor: palette.deepBubble,
    paddingVertical: 12,
    paddingHorizontal: 14,
    alignItems: "center",
    justifyContent: "center",
    shadowColor: "#506381",
    shadowOpacity: 0.32,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 6 },
  },
  storyActionBlock: {
    marginTop: 14,
    gap: 8,
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
    color: palette.accentText,
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
    backgroundColor: "rgba(8, 13, 24, 0.68)",
    alignItems: "center",
    justifyContent: "center",
    gap: 10,
  },
  threadLoadingBlock: {
    width: 180,
  },
  threadLoadingText: {
    color: palette.accentText,
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
    borderColor: theme.colors.borderStrong,
    backgroundColor: theme.colors.surfaceStrong,
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
    color: palette.accentText,
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
    color: palette.accentText,
    fontSize: 13,
    lineHeight: 20,
    marginTop: 12,
  },
  momentClose: {
    marginTop: 16,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: theme.colors.borderStrong,
    alignItems: "center",
    paddingVertical: 9,
    backgroundColor: theme.colors.surfaceMuted,
  },
  momentCloseText: {
    color: palette.fg,
    fontSize: 13,
    fontWeight: "600",
  },
});

const arcPalette = {
  fg: theme.colors.text,
  muted: theme.colors.textMuted,
  border: theme.colors.border,
  borderStrong: theme.colors.borderStrong,
  surface: theme.colors.surfaceMuted,
  accent: theme.colors.accent,
  accentText: theme.colors.accentText,
  accentSoft: theme.colors.accentSoft,
};

const arcStyles = StyleSheet.create({
  container: {
    marginTop: 16,
    paddingHorizontal: 4,
  },
  node: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 12,
  },
  nodeMarker: {
    width: 20,
    alignItems: "center",
    paddingTop: 3,
  },
  nodeDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: arcPalette.muted,
    borderWidth: 2,
    borderColor: arcPalette.border,
  },
  nodeDotAccent: {
    backgroundColor: arcPalette.accent,
    borderColor: arcPalette.accentSoft,
  },
  nodeContent: {
    flex: 1,
    paddingBottom: 4,
  },
  nodeKicker: {
    color: arcPalette.muted,
    fontSize: 10,
    letterSpacing: 1.1,
    textTransform: "uppercase",
    marginBottom: 4,
  },
  nodeLabel: {
    color: arcPalette.fg,
    fontSize: 14,
    lineHeight: 20,
    fontWeight: "500",
  },
  skeletonLine: {
    height: 14,
    width: "75%",
    borderRadius: 6,
    backgroundColor: arcPalette.surface,
    marginTop: 2,
  },
  connectorColumn: {
    flexDirection: "column",
    alignItems: "stretch",
    gap: 0,
  },
  connectorLine: {
    width: 1,
    height: 18,
    backgroundColor: arcPalette.border,
    alignSelf: "flex-start",
  },
  countPill: {
    alignSelf: "stretch",
    marginHorizontal: 0,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: arcPalette.borderStrong,
    backgroundColor: arcPalette.surface,
    paddingHorizontal: 14,
    paddingVertical: 10,
    marginVertical: 4,
  },
  countPillInner: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  countPillCount: {
    color: arcPalette.accentText,
    fontSize: 13,
    fontWeight: "600",
  },
  countPillSpan: {
    color: arcPalette.muted,
    fontSize: 12,
    flex: 1,
  },
  countPillChevron: {
    width: 18,
    height: 18,
    borderRadius: 9,
    borderWidth: 1,
    borderColor: arcPalette.borderStrong,
    alignItems: "center",
    justifyContent: "center",
  },
  countPillLast: {
    borderColor: arcPalette.accent,
    backgroundColor: arcPalette.accentSoft,
  },
  phaseLabel: {
    color: arcPalette.fg,
    fontSize: 13,
    fontWeight: "600",
    letterSpacing: 0.1,
  },
  phaseLabelAccent: {
    color: arcPalette.accentText,
  },
  noMomentsHint: {
    color: arcPalette.muted,
    fontSize: 12,
    fontStyle: "italic",
    paddingHorizontal: 14,
    paddingVertical: 8,
  },
  bridgeText: {
    color: arcPalette.muted,
    fontSize: 12,
    lineHeight: 17,
    marginTop: 6,
    fontStyle: "italic",
  },
  expandedMoments: {
    gap: 8,
    paddingVertical: 8,
    width: "100%",
  },
  arcMomentCard: {
    borderRadius: 16,
    borderWidth: 1,
    borderColor: arcPalette.borderStrong,
    backgroundColor: arcPalette.surface,
    paddingHorizontal: 14,
    paddingVertical: 12,
    gap: 6,
  },
  arcMomentHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  arcMomentIndex: {
    color: arcPalette.muted,
    fontSize: 11,
    letterSpacing: 0.3,
  },
  arcMomentDate: {
    color: arcPalette.accentText,
    fontSize: 11,
    fontWeight: "600",
  },
  arcMomentSnippet: {
    color: arcPalette.fg,
    fontSize: 13,
    lineHeight: 19,
  },
  arcMomentFacet: {
    color: arcPalette.muted,
    fontSize: 11,
    textTransform: "capitalize",
  },
});
