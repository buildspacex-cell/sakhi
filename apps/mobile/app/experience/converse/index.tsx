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

interface ContinuityPackDebug {
  topic_key: string;
  topic_label?: string;
}

const BACKEND_URL = config.backendUrl || "https://sakhi-production-930f.up.railway.app";
const DEEP_POLL_INTERVAL_MS = 2000;
const DEEP_POLL_MAX_ATTEMPTS = 70;

function toContinuityPack(raw: unknown): ContinuityPackDebug | null {
  if (!raw || typeof raw !== "object") return null;
  const data = raw as Record<string, unknown>;
  const topicKey = String(data.topic_key || "").trim();
  if (!topicKey) return null;
  const topicLabel = String(data.topic_label || "").trim();
  return {
    topic_key: topicKey,
    topic_label: topicLabel || undefined,
  };
}

function formatDeepReflectionResult(payload: Record<string, unknown>): string {
  const result = (payload.result as Record<string, unknown> | undefined) || {};
  const chatResponse = String(result.chat_response || "").trim();
  if (chatResponse) {
    return chatResponse;
  }

  const topicLabel = String(result.topic_label || payload.topic_key || "this thread");
  const lines: string[] = [`Deep reflection on ${topicLabel}:`];

  const originStory = String(result.origin_story || "").trim();
  const keyPivots = Array.isArray(result.key_pivots) ? result.key_pivots : [];
  const currentStage = String(result.current_stage || "").trim();

  if (originStory) lines.push(`Start: ${originStory}`);
  if (typeof keyPivots[0] === "string" && keyPivots[0].trim()) {
    lines.push(`Pivot: ${keyPivots[0].trim()}`);
  }
  if (currentStage) lines.push(`Current: ${currentStage}`);

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
  const [activeContinuityPack, setActiveContinuityPack] = useState<ContinuityPackDebug | null>(null);
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
  const deepAnswerReady = Boolean(activeContinuityPack?.topic_key && latestUserMessage.trim());

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
        const pack = toContinuityPack(data.continuity);
        setActiveContinuityPack(pack);

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
    if (!personId || !activeContinuityPack?.topic_key || !latestUserMessage.trim() || isRunningDeepAnswer) {
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
        content: "Deep answer is reading your full topic history...",
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
          topic_key: activeContinuityPack.topic_key,
          window: "3650d",
          mode: "deep_answer",
          user_query: latestUserMessage,
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
            content: "Deep answer did not complete this time. Please try again.",
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
          content: "Could not run deep answer right now.",
          timestamp: new Date(),
          kind: "system",
        },
      ]);
      console.error("[deep-answer] run error", err);
    } finally {
      setIsRunningDeepAnswer(false);
      setDeepReflectionStatus("");
    }
  }, [activeContinuityPack?.topic_key, authToken, isRunningDeepAnswer, latestUserMessage, personId, pollDeepAnswer]);

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
              <Text style={styles.emptyHint}>Send one message, then run Deep Answer for a whole-story lens.</Text>
            </View>
          ) : (
            <>
              {messages.map((msg) => {
                const isUser = msg.role === "user";
                const isDeep = msg.kind === "deep";
                const isSystem = msg.kind === "system";

                return (
                  <View
                    key={msg.id}
                    style={[
                      styles.bubble,
                      isUser
                        ? styles.userBubble
                        : isDeep
                          ? styles.deepBubble
                          : isSystem
                            ? styles.systemBubble
                            : styles.sakhiBubble,
                    ]}
                  >
                    {!isUser && isDeep && <Text style={styles.deepBadge}>Sakhi · Deep Answer</Text>}
                    <Text style={[styles.bubbleText, !isUser && styles.sakhiBubbleText]}>{msg.content}</Text>
                  </View>
                );
              })}
              {(isSending || isRunningDeepAnswer) && (
                <View style={[styles.bubble, styles.systemBubble, { opacity: 0.7 }]}> 
                  <ActivityIndicator size="small" color={palette.muted} />
                </View>
              )}
            </>
          )}
        </ScrollView>

        <View style={styles.inputArea}>
          <View style={styles.deepBar}>
            <View style={styles.deepTopicPill}>
              <Text style={styles.deepTopicText}>
                {activeContinuityPack?.topic_key
                  ? `Thread: ${activeContinuityPack.topic_label || activeContinuityPack.topic_key}`
                  : "Thread unlocks after the first reply"}
              </Text>
            </View>
            <Pressable
              style={[
                styles.deepAction,
                (!deepAnswerReady || isRunningDeepAnswer) && styles.deepActionDisabled,
              ]}
              onPress={handleRunDeepAnswer}
              disabled={!deepAnswerReady || isRunningDeepAnswer}
            >
              <Text style={styles.deepActionText}>
                {isRunningDeepAnswer ? `Deep ${deepReflectionStatus || "running"}` : "Run Deep"}
              </Text>
            </Pressable>
          </View>

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
              editable={!isSending && !isRunningDeepAnswer}
            />
            {inputText.trim().length > 0 && (
              <Pressable
                style={[styles.sendButton, (isSending || isRunningDeepAnswer) && styles.sendButtonDisabled]}
                onPress={sendMessage}
                disabled={isSending || isRunningDeepAnswer}
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
  deepAccent: "#d4b06e",
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
    maxWidth: "92%",
    backgroundColor: "rgba(212, 176, 110, 0.14)",
    borderColor: "rgba(242, 209, 147, 0.42)",
    borderBottomLeftRadius: 8,
    paddingTop: 10,
    paddingBottom: 16,
    paddingHorizontal: 16,
  },
  systemBubble: {
    alignSelf: "flex-start",
    backgroundColor: "rgba(78, 89, 110, 0.32)",
    borderColor: "rgba(170, 186, 212, 0.2)",
    borderBottomLeftRadius: 8,
  },
  deepBadge: {
    color: "#f3d3a1",
    fontSize: 11,
    fontWeight: "700",
    letterSpacing: 0.5,
    marginBottom: 8,
    textTransform: "uppercase",
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
    borderTopWidth: 1,
    borderTopColor: palette.border,
  },
  deepBar: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 10,
    gap: 8,
  },
  deepTopicPill: {
    flex: 1,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: palette.border,
    backgroundColor: "rgba(255, 255, 255, 0.06)",
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  deepTopicText: {
    color: palette.muted,
    fontSize: 12,
  },
  deepAction: {
    borderRadius: 14,
    borderWidth: 1,
    borderColor: "rgba(242, 209, 147, 0.45)",
    backgroundColor: "rgba(212, 176, 110, 0.2)",
    paddingHorizontal: 14,
    paddingVertical: 8,
  },
  deepActionDisabled: {
    opacity: 0.55,
  },
  deepActionText: {
    color: "#ffe2b8",
    fontSize: 12,
    fontWeight: "700",
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
