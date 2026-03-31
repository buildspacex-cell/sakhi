import React, { useState, useEffect, useRef, useCallback, useMemo } from "react";
import {
  View,
  Text,
  TextInput,
  Pressable,
  Modal,
  ScrollView,
  StyleSheet,
  SafeAreaView,
  StatusBar,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
} from "react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { useAuth } from "../../../lib/auth/AuthContext";
import { config } from "../../../lib/config";
import { trackSupportDebugEvent, type SupportDebugEventInput } from "../../../lib/support/debugTelemetry";
import { Analytics } from "../../../lib/analytics/events";
import { theme } from "../../../lib/theme/tokens";
import { useAppPreferences } from "../../../lib/preferences/AppPreferencesContext";
import { useAppHaptics } from "../../../lib/feedback/useAppHaptics";
import { LoadingBlock } from "../../../components/ui/LoadingBlock";

interface Message {
  id: string;
  role: "user" | "sakhi";
  content: string;
  timestamp: Date;
  kind?: "normal" | "deep" | "system";
}

interface HistoryMessagePayload {
  id?: string;
  role?: string;
  content?: string;
  created_at?: string | null;
}

interface DeepReflectSignal {
  ready: boolean;
  reason: string;
  mirror_allowed: boolean;
  detail_allowed: boolean;
  selected_count: number;
  min_moments: number;
}

interface WholeStorySignal {
  ready: boolean;
  reason: string;
  selected_topics: string[];
  selected_count_total: number;
  correlation_score: number;
}

interface ContinuitySignal {
  topic_key: string;
  topic_label?: string;
  deep_reflect?: DeepReflectSignal;
  whole_story?: WholeStorySignal;
}

const BACKEND_URL = (config.backendUrl || "").replace(/\/+$/, "");
const DEEP_POLL_INTERVAL_MS = 2000;
const DEEP_POLL_MAX_ATTEMPTS = 70;

function toNumber(value: unknown, fallback = 0): number {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function toContinuitySignal(raw: unknown): ContinuitySignal | null {
  if (!raw || typeof raw !== "object") return null;
  const data = raw as Record<string, unknown>;
  const topicKey = String(data.topic_key || "").trim();
  if (!topicKey) return null;

  const deepRaw = data.deep_reflect;
  const deep = deepRaw && typeof deepRaw === "object" ? (deepRaw as Record<string, unknown>) : null;
  const wholeRaw = data.whole_story;
  const whole = wholeRaw && typeof wholeRaw === "object" ? (wholeRaw as Record<string, unknown>) : null;
  const selectedTopics = Array.isArray(whole?.selected_topics)
    ? whole?.selected_topics
        .map((item) => String(item || "").trim().toLowerCase().replace(/\s+/g, "_"))
        .filter(Boolean)
    : [];

  return {
    topic_key: topicKey,
    topic_label: String(data.topic_label || "").trim() || undefined,
    deep_reflect: deep
      ? {
          ready: Boolean(deep.ready),
          reason: String(deep.reason || "unknown").trim() || "unknown",
          mirror_allowed: Boolean(deep.mirror_allowed),
          detail_allowed: Boolean(deep.detail_allowed),
          selected_count: toNumber(deep.selected_count, 0),
          min_moments: Math.max(1, toNumber(deep.min_moments, 8)),
        }
      : undefined,
    whole_story: whole
      ? {
          ready: Boolean(whole.ready),
          reason: String(whole.reason || "unknown").trim() || "unknown",
          selected_topics: selectedTopics,
          selected_count_total: Math.max(0, toNumber(whole.selected_count_total, 0)),
          correlation_score: toNumber(whole.correlation_score, 0),
        }
      : undefined,
  };
}

function formatDeepReflectionResult(payload: Record<string, unknown>): string {
  const result = (payload.result as Record<string, unknown> | undefined) || {};
  const chatResponse = String(result.chat_response || "").trim();
  if (chatResponse) {
    return chatResponse;
  }

  const topicLabel = String(result.topic_label || payload.topic_key || "this thread");
  const lines: string[] = [`Whole story on ${topicLabel}:`];

  const originStory = String(result.origin_story || "").trim();
  const keyPivots = Array.isArray(result.key_pivots) ? result.key_pivots : [];
  const currentStage = String(result.current_stage || "").trim();

  if (originStory) lines.push(`Start: ${originStory}`);
  if (typeof keyPivots[0] === "string" && keyPivots[0].trim()) {
    lines.push(`Shift: ${keyPivots[0].trim()}`);
  }
  if (currentStage) lines.push(`Now: ${currentStage}`);

  return lines.join("\n");
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export default function ConversationScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ user?: string; name?: string }>();
  const { user, session, signOut, isLoading: isAuthLoading } = useAuth();
  const { preferences } = useAppPreferences();
  const haptics = useAppHaptics();
  const scrollViewRef = useRef<ScrollView>(null);
  const debugSequenceRef = useRef(0);
  const loadedHistoryForPersonRef = useRef<string | null>(null);

  const [messages, setMessages] = useState<Message[]>([]);
  const [isHistoryLoading, setIsHistoryLoading] = useState(true);
  const [inputText, setInputText] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [isRunningDeepAnswer, setIsRunningDeepAnswer] = useState(false);
  const [, setDeepReflectionStatus] = useState("");
  const [activeContinuitySignal, setActiveContinuitySignal] = useState<ContinuitySignal | null>(null);
  const [latestUserMessage, setLatestUserMessage] = useState("");
  const [accountMenuVisible, setAccountMenuVisible] = useState(false);
  const [isSigningOut, setIsSigningOut] = useState(false);

  const routePersonId = typeof params.user === "string" ? params.user.trim() : "";
  const routeName = typeof params.name === "string" ? params.name.trim() : "";
  const personId = user?.personId || routePersonId;
  const authToken = session?.access_token || "";
  const backendConfigured = BACKEND_URL.length > 0;

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

  useEffect(() => {
    emitDebugEvent({
      type: "screen_view",
      name: "chat_opened",
      screen: "chat",
      route: "/mobile/chat",
      metadata: { has_messages: messages.length > 0 },
    });
    // fire once on screen mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (messages.length > 0) {
      setTimeout(() => {
        scrollViewRef.current?.scrollToEnd({ animated: true });
      }, 120);
    }
  }, [messages]);

  useEffect(() => {
    if (isAuthLoading) {
      return;
    }
    if (!personId || !BACKEND_URL) {
      setIsHistoryLoading(false);
      return;
    }
    if (loadedHistoryForPersonRef.current === personId) {
      setIsHistoryLoading(false);
      return;
    }

    let cancelled = false;
    setIsHistoryLoading(true);

    const loadHistory = async () => {
      try {
        const params = new URLSearchParams({
          user: personId,
          // TODO: support multi-session thread selection instead of the fixed converse slug.
          session_slug: "converse",
          limit: "20",
        });
        const response = await fetch(`${BACKEND_URL}/v2/conversation/history?${params.toString()}`, {
          headers: authToken ? { Authorization: `Bearer ${authToken}` } : undefined,
        });
        if (!response.ok) {
          return;
        }

        const payload = (await response.json()) as { messages?: HistoryMessagePayload[] };
        const historyMessages = Array.isArray(payload.messages) ? payload.messages : [];
        const mappedMessages = historyMessages
          .map((message): Message | null => {
            const role = message.role === "sakhi" || message.role === "assistant"
              ? "sakhi"
              : message.role === "user"
                ? "user"
                : null;
            const content = String(message.content || "").trim();
            if (!role || !content) {
              return null;
            }

            return {
              id: String(message.id || `${role}-${content.slice(0, 12)}`),
              role,
              content,
              timestamp: message.created_at ? new Date(message.created_at) : new Date(),
              kind: "normal",
            };
          })
          .filter((message): message is Message => Boolean(message));

        if (cancelled) {
          return;
        }

        loadedHistoryForPersonRef.current = personId;
        setMessages((current) => (current.length === 0 ? mappedMessages : current));
      } catch {
        // Gracefully fall back to the empty state if history cannot be loaded.
      } finally {
        if (!cancelled) {
          setIsHistoryLoading(false);
        }
      }
    };

    void loadHistory();

    return () => {
      cancelled = true;
    };
  }, [authToken, isAuthLoading, personId]);

  const deepReflectSignal = activeContinuitySignal?.deep_reflect;
  const wholeStorySignal = activeContinuitySignal?.whole_story;
  const wholeStoryTopics = useMemo(
    () => wholeStorySignal?.selected_topics || [],
    [wholeStorySignal?.selected_topics],
  );
  const wholeStorySelectedTopics = useMemo(() => {
    const primary = activeContinuitySignal?.topic_key || "";
    const normalized = wholeStoryTopics
      .map((topic) => String(topic || "").trim())
      .filter(Boolean);
    if (primary && !normalized.includes(primary)) {
      normalized.unshift(primary);
    }
    return normalized.slice(0, 3);
  }, [activeContinuitySignal?.topic_key, wholeStoryTopics]);
  const linkedWholeStoryReady = Boolean(
    wholeStorySignal?.ready && wholeStorySelectedTopics.length >= 2,
  );
  const deepReflectReady = Boolean(deepReflectSignal?.ready);
  const hasDeepQuery = latestUserMessage.trim().length > 0;
  const deepAnswerReady = Boolean(
    activeContinuitySignal?.topic_key && hasDeepQuery && deepReflectReady,
  );

  const prevDeepReadyRef = useRef(false);
  useEffect(() => {
    if (deepAnswerReady && !prevDeepReadyRef.current) {
      Analytics.deepButtonShown({ mode: "whole_story" });
    }
    prevDeepReadyRef.current = deepAnswerReady;
  }, [deepAnswerReady]);

  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return "Good morning";
    if (hour < 17) return "Good afternoon";
    return "Good evening";
  };

  const displayName = user?.fullName?.split(" ")[0] || routeName.split(" ")[0] || "";

  const ensureContinuityPolicyEnabled = useCallback(async () => {
    if (!personId) return;
    try {
      await fetch(`${BACKEND_URL}/continuity/policy/enable`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
        },
        body: JSON.stringify({ person_id: personId }),
      });
    } catch (err) {
      console.warn("[continuity] policy enable probe failed:", err);
    }
  }, [authToken, personId]);

  useEffect(() => {
    void ensureContinuityPolicyEnabled();
  }, [ensureContinuityPolicyEnabled]);

  const pollDeepAnswer = useCallback(
    async (reflectionId: string, person: string): Promise<string | null> => {
      const fetchResult = async (): Promise<string | null> => {
        const params = new URLSearchParams({ id: reflectionId, person_id: person, t: String(Date.now()) });
        const resultRes = await fetch(`${BACKEND_URL}/continuity/reflection/result?${params.toString()}`, {
          cache: "no-store",
          headers: authToken ? { Authorization: `Bearer ${authToken}` } : undefined,
        });
        if (!resultRes.ok) return null;
        const resultData = (await resultRes.json()) as Record<string, unknown>;
        if (String(resultData.status || "queued") !== "done") return null;
        return formatDeepReflectionResult(resultData);
      };

      for (let attempt = 0; attempt < DEEP_POLL_MAX_ATTEMPTS; attempt += 1) {
        try {
          const statusParams = new URLSearchParams({ id: reflectionId, person_id: person, t: String(Date.now()) });
          const statusRes = await fetch(`${BACKEND_URL}/continuity/reflection/status?${statusParams.toString()}`, {
            cache: "no-store",
            headers: authToken ? { Authorization: `Bearer ${authToken}` } : undefined,
          });
          if (!statusRes.ok) break;
          const statusData = (await statusRes.json()) as Record<string, unknown>;
          const status = String(statusData.status || "queued");
          setDeepReflectionStatus(status);

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
          console.error("[deep-answer] poll error", err);
          break;
        }

        await sleep(DEEP_POLL_INTERVAL_MS);
      }

      try {
        return await fetchResult();
      } catch {
        return null;
      }
    },
    [authToken],
  );

  const sendMessage = useCallback(async () => {
    const text = inputText.trim();
    if (!text || !personId) return;
    haptics.press();
    if (!backendConfigured) {
      setMessages((prev) => [
        ...prev,
        {
          id: `config-error-${Date.now()}`,
          role: "sakhi",
          content: "This build is missing EXPO_PUBLIC_BACKEND_URL. Ask the team to update the app configuration.",
          timestamp: new Date(),
          kind: "system",
        },
      ]);
      return;
    }
    Analytics.messageSent();
    emitDebugEvent({
      type: "action",
      name: "send_message_pressed",
      screen: "chat",
      metadata: { input_length: text.length },
    });

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: "user",
      content: text,
      timestamp: new Date(),
      kind: "normal",
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputText("");
    setIsSending(true);
    setLatestUserMessage(text);

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 30000);
    const requestStartMs = Date.now();
    emitDebugEvent({
      type: "api_start",
      name: "turn_v2",
      screen: "chat",
      route: "/v2/turn",
      method: "POST",
      metadata: { source: "chat_send" },
    });

    try {
      const url = `${BACKEND_URL}/v2/turn?user=${encodeURIComponent(personId)}`;
      const res = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
        },
        body: JSON.stringify({ text, source: "text" }),
        signal: controller.signal,
      });

      clearTimeout(timeout);
      emitDebugEvent({
        type: "api_end",
        name: "turn_v2",
        screen: "chat",
        route: "/v2/turn",
        method: "POST",
        status: res.status,
        latencyMs: Date.now() - requestStartMs,
        requestId: res.headers.get("x-request-id") || undefined,
        metadata: { ok: res.ok },
      });

      if (res.ok) {
        const data = await res.json();
        Analytics.turnCompleted({
          latency_ms: Date.now() - requestStartMs,
          status: res.status,
          request_id: res.headers.get("x-request-id") || undefined,
          has_continuity: Boolean(data.continuity?.topic_key),
        });
        setActiveContinuitySignal(toContinuitySignal(data.continuity));

        if (data.reply) {
          const sakhiMessage: Message = {
            id: `sakhi-${Date.now()}`,
            role: "sakhi",
            content: data.reply,
            timestamp: new Date(),
            kind: "normal",
          };
          setMessages((prev) => [...prev, sakhiMessage]);
        }
      } else {
        const statusText = await res.text().catch(() => "");
        const sakhiMessage: Message = {
          id: `error-${Date.now()}`,
          role: "sakhi",
          content: `Something went wrong (${res.status}). Try again.`,
          timestamp: new Date(),
          kind: "system",
        };
        setMessages((prev) => [...prev, sakhiMessage]);
        Analytics.turnFailed({
          status: res.status,
          latency_ms: Date.now() - requestStartMs,
          reason: "http_error",
          request_id: res.headers.get("x-request-id") || undefined,
        });
        emitDebugEvent({
          type: "ui_error",
          name: "turn_http_error",
          screen: "chat",
          route: "/v2/turn",
          method: "POST",
          status: res.status,
          latencyMs: Date.now() - requestStartMs,
        });
        console.error(`[turn] HTTP ${res.status}: ${statusText.slice(0, 200)}`);
      }
    } catch (err: unknown) {
      clearTimeout(timeout);
      emitDebugEvent({
        type: "api_end",
        name: "turn_v2",
        screen: "chat",
        route: "/v2/turn",
        method: "POST",
        status: 0,
        latencyMs: Date.now() - requestStartMs,
        metadata: {
          aborted: err instanceof Error && err.name === "AbortError",
        },
      });
      const isTimeout = err instanceof Error && err.name === "AbortError";
      Analytics.turnFailed({
        status: 0,
        latency_ms: Date.now() - requestStartMs,
        reason: isTimeout ? "timeout" : "network",
      });
      const errorMsg = isTimeout
        ? "That took too long. Try again - sometimes the first message is slow."
        : `Connection issue: ${err instanceof Error ? err.message : "unknown"}`;
      const sakhiMessage: Message = {
        id: `error-${Date.now()}`,
        role: "sakhi",
        content: errorMsg,
        timestamp: new Date(),
        kind: "system",
      };
      setMessages((prev) => [...prev, sakhiMessage]);
      emitDebugEvent({
        type: "ui_error",
        name: isTimeout ? "turn_timeout" : "turn_fetch_error",
        screen: "chat",
        route: "/v2/turn",
        method: "POST",
      });
      console.error("[turn] fetch error:", err);
    } finally {
      setIsSending(false);
    }
  }, [authToken, backendConfigured, emitDebugEvent, haptics, inputText, personId]);

  const handleRunDeepAnswer = useCallback(async () => {
    if (
      !personId
      || !activeContinuitySignal?.topic_key
      || !hasDeepQuery
      || !deepAnswerReady
      || isRunningDeepAnswer
    ) {
      return;
    }
    const mode = "whole_story";
    const selectedTopics = wholeStorySelectedTopics;
    const pendingMessage = linkedWholeStoryReady
      ? "Deep Reflect is reading your whole story across linked threads..."
      : "Deep Reflect is reading the full story of this thread...";

    const pendingId = `deep-pending-${Date.now()}`;
    haptics.strongPress();
    Analytics.deepStarted({ mode });
    emitDebugEvent({
      type: "action",
      name: "run_deep_pressed",
      screen: "chat",
      route: "/continuity/reflection/run",
      method: "POST",
      metadata: {
        mode,
        selected_topics: selectedTopics.length,
      },
    });
    setIsRunningDeepAnswer(true);
    setDeepReflectionStatus("queued");
    setMessages((prev) => [
      ...prev,
      {
        id: pendingId,
        role: "sakhi",
        content: pendingMessage,
        timestamp: new Date(),
        kind: "system",
      },
    ]);

    const removePending = () => {
      setMessages((prev) => prev.filter((msg) => msg.id !== pendingId));
    };

    try {
      const deepStartMs = Date.now();
      emitDebugEvent({
        type: "api_start",
        name: "run_whole_story",
        screen: "chat",
        route: "/continuity/reflection/run",
        method: "POST",
      });
      const res = await fetch(`${BACKEND_URL}/continuity/reflection/run`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
        },
        body: JSON.stringify({
          person_id: personId,
          topic_key: activeContinuitySignal.topic_key,
          window: "3650d",
          mode,
          topic_keys: selectedTopics,
          user_query: latestUserMessage.trim(),
        }),
      });
      emitDebugEvent({
        type: "api_end",
        name: "run_whole_story",
        screen: "chat",
        route: "/continuity/reflection/run",
        method: "POST",
        status: res.status,
        latencyMs: Date.now() - deepStartMs,
        requestId: res.headers.get("x-request-id") || undefined,
        metadata: { ok: res.ok },
      });

      if (!res.ok) {
        throw new Error(`Deep answer request failed (${res.status})`);
      }

      const data = (await res.json()) as Record<string, unknown>;
      const reflectionId = String(data.reflection_id || "");
      if (!reflectionId) {
        throw new Error("Deep answer response missing reflection id");
      }

      const deepReply = await pollDeepAnswer(reflectionId, personId);
      removePending();

      if (deepReply) {
        Analytics.deepCompleted({
          mode: "whole_story",
          latency_ms: Date.now() - deepStartMs,
          request_id: res.headers.get("x-request-id") || undefined,
        });
        setMessages((prev) => [
          ...prev,
          {
            id: `deep-${Date.now()}`,
            role: "sakhi",
            content: deepReply,
            timestamp: new Date(),
            kind: "deep",
          },
        ]);
      } else {
        emitDebugEvent({
          type: "ui_error",
          name: "deep_reflect_incomplete",
          screen: "chat",
          route: "/continuity/reflection/status",
        });
        setMessages((prev) => [
          ...prev,
          {
            id: `deep-fail-${Date.now()}`,
            role: "sakhi",
            content: "Deep Reflect did not complete this time. Please try again.",
            timestamp: new Date(),
            kind: "system",
          },
        ]);
      }
    } catch (err) {
      removePending();
      emitDebugEvent({
        type: "ui_error",
        name: "deep_reflect_run_failed",
        screen: "chat",
        route: "/continuity/reflection/run",
        method: "POST",
      });
      setMessages((prev) => [
        ...prev,
        {
          id: `deep-error-${Date.now()}`,
          role: "sakhi",
          content: "Could not run Deep Reflect right now.",
          timestamp: new Date(),
          kind: "system",
        },
      ]);
      console.error("[deep-answer] run error", err);
    } finally {
      setIsRunningDeepAnswer(false);
      setDeepReflectionStatus("");
    }
  }, [
    activeContinuitySignal?.topic_key,
    authToken,
    hasDeepQuery,
    isRunningDeepAnswer,
    latestUserMessage,
    personId,
    pollDeepAnswer,
    linkedWholeStoryReady,
    wholeStorySelectedTopics,
    emitDebugEvent,
    haptics,
  ]);

  const handleSignOut = async () => {
    if (isSigningOut) return;
    haptics.warning();
    setAccountMenuVisible(false);
    setIsSigningOut(true);
    try {
      await signOut();
    } finally {
      setIsSigningOut(false);
    }
  };

  const openAccountRoute = useCallback(
    (path: string) => {
      haptics.selection();
      setAccountMenuVisible(false);
      router.push(path as never);
    },
    [haptics, router],
  );

  const hasMessages = messages.length > 0;

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" />

      <View style={styles.header}>
        <View style={styles.headerLeft}>
          <Text style={styles.brand}>Sakhi</Text>
          <Text style={styles.greeting}>
            {getGreeting()}
            {displayName ? `, ${displayName}` : ""}
          </Text>
        </View>
        <Pressable
          style={styles.accountTrigger}
          onPress={() => {
            haptics.selection();
            setAccountMenuVisible(true);
          }}
          hitSlop={12}
        >
          <Ionicons name="person-circle-outline" size={16} color={palette.fg} />
          <Text style={styles.accountTriggerText}>Profile</Text>
          <Ionicons name="chevron-down" size={14} color={palette.muted} />
        </Pressable>
      </View>

      <KeyboardAvoidingView
        style={styles.keyboardView}
        behavior={Platform.OS === "ios" ? "padding" : "height"}
        keyboardVerticalOffset={0}
      >
        <ScrollView
          ref={scrollViewRef}
          style={styles.messagesArea}
          contentContainerStyle={[styles.messagesContent, !hasMessages && styles.messagesContentEmpty]}
          showsVerticalScrollIndicator={false}
          keyboardShouldPersistTaps="handled"
        >
          {!hasMessages && !backendConfigured ? (
            <View style={styles.emptyState}>
              <Text style={styles.emptyPrompt}>This build is not configured yet.</Text>
              <Text style={styles.emptyHint}>Set `EXPO_PUBLIC_BACKEND_URL` before sending chat or opening reflection.</Text>
            </View>
          ) : !hasMessages && isHistoryLoading ? (
            <View style={styles.historyLoadingState}>
              <LoadingBlock
                lines={["84%", "66%", "72%"]}
                style={styles.historySkeleton}
                lineHeight={14}
              />
            </View>
          ) : !hasMessages ? (
            <View style={styles.emptyState}>
              <Text style={styles.emptyPrompt}>A clear space to think out loud.</Text>
              <Text style={styles.emptyHint}>Start anywhere. Sakhi keeps context as you talk.</Text>
              <Text style={styles.emptyHint}>Deep Reflect unlocks once your story runs long enough to draw from.</Text>
            </View>
          ) : (
            <>
              {messages.map((msg) => {
                const isUser = msg.role === "user";
                const isSystem = msg.kind === "system";
                const isDeep = msg.kind === "deep";

                return (
                  <View
                    key={msg.id}
                    style={[
                      styles.bubble,
                      preferences.compactMode && styles.bubbleCompact,
                      isUser
                        ? styles.userBubble
                        : isSystem
                            ? styles.systemBubble
                            : isDeep
                                ? styles.deepBubble
                                : styles.sakhiBubble,
                    ]}
                  >
                    {isDeep ? <Text style={styles.deepBadge}>Whole Story</Text> : null}
                    <Text
                      style={[
                        styles.bubbleText,
                        preferences.compactMode && styles.bubbleTextCompact,
                        !isUser && styles.sakhiBubbleText,
                      ]}
                    >
                      {msg.content}
                    </Text>
                  </View>
                );
              })}
              {isSending && (
                <View style={[styles.bubble, styles.systemBubble, { opacity: 0.7 }]}>
                  <ActivityIndicator size="small" color={palette.muted} />
                </View>
              )}
              {deepAnswerReady && !isSending && (
                <Pressable
                  style={[styles.deepInlineCard, isRunningDeepAnswer && styles.deepInlineCardRunning]}
                  onPress={() => void handleRunDeepAnswer()}
                  disabled={isRunningDeepAnswer}
                >
                  {isRunningDeepAnswer ? (
                    <View style={styles.deepInlineContent}>
                      <ActivityIndicator size="small" color={palette.accentText} />
                      <Text style={styles.deepInlineText}>
                        {linkedWholeStoryReady ? "Reading across your threads..." : "Reading your thread..."}
                      </Text>
                    </View>
                  ) : (
                    <View style={styles.deepInlineContent}>
                      <Ionicons name="sparkles" size={13} color={palette.accentText} />
                      <Text style={styles.deepInlineText}>Run Deep</Text>
                    </View>
                  )}
                </Pressable>
              )}
            </>
          )}
        </ScrollView>

        <View style={styles.inputArea}>
          <View style={styles.inputRow}>
            <TextInput
              style={styles.textInput}
              placeholder="What's on your mind?"
              placeholderTextColor={palette.faint}
              value={inputText}
              onChangeText={setInputText}
              onSubmitEditing={sendMessage}
              returnKeyType="send"
              multiline={false}
              editable={!isSending}
            />
            {inputText.trim().length > 0 && (
              <Pressable
                style={[styles.sendButton, isSending && styles.sendButtonDisabled]}
                onPress={sendMessage}
                disabled={isSending}
              >
                <Ionicons name="arrow-up" size={20} color="#ffffff" />
              </Pressable>
            )}
          </View>
        </View>
      </KeyboardAvoidingView>

      <Modal
        visible={accountMenuVisible}
        transparent
        animationType="fade"
        onRequestClose={() => setAccountMenuVisible(false)}
      >
        <Pressable style={styles.accountOverlay} onPress={() => setAccountMenuVisible(false)}>
          <Pressable
            style={styles.accountSheet}
            onPress={(event) => event.stopPropagation()}
          >
            <Text style={styles.accountSheetKicker}>Account Hub</Text>
            <Text style={styles.accountSheetTitle}>
              {displayName ? `${displayName}'s space` : "Your space"}
            </Text>

            <Pressable
              style={styles.accountItem}
              onPress={() => openAccountRoute("/soul/topic-reflection")}
            >
              <View style={styles.accountItemCopy}>
                <Text style={styles.accountItemTitle}>Profile</Text>
                <Text style={styles.accountItemSubtitle}>Reflection and topic story</Text>
              </View>
              <Ionicons name="chevron-forward" size={16} color={palette.muted} />
            </Pressable>

            <Pressable
              style={styles.accountItem}
              onPress={() => openAccountRoute("/account/settings")}
            >
              <View style={styles.accountItemCopy}>
                <Text style={styles.accountItemTitle}>Settings</Text>
                <Text style={styles.accountItemSubtitle}>App, privacy, and account controls</Text>
              </View>
              <Ionicons name="chevron-forward" size={16} color={palette.muted} />
            </Pressable>

            <Pressable
              style={styles.accountItem}
              onPress={() => openAccountRoute("/account/support")}
            >
              <View style={styles.accountItemCopy}>
                <Text style={styles.accountItemTitle}>Report an issue</Text>
                <Text style={styles.accountItemSubtitle}>Something not working? Let us know</Text>
              </View>
              <Ionicons name="chevron-forward" size={16} color={palette.muted} />
            </Pressable>

            <Pressable
              style={[styles.accountItem, styles.accountItemDanger, isSigningOut && { opacity: 0.5 }]}
              onPress={handleSignOut}
              disabled={isSigningOut}
            >
              <View style={styles.accountItemCopy}>
                <Text style={[styles.accountItemTitle, styles.accountItemDangerText]}>
                  {isSigningOut ? "Signing out…" : "Sign out"}
                </Text>
                <Text style={styles.accountItemSubtitle}>End this session on this device</Text>
              </View>
              <Ionicons name="log-out-outline" size={16} color="#ef6f7e" />
            </Pressable>
          </Pressable>
        </Pressable>
      </Modal>
    </SafeAreaView>
  );
}

const palette = {
  bg: theme.colors.bg,
  bgElevated: theme.colors.bgElevated,
  fg: theme.colors.text,
  muted: theme.colors.textMuted,
  subtle: theme.colors.textSubtle,
  faint: theme.colors.textFaint,
  border: theme.colors.border,
  cardBg: theme.colors.surface,
  accent: theme.colors.accent,
  accentText: theme.colors.accentText,
  accentInk: theme.colors.accentInk,
  accentBorder: theme.colors.accentBorder,
  accentSoft: theme.colors.accentSoft,
  userBubble: theme.colors.userBubble,
  sakhiBubble: theme.colors.sakhiBubble,
  deepBubble: theme.colors.deepBubble,
  systemBubble: theme.colors.systemBubble,
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: palette.bg,
  },
  keyboardView: {
    flex: 1,
  },

  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
    paddingVertical: 16,
    paddingHorizontal: 22,
    borderBottomWidth: 1,
    borderBottomColor: palette.border,
  },
  headerLeft: {
    flex: 1,
  },
  brand: {
    fontSize: 12,
    letterSpacing: 1.5,
    textTransform: "uppercase",
    color: palette.muted,
    marginBottom: 4,
  },
  greeting: {
    fontSize: 18,
    fontWeight: "500",
    color: palette.fg,
  },
  accountTrigger: {
    flexDirection: "row",
    alignItems: "center",
    gap: 5,
    paddingVertical: 6,
    paddingHorizontal: 11,
    borderRadius: 999,
    backgroundColor: theme.colors.surfaceMuted,
    borderWidth: 1,
    borderColor: palette.border,
  },
  accountTriggerText: {
    color: palette.fg,
    fontSize: 11,
    fontWeight: "600",
  },
  accountOverlay: {
    flex: 1,
    backgroundColor: "rgba(6, 9, 15, 0.7)",
    justifyContent: "flex-end",
    paddingHorizontal: 14,
    paddingBottom: 20,
  },
  accountSheet: {
    borderRadius: 24,
    borderWidth: 1,
    borderColor: palette.border,
    backgroundColor: theme.colors.surfaceStrong,
    paddingHorizontal: 16,
    paddingVertical: 16,
    gap: 8,
  },
  accountSheetKicker: {
    color: palette.muted,
    textTransform: "uppercase",
    fontSize: 11,
    letterSpacing: 1.1,
  },
  accountSheetTitle: {
    color: palette.fg,
    fontSize: 20,
    fontWeight: "600",
    marginBottom: 2,
  },
  accountItem: {
    minHeight: 68,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: theme.colors.borderStrong,
    backgroundColor: theme.colors.surfaceMuted,
    paddingHorizontal: 14,
    paddingVertical: 10,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 10,
  },
  accountItemCopy: {
    flex: 1,
    gap: 3,
  },
  accountItemTitle: {
    color: palette.fg,
    fontSize: 16,
    fontWeight: "600",
  },
  accountItemSubtitle: {
    color: palette.muted,
    fontSize: 12,
    lineHeight: 17,
  },
  accountItemDanger: {
    borderColor: "rgba(239, 111, 126, 0.35)",
    backgroundColor: "rgba(88, 33, 44, 0.36)",
    marginTop: 3,
  },
  accountItemDangerText: {
    color: "#f8bcc6",
  },

  messagesArea: {
    flex: 1,
  },
  messagesContent: {
    paddingHorizontal: 20,
    paddingTop: 18,
    paddingBottom: 10,
  },
  messagesContentEmpty: {
    flex: 1,
    justifyContent: "center",
  },

  emptyState: {
    alignItems: "center",
    paddingHorizontal: 26,
  },
  historyLoadingState: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    paddingHorizontal: 26,
  },
  historySkeleton: {
    maxWidth: 280,
  },
  emptyPrompt: {
    fontSize: 24,
    color: palette.fg,
    textAlign: "center",
    lineHeight: 34,
    marginBottom: 16,
  },
  emptyHint: {
    fontSize: 14,
    color: palette.muted,
    textAlign: "center",
    lineHeight: 20,
  },

  bubble: {
    maxWidth: "86%",
    marginBottom: 12,
    paddingVertical: 13,
    paddingHorizontal: 15,
    borderRadius: 22,
    borderWidth: 1,
  },
  bubbleCompact: {
    marginBottom: 8,
    paddingVertical: 10,
    paddingHorizontal: 13,
    borderRadius: 18,
  },
  userBubble: {
    alignSelf: "flex-end",
    backgroundColor: palette.userBubble,
    borderColor: theme.colors.borderStrong,
    borderBottomRightRadius: 8,
  },
  sakhiBubble: {
    alignSelf: "flex-start",
    backgroundColor: palette.sakhiBubble,
    borderColor: palette.border,
    borderBottomLeftRadius: 8,
  },
  deepBubble: {
    alignSelf: "flex-start",
    backgroundColor: palette.deepBubble,
    borderColor: palette.accentBorder,
    borderBottomLeftRadius: 8,
  },
  deepInlineCard: {
    alignSelf: "flex-start",
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 12,
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: palette.accentBorder,
    backgroundColor: palette.deepBubble,
    shadowColor: "#506381",
    shadowOpacity: 0.28,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 4 },
  },
  deepInlineCardRunning: {
    opacity: 0.75,
  },
  deepInlineContent: {
    flexDirection: "row",
    alignItems: "center",
    gap: 7,
  },
  deepInlineText: {
    color: palette.accentText,
    fontSize: 13,
    fontWeight: "700",
    letterSpacing: 0.2,
  },
  deepBadge: {
    color: palette.accentText,
    fontSize: 11,
    fontWeight: "700",
    letterSpacing: 0.6,
    marginBottom: 6,
    textTransform: "uppercase",
  },
  systemBubble: {
    alignSelf: "flex-start",
    backgroundColor: palette.systemBubble,
    borderColor: theme.colors.borderStrong,
    borderBottomLeftRadius: 8,
  },
  bubbleText: {
    fontSize: 15,
    color: "#ffffff",
    lineHeight: 22,
  },
  bubbleTextCompact: {
    fontSize: 14,
    lineHeight: 20,
  },
  sakhiBubbleText: {
    color: palette.fg,
  },

  inputArea: {
    paddingHorizontal: 16,
    paddingTop: 10,
    paddingBottom: 28,
    gap: 8,
    borderTopWidth: 1,
    borderTopColor: palette.border,
  },
  deepActionRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  deepInfoPill: {
    flex: 1,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: theme.colors.borderStrong,
    backgroundColor: theme.colors.surfaceMuted,
    paddingVertical: 10,
    paddingHorizontal: 14,
    minHeight: 42,
    justifyContent: "center",
  },
  deepInfoPillReady: {
    borderColor: palette.accentBorder,
    backgroundColor: palette.accentSoft,
  },
  deepInfoText: {
    color: palette.muted,
    fontSize: 12,
    lineHeight: 17,
  },
  deepRunButton: {
    minWidth: 116,
    height: 46,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: palette.accentBorder,
    backgroundColor: palette.deepBubble,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 16,
    shadowColor: "#506381",
    shadowOpacity: 0.32,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 6 },
  },
  deepRunButtonDisabled: {
    opacity: 0.5,
    shadowOpacity: 0.08,
  },
  deepRunButtonContent: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },
  deepRunButtonText: {
    color: palette.accentText,
    fontSize: 14,
    fontWeight: "700",
    letterSpacing: 0.2,
  },
  deepStatusText: {
    color: palette.subtle,
    fontSize: 11,
    paddingHorizontal: 4,
  },
  inputRow: {
    flexDirection: "row",
    alignItems: "center",
    borderRadius: 24,
    borderWidth: 1,
    borderColor: palette.border,
    backgroundColor: palette.cardBg,
    paddingHorizontal: 14,
    paddingVertical: 11,
    minHeight: 50,
  },
  textInput: {
    flex: 1,
    fontSize: 15,
    color: palette.fg,
    paddingVertical: 0,
  },
  sendButton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: palette.accent,
    alignItems: "center",
    justifyContent: "center",
    marginLeft: 8,
  },
  sendButtonDisabled: {
    opacity: 0.55,
  },
});
