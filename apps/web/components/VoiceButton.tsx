"use client";

import React, { useCallback } from "react";
import { useVoice, VoiceState } from "@/lib/hooks/useVoice";

// =============================================================================
// TYPES
// =============================================================================

interface VoiceButtonProps {
  personId: string;
  onTranscript?: (text: string) => void;
  onResponse?: (text: string) => void;
  onError?: (error: Error) => void;
  size?: "small" | "medium" | "large";
  showStatus?: boolean;
  className?: string;
}

// =============================================================================
// STYLES
// =============================================================================

const palette = {
  bg: "#0e0f12",
  fg: "#f4f4f5",
  muted: "#a1a1aa",
  accent: "#6366f1",
  accentHover: "#818cf8",
  recording: "#ef4444",
  processing: "#f59e0b",
  speaking: "#22c55e",
  pulse: "rgba(99, 102, 241, 0.4)",
  pulseSpeaking: "rgba(34, 197, 94, 0.4)",
};

const sizes = {
  small: { button: 48, icon: 20, pulse: 64 },
  medium: { button: 64, icon: 24, pulse: 80 },
  large: { button: 80, icon: 32, pulse: 100 },
};

// =============================================================================
// COMPONENT
// =============================================================================

export function VoiceButton({
  personId,
  onTranscript,
  onResponse,
  onError,
  size = "medium",
  showStatus = true,
  className = "",
}: VoiceButtonProps) {
  const {
    state,
    isRecording,
    isProcessing,
    isSpeaking,
    transcript,
    startRecording,
    stopRecording,
    cancelRecording,
    stopPlayback,
  } = useVoice({
    personId,
    onTranscript: (t) => onTranscript?.(t.text),
    onResponse: (r) => onResponse?.(r.text),
    onError,
    autoPlayResponse: true,
  });

  const sizeConfig = sizes[size];

  // Handle button click based on current state
  const handleClick = useCallback(async () => {
    switch (state) {
      case "idle":
      case "error":
        await startRecording();
        break;
      case "recording":
        await stopRecording();
        break;
      case "speaking":
        stopPlayback();
        break;
      case "processing":
        // Can't interrupt processing
        break;
    }
  }, [state, startRecording, stopRecording, stopPlayback]);

  // Handle long press to cancel
  const handleLongPress = useCallback(() => {
    if (isRecording) {
      cancelRecording();
    }
  }, [isRecording, cancelRecording]);

  // Get button color based on state
  const getButtonColor = () => {
    switch (state) {
      case "recording":
        return palette.recording;
      case "processing":
        return palette.processing;
      case "speaking":
        return palette.speaking;
      default:
        return "transparent";
    }
  };

  // Get border color based on state
  const getBorderColor = () => {
    switch (state) {
      case "recording":
        return palette.recording;
      case "processing":
        return palette.processing;
      case "speaking":
        return palette.speaking;
      default:
        return palette.muted;
    }
  };

  // Get status text
  const getStatusText = () => {
    switch (state) {
      case "idle":
        return "Tap to speak";
      case "recording":
        return "Listening... tap to send";
      case "processing":
        return "Thinking...";
      case "speaking":
        return "Sakhi is speaking...";
      case "error":
        return "Try again";
      default:
        return "";
    }
  };

  // Get pulse color
  const getPulseColor = () => {
    if (isSpeaking) return palette.pulseSpeaking;
    if (isRecording) return palette.pulse;
    return "transparent";
  };

  const buttonStyle: React.CSSProperties = {
    width: sizeConfig.button,
    height: sizeConfig.button,
    borderRadius: "50%",
    border: `2px solid ${getBorderColor()}`,
    background: getButtonColor(),
    color: state === "idle" || state === "error" ? palette.fg : "#fff",
    cursor: isProcessing ? "wait" : "pointer",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    transition: "all 200ms ease",
    position: "relative",
    outline: "none",
  };

  const pulseStyle: React.CSSProperties = {
    position: "absolute",
    width: sizeConfig.pulse,
    height: sizeConfig.pulse,
    borderRadius: "50%",
    background: getPulseColor(),
    animation: isRecording || isSpeaking ? "voicePulse 1.5s ease-in-out infinite" : "none",
    pointerEvents: "none",
  };

  const statusStyle: React.CSSProperties = {
    fontSize: "13px",
    color: palette.muted,
    marginTop: "8px",
    textAlign: "center",
  };

  const transcriptStyle: React.CSSProperties = {
    fontSize: "12px",
    color: palette.muted,
    marginTop: "4px",
    maxWidth: "200px",
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
    opacity: 0.7,
  };

  return (
    <div className={className} style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
      <style>{`
        @keyframes voicePulse {
          0% { transform: scale(0.9); opacity: 0.7; }
          50% { transform: scale(1.1); opacity: 0.3; }
          100% { transform: scale(0.9); opacity: 0.7; }
        }
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>

      <button
        type="button"
        style={buttonStyle}
        onClick={handleClick}
        onContextMenu={(e) => {
          e.preventDefault();
          handleLongPress();
        }}
        disabled={isProcessing}
        aria-label={getStatusText()}
      >
        {(isRecording || isSpeaking) && <div style={pulseStyle} />}

        {/* Icon based on state */}
        {isProcessing ? (
          // Spinner
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            style={{
              width: sizeConfig.icon,
              height: sizeConfig.icon,
              animation: "spin 1s linear infinite",
              position: "relative",
              zIndex: 1,
            }}
          >
            <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
          </svg>
        ) : isSpeaking ? (
          // Sound waves
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            style={{ width: sizeConfig.icon, height: sizeConfig.icon, position: "relative", zIndex: 1 }}
          >
            <path d="M11 5L6 9H2v6h4l5 4V5z" />
            <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
            <path d="M19.07 4.93a10 10 0 0 1 0 14.14" />
          </svg>
        ) : (
          // Microphone
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            style={{ width: sizeConfig.icon, height: sizeConfig.icon, position: "relative", zIndex: 1 }}
          >
            <rect x="9" y="3" width="6" height="11" rx="3" />
            <path d="M5 10v2a7 7 0 0 0 14 0v-2" />
            <line x1="12" y1="19" x2="12" y2="22" />
          </svg>
        )}
      </button>

      {showStatus && (
        <>
          <div style={statusStyle}>{getStatusText()}</div>
          {transcript && state !== "idle" && (
            <div style={transcriptStyle} title={transcript}>
              &ldquo;{transcript}&rdquo;
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default VoiceButton;
