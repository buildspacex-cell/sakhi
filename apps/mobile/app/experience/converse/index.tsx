import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  View,
  Text,
  TextInput,
  Pressable,
  ScrollView,
  StyleSheet,
  SafeAreaView,
  StatusBar,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
} from "react-native";
import { useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { useAuth } from "../../../lib/auth/AuthContext";
import { config } from "../../../lib/config";

interface Message {
  id: string;
  role: "user" | "sakhi";
  content: string;
  timestamp: Date;
  kind?: "normal" | "deep" | "system";
}

interface DeepReflectSignal {
  ready: boolean;
  reason: string;
  mirror_allowed: boolean;
  detail_allowed: boolean;
  selected_count: number;
  min_moments: number;
}

interface ContinuitySignal {
  topic_key: string;
  topic_label?: string;
  deep_reflect?: DeepReflectSignal;
}

const BACKEND_URL = config.backendUrl || "https://sakhi-production-930f.up.railway.app";
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
  const { user, session, signOut } = useAuth();
  const scrollViewRef = useRef<ScrollView>(null);

  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [isRunningDeepAnswer, setIsRunningDeepAnswer] = useState(false);
  const [deepReflectionStatus, setDeepReflectionStatus] = useState("");
  const [activeContinuitySignal, setActiveContinuitySignal] = useState<ContinuitySignal | null>(null);
  const [latestUserMessage, setLatestUserMessage] = useState("");

  const personId = user?.personId || "";
  const authToken = session?.access_token || "";

  useEffect(() => {
    if (messages.length > 0) {
      setTimeout(() => {
        scrollViewRef.current?.scrollToEnd({ animated: true });
      }, 120);
    }
  }, [messages]);

  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return "Good morning";
    if (hour < 17) return "Good afternoon";
    return "Good evening";
  };

  const displayName = user?.fullName?.split(" ")[0] || "";
  const deepReflectSignal = activeContinuitySignal?.deep_reflect;
  const deepSelectedCount = deepReflectSignal?.selected_count || 0;
  const deepMinMoments = deepReflectSignal?.min_moments || 8;
  const deepThreadLabel =
    activeContinuitySignal?.topic_label || activeContinuitySignal?.topic_key || "this thread";
  const hasDeepQuery = latestUserMessage.trim().length > 0;
  const deepAnswerReady = Boolean(activeContinuitySignal?.topic_key && deepReflectSignal?.ready && hasDeepQuery);
  const deepStatusHint = (() => {
    if (!activeContinuitySignal?.topic_key) {
      return "Deep Reflect will appear when this chat forms a clear thread.";
    }
    if (!hasDeepQuery) {
      return "Send one message to set your current question.";
    }
    const reason = deepReflectSignal?.reason || "insufficient_depth";
    if (reason === "ready") {
      return `Deep Reflect is ready for ${deepThreadLabel}.`;
    }
    if (reason === "mirror_blocked") {
      return "Deep Reflect is temporarily unavailable while this thread is still stabilizing.";
    }
    if (reason === "detail_blocked") {
      return "Deep Reflect will unlock once this thread has clearer detail.";
    }
    return `Deep Reflect unlocks once your story runs long enough to draw from (${deepSelectedCount}/${deepMinMoments}).`;
  })();

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

      if (res.ok) {
        const data = await res.json();
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
        console.error(`[turn] HTTP ${res.status}: ${statusText.slice(0, 200)}`);
      }
    } catch (err: unknown) {
      clearTimeout(timeout);
      const isTimeout = err instanceof Error && err.name === "AbortError";
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
      console.error("[turn] fetch error:", err);
    } finally {
      setIsSending(false);
    }
  }, [authToken, inputText, personId]);

  const handleRunDeepAnswer = useCallback(async () => {
    if (!personId || !activeContinuitySignal?.topic_key || !hasDeepQuery || isRunningDeepAnswer) {
      return;
    }

    const pendingId = `deep-pending-${Date.now()}`;
    setIsRunningDeepAnswer(true);
    setDeepReflectionStatus("queued");
    setMessages((prev) => [
      ...prev,
      {
        id: pendingId,
        role: "sakhi",
        content: `Deep Reflect is reading the full ${deepThreadLabel} story...`,
        timestamp: new Date(),
        kind: "system",
      },
    ]);

    const removePending = () => {
      setMessages((prev) => prev.filter((msg) => msg.id !== pendingId));
    };

    try {
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
          mode: "deep_answer",
          user_query: latestUserMessage.trim(),
        }),
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
    deepThreadLabel,
    hasDeepQuery,
    isRunningDeepAnswer,
    latestUserMessage,
    personId,
    pollDeepAnswer,
  ]);

  const handleSignOut = async () => {
    await signOut();
    router.replace("/" as never);
  };

  const hasMessages = messages.length > 0;

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" />
      <View pointerEvents="none" style={styles.auroraA} />
      <View pointerEvents="none" style={styles.auroraB} />

      <View style={styles.header}>
        <View style={styles.headerLeft}>
          <Text style={styles.brand}>Sakhi</Text>
          <Text style={styles.greeting}>
            {getGreeting()}
            {displayName ? `, ${displayName}` : ""}
          </Text>
        </View>
        <View style={styles.headerActions}>
          <Pressable
            style={styles.headerPill}
            onPress={() => router.push("/soul/topic-reflection" as never)}
          >
            <Ionicons name="sparkles-outline" size={14} color={palette.fg} />
            <Text style={styles.headerPillText}>Profile</Text>
          </Pressable>
          <Pressable onPress={handleSignOut} hitSlop={12}>
            <Text style={styles.signOutText}>Sign out</Text>
          </Pressable>
        </View>
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
          {!hasMessages ? (
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
                    <Text style={[styles.bubbleText, !isUser && styles.sakhiBubbleText]}>{msg.content}</Text>
                  </View>
                );
              })}
              {isSending && (
                <View style={[styles.bubble, styles.systemBubble, { opacity: 0.7 }]}>
                  <ActivityIndicator size="small" color={palette.muted} />
                </View>
              )}
            </>
          )}
        </ScrollView>

        <View style={styles.inputArea}>
          {hasMessages && activeContinuitySignal?.topic_key ? (
            <>
              <View style={styles.deepActionRow}>
                <View style={[styles.deepInfoPill, deepAnswerReady && styles.deepInfoPillReady]}>
                  <Text style={styles.deepInfoText}>{deepStatusHint}</Text>
                </View>
                <Pressable
                  style={[
                    styles.deepRunButton,
                    (!deepAnswerReady || isRunningDeepAnswer) && styles.deepRunButtonDisabled,
                  ]}
                  onPress={() => void handleRunDeepAnswer()}
                  disabled={!deepAnswerReady || isRunningDeepAnswer}
                >
                  {isRunningDeepAnswer ? (
                    <View style={styles.deepRunButtonContent}>
                      <ActivityIndicator size="small" color="#f5dcb2" />
                      <Text style={styles.deepRunButtonText}>Reading...</Text>
                    </View>
                  ) : (
                    <View style={styles.deepRunButtonContent}>
                      <Ionicons name="sparkles" size={14} color="#ffe6bf" />
                      <Text style={styles.deepRunButtonText}>Run Deep</Text>
                    </View>
                  )}
                </Pressable>
              </View>
              {deepReflectionStatus ? (
                <Text style={styles.deepStatusText}>Deep Reflect status: {deepReflectionStatus}</Text>
              ) : null}
            </>
          ) : null}
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
    </SafeAreaView>
  );
}

const palette = {
  bg: "#070b14",
  fg: "#f6f7fb",
  muted: "#a4adbc",
  subtle: "#7d8899",
  faint: "#5a6372",
  accent: "#349ba9",
  cardBg: "rgba(21, 28, 40, 0.74)",
  border: "rgba(228, 236, 250, 0.14)",
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: palette.bg,
  },
  auroraA: {
    position: "absolute",
    top: -140,
    right: -90,
    width: 280,
    height: 280,
    borderRadius: 180,
    backgroundColor: "rgba(89, 214, 226, 0.18)",
  },
  auroraB: {
    position: "absolute",
    bottom: 120,
    left: -100,
    width: 240,
    height: 240,
    borderRadius: 140,
    backgroundColor: "rgba(243, 194, 109, 0.12)",
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
  headerActions: {
    alignItems: "flex-end",
    gap: 8,
  },
  headerPill: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    paddingVertical: 6,
    paddingHorizontal: 10,
    borderRadius: 999,
    backgroundColor: "rgba(255, 255, 255, 0.09)",
    borderWidth: 1,
    borderColor: palette.border,
  },
  headerPillText: {
    color: palette.fg,
    fontSize: 11,
    fontWeight: "600",
  },
  signOutText: {
    fontSize: 12,
    color: palette.subtle,
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
  userBubble: {
    alignSelf: "flex-end",
    backgroundColor: "rgba(52, 155, 169, 0.88)",
    borderColor: "rgba(137, 233, 244, 0.45)",
    borderBottomRightRadius: 8,
  },
  sakhiBubble: {
    alignSelf: "flex-start",
    backgroundColor: palette.cardBg,
    borderColor: palette.border,
    borderBottomLeftRadius: 8,
  },
  deepBubble: {
    alignSelf: "flex-start",
    backgroundColor: "rgba(78, 56, 24, 0.58)",
    borderColor: "rgba(233, 193, 128, 0.4)",
    borderBottomLeftRadius: 8,
  },
  deepBadge: {
    color: "#f0d5a6",
    fontSize: 11,
    fontWeight: "700",
    letterSpacing: 0.6,
    marginBottom: 6,
    textTransform: "uppercase",
  },
  systemBubble: {
    alignSelf: "flex-start",
    backgroundColor: "rgba(78, 89, 110, 0.32)",
    borderColor: "rgba(170, 186, 212, 0.2)",
    borderBottomLeftRadius: 8,
  },
  bubbleText: {
    fontSize: 15,
    color: "#ffffff",
    lineHeight: 22,
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
    borderColor: "rgba(178, 197, 226, 0.24)",
    backgroundColor: "rgba(20, 31, 50, 0.72)",
    paddingVertical: 10,
    paddingHorizontal: 14,
    minHeight: 42,
    justifyContent: "center",
  },
  deepInfoPillReady: {
    borderColor: "rgba(225, 190, 116, 0.44)",
    backgroundColor: "rgba(85, 66, 35, 0.46)",
  },
  deepInfoText: {
    color: "#c6d3ea",
    fontSize: 12,
    lineHeight: 17,
  },
  deepRunButton: {
    minWidth: 116,
    height: 46,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: "rgba(243, 214, 164, 0.58)",
    backgroundColor: "rgba(117, 86, 42, 0.62)",
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 16,
    shadowColor: "#c98f45",
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
    color: "#fce7c3",
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
