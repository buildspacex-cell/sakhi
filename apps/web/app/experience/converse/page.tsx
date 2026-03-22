"use client";

import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import type React from "react";
import type { Route } from "next";
import { editorialFontFamily, midnightEditorial as palette } from "@/lib/theme/midnightEditorial";

export const dynamic = "force-dynamic";

interface Message {
  id: string;
  role: "user" | "sakhi";
  content: string;
  timestamp: Date;
  kind?: "normal" | "deep" | "system";
}

interface AuthUser {
  person_id: string;
  full_name: string | null;
  email: string;
  needs_name?: boolean;
}

interface HistoryMessagePayload {
  id?: string;
  role?: string;
  content?: string;
  created_at?: string;
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
    ? whole.selected_topics
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

export default function ConversePage() {
  return (
    <Suspense fallback={null}>
      <ConverseContent />
    </Suspense>
  );
}

function ConverseContent() {
  const router = useRouter();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const loadedHistoryForPersonRef = useRef<string | null>(null);

  const [authUser, setAuthUser] = useState<AuthUser | null>(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [isHistoryLoading, setIsHistoryLoading] = useState(true);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [accountMenuOpen, setAccountMenuOpen] = useState(false);

  const [isRunningDeepAnswer, setIsRunningDeepAnswer] = useState(false);
  const [deepReflectionStatus, setDeepReflectionStatus] = useState("");
  const [activeContinuitySignal, setActiveContinuitySignal] = useState<ContinuitySignal | null>(null);
  const [latestUserMessage, setLatestUserMessage] = useState("");

  useEffect(() => {
    const loadAuth = async () => {
      try {
        const res = await fetch("/api/auth/me", { cache: "no-store" });
        if (res.ok) {
          const data = await res.json();
          const fullName = String(data.full_name || "").trim();
          const encodedUser = encodeURIComponent(data.person_id || "");
          const encodedName = encodeURIComponent(fullName);

          if (Boolean(data.needs_name) || !fullName) {
            router.replace(`/experience/onboarding?user=${encodedUser}&name=${encodedName}` as Route);
            return;
          }

          setAuthUser({
            person_id: data.person_id,
            full_name: fullName,
            email: data.email,
            needs_name: Boolean(data.needs_name),
          });
        } else if (res.status === 401) {
          router.replace("/auth/login?redirect=/experience/converse" as Route);
        }
      } catch (err) {
        console.error("Auth load failed:", err);
      } finally {
        setAuthLoading(false);
      }
    };
    void loadAuth();
  }, [router]);

  const personId = authUser?.person_id || "";
  const hasMessages = messages.length > 0;

  useEffect(() => {
    if (authLoading) {
      return;
    }
    if (!personId) {
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
          session_slug: "converse",
          limit: "20",
        });
        const response = await fetch(`/api/conversation/history?${params.toString()}`, {
          cache: "no-store",
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
        // Fall back to the current empty state if history cannot be loaded.
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
  }, [authLoading, personId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const deepReflectSignal = activeContinuitySignal?.deep_reflect;
  const wholeStorySignal = activeContinuitySignal?.whole_story;
  const deepThreadLabel =
    activeContinuitySignal?.topic_label || activeContinuitySignal?.topic_key || "this thread";

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

  const linkedWholeStoryReady = Boolean(wholeStorySignal?.ready && wholeStorySelectedTopics.length >= 2);
  const deepReflectReady = Boolean(deepReflectSignal?.ready);
  const hasDeepQuery = latestUserMessage.trim().length > 0;
  const deepAnswerReady = Boolean(activeContinuitySignal?.topic_key && hasDeepQuery && deepReflectReady);

  const deepStatusHint = (() => {
    if (!activeContinuitySignal?.topic_key) {
      return "Deep Reflect will appear when this chat forms a clear thread.";
    }
    if (!hasDeepQuery) {
      return "Send one message to set your current question.";
    }
    if (linkedWholeStoryReady) {
      const primary = deepThreadLabel;
      const linked = wholeStorySelectedTopics
        .filter((topic) => topic !== activeContinuitySignal.topic_key)
        .slice(0, 2)
        .join(", ");
      if (linked) {
        return `Deep Reflect is ready across ${primary} and ${linked}.`;
      }
      return `Deep Reflect is ready with whole-story context for ${primary}.`;
    }
    if (deepReflectReady) {
      return `Deep Reflect is ready for ${deepThreadLabel}. Linked threads will be woven in when they are clearly relevant.`;
    }
    if (deepReflectSignal && !deepReflectSignal.ready) {
      const reason = deepReflectSignal.reason || "insufficient_depth";
      if (reason === "mirror_blocked") {
        return "Deep Reflect will unlock once this thread is safe to mirror back clearly.";
      }
      if (reason === "detail_blocked") {
        return "Deep Reflect will unlock once this thread has enough detail to reflect back clearly.";
      }
      if (reason === "insufficient_depth") {
        return `Deep Reflect unlocks once this thread has at least ${deepReflectSignal.min_moments} moments to draw from.`;
      }
      return "Deep Reflect unlocks once this thread has enough history to draw from.";
    }
    return "Deep Reflect unlocks once this thread has enough history to draw from.";
  })();

  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return "Good morning";
    if (hour < 17) return "Good afternoon";
    return "Good evening";
  };

  const displayName = authUser?.full_name?.split(" ")[0] || "";

  const sendMessage = useCallback(async () => {
    const text = inputText.trim();
    if (!text || !personId || isSending) return;

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
      const url = `/api/turn-v2?user=${encodeURIComponent(personId)}`;
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
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
        const sakhiMessage: Message = {
          id: `error-${Date.now()}`,
          role: "sakhi",
          content: `Something went wrong (${res.status}). Try again.`,
          timestamp: new Date(),
          kind: "system",
        };
        setMessages((prev) => [...prev, sakhiMessage]);
      }
    } catch (err: unknown) {
      clearTimeout(timeout);
      const isTimeout = err instanceof Error && err.name === "AbortError";
      const errorMsg = isTimeout
        ? "That took too long. Try again — sometimes the first message is slower."
        : `Connection issue: ${err instanceof Error ? err.message : "unknown"}`;
      const sakhiMessage: Message = {
        id: `error-${Date.now()}`,
        role: "sakhi",
        content: errorMsg,
        timestamp: new Date(),
        kind: "system",
      };
      setMessages((prev) => [...prev, sakhiMessage]);
    } finally {
      setIsSending(false);
    }
  }, [inputText, isSending, personId]);

  const pollDeepAnswer = useCallback(async (reflectionId: string, person: string): Promise<string | null> => {
    const fetchResult = async (): Promise<string | null> => {
      const params = new URLSearchParams({ id: reflectionId, person_id: person, t: String(Date.now()) });
      const resultRes = await fetch(`/api/continuity/reflection/result?${params.toString()}`, {
        cache: "no-store",
      });
      if (!resultRes.ok) return null;
      const resultData = (await resultRes.json()) as Record<string, unknown>;
      if (String(resultData.status || "queued") !== "done") return null;
      return formatDeepReflectionResult(resultData);
    };

    for (let attempt = 0; attempt < DEEP_POLL_MAX_ATTEMPTS; attempt += 1) {
      try {
        const statusParams = new URLSearchParams({
          id: reflectionId,
          person_id: person,
          t: String(Date.now()),
        });
        const statusRes = await fetch(`/api/continuity/reflection/status?${statusParams.toString()}`, {
          cache: "no-store",
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
  }, []);

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

    const selectedTopics = wholeStorySelectedTopics;
    const pendingId = `deep-pending-${Date.now()}`;

    setIsRunningDeepAnswer(true);
    setDeepReflectionStatus("queued");
    setMessages((prev) => [
      ...prev,
      {
        id: pendingId,
        role: "sakhi",
        content:
          selectedTopics.length >= 2
            ? "Deep Reflect is reading your whole story across linked threads..."
            : "Deep Reflect is reading the full story of this thread...",
        timestamp: new Date(),
        kind: "system",
      },
    ]);

    const removePending = () => {
      setMessages((prev) => prev.filter((msg) => msg.id !== pendingId));
    };

    try {
      const res = await fetch(`/api/continuity/reflection/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          person_id: personId,
          topic_key: activeContinuitySignal.topic_key,
          window: "3650d",
          mode: "whole_story",
          topic_keys: selectedTopics,
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
    hasDeepQuery,
    isRunningDeepAnswer,
    latestUserMessage,
    personId,
    pollDeepAnswer,
    deepAnswerReady,
    wholeStorySelectedTopics,
  ]);

  const openAccountRoute = useCallback(
    (path: string) => {
      setAccountMenuOpen(false);
      const query = personId ? `?user=${encodeURIComponent(personId)}` : "";
      router.push(`${path}${query}` as Route);
    },
    [personId, router],
  );

  const handleSignOut = useCallback(async () => {
    setAccountMenuOpen(false);
    const supabase = createClient();
    await supabase.auth.signOut();
    router.replace("/experience" as Route);
  }, [router]);

  if (authLoading) {
    return (
      <div style={{ ...styles.container, display: "flex", alignItems: "center", justifyContent: "center" }}>
        <p style={{ color: palette.muted }}>Loading...</p>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <header style={styles.header}>
        <div style={styles.headerLeft}>
          <div style={styles.brand}>Sakhi</div>
          <div style={styles.greeting}>
            {getGreeting()}
            {displayName ? `, ${displayName}` : ""}
          </div>
        </div>

        <div style={{ position: "relative" }}>
          <button style={styles.accountTrigger} onClick={() => setAccountMenuOpen((prev) => !prev)}>
            <span style={{ fontSize: 14 }}>✦</span>
            <span>Profile</span>
          </button>

          {accountMenuOpen ? (
            <div style={styles.accountMenu}>
              <button style={styles.accountItem} onClick={() => openAccountRoute("/experience/reflection")}>Profile</button>
              <button style={styles.accountItem} onClick={() => openAccountRoute("/experience/settings")}>Settings</button>
              <button style={styles.accountItem} onClick={() => openAccountRoute("/experience/support")}>Report an issue</button>
              <button style={{ ...styles.accountItem, color: palette.danger }} onClick={() => void handleSignOut()}>Sign out</button>
            </div>
          ) : null}
        </div>
      </header>

      <main style={styles.messagesArea}>
        {!hasMessages && isHistoryLoading ? (
          <div style={styles.historyLoadingState}>
            <p style={{ color: palette.muted }}>Loading...</p>
          </div>
        ) : !hasMessages ? (
          <div style={styles.emptyState}>
            <p style={styles.emptyPrompt}>A clear space to think out loud.</p>
            <p style={styles.emptyHint}>Start anywhere. Sakhi keeps context as you talk.</p>
            <p style={styles.emptyHint}>Deep Reflect unlocks once your story runs long enough to draw from.</p>
          </div>
        ) : (
          <>
            {messages.map((msg) => {
              const isUser = msg.role === "user";
              const isSystem = msg.kind === "system";
              const isDeep = msg.kind === "deep";
              return (
                <div
                  key={msg.id}
                  style={{
                    ...styles.bubble,
                    ...(isUser
                      ? styles.userBubble
                      : isSystem
                        ? styles.systemBubble
                        : isDeep
                          ? styles.deepBubble
                          : styles.sakhiBubble),
                  }}
                >
                  {isDeep ? <div style={styles.deepBadge}>Whole Story</div> : null}
                  <div style={styles.bubbleText}>{msg.content}</div>
                </div>
              );
            })}
            {isSending ? (
              <div style={{ ...styles.bubble, ...styles.systemBubble, opacity: 0.7 }}>
                <span style={{ color: palette.muted }}>...</span>
              </div>
            ) : null}
          </>
        )}
        <div ref={messagesEndRef} />
      </main>

      <section style={styles.inputArea}>
        {hasMessages ? (
          <div style={styles.deepActionRow}>
            <div style={{
              ...styles.deepInfoPill,
              ...(deepAnswerReady ? styles.deepInfoPillReady : {}),
            }}>
              <span style={styles.deepInfoText}>{deepStatusHint}</span>
            </div>
            <button
              style={{
                ...styles.deepRunButton,
                ...((!deepAnswerReady || isRunningDeepAnswer) ? styles.deepRunButtonDisabled : {}),
              }}
              onClick={() => void handleRunDeepAnswer()}
              disabled={!deepAnswerReady || isRunningDeepAnswer}
              title={deepReflectionStatus || undefined}
            >
              {isRunningDeepAnswer ? "Reading..." : "Run Deep"}
            </button>
          </div>
        ) : null}

        <form
          style={styles.textInputRow}
          onSubmit={(event) => {
            event.preventDefault();
            void sendMessage();
          }}
        >
          <input
            type="text"
            value={inputText}
            placeholder="What's on your mind?"
            onChange={(event) => setInputText(event.target.value)}
            style={styles.textInput}
          />
          <button
            type="submit"
            disabled={!inputText.trim() || isSending}
            style={{
              ...styles.sendButton,
              ...((!inputText.trim() || isSending) ? styles.sendButtonDisabled : {}),
            }}
          >
            Send
          </button>
        </form>
      </section>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    minHeight: "100vh",
    background: `linear-gradient(180deg, ${palette.bgElevated} 0%, ${palette.bg} 18%, ${palette.bg} 100%)`,
    color: palette.fg,
    fontFamily: editorialFontFamily,
    display: "flex",
    flexDirection: "column",
    position: "relative",
    overflow: "hidden",
  },
  header: {
    position: "relative",
    zIndex: 2,
    borderBottom: `1px solid ${palette.border}`,
    padding: "16px 20px 12px",
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 14,
  },
  headerLeft: {
    display: "flex",
    flexDirection: "column",
    gap: 6,
  },
  brand: {
    textTransform: "uppercase",
    letterSpacing: "0.18em",
    fontSize: 12,
    color: palette.muted,
  },
  greeting: {
    fontSize: 30,
    lineHeight: 1.08,
    fontWeight: 560,
    color: palette.fg,
    letterSpacing: "-0.03em",
  },
  accountTrigger: {
    borderRadius: 999,
    border: `1px solid ${palette.border}`,
    background: palette.glassMuted,
    color: palette.fg,
    padding: "10px 16px",
    display: "inline-flex",
    alignItems: "center",
    gap: 8,
    minHeight: 44,
    fontSize: 14,
    cursor: "pointer",
  },
  accountMenu: {
    position: "absolute",
    right: 0,
    top: "calc(100% + 10px)",
    minWidth: 200,
    borderRadius: 16,
    border: `1px solid ${palette.border}`,
    background: palette.glassStrong,
    backdropFilter: "blur(8px)",
    boxShadow: "0 12px 28px rgba(0,0,0,0.35)",
    padding: 8,
    display: "flex",
    flexDirection: "column",
    gap: 4,
    zIndex: 5,
  },
  accountItem: {
    border: "none",
    background: "transparent",
    color: palette.fg,
    fontSize: 13,
    textAlign: "left",
    borderRadius: 10,
    padding: "10px 12px",
    cursor: "pointer",
  },
  messagesArea: {
    position: "relative",
    zIndex: 1,
    flex: 1,
    overflowY: "auto",
    padding: "18px 20px 10px",
    display: "flex",
    flexDirection: "column",
    gap: 12,
  },
  emptyState: {
    margin: "auto",
    textAlign: "center",
    maxWidth: 620,
  },
  historyLoadingState: {
    margin: "auto",
    textAlign: "center",
  },
  emptyPrompt: {
    fontSize: 42,
    lineHeight: 1.08,
    letterSpacing: "-0.03em",
    margin: 0,
    color: palette.fg,
    fontWeight: 520,
  },
  emptyHint: {
    margin: "14px auto 0",
    fontSize: 20,
    lineHeight: 1.32,
    color: palette.muted,
    maxWidth: 620,
  },
  bubble: {
    maxWidth: "78%",
    borderRadius: 22,
    border: `1px solid ${palette.border}`,
    padding: "13px 15px",
    whiteSpace: "pre-wrap",
  },
  userBubble: {
    alignSelf: "flex-end",
    background: palette.userBubble,
    borderColor: palette.borderStrong,
  },
  sakhiBubble: {
    alignSelf: "flex-start",
    background: palette.sakhiBubble,
  },
  deepBubble: {
    alignSelf: "flex-start",
    background: palette.deepBubble,
    borderColor: palette.accentBorder,
  },
  systemBubble: {
    alignSelf: "center",
    background: palette.systemBubble,
  },
  bubbleText: {
    fontSize: 15,
    lineHeight: 1.5,
    color: palette.fg,
  },
  deepBadge: {
    display: "inline-block",
    textTransform: "uppercase",
    letterSpacing: "0.1em",
    fontSize: 11,
    marginBottom: 8,
    color: palette.accentText,
    fontWeight: 600,
  },
  inputArea: {
    position: "relative",
    zIndex: 2,
    borderTop: `1px solid ${palette.border}`,
    padding: "10px 20px 18px",
    background: palette.glassStrong,
    backdropFilter: "blur(8px)",
    display: "flex",
    flexDirection: "column",
    gap: 10,
  },
  deepActionRow: {
    display: "flex",
    alignItems: "center",
    gap: 10,
  },
  deepInfoPill: {
    flex: 1,
    borderRadius: 999,
    border: `1px solid ${palette.border}`,
    background: palette.glassMuted,
    padding: "9px 14px",
  },
  deepInfoPillReady: {
    borderColor: palette.accentBorder,
    background: palette.accentSoft,
  },
  deepInfoText: {
    color: palette.muted,
    fontSize: 13,
  },
  deepRunButton: {
    borderRadius: 999,
    border: `1px solid ${palette.accentBorder}`,
    background: palette.deepBubble,
    color: palette.accentText,
    minHeight: 44,
    padding: "10px 18px",
    fontSize: 15,
    fontWeight: 600,
    cursor: "pointer",
  },
  deepRunButtonDisabled: {
    opacity: 0.58,
    cursor: "default",
  },
  textInputRow: {
    display: "flex",
    gap: 10,
  },
  textInput: {
    flex: 1,
    minHeight: 56,
    borderRadius: 22,
    border: `1px solid ${palette.border}`,
    background: palette.glass,
    color: palette.fg,
    fontSize: 18,
    padding: "14px 18px",
    outline: "none",
  },
  sendButton: {
    minWidth: 112,
    minHeight: 56,
    borderRadius: 999,
    border: "none",
    background: palette.accent,
    color: palette.accentInk,
    padding: "0 22px",
    fontSize: 16,
    fontWeight: 600,
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    cursor: "pointer",
  },
  sendButtonDisabled: {
    opacity: 0.55,
    cursor: "default",
  },
};
