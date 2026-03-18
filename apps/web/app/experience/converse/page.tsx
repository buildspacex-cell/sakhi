"use client";

import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import type React from "react";
import type { Route } from "next";

export const dynamic = "force-dynamic";

const palette = {
  bg: "#060a13",
  fg: "#f5f7fb",
  muted: "#a7b0c0",
  border: "rgba(231, 239, 255, 0.16)",
  glass: "rgba(20, 28, 40, 0.72)",
  userBubble: "rgba(62, 87, 132, 0.58)",
  sakhiBubble: "rgba(27, 36, 54, 0.9)",
  deepBubble: "rgba(72, 57, 36, 0.9)",
  systemBubble: "rgba(32, 38, 48, 0.74)",
  accent: "#d08b4e",
  accentDim: "rgba(208, 139, 78, 0.28)",
};

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

  const [authUser, setAuthUser] = useState<AuthUser | null>(null);
  const [authLoading, setAuthLoading] = useState(true);
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
          setAuthUser({
            person_id: data.person_id,
            full_name: data.full_name,
            email: data.email,
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

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const personId = authUser?.person_id || "";
  const hasMessages = messages.length > 0;

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

  const wholeStoryReady = Boolean(wholeStorySignal?.ready && wholeStorySelectedTopics.length >= 2);
  const hasDeepQuery = latestUserMessage.trim().length > 0;
  const deepAnswerReady = Boolean(activeContinuitySignal?.topic_key && hasDeepQuery && wholeStoryReady);

  const deepStatusHint = (() => {
    if (!activeContinuitySignal?.topic_key) {
      return "Deep Reflect will appear when this chat forms a clear thread.";
    }
    if (!hasDeepQuery) {
      return "Send one message to set your current question.";
    }
    if (wholeStoryReady) {
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
    if (wholeStorySignal && !wholeStorySignal.ready) {
      const reason = wholeStorySignal.reason || "insufficient_depth";
      if (reason === "insufficient_overlap") {
        return "Deep Reflect is waiting for clearer links across your active threads.";
      }
      if (reason === "threads_inactive") {
        return "Deep Reflect will unlock after more recent activity across related threads.";
      }
      if (reason === "insufficient_depth") {
        return "Deep Reflect unlocks once this thread has deeper linked history.";
      }
      return "Deep Reflect unlocks once this thread has enough linked history.";
    }
    return "Deep Reflect unlocks once a second thread clearly links to this one.";
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
      || !wholeStoryReady
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
        content: "Deep Reflect is reading your whole story across linked threads...",
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
    wholeStoryReady,
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
      <div style={styles.auroraA} />
      <div style={styles.auroraB} />

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
              <button style={styles.accountItem} onClick={() => openAccountRoute("/experience/reflection")}>Reflection</button>
              <button style={styles.accountItem} onClick={() => openAccountRoute("/experience/settings")}>Settings</button>
              <button style={styles.accountItem} onClick={() => openAccountRoute("/experience/support")}>Support Console</button>
              <button style={{ ...styles.accountItem, color: "#f0b8c0" }} onClick={() => void handleSignOut()}>Sign out</button>
            </div>
          ) : null}
        </div>
      </header>

      <main style={styles.messagesArea}>
        {!hasMessages ? (
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
    background: palette.bg,
    color: palette.fg,
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Inter, sans-serif',
    display: "flex",
    flexDirection: "column",
    position: "relative",
    overflow: "hidden",
  },
  auroraA: {
    position: "absolute",
    top: -130,
    right: -120,
    width: 340,
    height: 340,
    borderRadius: "50%",
    background: "rgba(114, 206, 239, 0.14)",
    pointerEvents: "none",
  },
  auroraB: {
    position: "absolute",
    bottom: 100,
    left: -100,
    width: 280,
    height: 280,
    borderRadius: "50%",
    background: "rgba(255, 190, 124, 0.11)",
    pointerEvents: "none",
  },
  header: {
    position: "relative",
    zIndex: 2,
    borderBottom: `1px solid ${palette.border}`,
    padding: "20px 24px 14px",
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 16,
  },
  headerLeft: {
    display: "flex",
    flexDirection: "column",
    gap: 6,
  },
  brand: {
    textTransform: "uppercase",
    letterSpacing: "0.18em",
    fontSize: 13,
    color: palette.muted,
  },
  greeting: {
    fontSize: 40,
    lineHeight: 1.1,
    fontWeight: 560,
    color: palette.fg,
  },
  accountTrigger: {
    borderRadius: 999,
    border: `1px solid ${palette.border}`,
    background: "rgba(255,255,255,0.08)",
    color: palette.fg,
    padding: "8px 14px",
    display: "inline-flex",
    alignItems: "center",
    gap: 8,
    fontSize: 15,
    cursor: "pointer",
  },
  accountMenu: {
    position: "absolute",
    right: 0,
    top: "calc(100% + 10px)",
    minWidth: 200,
    borderRadius: 16,
    border: `1px solid ${palette.border}`,
    background: "rgba(14, 20, 31, 0.97)",
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
    fontSize: 14,
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
    padding: "22px 24px 12px",
    display: "flex",
    flexDirection: "column",
    gap: 14,
  },
  emptyState: {
    margin: "auto",
    textAlign: "center",
    maxWidth: 620,
  },
  emptyPrompt: {
    fontSize: 52,
    lineHeight: 1.08,
    letterSpacing: "-0.03em",
    margin: 0,
    color: palette.fg,
    fontWeight: 520,
  },
  emptyHint: {
    margin: "18px auto 0",
    fontSize: 26,
    lineHeight: 1.25,
    color: palette.muted,
    maxWidth: 700,
  },
  bubble: {
    maxWidth: "78%",
    borderRadius: 22,
    border: `1px solid ${palette.border}`,
    padding: "14px 16px",
    whiteSpace: "pre-wrap",
  },
  userBubble: {
    alignSelf: "flex-end",
    background: palette.userBubble,
  },
  sakhiBubble: {
    alignSelf: "flex-start",
    background: palette.sakhiBubble,
  },
  deepBubble: {
    alignSelf: "flex-start",
    background: palette.deepBubble,
    borderColor: "rgba(225, 186, 130, 0.3)",
  },
  systemBubble: {
    alignSelf: "center",
    background: palette.systemBubble,
  },
  bubbleText: {
    fontSize: 17,
    lineHeight: 1.55,
    color: palette.fg,
  },
  deepBadge: {
    display: "inline-block",
    textTransform: "uppercase",
    letterSpacing: "0.1em",
    fontSize: 11,
    marginBottom: 8,
    color: "#f5dcb2",
    fontWeight: 600,
  },
  inputArea: {
    position: "relative",
    zIndex: 2,
    borderTop: `1px solid ${palette.border}`,
    padding: "12px 24px 20px",
    background: "rgba(8, 12, 18, 0.95)",
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
    border: `1px solid rgba(183, 198, 230, 0.24)`,
    background: "rgba(8, 18, 39, 0.62)",
    padding: "9px 14px",
  },
  deepInfoPillReady: {
    borderColor: "rgba(208, 139, 78, 0.52)",
    background: "rgba(61, 45, 24, 0.5)",
  },
  deepInfoText: {
    color: palette.muted,
    fontSize: 14,
  },
  deepRunButton: {
    borderRadius: 999,
    border: `1px solid rgba(215, 175, 118, 0.6)`,
    background: "rgba(74, 58, 36, 0.75)",
    color: "#f5dcb2",
    padding: "10px 18px",
    fontSize: 16,
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
    borderRadius: 26,
    border: `1px solid ${palette.border}`,
    background: "rgba(6, 16, 34, 0.8)",
    color: palette.fg,
    fontSize: 22,
    padding: "14px 18px",
    outline: "none",
  },
  sendButton: {
    borderRadius: 999,
    border: "none",
    background: palette.accent,
    color: "#fff",
    padding: "0 22px",
    fontSize: 18,
    fontWeight: 600,
    cursor: "pointer",
  },
  sendButtonDisabled: {
    opacity: 0.55,
    cursor: "default",
  },
};
