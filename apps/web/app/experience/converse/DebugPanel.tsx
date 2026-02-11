"use client";

import React, { useState, useEffect, useRef } from "react";

// =============================================================================
// TYPES
// =============================================================================

interface AdaptiveResponse {
  sense?: {
    domain?: string;
    sub_domain?: string;
    symptom?: string;
    temporal?: string;
    tone?: string;
    specificity?: string;
    urgency?: string;
    confidence?: number;
  };
  knowledge_gap?: {
    known_count?: number;
    inferred_count?: number;
    unknown_count?: number;
    dominant_dosha?: string;
    guna_mode?: string;
  };
  strategy?: {
    mode?: string;
    questions_count?: number;
    known_referenced?: number;
    reasoning?: string;
  };
  synthesized?: {
    response_mode?: string;
    constitution?: string;
    symptom?: string;
  };
  pipeline_stages?: Record<string, boolean>;
  errors?: Record<string, string>;
  warnings?: string[];
}

interface DebugData {
  // Input
  input_text?: string;

  // Personal OS
  operating_system?: string;
  dosha_baseline?: { vata?: number; pitta?: number; kapha?: number };
  life_context?: Record<string, unknown>;
  decision_profile?: Record<string, unknown>;

  // Adaptive Response
  adaptive_response?: AdaptiveResponse;

  // Memory
  memory_recall?: Array<{ type?: string; text?: string; score?: number }>;
  memory_context?: string;

  // Engine Debug
  debug?: {
    conversation_engine_debug?: {
      adaptive_prompt?: string;
      base_prompt?: string;
      system_context?: string;
      recall_context?: string;
    };
    adaptive_response?: AdaptiveResponse;
    adaptive_error?: string;
    used_fallback?: boolean;
  };

  // Orchestration
  orchestration?: Record<string, unknown>;
  behavior_profile?: Record<string, unknown>;
  triage?: Record<string, unknown>;

  // States
  internal_state?: Record<string, unknown>;
  tone_state?: Record<string, unknown>;
  continuity?: Record<string, unknown>;
  rhythm_soul_frame?: Record<string, unknown>;
  emotion_soul_rhythm_frame?: Record<string, unknown>;

  // Reply
  reply?: string;
}

interface DebugPanelProps {
  data: DebugData;
  isOpen: boolean;
  onClose: () => void;
  personId?: string;
}

// =============================================================================
// STYLES
// =============================================================================

const palette = {
  bg: "rgba(14, 15, 18, 0.95)",
  fg: "#f4f4f5",
  muted: "#a1a1aa",
  accent: "#6366f1",
  border: "#27272a",
  cardBg: "#18191d",
  sectionBg: "#1a1b1f",
  success: "#22c55e",
  warning: "#f59e0b",
  error: "#ef4444",
  info: "#3b82f6",
};

const styles: Record<string, React.CSSProperties> = {
  overlay: {
    position: "fixed",
    top: 0,
    right: 0,
    bottom: 0,
    width: "480px",
    maxWidth: "100vw",
    background: palette.bg,
    borderLeft: `1px solid ${palette.border}`,
    zIndex: 1000,
    display: "flex",
    flexDirection: "column",
    fontFamily: 'ui-monospace, "SF Mono", Monaco, "Cascadia Code", monospace',
    fontSize: "12px",
    color: palette.fg,
    backdropFilter: "blur(20px)",
    boxShadow: "-4px 0 24px rgba(0, 0, 0, 0.5)",
  },
  header: {
    padding: "16px 20px",
    borderBottom: `1px solid ${palette.border}`,
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    background: palette.cardBg,
  },
  title: {
    fontSize: "14px",
    fontWeight: 600,
    color: palette.fg,
    letterSpacing: "0.05em",
  },
  closeBtn: {
    background: "transparent",
    border: "none",
    color: palette.muted,
    cursor: "pointer",
    padding: "4px 8px",
    borderRadius: "4px",
    fontSize: "18px",
  },
  content: {
    flex: 1,
    overflowY: "auto",
    padding: "16px",
  },
  section: {
    marginBottom: "16px",
    background: palette.sectionBg,
    borderRadius: "8px",
    border: `1px solid ${palette.border}`,
    overflow: "hidden",
  },
  sectionHeader: {
    padding: "12px 16px",
    background: palette.cardBg,
    borderBottom: `1px solid ${palette.border}`,
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    cursor: "pointer",
    userSelect: "none",
  },
  sectionTitle: {
    fontSize: "12px",
    fontWeight: 600,
    textTransform: "uppercase",
    letterSpacing: "0.08em",
    color: palette.accent,
  },
  sectionContent: {
    padding: "12px 16px",
  },
  row: {
    display: "flex",
    justifyContent: "space-between",
    padding: "6px 0",
    borderBottom: `1px solid ${palette.border}`,
  },
  label: {
    color: palette.muted,
    fontSize: "11px",
  },
  value: {
    color: palette.fg,
    fontWeight: 500,
    textAlign: "right" as const,
    maxWidth: "60%",
    wordBreak: "break-word" as const,
  },
  badge: {
    display: "inline-block",
    padding: "2px 8px",
    borderRadius: "4px",
    fontSize: "10px",
    fontWeight: 600,
    textTransform: "uppercase" as const,
  },
  codeBlock: {
    background: "#0d0d0f",
    padding: "12px",
    borderRadius: "4px",
    fontSize: "11px",
    lineHeight: 1.5,
    overflowX: "auto" as const,
    whiteSpace: "pre-wrap" as const,
    wordBreak: "break-word" as const,
    maxHeight: "200px",
    overflowY: "auto" as const,
  },
  stageIndicator: {
    display: "flex",
    gap: "8px",
    flexWrap: "wrap" as const,
    marginTop: "8px",
  },
  stageBadge: {
    padding: "4px 8px",
    borderRadius: "4px",
    fontSize: "10px",
    fontWeight: 500,
  },
};

// =============================================================================
// HELPER COMPONENTS
// =============================================================================

function Section({
  title,
  children,
  defaultOpen = false,
  badge,
}: {
  title: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
  badge?: React.ReactNode;
}) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div style={styles.section}>
      <div style={styles.sectionHeader} onClick={() => setIsOpen(!isOpen)}>
        <span style={styles.sectionTitle}>{title}</span>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          {badge}
          <span style={{ color: palette.muted }}>{isOpen ? "▼" : "▶"}</span>
        </div>
      </div>
      {isOpen && <div style={styles.sectionContent}>{children}</div>}
    </div>
  );
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div style={styles.row}>
      <span style={styles.label}>{label}</span>
      <span style={styles.value}>{value}</span>
    </div>
  );
}

function Badge({
  children,
  color,
}: {
  children: React.ReactNode;
  color: "success" | "warning" | "error" | "info" | "muted";
}) {
  const colors = {
    success: { bg: "#22c55e20", text: palette.success },
    warning: { bg: "#f59e0b20", text: palette.warning },
    error: { bg: "#ef444420", text: palette.error },
    info: { bg: "#3b82f620", text: palette.info },
    muted: { bg: "#71717a20", text: palette.muted },
  };

  return (
    <span
      style={{
        ...styles.badge,
        background: colors[color].bg,
        color: colors[color].text,
      }}
    >
      {children}
    </span>
  );
}

function CodeBlock({ content }: { content: string }) {
  return <pre style={styles.codeBlock}>{content}</pre>;
}

// =============================================================================
// MAIN COMPONENT
// =============================================================================

export default function DebugPanel({ data, isOpen, onClose, personId }: DebugPanelProps) {
  const [editedPrompt, setEditedPrompt] = useState("");
  const [isReplaying, setIsReplaying] = useState(false);
  const [replayResult, setReplayResult] = useState<string | null>(null);
  const lastPromptRef = useRef<string>("");

  const engineDebugForEffect = data.debug?.conversation_engine_debug;
  const originalPrompt = engineDebugForEffect?.adaptive_prompt || engineDebugForEffect?.base_prompt || "";

  // Sync edited prompt when new data arrives (new turn)
  useEffect(() => {
    if (originalPrompt && originalPrompt !== lastPromptRef.current) {
      setEditedPrompt(originalPrompt);
      setReplayResult(null);
      lastPromptRef.current = originalPrompt;
    }
  }, [originalPrompt]);

  if (!isOpen) return null;

  const adaptive = data.adaptive_response || data.debug?.adaptive_response;
  const engineDebug = engineDebugForEffect;
  const doshaBaseline = data.dosha_baseline || {};

  // Collect all errors and warnings
  const errors: Array<{ stage: string; message: string }> = [];
  const warnings: string[] = [];

  // Pipeline-level error (complete failure)
  if (data.debug?.adaptive_error) {
    errors.push({ stage: "pipeline", message: data.debug.adaptive_error });
  }

  // Stage-level errors
  if (adaptive?.errors) {
    Object.entries(adaptive.errors).forEach(([stage, message]) => {
      errors.push({ stage, message: message as string });
    });
  }

  // Warnings
  if (adaptive?.warnings) {
    warnings.push(...adaptive.warnings);
  }

  // Fallback warning
  if (data.debug?.used_fallback && !data.debug?.adaptive_error) {
    warnings.push("Fell back to base prompt (adaptive pipeline incomplete)");
  }

  const hasIssues = errors.length > 0 || warnings.length > 0;

  // Calculate dominant dosha
  const getDominantDosha = () => {
    if (!doshaBaseline.vata && !doshaBaseline.pitta && !doshaBaseline.kapha) {
      return "Unknown";
    }
    const max = Math.max(
      doshaBaseline.vata || 0,
      doshaBaseline.pitta || 0,
      doshaBaseline.kapha || 0
    );
    if (max === doshaBaseline.pitta) return "Pitta";
    if (max === doshaBaseline.vata) return "Vata";
    return "Kapha";
  };

  // Format percentage
  const formatPct = (val?: number) => (val ? `${Math.round(val * 100)}%` : "—");

  // Get response mode badge color
  const getModeColor = (mode?: string): "success" | "warning" | "info" => {
    if (mode === "RESPOND") return "success";
    if (mode === "CONNECT_AND_INQUIRE") return "warning";
    return "info";
  };

  return (
    <div style={styles.overlay}>
      {/* Header */}
      <div style={styles.header}>
        <span style={styles.title}>🔬 Execution Debug</span>
        <button style={styles.closeBtn} onClick={onClose}>
          ✕
        </button>
      </div>

      {/* Content */}
      <div style={styles.content}>
        {/* User Input */}
        <Section title="User Input" defaultOpen={true}>
          <CodeBlock content={data.input_text || (data as any).debug?.loop_trace?.input_text || "—"} />
        </Section>

        {/* Errors & Warnings - Always shown if any exist */}
        {hasIssues && (
          <Section
            title="Errors & Warnings"
            defaultOpen={true}
            badge={
              errors.length > 0 ? (
                <Badge color="error">{errors.length} error(s)</Badge>
              ) : (
                <Badge color="warning">{warnings.length} warning(s)</Badge>
              )
            }
          >
            {errors.length > 0 && (
              <div style={{ marginBottom: "12px" }}>
                <div style={{ ...styles.label, marginBottom: "8px", color: palette.error }}>
                  ERRORS
                </div>
                {errors.map((err, idx) => (
                  <div
                    key={idx}
                    style={{
                      padding: "8px 12px",
                      marginBottom: "8px",
                      background: "#ef444420",
                      borderRadius: "4px",
                      borderLeft: `3px solid ${palette.error}`,
                    }}
                  >
                    <div style={{ fontSize: "10px", color: palette.error, marginBottom: "4px" }}>
                      Stage: {err.stage.toUpperCase()}
                    </div>
                    <div style={{ fontSize: "11px", color: palette.fg }}>
                      {err.message}
                    </div>
                  </div>
                ))}
              </div>
            )}
            {warnings.length > 0 && (
              <div>
                <div style={{ ...styles.label, marginBottom: "8px", color: palette.warning }}>
                  WARNINGS
                </div>
                {warnings.map((warn, idx) => (
                  <div
                    key={idx}
                    style={{
                      padding: "8px 12px",
                      marginBottom: "8px",
                      background: "#f59e0b20",
                      borderRadius: "4px",
                      borderLeft: `3px solid ${palette.warning}`,
                    }}
                  >
                    <div style={{ fontSize: "11px", color: palette.fg }}>
                      {warn}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Section>
        )}

        {/* Personal OS */}
        <Section
          title="Personal Operating System"
          defaultOpen={true}
          badge={<Badge color="info">{getDominantDosha()}</Badge>}
        >
          <Row label="OS Type" value={data.operating_system || "—"} />
          <Row label="Vata" value={formatPct(doshaBaseline.vata)} />
          <Row label="Pitta" value={formatPct(doshaBaseline.pitta)} />
          <Row label="Kapha" value={formatPct(doshaBaseline.kapha)} />
          {data.life_context && (
            <Row
              label="Life Phase"
              value={(data.life_context as { life_phase?: string })?.life_phase || "—"}
            />
          )}
        </Section>

        {/* Adaptive Response Pipeline */}
        {adaptive && (
          <Section
            title="Adaptive Response Pipeline"
            defaultOpen={true}
            badge={
              <Badge color={getModeColor(adaptive.strategy?.mode)}>
                {adaptive.strategy?.mode || "N/A"}
              </Badge>
            }
          >
            {/* Pipeline Stages */}
            <div style={{ marginBottom: "12px" }}>
              <span style={styles.label}>Pipeline Stages</span>
              <div style={styles.stageIndicator}>
                {["sensing", "knowledge_gap", "strategy", "synthesis", "prompt"].map(
                  (stage) => (
                    <span
                      key={stage}
                      style={{
                        ...styles.stageBadge,
                        background: adaptive.pipeline_stages?.[stage]
                          ? "#22c55e20"
                          : "#ef444420",
                        color: adaptive.pipeline_stages?.[stage]
                          ? palette.success
                          : palette.error,
                      }}
                    >
                      {stage} {adaptive.pipeline_stages?.[stage] ? "✓" : "✗"}
                    </span>
                  )
                )}
              </div>
            </div>

            {/* Sensing */}
            {adaptive.sense && (
              <>
                <Row label="Domain" value={adaptive.sense.domain || "—"} />
                <Row label="Sub-domain" value={adaptive.sense.sub_domain || "—"} />
                <Row label="Symptom" value={adaptive.sense.symptom || "—"} />
                <Row label="Temporal" value={adaptive.sense.temporal || "—"} />
                <Row label="Tone" value={adaptive.sense.tone || "—"} />
                <Row label="Specificity" value={adaptive.sense.specificity || "—"} />
                <Row
                  label="Confidence"
                  value={formatPct(adaptive.sense.confidence)}
                />
              </>
            )}

            {/* Knowledge Gap */}
            {adaptive.knowledge_gap && (
              <>
                <Row
                  label="Known Facts"
                  value={adaptive.knowledge_gap.known_count || 0}
                />
                <Row
                  label="Inferences"
                  value={adaptive.knowledge_gap.inferred_count || 0}
                />
                <Row
                  label="Unknown (to ask)"
                  value={adaptive.knowledge_gap.unknown_count || 0}
                />
                <Row
                  label="Dominant Dosha"
                  value={adaptive.knowledge_gap.dominant_dosha || "—"}
                />
                <Row
                  label="Guna Mode"
                  value={adaptive.knowledge_gap.guna_mode || "—"}
                />
              </>
            )}

            {/* Strategy */}
            {adaptive.strategy && (
              <>
                <Row label="Response Mode" value={adaptive.strategy.mode || "—"} />
                <Row
                  label="Questions to Ask"
                  value={adaptive.strategy.questions_count || 0}
                />
                <Row label="Reasoning" value={adaptive.strategy.reasoning || "—"} />
              </>
            )}
          </Section>
        )}

        {/* Memory Recalls */}
        <Section title="Memory Recalls" defaultOpen={false}>
          {data.memory_recall && Array.isArray(data.memory_recall) ? (
            data.memory_recall.length > 0 ? (
              data.memory_recall.map((item, idx) => (
                <div
                  key={idx}
                  style={{
                    padding: "8px",
                    marginBottom: "8px",
                    background: "#0d0d0f",
                    borderRadius: "4px",
                  }}
                >
                  <div style={{ display: "flex", gap: "8px", marginBottom: "4px" }}>
                    <Badge color="muted">{item.type || "unknown"}</Badge>
                    <Badge color="info">
                      {item.score ? `${(item.score * 100).toFixed(0)}%` : "—"}
                    </Badge>
                  </div>
                  <div style={{ fontSize: "11px", color: palette.muted }}>
                    {item.text || "—"}
                  </div>
                </div>
              ))
            ) : (
              <div style={{ color: palette.muted }}>No recalls found</div>
            )
          ) : (
            <div style={{ color: palette.muted }}>No recall data</div>
          )}
        </Section>

        {/* Context Sent to LLM */}
        <Section title="Context Sent to LLM" defaultOpen={false}>
          {engineDebug?.system_context && (
            <>
              <div style={{ marginBottom: "8px" }}>
                <span style={styles.label}>System Context (Recalls + Patterns)</span>
              </div>
              <CodeBlock content={engineDebug.system_context} />
            </>
          )}
        </Section>

        {/* Prompt Playground */}
        <Section title="Prompt Playground" defaultOpen={false}>
          {(() => {
            const promptSource = engineDebug?.adaptive_prompt ? "adaptive" : "base";

            const handleReplay = async () => {
              if (!personId || !editedPrompt) return;
              setIsReplaying(true);
              setReplayResult(null);
              try {
                // Extract conversation history (user/assistant turns only)
                const allMessages = (data.debug as any)?.conversation_engine_debug?.messages || [];
                const convHistory: Array<{role: string; text: string}> = [];
                let sessionSummary = "";
                for (const msg of allMessages) {
                  if (msg.role === "user" || msg.role === "assistant") {
                    convHistory.push({ role: msg.role, text: msg.content || "" });
                  } else if (msg.role === "system" && (msg.content || "").includes("[Earlier Conversation Context]")) {
                    sessionSummary = (msg.content || "").replace("[Earlier Conversation Context]\nUse this context to understand references in the recent conversation:\n- When user says \"she/he/they\", refer to People & Relationships\n- When user says \"it/that/the project\", refer to Topics & References\n- Be aware of the Emotional Thread and Open Threads\n\n", "");
                  }
                }
                // Remove the last user message from history (it's sent as user_text)
                if (convHistory.length > 0 && convHistory[convHistory.length - 1].role === "user") {
                  convHistory.pop();
                }

                const res = await fetch("/api/lab/replay-prompt", {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({
                    person_id: personId,
                    edited_prompt: editedPrompt,
                    system_context: engineDebug?.system_context || "",
                    user_text: data.input_text || "",
                    conversation_history: convHistory,
                    session_summary: sessionSummary,
                  }),
                });
                const result = await res.json();
                if (res.ok) {
                  setReplayResult(result.replay_reply || "(empty response)");
                } else {
                  setReplayResult(`Error: ${result.error || result.detail || res.statusText}`);
                }
              } catch (err: any) {
                setReplayResult(`Error: ${err.message || "Failed to replay"}`);
              } finally {
                setIsReplaying(false);
              }
            };

            const handleReset = () => {
              setEditedPrompt(originalPrompt);
              setReplayResult(null);
            };

            if (!originalPrompt) {
              return <div style={{ color: palette.muted }}>No prompt data available</div>;
            }

            return (
              <>
                <div style={{ marginBottom: "8px" }}>
                  <Badge color={promptSource === "adaptive" ? "info" : "muted"}>
                    {promptSource === "adaptive" ? "Adaptive Prompt" : "Base Prompt (adaptive not used)"}
                  </Badge>
                </div>

                <textarea
                  value={editedPrompt}
                  onChange={(e) => setEditedPrompt(e.target.value)}
                  style={{
                    width: "100%",
                    minHeight: "200px",
                    maxHeight: "400px",
                    background: "#111215",
                    color: palette.fg,
                    border: `1px solid ${palette.border}`,
                    borderRadius: "6px",
                    padding: "12px",
                    fontFamily: 'ui-monospace, "SF Mono", Monaco, "Cascadia Code", monospace',
                    fontSize: "11px",
                    lineHeight: "1.5",
                    resize: "vertical",
                    outline: "none",
                    boxSizing: "border-box",
                  }}
                  onFocus={(e) => { e.target.style.borderColor = palette.accent; }}
                  onBlur={(e) => { e.target.style.borderColor = palette.border; }}
                />

                <div style={{ display: "flex", gap: "8px", marginTop: "8px" }}>
                  <button
                    onClick={handleReplay}
                    disabled={isReplaying || !personId}
                    style={{
                      padding: "8px 16px",
                      background: isReplaying ? palette.border : palette.accent,
                      color: palette.fg,
                      border: "none",
                      borderRadius: "6px",
                      fontSize: "12px",
                      fontWeight: 600,
                      cursor: isReplaying ? "not-allowed" : "pointer",
                      opacity: isReplaying ? 0.7 : 1,
                      fontFamily: 'ui-monospace, "SF Mono", Monaco, "Cascadia Code", monospace',
                    }}
                  >
                    {isReplaying ? "Re-running..." : "Re-run with Edited Prompt"}
                  </button>
                  <button
                    onClick={handleReset}
                    style={{
                      padding: "8px 16px",
                      background: "transparent",
                      color: palette.muted,
                      border: `1px solid ${palette.border}`,
                      borderRadius: "6px",
                      fontSize: "12px",
                      fontWeight: 500,
                      cursor: "pointer",
                      fontFamily: 'ui-monospace, "SF Mono", Monaco, "Cascadia Code", monospace',
                    }}
                  >
                    Reset
                  </button>
                </div>

                {/* Comparison view */}
                {replayResult !== null && (
                  <div style={{ marginTop: "12px" }}>
                    <div style={{ marginBottom: "8px" }}>
                      <Badge color="muted">Original Response</Badge>
                    </div>
                    <CodeBlock content={data.reply || "(no original response)"} />

                    <div style={{ marginTop: "12px", marginBottom: "8px" }}>
                      <Badge color="info">Replayed Response</Badge>
                    </div>
                    <CodeBlock content={replayResult} />
                  </div>
                )}
              </>
            );
          })()}
        </Section>

        {/* States */}
        <Section title="Engine States" defaultOpen={false}>
          {data.behavior_profile && (
            <Row
              label="Conversation Depth"
              value={
                (data.behavior_profile as { conversation_depth?: string })
                  ?.conversation_depth || "—"
              }
            />
          )}
          {data.tone_state && (
            <Row
              label="Tone"
              value={(data.tone_state as { final?: string })?.final || "—"}
            />
          )}
          {data.continuity && (
            <Row
              label="Continuity"
              value={
                (data.continuity as { clarity_level?: number })?.clarity_level
                  ? `${Math.round(((data.continuity as { clarity_level?: number }).clarity_level || 0) * 100)}%`
                  : "—"
              }
            />
          )}
        </Section>

        {/* Response */}
        <Section title="Generated Response" defaultOpen={true}>
          <CodeBlock content={data.reply || "—"} />
        </Section>

        {/* Raw Debug Data */}
        <Section title="Raw Debug JSON" defaultOpen={false}>
          <CodeBlock content={JSON.stringify(data, null, 2)} />
        </Section>
      </div>
    </div>
  );
}
