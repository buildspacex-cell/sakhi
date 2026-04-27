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
import { useOffload } from "../../../lib/offload/OffloadContext";
import { MOBILE_CONTINUITY_PLAN } from "../../../lib/continuity/plan";
import { useAppHaptics } from "../../../lib/feedback/useAppHaptics";
import { LoadingBlock } from "../../../components/ui/LoadingBlock";
import { SakhiBrandMark } from "../../../components/brand/SakhiBrandMark";

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

interface WhatChangedSignal {
  from: string;
  to: string;
  confidence: number;
  topic_key?: string;
}

interface OpenLoop {
  id: string;
  loop_type: "open_decision" | "conversation_commitment";
  topic: string;
}

interface OpenLoopsData {
  decisions: OpenLoop[];
  commitments: OpenLoop[];
  total: number;
}

interface ContinuitySignal {
  topic_key: string;
  topic_label?: string;
  deep_reflect?: DeepReflectSignal;
  whole_story?: WholeStorySignal;
  what_changed?: WhatChangedSignal;
  open_loops?: OpenLoopsData;
}

interface ContinuationPrompt {
  has_continuation: boolean;
  display?: string;
  topic_key?: string;
  decision_state?: string;
  hours_since?: number;
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

function formatOffloadTimestamp(iso: string): string {
  const created = new Date(iso);
  if (Number.isNaN(created.getTime())) return "";

  const diffMs = Date.now() - created.getTime();
  const minutes = Math.floor(diffMs / 60000);
  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return created.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function getOffloadStatusLabel(status: string): string {
  switch (status) {
    case "saved":
      return "Saved";
    case "saved_offline":
      return "Saved offline";
    case "syncing":
      return "Syncing...";
    case "synced":
      return "Synced";
    case "needs_retry":
      return "Needs retry";
    default:
      return status;
  }
}

function getModeMeta(mode: "talk" | "offload") {
  if (mode === "offload") {
    return {
      title: "Drop it. Sakhi picks it up.",
      backdrop: "offload" as const,
      mode: "offload" as const,
    };
  }

  return {
    title: "A quiet space to stay with what matters.",
    backdrop: "talk" as const,
    mode: "talk" as const,
  };
}

export default function ConversationScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ user?: string; name?: string; mode?: string }>();
  const { user, session, signOut, isLoading: isAuthLoading } = useAuth();
  const { preferences, setLastEntryMode } = useAppPreferences();
  const {
    items: offloadItems,
    connectivity,
    isSyncing: isOffloadSyncing,
    saveOffload,
    syncPending,
  } = useOffload();
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
  const [continuationPrompt, setContinuationPrompt] = useState<ContinuationPrompt | null>(null);
  const [showContinuationCard, setShowContinuationCard] = useState(false);
  const [accountMenuVisible, setAccountMenuVisible] = useState(false);
  const [isSigningOut, setIsSigningOut] = useState(false);
  const [isSavingOffload, setIsSavingOffload] = useState(false);
  const [openLoops, setOpenLoops] = useState<OpenLoopsData | null>(null);
  const [dismissedLoopIds, setDismissedLoopIds] = useState<Set<string>>(new Set());
  const [openLoopsPanelDismissed, setOpenLoopsPanelDismissed] = useState(false);
  const paywallNudgeFiredRef = useRef(false);

  const routePersonId = typeof params.user === "string" ? params.user.trim() : "";
  const routeName = typeof params.name === "string" ? params.name.trim() : "";
  const routeMode = params.mode === "offload" ? "offload" : "talk";
  const personId = user?.personId || routePersonId;
  const authToken = session?.access_token || "";
  const backendConfigured = BACKEND_URL.length > 0;
  const isOffloadMode = routeMode === "offload";

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
    if (preferences.lastEntryMode === routeMode) {
      return;
    }
    setLastEntryMode(routeMode);
  }, [preferences.lastEntryMode, routeMode, setLastEntryMode]);

  useEffect(() => {
    emitDebugEvent({
      type: "screen_view",
      name: isOffloadMode ? "offload_opened" : "chat_opened",
      screen: isOffloadMode ? "offload" : "chat",
      route: isOffloadMode ? "/mobile/offload" : "/mobile/chat",
      metadata: {
        has_messages: isOffloadMode ? offloadItems.length > 0 : messages.length > 0,
      },
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
    if (isOffloadMode) {
      return;
    }
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
  }, [authToken, isAuthLoading, isOffloadMode, personId]);

  useEffect(() => {
    if (!personId || !BACKEND_URL || isOffloadMode || isHistoryLoading) return;
    const fetchPrompt = async () => {
      try {
        const res = await fetch(
          `${BACKEND_URL}/continuity/prompt?person_id=${encodeURIComponent(personId)}`,
          { headers: authToken ? { Authorization: `Bearer ${authToken}` } : undefined },
        );
        if (!res.ok) return;
        const data = (await res.json()) as ContinuationPrompt;
        if (data.has_continuation) {
          setContinuationPrompt(data);
          setShowContinuationCard(true);
        }
      } catch {
        // best-effort
      }
    };
    void fetchPrompt();
  }, [authToken, isHistoryLoading, isOffloadMode, personId]);

  useEffect(() => {
    if (!personId || !BACKEND_URL || isOffloadMode || isHistoryLoading) return;
    const fetchOpenLoops = async () => {
      try {
        const res = await fetch(
          `${BACKEND_URL}/continuity/open-loops?person_id=${encodeURIComponent(personId)}`,
          { headers: authToken ? { Authorization: `Bearer ${authToken}` } : undefined },
        );
        if (!res.ok) return;
        const data = (await res.json()) as OpenLoopsData;
        if ((data.decisions?.length ?? 0) + (data.commitments?.length ?? 0) > 0) {
          setOpenLoops(data);
        }
      } catch {
        // best-effort
      }
    };
    void fetchOpenLoops();
  }, [authToken, isHistoryLoading, isOffloadMode, personId]);

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
    if (isOffloadMode) {
      return;
    }
    void ensureContinuityPolicyEnabled();
  }, [ensureContinuityPolicyEnabled, isOffloadMode]);

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
    setShowContinuationCard(false);
    setOpenLoopsPanelDismissed(true);

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

        if (!paywallNudgeFiredRef.current && BACKEND_URL) {
          try {
            const pwRes = await fetch(
              `${BACKEND_URL}/continuity/paywall-status?person_id=${encodeURIComponent(personId)}`,
              { headers: authToken ? { Authorization: `Bearer ${authToken}` } : undefined },
            );
            if (pwRes.ok) {
              const pw = await pwRes.json();
              if (pw.show_upgrade_cta) {
                paywallNudgeFiredRef.current = true;
                setMessages((prev) => [
                  ...prev,
                  {
                    id: `paywall-${Date.now()}`,
                    role: "sakhi" as const,
                    content: "You've built up real context here. Morning Review and What Changed are part of Sakhi Pro.",
                    timestamp: new Date(),
                    kind: "system" as const,
                  },
                ]);
              }
            }
          } catch {
            // best-effort
          }
        }

        if (data.reply) {
          const sakhiMessage: Message = {
            id: `sakhi-${Date.now()}`,
            role: "sakhi",
            content: data.reply,
            timestamp: new Date(),
            kind: "normal",
          };
          setMessages((prev) => {
            const next = [...prev, sakhiMessage];
            // First-session nudge: at exactly 8 messages (4 exchanges), show return-value hint
            if (next.length === 8) {
              return [
                ...next,
                {
                  id: `nudge-${Date.now()}`,
                  role: "sakhi" as const,
                  content: "I'm tracking where this thinking goes. Come back tomorrow and I'll show you what I noticed.",
                  timestamp: new Date(),
                  kind: "system" as const,
                },
              ];
            }
            return next;
          });
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
      ? "Deep Dive is reading across your linked threads..."
      : "Deep Dive is reading the full history of this thread...";

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
          window: MOBILE_CONTINUITY_PLAN.continuityWindow,
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
            content: "Deep Dive did not complete this time. Please try again.",
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
          content: "Could not run Deep Dive right now.",
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
    deepAnswerReady,
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

  const handleDismissLoop = useCallback((loopId: string) => {
    setDismissedLoopIds((prev) => new Set(Array.from(prev).concat(loopId)));
    if (BACKEND_URL) {
      void fetch(`${BACKEND_URL}/continuity/open-loops/${loopId}/resolve`, {
        method: "POST",
        headers: authToken ? { Authorization: `Bearer ${authToken}` } : undefined,
      });
    }
  }, [authToken]);

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
  const displayName = user?.fullName?.split(" ")[0] || routeName.split(" ")[0] || "";
  const isPrimaryEmpty = isOffloadMode ? offloadItems.length === 0 : !hasMessages;
  const modeMeta = getModeMeta(routeMode);

  const switchMode = useCallback((mode: "talk" | "offload") => {
    if (mode === routeMode) return;
    haptics.selection();
    setLastEntryMode(mode);
    router.replace(`/experience/converse?mode=${mode}` as never);
  }, [haptics, routeMode, router, setLastEntryMode]);

  const handleSaveOffload = useCallback(async () => {
    const text = inputText.trim();
    if (!text || !personId || isSavingOffload) return;
    haptics.press();
    setIsSavingOffload(true);
    try {
      const saved = await saveOffload(text);
      if (saved) {
        emitDebugEvent({
          type: "action",
          name: "offload_saved",
          screen: "offload",
          route: "/mobile/offload",
          metadata: { sync_status: saved.syncStatus, input_length: text.length },
        });
        setInputText("");
        if (saved.syncStatus === "needs_retry") {
          void syncPending();
        }
      }
    } finally {
      setIsSavingOffload(false);
    }
  }, [emitDebugEvent, haptics, inputText, isSavingOffload, personId, saveOffload, syncPending]);

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" />
      <View pointerEvents="none" style={styles.backdropBase}>
        <View
          style={[
            styles.backdropTint,
            modeMeta.backdrop === "talk" ? styles.backdropTintTalk : styles.backdropTintOffload,
          ]}
        />
        <View
          style={[
            styles.backdropGlow,
            modeMeta.backdrop === "talk" ? styles.backdropGlowTalk : styles.backdropGlowOffload,
          ]}
        />
        <View
          style={[
            styles.backdropWash,
            modeMeta.backdrop === "talk" ? styles.backdropWashTalk : styles.backdropWashOffload,
          ]}
        />
      </View>

      <View style={styles.header}>
        <View style={styles.headerLeft}>
          <Text style={styles.brand}>Sakhi</Text>
          <Text style={styles.greeting}>
            {getGreeting()}
            {displayName ? `, ${displayName}` : ""}
          </Text>
          <Text style={styles.headerSubcopy}>{modeMeta.title}</Text>
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

      {!isOffloadMode && connectivity === "offline" ? (
        <View style={styles.noticeBanner}>
          <Text style={styles.noticeBannerText}>
            You are offline. Switch to Drop to save this without a response.
          </Text>
          <Pressable onPress={() => switchMode("offload")}>
            <Text style={styles.noticeBannerAction}>Switch</Text>
          </Pressable>
        </View>
      ) : null}

      {isOffloadMode && isOffloadSyncing ? (
        <View style={styles.noticeBanner}>
          <Text style={styles.noticeBannerText}>Back online. Syncing your drops...</Text>
        </View>
      ) : null}

      <KeyboardAvoidingView
        style={styles.keyboardView}
        behavior={Platform.OS === "ios" ? "padding" : "height"}
        keyboardVerticalOffset={0}
      >
        <ScrollView
          ref={scrollViewRef}
          style={styles.messagesArea}
          contentContainerStyle={[styles.messagesContent, isPrimaryEmpty && styles.messagesContentEmpty]}
          showsVerticalScrollIndicator={false}
          keyboardShouldPersistTaps="handled"
        >
          {isOffloadMode ? (
            offloadItems.length === 0 ? (
              <View style={styles.emptyState}>
                <Text style={styles.emptyPrompt}>Drop it. No response needed.</Text>
                <Text style={styles.emptyHint}>Nothing is sent back to you here. Drops are saved and processed quietly.</Text>
              </View>
            ) : (
              <>
                {offloadItems.map((item) => (
                  <View key={item.clientId} style={styles.offloadCard}>
                    <View style={styles.offloadCardHeader}>
                      <Text style={styles.offloadTimestamp}>{formatOffloadTimestamp(item.createdAt)}</Text>
                      <View style={[
                        styles.offloadStatusPill,
                        item.syncStatus === "needs_retry" && styles.offloadStatusPillWarning,
                        item.syncStatus === "saved_offline" && styles.offloadStatusPillMuted,
                      ]}>
                        <Text style={styles.offloadStatusText}>{getOffloadStatusLabel(item.syncStatus)}</Text>
                      </View>
                    </View>
                    <Text style={styles.offloadText}>{item.text}</Text>
                    {item.syncStatus === "needs_retry" ? (
                      <Pressable style={styles.offloadRetryButton} onPress={() => void syncPending()}>
                        <Text style={styles.offloadRetryText}>Retry</Text>
                      </Pressable>
                    ) : null}
                  </View>
                ))}
              </>
            )
          ) : !hasMessages && !backendConfigured ? (
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
              {!openLoopsPanelDismissed && openLoops &&
               ((openLoops.decisions.filter(l => !dismissedLoopIds.has(l.id)).length > 0) ||
                (openLoops.commitments.filter(l => !dismissedLoopIds.has(l.id)).length > 0)) ? (
                <View style={styles.activeContextPanel}>
                  <View style={styles.activeContextHeader}>
                    <Text style={styles.activeContextTitle}>Open threads</Text>
                    <Pressable onPress={() => setOpenLoopsPanelDismissed(true)} hitSlop={10}>
                      <Text style={styles.activeContextDismissAll}>×</Text>
                    </Pressable>
                  </View>
                  {openLoops.decisions.filter(l => !dismissedLoopIds.has(l.id)).length > 0 ? (
                    <View style={styles.activeContextSection}>
                      <Text style={styles.activeContextSectionLabel}>Unresolved decisions</Text>
                      {openLoops.decisions.filter(l => !dismissedLoopIds.has(l.id)).map((loop) => (
                        <View key={loop.id} style={styles.activeContextItem}>
                          <Text style={styles.activeContextItemText}>{loop.topic}</Text>
                          <Pressable onPress={() => handleDismissLoop(loop.id)} hitSlop={10}>
                            <Text style={styles.activeContextItemCheck}>✓</Text>
                          </Pressable>
                        </View>
                      ))}
                    </View>
                  ) : null}
                  {openLoops.commitments.filter(l => !dismissedLoopIds.has(l.id)).length > 0 ? (
                    <View style={styles.activeContextSection}>
                      <Text style={styles.activeContextSectionLabel}>Commitments you made</Text>
                      {openLoops.commitments.filter(l => !dismissedLoopIds.has(l.id)).map((loop) => (
                        <View key={loop.id} style={styles.activeContextItem}>
                          <Text style={styles.activeContextItemText}>{loop.topic}</Text>
                          <Pressable onPress={() => handleDismissLoop(loop.id)} hitSlop={10}>
                            <Text style={styles.activeContextItemCheck}>✓</Text>
                          </Pressable>
                        </View>
                      ))}
                    </View>
                  ) : null}
                </View>
              ) : null}
              <Text style={styles.emptyPrompt}>A clear space to think out loud.</Text>
              <Text style={styles.emptyHint}>Start anywhere. Sakhi keeps context as you talk.</Text>
              <Text style={styles.emptyHint}>Deep Dive unlocks once your thread runs long enough to draw from.</Text>
            </View>
          ) : (
            <>
              {showContinuationCard && continuationPrompt ? (
                <View style={styles.continuationCard}>
                  <Text style={styles.continuationText}>{continuationPrompt.display}</Text>
                  <View style={styles.continuationActions}>
                    <Pressable
                      onPress={() => setShowContinuationCard(false)}
                      style={styles.continuationCta}
                    >
                      <Text style={styles.continuationCtaText}>Continue →</Text>
                    </Pressable>
                    <Pressable onPress={() => setShowContinuationCard(false)}>
                      <Text style={styles.continuationDismiss}>Dismiss</Text>
                    </Pressable>
                  </View>
                </View>
              ) : null}
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
                      <Text style={styles.deepInlineText}>Deep Dive</Text>
                    </View>
                  )}
                </Pressable>
              )}
            </>
          )}
        </ScrollView>

        <View style={styles.inputArea}>
          <View
            style={[
              styles.footerModeRail,
              isOffloadMode ? styles.footerModeRailOffload : styles.footerModeRailTalk,
            ]}
          >
            <Pressable
              style={[
                styles.footerModePill,
                !isOffloadMode && styles.footerModePillActive,
                !isOffloadMode && styles.footerModePillTalkActive,
              ]}
              onPress={() => switchMode("talk")}
            >
              <View style={styles.footerModePillContent}>
                <SakhiBrandMark size={18} mode="talk" active={!isOffloadMode} />
                <Text
                  style={[
                    styles.footerModePillText,
                    !isOffloadMode && styles.footerModePillTextActive,
                  ]}
                >
                  Talk
                </Text>
              </View>
            </Pressable>
            <Pressable
              style={[
                styles.footerModePill,
                isOffloadMode && styles.footerModePillActive,
                isOffloadMode && styles.footerModePillOffloadActive,
              ]}
              onPress={() => switchMode("offload")}
            >
              <View style={styles.footerModePillContent}>
                <SakhiBrandMark size={18} mode="offload" active={isOffloadMode} />
                <Text
                  style={[
                    styles.footerModePillText,
                    isOffloadMode && styles.footerModePillTextActive,
                  ]}
                >
                  Drop
                </Text>
              </View>
            </Pressable>
          </View>

          {isOffloadMode ? (
            <View style={[styles.inputRow, styles.offloadInputRow]}>
              <TextInput
                style={[styles.textInput, styles.offloadTextInput]}
                placeholder="Drop it here."
                placeholderTextColor={palette.faint}
                value={inputText}
                onChangeText={setInputText}
                multiline
                textAlignVertical="top"
                editable={!isSavingOffload}
              />
              <Pressable
                style={[
                  styles.offloadSaveButton,
                  (!inputText.trim() || isSavingOffload) && styles.sendButtonDisabled,
                ]}
                onPress={() => void handleSaveOffload()}
                disabled={!inputText.trim() || isSavingOffload}
              >
                {isSavingOffload ? (
                  <ActivityIndicator size="small" color="#ffffff" />
                ) : (
                  <Text style={styles.offloadSaveButtonText}>
                    {connectivity === "offline" ? "Save offline" : "Save"}
                  </Text>
                )}
              </Pressable>
            </View>
          ) : (
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
          )}
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
                <Text style={styles.accountItemSubtitle}>
                  Threads and discussions from your last {MOBILE_CONTINUITY_PLAN.continuityDays} days
                </Text>
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
  surfaceStrong: theme.colors.surfaceStrong,
  surfaceMuted: theme.colors.surfaceMuted,
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
  backdropBase: {
    ...StyleSheet.absoluteFillObject,
    overflow: "hidden",
  },
  backdropTint: {
    ...StyleSheet.absoluteFillObject,
  },
  backdropTintTalk: {
    backgroundColor: "rgba(15, 21, 36, 0.28)",
  },
  backdropTintOffload: {
    backgroundColor: "rgba(23, 21, 16, 0.34)",
  },
  backdropGlow: {
    position: "absolute",
    width: 300,
    height: 300,
    borderRadius: 200,
    opacity: 1,
  },
  backdropGlowTalk: {
    top: 56,
    right: -64,
    backgroundColor: "rgba(120, 171, 255, 0.2)",
  },
  backdropGlowOffload: {
    top: 110,
    left: -70,
    backgroundColor: "rgba(196, 166, 105, 0.18)",
  },
  backdropWash: {
    position: "absolute",
    left: 0,
    right: 0,
    height: 300,
  },
  backdropWashTalk: {
    top: 0,
    backgroundColor: "rgba(31, 49, 81, 0.24)",
  },
  backdropWashOffload: {
    bottom: 0,
    backgroundColor: "rgba(72, 58, 31, 0.2)",
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
  headerSubcopy: {
    marginTop: 4,
    fontSize: 13,
    lineHeight: 18,
    color: palette.muted,
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
  noticeBanner: {
    marginHorizontal: 20,
    marginBottom: 10,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: palette.border,
    backgroundColor: theme.colors.surfaceMuted,
    paddingHorizontal: 14,
    paddingVertical: 10,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 10,
  },
  noticeBannerText: {
    flex: 1,
    color: palette.muted,
    fontSize: 12,
    lineHeight: 17,
  },
  noticeBannerAction: {
    color: palette.accent,
    fontSize: 12,
    fontWeight: "700",
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
  continuationCard: {
    marginBottom: 12,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "rgba(99,102,241,0.3)",
    backgroundColor: "rgba(99,102,241,0.07)",
    paddingHorizontal: 16,
    paddingVertical: 13,
  },
  continuationText: {
    fontSize: 14,
    lineHeight: 21,
    color: theme.colors.text,
  },
  continuationActions: {
    flexDirection: "row",
    alignItems: "center",
    gap: 16,
    marginTop: 9,
  },
  continuationCta: {
    paddingVertical: 2,
  },
  continuationCtaText: {
    fontSize: 13,
    fontWeight: "600" as const,
    color: theme.colors.accent,
    letterSpacing: 0.3,
  },
  continuationDismiss: {
    fontSize: 12,
    color: theme.colors.textMuted,
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
  offloadCard: {
    width: "100%",
    borderRadius: 20,
    borderWidth: 1,
    borderColor: palette.border,
    backgroundColor: palette.cardBg,
    paddingHorizontal: 16,
    paddingVertical: 14,
    marginBottom: 12,
    gap: 10,
  },
  offloadCardHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 10,
  },
  offloadTimestamp: {
    color: palette.muted,
    fontSize: 12,
  },
  offloadStatusPill: {
    borderRadius: 999,
    borderWidth: 1,
    borderColor: palette.accentBorder,
    backgroundColor: palette.accentSoft,
    paddingHorizontal: 10,
    paddingVertical: 5,
  },
  offloadStatusPillMuted: {
    borderColor: palette.border,
    backgroundColor: theme.colors.surfaceMuted,
  },
  offloadStatusPillWarning: {
    borderColor: "rgba(239, 111, 126, 0.35)",
    backgroundColor: "rgba(88, 33, 44, 0.36)",
  },
  offloadStatusText: {
    color: palette.fg,
    fontSize: 11,
    fontWeight: "600",
  },
  offloadText: {
    color: palette.fg,
    fontSize: 15,
    lineHeight: 22,
  },
  offloadRetryButton: {
    alignSelf: "flex-start",
    paddingVertical: 4,
  },
  offloadRetryText: {
    color: palette.accent,
    fontSize: 12,
    fontWeight: "700",
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
  footerModeRail: {
    flexDirection: "row",
    gap: 8,
    padding: 6,
    borderRadius: 999,
    borderWidth: 1,
  },
  footerModeRailTalk: {
    borderColor: "rgba(120, 171, 255, 0.2)",
    backgroundColor: "rgba(18, 25, 39, 0.9)",
  },
  footerModeRailOffload: {
    borderColor: "rgba(196, 166, 105, 0.22)",
    backgroundColor: "rgba(31, 26, 19, 0.92)",
  },
  footerModePill: {
    flex: 1,
    minHeight: 44,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: "transparent",
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 12,
    backgroundColor: "transparent",
  },
  footerModePillContent: {
    flexDirection: "row",
    alignItems: "center",
    gap: 7,
  },
  footerModePillActive: {
    borderColor: "rgba(245, 248, 255, 0.34)",
    shadowOpacity: 0.28,
    shadowRadius: 16,
    shadowOffset: { width: 0, height: 6 },
  },
  footerModePillTalkActive: {
    backgroundColor: "rgba(120, 171, 255, 0.28)",
    shadowColor: "#6b8dcc",
  },
  footerModePillOffloadActive: {
    backgroundColor: "rgba(196, 166, 105, 0.3)",
    shadowColor: "#8c7350",
  },
  footerModePillText: {
    color: palette.subtle,
    fontSize: 13,
    fontWeight: "700",
  },
  footerModePillTextActive: {
    color: palette.fg,
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
  offloadInputRow: {
    flexDirection: "column",
    alignItems: "stretch",
    borderRadius: 20,
    paddingVertical: 14,
    gap: 12,
  },
  offloadTextInput: {
    minHeight: 108,
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
  offloadSaveButton: {
    minHeight: 44,
    borderRadius: 999,
    backgroundColor: palette.accent,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 18,
    alignSelf: "flex-end",
  },
  offloadSaveButtonText: {
    color: "#ffffff",
    fontSize: 14,
    fontWeight: "700",
  },
  activeContextPanel: {
    width: "100%",
    borderRadius: 14,
    borderWidth: 1,
    borderColor: palette.border,
    backgroundColor: palette.surfaceStrong,
    padding: 14,
    marginBottom: 20,
    gap: 12,
  },
  activeContextHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  activeContextTitle: {
    fontSize: 11,
    textTransform: "uppercase",
    letterSpacing: 1.2,
    color: palette.muted,
    fontWeight: "600",
  },
  activeContextDismissAll: {
    fontSize: 20,
    color: palette.muted,
    lineHeight: 22,
    paddingHorizontal: 4,
  },
  activeContextSection: {
    gap: 6,
  },
  activeContextSectionLabel: {
    fontSize: 11,
    textTransform: "uppercase",
    letterSpacing: 0.8,
    color: palette.muted,
  },
  activeContextItem: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 10,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: palette.border,
    backgroundColor: palette.surfaceMuted,
    paddingVertical: 9,
    paddingHorizontal: 12,
  },
  activeContextItemText: {
    flex: 1,
    fontSize: 14,
    lineHeight: 20,
    color: palette.fg,
  },
  activeContextItemCheck: {
    fontSize: 15,
    color: palette.muted,
    paddingHorizontal: 4,
  },
});
