"use client";

import { Suspense, useState, useCallback, useMemo } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import type React from "react";
import type { Route } from "next";

export const dynamic = "force-dynamic";

const palette = {
  bg: "#0e0f12",
  fg: "#f4f4f5",
  muted: "#a1a1aa",
  accent: "#6366f1",
  accentHover: "#818cf8",
  cardBg: "#18191d",
  border: "#27272a",
  success: "#22c55e",
};

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
  reason?: string; // Why we ask this - tied to Operating System / Friction Framework
  expandable?: boolean; // Allow optional free text expansion
  expandPlaceholder?: string; // Placeholder for expansion text
}

interface Screen {
  id: string;
  title: string;
  subtitle?: string;
  intent?: string;
  questions: Question[];
}

// =============================================================================
// ONBOARDING DATA
// =============================================================================

const SCREENS: Screen[] = [
  {
    id: "framing",
    title: "Welcome to Sakhi",
    subtitle: "Before we begin, a few questions to understand you better.",
    intent: "This helps Sakhi give you relevant, personalized guidance.",
    questions: [
      {
        id: "preferred_name",
        text: "What should we call you?",
        type: "text",
        placeholder: "Name or nickname you prefer",
        reason: "So Sakhi can address you personally in conversations.",
      },
    ],
  },
  {
    id: "basics",
    title: "About You",
    subtitle: "Basic context to personalize your experience.",
    intent: "Establish life stage and environmental context.",
    questions: [
      {
        id: "location",
        text: "Where do you live?",
        type: "text",
        placeholder: "City, Country",
        reason: "Climate and seasons affect your natural rhythms and energy patterns.",
      },
      {
        id: "age_range",
        text: "Your age range:",
        type: "single",
        options: [
          { value: "18-24", label: "18–24" },
          { value: "25-34", label: "25–34" },
          { value: "35-44", label: "35–44" },
          { value: "45-54", label: "45–54" },
          { value: "55-64", label: "55–64" },
          { value: "65+", label: "65+" },
        ],
        reason: "Life stage shapes your operating rhythm and the demands you face.",
      },
    ],
  },
  {
    id: "rhythm_energy",
    title: "Rhythm & Energy",
    subtitle: "Understanding your natural patterns.",
    intent: "Understand natural clarity window, pacing tendency, and current energy state.",
    questions: [
      {
        id: "clarity_window",
        text: "When do you usually feel most clear?",
        type: "single",
        options: [
          { value: "morning", label: "Morning" },
          { value: "afternoon", label: "Afternoon" },
          { value: "evening", label: "Evening" },
          { value: "varies", label: "It varies day to day" },
        ],
        reason: "Your natural clarity window reveals your operating system's rhythm.",
        expandable: true,
        expandPlaceholder: "What does clarity feel like for you? (optional)",
      },
      {
        id: "pacing_under_demand",
        text: "When days get demanding, you usually:",
        type: "single",
        options: [
          { value: "push_harder", label: "Push harder" },
          { value: "slow_down", label: "Slow down" },
          { value: "oscillate", label: "Move between both" },
        ],
        reason: "How you respond to pressure is a core signal of your operating mode.",
        expandable: true,
        expandPlaceholder: "What does a demanding day look like for you? (optional)",
      },
      {
        id: "current_energy",
        text: "Right now, your energy feels:",
        type: "single",
        options: [
          { value: "steady", label: "Steady" },
          { value: "waves", label: "In waves" },
          { value: "drained", label: "Drained" },
          { value: "wired_tired", label: "Wired but tired" },
        ],
        reason: "Your current state helps Sakhi calibrate recommendations to where you are now.",
        expandable: true,
        expandPlaceholder: "What's contributing to this? (optional)",
      },
    ],
  },
  {
    id: "body_signals",
    title: "Body Signals & Recovery",
    subtitle: "How your body communicates with you.",
    intent: "Capture concrete stress signals and recovery pathways.",
    questions: [
      {
        id: "first_stress_signal",
        text: "When your days get very busy, what do you notice first?",
        type: "single",
        options: [
          { value: "sleep_trouble", label: "Trouble settling or sleeping" },
          { value: "irritability", label: "Irritability or impatience" },
          { value: "low_energy", label: "Low energy or heaviness" },
          { value: "depends", label: "It depends" },
        ],
        reason: "Early friction signals reveal how your system responds to overload.",
        expandable: true,
        expandPlaceholder: "How does stress show up for you? (optional)",
      },
      {
        id: "body_request",
        text: "After a few demanding days, your body usually asks for:",
        type: "single",
        options: [
          { value: "quiet_space", label: "Quiet or mental space" },
          { value: "physical_release", label: "Physical release (walk, stretch, workout)" },
          { value: "rest_food", label: "Extra rest or comforting food" },
          { value: "unsure", label: "I'm not sure" },
        ],
        reason: "Your body's requests show what restores balance in your operating system.",
        expandable: true,
        expandPlaceholder: "What does your body typically ask for? (optional)",
      },
      {
        id: "fastest_recovery",
        text: "What helps you recover fastest?",
        type: "single",
        options: [
          { value: "calm_time", label: "Calm, low-stimulus time" },
          { value: "movement", label: "Moving my body" },
          { value: "sleep_food", label: "Sleeping or eating well" },
          { value: "varies", label: "It varies" },
        ],
        reason: "Your recovery pathway guides personalized recommendations for reducing friction.",
        expandable: true,
        expandPlaceholder: "What specific activities help you recharge? (optional)",
      },
    ],
  },
  {
    id: "life_context",
    title: "Life Context",
    subtitle: "Understanding your current situation.",
    intent: "Understand constraints, role load, and decision surface.",
    questions: [
      {
        id: "active_roles",
        text: "Which roles feel most present right now?",
        type: "multi",
        options: [
          { value: "professional", label: "Professional / builder" },
          { value: "caregiver", label: "Caregiver" },
          { value: "partner_family", label: "Partner / family" },
          { value: "transition", label: "Personal transition" },
        ],
        reason: "Multiple roles create competing demands that affect your operating load.",
        expandable: true,
        expandPlaceholder: "Tell us more about what you're juggling (optional)",
      },
      {
        id: "life_phase",
        text: "This phase of life feels like:",
        type: "single",
        options: [
          { value: "building", label: "Building" },
          { value: "maintaining", label: "Maintaining" },
          { value: "reorienting", label: "Re-orienting" },
          { value: "recovering", label: "Recovering" },
        ],
        reason: "Your current phase shapes whether you need activation or conservation support.",
        expandable: true,
        expandPlaceholder: "What's shaping this phase for you? (optional)",
      },
      {
        id: "responsibility_load",
        text: "Your current responsibility load feels:",
        type: "single",
        options: [
          { value: "personal", label: "Mostly personal" },
          { value: "shared", label: "Shared" },
          { value: "carrying_others", label: "Carrying others" },
        ],
        reason: "Carrying others creates different friction patterns than personal load.",
        expandable: true,
        expandPlaceholder: "Who or what are you carrying? (optional)",
      },
    ],
  },
  {
    id: "food_body",
    title: "Food & Body Preferences",
    subtitle: "For practical, embodied recommendations.",
    intent: "Enable food and energy recommendations.",
    questions: [
      {
        id: "allergies",
        text: "Any food allergies or strong intolerances?",
        type: "text",
        placeholder: "e.g., dairy, gluten, nuts (or 'None')",
        optional: true,
        reason: "So Sakhi never suggests foods that don't work for you.",
      },
      {
        id: "foods_avoided",
        text: "Are there foods you usually avoid?",
        type: "text",
        placeholder: "e.g., red meat, sugar (or 'None')",
        optional: true,
        reason: "Respects your preferences when suggesting nourishment.",
      },
      {
        id: "appetite_pattern",
        text: "Which best describes your appetite most days?",
        type: "single",
        options: [
          { value: "light_variable", label: "Light or variable" },
          { value: "strong_regular", label: "Strong and regular" },
          { value: "slow_inconsistent", label: "Slow or inconsistent" },
        ],
        optional: true,
        reason: "Appetite patterns reflect your digestive rhythm and metabolic operating mode.",
        expandable: true,
        expandPlaceholder: "Anything about your eating patterns you'd like to share? (optional)",
      },
    ],
  },
  {
    id: "decision_making",
    title: "How You Make Tradeoffs",
    subtitle: "Understanding your decision patterns.",
    intent: "Learn how you handle tradeoffs and decisions.",
    questions: [
      {
        id: "decision_driver",
        text: "When choosing between two reasonable options, what usually tips the scale first?",
        type: "single",
        options: [
          { value: "protect_energy", label: "Protecting my energy or health" },
          { value: "people_relationships", label: "Making time for people or relationships" },
          { value: "reduce_stress", label: "Reducing stress or uncertainty" },
          { value: "make_progress", label: "Making progress or moving forward" },
          { value: "depends", label: "It depends on the situation" },
        ],
        reason: "Your decision driver shows what your system prioritizes under pressure.",
        expandable: true,
        expandPlaceholder: "Can you share a recent example? (optional)",
      },
      {
        id: "risk_behavior",
        text: "Over the past few months, you've been more likely to:",
        type: "single",
        options: [
          { value: "safer", label: "Choose the safer, predictable option" },
          { value: "calculated_risk", label: "Take a calculated risk if it supports longer-term goals" },
          { value: "balance", label: "Balance both, depending on context" },
        ],
        reason: "Risk tolerance indicates your current operating mode—conservation vs. expansion.",
        expandable: true,
        expandPlaceholder: "What's influencing how you approach risk right now? (optional)",
      },
      {
        id: "time_horizon",
        text: "Right now, most of your decisions are shaped by:",
        type: "single",
        options: [
          { value: "weeks", label: "What will help in the next few weeks" },
          { value: "year_two", label: "What will matter over the next year or two" },
          { value: "long_term", label: "A longer-term direction I'm holding in mind" },
        ],
        reason: "Your time horizon affects how Sakhi frames suggestions and tradeoffs.",
        expandable: true,
        expandPlaceholder: "What's the bigger picture you're working toward? (optional)",
      },
      {
        id: "energy_vs_outcome",
        text: "When outcomes matter but you're tired, you usually:",
        type: "single",
        options: [
          { value: "preserve_energy", label: "Choose the option that preserves energy" },
          { value: "push_through", label: "Push through to get the result" },
          { value: "case_by_case", label: "Decide case by case" },
        ],
        reason: "This reveals friction between your goals and your capacity—a key pattern.",
        expandable: true,
        expandPlaceholder: "How do you navigate this tension? (optional)",
      },
      {
        id: "flexibility_under_load",
        text: "When plans start to feel heavy or constrained, you tend to:",
        type: "single",
        options: [
          { value: "simplify", label: "Simplify and reduce commitments" },
          { value: "reorganize", label: "Reorganize and push through" },
          { value: "pause_reassess", label: "Pause and reassess before deciding" },
        ],
        reason: "How you adapt under load shows your natural friction response pattern.",
        expandable: true,
        expandPlaceholder: "What do you do when things feel too heavy? (optional)",
      },
    ],
  },
  {
    id: "closure",
    title: "You're all set",
    subtitle: "Sakhi will learn and adapt as you share more over time.",
    intent: "These answers describe current tendencies, not identity. They are soft constraints and will be updated by observed behavior.",
    questions: [],
  },
];

// =============================================================================
// COMPONENT
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
const [isSubmitting, setIsSubmitting] = useState(false);
const [submitError, setSubmitError] = useState<string | null>(null);
const [hoveredOption, setHoveredOption] = useState<string | null>(null);
const [showLocationSuggestions, setShowLocationSuggestions] = useState(false);
const locationSuggestions = useMemo(
  () => [
    "Bengaluru, India",
    "Delhi, India",
    "Mumbai, India",
    "Hyderabad, India",
    "Chennai, India",
    "Pune, India",
    "New York, United States",
    "San Francisco, United States",
    "Los Angeles, United States",
    "Seattle, United States",
    "Chicago, United States",
    "Austin, United States",
    "London, United Kingdom",
    "Manchester, United Kingdom",
    "Birmingham, United Kingdom",
    "Edinburgh, United Kingdom",
    "Toronto, Canada",
    "Vancouver, Canada",
    "Montreal, Canada",
    "Sydney, Australia",
    "Melbourne, Australia",
    "Singapore, Singapore",
    "Berlin, Germany",
    "Munich, Germany",
    "Paris, France",
    "Madrid, Spain",
    "Barcelona, Spain",
    "São Paulo, Brazil",
    "Rio de Janeiro, Brazil",
    "Mexico City, Mexico",
    "Guadalajara, Mexico",
    "Monterrey, Mexico",
    "Singapore, Singapore",
    "Dubai, UAE",
    "Riyadh, Saudi Arabia",
    "Doha, Qatar",
  ],
  []
);
const locationQuery = (answers["location"] as string) || "";
const filteredLocations = useMemo(() => {
  const query = locationQuery.toLowerCase().trim();
  if (query.length < 2) return [];
  return locationSuggestions
    .filter((loc) => loc.toLowerCase().includes(query))
    .slice(0, 8);
}, [locationQuery, locationSuggestions]);

  const screen = SCREENS[currentScreen];
  const isFirstScreen = currentScreen === 0;
  const isLastScreen = currentScreen === SCREENS.length - 1;
  const progress = ((currentScreen + 1) / SCREENS.length) * 100;

  // Check if current screen questions are answered (for required questions)
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

  const handleNext = useCallback(async () => {
    if (isLastScreen) {
      // Submit all answers
      setIsSubmitting(true);
      setSubmitError(null);
      try {
        const response = await fetch("/api/onboarding/complete", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            user_id: user,
            responses: answers,
            completed_at: new Date().toISOString(),
          }),
        });

        const data = await response.json();

        if (!response.ok) {
          setSubmitError(data.error || "Failed to save your profile. Please try again.");
          setIsSubmitting(false);
          return;
        }

        // Navigate to result page to show Operating System
        const resultParam = encodeURIComponent(JSON.stringify(data));
        const nextPath = user
          ? `/experience/onboarding/result?user=${encodeURIComponent(user)}&result=${resultParam}`
          : `/experience/onboarding/result?result=${resultParam}`;
        router.push(nextPath as Route);
      } catch (error) {
        console.error("Onboarding submission error:", error);
        setSubmitError("Unable to connect to server. Please check if the API is running.");
        setIsSubmitting(false);
      }
    } else {
      setCurrentScreen((prev) => prev + 1);
    }
  }, [isLastScreen, answers, user, router]);

  const handleBack = useCallback(() => {
    if (currentScreen > 0) {
      setCurrentScreen((prev) => prev - 1);
    }
  }, [currentScreen]);

  const handleSkip = useCallback(() => {
    setCurrentScreen((prev) => prev + 1);
  }, []);

  // Styles
  const containerStyle: React.CSSProperties = {
    minHeight: "100vh",
    background: palette.bg,
    color: palette.fg,
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Inter, sans-serif',
    display: "flex",
    flexDirection: "column",
  };

  const progressBarContainerStyle: React.CSSProperties = {
    position: "fixed",
    top: 0,
    left: 0,
    right: 0,
    height: "3px",
    background: palette.border,
    zIndex: 100,
  };

  const progressBarStyle: React.CSSProperties = {
    height: "100%",
    background: palette.accent,
    width: `${progress}%`,
    transition: "width 300ms ease",
  };

  const mainStyle: React.CSSProperties = {
    flex: 1,
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    padding: "80px 24px 120px",
    maxWidth: "640px",
    margin: "0 auto",
    width: "100%",
  };

  const headerStyle: React.CSSProperties = {
    textAlign: "center",
    marginBottom: "48px",
  };

  const titleStyle: React.CSSProperties = {
    fontSize: "28px",
    fontWeight: 600,
    marginBottom: "12px",
    letterSpacing: "-0.02em",
  };

  const subtitleStyle: React.CSSProperties = {
    fontSize: "16px",
    color: palette.muted,
    lineHeight: 1.5,
  };

  const questionsContainerStyle: React.CSSProperties = {
    width: "100%",
    display: "flex",
    flexDirection: "column",
    gap: "32px",
  };

  const questionStyle: React.CSSProperties = {
    display: "flex",
    flexDirection: "column",
    gap: "12px",
  };

  const questionTextStyle: React.CSSProperties = {
    fontSize: "16px",
    fontWeight: 500,
    color: palette.fg,
  };

  const optionsContainerStyle: React.CSSProperties = {
    display: "flex",
    flexDirection: "column",
    gap: "8px",
  };

  const getOptionStyle = (questionId: string, value: string, isMulti: boolean): React.CSSProperties => {
    const currentAnswer = answers[questionId];
    const isSelected = isMulti
      ? (currentAnswer as string[] || []).includes(value)
      : currentAnswer === value;
    const isHovered = hoveredOption === `${questionId}-${value}`;

    return {
      padding: "14px 18px",
      borderRadius: "10px",
      border: `1px solid ${isSelected ? palette.accent : palette.border}`,
      background: isSelected ? `${palette.accent}15` : isHovered ? palette.cardBg : "transparent",
      color: isSelected ? palette.fg : palette.muted,
      cursor: "pointer",
      transition: "all 150ms ease",
      fontSize: "15px",
      display: "flex",
      alignItems: "center",
      gap: "12px",
    };
  };

  const checkboxStyle = (checked: boolean): React.CSSProperties => ({
    width: "18px",
    height: "18px",
    borderRadius: "4px",
    border: `2px solid ${checked ? palette.accent : palette.muted}`,
    background: checked ? palette.accent : "transparent",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    flexShrink: 0,
  });

  const radioStyle = (checked: boolean): React.CSSProperties => ({
    width: "18px",
    height: "18px",
    borderRadius: "50%",
    border: `2px solid ${checked ? palette.accent : palette.muted}`,
    background: "transparent",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    flexShrink: 0,
  });

  const radioInnerStyle: React.CSSProperties = {
    width: "8px",
    height: "8px",
    borderRadius: "50%",
    background: palette.accent,
  };

  const textInputStyle: React.CSSProperties = {
    padding: "14px 18px",
    borderRadius: "10px",
    border: `1px solid ${palette.border}`,
    background: palette.cardBg,
    color: palette.fg,
    fontSize: "15px",
    width: "100%",
    outline: "none",
    transition: "border-color 150ms ease",
  };

  const footerStyle: React.CSSProperties = {
    position: "fixed",
    bottom: 0,
    left: 0,
    right: 0,
    padding: "20px 24px",
    background: `linear-gradient(transparent, ${palette.bg} 30%)`,
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    maxWidth: "640px",
    margin: "0 auto",
  };

  const buttonStyle = (primary: boolean, disabled: boolean): React.CSSProperties => ({
    padding: "12px 24px",
    borderRadius: "8px",
    border: primary ? "none" : `1px solid ${palette.border}`,
    background: primary ? (disabled ? palette.muted : palette.accent) : "transparent",
    color: primary ? "#fff" : palette.muted,
    fontSize: "14px",
    fontWeight: 500,
    cursor: disabled ? "not-allowed" : "pointer",
    opacity: disabled ? 0.6 : 1,
    transition: "all 150ms ease",
  });

  const screenCountStyle: React.CSSProperties = {
    fontSize: "13px",
    color: palette.muted,
  };

  return (
    <div style={containerStyle}>
      {/* Progress bar */}
      <div style={progressBarContainerStyle}>
        <div style={progressBarStyle} />
      </div>

      <main style={mainStyle}>
        {/* Header */}
        <header style={headerStyle}>
          <h1 style={titleStyle}>{screen.title}</h1>
          {screen.subtitle && <p style={subtitleStyle}>{screen.subtitle}</p>}
        </header>

        {/* Questions */}
        {screen.questions.length > 0 && (
          <div style={questionsContainerStyle}>
            {screen.questions.map((question) => (
              <div key={question.id} style={questionStyle}>
                <div>
                  <label style={questionTextStyle}>
                    {question.text}
                    {question.optional && (
                      <span style={{ color: palette.muted, fontWeight: 400, marginLeft: "8px" }}>
                        (optional)
                      </span>
                    )}
                  </label>
                  {question.reason && (
                    <p
                      style={{
                        fontSize: "13px",
                        color: palette.muted,
                        marginTop: "6px",
                        lineHeight: 1.4,
                        opacity: 0.8,
                      }}
                    >
                      {question.reason}
                    </p>
                  )}
                </div>

                {question.type === "text" ? (
                  <input
                    type="text"
                    style={textInputStyle}
                    placeholder={question.placeholder}
                    value={(answers[question.id] as string) || ""}
                    onChange={(e) => {
                      handleTextAnswer(question.id, e.target.value);
                      if (question.id === "location") setShowLocationSuggestions(true);
                    }}
                    onFocus={(e) => {
                      e.target.style.borderColor = palette.accent;
                      if (question.id === "location" && locationQuery.length >= 2) {
                        setShowLocationSuggestions(true);
                      }
                    }}
                    onBlur={(e) => {
                      e.target.style.borderColor = palette.border;
                      if (question.id === "location") {
                        setTimeout(() => setShowLocationSuggestions(false), 120);
                      }
                    }}
                  />
                ) : (
                  <>
                    <div style={optionsContainerStyle}>
                      {question.options?.map((option) => {
                        const isMulti = question.type === "multi";
                        const currentAnswer = answers[question.id];
                        const isSelected = isMulti
                          ? (currentAnswer as string[] || []).includes(option.value)
                          : currentAnswer === option.value;

                        return (
                          <div
                            key={option.value}
                            style={getOptionStyle(question.id, option.value, isMulti)}
                            onClick={() => handleAnswer(question.id, option.value, isMulti)}
                            onMouseEnter={() => setHoveredOption(`${question.id}-${option.value}`)}
                            onMouseLeave={() => setHoveredOption(null)}
                          >
                            {isMulti ? (
                              <div style={checkboxStyle(isSelected)}>
                                {isSelected && (
                                  <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                                    <path
                                      d="M2 6L5 9L10 3"
                                      stroke="#fff"
                                      strokeWidth="2"
                                      strokeLinecap="round"
                                      strokeLinejoin="round"
                                    />
                                  </svg>
                                )}
                              </div>
                            ) : (
                              <div style={radioStyle(isSelected)}>
                                {isSelected && <div style={radioInnerStyle} />}
                              </div>
                            )}
                            <span>{option.label}</span>
                          </div>
                        );
                      })}
                    </div>

                    {/* Expandable free text area for subjective questions */}
                    {question.expandable && (
                      <textarea
                        style={{
                          marginTop: "12px",
                          padding: "12px 14px",
                          borderRadius: "10px",
                          border: `1px solid ${palette.border}`,
                          background: palette.cardBg,
                          color: palette.fg,
                          fontSize: "14px",
                          width: "100%",
                          minHeight: "80px",
                          resize: "vertical",
                          outline: "none",
                          transition: "border-color 150ms ease",
                          fontFamily: "inherit",
                          lineHeight: 1.5,
                        }}
                        placeholder={question.expandPlaceholder || "Tell us more... (optional)"}
                        value={(answers[`${question.id}_expanded`] as string) || ""}
                        onChange={(e) => handleTextAnswer(`${question.id}_expanded`, e.target.value)}
                        onFocus={(e) => {
                          e.target.style.borderColor = palette.accent;
                        }}
                        onBlur={(e) => {
                          e.target.style.borderColor = palette.border;
                        }}
                      />
                    )}
                  </>
                )}

                {question.id === "location" && showLocationSuggestions && filteredLocations.length > 0 && (
                  <div
                    style={{
                      marginTop: "8px",
                      border: `1px solid ${palette.border}`,
                      borderRadius: "10px",
                      background: palette.cardBg,
                      overflow: "hidden",
                      boxShadow: "0 10px 30px rgba(0,0,0,0.35)",
                    }}
                  >
                    {filteredLocations.map((loc) => (
                      <button
                        key={loc}
                        type="button"
                        style={{
                          width: "100%",
                          textAlign: "left",
                          padding: "10px 12px",
                          background: "transparent",
                          border: "none",
                          color: palette.fg,
                          cursor: "pointer",
                          fontSize: "14px",
                        }}
                        onMouseDown={(e) => {
                          e.preventDefault(); // prevent blur before selection applies
                          handleTextAnswer("location", loc);
                          setShowLocationSuggestions(false);
                        }}
                      >
                        {loc}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Intent note for framing/closure screens */}
        {screen.questions.length === 0 && screen.intent && (
          <p style={{ ...subtitleStyle, marginTop: "24px", textAlign: "center", maxWidth: "480px" }}>
            {screen.intent}
          </p>
        )}

        {/* Error message */}
        {submitError && (
          <div
            style={{
              marginTop: "24px",
              padding: "16px 20px",
              background: "#ef444420",
              border: "1px solid #ef4444",
              borderRadius: "10px",
              color: "#fca5a5",
              fontSize: "14px",
              textAlign: "center",
              maxWidth: "480px",
            }}
          >
            {submitError}
          </div>
        )}
      </main>

      {/* Footer navigation */}
      <footer style={footerStyle}>
        <div>
          {!isFirstScreen && (
            <button
              style={buttonStyle(false, false)}
              onClick={handleBack}
            >
              Back
            </button>
          )}
        </div>

        <span style={screenCountStyle}>
          {currentScreen + 1} / {SCREENS.length}
        </span>

        <div style={{ display: "flex", gap: "12px" }}>
          {screen.questions.some((q) => q.optional) && !canProceed && (
            <button
              style={buttonStyle(false, false)}
              onClick={handleSkip}
            >
              Skip
            </button>
          )}
          <button
            style={buttonStyle(true, !canProceed && screen.questions.length > 0)}
            onClick={handleNext}
            disabled={!canProceed && screen.questions.length > 0}
          >
            {isSubmitting ? "Saving..." : isLastScreen ? "Begin" : "Continue"}
          </button>
        </div>
      </footer>
    </div>
  );
}
