"use client";

import { Suspense, useState, useEffect, useCallback, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import type { Route } from "next";
import { useVoice, type VoiceState } from "@/lib/hooks/useVoice";

export const dynamic = "force-dynamic";

// =============================================================================
// STYLES
// =============================================================================

const palette = {
  bg: "#0a0a0c",
  fg: "#f4f4f5",
  muted: "#71717a",
  accent: "#6366f1",
  accentGlow: "rgba(99, 102, 241, 0.3)",
  recording: "#ef4444",
  recordingGlow: "rgba(239, 68, 68, 0.4)",
  speaking: "#22c55e",
  speakingGlow: "rgba(34, 197, 94, 0.4)",
  processing: "#f59e0b",
  processingGlow: "rgba(245, 158, 11, 0.4)",
};

// =============================================================================
// TYPES
// =============================================================================

interface AuthUser {
  person_id: string;
  full_name: string | null;
}

interface VoiceSettings {
  voice: "nova" | "shimmer" | "alloy";
  autoPlay: boolean;
  continuousMode: boolean;
}

// =============================================================================
// COMPONENT
// =============================================================================

export default function VoicePage() {
  return (
    <Suspense fallback={null}>
      <VoicePageContent />
    </Suspense>
  );
}

function VoicePageContent() {
  const router = useRouter();
  const search = useSearchParams();

  // Auth state
  const [authUser, setAuthUser] = useState<AuthUser | null>(null);
  const [authLoading, setAuthLoading] = useState(true);

  // Voice settings
  const [settings, setSettings] = useState<VoiceSettings>({
    voice: "nova",
    autoPlay: true,
    continuousMode: false,
  });
  const [showSettings, setShowSettings] = useState(false);

  // Conversation state
  const [transcript, setTranscript] = useState<string>("");
  const [response, setResponse] = useState<string>("");
  const [conversationHistory, setConversationHistory] = useState<
    { role: "user" | "sakhi"; text: string }[]
  >([]);

  // Refs for continuous mode
  const continuousModeRef = useRef(false);

  // Load auth
  useEffect(() => {
    const loadAuth = async () => {
      try {
        const res = await fetch("/api/auth/me");
        if (res.ok) {
          const data = await res.json();
          setAuthUser({
            person_id: data.person_id,
            full_name: data.full_name,
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

  // Load settings from localStorage
  useEffect(() => {
    const saved = localStorage.getItem("sakhi_voice_settings");
    if (saved) {
      try {
        setSettings(JSON.parse(saved));
      } catch {
        // Ignore parse errors
      }
    }
  }, []);

  // Save settings
  const saveSettings = useCallback((newSettings: VoiceSettings) => {
    setSettings(newSettings);
    localStorage.setItem("sakhi_voice_settings", JSON.stringify(newSettings));
  }, []);

  // Voice hook
  const voice = useVoice({
    personId: authUser?.person_id || "",
    autoPlayResponse: settings.autoPlay,
    onTranscript: (t) => {
      if (t.isFinal && t.text) {
        setTranscript(t.text);
        setConversationHistory((prev) => [...prev, { role: "user", text: t.text }]);
      }
    },
    onResponse: (r) => {
      if (r.text) {
        setResponse(r.text);
        setConversationHistory((prev) => [...prev, { role: "sakhi", text: r.text }]);
      }
    },
    onStateChange: (state) => {
      // If continuous mode and we just finished speaking, start recording again
      if (
        state === "idle" &&
        continuousModeRef.current &&
        settings.continuousMode
      ) {
        setTimeout(() => {
          if (continuousModeRef.current) {
            voice.startRecording();
          }
        }, 1500); // Brief pause before listening again
      }
    },
  });

  // Toggle continuous mode
  const toggleContinuousMode = useCallback(() => {
    if (settings.continuousMode) {
      // Turn off
      continuousModeRef.current = false;
      saveSettings({ ...settings, continuousMode: false });
      if (voice.isRecording) {
        voice.cancelRecording();
      }
    } else {
      // Turn on
      continuousModeRef.current = true;
      saveSettings({ ...settings, continuousMode: true });
      voice.startRecording();
    }
  }, [settings, saveSettings, voice]);

  // Handle main button press
  const handleMainButton = useCallback(async () => {
    if (voice.isRecording) {
      await voice.stopRecording();
    } else if (voice.isSpeaking) {
      voice.stopPlayback();
    } else if (!voice.isProcessing) {
      setTranscript("");
      setResponse("");
      await voice.startRecording();
    }
  }, [voice]);

  // Get state-dependent styles
  const getOrbStyles = () => {
    if (voice.isRecording) {
      return {
        borderColor: palette.recording,
        glowColor: palette.recordingGlow,
        pulseAnimation: true,
      };
    }
    if (voice.isProcessing) {
      return {
        borderColor: palette.processing,
        glowColor: palette.processingGlow,
        pulseAnimation: false,
        spinAnimation: true,
      };
    }
    if (voice.isSpeaking) {
      return {
        borderColor: palette.speaking,
        glowColor: palette.speakingGlow,
        pulseAnimation: true,
      };
    }
    return {
      borderColor: palette.muted,
      glowColor: "transparent",
      pulseAnimation: false,
    };
  };

  const orbStyles = getOrbStyles();
  const isActive = voice.isRecording || voice.isProcessing || voice.isSpeaking;

  // Status text
  const getStatusText = () => {
    if (voice.isRecording) return "Listening...";
    if (voice.isProcessing) return "Thinking...";
    if (voice.isSpeaking) return "Speaking...";
    if (settings.continuousMode) return "Continuous mode - tap to pause";
    return "Tap to speak";
  };

  // Loading state
  if (authLoading) {
    return (
      <div style={containerStyle}>
        <p style={{ color: palette.muted }}>Loading...</p>
      </div>
    );
  }

  return (
    <div style={containerStyle}>
      <style>{`
        @keyframes pulse {
          0% { transform: scale(1); opacity: 0.6; }
          50% { transform: scale(1.15); opacity: 0.3; }
          100% { transform: scale(1); opacity: 0.6; }
        }
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        @keyframes breathe {
          0% { transform: scale(0.95); opacity: 0.5; }
          50% { transform: scale(1.05); opacity: 0.8; }
          100% { transform: scale(0.95); opacity: 0.5; }
        }
        @keyframes waveform {
          0%, 100% { height: 4px; }
          50% { height: 24px; }
        }
      `}</style>

      {/* Header */}
      <header style={headerStyle}>
        <Link
          href={`/experience/converse?user=${encodeURIComponent(authUser?.person_id || "")}` as Route}
          style={backButtonStyle}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M19 12H5M12 19l-7-7 7-7" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </Link>
        <span style={{ fontSize: "14px", letterSpacing: "0.1em", textTransform: "uppercase" }}>
          Sakhi Voice
        </span>
        <button style={settingsButtonStyle} onClick={() => setShowSettings(true)}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="3" />
            <path d="M12 1v4M12 19v4M4.22 4.22l2.83 2.83M16.95 16.95l2.83 2.83M1 12h4M19 12h4M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83" />
          </svg>
        </button>
      </header>

      {/* Main Content */}
      <main style={mainStyle}>
        {/* Recent Transcript */}
        {transcript && (
          <div style={transcriptStyle}>
            <span style={{ color: palette.muted, fontSize: "12px", marginBottom: "4px", display: "block" }}>
              You said:
            </span>
            {transcript}
          </div>
        )}

        {/* Voice Orb */}
        <div style={orbContainerStyle}>
          <button
            style={{
              ...orbStyle,
              borderColor: orbStyles.borderColor,
              cursor: voice.isProcessing ? "wait" : "pointer",
            }}
            onClick={handleMainButton}
            disabled={voice.isProcessing}
          >
            {/* Glow effect */}
            {isActive && (
              <div
                style={{
                  ...orbGlowStyle,
                  background: `radial-gradient(circle, ${orbStyles.glowColor} 0%, transparent 70%)`,
                  animation: orbStyles.pulseAnimation
                    ? "pulse 2s ease-in-out infinite"
                    : orbStyles.spinAnimation
                    ? "spin 2s linear infinite"
                    : "none",
                }}
              />
            )}

            {/* Icon */}
            {voice.isProcessing ? (
              <svg
                viewBox="0 0 24 24"
                style={{ width: 48, height: 48, animation: "spin 1s linear infinite" }}
              >
                <circle
                  cx="12"
                  cy="12"
                  r="10"
                  stroke={palette.processing}
                  strokeWidth="2"
                  fill="none"
                  strokeDasharray="31.4 31.4"
                  strokeLinecap="round"
                />
              </svg>
            ) : voice.isSpeaking ? (
              // Waveform animation for speaking
              <div style={{ display: "flex", gap: "4px", alignItems: "center", height: "32px" }}>
                {[0, 1, 2, 3, 4].map((i) => (
                  <div
                    key={i}
                    style={{
                      width: "4px",
                      height: "12px",
                      background: palette.speaking,
                      borderRadius: "2px",
                      animation: `waveform 0.6s ease-in-out ${i * 0.1}s infinite`,
                    }}
                  />
                ))}
              </div>
            ) : (
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke={voice.isRecording ? palette.recording : palette.fg}
                strokeWidth="1.5"
                style={{ width: 48, height: 48 }}
              >
                <rect x="9" y="3" width="6" height="11" rx="3" />
                <path d="M5 10v2a7 7 0 0 0 14 0v-2" strokeLinecap="round" />
                <line x1="12" y1="19" x2="12" y2="22" strokeLinecap="round" />
              </svg>
            )}
          </button>
        </div>

        {/* Status Text */}
        <div style={statusTextStyle}>{getStatusText()}</div>

        {/* Response */}
        {response && (
          <div style={responseStyle}>
            <span style={{ color: palette.muted, fontSize: "12px", marginBottom: "4px", display: "block" }}>
              Sakhi:
            </span>
            {response}
          </div>
        )}
      </main>

      {/* Bottom Controls */}
      <footer style={footerStyle}>
        <button
          style={{
            ...controlButtonStyle,
            background: settings.continuousMode ? palette.accent : "transparent",
            borderColor: settings.continuousMode ? palette.accent : palette.muted,
          }}
          onClick={toggleContinuousMode}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M17 1l4 4-4 4" strokeLinecap="round" strokeLinejoin="round" />
            <path d="M3 11V9a4 4 0 0 1 4-4h14" strokeLinecap="round" strokeLinejoin="round" />
            <path d="M7 23l-4-4 4-4" strokeLinecap="round" strokeLinejoin="round" />
            <path d="M21 13v2a4 4 0 0 1-4 4H3" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <span style={{ marginLeft: "8px" }}>Continuous</span>
        </button>

        {voice.isSpeaking && (
          <button style={controlButtonStyle} onClick={() => voice.stopPlayback()}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="6" y="4" width="4" height="16" rx="1" />
              <rect x="14" y="4" width="4" height="16" rx="1" />
            </svg>
            <span style={{ marginLeft: "8px" }}>Stop</span>
          </button>
        )}
      </footer>

      {/* Settings Modal */}
      {showSettings && (
        <div style={modalOverlayStyle} onClick={() => setShowSettings(false)}>
          <div style={modalStyle} onClick={(e) => e.stopPropagation()}>
            <h2 style={{ fontSize: "18px", marginBottom: "20px" }}>Voice Settings</h2>

            {/* Voice Selection */}
            <div style={settingGroupStyle}>
              <label style={settingLabelStyle}>Voice</label>
              <div style={{ display: "flex", gap: "8px" }}>
                {(["nova", "shimmer", "alloy"] as const).map((v) => (
                  <button
                    key={v}
                    style={{
                      ...voiceOptionStyle,
                      background: settings.voice === v ? palette.accent : "transparent",
                      borderColor: settings.voice === v ? palette.accent : palette.muted,
                    }}
                    onClick={() => saveSettings({ ...settings, voice: v })}
                  >
                    {v === "nova" && "Nova (Warm)"}
                    {v === "shimmer" && "Shimmer (Calm)"}
                    {v === "alloy" && "Alloy (Clear)"}
                  </button>
                ))}
              </div>
            </div>

            {/* Auto-play Toggle */}
            <div style={settingGroupStyle}>
              <label style={settingLabelStyle}>Auto-play responses</label>
              <button
                style={{
                  ...toggleStyle,
                  background: settings.autoPlay ? palette.accent : palette.muted,
                }}
                onClick={() => saveSettings({ ...settings, autoPlay: !settings.autoPlay })}
              >
                <div
                  style={{
                    ...toggleKnobStyle,
                    transform: settings.autoPlay ? "translateX(20px)" : "translateX(0)",
                  }}
                />
              </button>
            </div>

            <button style={closeModalButtonStyle} onClick={() => setShowSettings(false)}>
              Done
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

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
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  padding: "16px 20px",
  borderBottom: `1px solid rgba(255,255,255,0.1)`,
};

const backButtonStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  width: "40px",
  height: "40px",
  borderRadius: "50%",
  background: "transparent",
  color: palette.muted,
  textDecoration: "none",
};

const settingsButtonStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  width: "40px",
  height: "40px",
  borderRadius: "50%",
  background: "transparent",
  border: "none",
  color: palette.muted,
  cursor: "pointer",
};

const mainStyle: React.CSSProperties = {
  flex: 1,
  display: "flex",
  flexDirection: "column",
  alignItems: "center",
  justifyContent: "center",
  padding: "24px",
  gap: "32px",
};

const transcriptStyle: React.CSSProperties = {
  maxWidth: "320px",
  textAlign: "center",
  fontSize: "16px",
  lineHeight: 1.6,
  color: palette.fg,
  opacity: 0.8,
};

const orbContainerStyle: React.CSSProperties = {
  position: "relative",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
};

const orbStyle: React.CSSProperties = {
  position: "relative",
  width: "140px",
  height: "140px",
  borderRadius: "50%",
  border: "2px solid",
  background: "transparent",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  transition: "all 300ms ease",
  zIndex: 1,
};

const orbGlowStyle: React.CSSProperties = {
  position: "absolute",
  width: "180px",
  height: "180px",
  borderRadius: "50%",
  zIndex: 0,
};

const statusTextStyle: React.CSSProperties = {
  fontSize: "14px",
  color: palette.muted,
  textAlign: "center",
};

const responseStyle: React.CSSProperties = {
  maxWidth: "320px",
  textAlign: "center",
  fontSize: "16px",
  lineHeight: 1.6,
  color: palette.fg,
  padding: "16px 20px",
  background: "rgba(255,255,255,0.05)",
  borderRadius: "16px",
};

const footerStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "center",
  gap: "12px",
  padding: "24px",
  borderTop: `1px solid rgba(255,255,255,0.1)`,
};

const controlButtonStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  padding: "12px 20px",
  borderRadius: "24px",
  border: "1px solid",
  background: "transparent",
  color: palette.fg,
  fontSize: "14px",
  cursor: "pointer",
  transition: "all 200ms ease",
};

const modalOverlayStyle: React.CSSProperties = {
  position: "fixed",
  inset: 0,
  background: "rgba(0,0,0,0.8)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  zIndex: 100,
};

const modalStyle: React.CSSProperties = {
  background: "#1a1a1e",
  padding: "24px",
  borderRadius: "16px",
  width: "90%",
  maxWidth: "360px",
};

const settingGroupStyle: React.CSSProperties = {
  marginBottom: "20px",
};

const settingLabelStyle: React.CSSProperties = {
  display: "block",
  fontSize: "13px",
  color: palette.muted,
  marginBottom: "8px",
};

const voiceOptionStyle: React.CSSProperties = {
  padding: "8px 12px",
  borderRadius: "8px",
  border: "1px solid",
  background: "transparent",
  color: palette.fg,
  fontSize: "13px",
  cursor: "pointer",
};

const toggleStyle: React.CSSProperties = {
  width: "48px",
  height: "28px",
  borderRadius: "14px",
  border: "none",
  position: "relative",
  cursor: "pointer",
  transition: "background 200ms ease",
};

const toggleKnobStyle: React.CSSProperties = {
  position: "absolute",
  top: "4px",
  left: "4px",
  width: "20px",
  height: "20px",
  borderRadius: "50%",
  background: "#fff",
  transition: "transform 200ms ease",
};

const closeModalButtonStyle: React.CSSProperties = {
  width: "100%",
  padding: "14px",
  borderRadius: "12px",
  border: "none",
  background: palette.accent,
  color: "#fff",
  fontSize: "15px",
  fontWeight: 500,
  cursor: "pointer",
  marginTop: "8px",
};
