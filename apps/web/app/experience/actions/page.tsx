"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { CSSProperties } from "react";
import Link from "next/link";

export const dynamic = "force-dynamic";

type AuthUser = {
  person_id: string;
  full_name?: string | null;
};

type TaskStep = {
  step: number;
  action: string;
  description: string;
  status: string;
  result?: unknown;
  error?: string | null;
};

type TaskPlanResponse = {
  plan_id: string;
  status: string;
  goal: string;
  steps: TaskStep[];
  requires_approval: boolean;
  final_output?: string | null;
};

type ActiveTask = {
  plan_id: string;
  status: string;
  goal: string;
  steps_count: number;
};

const TERMINAL_STATUSES = new Set(["completed", "failed", "cancelled"]);

const palette = {
  bg: "#0e0f12",
  card: "#1a1b1e",
  border: "#2a2b30",
  fg: "#f4f4f5",
  muted: "#a1a1aa",
  accent: "#3b82f6",
  accentSoft: "rgba(59, 130, 246, 0.16)",
  success: "#22c55e",
  warning: "#f59e0b",
  danger: "#ef4444",
};

function toErrorMessage(payload: unknown): string {
  if (!payload || typeof payload !== "object") {
    return "Request failed";
  }
  const maybePayload = payload as { detail?: string; error?: string };
  return maybePayload.detail || maybePayload.error || "Request failed";
}

function toStatusColor(status: string): string {
  switch (status) {
    case "pending_approval":
      return palette.warning;
    case "executing":
      return palette.accent;
    case "completed":
      return palette.success;
    case "failed":
      return palette.danger;
    case "cancelled":
      return palette.muted;
    default:
      return palette.muted;
  }
}

function summarizeResult(result: unknown): string {
  if (result == null) return "";
  if (typeof result === "string") return result;
  try {
    const text = JSON.stringify(result);
    return text.length > 180 ? `${text.slice(0, 177)}...` : text;
  } catch {
    return String(result);
  }
}

export default function ExperienceActionsPage() {
  const [authUser, setAuthUser] = useState<AuthUser | null>(null);
  const [authLoading, setAuthLoading] = useState(true);

  const [taskInput, setTaskInput] = useState("Find three highly rated electric kettles under $80");
  const [plan, setPlan] = useState<TaskPlanResponse | null>(null);
  const [activeTasks, setActiveTasks] = useState<ActiveTask[]>([]);
  const [loading, setLoading] = useState(false);
  const [busyAction, setBusyAction] = useState<"approve" | "cancel" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);

  const isExecuting = useMemo(
    () => Boolean(plan && !TERMINAL_STATUSES.has(plan.status) && plan.status !== "pending_approval"),
    [plan]
  );

  const loadActiveTasks = useCallback(async () => {
    if (!authUser?.person_id) return;
    try {
      const response = await fetch(
        `/api/agent/plans?person_id=${encodeURIComponent(authUser.person_id)}`
      );
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) return;
      const tasks = Array.isArray(payload?.tasks) ? payload.tasks : [];
      setActiveTasks(tasks as ActiveTask[]);
    } catch {
      // intentionally silent
    }
  }, [authUser?.person_id]);

  const refreshPlan = useCallback(async (planId: string) => {
    const response = await fetch(`/api/agent/plans/${encodeURIComponent(planId)}`);
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(toErrorMessage(payload));
    }
    setPlan(payload as TaskPlanResponse);
  }, []);

  useEffect(() => {
    const loadAuth = async () => {
      try {
        const response = await fetch("/api/auth/me");
        if (!response.ok) return;
        const payload = await response.json();
        if (payload?.person_id) {
          setAuthUser({
            person_id: payload.person_id,
            full_name: payload.full_name,
          });
        }
      } catch {
        // intentionally silent
      } finally {
        setAuthLoading(false);
      }
    };
    loadAuth();
  }, []);

  useEffect(() => {
    if (!authUser?.person_id) return;
    loadActiveTasks();
  }, [authUser?.person_id, loadActiveTasks]);

  useEffect(() => {
    if (!plan?.plan_id || TERMINAL_STATUSES.has(plan.status) || plan.status === "pending_approval") {
      return;
    }
    const timer = window.setInterval(() => {
      refreshPlan(plan.plan_id).catch((err) => {
        setError(err instanceof Error ? err.message : "Failed to refresh task state");
      });
    }, 2500);

    return () => window.clearInterval(timer);
  }, [plan?.plan_id, plan?.status, refreshPlan]);

  const createPlan = useCallback(async () => {
    if (!authUser?.person_id || !taskInput.trim()) return;
    setLoading(true);
    setError(null);
    setStatusMsg(null);

    try {
      const response = await fetch("/api/agent/plans", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          person_id: authUser.person_id,
          task: taskInput.trim(),
          auto_execute: false,
        }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(toErrorMessage(payload));
      }
      setPlan(payload as TaskPlanResponse);
      setStatusMsg("Plan created. Review steps and approve when ready.");
      await loadActiveTasks();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create plan");
    } finally {
      setLoading(false);
    }
  }, [authUser?.person_id, loadActiveTasks, taskInput]);

  const approvePlan = useCallback(async () => {
    if (!authUser?.person_id || !plan?.plan_id) return;
    setBusyAction("approve");
    setError(null);
    setStatusMsg(null);
    try {
      const response = await fetch(
        `/api/agent/plans/${encodeURIComponent(plan.plan_id)}/approve`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ person_id: authUser.person_id }),
        }
      );
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(toErrorMessage(payload));
      }
      setPlan(payload as TaskPlanResponse);
      setStatusMsg("Execution started.");
      await loadActiveTasks();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to approve plan");
    } finally {
      setBusyAction(null);
    }
  }, [authUser?.person_id, loadActiveTasks, plan?.plan_id]);

  const cancelPlan = useCallback(async () => {
    if (!authUser?.person_id || !plan?.plan_id) return;
    setBusyAction("cancel");
    setError(null);
    setStatusMsg(null);
    try {
      const response = await fetch(
        `/api/agent/plans/${encodeURIComponent(plan.plan_id)}/cancel`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ person_id: authUser.person_id }),
        }
      );
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(toErrorMessage(payload));
      }
      setPlan((prev) => (prev ? { ...prev, status: "cancelled" } : prev));
      setStatusMsg("Plan cancelled.");
      await loadActiveTasks();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to cancel plan");
    } finally {
      setBusyAction(null);
    }
  }, [authUser?.person_id, loadActiveTasks, plan?.plan_id]);

  return (
    <main style={styles.page}>
      <div style={styles.container}>
        <div style={styles.headerRow}>
          <div>
            <p style={styles.kicker}>Stage 2 - Outer Action</p>
            <h1 style={styles.title}>Ask, Approve, Execute</h1>
            <p style={styles.subtitle}>
              One real external task loop with explicit approval and visible execution states.
            </p>
          </div>
          <Link href="/experience" style={styles.backLink}>
            Back
          </Link>
        </div>

        <section style={styles.card}>
          <div style={styles.modeRow}>
            <span style={styles.modeBadge}>Mode: Live</span>
            <span style={styles.modeHint}>High-impact actions run only after your approval.</span>
          </div>

          {!authLoading && !authUser?.person_id && (
            <div style={{ ...styles.notice, borderColor: palette.warning }}>
              Sign in to run live tasks.
            </div>
          )}

          <label style={styles.label}>What should Sakhi do?</label>
          <textarea
            value={taskInput}
            onChange={(event) => setTaskInput(event.target.value)}
            rows={3}
            style={styles.textarea}
            placeholder="Example: find three top-rated air purifiers and summarize tradeoffs."
          />

          <div style={styles.inlineActions}>
            <button
              type="button"
              onClick={createPlan}
              disabled={loading || !authUser?.person_id || !taskInput.trim()}
              style={loading ? styles.ctaDisabled : styles.cta}
            >
              {loading ? "Planning..." : "Propose Plan"}
            </button>
            <button
              type="button"
              onClick={loadActiveTasks}
              disabled={!authUser?.person_id}
              style={styles.secondaryBtn}
            >
              Refresh Active Tasks
            </button>
          </div>
        </section>

        {error && <div style={{ ...styles.notice, borderColor: palette.danger }}>{error}</div>}
        {statusMsg && <div style={{ ...styles.notice, borderColor: palette.accent }}>{statusMsg}</div>}

        {plan && (
          <section style={styles.card}>
            <div style={styles.planHeader}>
              <div>
                <h2 style={styles.sectionTitle}>Current Plan</h2>
                <p style={styles.planGoal}>{plan.goal}</p>
              </div>
              <span
                style={{
                  ...styles.statusBadge,
                  borderColor: toStatusColor(plan.status),
                  color: toStatusColor(plan.status),
                }}
              >
                {plan.status}
              </span>
            </div>

            <div style={styles.planMeta}>
              <span>Plan ID: {plan.plan_id}</span>
              <span>Steps: {plan.steps?.length || 0}</span>
              <span>{isExecuting ? "Execution in progress" : "Execution idle"}</span>
            </div>

            <div style={styles.stepsList}>
              {(plan.steps || []).map((step) => (
                <article key={`${plan.plan_id}-step-${step.step}`} style={styles.stepCard}>
                  <div style={styles.stepHeader}>
                    <span style={styles.stepIndex}>Step {step.step}</span>
                    <span
                      style={{
                        ...styles.stepStatus,
                        color: toStatusColor(step.status),
                        borderColor: toStatusColor(step.status),
                      }}
                    >
                      {step.status}
                    </span>
                  </div>
                  <p style={styles.stepAction}>{step.action}</p>
                  <p style={styles.stepDescription}>{step.description || "No description provided."}</p>
                  {step.result !== undefined && step.result !== null && (
                    <p style={styles.stepResult}>Result: {summarizeResult(step.result)}</p>
                  )}
                  {typeof step.error === "string" && step.error.length > 0 && (
                    <p style={styles.stepError}>Error: {step.error}</p>
                  )}
                </article>
              ))}
            </div>

            {plan.status === "pending_approval" && (
              <div style={styles.inlineActions}>
                <button
                  type="button"
                  style={styles.cta}
                  disabled={busyAction !== null}
                  onClick={approvePlan}
                >
                  {busyAction === "approve" ? "Approving..." : "Approve & Execute"}
                </button>
                <button
                  type="button"
                  style={styles.secondaryBtn}
                  disabled={busyAction !== null}
                  onClick={cancelPlan}
                >
                  {busyAction === "cancel" ? "Cancelling..." : "Cancel"}
                </button>
              </div>
            )}

            {plan.status === "failed" && (
              <div style={styles.inlineActions}>
                <button type="button" style={styles.secondaryBtn} onClick={createPlan}>
                  Retry with Same Ask
                </button>
              </div>
            )}

            {plan.status === "completed" && plan.final_output && (
              <div style={styles.outputBox}>
                <h3 style={styles.outputTitle}>Final Output</h3>
                <p style={styles.outputText}>{plan.final_output}</p>
              </div>
            )}
          </section>
        )}

        <section style={styles.card}>
          <h2 style={styles.sectionTitle}>Active Task Queue</h2>
          {activeTasks.length === 0 ? (
            <p style={styles.emptyState}>No active tasks.</p>
          ) : (
            <div style={styles.activeTaskList}>
              {activeTasks.map((task) => (
                <button
                  key={task.plan_id}
                  type="button"
                  style={styles.activeTaskBtn}
                  onClick={() => {
                    setPlan(null);
                    setError(null);
                    setStatusMsg(null);
                    refreshPlan(task.plan_id).catch((err) => {
                      setError(err instanceof Error ? err.message : "Failed to load selected task");
                    });
                  }}
                >
                  <span style={styles.activeTaskTitle}>{task.goal}</span>
                  <span style={{ ...styles.activeTaskStatus, color: toStatusColor(task.status) }}>
                    {task.status} · {task.steps_count} steps
                  </span>
                </button>
              ))}
            </div>
          )}
        </section>
      </div>
    </main>
  );
}

const styles: Record<string, CSSProperties> = {
  page: {
    minHeight: "100vh",
    background: palette.bg,
    color: palette.fg,
    padding: "40px 18px 64px",
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Inter, sans-serif',
  },
  container: {
    maxWidth: "860px",
    margin: "0 auto",
    display: "grid",
    gap: "14px",
  },
  headerRow: {
    display: "flex",
    justifyContent: "space-between",
    gap: "16px",
    alignItems: "flex-start",
  },
  kicker: {
    margin: 0,
    fontSize: "12px",
    letterSpacing: "0.08em",
    textTransform: "uppercase",
    color: palette.accent,
  },
  title: {
    margin: "2px 0 6px",
    fontSize: "1.8rem",
    lineHeight: 1.2,
  },
  subtitle: {
    margin: 0,
    color: palette.muted,
    maxWidth: "680px",
  },
  backLink: {
    color: palette.muted,
    textDecoration: "underline",
    textUnderlineOffset: "3px",
    fontSize: "0.9rem",
    whiteSpace: "nowrap",
  },
  card: {
    border: `1px solid ${palette.border}`,
    borderRadius: "12px",
    background: palette.card,
    padding: "16px",
    display: "grid",
    gap: "12px",
  },
  modeRow: {
    display: "flex",
    flexWrap: "wrap",
    gap: "10px",
    alignItems: "center",
  },
  modeBadge: {
    border: `1px solid ${palette.accent}`,
    color: palette.accent,
    background: palette.accentSoft,
    borderRadius: "999px",
    padding: "4px 10px",
    fontSize: "0.78rem",
    fontWeight: 600,
  },
  modeHint: {
    fontSize: "0.86rem",
    color: palette.muted,
  },
  label: {
    fontSize: "0.92rem",
    fontWeight: 500,
  },
  textarea: {
    width: "100%",
    borderRadius: "10px",
    border: `1px solid ${palette.border}`,
    background: "#111215",
    color: palette.fg,
    fontSize: "0.98rem",
    padding: "12px",
    resize: "vertical",
  },
  inlineActions: {
    display: "flex",
    gap: "10px",
    flexWrap: "wrap",
  },
  cta: {
    border: "none",
    borderRadius: "10px",
    background: palette.accent,
    color: "#fff",
    fontWeight: 600,
    padding: "10px 14px",
    cursor: "pointer",
  },
  ctaDisabled: {
    border: "none",
    borderRadius: "10px",
    background: "#334155",
    color: "#cbd5e1",
    fontWeight: 600,
    padding: "10px 14px",
    cursor: "not-allowed",
  },
  secondaryBtn: {
    border: `1px solid ${palette.border}`,
    borderRadius: "10px",
    background: "transparent",
    color: palette.fg,
    padding: "10px 14px",
    cursor: "pointer",
  },
  notice: {
    border: `1px solid ${palette.border}`,
    borderRadius: "10px",
    padding: "10px 12px",
    fontSize: "0.9rem",
    color: palette.fg,
    background: "#101113",
  },
  planHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "flex-start",
    gap: "12px",
  },
  sectionTitle: {
    margin: 0,
    fontSize: "1.05rem",
  },
  planGoal: {
    margin: "4px 0 0",
    color: palette.muted,
    fontSize: "0.92rem",
  },
  statusBadge: {
    border: `1px solid ${palette.border}`,
    borderRadius: "999px",
    padding: "5px 10px",
    fontSize: "0.78rem",
    textTransform: "uppercase",
    letterSpacing: "0.04em",
    fontWeight: 700,
  },
  planMeta: {
    display: "flex",
    gap: "10px",
    flexWrap: "wrap",
    color: palette.muted,
    fontSize: "0.82rem",
  },
  stepsList: {
    display: "grid",
    gap: "10px",
  },
  stepCard: {
    border: `1px solid ${palette.border}`,
    borderRadius: "10px",
    padding: "10px",
    background: "#111215",
    display: "grid",
    gap: "6px",
  },
  stepHeader: {
    display: "flex",
    justifyContent: "space-between",
    gap: "8px",
    alignItems: "center",
  },
  stepIndex: {
    fontSize: "0.84rem",
    color: palette.muted,
  },
  stepStatus: {
    border: `1px solid ${palette.border}`,
    borderRadius: "999px",
    padding: "3px 8px",
    fontSize: "0.72rem",
    textTransform: "uppercase",
    letterSpacing: "0.04em",
    fontWeight: 700,
  },
  stepAction: {
    margin: 0,
    fontWeight: 600,
    fontSize: "0.94rem",
  },
  stepDescription: {
    margin: 0,
    color: palette.muted,
    fontSize: "0.88rem",
  },
  stepResult: {
    margin: 0,
    fontSize: "0.82rem",
    color: "#cbd5e1",
  },
  stepError: {
    margin: 0,
    fontSize: "0.82rem",
    color: palette.danger,
  },
  outputBox: {
    border: `1px solid ${palette.success}`,
    borderRadius: "10px",
    background: "rgba(34, 197, 94, 0.1)",
    padding: "10px",
    display: "grid",
    gap: "6px",
  },
  outputTitle: {
    margin: 0,
    fontSize: "0.92rem",
    color: palette.success,
  },
  outputText: {
    margin: 0,
    whiteSpace: "pre-wrap",
    fontSize: "0.9rem",
    lineHeight: 1.4,
  },
  activeTaskList: {
    display: "grid",
    gap: "8px",
  },
  activeTaskBtn: {
    border: `1px solid ${palette.border}`,
    borderRadius: "10px",
    background: "#111215",
    color: palette.fg,
    padding: "10px",
    textAlign: "left",
    cursor: "pointer",
    display: "grid",
    gap: "4px",
  },
  activeTaskTitle: {
    fontSize: "0.9rem",
    fontWeight: 600,
  },
  activeTaskStatus: {
    fontSize: "0.8rem",
  },
  emptyState: {
    margin: 0,
    color: palette.muted,
    fontSize: "0.88rem",
  },
};
