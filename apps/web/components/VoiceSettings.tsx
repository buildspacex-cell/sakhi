"use client";

import { useState, useEffect, useCallback } from "react";

// =============================================================================
// TYPES
// =============================================================================

export type VoiceOption = "nova" | "shimmer" | "alloy";

export interface VoiceSettingsData {
  voice: VoiceOption;
  speed: number;
  autoPlay: boolean;
}

export interface VoiceSettingsProps {
  isOpen: boolean;
  onClose: () => void;
  onSave?: (settings: VoiceSettingsData) => void;
}

// Voice descriptions
const VOICE_OPTIONS: { value: VoiceOption; label: string; description: string }[] = [
  { value: "nova", label: "Nova", description: "Warm and friendly - default for Sakhi" },
  { value: "shimmer", label: "Shimmer", description: "Soft and calming" },
  { value: "alloy", label: "Alloy", description: "Clear and neutral" },
];

// Storage key
const STORAGE_KEY = "sakhi_voice_settings";

// =============================================================================
// HOOKS
// =============================================================================

export function useVoiceSettings() {
  const [settings, setSettings] = useState<VoiceSettingsData>({
    voice: "nova",
    speed: 1.0,
    autoPlay: true,
  });

  // Load from localStorage on mount
  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        setSettings((prev) => ({
          ...prev,
          ...parsed,
        }));
      } catch {
        // Ignore parse errors
      }
    }
  }, []);

  // Save to localStorage
  const saveSettings = useCallback((newSettings: Partial<VoiceSettingsData>) => {
    setSettings((prev) => {
      const updated = { ...prev, ...newSettings };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
      return updated;
    });
  }, []);

  return { settings, saveSettings };
}

// =============================================================================
// COMPONENT
// =============================================================================

export default function VoiceSettings({ isOpen, onClose, onSave }: VoiceSettingsProps) {
  const { settings, saveSettings } = useVoiceSettings();
  const [localSettings, setLocalSettings] = useState(settings);

  // Sync with parent settings
  useEffect(() => {
    if (isOpen) {
      setLocalSettings(settings);
    }
  }, [isOpen, settings]);

  const handleSave = () => {
    saveSettings(localSettings);
    onSave?.(localSettings);
    onClose();
  };

  const handleVoiceChange = (voice: VoiceOption) => {
    setLocalSettings((prev) => ({ ...prev, voice }));
  };

  const handleSpeedChange = (speed: number) => {
    setLocalSettings((prev) => ({ ...prev, speed }));
  };

  const handleAutoPlayToggle = () => {
    setLocalSettings((prev) => ({ ...prev, autoPlay: !prev.autoPlay }));
  };

  // Test voice
  const testVoice = async () => {
    try {
      const res = await fetch("/api/voice/tts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: "Hello! This is how I'll sound when we talk.",
          voice: localSettings.voice,
          speed: localSettings.speed,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        if (data.audio_url) {
          const audio = new Audio(data.audio_url);
          audio.play();
        }
      }
    } catch (err) {
      console.error("Test voice error:", err);
    }
  };

  if (!isOpen) return null;

  return (
    <div style={overlayStyle} onClick={onClose}>
      <div style={modalStyle} onClick={(e) => e.stopPropagation()}>
        <div style={headerStyle}>
          <h2 style={titleStyle}>Voice Settings</h2>
          <button style={closeIconStyle} onClick={onClose}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M18 6L6 18M6 6l12 12" strokeLinecap="round" />
            </svg>
          </button>
        </div>

        {/* Voice Selection */}
        <div style={sectionStyle}>
          <label style={labelStyle}>Voice</label>
          <div style={voiceGridStyle}>
            {VOICE_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                style={{
                  ...voiceCardStyle,
                  borderColor: localSettings.voice === opt.value ? "#6366f1" : "#3f3f46",
                  background: localSettings.voice === opt.value ? "rgba(99, 102, 241, 0.1)" : "transparent",
                }}
                onClick={() => handleVoiceChange(opt.value)}
              >
                <div style={{ fontWeight: 500, marginBottom: "4px" }}>{opt.label}</div>
                <div style={{ fontSize: "12px", color: "#a1a1aa" }}>{opt.description}</div>
              </button>
            ))}
          </div>
        </div>

        {/* Speed Slider */}
        <div style={sectionStyle}>
          <label style={labelStyle}>
            Speed: {localSettings.speed.toFixed(1)}x
          </label>
          <input
            type="range"
            min="0.5"
            max="2.0"
            step="0.1"
            value={localSettings.speed}
            onChange={(e) => handleSpeedChange(parseFloat(e.target.value))}
            style={sliderStyle}
          />
          <div style={sliderLabelsStyle}>
            <span>0.5x</span>
            <span>1.0x</span>
            <span>2.0x</span>
          </div>
        </div>

        {/* Auto-play Toggle */}
        <div style={sectionStyle}>
          <div style={toggleRowStyle}>
            <div>
              <div style={{ fontWeight: 500 }}>Auto-play responses</div>
              <div style={{ fontSize: "13px", color: "#a1a1aa", marginTop: "2px" }}>
                Automatically speak Sakhi's responses
              </div>
            </div>
            <button
              style={{
                ...toggleStyle,
                background: localSettings.autoPlay ? "#6366f1" : "#3f3f46",
              }}
              onClick={handleAutoPlayToggle}
            >
              <div
                style={{
                  ...toggleKnobStyle,
                  transform: localSettings.autoPlay ? "translateX(20px)" : "translateX(0)",
                }}
              />
            </button>
          </div>
        </div>

        {/* Actions */}
        <div style={actionsStyle}>
          <button style={testButtonStyle} onClick={testVoice}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polygon points="5 3 19 12 5 21 5 3" />
            </svg>
            Test Voice
          </button>
          <button style={saveButtonStyle} onClick={handleSave}>
            Save Changes
          </button>
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// STYLES
// =============================================================================

const overlayStyle: React.CSSProperties = {
  position: "fixed",
  inset: 0,
  background: "rgba(0, 0, 0, 0.8)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  zIndex: 1000,
  padding: "20px",
};

const modalStyle: React.CSSProperties = {
  background: "#18181b",
  borderRadius: "16px",
  padding: "24px",
  width: "100%",
  maxWidth: "400px",
  maxHeight: "90vh",
  overflowY: "auto",
  color: "#f4f4f5",
  fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Inter, sans-serif',
};

const headerStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  marginBottom: "24px",
};

const titleStyle: React.CSSProperties = {
  fontSize: "18px",
  fontWeight: 600,
  margin: 0,
};

const closeIconStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  width: "32px",
  height: "32px",
  borderRadius: "8px",
  border: "none",
  background: "transparent",
  color: "#a1a1aa",
  cursor: "pointer",
};

const sectionStyle: React.CSSProperties = {
  marginBottom: "24px",
};

const labelStyle: React.CSSProperties = {
  display: "block",
  fontSize: "14px",
  color: "#a1a1aa",
  marginBottom: "12px",
};

const voiceGridStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "8px",
};

const voiceCardStyle: React.CSSProperties = {
  padding: "12px 16px",
  borderRadius: "10px",
  border: "1px solid",
  background: "transparent",
  color: "#f4f4f5",
  textAlign: "left",
  cursor: "pointer",
  transition: "all 150ms ease",
};

const sliderStyle: React.CSSProperties = {
  width: "100%",
  height: "4px",
  borderRadius: "2px",
  appearance: "none",
  background: "#3f3f46",
  cursor: "pointer",
};

const sliderLabelsStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  fontSize: "12px",
  color: "#71717a",
  marginTop: "8px",
};

const toggleRowStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  gap: "16px",
};

const toggleStyle: React.CSSProperties = {
  width: "48px",
  height: "28px",
  borderRadius: "14px",
  border: "none",
  position: "relative",
  cursor: "pointer",
  transition: "background 200ms ease",
  flexShrink: 0,
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

const actionsStyle: React.CSSProperties = {
  display: "flex",
  gap: "12px",
  marginTop: "8px",
};

const testButtonStyle: React.CSSProperties = {
  flex: 1,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  gap: "8px",
  padding: "12px",
  borderRadius: "10px",
  border: "1px solid #3f3f46",
  background: "transparent",
  color: "#f4f4f5",
  fontSize: "14px",
  cursor: "pointer",
};

const saveButtonStyle: React.CSSProperties = {
  flex: 1,
  padding: "12px",
  borderRadius: "10px",
  border: "none",
  background: "#6366f1",
  color: "#fff",
  fontSize: "14px",
  fontWeight: 500,
  cursor: "pointer",
};
