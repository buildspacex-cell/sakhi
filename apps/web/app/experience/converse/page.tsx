"use client";

import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
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
  snippet?: string;
  topic_label?: string;
  topic_key?: string;
  decision_state?: string;
  hours_since?: number;
}

interface OffloadItem {
  clientId: string;
  text: string;
  createdAt: string;
  syncStatus: "saving" | "saved" | "error";
}

const DEEP_POLL_INTERVAL_MS = 2000;
const DEEP_POLL_MAX_ATTEMPTS = 70;
const LAST_MODE_KEY = "sakhi.web.lastEntryMode";

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
  if (chatResponse) return chatResponse;

  const topicLabel = String(result.topic_label || payload.topic_key || "this thread");
  const lines: string[] = [`Whole story on ${topicLabel}:`];

  const originStory = String(result.origin_story || "").trim();
  const keyPivots = Array.isArray(result.key_pivots) ? result.key_pivots : [];
  const currentStage = String(result.current_stage || "").trim();

  if (originStory) lines.push(`Start: ${originStory}`);
  if (typeof keyPivots[0] === "string" && keyPivots[0].trim()) lines.push(`Shift: ${keyPivots[0].trim()}`);
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

function getOffloadStatusLabel(status: OffloadItem["syncStatus"]): string {
  switch (status) {
    case "saving": return "Saving...";
    case "saved": return "Saved";
    case "error": return "Retry";
    default: return status;
  }
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
  const searchParams = useSearchParams();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const loadedHistoryForPersonRef = useRef<string | null>(null);

  const routeMode = searchParams?.get("mode") === "offload" ? "offload" : "talk";
  const isOffloadMode = routeMode === "offload";

  const [authUser, setAuthUser] = useState<AuthUser | null>(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [isHistoryLoading, setIsHistoryLoading] = useState(true);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [accountMenuOpen, setAccountMenuOpen] = useState(false);

  const [offloadItems, setOffloadItems] = useState<OffloadItem[]>([]);
  const [isSavingOffload, setIsSavingOffload] = useState(false);

  const [isRunningDeepAnswer, setIsRunningDeepAnswer] = useState(false);
  const [deepReflectionStatus, setDeepReflectionStatus] = useState("");
  const [activeContinuitySignal, setActiveContinuitySignal] = useState<ContinuitySignal | null>(null);
  const [latestUserMessage, setLatestUserMessage] = useState("");
  const [continuationPrompt, setContinuationPrompt] = useState<ContinuationPrompt | null>(null);
  const [showContinuationCard, setShowContinuationCard] = useState(false);
  const [openLoops, setOpenLoops] = useState<OpenLoopsData | null>(null);
  const [dismissedLoopIds, setDismissedLoopIds] = useState<Set<string>>(new Set());
  const [openLoopsPanelDismissed, setOpenLoopsPanelDismissed] = useState(false);
  const paywallNudgeFiredRef = useRef(false);

  // Persist mode preference so experience gate can resume it
  useEffect(() => {
    try { localStorage.setItem(LAST_MODE_KEY, routeMode); } catch { /* noop */ }
  }, [routeMode]);

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
    if (isOffloadMode || authLoading) return;
    if (!personId) { setIsHistoryLoading(false); return; }
    if (loadedHistoryForPersonRef.current === personId) { setIsHistoryLoading(false); return; }

    let cancelled = false;
    setIsHistoryLoading(true);

    const loadHistory = async () => {
      try {
        const params = new URLSearchParams({ user: personId, session_slug: "converse", limit: "20" });
        const response = await fetch(`/api/conversation/history?${params.toString()}`, { cache: "no-store" });
        if (!response.ok) return;

        const payload = (await response.json()) as { messages?: HistoryMessagePayload[] };
        const historyMessages = Array.isArray(payload.messages) ? payload.messages : [];
        const mappedMessages = historyMessages
          .map((message): Message | null => {
            const role = message.role === "sakhi" || message.role === "assistant"
              ? "sakhi"
              : message.role === "user" ? "user" : null;
            const content = String(message.content || "").trim();
            if (!role || !content) return null;
            return {
              id: String(message.id || `${role}-${content.slice(0, 12)}`),
              role,
              content,
              timestamp: message.created_at ? new Date(message.created_at) : new Date(),
              kind: "normal",
            };
          })
          .filter((message): message is Message => Boolean(message));

        if (cancelled) return;
        loadedHistoryForPersonRef.current = personId;
        setMessages((current) => (current.length === 0 ? mappedMessages : current));
      } catch {
        // fall back to empty state
      } finally {
        if (!cancelled) setIsHistoryLoading(false);
      }
    };

    void loadHistory();
    return () => { cancelled = true; };
  }, [authLoading, isOffloadMode, personId]);

  useEffect(() => {
    if (isOffloadMode || !personId) return;
    void fetch("/api/continuity/policy/enable", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ person_id: personId }),
    }).catch(() => { /* best-effort */ });
  }, [isOffloadMode, personId]);

  useEffect(() => {
    if (isOffloadMode || !personId || isHistoryLoading) return;
    const fetchPrompt = async () => {
      try {
        const res = await fetch(`/api/continuity/prompt?person_id=${encodeURIComponent(personId)}`, { cache: "no-store" });
        if (!res.ok) return;
        const data = (await res.json()) as ContinuationPrompt;
        if (data.has_continuation) { setContinuationPrompt(data); setShowContinuationCard(true); }
      } catch { /* best-effort */ }
    };
    void fetchPrompt();
  }, [isOffloadMode, personId, isHistoryLoading]);

  useEffect(() => {
    if (isOffloadMode || !personId || isHistoryLoading) return;
    const fetchOpenLoops = async () => {
      try {
        const res = await fetch(`/api/continuity/open-loops?person_id=${encodeURIComponent(personId)}`, { cache: "no-store" });
        if (!res.ok) return;
        const data = (await res.json()) as OpenLoopsData;
        if ((data.decisions?.length ?? 0) + (data.commitments?.length ?? 0) > 0) setOpenLoops(data);
      } catch { /* best-effort */ }
    };
    void fetchOpenLoops();
  }, [isOffloadMode, personId, isHistoryLoading]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const deepReflectSignal = activeContinuitySignal?.deep_reflect;
  const wholeStorySignal = activeContinuitySignal?.whole_story;
  const deepThreadLabel = activeContinuitySignal?.topic_label || activeContinuitySignal?.topic_key || "this thread";

  const wholeStoryTopics = useMemo(() => wholeStorySignal?.selected_topics || [], [wholeStorySignal?.selected_topics]);

  const wholeStorySelectedTopics = useMemo(() => {
    const primary = activeContinuitySignal?.topic_key || "";
    const normalized = wholeStoryTopics.map((topic) => String(topic || "").trim()).filter(Boolean);
    if (primary && !normalized.includes(primary)) normalized.unshift(primary);
    return normalized.slice(0, 3);
  }, [activeContinuitySignal?.topic_key, wholeStoryTopics]);

  const linkedWholeStoryReady = Boolean(wholeStorySignal?.ready && wholeStorySelectedTopics.length >= 2);
  const deepReflectReady = Boolean(deepReflectSignal?.ready);
  const hasDeepQuery = latestUserMessage.trim().length > 0;
  const deepAnswerReady = Boolean(activeContinuitySignal?.topic_key && hasDeepQuery && deepReflectReady);

  const deepStatusHint = (() => {
    if (!activeContinuitySignal?.topic_key) return "Deep Reflect will appear when this chat forms a clear thread.";
    if (!hasDeepQuery) return "Send one message to set your current question.";
    if (linkedWholeStoryReady) {
      const linked = wholeStorySelectedTopics.filter((t) => t !== activeContinuitySignal.topic_key).slice(0, 2).join(", ");
      if (linked) return `Deep Reflect is ready across ${deepThreadLabel} and ${linked}.`;
      return `Deep Reflect is ready with whole-story context for ${deepThreadLabel}.`;
    }
    if (deepReflectReady) return `Deep Reflect is ready for ${deepThreadLabel}. Linked threads will be woven in when clearly relevant.`;
    if (deepReflectSignal && !deepReflectSignal.ready) {
      const reason = deepReflectSignal.reason || "insufficient_depth";
      if (reason === "mirror_blocked") return "Deep Reflect will unlock once this thread is safe to mirror back clearly.";
      if (reason === "detail_blocked") return "Deep Reflect will unlock once this thread has enough detail to reflect back clearly.";
      if (reason === "insufficient_depth") return `Deep Reflect unlocks once this thread has at least ${deepReflectSignal.min_moments} moments to draw from.`;
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

  const switchMode = useCallback((newMode: "talk" | "offload") => {
    if (newMode === routeMode) return;
    router.replace(`/experience/converse?mode=${newMode}` as Route);
  }, [routeMode, router]);

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
    setShowContinuationCard(false);
    setOpenLoopsPanelDismissed(true);

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

        if (!paywallNudgeFiredRef.current) {
          try {
            const pwRes = await fetch(`/api/continuity/paywall-status?person_id=${encodeURIComponent(personId)}`, { cache: "no-store" });
            if (pwRes.ok) {
              const pw = await pwRes.json();
              if (pw.show_upgrade_cta) {
                paywallNudgeFiredRef.current = true;
                setMessages((prev) => [
                  ...prev,
                  {
                    id: `paywall-${Date.now()}`,
                    role: "sakhi" as const,
                    content: "You've built up real context here. Morning Review and What Changed — the parts that show you what shifted and what's still unresolved — are part of Sakhi Pro.",
                    timestamp: new Date(),
                    kind: "system" as const,
                  },
                ]);
              }
            }
          } catch { /* best-effort */ }
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
        setMessages((prev) => [
          ...prev,
          { id: `error-${Date.now()}`, role: "sakhi", content: `Something went wrong (${res.status}). Try again.`, timestamp: new Date(), kind: "system" },
        ]);
      }
    } catch (err: unknown) {
      clearTimeout(timeout);
      const isTimeout = err instanceof Error && err.name === "AbortError";
      const errorMsg = isTimeout
        ? "That took too long. Try again — sometimes the first message is slower."
        : `Connection issue: ${err instanceof Error ? err.message : "unknown"}`;
      setMessages((prev) => [
        ...prev,
        { id: `error-${Date.now()}`, role: "sakhi", content: errorMsg, timestamp: new Date(), kind: "system" },
      ]);
    } finally {
      setIsSending(false);
    }
  }, [inputText, isSending, personId]);

  const handleSaveOffload = useCallback(async () => {
    const text = inputText.trim();
    if (!text || !personId || isSavingOffload) return;

    const clientId = `offload-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    const now = new Date().toISOString();
    const item: OffloadItem = { clientId, text, createdAt: now, syncStatus: "saving" };

    setOffloadItems((prev) => [item, ...prev]);
    setInputText("");
    setIsSavingOffload(true);

    try {
      const res = await fetch(`/api/turn-v2?user=${encodeURIComponent(personId)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, capture_only: true, source: "offload", ts: now, client_id: clientId }),
      });
      setOffloadItems((prev) => prev.map((i) => i.clientId === clientId ? { ...i, syncStatus: res.ok ? "saved" : "error" } : i));
    } catch {
      setOffloadItems((prev) => prev.map((i) => i.clientId === clientId ? { ...i, syncStatus: "error" } : i));
    } finally {
      setIsSavingOffload(false);
    }
  }, [inputText, isSavingOffload, personId]);

  const pollDeepAnswer = useCallback(async (reflectionId: string, person: string): Promise<string | null> => {
    const fetchResult = async (): Promise<string | null> => {
      const params = new URLSearchParams({ id: reflectionId, person_id: person, t: String(Date.now()) });
      const resultRes = await fetch(`/api/continuity/reflection/result?${params.toString()}`, { cache: "no-store" });
      if (!resultRes.ok) return null;
      const resultData = (await resultRes.json()) as Record<string, unknown>;
      if (String(resultData.status || "queued") !== "done") return null;
      return formatDeepReflectionResult(resultData);
    };

    for (let attempt = 0; attempt < DEEP_POLL_MAX_ATTEMPTS; attempt += 1) {
      try {
        const statusParams = new URLSearchParams({ id: reflectionId, person_id: person, t: String(Date.now()) });
        const statusRes = await fetch(`/api/continuity/reflection/status?${statusParams.toString()}`, { cache: "no-store" });
        if (!statusRes.ok) break;
        const statusData = (await statusRes.json()) as Record<string, unknown>;
        const status = String(statusData.status || "queued");
        setDeepReflectionStatus(status);

        if (status === "done") return await fetchResult();
        if (status === "failed") return null;
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

    try { return await fetchResult(); } catch { return null; }
  }, []);

  const handleRunDeepAnswer = useCallback(async () => {
    if (!personId || !activeContinuitySignal?.topic_key || !hasDeepQuery || !deepAnswerReady || isRunningDeepAnswer) return;

    const selectedTopics = wholeStorySelectedTopics;
    const pendingId = `deep-pending-${Date.now()}`;

    setIsRunningDeepAnswer(true);
    setDeepReflectionStatus("queued");
    setMessages((prev) => [
      ...prev,
      {
        id: pendingId,
        role: "sakhi",
        content: selectedTopics.length >= 2
          ? "Deep Reflect is reading your whole story across linked threads..."
          : "Deep Reflect is reading the full story of this thread...",
        timestamp: new Date(),
        kind: "system",
      },
    ]);

    const removePending = () => setMessages((prev) => prev.filter((msg) => msg.id !== pendingId));

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

      if (!res.ok) throw new Error(`Deep answer request failed (${res.status})`);

      const data = (await res.json()) as Record<string, unknown>;
      const reflectionId = String(data.reflection_id || "");
      if (!reflectionId) throw new Error("Deep answer response missing reflection id");

      const deepReply = await pollDeepAnswer(reflectionId, personId);
      removePending();

      if (deepReply) {
        setMessages((prev) => [
          ...prev,
          { id: `deep-${Date.now()}`, role: "sakhi", content: deepReply, timestamp: new Date(), kind: "deep" },
        ]);
      } else {
        setMessages((prev) => [
          ...prev,
          { id: `deep-fail-${Date.now()}`, role: "sakhi", content: "Deep Reflect did not complete this time. Please try again.", timestamp: new Date(), kind: "system" },
        ]);
      }
    } catch (err) {
      removePending();
      setMessages((prev) => [
        ...prev,
        { id: `deep-error-${Date.now()}`, role: "sakhi", content: "Could not run Deep Reflect right now.", timestamp: new Date(), kind: "system" },
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

  const handleDismissLoop = useCallback((loopId: string) => {
    setDismissedLoopIds((prev) => new Set(Array.from(prev).concat(loopId)));
    void fetch(`/api/continuity/open-loops/${loopId}/resolve`, { method: "POST" });
  }, []);

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

  const isPrimaryEmpty = isOffloadMode ? offloadItems.length === 0 : !hasMessages;
  const modeSubcopy = isOffloadMode
    ? "Drop it. Sakhi picks it up."
    : "A quiet space to stay with what matters.";

  return (
    <div style={styles.container}>
      {/* Mode-aware ambient backdrop */}
      <div style={styles.backdropBase} aria-hidden>
        <div style={{ ...styles.backdropGlow, ...(isOffloadMode ? styles.backdropGlowOffload : styles.backdropGlowTalk) }} />
        <div style={{ ...styles.backdropWash, ...(isOffloadMode ? styles.backdropWashOffload : styles.backdropWashTalk) }} />
      </div>

      <header style={styles.header}>
        <div style={styles.headerLeft}>
          <div style={styles.brand}>Sakhi</div>
          <div style={styles.greeting}>
            {getGreeting()}
            {displayName ? `, ${displayName}` : ""}
          </div>
          <div style={styles.headerSubcopy}>{modeSubcopy}</div>
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

      <main style={{ ...styles.messagesArea, ...(isPrimaryEmpty ? styles.messagesAreaEmpty : {}) }}>
        {/* Open loops panel — talk mode only */}
        {!isOffloadMode && !openLoopsPanelDismissed && openLoops ? (
          <div style={styles.activeContextPanel}>
            <div style={styles.activeContextHeader}>
              <span style={styles.activeContextTitle}>Open threads</span>
              <button style={styles.activeContextDismissAll} onClick={() => setOpenLoopsPanelDismissed(true)}>×</button>
            </div>
            {openLoops.decisions.filter((l) => !dismissedLoopIds.has(l.id)).length > 0 ? (
              <div style={styles.activeContextSection}>
                <p style={styles.activeContextSectionLabel}>Unresolved decisions</p>
                {openLoops.decisions.filter((l) => !dismissedLoopIds.has(l.id)).map((loop) => (
                  <div key={loop.id} style={styles.activeContextItem}>
                    <span style={styles.activeContextItemText}>{loop.topic}</span>
                    <button style={styles.activeContextItemDismiss} onClick={() => handleDismissLoop(loop.id)} title="Mark resolved">✓</button>
                  </div>
                ))}
              </div>
            ) : null}
            {openLoops.commitments.filter((l) => !dismissedLoopIds.has(l.id)).length > 0 ? (
              <div style={styles.activeContextSection}>
                <p style={styles.activeContextSectionLabel}>Commitments you made</p>
                {openLoops.commitments.filter((l) => !dismissedLoopIds.has(l.id)).map((loop) => (
                  <div key={loop.id} style={styles.activeContextItem}>
                    <span style={styles.activeContextItemText}>{loop.topic}</span>
                    <button style={styles.activeContextItemDismiss} onClick={() => handleDismissLoop(loop.id)} title="Mark done">✓</button>
                  </div>
                ))}
              </div>
            ) : null}
          </div>
        ) : null}

        {/* Offload mode */}
        {isOffloadMode ? (
          offloadItems.length === 0 ? (
            <div style={styles.emptyState}>
              <p style={{ ...styles.emptyPrompt, fontSize: "28px" }}>Drop it. No response needed.</p>
              <p style={styles.emptyHint}>Nothing is sent back to you here. Drops are saved and processed quietly.</p>
            </div>
          ) : (
            <div style={styles.offloadList}>
              {offloadItems.map((item) => (
                <div key={item.clientId} style={styles.offloadCard}>
                  <div style={styles.offloadCardHeader}>
                    <span style={styles.offloadTimestamp}>{formatOffloadTimestamp(item.createdAt)}</span>
                    <span style={{
                      ...styles.offloadStatusPill,
                      ...(item.syncStatus === "error" ? styles.offloadStatusPillWarning : {}),
                      ...(item.syncStatus === "saving" ? styles.offloadStatusPillMuted : {}),
                    }}>
                      {getOffloadStatusLabel(item.syncStatus)}
                    </span>
                  </div>
                  <p style={styles.offloadText}>{item.text}</p>
                </div>
              ))}
            </div>
          )
        ) : (
          /* Talk mode */
          <>
            {showContinuationCard && continuationPrompt ? (
              <div style={styles.continuationCard}>
                <p style={styles.continuationText}>{continuationPrompt.display}</p>
                <div style={styles.continuationActions}>
                  <button
                    style={styles.continuationCta}
                    onClick={() => {
                      setShowContinuationCard(false);
                      (document.querySelector("input[type=text]") as HTMLInputElement | null)?.focus();
                    }}
                  >
                    Continue →
                  </button>
                  <button style={styles.continuationDismiss} onClick={() => setShowContinuationCard(false)}>
                    Dismiss
                  </button>
                </div>
              </div>
            ) : null}
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
                        ...(isUser ? styles.userBubble : isSystem ? styles.systemBubble : isDeep ? styles.deepBubble : styles.sakhiBubble),
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
                {deepAnswerReady && !isSending ? (
                  <button
                    style={{ ...styles.deepInlineCard, ...(isRunningDeepAnswer ? { opacity: 0.75 } : {}) }}
                    onClick={() => void handleRunDeepAnswer()}
                    disabled={isRunningDeepAnswer}
                  >
                    <span style={styles.deepInlineIcon}>✦</span>
                    <span style={styles.deepInlineText}>
                      {isRunningDeepAnswer
                        ? (linkedWholeStoryReady ? "Reading across threads..." : "Reading your thread...")
                        : "Deep Dive"}
                    </span>
                  </button>
                ) : null}
              </>
            )}
          </>
        )}
        <div ref={messagesEndRef} />
      </main>

      <section style={styles.inputArea}>
        {/* Talk / Drop mode rail */}
        <div style={{ ...styles.footerModeRail, ...(isOffloadMode ? styles.footerModeRailOffload : styles.footerModeRailTalk) }}>
          <button
            style={{
              ...styles.footerModePill,
              ...(!isOffloadMode ? styles.footerModePillTalkActive : {}),
            }}
            onClick={() => switchMode("talk")}
          >
            <span style={{ ...styles.footerModePillText, ...(!isOffloadMode ? styles.footerModePillTextActive : {}) }}>
              Talk
            </span>
          </button>
          <button
            style={{
              ...styles.footerModePill,
              ...(isOffloadMode ? styles.footerModePillOffloadActive : {}),
            }}
            onClick={() => switchMode("offload")}
          >
            <span style={{ ...styles.footerModePillText, ...(isOffloadMode ? styles.footerModePillTextActive : {}) }}>
              Drop
            </span>
          </button>
        </div>

        {/* Deep action row — talk mode, has messages */}
        {!isOffloadMode && hasMessages ? (
          <div style={styles.deepActionRow}>
            <div style={{ ...styles.deepInfoPill, ...(deepAnswerReady ? styles.deepInfoPillReady : {}) }}>
              <span style={styles.deepInfoText}>{deepStatusHint}</span>
            </div>
            <button
              style={{ ...styles.deepRunButton, ...((!deepAnswerReady || isRunningDeepAnswer) ? styles.deepRunButtonDisabled : {}) }}
              onClick={() => void handleRunDeepAnswer()}
              disabled={!deepAnswerReady || isRunningDeepAnswer}
              title={deepReflectionStatus || undefined}
            >
              {isRunningDeepAnswer ? "Reading..." : "Run Deep"}
            </button>
          </div>
        ) : null}

        {/* Mode-specific input */}
        {isOffloadMode ? (
          <div style={styles.offloadInputRow}>
            <textarea
              value={inputText}
              placeholder="Drop it here."
              onChange={(e) => setInputText(e.target.value)}
              style={styles.offloadTextarea}
              disabled={isSavingOffload}
            />
            <button
              onClick={() => void handleSaveOffload()}
              disabled={!inputText.trim() || isSavingOffload}
              style={{
                ...styles.offloadSaveButton,
                ...(!inputText.trim() || isSavingOffload ? styles.sendButtonDisabled : {}),
              }}
            >
              {isSavingOffload ? "Saving..." : "Save"}
            </button>
          </div>
        ) : (
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
        )}
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
  backdropBase: {
    position: "absolute",
    inset: 0,
    overflow: "hidden",
    zIndex: 0,
    pointerEvents: "none",
  },
  backdropGlow: {
    position: "absolute",
    width: "400px",
    height: "400px",
    borderRadius: "50%",
  },
  backdropGlowTalk: {
    top: "40px",
    right: "-80px",
    background: "rgba(120, 171, 255, 0.09)",
  },
  backdropGlowOffload: {
    top: "60px",
    left: "-80px",
    background: "rgba(196, 166, 105, 0.09)",
  },
  backdropWash: {
    position: "absolute",
    left: 0,
    right: 0,
    height: "240px",
  },
  backdropWashTalk: {
    top: 0,
    background: "rgba(31, 49, 81, 0.12)",
  },
  backdropWashOffload: {
    bottom: 0,
    background: "rgba(72, 58, 31, 0.1)",
  },
  header: {
    position: "relative",
    zIndex: 2,
    borderBottom: `1px solid ${palette.border}`,
    padding: "16px 20px 12px",
    display: "flex",
    alignItems: "flex-start",
    justifyContent: "space-between",
    gap: 14,
  },
  headerLeft: {
    display: "flex",
    flexDirection: "column",
    gap: 4,
  },
  brand: {
    textTransform: "uppercase",
    letterSpacing: "0.18em",
    fontSize: 12,
    color: palette.muted,
  },
  greeting: {
    fontSize: 22,
    lineHeight: 1.1,
    fontWeight: 520,
    color: palette.fg,
    letterSpacing: "-0.02em",
  },
  headerSubcopy: {
    fontSize: 13,
    lineHeight: "18px",
    color: palette.muted,
    marginTop: 2,
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
    fontFamily: editorialFontFamily,
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
    fontFamily: editorialFontFamily,
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
  messagesAreaEmpty: {
    justifyContent: "center",
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
  continuationCard: {
    margin: "0 auto 16px",
    width: "100%",
    maxWidth: 620,
    borderRadius: 12,
    border: `1px solid ${palette.accent}40`,
    backgroundColor: `${palette.accent}0d`,
    padding: "14px 18px",
  },
  continuationText: {
    margin: 0,
    fontSize: 14,
    lineHeight: "21px",
    color: palette.fg,
  },
  continuationActions: {
    display: "flex",
    gap: 12,
    marginTop: 10,
    alignItems: "center",
  },
  continuationCta: {
    background: "none",
    border: "none",
    padding: 0,
    fontSize: 13,
    fontWeight: 600,
    color: palette.accent,
    cursor: "pointer",
    letterSpacing: "0.3px",
    fontFamily: editorialFontFamily,
  },
  continuationDismiss: {
    background: "none",
    border: "none",
    padding: 0,
    fontSize: 12,
    color: palette.muted,
    cursor: "pointer",
    fontFamily: editorialFontFamily,
  },
  emptyPrompt: {
    fontSize: 38,
    lineHeight: 1.1,
    letterSpacing: "-0.025em",
    margin: 0,
    color: palette.fg,
    fontWeight: 500,
  },
  emptyHint: {
    margin: "14px auto 0",
    fontSize: 17,
    lineHeight: 1.4,
    color: palette.muted,
    maxWidth: 560,
  },
  offloadList: {
    display: "flex",
    flexDirection: "column",
    gap: 12,
    width: "100%",
    maxWidth: 620,
    margin: "0 auto",
  },
  offloadCard: {
    borderRadius: 20,
    border: `1px solid ${palette.border}`,
    background: palette.sakhiBubble,
    padding: "14px 16px",
    display: "flex",
    flexDirection: "column",
    gap: 10,
  },
  offloadCardHeader: {
    display: "flex",
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
    border: `1px solid ${palette.accentBorder}`,
    background: palette.accentSoft,
    padding: "4px 10px",
    fontSize: 11,
    fontWeight: 600,
    color: palette.fg,
  },
  offloadStatusPillMuted: {
    borderColor: palette.border,
    background: palette.glassMuted,
  },
  offloadStatusPillWarning: {
    borderColor: "rgba(239, 111, 126, 0.35)",
    background: "rgba(88, 33, 44, 0.36)",
  },
  offloadText: {
    margin: 0,
    fontSize: 15,
    lineHeight: "22px",
    color: palette.fg,
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
  deepInlineCard: {
    alignSelf: "flex-start",
    display: "inline-flex",
    alignItems: "center",
    gap: 7,
    marginBottom: 4,
    padding: "10px 16px",
    borderRadius: 999,
    border: `1px solid ${palette.accentBorder}`,
    background: palette.deepBubble,
    cursor: "pointer",
    fontFamily: editorialFontFamily,
  },
  deepInlineIcon: {
    fontSize: 12,
    color: palette.accentText,
  },
  deepInlineText: {
    fontSize: 13,
    fontWeight: 700,
    color: palette.accentText,
    letterSpacing: "0.2px",
  },
  inputArea: {
    position: "relative",
    zIndex: 2,
    borderTop: `1px solid ${palette.border}`,
    padding: "10px 16px 20px",
    background: palette.glassStrong,
    backdropFilter: "blur(8px)",
    display: "flex",
    flexDirection: "column",
    gap: 10,
  },
  footerModeRail: {
    display: "flex",
    gap: 6,
    padding: "5px",
    borderRadius: 999,
    border: "1px solid",
  },
  footerModeRailTalk: {
    borderColor: "rgba(120, 171, 255, 0.2)",
    background: "rgba(18, 25, 39, 0.9)",
  },
  footerModeRailOffload: {
    borderColor: "rgba(196, 166, 105, 0.22)",
    background: "rgba(31, 26, 19, 0.92)",
  },
  footerModePill: {
    flex: 1,
    minHeight: 38,
    borderRadius: 999,
    border: "none",
    background: "transparent",
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontFamily: editorialFontFamily,
    transition: "background 150ms ease",
  },
  footerModePillTalkActive: {
    background: "rgba(120, 171, 255, 0.2)",
  },
  footerModePillOffloadActive: {
    background: "rgba(196, 166, 105, 0.22)",
  },
  footerModePillText: {
    fontSize: 13,
    fontWeight: 700,
    color: palette.subtle,
  },
  footerModePillTextActive: {
    color: palette.fg,
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
    fontFamily: editorialFontFamily,
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
    minHeight: 52,
    borderRadius: 22,
    border: `1px solid ${palette.border}`,
    background: palette.glass,
    color: palette.fg,
    fontSize: 16,
    padding: "14px 18px",
    outline: "none",
    fontFamily: editorialFontFamily,
  },
  sendButton: {
    minWidth: 100,
    minHeight: 52,
    borderRadius: 999,
    border: "none",
    background: palette.accent,
    color: palette.accentInk,
    padding: "0 20px",
    fontSize: 15,
    fontWeight: 600,
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    cursor: "pointer",
    fontFamily: editorialFontFamily,
  },
  sendButtonDisabled: {
    opacity: 0.55,
    cursor: "default",
  },
  offloadInputRow: {
    display: "flex",
    flexDirection: "column",
    gap: 10,
  },
  offloadTextarea: {
    width: "100%",
    minHeight: 110,
    borderRadius: 20,
    border: `1px solid ${palette.border}`,
    background: palette.glass,
    color: palette.fg,
    fontSize: 16,
    padding: "14px 18px",
    outline: "none",
    resize: "none",
    fontFamily: editorialFontFamily,
    lineHeight: "22px",
    boxSizing: "border-box",
  },
  offloadSaveButton: {
    alignSelf: "flex-end",
    minHeight: 44,
    borderRadius: 999,
    border: "none",
    background: palette.accent,
    color: palette.accentInk,
    padding: "0 24px",
    fontSize: 14,
    fontWeight: 700,
    cursor: "pointer",
    fontFamily: editorialFontFamily,
  },
  activeContextPanel: {
    margin: "0 auto 16px",
    width: "100%",
    maxWidth: 620,
    borderRadius: 14,
    border: `1px solid ${palette.border}`,
    background: palette.glassStrong,
    padding: "14px 16px",
    display: "flex",
    flexDirection: "column",
    gap: 12,
  },
  activeContextHeader: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
  },
  activeContextTitle: {
    fontSize: 11,
    textTransform: "uppercase" as const,
    letterSpacing: "0.12em",
    color: palette.muted,
    fontWeight: 600,
  },
  activeContextDismissAll: {
    background: "none",
    border: "none",
    color: palette.muted,
    fontSize: 18,
    lineHeight: 1,
    cursor: "pointer",
    padding: "0 2px",
    fontFamily: editorialFontFamily,
  },
  activeContextSection: {
    display: "flex",
    flexDirection: "column",
    gap: 6,
  },
  activeContextSectionLabel: {
    margin: 0,
    fontSize: 11,
    color: palette.muted,
    letterSpacing: "0.06em",
    textTransform: "uppercase" as const,
  },
  activeContextItem: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 10,
    borderRadius: 8,
    border: `1px solid ${palette.border}`,
    background: palette.glassMuted,
    padding: "9px 12px",
  },
  activeContextItemText: {
    fontSize: 14,
    lineHeight: 1.4,
    color: palette.fg,
    flex: 1,
  },
  activeContextItemDismiss: {
    background: "none",
    border: "none",
    color: palette.muted,
    fontSize: 15,
    cursor: "pointer",
    padding: "0 4px",
    flexShrink: 0,
    fontFamily: editorialFontFamily,
  },
};
