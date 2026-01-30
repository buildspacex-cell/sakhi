"use client";

import { Suspense, useState, useEffect, useRef, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
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

interface Message {
  id: string;
  role: "user" | "sakhi";
  content: string;
  timestamp: Date;
  source?: "text" | "voice";
}

interface AuthUser {
  person_id: string;
  full_name: string | null;
  email: string;
}

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

  // Debug panel state
  const [showDebug, setShowDebug] = useState(false);
  const [lastResponseDebug, setLastResponseDebug] = useState<Record<string, unknown> | null>(null);

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
          `/api/turn-v2?user=${encodeURIComponent(authUser.person_id)}`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text: text.trim(), source: "text" }),
          }
        );

        if (res.ok) {
          const data = await res.json();
          // Store the full response for debug panel
          setLastResponseDebug({
            ...data,
            input_text: text.trim(),
          });

          if (data.reply) {
            const sakhiMessage: Message = {
              id: (Date.now() + 1).toString(),
              role: "sakhi",
              content: data.reply,
              timestamp: new Date(),
              source: "text",
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
    minHeight: "100vh",
    background: palette.bg,
    color: palette.fg,
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Inter, sans-serif',
    display: "flex",
    flexDirection: "column",
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
    bottom: "140px",
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
        <div style={brandStyle}>Sakhi</div>
        <div style={greetingStyle}>
          {getGreeting()}
          {displayName && `, ${displayName}`}
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
                {msg.content}
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
          style={{ ...fabOptionStyle, transitionDelay: "150ms" }}
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
          style={{ ...fabOptionStyle, transitionDelay: "100ms" }}
          onClick={() => navigateTo("/experience/state")}
        >
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
            <circle cx="9" cy="9" r="7" stroke={palette.accent} strokeWidth="1.5" />
            <path d="M9 5v4l3 2" stroke={palette.accent} strokeWidth="1.5" strokeLinecap="round" />
          </svg>
          Today&apos;s State
        </div>

        <div
          style={{ ...fabOptionStyle, transitionDelay: "50ms" }}
          onClick={() => navigateTo("/experience/onboarding/result")}
        >
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
            <circle cx="9" cy="9" r="7" stroke={palette.success} strokeWidth="1.5" />
            <path d="M6 9l2 2 4-4" stroke={palette.success} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          My Operating System
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
      />
    </div>
  );
}
