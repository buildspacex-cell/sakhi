"use client";

import { Suspense, useState, useCallback, useMemo, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import type React from "react";
import type { Route } from "next";

export const dynamic = "force-dynamic";

// =============================================================================
// PALETTE
// =============================================================================

const palette = {
  bg: "#0a0a0a",
  fg: "#f4f4f5",
  muted: "#a1a1aa",
  mutedDark: "#71717a",
  dimText: "#52525b",
  dimmer: "#3f3f46",
  accent: "#6366f1",
  cardBg: "#18191d",
  border: "#27272a",
  borderDim: "#1a1a1f",
  error: "#ef4444",
  success: "#22c55e",
  barAdaptive: "#8b5cf6",
  barPerformance: "#f59e0b",
  barConservation: "#10b981",
};

const fontFamily =
  '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Inter, Helvetica, Arial, sans-serif';

// =============================================================================
// TYPES
// =============================================================================

interface Question {
  id: string;
  text: string;
  type: "single" | "multi" | "text";
  options?: { value: string; label: string }[];
  placeholder?: string;
  optional?: boolean;
}

interface Screen {
  id: string;
  title: string;
  subtitle?: string;
  body?: string;
  questions: Question[];
  isTransition?: boolean;
  isCalibration?: boolean;
  isMirror?: boolean;
  isFollowUp?: boolean;
  isIntermediateOS?: boolean;
  isFinalOS?: boolean;
  skipAllowed?: boolean;
}

interface DoshaBaseline {
  vata: number;
  pitta: number;
  kapha: number;
}

interface OSDetails {
  description: string;
  strengths: string[];
  patterns_to_watch: string[];
}

interface OnboardingResponse {
  success: boolean;
  person_id: string;
  phase_completed: string;
  phases_remaining: string[];
  operating_system: string;
  primary: string;
  secondary: string | null;
  dosha_baseline: DoshaBaseline;
  os_confidence: number;
  os_label: string;
  os_details: OSDetails;
}

// =============================================================================
// SCREEN DATA — MAIN FLOW (matches mobile exactly)
// =============================================================================

const SCREENS: Screen[] = [
  {
    id: "framing",
    title: "What should I call you?",
    subtitle: "Whatever feels natural to you.",
    questions: [
      {
        id: "preferred_name",
        text: "",
        type: "text",
        placeholder: "Your name (or a nickname)",
      },
    ],
  },
  {
    id: "transition",
    title: "I will get to know you gently.",
    body: "Just 3 things to start.\nThe rest unfolds through conversation, at your pace.",
    questions: [],
    isTransition: true,
  },
  {
    id: "clarity_time",
    title: "When do you usually feel most clear and like yourself?",
    questions: [
      {
        id: "clarity_window",
        text: "",
        type: "single",
        options: [
          { value: "early_morning", label: "Early morning" },
          { value: "late_morning", label: "Late morning" },
          { value: "afternoon", label: "Afternoon" },
          { value: "evening", label: "Evening" },
          { value: "varies", label: "It varies a lot" },
        ],
      },
    ],
    isCalibration: true,
  },
  {
    id: "demanding_days",
    title: "When days get demanding, you usually\u2026",
    questions: [
      {
        id: "pacing_under_demand",
        text: "",
        type: "single",
        options: [
          { value: "push_harder", label: "Push through and keep going" },
          { value: "slow_down", label: "Slow down and conserve energy" },
          { value: "oscillate", label: "Shift between both depending on the situation" },
        ],
      },
    ],
    isCalibration: true,
  },
  {
    id: "first_signal",
    title: "When life gets busy, what do you usually notice first?",
    questions: [
      {
        id: "first_stress_signal",
        text: "",
        type: "single",
        options: [
          { value: "irritability", label: "Tension or tightness in my body" },
          { value: "sleep_trouble", label: "Mental fog or scattered thoughts" },
          { value: "low_energy", label: "Low energy or heaviness" },
          { value: "depends", label: "I\u2019m not sure" },
        ],
      },
    ],
    isCalibration: true,
  },
  {
    id: "mirror",
    title: "",
    questions: [],
    isMirror: true,
  },
  {
    id: "follow_up",
    title: "",
    questions: [],
    isFollowUp: true,
  },
];

// =============================================================================
// SCREEN DATA — REFINE FLOW
// =============================================================================

const REFINE_SCREENS: Screen[] = [
  {
    id: "refine_intro",
    title: "A few more questions",
    body: "These help Sakhi understand you a little better.\nAnswer what feels useful, skip anything you don\u2019t want to share.",
    questions: [],
    isTransition: true,
  },
  {
    id: "current_energy",
    title: "Right now, your energy feels\u2026",
    questions: [
      {
        id: "current_energy",
        text: "",
        type: "single",
        options: [
          { value: "steady", label: "Steady" },
          { value: "waves", label: "In waves" },
          { value: "drained", label: "Drained" },
          { value: "wired_tired", label: "Wired but tired" },
        ],
      },
    ],
    isCalibration: true,
  },
  {
    id: "body_request",
    title: "After a few demanding days, your body usually asks for\u2026",
    questions: [
      {
        id: "body_request",
        text: "",
        type: "single",
        options: [
          { value: "quiet_space", label: "Quiet or mental space" },
          { value: "physical_release", label: "Physical release (walk, stretch, workout)" },
          { value: "rest_food", label: "Extra rest or comforting food" },
          { value: "unsure", label: "I\u2019m not sure" },
        ],
      },
    ],
    isCalibration: true,
  },
  {
    id: "intermediate_os",
    title: "",
    questions: [],
    isIntermediateOS: true,
  },
  {
    id: "life_phase",
    title: "This phase of life feels like\u2026",
    questions: [
      {
        id: "life_phase",
        text: "",
        type: "single",
        options: [
          { value: "building", label: "Building" },
          { value: "maintaining", label: "Maintaining" },
          { value: "reorienting", label: "Re-orienting" },
          { value: "recovering", label: "Recovering" },
        ],
      },
    ],
    isCalibration: true,
  },
  {
    id: "time_horizon",
    title: "Right now, most of your decisions are shaped by\u2026",
    questions: [
      {
        id: "time_horizon",
        text: "",
        type: "single",
        options: [
          { value: "weeks", label: "What will help in the next few weeks" },
          { value: "year_two", label: "What will matter over the next year or two" },
          { value: "long_term", label: "A longer-term direction I\u2019m holding in mind" },
        ],
      },
    ],
    isCalibration: true,
  },
  {
    id: "fastest_recovery",
    title: "What helps you recover fastest?",
    questions: [
      {
        id: "fastest_recovery",
        text: "",
        type: "single",
        options: [
          { value: "calm_time", label: "Calm, low-stimulus time" },
          { value: "movement", label: "Moving my body" },
          { value: "sleep_food", label: "Sleeping or eating well" },
          { value: "varies", label: "It varies" },
        ],
      },
    ],
    isCalibration: true,
  },
  {
    id: "active_roles",
    title: "Which roles feel most present right now?",
    subtitle: "Select all that apply",
    questions: [
      {
        id: "active_roles",
        text: "",
        type: "multi",
        options: [
          { value: "professional", label: "Professional / builder" },
          { value: "caregiver", label: "Caregiver" },
          { value: "partner_family", label: "Partner / family" },
          { value: "transition", label: "Personal transition" },
        ],
      },
    ],
    isCalibration: true,
  },
  {
    id: "responsibility_load",
    title: "Your current responsibility load feels\u2026",
    questions: [
      {
        id: "responsibility_load",
        text: "",
        type: "single",
        options: [
          { value: "personal", label: "Mostly personal" },
          { value: "shared", label: "Shared" },
          { value: "carrying_others", label: "Carrying others" },
        ],
      },
    ],
    isCalibration: true,
  },
  {
    id: "decision_driver",
    title: "When choosing between two reasonable options, what usually tips the scale?",
    questions: [
      {
        id: "decision_driver",
        text: "",
        type: "single",
        options: [
          { value: "protect_energy", label: "Protecting my energy or health" },
          { value: "people_relationships", label: "Making time for people" },
          { value: "reduce_stress", label: "Reducing stress or uncertainty" },
          { value: "make_progress", label: "Making progress" },
          { value: "depends", label: "It depends" },
        ],
      },
    ],
    isCalibration: true,
  },
  {
    id: "flexibility_under_load",
    title: "When plans start to feel heavy or constrained, you tend to\u2026",
    questions: [
      {
        id: "flexibility_under_load",
        text: "",
        type: "single",
        options: [
          { value: "simplify", label: "Simplify and reduce commitments" },
          { value: "reorganize", label: "Reorganize and push through" },
          { value: "pause_reassess", label: "Pause and reassess before deciding" },
        ],
      },
    ],
    isCalibration: true,
  },
  {
    id: "body_rhythms",
    title: "Are there any body rhythms Sakhi should be aware of?",
    questions: [
      {
        id: "body_rhythm",
        text: "",
        type: "single",
        options: [
          { value: "menstrual_cycle", label: "Menstrual cycle" },
          { value: "perimenopause", label: "Perimenopause / menopause" },
          { value: "testosterone_cycle", label: "Testosterone-driven cycle" },
          { value: "prefer_not_say", label: "Prefer not to say" },
          { value: "not_sure", label: "Not sure" },
        ],
      },
    ],
    isCalibration: true,
    skipAllowed: true,
  },
  {
    id: "refine_complete",
    title: "",
    questions: [],
    isFinalOS: true,
  },
];

// =============================================================================
// OS FRAMEWORK CARDS (for "About your Personal OS" modal)
// =============================================================================

const OS_FRAMEWORK_CARDS = [
  {
    id: 1,
    title: "Adaptive",
    color: palette.barAdaptive,
    body: "Your capacity for creativity, flexibility, and quick thinking.\n\nHigh adaptive energy means you thrive on change, new ideas, and spontaneity.",
    accent: "When overextended: scattered attention, restlessness, anxiety.",
  },
  {
    id: 2,
    title: "Performance",
    color: palette.barPerformance,
    body: "Your drive, focus, and intensity.\n\nHigh performance energy means you pursue goals with precision and don\u2019t shy away from challenge.",
    accent: "When overextended: irritability, perfectionism, burnout.",
  },
  {
    id: 3,
    title: "Conservation",
    color: palette.barConservation,
    body: "Your stability, patience, and endurance.\n\nHigh conservation energy means you bring grounding, loyalty, and steady follow-through.",
    accent: "When overextended: stagnation, resistance to change, heaviness.",
  },
];

// =============================================================================
// MIRROR SCREEN (OS Result after Phase 1)
// =============================================================================

function MirrorScreen({
  osResult,
  loading,
  error,
  onContinue,
}: {
  osResult: OnboardingResponse | null;
  loading: boolean;
  error: string | null;
  onContinue: () => void;
}) {
  const [showOSModal, setShowOSModal] = useState(false);
  const [osModalCard, setOsModalCard] = useState(0);
  const osScrollRef = useCallback((el: HTMLDivElement | null) => {
    if (el) {
      const handleScroll = () => {
        const index = Math.round(el.scrollLeft / el.clientWidth);
        setOsModalCard(index);
      };
      el.addEventListener("scroll", handleScroll);
    }
  }, []);

  if (loading) {
    return (
      <div style={fullScreenStyle}>
        <div style={centerContentStyle}>
          <div style={spinnerStyle} />
          <p style={{ color: palette.muted, marginTop: "16px", fontSize: "16px" }}>
            Analyzing your responses...
          </p>
        </div>
      </div>
    );
  }

  if (error || !osResult) {
    return (
      <div style={fullScreenStyle}>
        <div style={centerContentStyle}>
          <p style={{ color: palette.error, fontSize: "16px", textAlign: "center", marginBottom: "24px", lineHeight: "24px" }}>
            {error || "Something went wrong. Please try again."}
          </p>
          <button style={secondaryButtonStyle} onClick={onContinue}>
            Continue anyway
          </button>
        </div>
      </div>
    );
  }

  const adaptive = Math.round(osResult.dosha_baseline.vata * 100);
  const performance = Math.round(osResult.dosha_baseline.pitta * 100);
  const conservation = Math.round(osResult.dosha_baseline.kapha * 100);
  const isLastOSCard = osModalCard === OS_FRAMEWORK_CARDS.length - 1;

  return (
    <div style={fullScreenStyle}>
      <div style={{ maxWidth: "560px", width: "100%", margin: "0 auto", padding: "28px", overflowY: "auto", flex: 1 }}>
        {/* Header */}
        <p style={osHeaderLabelStyle}>YOUR OPERATING SYSTEM</p>

        {/* Primary Title */}
        <h1 style={osTitleStyle}>{osResult.operating_system}</h1>

        {/* Subtitle */}
        <p style={osSubtitleStyle}>{osResult.os_label}</p>

        {/* Description */}
        <p style={osDescriptionStyle}>{osResult.os_details.description}</p>

        {/* Distribution Bars */}
        <div style={{ display: "flex", flexDirection: "column", gap: "18px", marginBottom: "28px" }}>
          <DoshaBar label="Adaptive" value={adaptive} color={palette.barAdaptive} />
          <DoshaBar label="Performance" value={performance} color={palette.barPerformance} />
          <DoshaBar label="Conservation" value={conservation} color={palette.barConservation} />
        </div>

        {/* About your OS link */}
        <button
          style={{ display: "block", margin: "0 auto 24px", padding: "14px 20px", background: "none", border: "none", color: palette.accent, fontSize: "13px", cursor: "pointer", fontFamily, textDecoration: "underline" }}
          onClick={() => { setShowOSModal(true); setOsModalCard(0); }}
        >
          About your Personal OS
        </button>

        {/* Anchor */}
        <p style={anchorLineStyle}>
          This is a starting tendency, not a fixed identity.
        </p>

        {/* CTA — inside content column */}
        <div style={{ display: "flex", justifyContent: "center", padding: "12px 0 40px" }}>
          <button style={primaryCTAStyle} onClick={onContinue}>
            Continue
          </button>
        </div>
      </div>

      {/* OS Framework Modal */}
      {showOSModal && (
        <div style={{ position: "fixed", inset: 0, backgroundColor: "rgba(0, 0, 0, 0.96)", zIndex: 1000, display: "flex", flexDirection: "column", justifyContent: "center", fontFamily }}>
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100%", position: "relative" }}>
            {/* Close */}
            <button
              style={{ position: "absolute", top: "24px", right: "16px", zIndex: 10, width: "48px", height: "48px", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "20px", color: palette.dimText, background: "none", border: "none", cursor: "pointer" }}
              onClick={() => setShowOSModal(false)}
            >
              &#10005;
            </button>

            {/* Swipeable cards */}
            <div
              ref={osScrollRef}
              style={{ display: "flex", overflowX: "auto", scrollSnapType: "x mandatory", WebkitOverflowScrolling: "touch", width: "100%", scrollbarWidth: "none" }}
            >
              {OS_FRAMEWORK_CARDS.map((card) => (
                <div key={card.id} style={{ minWidth: "100%", scrollSnapAlign: "start", display: "flex", justifyContent: "center", padding: "0 36px", boxSizing: "border-box" }}>
                  <div style={{ textAlign: "center", padding: "48px 0", maxWidth: "560px" }}>
                    <div style={{ width: "48px", height: "6px", borderRadius: "3px", backgroundColor: card.color, margin: "0 auto 28px" }} />
                    <h2 style={{ fontSize: "26px", fontWeight: 500, color: "#ffffff", textAlign: "center", lineHeight: "36px", marginBottom: "28px", letterSpacing: "-0.5px" }}>
                      {card.title}
                    </h2>
                    <p style={{ fontSize: "16px", color: palette.muted, textAlign: "center", lineHeight: "26px", marginBottom: "36px", whiteSpace: "pre-line" }}>
                      {card.body}
                    </p>
                    <p style={{ fontSize: "14px", color: palette.mutedDark, textAlign: "center", fontStyle: "italic", lineHeight: "22px" }}>
                      {card.accent}
                    </p>
                  </div>
                </div>
              ))}
            </div>

            {/* Pagination dots */}
            <div style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: "10px", marginTop: "40px", marginBottom: "32px" }}>
              {OS_FRAMEWORK_CARDS.map((_, index) => (
                <div
                  key={index}
                  style={{
                    width: osModalCard === index ? "28px" : "8px",
                    height: "8px",
                    borderRadius: "4px",
                    backgroundColor: osModalCard === index ? palette.accent : palette.border,
                    transition: "all 200ms ease",
                  }}
                />
              ))}
            </div>

            {/* Got it button */}
            <button
              style={{
                margin: "0 28px",
                backgroundColor: isLastOSCard ? palette.cardBg : "transparent",
                padding: "18px 48px",
                borderRadius: "14px",
                border: isLastOSCard ? `1px solid ${palette.border}` : "1px solid transparent",
                cursor: isLastOSCard ? "pointer" : "default",
                minWidth: "220px",
                fontFamily,
              }}
              onClick={() => setShowOSModal(false)}
              disabled={!isLastOSCard}
            >
              <span style={{ fontSize: isLastOSCard ? "15px" : "13px", fontWeight: 500, color: isLastOSCard ? palette.fg : palette.dimText }}>
                {isLastOSCard ? "Got it" : "Swipe to continue"}
              </span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// =============================================================================
// FOLLOW-UP SCREEN
// =============================================================================

function FollowUpScreen({
  onStartConversation,
  onRefine,
}: {
  onStartConversation: () => void;
  onRefine: () => void;
}) {
  return (
    <div style={fullScreenStyle}>
      <div style={{ maxWidth: "560px", width: "100%", margin: "0 auto", padding: "56px 32px 48px", overflowY: "auto", flex: 1, display: "flex", flexDirection: "column", justifyContent: "center" }}>
        <h1 style={{ fontSize: "24px", fontWeight: 500, color: palette.fg, textAlign: "center", marginBottom: "28px", letterSpacing: "-0.3px" }}>
          Let&apos;s refine this together
        </h1>

        <p style={{ fontSize: "15px", color: palette.muted, textAlign: "center", lineHeight: "24px", marginBottom: "14px" }}>
          This snapshot is based on a few early signals. Sakhi learns best over time, from conversation, choices, and patterns you share.
        </p>
        <p style={{ fontSize: "15px", color: palette.mutedDark, textAlign: "center", lineHeight: "24px", marginBottom: "32px" }}>
          You&apos;re always in control of how this evolves.
        </p>

        <div style={{ marginBottom: "28px" }}>
          <p style={{ fontSize: "13px", fontWeight: 500, color: palette.dimText, textAlign: "center", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: "14px" }}>
            You can:
          </p>
          <p style={{ fontSize: "14px", color: palette.muted, textAlign: "center", lineHeight: "22px", marginBottom: "8px" }}>
            &bull; Let this evolve naturally as you talk
          </p>
          <p style={{ fontSize: "14px", color: palette.muted, textAlign: "center", lineHeight: "22px" }}>
            &bull; Or answer more questions to sharpen this view
          </p>
        </div>

        <div style={{ marginTop: "12px", paddingTop: "24px", paddingBottom: "8px", borderTop: `1px solid ${palette.borderDim}`, textAlign: "center" }}>
          <p style={{ fontSize: "10px", fontWeight: 500, color: palette.dimmer, letterSpacing: "1.5px", textTransform: "uppercase", marginBottom: "10px" }}>
            Along the way
          </p>
          <p style={{ fontSize: "13px", color: palette.dimText, textAlign: "center", lineHeight: "20px" }}>
            Sakhi can also help with outside friction: making sense of things, or taking small things off your plate.
          </p>
        </div>

        <div style={{ marginTop: "36px", display: "flex", flexDirection: "column", alignItems: "center", gap: "12px" }}>
          <button style={primaryCTAStyle} onClick={onRefine}>
            Refine this now
          </button>
          <button
            style={{ padding: "14px 24px", background: "none", border: "none", color: palette.dimText, fontSize: "14px", cursor: "pointer", fontFamily }}
            onClick={onStartConversation}
          >
            Start a conversation
          </button>
        </div>

        <p style={{ fontSize: "12px", color: palette.dimmer, textAlign: "center", marginTop: "20px" }}>
          You can revisit or update this anytime.
        </p>
      </div>
    </div>
  );
}

// =============================================================================
// INTERMEDIATE OS SCREEN (after Phase 2a)
// =============================================================================

function IntermediateOSScreen({
  osResult,
  loading,
  error,
  onRefineMore,
  onStartConversation,
}: {
  osResult: OnboardingResponse | null;
  loading: boolean;
  error: string | null;
  onRefineMore: () => void;
  onStartConversation: () => void;
}) {
  if (loading) {
    return (
      <div style={fullScreenStyle}>
        <div style={centerContentStyle}>
          <div style={spinnerStyle} />
          <p style={{ color: palette.muted, marginTop: "16px", fontSize: "16px" }}>
            Refining your profile...
          </p>
        </div>
      </div>
    );
  }

  if (error || !osResult) {
    return (
      <div style={fullScreenStyle}>
        <div style={centerContentStyle}>
          <p style={{ color: palette.error, fontSize: "16px", textAlign: "center", marginBottom: "24px" }}>
            {error || "Something went wrong. Please try again."}
          </p>
          <button style={secondaryButtonStyle} onClick={onStartConversation}>
            Continue anyway
          </button>
        </div>
      </div>
    );
  }

  const adaptive = Math.round(osResult.dosha_baseline.vata * 100);
  const performance = Math.round(osResult.dosha_baseline.pitta * 100);
  const conservation = Math.round(osResult.dosha_baseline.kapha * 100);

  return (
    <div style={fullScreenStyle}>
      <div style={{ maxWidth: "560px", width: "100%", margin: "0 auto", padding: "56px 28px", overflowY: "auto", flex: 1, display: "flex", flexDirection: "column", justifyContent: "center" }}>
        <p style={{ fontSize: "11px", fontWeight: 500, color: palette.dimText, letterSpacing: "2px", textAlign: "center", marginBottom: "10px" }}>
          YOUR OPERATING SYSTEM
        </p>
        <p style={{ fontSize: "14px", color: palette.accent, textAlign: "center", marginBottom: "28px" }}>
          {osResult.os_label}
        </p>
        <h1 style={{ fontSize: "28px", fontWeight: 600, color: palette.fg, textAlign: "center", letterSpacing: "-0.5px", marginBottom: "36px" }}>
          {osResult.operating_system}
        </h1>

        <div style={{ display: "flex", flexDirection: "column", gap: "16px", marginBottom: "36px" }}>
          <DoshaBar label="Adaptive" value={adaptive} color={palette.barAdaptive} />
          <DoshaBar label="Performance" value={performance} color={palette.barPerformance} />
          <DoshaBar label="Conservation" value={conservation} color={palette.barConservation} />
        </div>

        <p style={{ fontSize: "14px", color: palette.dimText, textAlign: "center", marginBottom: "12px" }}>
          A few more questions will sharpen this picture.
        </p>
        <p style={{ fontSize: "13px", color: palette.accent, textAlign: "center", marginBottom: "36px", fontStyle: "italic" }}>
          Refine further to see your strengths and patterns.
        </p>

        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "14px" }}>
          <button style={primaryCTAStyle} onClick={onRefineMore}>
            Refine more
          </button>
          <button
            style={{ padding: "14px 24px", background: "none", border: "none", color: palette.dimText, fontSize: "14px", cursor: "pointer", fontFamily }}
            onClick={onStartConversation}
          >
            Start a conversation
          </button>
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// FINAL OS SCREEN (after Phase 2b)
// =============================================================================

function FinalOSScreen({
  osResult,
  loading,
  error,
  onStartConversation,
}: {
  osResult: OnboardingResponse | null;
  loading: boolean;
  error: string | null;
  onStartConversation: () => void;
}) {
  if (loading) {
    return (
      <div style={fullScreenStyle}>
        <div style={centerContentStyle}>
          <div style={spinnerStyle} />
          <p style={{ color: palette.muted, marginTop: "16px", fontSize: "16px" }}>
            Finalizing your profile...
          </p>
        </div>
      </div>
    );
  }

  if (error || !osResult) {
    return (
      <div style={fullScreenStyle}>
        <div style={centerContentStyle}>
          <p style={{ color: palette.error, fontSize: "16px", textAlign: "center", marginBottom: "24px" }}>
            {error || "Something went wrong. Please try again."}
          </p>
          <button style={secondaryButtonStyle} onClick={onStartConversation}>
            Continue anyway
          </button>
        </div>
      </div>
    );
  }

  const adaptive = Math.round(osResult.dosha_baseline.vata * 100);
  const performance = Math.round(osResult.dosha_baseline.pitta * 100);
  const conservation = Math.round(osResult.dosha_baseline.kapha * 100);

  return (
    <div style={fullScreenStyle}>
      <div style={{ maxWidth: "960px", width: "100%", margin: "0 auto", padding: "40px 28px", overflowY: "auto", flex: 1 }}>
        {/* Header — centered */}
        <p style={{ fontSize: "11px", fontWeight: 500, color: palette.dimText, letterSpacing: "2px", textAlign: "center", marginBottom: "10px" }}>
          YOUR OPERATING SYSTEM
        </p>
        <p style={{ fontSize: "14px", color: palette.success, textAlign: "center", marginBottom: "16px" }}>
          {osResult.os_label}
        </p>
        <h1 style={{ fontSize: "28px", fontWeight: 600, color: palette.fg, textAlign: "center", letterSpacing: "-0.5px", marginBottom: "36px" }}>
          {osResult.operating_system}
        </h1>

        {/* Three-column layout: Bars | Strengths | Patterns */}
        <div style={{ display: "flex", gap: "24px", marginBottom: "36px", flexWrap: "wrap", justifyContent: "center" }}>
          {/* Column 1: Distribution Bars */}
          <div style={{ flex: "1 1 280px", maxWidth: "320px", minWidth: "260px" }}>
            <h3 style={{ fontSize: "12px", fontWeight: 500, color: palette.dimText, letterSpacing: "1px", textTransform: "uppercase", marginBottom: "18px" }}>
              Distribution
            </h3>
            <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
              <DoshaBar label="Adaptive" value={adaptive} color={palette.barAdaptive} />
              <DoshaBar label="Performance" value={performance} color={palette.barPerformance} />
              <DoshaBar label="Conservation" value={conservation} color={palette.barConservation} />
            </div>
          </div>

          {/* Column 2: Strengths */}
          <div style={{ flex: "1 1 260px", maxWidth: "300px", minWidth: "240px" }}>
            <div style={cardStyle}>
              <h3 style={cardTitleStyle}>Your Strengths</h3>
              {osResult.os_details.strengths.map((s, i) => (
                <div key={i} style={bulletRowStyle}>
                  <span style={{ color: palette.accent, marginRight: "12px", marginTop: "2px" }}>&bull;</span>
                  <span style={bulletTextStyle}>{s}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Column 3: Patterns to Watch */}
          <div style={{ flex: "1 1 260px", maxWidth: "300px", minWidth: "240px" }}>
            <div style={cardStyle}>
              <h3 style={cardTitleStyle}>Patterns to Watch</h3>
              {osResult.os_details.patterns_to_watch.map((p, i) => (
                <div key={i} style={bulletRowStyle}>
                  <span style={{ color: palette.accent, marginRight: "12px", marginTop: "2px" }}>&bull;</span>
                  <span style={bulletTextStyle}>{p}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Footer text + CTA — centered */}
        <p style={{ fontSize: "16px", color: palette.fg, textAlign: "center", marginBottom: "10px" }}>
          This is a good picture to start with.
        </p>
        <p style={{ fontSize: "14px", color: palette.dimText, textAlign: "center", marginBottom: "36px" }}>
          Sakhi will continue learning as you talk.
        </p>

        <div style={{ display: "flex", justifyContent: "center", padding: "0 0 40px" }}>
          <button style={primaryCTAStyle} onClick={onStartConversation}>
            Start a conversation
          </button>
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// DOSHA BAR COMPONENT
// =============================================================================

function DoshaBar({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
      <span style={{ fontSize: "13px", color: palette.mutedDark, width: "95px" }}>{label}</span>
      <div style={{ flex: 1, height: "10px", backgroundColor: palette.cardBg, borderRadius: "5px", overflow: "hidden" }}>
        <div style={{ width: `${value}%`, height: "100%", backgroundColor: color, borderRadius: "5px", transition: "width 600ms ease" }} />
      </div>
      <span style={{ fontSize: "13px", color: palette.mutedDark, width: "44px", textAlign: "right" }}>{value}%</span>
    </div>
  );
}

// =============================================================================
// MAIN ONBOARDING COMPONENT
// =============================================================================

export default function OnboardingPage() {
  return (
    <Suspense fallback={null}>
      <OnboardingContent />
    </Suspense>
  );
}

function OnboardingContent() {
  const router = useRouter();
  const search = useSearchParams();
  const user = search?.get("user");

  const [currentScreen, setCurrentScreen] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string | string[]>>({});
  const [refineMode, setRefineMode] = useState(false);
  const [refineScreen, setRefineScreen] = useState(0);
  const [hoveredOption, setHoveredOption] = useState<string | null>(null);

  // API state
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [osResult, setOsResult] = useState<OnboardingResponse | null>(null);
  const [phase1Submitted, setPhase1Submitted] = useState(false);
  const [phase2aSubmitted, setPhase2aSubmitted] = useState(false);
  const [phase2bSubmitted, setPhase2bSubmitted] = useState(false);

  const handleSignOut = useCallback(async () => {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.replace("/experience" as Route);
  }, [router]);

  // Submit to API
  const submitOnboarding = useCallback(
    async (phase: "phase1" | "phase2a" | "phase2b", responses: Record<string, string | string[]>) => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch("/api/onboarding/submit", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            phase,
            responses,
            completed_at: new Date().toISOString(),
          }),
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.error || `API error: ${res.status}`);
        }

        const data: OnboardingResponse = await res.json();
        setOsResult(data);
        return data;
      } catch (err) {
        const message = err instanceof Error ? err.message : "Unknown error";
        setError(message);
        console.error("Onboarding submission failed:", err);
        return null;
      } finally {
        setLoading(false);
      }
    },
    []
  );

  // Auto-submit when entering mirror/OS screens
  const screens = refineMode ? REFINE_SCREENS : SCREENS;
  const screenIndex = refineMode ? refineScreen : currentScreen;
  const screen = screens[screenIndex];

  useEffect(() => {
    if (screen.isMirror && !phase1Submitted && !loading) {
      setPhase1Submitted(true);
      submitOnboarding("phase1", answers);
    }
  }, [screen.isMirror, phase1Submitted, loading, answers, submitOnboarding]);

  useEffect(() => {
    if (screen.isIntermediateOS && !phase2aSubmitted && !loading) {
      setPhase2aSubmitted(true);
      submitOnboarding("phase2a", answers);
    }
  }, [screen.isIntermediateOS, phase2aSubmitted, loading, answers, submitOnboarding]);

  useEffect(() => {
    if (screen.isFinalOS && !phase2bSubmitted && !loading) {
      setPhase2bSubmitted(true);
      submitOnboarding("phase2b", answers);
    }
  }, [screen.isFinalOS, phase2bSubmitted, loading, answers, submitOnboarding]);

  const isFirstScreen = refineMode ? refineScreen === 0 : currentScreen === 0;
  const isLastRefineScreen = refineMode && refineScreen === REFINE_SCREENS.length - 1;

  const canProceed = useMemo(() => {
    if (screen.questions.length === 0) return true;
    return screen.questions.every((q) => {
      if (q.optional) return true;
      const answer = answers[q.id];
      if (q.type === "multi") {
        return Array.isArray(answer) && answer.length > 0;
      }
      return answer && answer.length > 0;
    });
  }, [screen, answers]);

  const handleAnswer = useCallback((questionId: string, value: string, isMulti: boolean) => {
    setAnswers((prev) => {
      if (isMulti) {
        const current = (prev[questionId] as string[]) || [];
        const updated = current.includes(value)
          ? current.filter((v) => v !== value)
          : [...current, value];
        return { ...prev, [questionId]: updated };
      }
      return { ...prev, [questionId]: value };
    });
  }, []);

  const handleTextAnswer = useCallback((questionId: string, value: string) => {
    setAnswers((prev) => ({ ...prev, [questionId]: value }));
  }, []);

  const handleNext = useCallback(() => {
    if (refineMode) {
      if (refineScreen >= REFINE_SCREENS.length - 1) {
        const nextPath = user
          ? `/experience/converse?user=${encodeURIComponent(user)}`
          : "/experience/converse";
        router.replace(nextPath as Route);
      } else {
        setRefineScreen((prev) => prev + 1);
      }
    } else {
      setCurrentScreen((prev) => prev + 1);
    }
  }, [refineMode, refineScreen, router, user]);

  const handleBack = useCallback(() => {
    if (refineMode) {
      if (refineScreen > 0) {
        setRefineScreen((prev) => prev - 1);
      } else {
        setRefineMode(false);
      }
    } else {
      if (currentScreen > 0) {
        setCurrentScreen((prev) => prev - 1);
      }
    }
  }, [refineMode, refineScreen, currentScreen]);

  const handleSkip = useCallback(() => {
    if (refineMode) {
      if (refineScreen >= REFINE_SCREENS.length - 1) {
        const nextPath = user
          ? `/experience/converse?user=${encodeURIComponent(user)}`
          : "/experience/converse";
        router.replace(nextPath as Route);
      } else {
        setRefineScreen((prev) => prev + 1);
      }
    } else {
      setCurrentScreen((prev) => prev + 1);
    }
  }, [refineMode, refineScreen, router, user]);

  const handleStartConversation = useCallback(() => {
    // Save preferred name if entered (fire and forget)
    const name = answers.preferred_name;
    if (typeof name === "string" && name.trim()) {
      fetch("/api/auth/update-name", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: name.trim() }),
      }).catch(() => {}); // best effort — don't block navigation
    }
    const nextPath = user
      ? `/experience/converse?user=${encodeURIComponent(user)}`
      : "/experience/converse";
    router.replace(nextPath as Route);
  }, [router, user, answers]);

  const handleRefine = useCallback(() => {
    setRefineMode(true);
    setRefineScreen(0);
  }, []);

  const handleRefineMore = useCallback(() => {
    setRefineScreen((prev) => prev + 1);
  }, []);

  const handleMirrorContinue = useCallback(() => {
    setCurrentScreen((prev) => prev + 1);
  }, []);

  // =========================================================================
  // SPECIAL SCREEN RENDERS
  // =========================================================================

  if (screen.isMirror) {
    return (
      <MirrorScreen
        osResult={osResult}
        loading={loading}
        error={error}
        onContinue={handleMirrorContinue}
      />
    );
  }

  if (screen.isFollowUp) {
    return (
      <FollowUpScreen
        onStartConversation={handleStartConversation}
        onRefine={handleRefine}
      />
    );
  }

  if (screen.isIntermediateOS) {
    return (
      <IntermediateOSScreen
        osResult={osResult}
        loading={loading}
        error={error}
        onRefineMore={handleRefineMore}
        onStartConversation={handleStartConversation}
      />
    );
  }

  if (screen.isFinalOS) {
    return (
      <FinalOSScreen
        osResult={osResult}
        loading={loading}
        error={error}
        onStartConversation={handleStartConversation}
      />
    );
  }

  // =========================================================================
  // REGULAR SCREEN RENDER (questions, transitions, calibrations)
  // =========================================================================

  return (
    <div style={fullScreenStyle}>
      {/* Sign out — top right */}
      <button
        onClick={handleSignOut}
        style={{
          position: "absolute",
          top: "16px",
          right: "24px",
          background: "none",
          border: "none",
          color: palette.dimText,
          fontSize: "12px",
          cursor: "pointer",
          zIndex: 5,
          fontFamily,
        }}
      >
        Sign out
      </button>

      {/* Progress bar (refine mode only) */}
      {refineMode && (
        <div style={{ height: "4px", backgroundColor: palette.border, width: "100%" }}>
          <div style={{ height: "100%", backgroundColor: palette.accent, width: `${((refineScreen + 1) / REFINE_SCREENS.length) * 100}%`, transition: "width 300ms ease" }} />
        </div>
      )}

      {/* Centered content column — everything lives inside this */}
      <div style={{
        flex: 1,
        display: "flex",
        flexDirection: "column",
        maxWidth: "560px",
        width: "100%",
        margin: "0 auto",
        padding: "0 28px",
      }}>
        {/* Sakhi header for transition/calibration (non-refine) */}
        {(screen.isTransition || screen.isCalibration) && !refineMode && (
          <div style={{ paddingTop: "24px", textAlign: "center", flexShrink: 0 }}>
            <span style={{ fontSize: "16px", fontWeight: 500, color: palette.mutedDark, letterSpacing: "1px" }}>Sakhi</span>
          </div>
        )}

        {/* Back button (refine mode) */}
        {refineMode && refineScreen > 0 && (
          <div style={{ paddingTop: "16px", flexShrink: 0 }}>
            <button
              style={{ padding: "12px 0", background: "none", border: "none", color: palette.mutedDark, fontSize: "14px", cursor: "pointer", fontFamily }}
              onClick={handleBack}
            >
              &larr; Back
            </button>
          </div>
        )}

        {/* Content area */}
        <div style={{
          flex: 1,
          overflowY: "auto",
          display: "flex",
          flexDirection: "column",
          justifyContent: screen.id === "framing" || screen.isTransition ? "center" : "flex-start",
          paddingTop: screen.isCalibration ? "48px" : screen.id === "framing" || screen.isTransition ? "0" : "28px",
        }}>
          {/* Header */}
          <div style={{
            marginBottom: screen.isTransition ? "0" : "44px",
            textAlign: "center",
            ...(screen.isCalibration ? { marginBottom: "28px" } : {}),
          }}>
            <h1 style={{
              fontSize: screen.isTransition ? "26px" : screen.isCalibration ? "24px" : "28px",
              fontWeight: screen.isTransition || screen.isCalibration ? 400 : 600,
              color: palette.fg,
              textAlign: "center",
              lineHeight: screen.isTransition ? "36px" : screen.isCalibration ? "34px" : "38px",
              marginBottom: screen.isTransition ? "36px" : screen.isCalibration ? "0" : "14px",
              letterSpacing: "-0.5px",
            }}>
              {screen.title}
            </h1>
            {screen.subtitle && (
              <p style={{ fontSize: "16px", color: palette.muted, textAlign: "center", lineHeight: "24px" }}>
                {screen.subtitle}
              </p>
            )}
            {screen.body && (
              <p style={{ fontSize: "16px", color: palette.muted, textAlign: "center", lineHeight: "28px", marginTop: "8px", whiteSpace: "pre-line" }}>
                {screen.body}
              </p>
            )}
          </div>

          {/* Questions */}
          {screen.questions.map((question) => (
            <div key={question.id} style={{ marginBottom: "36px" }}>
              {question.text && (
                <p style={{ fontSize: "16px", fontWeight: 500, color: palette.fg, marginBottom: "18px" }}>
                  {question.text}
                </p>
              )}

              {question.type === "text" ? (
                <input
                  type="text"
                  style={textInputStyle}
                  placeholder={question.placeholder}
                  value={(answers[question.id] as string) || ""}
                  onChange={(e) => handleTextAnswer(question.id, e.target.value)}
                  onFocus={(e) => { e.target.style.borderColor = palette.accent; }}
                  onBlur={(e) => { e.target.style.borderColor = palette.border; }}
                />
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                  {question.options?.map((option) => {
                    const isMulti = question.type === "multi";
                    const currentAnswer = answers[question.id];
                    const isSelected = isMulti
                      ? ((currentAnswer as string[]) || []).includes(option.value)
                      : currentAnswer === option.value;
                    const isHovered = hoveredOption === `${question.id}-${option.value}`;

                    return (
                      <div
                        key={option.value}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          backgroundColor: isSelected ? "rgba(99, 102, 241, 0.1)" : isHovered ? palette.cardBg : "transparent",
                          border: `1px solid ${isSelected ? palette.accent : palette.border}`,
                          borderRadius: "14px",
                          padding: "18px",
                          gap: "16px",
                          cursor: "pointer",
                          transition: "all 150ms ease",
                          minHeight: "56px",
                        }}
                        onClick={() => handleAnswer(question.id, option.value, isMulti)}
                        onMouseEnter={() => setHoveredOption(`${question.id}-${option.value}`)}
                        onMouseLeave={() => setHoveredOption(null)}
                      >
                        {/* Radio / Checkbox */}
                        <div style={{
                          width: "22px",
                          height: "22px",
                          borderRadius: isMulti ? "5px" : "11px",
                          border: `2px solid ${isSelected ? palette.accent : palette.dimText}`,
                          backgroundColor: isSelected ? palette.accent : "transparent",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          flexShrink: 0,
                        }}>
                          {isSelected && (
                            <div style={{
                              width: isMulti ? "11px" : "10px",
                              height: isMulti ? "11px" : "10px",
                              backgroundColor: "#fff",
                              borderRadius: isMulti ? "2px" : "5px",
                            }} />
                          )}
                        </div>
                        <span style={{ fontSize: "15px", color: isSelected ? palette.fg : palette.muted, flex: 1 }}>
                          {option.label}
                        </span>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          ))}

          {/* Inline CTA for centered screens (framing / transition) — button right below content */}
          {(screen.id === "framing" || screen.isTransition) && (
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "14px", marginTop: "36px" }}>
              {screen.skipAllowed && screen.isTransition && (
                <button
                  style={{ padding: "10px 28px", background: "none", border: "none", color: palette.dimText, fontSize: "14px", cursor: "pointer", fontFamily }}
                  onClick={handleStartConversation}
                >
                  Skip for now
                </button>
              )}
              {screen.isTransition ? (
                <button
                  style={primaryCTAStyle}
                  onClick={isLastRefineScreen ? handleStartConversation : handleNext}
                >
                  {isLastRefineScreen
                    ? "Start a conversation"
                    : refineMode && refineScreen === 0
                      ? "Let\u2019s continue"
                      : "Continue"}
                </button>
              ) : (
                <button
                  style={{
                    ...primaryCTAStyle,
                    ...(!canProceed ? { backgroundColor: "rgba(99, 102, 241, 0.15)", cursor: "not-allowed" } : {}),
                  }}
                  onClick={handleNext}
                  disabled={!canProceed && screen.questions.length > 0}
                >
                  <span style={!canProceed ? { color: palette.mutedDark } : {}}>
                    Continue
                  </span>
                </button>
              )}
            </div>
          )}
        </div>

        {/* Footer — only for question screens (calibration, refine) */}
        {screen.id !== "framing" && !screen.isTransition && (
        <div style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: "14px",
          padding: "24px 0 48px",
          flexShrink: 0,
        }}>
          {/* Back link for non-first screens */}
          {!screen.isCalibration && !isFirstScreen && (
            <button
              style={{ padding: "10px 16px", background: "none", border: "none", color: palette.mutedDark, fontSize: "14px", cursor: "pointer", fontFamily }}
              onClick={handleBack}
            >
              &larr; Back
            </button>
          )}

          {/* Skip link */}
          {screen.skipAllowed && screen.isCalibration && (
            <button
              style={{ padding: "10px 28px", background: "none", border: "none", color: palette.dimText, fontSize: "14px", cursor: "pointer", fontFamily }}
              onClick={handleSkip}
            >
              Skip
            </button>
          )}

          {/* Primary action */}
          <button
            style={{
              ...primaryCTAStyle,
              ...((!canProceed && !screen.skipAllowed) ? { backgroundColor: "rgba(99, 102, 241, 0.15)", cursor: "not-allowed" } : {}),
            }}
            onClick={handleNext}
            disabled={!canProceed && !screen.skipAllowed && screen.questions.length > 0}
          >
            <span style={(!canProceed && !screen.skipAllowed) ? { color: palette.mutedDark } : {}}>
              Continue
            </span>
          </button>
        </div>
        )}
      </div>
    </div>
  );
}

// =============================================================================
// SHARED STYLES
// =============================================================================

const fullScreenStyle: React.CSSProperties = {
  height: "100vh",
  background: palette.bg,
  color: palette.fg,
  fontFamily,
  display: "flex",
  flexDirection: "column",
  position: "relative",
  overflow: "hidden",
};

const centerContentStyle: React.CSSProperties = {
  flex: 1,
  display: "flex",
  flexDirection: "column",
  alignItems: "center",
  justifyContent: "center",
  padding: "28px",
};

const primaryCTAStyle: React.CSSProperties = {
  backgroundColor: palette.accent,
  padding: "18px 52px",
  borderRadius: "14px",
  border: "none",
  color: "#fff",
  fontSize: "16px",
  fontWeight: 500,
  cursor: "pointer",
  minWidth: "220px",
  minHeight: "56px",
  fontFamily,
  width: "100%",
  maxWidth: "400px",
};

const secondaryButtonStyle: React.CSSProperties = {
  backgroundColor: palette.border,
  padding: "14px 28px",
  borderRadius: "12px",
  border: "none",
  color: palette.muted,
  fontSize: "14px",
  fontWeight: 500,
  cursor: "pointer",
  fontFamily,
};

const textInputStyle: React.CSSProperties = {
  backgroundColor: palette.cardBg,
  border: `1px solid ${palette.border}`,
  borderRadius: "14px",
  padding: "18px",
  fontSize: "15px",
  color: palette.fg,
  width: "100%",
  outline: "none",
  transition: "border-color 150ms ease",
  minHeight: "56px",
  fontFamily,
  boxSizing: "border-box",
};

const osHeaderLabelStyle: React.CSSProperties = {
  fontSize: "12px",
  fontWeight: 500,
  color: palette.dimText,
  letterSpacing: "2px",
  textAlign: "center",
  marginTop: "24px",
  marginBottom: "28px",
};

const osTitleStyle: React.CSSProperties = {
  fontSize: "32px",
  fontWeight: 600,
  color: palette.fg,
  textAlign: "center",
  letterSpacing: "-0.5px",
  marginBottom: "10px",
};

const osSubtitleStyle: React.CSSProperties = {
  fontSize: "18px",
  fontWeight: 400,
  color: palette.accent,
  textAlign: "center",
  marginBottom: "28px",
};

const osDescriptionStyle: React.CSSProperties = {
  fontSize: "16px",
  color: palette.muted,
  textAlign: "center",
  lineHeight: "26px",
  marginBottom: "36px",
  padding: "0 12px",
};

const toggleButtonStyle: React.CSSProperties = {
  display: "block",
  margin: "0 auto",
  padding: "14px 20px",
  background: "none",
  border: "none",
  color: palette.dimText,
  fontSize: "13px",
  cursor: "pointer",
  fontFamily,
};

const cardStyle: React.CSSProperties = {
  backgroundColor: palette.cardBg,
  borderRadius: "18px",
  padding: "22px",
  marginBottom: "18px",
  border: `1px solid ${palette.border}`,
};

const cardTitleStyle: React.CSSProperties = {
  fontSize: "15px",
  fontWeight: 600,
  color: palette.fg,
  marginBottom: "18px",
};

const bulletRowStyle: React.CSSProperties = {
  display: "flex",
  marginBottom: "12px",
  paddingRight: "8px",
};

const bulletTextStyle: React.CSSProperties = {
  fontSize: "14px",
  color: palette.muted,
  flex: 1,
  lineHeight: "20px",
};

const anchorLineStyle: React.CSSProperties = {
  fontSize: "13px",
  color: palette.dimText,
  textAlign: "center",
  fontStyle: "italic",
  marginTop: "12px",
  marginBottom: "28px",
};

const spinnerStyle: React.CSSProperties = {
  width: "32px",
  height: "32px",
  border: `3px solid ${palette.border}`,
  borderTopColor: palette.accent,
  borderRadius: "50%",
  animation: "spin 1s linear infinite",
};
