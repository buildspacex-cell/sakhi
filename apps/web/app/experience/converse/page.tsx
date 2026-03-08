"use client";

import { Suspense, useState, useEffect, useRef, useCallback, useMemo } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import type React from "react";
import type { Route } from "next";
import DebugPanel from "./DebugPanel";
import { useVoice, type VoiceState } from "@/lib/hooks/useVoice";

export const dynamic = "force-dynamic";

const palette = {
  bg: "#0e0f12",
  fg: "#f4f4f5",
  muted: "#a1a1aa",
  accent: "#6366f1",
  accentHover: "#818cf8",
  cardBg: "#18191d",
  border: "#27272a",
  userBubble: "#27272a",
  sakhiBubble: "#1e1e24",
  success: "#22c55e",
  pulse: "rgba(99, 102, 241, 0.4)",
};

// =============================================================================
// TYPES
// =============================================================================

interface MessageInsight {
  reasoning?: string;
  memories?: Array<{ text: string; type?: string; score?: number }>;
  stateContext?: {
    friction_state?: string;
    drift_percentage?: number;
    why_this_advice?: string;
  };
}

interface Message {
  id: string;
  role: "user" | "sakhi";
  content: string;
  timestamp: Date;
  source?: "text" | "voice";
  // Agent task related
  isTaskPlan?: boolean;
  taskPlan?: TaskPlan;
  isApprovalRequest?: boolean;
  approvalRequest?: ApprovalRequest;
  // Insight data for transparency
  insight?: MessageInsight;
}

interface TaskPlan {
  task_id: string;
  task_type: string;
  steps: TaskStep[];
  estimated_duration: number;
  formatted_plan: string;
}

interface TaskStep {
  step_number: number;
  action: string;
  description: string;
  requires_approval?: boolean;
}

interface ApprovalRequest {
  request_id: string;
  action_type: string;
  action_description: string;
  risk_level: string;
  context_summary: string;
  options: { label: string; value: string }[];
}

interface AgentTaskContext {
  new_task?: TaskPlan;
  awaiting_confirmation?: boolean;
  execution?: {
    task_id: string;
    status: string;
    current_step: number;
    total_steps: number;
    message: string;
    pending_approval?: {
      step: number;
      action: string;
      description: string;
      request_id: string;
    };
  };
  confirmed?: boolean;
  rejected?: boolean;
  message?: string;
}

interface AuthUser {
  person_id: string;
  full_name: string | null;
  email: string;
}

interface FrictionState {
  friction_state: string | null;
  friction_name: string | null;
  drift_percentage: number | null;
  severity: string | null;
}

interface ContinuityPolicyState {
  enabled: boolean;
  exclusions: Array<{ source?: string; id?: string }>;
}

interface ContinuityPackDebug {
  topic_key: string;
  topic_label?: string;
  arc_compact?: {
    start_signal?: string;
    pivots_signal?: string;
    current_signal?: string;
  };
}

type DeepReflectionRunMode = "deep_answer" | "topic_reflection";

// =============================================================================
// COMPONENT
// =============================================================================

export default function ConversePage() {
  return (
    <Suspense fallback={null}>
      <ConverseContent />
    </Suspense>
  );
}

function ConverseContent() {
  const router = useRouter();
  const search = useSearchParams();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auth state
  const [authUser, setAuthUser] = useState<AuthUser | null>(null);
  const [authLoading, setAuthLoading] = useState(true);

  // Conversation state
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [showTextInput, setShowTextInput] = useState(false);
  const [historyLoaded, setHistoryLoaded] = useState(false);
  const [voiceStatus, setVoiceStatus] = useState<string>("");

  // FAB state
  const [fabOpen, setFabOpen] = useState(false);

  // Expanded insights state (tracks which messages have insights panel open)
  const [expandedInsights, setExpandedInsights] = useState<Set<string>>(new Set());

  // Debug panel state
  const [showDebug, setShowDebug] = useState(false);
  const [lastResponseDebug, setLastResponseDebug] = useState<Record<string, unknown> | null>(null);

  // Friction state for UX indicator
  const [frictionState, setFrictionState] = useState<FrictionState | null>(null);
  const [continuityPolicy, setContinuityPolicy] = useState<ContinuityPolicyState | null>(null);
  const [isUpdatingContinuity, setIsUpdatingContinuity] = useState(false);
  const [activeContinuityPack, setActiveContinuityPack] = useState<ContinuityPackDebug | null>(null);
  const [isRunningDeepReflection, setIsRunningDeepReflection] = useState(false);
  const [deepReflectionStatus, setDeepReflectionStatus] = useState<string>("");
  const [deepReflectionMode, setDeepReflectionMode] = useState<DeepReflectionRunMode | null>(null);

  // Agent task state
  const [activeTask, setActiveTask] = useState<AgentTaskContext | null>(null);
  const [isPollingApprovals, setIsPollingApprovals] = useState(false);

  // Voice hook - add messages from voice interactions
  const addVoiceMessage = useCallback((role: "user" | "sakhi", content: string) => {
    const message: Message = {
      id: `voice-${Date.now()}-${role}`,
      role,
      content,
      timestamp: new Date(),
      source: "voice",
    };
    setMessages((prev) => [...prev, message]);
  }, []);

  const voice = useVoice({
    personId: authUser?.person_id || "",
    autoPlayResponse: true,
    onTranscript: (transcript) => {
      if (transcript.isFinal && transcript.text) {
        addVoiceMessage("user", transcript.text);
      }
    },
    onResponse: (response) => {
      if (response.text) {
        addVoiceMessage("sakhi", response.text);
        setLastResponseDebug((prev) => ({
          ...prev,
          voice_response: response.text,
        }));
      }
    },
    onStateChange: (state) => {
      const statusMap: Record<VoiceState, string> = {
        idle: "",
        recording: "Listening...",
        processing: "Thinking...",
        speaking: "Speaking...",
        error: "Error occurred",
      };
      setVoiceStatus(statusMap[state]);
    },
    onError: (error) => {
      console.error("Voice error:", error);
      setVoiceStatus(`Error: ${error.message}`);
      setTimeout(() => setVoiceStatus(""), 3000);
    },
  });

  // Load auth user
  useEffect(() => {
    const loadAuth = async () => {
      try {
        const res = await fetch("/api/auth/me");
        if (res.ok) {
          const data = await res.json();
          setAuthUser({
            person_id: data.person_id,
            full_name: data.full_name,
            email: data.email,
          });
        }
      } catch (err) {
        console.error("Auth error:", err);
      } finally {
        setAuthLoading(false);
      }
    };
    loadAuth();
  }, []);

  const latestUserMessage = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i -= 1) {
      const item = messages[i];
      if (item.role === "user") {
        const text = String(item.content || "").trim();
        if (text) return text;
      }
    }
    return "";
  }, [messages]);

  const loadContinuityPolicy = useCallback(async () => {
    if (!authUser?.person_id) return;
    try {
      const res = await fetch(
        `/api/continuity/policy?person_id=${encodeURIComponent(authUser.person_id)}`,
      );
      if (!res.ok) return;
      const data = await res.json();
      setContinuityPolicy({
        enabled: !!data.enabled,
        exclusions: Array.isArray(data.exclusions) ? data.exclusions : [],
      });
    } catch (err) {
      console.error("Continuity policy load error:", err);
    }
  }, [authUser?.person_id]);

  useEffect(() => {
    if (!authUser?.person_id) return;
    void loadContinuityPolicy();
  }, [authUser?.person_id, loadContinuityPolicy]);

  // Track previous friction state for change notifications
  const prevFrictionStateRef = useRef<string | null>(null);

  // Load friction state for indicator
  useEffect(() => {
    if (!authUser?.person_id) return;

    const loadFrictionState = async () => {
      try {
        const res = await fetch("/api/friction/state");
        if (res.ok) {
          const data = await res.json();
          const newState = data.friction_state;
          const prevState = prevFrictionStateRef.current;

          // Check for significant state change
          if (prevState && newState && prevState !== newState && prevState !== "balanced") {
            // State changed - add a notification message
            const stateMessages: Record<string, string> = {
              chaos: "I notice you seem more scattered than usual. Would you like some grounding suggestions?",
              intensity: "Your energy seems heightened right now. Might be a good time for some cooling practices.",
              stagnation: "I sense some heaviness today. How about we get things moving?",
              balanced: "You're looking more balanced now. Nice work taking care of yourself.",
            };

            const notificationMessage: Message = {
              id: `state-change-${Date.now()}`,
              role: "sakhi",
              content: stateMessages[newState] || `Your state has shifted to ${data.friction_name || newState}.`,
              timestamp: new Date(),
              source: "text",
              insight: {
                stateContext: {
                  friction_state: newState,
                  drift_percentage: data.drift_percentage,
                },
              },
            };

            setMessages((prev) => {
              // Don't add if we already have a recent state change message
              const recentStateMsg = prev.find(
                (m) => m.id.startsWith("state-change-") &&
                       Date.now() - m.timestamp.getTime() < 5 * 60 * 1000
              );
              if (recentStateMsg) return prev;
              return [...prev, notificationMessage];
            });
          }

          prevFrictionStateRef.current = newState;
          setFrictionState({
            friction_state: newState,
            friction_name: data.friction_name,
            drift_percentage: data.drift_percentage,
            severity: data.severity,
          });
        }
      } catch (err) {
        console.error("Friction state error:", err);
      }
    };

    loadFrictionState();

    // Refresh friction state every 5 minutes
    const interval = setInterval(loadFrictionState, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, [authUser?.person_id]);

  // Load conversation history when auth is ready
  useEffect(() => {
    if (!authUser?.person_id || historyLoaded) return;

    const loadHistory = async () => {
      try {
        const res = await fetch(
          `/api/conversation/history?user=${encodeURIComponent(authUser.person_id)}&limit=20`
        );
        if (res.ok) {
          const data = await res.json();
          if (data.messages && data.messages.length > 0) {
            const loadedMessages: Message[] = data.messages.map(
              (msg: { role: string; content: string; source?: string }, idx: number) => ({
                id: `history-${idx}`,
                // Map 'assistant' or 'sakhi' to 'sakhi' for display, everything else is 'user'
                role: (msg.role === "sakhi" || msg.role === "assistant") ? "sakhi" : "user",
                content: msg.content,
                timestamp: new Date(), // Loaded messages don't have exact timestamps
                source: (msg.source as "text" | "voice") || "text",
              })
            );
            setMessages(loadedMessages);
          }
        }
      } catch (err) {
        console.error("Error loading conversation history:", err);
      } finally {
        setHistoryLoaded(true);
      }
    };
    loadHistory();
  }, [authUser?.person_id, historyLoaded]);

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Poll for approval requests during task execution
  useEffect(() => {
    if (!isPollingApprovals || !authUser?.person_id) return;

    const pollApprovals = async () => {
      try {
        const res = await fetch(
          `/api/agent/approvals/pending?user=${encodeURIComponent(authUser.person_id)}`
        );
        if (res.ok) {
          const data = await res.json();

          // Check active tasks for status updates (failed, completed)
          if (data.active_tasks && data.active_tasks.length > 0) {
            const task = data.active_tasks[0];

            // Handle failed status
            if (task.status === "failed") {
              const failedMessage: Message = {
                id: `task-failed-${task.task_id}`,
                role: "sakhi",
                content: `I ran into an issue: ${task.error || "Task could not be completed"}. Would you like me to try again?`,
                timestamp: new Date(),
                source: "text",
              };
              setMessages((prev) => {
                if (prev.some((m) => m.id === failedMessage.id)) return prev;
                return [...prev, failedMessage];
              });
              setActiveTask(null);
              setIsPollingApprovals(false);
              return;
            }

            // Handle completed status
            if (task.status === "completed") {
              const completedMessage: Message = {
                id: `task-completed-${task.task_id}`,
                role: "sakhi",
                content: `Done! Completed all ${task.total_steps} steps successfully.`,
                timestamp: new Date(),
                source: "text",
              };
              setMessages((prev) => {
                if (prev.some((m) => m.id === completedMessage.id)) return prev;
                return [...prev, completedMessage];
              });
              setActiveTask(null);
              setIsPollingApprovals(false);
              return;
            }
          }

          // Check for pending approvals
          if (data.pending && data.pending.length > 0) {
            const approval = data.pending[0];
            // Add approval message if not already shown
            const approvalMessage: Message = {
              id: `approval-${approval.request_id}`,
              role: "sakhi",
              content: `**${approval.context_summary}**\n\n${approval.action_description}\n\nShould I proceed?`,
              timestamp: new Date(),
              source: "text",
              isApprovalRequest: true,
              approvalRequest: approval,
            };
            setMessages((prev) => {
              // Check if we already have this approval message
              if (prev.some((m) => m.id === approvalMessage.id)) return prev;
              return [...prev, approvalMessage];
            });
          }
        }
      } catch (err) {
        console.error("Error polling approvals:", err);
      }
    };

    // Poll every 2 seconds
    const interval = setInterval(pollApprovals, 2000);
    pollApprovals(); // Initial poll

    return () => clearInterval(interval);
  }, [isPollingApprovals, authUser?.person_id]);

  // Handle approval response
  const handleApprovalResponse = useCallback(
    async (requestId: string, approved: boolean) => {
      if (!authUser?.person_id) return;

      try {
        const res = await fetch(
          `/api/agent/approvals/${requestId}/respond?user=${encodeURIComponent(authUser.person_id)}`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ approved }),
          }
        );

        if (res.ok) {
          const data = await res.json();

          // Add response message
          const responseMessage: Message = {
            id: Date.now().toString(),
            role: "sakhi",
            content: approved
              ? "Got it! Proceeding with the action..."
              : "No problem, I'll skip this step.",
            timestamp: new Date(),
            source: "text",
          };
          setMessages((prev) => [...prev, responseMessage]);

          // Continue polling or stop
          if (data.task_completed) {
            setIsPollingApprovals(false);
            setActiveTask(null);
          }
        }
      } catch (err) {
        console.error("Error responding to approval:", err);
      }
    },
    [authUser?.person_id]
  );

  const formatDeepReflectionResult = useCallback((payload: Record<string, unknown>) => {
    const result = (payload.result as Record<string, unknown> | undefined) || {};
    const chatResponse = String(result.chat_response || "").trim();
    if (chatResponse) {
      return chatResponse;
    }
    const topicLabel = String(result.topic_label || payload.topic_key || "this thread");
    const lines = [`Deep reflection on ${topicLabel}:`];

    const originStory = String(result.origin_story || "").trim();
    const keyPivots = Array.isArray(result.key_pivots) ? result.key_pivots : [];
    const currentStage = String(result.current_stage || "").trim();
    const recurringTensions = Array.isArray(result.recurring_tensions)
      ? result.recurring_tensions
      : [];

    if (originStory) lines.push(`Start: ${originStory}`);
    if (typeof keyPivots[0] === "string" && keyPivots[0].trim()) {
      lines.push(`Pivot: ${keyPivots[0].trim()}`);
    }
    if (currentStage) lines.push(`Current: ${currentStage}`);
    if (typeof recurringTensions[0] === "string" && recurringTensions[0].trim()) {
      lines.push(`Recurring: ${recurringTensions[0].trim()}`);
    }

    return lines.join("\n");
  }, []);

  const pollDeepReflection = useCallback(
    async (reflectionId: string) => {
      const fetchResult = async () => {
        const nonce = Date.now();
        const resultRes = await fetch(
          `/api/continuity/reflection/result?id=${encodeURIComponent(reflectionId)}&t=${nonce}`,
          { cache: "no-store" },
        );
        if (!resultRes.ok) return null;
        return (await resultRes.json()) as Record<string, unknown>;
      };

      for (let attempt = 0; attempt < 60; attempt += 1) {
        try {
          const statusNonce = Date.now();
          const statusRes = await fetch(
            `/api/continuity/reflection/status?id=${encodeURIComponent(reflectionId)}&t=${statusNonce}`,
            { cache: "no-store" },
          );
          if (!statusRes.ok) break;
          const statusData = await statusRes.json();
          const status = String(statusData.status || "queued");
          setDeepReflectionStatus(status);

          if (status === "done") {
            const resultData = await fetchResult();
            if (resultData) {
              setMessages((prev) => [
                ...prev,
                {
                  id: `reflection-${Date.now()}`,
                  role: "sakhi",
                  content: formatDeepReflectionResult(resultData),
                  timestamp: new Date(),
                  source: "text",
                },
              ]);
            }
            setIsRunningDeepReflection(false);
            setDeepReflectionStatus("");
            return;
          }

          if (status === "failed") {
            setMessages((prev) => [
              ...prev,
              {
                id: `reflection-failed-${Date.now()}`,
                role: "sakhi",
                content: "Deep reflection could not complete for this thread.",
                timestamp: new Date(),
                source: "text",
              },
            ]);
            setIsRunningDeepReflection(false);
            setDeepReflectionStatus("");
            return;
          }

          if (attempt % 3 === 0) {
            const resultData = await fetchResult();
            const resultStatus = String(resultData?.status || "queued");
            if (resultData && resultStatus === "done") {
              setMessages((prev) => [
                ...prev,
                {
                  id: `reflection-${Date.now()}`,
                  role: "sakhi",
                  content: formatDeepReflectionResult(resultData),
                  timestamp: new Date(),
                  source: "text",
                },
              ]);
              setIsRunningDeepReflection(false);
              setDeepReflectionStatus("");
              return;
            }
          }
        } catch (err) {
          console.error("Deep reflection poll error:", err);
          break;
        }

        await new Promise((resolve) => setTimeout(resolve, 2000));
      }

      const finalResult = await fetchResult().catch(() => null);
      if (finalResult && String(finalResult.status || "queued") === "done") {
        setMessages((prev) => [
          ...prev,
          {
            id: `reflection-${Date.now()}`,
            role: "sakhi",
            content: formatDeepReflectionResult(finalResult),
            timestamp: new Date(),
            source: "text",
          },
        ]);
      }

      setIsRunningDeepReflection(false);
      setDeepReflectionStatus("");
    },
    [formatDeepReflectionResult]
  );

  const handleRunDeepReflection = useCallback(async (mode: DeepReflectionRunMode) => {
    if (!authUser?.person_id || !activeContinuityPack?.topic_key || isRunningDeepReflection) return;
    const queryText = mode === "deep_answer" ? latestUserMessage : "";
    if (mode === "deep_answer" && !queryText) return;

    setIsRunningDeepReflection(true);
    setDeepReflectionStatus("queued");
    setDeepReflectionMode(mode);

    try {
      const res = await fetch("/api/continuity/reflection/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          person_id: authUser.person_id,
          topic_key: activeContinuityPack.topic_key,
          window: "3650d",
          mode,
          user_query: mode === "deep_answer" ? queryText : undefined,
        }),
      });
      if (!res.ok) {
        throw new Error(`Reflection request failed (${res.status})`);
      }
      const data = await res.json();
      setDeepReflectionStatus(String(data.status || "queued"));
      void pollDeepReflection(String(data.reflection_id || ""));
    } catch (err) {
      console.error("Deep reflection run error:", err);
      setIsRunningDeepReflection(false);
      setDeepReflectionStatus("");
      setDeepReflectionMode(null);
    }
  }, [
    activeContinuityPack?.topic_key,
    authUser?.person_id,
    isRunningDeepReflection,
    latestUserMessage,
    pollDeepReflection,
  ]);

  const handleContinuityToggle = useCallback(async () => {
    if (!authUser?.person_id || isUpdatingContinuity) return;

    setIsUpdatingContinuity(true);
    try {
      const nextEnabled = !Boolean(continuityPolicy?.enabled);
      const res = await fetch("/api/continuity/policy", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          person_id: authUser.person_id,
          enabled: nextEnabled,
          exclusions: continuityPolicy?.exclusions || [],
        }),
      });
      if (!res.ok) {
        throw new Error(`Continuity update failed (${res.status})`);
      }
      const data = await res.json();
      setContinuityPolicy({
        enabled: !!data.enabled,
        exclusions: Array.isArray(data.exclusions) ? data.exclusions : [],
      });
      if (!data.enabled) {
        setActiveContinuityPack(null);
      }
    } catch (err) {
      console.error("Continuity update error:", err);
    } finally {
      setIsUpdatingContinuity(false);
    }
  }, [
    authUser?.person_id,
    continuityPolicy?.enabled,
    continuityPolicy?.exclusions,
    isUpdatingContinuity,
  ]);

  // Send message to API
  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim() || !authUser?.person_id) return;

      const userMessage: Message = {
        id: Date.now().toString(),
        role: "user",
        content: text.trim(),
        timestamp: new Date(),
        source: "text",
      };

      setMessages((prev) => [...prev, userMessage]);
      setInputText("");
      setIsSending(true);

      try {
        const res = await fetch(
          `/api/turn-v2?user=${encodeURIComponent(authUser.person_id)}&debug=1`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text: text.trim(), source: "text" }),
          }
        );

        if (res.ok) {
          const data = await res.json();
          // Store the full response for debug panel, normalizing backend shape
          // Backend puts debug info in debug_data; DebugPanel reads from debug
          const debugData = data.debug_data || {};
          const internalState = debugData.internal_state || {};
          const engineDebug = debugData.conversation_engine_debug || {};
          const continuityPack = (debugData.continuity_pack ||
            engineDebug.metadata?.continuity_pack ||
            null) as ContinuityPackDebug | null;

          // Parse recall_context string into structured memory_recall array
          // Format: "- [type] text (s=0.85)\n"
          const recallStr = engineDebug.recall_context || "";
          const parsedRecalls = recallStr
            .split("\n")
            .filter((line: string) => line.startsWith("- ["))
            .map((line: string) => {
              const typeMatch = line.match(/\[(\w+)\]/);
              const scoreMatch = line.match(/\(s=([\d.]+)\)/);
              const textMatch = line.match(/\]\s*(.+?)(?:\s*\(s=|$)/);
              return {
                type: typeMatch?.[1] || "unknown",
                text: textMatch?.[1]?.trim() || line,
                score: scoreMatch ? parseFloat(scoreMatch[1]) : 0,
              };
            });

          setLastResponseDebug({
            ...data,
            input_text: text.trim(),
            // Map internal_state fields to top level for DebugPanel
            operating_system: internalState.operating_system || data.operating_system,
            dosha_baseline: internalState.dosha_baseline || data.dosha_baseline,
            life_context: internalState.life_context || data.life_context,
            decision_profile: internalState.decision_profile || data.decision_profile,
            // Engine states live in debug_data, DebugPanel reads from top level
            behavior_profile: engineDebug.metadata?.behavior_profile || data.behavior_profile,
            tone_state: debugData.tone_state || data.tone_state,
            continuity: engineDebug.metadata?.continuity || data.continuity,
            continuity_pack: continuityPack,
            // Parse recall data from engine debug string into structured format
            memory_recall: parsedRecalls.length > 0 ? parsedRecalls : data.memory_recall,
            // Map debug_data to debug key that DebugPanel expects
            debug: {
              conversation_engine_debug: engineDebug,
              adaptive_response: data.adaptive_response,
              adaptive_error: engineDebug.adaptive_error,
              used_fallback: engineDebug.used_fallback,
            },
          });

          setActiveContinuityPack(
            continuityPack && continuityPack.topic_key ? continuityPack : null,
          );

          // Handle agent task context
          const taskContext = data.agent_task_context as AgentTaskContext | null;
          if (taskContext) {
            setActiveTask(taskContext);

            // If there's a new task plan, show it as a special message
            if (taskContext.new_task) {
              const planMessage: Message = {
                id: (Date.now() + 1).toString(),
                role: "sakhi",
                content: taskContext.new_task.formatted_plan,
                timestamp: new Date(),
                source: "text",
                isTaskPlan: true,
                taskPlan: taskContext.new_task,
              };
              setMessages((prev) => [...prev, planMessage]);
              return; // Don't add the regular reply
            }

            // If task is executing and waiting for approval
            if (taskContext.execution?.status === "waiting_approval") {
              const approvalMessage: Message = {
                id: (Date.now() + 1).toString(),
                role: "sakhi",
                content: taskContext.execution.message,
                timestamp: new Date(),
                source: "text",
                isApprovalRequest: true,
              };
              setMessages((prev) => [...prev, approvalMessage]);
              setIsPollingApprovals(true);
              return;
            }

            // If task was rejected
            if (taskContext.rejected) {
              const cancelMessage: Message = {
                id: (Date.now() + 1).toString(),
                role: "sakhi",
                content: taskContext.message || "No problem, I've cancelled that.",
                timestamp: new Date(),
                source: "text",
              };
              setMessages((prev) => [...prev, cancelMessage]);
              setActiveTask(null);
              return;
            }

            // If task was confirmed and started
            if (taskContext.confirmed && taskContext.execution) {
              const startMessage: Message = {
                id: (Date.now() + 1).toString(),
                role: "sakhi",
                content: taskContext.execution.message,
                timestamp: new Date(),
                source: "text",
              };
              setMessages((prev) => [...prev, startMessage]);

              // Handle no_agent status - agent not connected
              if (taskContext.execution.status === "no_agent") {
                setActiveTask(null);
                return;
              }

              // Handle failed status
              if (taskContext.execution.status === "failed") {
                setActiveTask(null);
                return;
              }

              // Start polling if execution is in progress
              if (taskContext.execution.status === "running" ||
                  taskContext.execution.status === "waiting_approval") {
                setIsPollingApprovals(true);
              }
              return;
            }
          }

          if (data.reply) {
            // Extract insight data for transparency
            const insight: MessageInsight = {};

            // Get reasoning from adaptive response or reasoning field
            const adaptiveReasoning = data.adaptive_response?.strategy?.reasoning;
            const debugData = data.debug_data as Record<string, any> | undefined;
            const directReasoning = data.reasoning?.summary || data.reasoning?.explanation
              || debugData?.reasoning?.summary || debugData?.reasoning?.explanation;
            if (adaptiveReasoning || directReasoning) {
              insight.reasoning = adaptiveReasoning || directReasoning;
            }

            // Get memories used
            if (data.memory_recall && Array.isArray(data.memory_recall) && data.memory_recall.length > 0) {
              insight.memories = data.memory_recall.slice(0, 3).map((m: { text?: string; content?: string; type?: string; score?: number }) => ({
                text: m.text || m.content || "",
                type: m.type,
                score: m.score,
              })).filter((m: { text: string }) => m.text);
            }

            // Get state context if available
            if (data.adaptive_response?.context) {
              insight.stateContext = {
                friction_state: data.adaptive_response.context.friction_state,
                drift_percentage: data.adaptive_response.context.drift_percentage,
                why_this_advice: data.adaptive_response.strategy?.why,
              };
            }

            const sakhiMessage: Message = {
              id: (Date.now() + 1).toString(),
              role: "sakhi",
              content: data.reply,
              timestamp: new Date(),
              source: "text",
              insight: Object.keys(insight).length > 0 ? insight : undefined,
            };
            setMessages((prev) => [...prev, sakhiMessage]);
          }
        }
      } catch (err) {
        console.error("Send error:", err);
      } finally {
        setIsSending(false);
      }
    },
    [authUser?.person_id]
  );

  // Handle task confirmation (must be after sendMessage)
  const handleTaskConfirmation = useCallback(
    async (confirmed: boolean) => {
      if (!authUser?.person_id) return;

      // Send confirmation as a message
      const confirmText = confirmed ? "Yes, go ahead" : "No, cancel";
      await sendMessage(confirmText);
      setActiveTask(null);
    },
    [authUser?.person_id, sendMessage]
  );

  // Handle voice recording
  const toggleVoice = useCallback(async () => {
    if (voice.isRecording) {
      await voice.stopRecording();
    } else if (voice.isSpeaking) {
      voice.stopPlayback();
    } else if (!voice.isProcessing) {
      await voice.startRecording();
    }
  }, [voice]);

  // Handle text submit
  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      sendMessage(inputText);
    },
    [inputText, sendMessage]
  );

  // FAB navigation
  const navigateTo = useCallback(
    (path: string) => {
      setFabOpen(false);
      const userId = authUser?.person_id || "";
      router.push(`${path}?user=${encodeURIComponent(userId)}` as Route);
    },
    [router, authUser?.person_id]
  );

  const handleSignOut = useCallback(async () => {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.replace("/experience" as Route);
  }, [router]);

  // Get greeting based on time
  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return "Good morning";
    if (hour < 17) return "Good afternoon";
    return "Good evening";
  };

  const displayName = authUser?.full_name?.split(" ")[0] || "";

  // =============================================================================
  // STYLES
  // =============================================================================

  const containerStyle: React.CSSProperties = {
    height: "100vh",
    background: palette.bg,
    color: palette.fg,
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Inter, sans-serif',
    display: "flex",
    flexDirection: "column",
    overflow: "hidden",
  };

  const headerStyle: React.CSSProperties = {
    padding: "20px 24px 16px",
    borderBottom: `1px solid ${palette.border}`,
    position: "sticky",
    top: 0,
    background: palette.bg,
    zIndex: 10,
  };

  const brandStyle: React.CSSProperties = {
    fontSize: "14px",
    letterSpacing: "0.12em",
    textTransform: "uppercase",
    color: palette.muted,
    marginBottom: "4px",
  };

  const greetingStyle: React.CSSProperties = {
    fontSize: "18px",
    color: palette.fg,
    fontWeight: 500,
  };

  // Friction state indicator styles
  const getFrictionColors = () => {
    if (!frictionState?.friction_state) {
      return { bg: palette.border, text: palette.muted, dot: palette.muted };
    }
    switch (frictionState.friction_state) {
      case "chaos":
        return { bg: "#3b1f5e", text: "#c084fc", dot: "#a855f7" }; // Purple for Vata
      case "intensity":
        return { bg: "#5e1f2e", text: "#f87171", dot: "#ef4444" }; // Red for Pitta
      case "stagnation":
        return { bg: "#1f3d5e", text: "#60a5fa", dot: "#3b82f6" }; // Blue for Kapha
      case "balanced":
        return { bg: "#1f5e3d", text: "#4ade80", dot: "#22c55e" }; // Green for balanced
      default:
        return { bg: palette.border, text: palette.muted, dot: palette.muted };
    }
  };

  const frictionColors = getFrictionColors();

  const frictionIndicatorStyle: React.CSSProperties = {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    padding: "6px 12px",
    borderRadius: "16px",
    background: frictionColors.bg,
    fontSize: "12px",
    color: frictionColors.text,
    marginTop: "8px",
    width: "fit-content",
    cursor: "pointer",
    transition: "all 200ms ease",
  };

  const frictionDotStyle: React.CSSProperties = {
    width: "8px",
    height: "8px",
    borderRadius: "50%",
    background: frictionColors.dot,
  };

  const messagesContainerStyle: React.CSSProperties = {
    flex: 1,
    padding: "24px",
    overflowY: "auto",
    display: "flex",
    flexDirection: "column",
    gap: "16px",
  };

  const emptyStateStyle: React.CSSProperties = {
    flex: 1,
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    textAlign: "center",
    padding: "48px 24px",
    gap: "20px",
  };

  const emptyPromptStyle: React.CSSProperties = {
    fontSize: "16px",
    color: palette.muted,
    lineHeight: 1.6,
    maxWidth: "280px",
  };

  const messageStyle = (role: "user" | "sakhi"): React.CSSProperties => ({
    maxWidth: "85%",
    padding: "14px 18px",
    borderRadius: "18px",
    fontSize: "15px",
    lineHeight: 1.6,
    alignSelf: role === "user" ? "flex-end" : "flex-start",
    background: role === "user" ? palette.userBubble : palette.sakhiBubble,
    color: palette.fg,
  });

  const inputAreaStyle: React.CSSProperties = {
    padding: "16px 24px 32px",
    borderTop: `1px solid ${palette.border}`,
    background: palette.bg,
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: "16px",
  };

  // Voice button colors based on state
  const getVoiceButtonColors = () => {
    if (voice.isRecording) {
      return { border: "#ef4444", bg: "#ef4444", color: "#fff" }; // Red for recording
    }
    if (voice.isProcessing) {
      return { border: "#f59e0b", bg: "#f59e0b", color: "#fff" }; // Amber for processing
    }
    if (voice.isSpeaking) {
      return { border: "#22c55e", bg: "#22c55e", color: "#fff" }; // Green for speaking
    }
    return { border: palette.muted, bg: "transparent", color: palette.fg }; // Default
  };

  const voiceColors = getVoiceButtonColors();
  const isVoiceActive = voice.isRecording || voice.isProcessing || voice.isSpeaking;

  const micButtonStyle: React.CSSProperties = {
    width: "64px",
    height: "64px",
    borderRadius: "50%",
    border: `2px solid ${voiceColors.border}`,
    background: voiceColors.bg,
    color: voiceColors.color,
    cursor: voice.isProcessing ? "wait" : "pointer",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    transition: "all 200ms ease",
    position: "relative",
  };

  const pulseStyle: React.CSSProperties = {
    position: "absolute",
    width: "80px",
    height: "80px",
    borderRadius: "50%",
    background: voice.isRecording
      ? "rgba(239, 68, 68, 0.4)" // Red pulse for recording
      : voice.isSpeaking
      ? "rgba(34, 197, 94, 0.4)" // Green pulse for speaking
      : palette.pulse,
    animation: isVoiceActive ? "pulse 1.5s ease-in-out infinite" : "none",
    pointerEvents: "none",
  };

  const textToggleStyle: React.CSSProperties = {
    fontSize: "13px",
    color: palette.muted,
    cursor: "pointer",
    textDecoration: "underline",
  };

  const textInputContainerStyle: React.CSSProperties = {
    width: "100%",
    display: "flex",
    gap: "12px",
  };

  const textInputStyle: React.CSSProperties = {
    flex: 1,
    padding: "14px 18px",
    borderRadius: "24px",
    border: `1px solid ${palette.border}`,
    background: palette.cardBg,
    color: palette.fg,
    fontSize: "15px",
    outline: "none",
  };

  const sendButtonStyle: React.CSSProperties = {
    padding: "14px 24px",
    borderRadius: "24px",
    border: "none",
    background: palette.accent,
    color: "#fff",
    fontSize: "15px",
    cursor: "pointer",
    opacity: inputText.trim() ? 1 : 0.5,
  };

  // FAB styles
  const fabContainerStyle: React.CSSProperties = {
    position: "fixed",
    bottom: "200px",
    right: "24px",
    zIndex: 100,
    display: "flex",
    flexDirection: "column",
    alignItems: "flex-end",
    gap: "12px",
  };

  const fabButtonStyle: React.CSSProperties = {
    width: "56px",
    height: "56px",
    borderRadius: "50%",
    border: "none",
    background: palette.cardBg,
    color: palette.fg,
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    boxShadow: "0 4px 12px rgba(0, 0, 0, 0.3)",
    transition: "all 200ms ease",
  };

  const fabOptionStyle: React.CSSProperties = {
    display: "flex",
    alignItems: "center",
    gap: "12px",
    padding: "12px 16px",
    borderRadius: "12px",
    background: palette.cardBg,
    color: palette.fg,
    cursor: "pointer",
    boxShadow: "0 4px 12px rgba(0, 0, 0, 0.3)",
    fontSize: "14px",
    whiteSpace: "nowrap",
    transition: "all 200ms ease",
    transform: fabOpen ? "translateX(0) scale(1)" : "translateX(20px) scale(0.9)",
    opacity: fabOpen ? 1 : 0,
    pointerEvents: fabOpen ? "auto" : "none",
  };

  // =============================================================================
  // RENDER
  // =============================================================================

  if (authLoading || (!historyLoaded && authUser?.person_id)) {
    return (
      <div style={{ ...containerStyle, alignItems: "center", justifyContent: "center" }}>
        <p style={{ color: palette.muted }}>Loading...</p>
      </div>
    );
  }

  return (
    <div style={containerStyle}>
      <style>{`
        @keyframes pulse {
          0% { transform: scale(0.9); opacity: 0.7; }
          50% { transform: scale(1.1); opacity: 0.3; }
          100% { transform: scale(0.9); opacity: 0.7; }
        }
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>

      {/* Header */}
      <header style={headerStyle}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
              <div style={brandStyle}>Sakhi</div>
              <button
                onClick={handleSignOut}
                style={{
                  background: "none",
                  border: "none",
                  color: palette.muted,
                  fontSize: "12px",
                  cursor: "pointer",
                  padding: "2px 0",
                  opacity: 0.6,
                }}
              >
                Sign out
              </button>
            </div>
            <div style={greetingStyle}>
              {getGreeting()}
              {displayName && `, ${displayName}`}
            </div>
            <div
              style={{
                display: "flex",
                flexWrap: "wrap",
                gap: "8px",
                marginTop: "10px",
              }}
            >
              <button
                onClick={() => {
                  void handleContinuityToggle();
                }}
                disabled={!authUser?.person_id || isUpdatingContinuity}
                style={{
                  background: continuityPolicy?.enabled ? "rgba(34, 197, 94, 0.12)" : palette.cardBg,
                  border: `1px solid ${continuityPolicy?.enabled ? "rgba(34, 197, 94, 0.35)" : palette.border}`,
                  color: continuityPolicy?.enabled ? palette.success : palette.muted,
                  fontSize: "12px",
                  cursor: authUser?.person_id && !isUpdatingContinuity ? "pointer" : "default",
                  padding: "6px 10px",
                  borderRadius: "999px",
                }}
              >
                {isUpdatingContinuity
                  ? "Updating continuity..."
                  : `Continuity ${continuityPolicy?.enabled ? "On" : "Off"}`}
              </button>

              {continuityPolicy?.enabled && activeContinuityPack?.topic_key && (
                <>
                  <span
                    style={{
                      background: "rgba(99, 102, 241, 0.12)",
                      border: `1px solid rgba(99, 102, 241, 0.3)`,
                      color: palette.fg,
                      fontSize: "12px",
                      padding: "6px 10px",
                      borderRadius: "999px",
                    }}
                  >
                    Using continuity: {activeContinuityPack.topic_label || activeContinuityPack.topic_key}
                  </span>
                  <button
                    onClick={() => {
                      void handleRunDeepReflection("deep_answer");
                    }}
                    disabled={isRunningDeepReflection || !latestUserMessage}
                    style={{
                      background: palette.cardBg,
                      border: `1px solid ${palette.border}`,
                      color: palette.fg,
                      fontSize: "12px",
                      cursor: isRunningDeepReflection || !latestUserMessage ? "default" : "pointer",
                      padding: "6px 10px",
                      borderRadius: "999px",
                      opacity: isRunningDeepReflection || !latestUserMessage ? 0.7 : 1,
                    }}
                    title={latestUserMessage ? "Run deep answer with current query + full history" : "Send a user message first to run Deep Answer"}
                  >
                    {isRunningDeepReflection && deepReflectionMode === "deep_answer"
                      ? `Deep Answer: ${deepReflectionStatus || "running"}`
                      : "Run Deep Answer"}
                  </button>
                  <button
                    onClick={() => {
                      void handleRunDeepReflection("topic_reflection");
                    }}
                    disabled={isRunningDeepReflection}
                    style={{
                      background: palette.cardBg,
                      border: `1px solid ${palette.border}`,
                      color: palette.fg,
                      fontSize: "12px",
                      cursor: isRunningDeepReflection ? "default" : "pointer",
                      padding: "6px 10px",
                      borderRadius: "999px",
                      opacity: isRunningDeepReflection ? 0.7 : 1,
                    }}
                    title="Run longitudinal topic reflection without requiring a current query"
                  >
                    {isRunningDeepReflection && deepReflectionMode === "topic_reflection"
                      ? `Topic Reflection: ${deepReflectionStatus || "running"}`
                      : "Run Topic Reflection"}
                  </button>
                </>
              )}
            </div>
          </div>
          {/* Friction State Indicator */}
          {frictionState && (
            <div
              style={frictionIndicatorStyle}
              onClick={() => navigateTo("/experience/me")}
              title={`${frictionState.friction_name || "Your State"}: ${frictionState.drift_percentage?.toFixed(0) || 0}% drift from baseline. Click to see more.`}
            >
              <div style={frictionDotStyle} />
              <span>
                {frictionState.friction_state === "balanced"
                  ? "Balanced"
                  : frictionState.friction_name?.replace(" Friction", "") || "Loading..."}
              </span>
              {frictionState.drift_percentage != null && frictionState.drift_percentage > 10 && (
                <span style={{ opacity: 0.7, fontSize: "11px" }}>
                  {frictionState.drift_percentage.toFixed(0)}%
                </span>
              )}
            </div>
          )}
        </div>
      </header>

      {/* Messages */}
      <div style={messagesContainerStyle}>
        {messages.length === 0 ? (
          <div style={emptyStateStyle}>
              <p style={emptyPromptStyle}>
                This is a quiet space to unload your mind.
                <br />
                <br />
                Say whatever is present — you don&apos;t need to sort it.
              </p>
            </div>
        ) : (
          <>
            {messages.map((msg) => (
              <div key={msg.id} style={messageStyle(msg.role)}>
                {msg.source === "voice" && (
                  <svg
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke={palette.muted}
                    strokeWidth="1.5"
                    style={{
                      width: 12,
                      height: 12,
                      marginRight: 6,
                      display: "inline",
                      verticalAlign: "middle",
                      opacity: 0.6,
                    }}
                  >
                    <rect x="9" y="3" width="6" height="11" rx="3" />
                    <path d="M5 10v2a7 7 0 0 0 14 0v-2" />
                  </svg>
                )}
                {/* Task Plan Icon */}
                {msg.isTaskPlan && (
                  <svg
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke={palette.accent}
                    strokeWidth="1.5"
                    style={{
                      width: 14,
                      height: 14,
                      marginRight: 8,
                      display: "inline",
                      verticalAlign: "middle",
                    }}
                  >
                    <rect x="3" y="3" width="18" height="18" rx="2" />
                    <path d="M7 8h10M7 12h6M7 16h8" strokeLinecap="round" />
                  </svg>
                )}
                {/* State Change Notification Icon */}
                {msg.id.startsWith("state-change-") && (
                  <svg
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke={palette.accent}
                    strokeWidth="1.5"
                    style={{
                      width: 14,
                      height: 14,
                      marginRight: 8,
                      display: "inline",
                      verticalAlign: "middle",
                    }}
                  >
                    <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" strokeLinecap="round" />
                  </svg>
                )}
                {/* Approval Icon */}
                {msg.isApprovalRequest && (
                  <svg
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="#f59e0b"
                    strokeWidth="1.5"
                    style={{
                      width: 14,
                      height: 14,
                      marginRight: 8,
                      display: "inline",
                      verticalAlign: "middle",
                    }}
                  >
                    <circle cx="12" cy="12" r="9" />
                    <path d="M12 8v4M12 16h.01" strokeLinecap="round" />
                  </svg>
                )}
                <span style={{ whiteSpace: "pre-wrap" }}>{msg.content}</span>

                {/* State Change - Quick Link to Me Page */}
                {msg.id.startsWith("state-change-") && (
                  <button
                    onClick={() => navigateTo("/experience/me")}
                    style={{
                      display: "block",
                      marginTop: "10px",
                      background: "transparent",
                      border: `1px solid ${palette.accent}`,
                      color: palette.accent,
                      fontSize: "12px",
                      padding: "6px 12px",
                      borderRadius: "16px",
                      cursor: "pointer",
                    }}
                  >
                    View your wellness profile
                  </button>
                )}

                {/* Insight Section - Why this response? */}
                {msg.role === "sakhi" && msg.insight && (msg.insight.reasoning || msg.insight.memories?.length) && (
                  <div style={{ marginTop: "12px" }}>
                    <button
                      onClick={() => {
                        setExpandedInsights((prev) => {
                          const next = new Set(prev);
                          if (next.has(msg.id)) {
                            next.delete(msg.id);
                          } else {
                            next.add(msg.id);
                          }
                          return next;
                        });
                      }}
                      style={{
                        background: "transparent",
                        border: "none",
                        color: palette.muted,
                        fontSize: "11px",
                        cursor: "pointer",
                        padding: "4px 0",
                        display: "flex",
                        alignItems: "center",
                        gap: "4px",
                      }}
                    >
                      <svg
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1.5"
                        style={{
                          width: 12,
                          height: 12,
                          transform: expandedInsights.has(msg.id) ? "rotate(90deg)" : "none",
                          transition: "transform 150ms ease",
                        }}
                      >
                        <path d="M9 18l6-6-6-6" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                      Why this response?
                    </button>

                    {expandedInsights.has(msg.id) && (
                      <div
                        style={{
                          marginTop: "8px",
                          padding: "12px",
                          background: "rgba(99, 102, 241, 0.08)",
                          borderRadius: "8px",
                          fontSize: "12px",
                          lineHeight: "1.5",
                        }}
                      >
                        {/* Reasoning */}
                        {msg.insight.reasoning && (
                          <div style={{ marginBottom: msg.insight.memories?.length ? "10px" : 0 }}>
                            <div style={{ color: palette.accent, fontWeight: 500, marginBottom: "4px", fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.5px" }}>
                              Reasoning
                            </div>
                            <div style={{ color: palette.fg, opacity: 0.9 }}>
                              {msg.insight.reasoning}
                            </div>
                          </div>
                        )}

                        {/* Memories Used */}
                        {msg.insight.memories && msg.insight.memories.length > 0 && (
                          <div>
                            <div style={{ color: palette.accent, fontWeight: 500, marginBottom: "4px", fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.5px" }}>
                              I remembered...
                            </div>
                            <ul style={{ margin: 0, paddingLeft: "16px", color: palette.fg, opacity: 0.9 }}>
                              {msg.insight.memories.map((mem, idx) => (
                                <li key={idx} style={{ marginBottom: "4px" }}>
                                  {mem.text.length > 100 ? `${mem.text.slice(0, 100)}...` : mem.text}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {/* State Context */}
                        {msg.insight.stateContext?.friction_state && (
                          <div style={{ marginTop: "10px", paddingTop: "10px", borderTop: `1px solid ${palette.border}` }}>
                            <div style={{ color: palette.muted, fontSize: "11px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                              <span>
                                Your current state: <span style={{ color: palette.fg }}>{msg.insight.stateContext.friction_state}</span>
                                {msg.insight.stateContext.drift_percentage != null && msg.insight.stateContext.drift_percentage > 10 && (
                                  <span> ({msg.insight.stateContext.drift_percentage.toFixed(0)}% drift)</span>
                                )}
                              </span>
                              <button
                                onClick={() => navigateTo("/experience/me")}
                                style={{
                                  background: "transparent",
                                  border: "none",
                                  color: palette.accent,
                                  fontSize: "11px",
                                  cursor: "pointer",
                                  textDecoration: "underline",
                                }}
                              >
                                See full profile
                              </button>
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}

                {/* Task Plan Confirmation Buttons */}
                {msg.isTaskPlan && msg.taskPlan && (
                  <div style={{
                    display: "flex",
                    gap: "10px",
                    marginTop: "16px",
                    paddingTop: "12px",
                    borderTop: `1px solid ${palette.border}`,
                  }}>
                    <button
                      onClick={() => handleTaskConfirmation(true)}
                      style={{
                        padding: "10px 20px",
                        borderRadius: "20px",
                        border: "none",
                        background: palette.accent,
                        color: "#fff",
                        fontSize: "14px",
                        cursor: "pointer",
                        fontWeight: 500,
                      }}
                    >
                      Yes, proceed
                    </button>
                    <button
                      onClick={() => handleTaskConfirmation(false)}
                      style={{
                        padding: "10px 20px",
                        borderRadius: "20px",
                        border: `1px solid ${palette.border}`,
                        background: "transparent",
                        color: palette.fg,
                        fontSize: "14px",
                        cursor: "pointer",
                      }}
                    >
                      Cancel
                    </button>
                  </div>
                )}

                {/* Approval Request Buttons */}
                {msg.isApprovalRequest && msg.approvalRequest && (
                  <div style={{
                    display: "flex",
                    gap: "10px",
                    marginTop: "16px",
                    paddingTop: "12px",
                    borderTop: `1px solid ${palette.border}`,
                  }}>
                    {msg.approvalRequest.options.map((opt) => (
                      <button
                        key={opt.value}
                        onClick={() => handleApprovalResponse(
                          msg.approvalRequest!.request_id,
                          opt.value === "approve"
                        )}
                        style={{
                          padding: "10px 16px",
                          borderRadius: "20px",
                          border: opt.value === "approve" ? "none" : `1px solid ${palette.border}`,
                          background: opt.value === "approve" ? palette.accent : "transparent",
                          color: opt.value === "approve" ? "#fff" : palette.fg,
                          fontSize: "13px",
                          cursor: "pointer",
                        }}
                      >
                        {opt.label}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {isSending && (
              <div style={{ ...messageStyle("sakhi"), opacity: 0.6 }}>
                <span style={{ display: "inline-block", animation: "pulse 1s infinite" }}>
                  ...
                </span>
              </div>
            )}
          </>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div style={inputAreaStyle}>
        {showTextInput ? (
          <form onSubmit={handleSubmit} style={textInputContainerStyle}>
            <input
              type="text"
              style={textInputStyle}
              placeholder="What's on your mind?"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              autoFocus
            />
            <button type="submit" style={sendButtonStyle} disabled={!inputText.trim()}>
              Send
            </button>
          </form>
        ) : (
          <>
            <button
              style={micButtonStyle}
              onClick={toggleVoice}
              disabled={voice.isProcessing}
            >
              {isVoiceActive && <div style={pulseStyle} />}
              {voice.isProcessing ? (
                // Spinner for processing
                <svg
                  viewBox="0 0 24 24"
                  style={{
                    width: 24,
                    height: 24,
                    position: "relative",
                    zIndex: 1,
                    animation: "spin 1s linear infinite",
                  }}
                >
                  <circle
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="2"
                    fill="none"
                    strokeDasharray="31.4 31.4"
                    strokeLinecap="round"
                  />
                </svg>
              ) : voice.isSpeaking ? (
                // Sound waves for speaking
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  style={{ width: 24, height: 24, position: "relative", zIndex: 1 }}
                >
                  <path d="M11 5L6 9H2v6h4l5 4V5z" />
                  <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
                  <path d="M19.07 4.93a10 10 0 0 1 0 14.14" />
                </svg>
              ) : (
                // Microphone for idle/recording
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  style={{ width: 24, height: 24, position: "relative", zIndex: 1 }}
                >
                  <rect x="9" y="3" width="6" height="11" rx="3" />
                  <path d="M5 10v2a7 7 0 0 0 14 0v-2" />
                  <line x1="12" y1="19" x2="12" y2="22" />
                </svg>
              )}
            </button>
            <span style={{ fontSize: "13px", color: palette.muted }}>
              {voiceStatus || (voice.isRecording ? "Tap to stop" : "Tap to speak")}
            </span>
          </>
        )}

        <div
          style={textToggleStyle}
          onClick={() => setShowTextInput(!showTextInput)}
        >
          {showTextInput ? "Use voice instead" : "Type instead"}
        </div>
      </div>

      {/* Floating Action Button */}
      <div style={fabContainerStyle}>
        {/* FAB Options */}
        <div
          style={{ ...fabOptionStyle, transitionDelay: "200ms" }}
          onClick={() => {
            setFabOpen(false);
            setShowDebug(true);
          }}
        >
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
            <rect x="2" y="2" width="14" height="14" rx="2" stroke="#f59e0b" strokeWidth="1.5" />
            <path d="M5 6h8M5 9h6M5 12h4" stroke="#f59e0b" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
          Debug Panel
        </div>

        <div
          style={{ ...fabOptionStyle, transitionDelay: "150ms" }}
          onClick={() => navigateTo("/experience/state")}
        >
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
            <circle cx="9" cy="9" r="7" stroke={palette.accent} strokeWidth="1.5" />
            <path d="M9 5v4l3 2" stroke={palette.accent} strokeWidth="1.5" strokeLinecap="round" />
          </svg>
          Today&apos;s State
        </div>

        <div
          style={{ ...fabOptionStyle, transitionDelay: "100ms" }}
          onClick={() => navigateTo("/experience/onboarding/result")}
        >
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
            <circle cx="9" cy="9" r="7" stroke={palette.success} strokeWidth="1.5" />
            <path d="M6 9l2 2 4-4" stroke={palette.success} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          My Operating System
        </div>

        <div
          style={{ ...fabOptionStyle, transitionDelay: "50ms" }}
          onClick={() => navigateTo("/experience/me")}
        >
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
            <circle cx="9" cy="6" r="3" stroke={palette.accent} strokeWidth="1.5" />
            <path d="M3 16c0-3.3 2.7-6 6-6s6 2.7 6 6" stroke={palette.accent} strokeWidth="1.5" strokeLinecap="round" />
          </svg>
          Me
        </div>

        <div
          style={{ ...fabOptionStyle, transitionDelay: "0ms" }}
          onClick={() => navigateTo("/experience/settings")}
        >
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
            <circle cx="9" cy="9" r="3" stroke={palette.muted} strokeWidth="1.5" />
            <path d="M9 1v2M9 15v2M1 9h2M15 9h2M3 3l1.5 1.5M13.5 13.5L15 15M15 3l-1.5 1.5M4.5 13.5L3 15" stroke={palette.muted} strokeWidth="1.5" strokeLinecap="round" />
          </svg>
          Settings
        </div>

        {/* Main FAB Button */}
        <button
          style={{
            ...fabButtonStyle,
            background: fabOpen ? palette.accent : palette.cardBg,
            transform: fabOpen ? "rotate(45deg)" : "rotate(0deg)",
          }}
          onClick={() => setFabOpen(!fabOpen)}
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
            <line x1="12" y1="5" x2="12" y2="19" stroke={palette.fg} strokeWidth="2" strokeLinecap="round" />
            <line x1="5" y1="12" x2="19" y2="12" stroke={palette.fg} strokeWidth="2" strokeLinecap="round" />
          </svg>
        </button>
      </div>

      {/* Debug Panel */}
      <DebugPanel
        data={lastResponseDebug || {}}
        isOpen={showDebug}
        onClose={() => setShowDebug(false)}
        personId={authUser?.person_id}
      />
    </div>
  );
}
