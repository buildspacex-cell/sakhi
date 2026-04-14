import React, { useState, useMemo, useCallback, useEffect } from "react";
import {
  View,
  Text,
  ScrollView,
  TextInput,
  Pressable,
  StyleSheet,
  SafeAreaView,
  StatusBar,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
  Modal,
  Dimensions,
  Alert,
} from "react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useOnboarding, OnboardingResponse } from "../../hooks/useOnboarding";
import { supabase } from "../../lib/supabase";
import { useAuth } from "../../lib/auth/AuthContext";
import { bootstrapMobileAuthProfile } from "../../lib/auth/mobileBootstrap";

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

// =============================================================================
// ONBOARDING DATA - MAIN FLOW
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
    title: "When days get demanding, you usually…",
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
          { value: "depends", label: "I'm not sure" },
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
// REFINE FLOW - ADDITIONAL QUESTIONS
// =============================================================================

const REFINE_SCREENS: Screen[] = [
  // Phase 1: Before intermediate OS
  {
    id: "refine_intro",
    title: "A few more questions",
    body: "These help Sakhi understand you a little better.\nAnswer what feels useful, skip anything you don't want to share.",
    questions: [],
    isTransition: true,
  },
  {
    id: "current_energy",
    title: "Right now, your energy feels…",
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
    title: "After a few demanding days, your body usually asks for…",
    questions: [
      {
        id: "body_request",
        text: "",
        type: "single",
        options: [
          { value: "quiet_space", label: "Quiet or mental space" },
          { value: "physical_release", label: "Physical release (walk, stretch, workout)" },
          { value: "rest_food", label: "Extra rest or comforting food" },
          { value: "unsure", label: "I'm not sure" },
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
  // Phase 2: After intermediate OS (if they choose "Refine more")
  {
    id: "life_phase",
    title: "This phase of life feels like…",
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
    title: "Right now, most of your decisions are shaped by…",
    questions: [
      {
        id: "time_horizon",
        text: "",
        type: "single",
        options: [
          { value: "weeks", label: "What will help in the next few weeks" },
          { value: "year_two", label: "What will matter over the next year or two" },
          { value: "long_term", label: "A longer-term direction I'm holding in mind" },
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
    title: "Your current responsibility load feels…",
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
    title: "When plans start to feel heavy or constrained, you tend to…",
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
    color: "#8b5cf6",
    body: "Your capacity for creativity, flexibility, and quick thinking.\n\nHigh adaptive energy means you thrive on change, new ideas, and spontaneity.",
    accent: "When overextended: scattered attention, restlessness, anxiety.",
  },
  {
    id: 2,
    title: "Performance",
    color: "#f59e0b",
    body: "Your drive, focus, and intensity.\n\nHigh performance energy means you pursue goals with precision and don\u2019t shy away from challenge.",
    accent: "When overextended: irritability, perfectionism, burnout.",
  },
  {
    id: 3,
    title: "Conservation",
    color: "#10b981",
    body: "Your stability, patience, and endurance.\n\nHigh conservation energy means you bring grounding, loyalty, and steady follow-through.",
    accent: "When overextended: stagnation, resistance to change, heaviness.",
  },
];

const SCREEN_WIDTH = Dimensions.get("window").width;

// =============================================================================
// MIRROR SCREEN COMPONENT
// =============================================================================

interface MirrorScreenProps {
  osResult: OnboardingResponse | null;
  loading: boolean;
  error: string | null;
  onContinue: () => void;
}

function MirrorScreen({ osResult, loading, error, onContinue }: MirrorScreenProps) {
  const [showOSModal, setShowOSModal] = useState(false);
  const [osModalCard, setOsModalCard] = useState(0);

  const handleModalScroll = useCallback((event: any) => {
    const offsetX = event.nativeEvent.contentOffset.x;
    const index = Math.round(offsetX / SCREEN_WIDTH);
    setOsModalCard(index);
  }, []);

  const isLastOSCard = osModalCard === OS_FRAMEWORK_CARDS.length - 1;

  // Show loading state while API is being called
  if (loading) {
    return (
      <SafeAreaView style={mirrorStyles.container}>
        <StatusBar barStyle="light-content" />
        <View style={mirrorStyles.loadingContainer}>
          <ActivityIndicator size="large" color="#6366f1" />
          <Text style={mirrorStyles.loadingText}>Analyzing your responses...</Text>
        </View>
      </SafeAreaView>
    );
  }

  // Show error state if API call failed
  if (error || !osResult) {
    return (
      <SafeAreaView style={mirrorStyles.container}>
        <StatusBar barStyle="light-content" />
        <View style={mirrorStyles.loadingContainer}>
          <Text style={mirrorStyles.errorText}>
            {error || "Something went wrong. Please try again."}
          </Text>
          <Pressable style={mirrorStyles.retryButton} onPress={onContinue}>
            <Text style={mirrorStyles.retryButtonText}>Continue anyway</Text>
          </Pressable>
        </View>
      </SafeAreaView>
    );
  }

  // Map API response to display format
  const displayResult = {
    title: osResult.operating_system,
    subtitle: osResult.os_label,
    description: osResult.os_details.description,
    adaptive: Math.round(osResult.dosha_baseline.vata * 100),
    performance: Math.round(osResult.dosha_baseline.pitta * 100),
    conservation: Math.round(osResult.dosha_baseline.kapha * 100),
    strengths: osResult.os_details.strengths,
    patterns: osResult.os_details.patterns_to_watch,
  };

  return (
    <SafeAreaView style={mirrorStyles.container}>
      <StatusBar barStyle="light-content" />
      <ScrollView
        style={mirrorStyles.scrollView}
        contentContainerStyle={mirrorStyles.content}
        showsVerticalScrollIndicator={false}
      >
        {/* Header */}
        <Text style={mirrorStyles.header}>YOUR OPERATING SYSTEM</Text>

        {/* Primary Title */}
        <Text style={mirrorStyles.primaryTitle}>{displayResult.title}</Text>

        {/* Subtitle */}
        <Text style={mirrorStyles.subtitle}>{displayResult.subtitle}</Text>

        {/* Description */}
        <Text style={mirrorStyles.description}>{displayResult.description}</Text>

        {/* Distribution Bars */}
        <View style={mirrorStyles.barsContainer}>
          <View style={mirrorStyles.barRow}>
            <Text style={mirrorStyles.barLabel}>Adaptive</Text>
            <View style={mirrorStyles.barTrack}>
              <View style={[mirrorStyles.barFill, mirrorStyles.barAdaptive, { width: `${displayResult.adaptive}%` }]} />
            </View>
            <Text style={mirrorStyles.barValue}>{displayResult.adaptive}%</Text>
          </View>
          <View style={mirrorStyles.barRow}>
            <Text style={mirrorStyles.barLabel}>Performance</Text>
            <View style={mirrorStyles.barTrack}>
              <View style={[mirrorStyles.barFill, mirrorStyles.barPerformance, { width: `${displayResult.performance}%` }]} />
            </View>
            <Text style={mirrorStyles.barValue}>{displayResult.performance}%</Text>
          </View>
          <View style={mirrorStyles.barRow}>
            <Text style={mirrorStyles.barLabel}>Conservation</Text>
            <View style={mirrorStyles.barTrack}>
              <View style={[mirrorStyles.barFill, mirrorStyles.barConservation, { width: `${displayResult.conservation}%` }]} />
            </View>
            <Text style={mirrorStyles.barValue}>{displayResult.conservation}%</Text>
          </View>
        </View>

        {/* About your OS link */}
        <Pressable
          style={mirrorStyles.toggleButton}
          onPress={() => { setShowOSModal(true); setOsModalCard(0); }}
        >
          <Text style={[mirrorStyles.toggleText, { color: "#6366f1", textDecorationLine: "underline" }]}>
            About your Personal OS
          </Text>
        </Pressable>

        {/* Soft Anchor Line */}
        <Text style={mirrorStyles.anchorLine}>
          This is a starting tendency, not a fixed identity.
        </Text>
      </ScrollView>

      {/* CTA */}
      <View style={mirrorStyles.footer}>
        <Pressable style={mirrorStyles.ctaButton} onPress={onContinue}>
          <Text style={mirrorStyles.ctaText}>Continue</Text>
        </Pressable>
      </View>

      {/* OS Framework Modal */}
      <Modal
        visible={showOSModal}
        animationType="fade"
        transparent
        onRequestClose={() => setShowOSModal(false)}
      >
        <View style={osModalStyles.overlay}>
          <SafeAreaView style={osModalStyles.container}>
            {/* Close button */}
            <Pressable
              style={osModalStyles.closeButton}
              onPress={() => setShowOSModal(false)}
            >
              <Text style={osModalStyles.closeText}>{"\u2715"}</Text>
            </Pressable>

            {/* Swipeable cards */}
            <View style={osModalStyles.cardsWrapper}>
              <ScrollView
                horizontal
                pagingEnabled
                showsHorizontalScrollIndicator={false}
                onMomentumScrollEnd={handleModalScroll}
                decelerationRate="fast"
              >
                {OS_FRAMEWORK_CARDS.map((card) => (
                  <View key={card.id} style={osModalStyles.cardOuter}>
                    <View style={osModalStyles.cardInner}>
                      <View style={[osModalStyles.colorBar, { backgroundColor: card.color }]} />
                      <Text style={osModalStyles.cardTitle}>{card.title}</Text>
                      <Text style={osModalStyles.cardBody}>{card.body}</Text>
                      <Text style={osModalStyles.cardAccent}>{card.accent}</Text>
                    </View>
                  </View>
                ))}
              </ScrollView>
            </View>

            {/* Pagination dots */}
            <View style={osModalStyles.pagination}>
              {OS_FRAMEWORK_CARDS.map((_, index) => (
                <View
                  key={index}
                  style={[
                    osModalStyles.dot,
                    osModalCard === index && osModalStyles.dotActive,
                  ]}
                />
              ))}
            </View>

            {/* Got it button */}
            <Pressable
              style={[
                osModalStyles.gotItButton,
                !isLastOSCard && osModalStyles.gotItButtonDisabled,
              ]}
              onPress={() => setShowOSModal(false)}
              disabled={!isLastOSCard}
            >
              <Text
                style={[
                  osModalStyles.gotItText,
                  !isLastOSCard && osModalStyles.gotItTextDisabled,
                ]}
              >
                {isLastOSCard ? "Got it" : "Swipe to continue"}
              </Text>
            </Pressable>
          </SafeAreaView>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

// =============================================================================
// MIRROR STYLES
// =============================================================================

const mirrorStyles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#0a0a0a",
  },
  scrollView: {
    flex: 1,
  },
  content: {
    padding: 28,
    paddingBottom: 130,
  },
  header: {
    fontSize: 12,
    fontWeight: "500",
    color: "#52525b",
    letterSpacing: 2,
    textAlign: "center",
    marginTop: 24,
    marginBottom: 28,
  },
  primaryTitle: {
    fontSize: 32,
    fontWeight: "600",
    color: "#f4f4f5",
    textAlign: "center",
    letterSpacing: -0.5,
    marginBottom: 10,
  },
  subtitle: {
    fontSize: 18,
    fontWeight: "400",
    color: "#6366f1",
    textAlign: "center",
    marginBottom: 28,
  },
  description: {
    fontSize: 16,
    color: "#a1a1aa",
    textAlign: "center",
    lineHeight: 26,
    marginBottom: 36,
    paddingHorizontal: 12,
  },
  barsContainer: {
    gap: 18,
    marginBottom: 28,
  },
  barRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 14,
  },
  barLabel: {
    fontSize: 13,
    color: "#71717a",
    width: 95,
  },
  barTrack: {
    flex: 1,
    height: 10,
    backgroundColor: "#18191d",
    borderRadius: 5,
    overflow: "hidden",
  },
  barFill: {
    height: "100%",
    borderRadius: 5,
  },
  barAdaptive: {
    backgroundColor: "#8b5cf6",
  },
  barPerformance: {
    backgroundColor: "#f59e0b",
  },
  barConservation: {
    backgroundColor: "#10b981",
  },
  barValue: {
    fontSize: 13,
    color: "#71717a",
    width: 44,
    textAlign: "right",
  },
  toggleButton: {
    alignSelf: "center",
    paddingVertical: 14,
    paddingHorizontal: 20,
    marginBottom: 24,
    minHeight: 48,
    justifyContent: "center",
  },
  toggleText: {
    fontSize: 13,
    color: "#52525b",
  },
  card: {
    backgroundColor: "#18191d",
    borderRadius: 18,
    padding: 22,
    marginBottom: 18,
    borderWidth: 1,
    borderColor: "#27272a",
  },
  cardTitle: {
    fontSize: 15,
    fontWeight: "600",
    color: "#f4f4f5",
    marginBottom: 18,
  },
  cardTitleWarning: {
    fontSize: 15,
    fontWeight: "600",
    color: "#f4f4f5",
    marginBottom: 18,
  },
  bulletRow: {
    flexDirection: "row",
    marginBottom: 12,
    paddingRight: 8,
  },
  bullet: {
    fontSize: 14,
    color: "#6366f1",
    marginRight: 12,
    marginTop: 2,
  },
  bulletText: {
    fontSize: 14,
    color: "#a1a1aa",
    flex: 1,
    lineHeight: 20,
  },
  anchorLine: {
    fontSize: 13,
    color: "#52525b",
    textAlign: "center",
    fontStyle: "italic",
    marginTop: 12,
    marginBottom: 28,
  },
  footer: {
    padding: 24,
    paddingBottom: 40,
    backgroundColor: "#0a0a0a",
  },
  ctaButton: {
    backgroundColor: "#6366f1",
    paddingVertical: 18,
    borderRadius: 14,
    alignItems: "center",
    minHeight: 56,
    justifyContent: "center",
  },
  ctaText: {
    fontSize: 16,
    fontWeight: "500",
    color: "#fff",
  },
  loadingContainer: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    padding: 28,
  },
  loadingText: {
    fontSize: 16,
    color: "#a1a1aa",
    marginTop: 16,
    textAlign: "center",
  },
  errorText: {
    fontSize: 16,
    color: "#ef4444",
    textAlign: "center",
    marginBottom: 24,
    lineHeight: 24,
  },
  retryButton: {
    backgroundColor: "#27272a",
    paddingVertical: 14,
    paddingHorizontal: 28,
    borderRadius: 12,
    minHeight: 48,
    justifyContent: "center",
  },
  retryButtonText: {
    fontSize: 14,
    fontWeight: "500",
    color: "#a1a1aa",
  },
});

// =============================================================================
// OS FRAMEWORK MODAL STYLES
// =============================================================================

const osModalStyles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: "rgba(0, 0, 0, 0.96)",
  },
  container: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
  },
  closeButton: {
    position: "absolute",
    top: 16,
    right: 16,
    zIndex: 10,
    width: 48,
    height: 48,
    alignItems: "center",
    justifyContent: "center",
  },
  closeText: {
    fontSize: 20,
    color: "#52525b",
  },
  cardsWrapper: {
    flex: 1,
    justifyContent: "center",
  },
  cardOuter: {
    width: SCREEN_WIDTH,
    justifyContent: "center",
    alignItems: "center",
    paddingHorizontal: 36,
  },
  cardInner: {
    alignItems: "center",
    paddingVertical: 48,
    maxWidth: 560,
  },
  colorBar: {
    width: 48,
    height: 6,
    borderRadius: 3,
    marginBottom: 28,
  },
  cardTitle: {
    fontSize: 26,
    fontWeight: "500",
    color: "#ffffff",
    textAlign: "center",
    lineHeight: 36,
    marginBottom: 28,
    letterSpacing: -0.5,
  },
  cardBody: {
    fontSize: 16,
    color: "#a1a1aa",
    textAlign: "center",
    lineHeight: 26,
    marginBottom: 36,
  },
  cardAccent: {
    fontSize: 14,
    color: "#71717a",
    textAlign: "center",
    fontStyle: "italic",
    lineHeight: 22,
  },
  pagination: {
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
    gap: 10,
    marginBottom: 32,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: "#27272a",
  },
  dotActive: {
    backgroundColor: "#6366f1",
    width: 28,
  },
  gotItButton: {
    backgroundColor: "#18191d",
    paddingVertical: 18,
    paddingHorizontal: 48,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: "#27272a",
    minWidth: 220,
    alignItems: "center",
    marginBottom: 40,
  },
  gotItButtonDisabled: {
    backgroundColor: "transparent",
    borderColor: "transparent",
  },
  gotItText: {
    fontSize: 15,
    fontWeight: "500",
    color: "#f4f4f5",
  },
  gotItTextDisabled: {
    color: "#52525b",
    fontSize: 13,
  },
});

// =============================================================================
// FOLLOW-UP SCREEN COMPONENT
// =============================================================================

interface FollowUpScreenProps {
  onStartConversation: () => void;
  onRefine: () => void;
}

function FollowUpScreen({ onStartConversation, onRefine }: FollowUpScreenProps) {
  return (
    <SafeAreaView style={followUpStyles.container}>
      <StatusBar barStyle="light-content" />
      <ScrollView
        style={followUpStyles.scrollView}
        contentContainerStyle={followUpStyles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        {/* Header */}
        <Text style={followUpStyles.header}>Let us refine this together</Text>

        {/* Body Copy - more compact */}
        <Text style={followUpStyles.body}>
          This snapshot is based on a few early signals. Sakhi learns best over time, from conversation, choices, and patterns you share.
        </Text>
        <Text style={followUpStyles.bodySecondary}>
          You are always in control of how this evolves.
        </Text>

        {/* What Happens Next - compact */}
        <View style={followUpStyles.optionsSection}>
          <Text style={followUpStyles.optionsTitle}>You can:</Text>
          <Text style={followUpStyles.optionItem}>• Let this evolve naturally as you talk</Text>
          <Text style={followUpStyles.optionItem}>• Or answer more questions to sharpen this view</Text>
        </View>

        {/* Actions Awareness - subtle, compact */}
        <View style={followUpStyles.actionsAwareness}>
          <Text style={followUpStyles.actionsLabel}>Along the way</Text>
          <Text style={followUpStyles.actionsBody}>
            Sakhi can also help with outside friction: making sense of things, or taking small things off your plate.
          </Text>
        </View>

        {/* CTA Stack - inside scroll for better layout */}
        <View style={followUpStyles.ctaSection}>
          <Pressable style={followUpStyles.primaryButton} onPress={onRefine}>
            <Text style={followUpStyles.primaryButtonText}>Refine this now</Text>
          </Pressable>
          <Pressable style={followUpStyles.secondaryButton} onPress={onStartConversation}>
            <Text style={followUpStyles.secondaryButtonText}>Start a conversation</Text>
          </Pressable>
        </View>

        {/* Footer Reassurance */}
        <Text style={followUpStyles.reassurance}>
          You can revisit or update this anytime.
        </Text>
      </ScrollView>
    </SafeAreaView>
  );
}

// =============================================================================
// FOLLOW-UP STYLES
// =============================================================================

const followUpStyles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#0a0a0a",
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    flexGrow: 1,
    paddingHorizontal: 32,
    paddingTop: 56,
    paddingBottom: 48,
    justifyContent: "center",
  },
  header: {
    fontSize: 24,
    fontWeight: "500",
    color: "#f4f4f5",
    textAlign: "center",
    marginBottom: 28,
    letterSpacing: -0.3,
  },
  body: {
    fontSize: 15,
    color: "#a1a1aa",
    textAlign: "center",
    lineHeight: 24,
    marginBottom: 14,
  },
  bodySecondary: {
    fontSize: 15,
    color: "#71717a",
    textAlign: "center",
    lineHeight: 24,
    marginBottom: 32,
  },
  optionsSection: {
    marginBottom: 28,
  },
  optionsTitle: {
    fontSize: 13,
    fontWeight: "500",
    color: "#52525b",
    marginBottom: 14,
    textAlign: "center",
    textTransform: "uppercase",
    letterSpacing: 0.5,
  },
  optionItem: {
    fontSize: 14,
    color: "#a1a1aa",
    textAlign: "center",
    lineHeight: 22,
    marginBottom: 8,
  },
  actionsAwareness: {
    marginTop: 12,
    paddingTop: 24,
    paddingBottom: 8,
    borderTopWidth: 1,
    borderTopColor: "#1a1a1f",
    alignItems: "center",
  },
  actionsLabel: {
    fontSize: 10,
    fontWeight: "500",
    color: "#3f3f46",
    letterSpacing: 1.5,
    textTransform: "uppercase",
    marginBottom: 10,
  },
  actionsBody: {
    fontSize: 13,
    color: "#52525b",
    textAlign: "center",
    lineHeight: 20,
    paddingHorizontal: 12,
  },
  ctaSection: {
    marginTop: 36,
    alignItems: "center",
    gap: 12,
  },
  primaryButton: {
    backgroundColor: "#6366f1",
    paddingVertical: 18,
    paddingHorizontal: 36,
    borderRadius: 14,
    width: "100%",
    alignItems: "center",
    minHeight: 56,
    justifyContent: "center",
  },
  primaryButtonText: {
    fontSize: 16,
    fontWeight: "500",
    color: "#fff",
  },
  secondaryButton: {
    paddingVertical: 14,
    paddingHorizontal: 24,
    minHeight: 48,
    justifyContent: "center",
  },
  secondaryButtonText: {
    fontSize: 14,
    color: "#52525b",
  },
  reassurance: {
    fontSize: 12,
    color: "#3f3f46",
    textAlign: "center",
    marginTop: 20,
  },
});

// =============================================================================
// INTERMEDIATE OS SCREEN COMPONENT
// =============================================================================

interface IntermediateOSScreenProps {
  osResult: OnboardingResponse | null;
  loading: boolean;
  error: string | null;
  onRefineMore: () => void;
  onStartConversation: () => void;
}

function IntermediateOSScreen({ osResult, loading, error, onRefineMore, onStartConversation }: IntermediateOSScreenProps) {
  // Show loading state while API is being called
  if (loading) {
    return (
      <SafeAreaView style={intermediateStyles.container}>
        <StatusBar barStyle="light-content" />
        <View style={intermediateStyles.loadingContainer}>
          <ActivityIndicator size="large" color="#6366f1" />
          <Text style={intermediateStyles.loadingText}>Refining your profile...</Text>
        </View>
      </SafeAreaView>
    );
  }

  // Show error state if API call failed
  if (error || !osResult) {
    return (
      <SafeAreaView style={intermediateStyles.container}>
        <StatusBar barStyle="light-content" />
        <View style={intermediateStyles.loadingContainer}>
          <Text style={intermediateStyles.errorText}>
            {error || "Something went wrong. Please try again."}
          </Text>
          <Pressable style={intermediateStyles.retryButton} onPress={onStartConversation}>
            <Text style={intermediateStyles.retryButtonText}>Continue anyway</Text>
          </Pressable>
        </View>
      </SafeAreaView>
    );
  }

  // Map API response to display format
  const displayResult = {
    title: osResult.operating_system,
    adaptive: Math.round(osResult.dosha_baseline.vata * 100),
    performance: Math.round(osResult.dosha_baseline.pitta * 100),
    conservation: Math.round(osResult.dosha_baseline.kapha * 100),
  };

  return (
    <SafeAreaView style={intermediateStyles.container}>
      <StatusBar barStyle="light-content" />
      <ScrollView
        style={intermediateStyles.scrollView}
        contentContainerStyle={intermediateStyles.content}
        showsVerticalScrollIndicator={false}
      >
        {/* Header */}
        <Text style={intermediateStyles.header}>YOUR OPERATING SYSTEM</Text>
        <Text style={intermediateStyles.subheader}>{osResult.os_label}</Text>

        {/* Primary Title */}
        <Text style={intermediateStyles.primaryTitle}>{displayResult.title}</Text>

        {/* Distribution Bars */}
        <View style={intermediateStyles.barsContainer}>
          <View style={intermediateStyles.barRow}>
            <Text style={intermediateStyles.barLabel}>Adaptive</Text>
            <View style={intermediateStyles.barTrack}>
              <View style={[intermediateStyles.barFill, intermediateStyles.barAdaptive, { width: `${displayResult.adaptive}%` }]} />
            </View>
            <Text style={intermediateStyles.barValue}>{displayResult.adaptive}%</Text>
          </View>
          <View style={intermediateStyles.barRow}>
            <Text style={intermediateStyles.barLabel}>Performance</Text>
            <View style={intermediateStyles.barTrack}>
              <View style={[intermediateStyles.barFill, intermediateStyles.barPerformance, { width: `${displayResult.performance}%` }]} />
            </View>
            <Text style={intermediateStyles.barValue}>{displayResult.performance}%</Text>
          </View>
          <View style={intermediateStyles.barRow}>
            <Text style={intermediateStyles.barLabel}>Conservation</Text>
            <View style={intermediateStyles.barTrack}>
              <View style={[intermediateStyles.barFill, intermediateStyles.barConservation, { width: `${displayResult.conservation}%` }]} />
            </View>
            <Text style={intermediateStyles.barValue}>{displayResult.conservation}%</Text>
          </View>
        </View>

        {/* Progress note */}
        <Text style={intermediateStyles.progressNote}>
          A few more questions will sharpen this picture.
        </Text>
        <Text style={[intermediateStyles.progressNote, { color: "#6366f1", fontStyle: "italic", marginBottom: 28 }]}>
          Refine further to see your strengths and patterns.
        </Text>

        {/* CTA Stack */}
        <View style={intermediateStyles.ctaSection}>
          <Pressable style={intermediateStyles.primaryButton} onPress={onRefineMore}>
            <Text style={intermediateStyles.primaryButtonText}>Refine more</Text>
          </Pressable>
          <Pressable style={intermediateStyles.secondaryButton} onPress={onStartConversation}>
            <Text style={intermediateStyles.secondaryButtonText}>Start a conversation</Text>
          </Pressable>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

// =============================================================================
// INTERMEDIATE OS STYLES
// =============================================================================

const intermediateStyles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#0a0a0a",
  },
  scrollView: {
    flex: 1,
  },
  content: {
    flexGrow: 1,
    padding: 28,
    paddingTop: 56,
    justifyContent: "center",
  },
  header: {
    fontSize: 11,
    fontWeight: "500",
    color: "#52525b",
    letterSpacing: 2,
    textAlign: "center",
    marginBottom: 10,
  },
  subheader: {
    fontSize: 14,
    color: "#6366f1",
    textAlign: "center",
    marginBottom: 28,
  },
  primaryTitle: {
    fontSize: 28,
    fontWeight: "600",
    color: "#f4f4f5",
    textAlign: "center",
    letterSpacing: -0.5,
    marginBottom: 36,
  },
  barsContainer: {
    gap: 16,
    marginBottom: 36,
  },
  barRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 14,
  },
  barLabel: {
    fontSize: 13,
    color: "#71717a",
    width: 95,
  },
  barTrack: {
    flex: 1,
    height: 10,
    backgroundColor: "#18191d",
    borderRadius: 5,
    overflow: "hidden",
  },
  barFill: {
    height: "100%",
    borderRadius: 5,
  },
  barAdaptive: {
    backgroundColor: "#8b5cf6",
  },
  barPerformance: {
    backgroundColor: "#f59e0b",
  },
  barConservation: {
    backgroundColor: "#10b981",
  },
  barValue: {
    fontSize: 13,
    color: "#71717a",
    width: 44,
    textAlign: "right",
  },
  progressNote: {
    fontSize: 14,
    color: "#52525b",
    textAlign: "center",
    marginBottom: 36,
  },
  ctaSection: {
    alignItems: "center",
    gap: 14,
  },
  primaryButton: {
    backgroundColor: "#6366f1",
    paddingVertical: 18,
    paddingHorizontal: 36,
    borderRadius: 14,
    width: "100%",
    alignItems: "center",
    minHeight: 56,
    justifyContent: "center",
  },
  primaryButtonText: {
    fontSize: 16,
    fontWeight: "500",
    color: "#fff",
  },
  secondaryButton: {
    paddingVertical: 14,
    paddingHorizontal: 24,
    minHeight: 48,
    justifyContent: "center",
  },
  secondaryButtonText: {
    fontSize: 14,
    color: "#52525b",
  },
  loadingContainer: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    padding: 28,
  },
  loadingText: {
    fontSize: 16,
    color: "#a1a1aa",
    marginTop: 16,
    textAlign: "center",
  },
  errorText: {
    fontSize: 16,
    color: "#ef4444",
    textAlign: "center",
    marginBottom: 24,
    lineHeight: 24,
  },
  retryButton: {
    backgroundColor: "#27272a",
    paddingVertical: 14,
    paddingHorizontal: 28,
    borderRadius: 12,
    minHeight: 48,
    justifyContent: "center",
  },
  retryButtonText: {
    fontSize: 14,
    fontWeight: "500",
    color: "#a1a1aa",
  },
});

// =============================================================================
// FINAL OS SCREEN COMPONENT
// =============================================================================

interface FinalOSScreenProps {
  osResult: OnboardingResponse | null;
  loading: boolean;
  error: string | null;
  onStartConversation: () => void;
}

function FinalOSScreen({ osResult, loading, error, onStartConversation }: FinalOSScreenProps) {
  // Show loading state while API is being called
  if (loading) {
    return (
      <SafeAreaView style={finalStyles.container}>
        <StatusBar barStyle="light-content" />
        <View style={finalStyles.loadingContainer}>
          <ActivityIndicator size="large" color="#6366f1" />
          <Text style={finalStyles.loadingText}>Finalizing your profile...</Text>
        </View>
      </SafeAreaView>
    );
  }

  // Show error state if API call failed
  if (error || !osResult) {
    return (
      <SafeAreaView style={finalStyles.container}>
        <StatusBar barStyle="light-content" />
        <View style={finalStyles.loadingContainer}>
          <Text style={finalStyles.errorText}>
            {error || "Something went wrong. Please try again."}
          </Text>
          <Pressable style={finalStyles.retryButton} onPress={onStartConversation}>
            <Text style={finalStyles.retryButtonText}>Continue anyway</Text>
          </Pressable>
        </View>
      </SafeAreaView>
    );
  }

  // Map API response to display format
  const displayResult = {
    title: osResult.operating_system,
    adaptive: Math.round(osResult.dosha_baseline.vata * 100),
    performance: Math.round(osResult.dosha_baseline.pitta * 100),
    conservation: Math.round(osResult.dosha_baseline.kapha * 100),
  };

  return (
    <SafeAreaView style={finalStyles.container}>
      <StatusBar barStyle="light-content" />
      <ScrollView
        style={finalStyles.scrollView}
        contentContainerStyle={finalStyles.content}
        showsVerticalScrollIndicator={false}
      >
        {/* Header */}
        <Text style={finalStyles.header}>YOUR OPERATING SYSTEM</Text>
        <Text style={finalStyles.subheader}>{osResult.os_label}</Text>

        {/* Primary Title */}
        <Text style={finalStyles.primaryTitle}>{displayResult.title}</Text>

        {/* Distribution Bars */}
        <View style={finalStyles.barsContainer}>
          <View style={finalStyles.barRow}>
            <Text style={finalStyles.barLabel}>Adaptive</Text>
            <View style={finalStyles.barTrack}>
              <View style={[finalStyles.barFill, finalStyles.barAdaptive, { width: `${displayResult.adaptive}%` }]} />
            </View>
            <Text style={finalStyles.barValue}>{displayResult.adaptive}%</Text>
          </View>
          <View style={finalStyles.barRow}>
            <Text style={finalStyles.barLabel}>Performance</Text>
            <View style={finalStyles.barTrack}>
              <View style={[finalStyles.barFill, finalStyles.barPerformance, { width: `${displayResult.performance}%` }]} />
            </View>
            <Text style={finalStyles.barValue}>{displayResult.performance}%</Text>
          </View>
          <View style={finalStyles.barRow}>
            <Text style={finalStyles.barLabel}>Conservation</Text>
            <View style={finalStyles.barTrack}>
              <View style={[finalStyles.barFill, finalStyles.barConservation, { width: `${displayResult.conservation}%` }]} />
            </View>
            <Text style={finalStyles.barValue}>{displayResult.conservation}%</Text>
          </View>
        </View>

        {/* Strengths Card */}
        <View style={{ backgroundColor: "#18191d", borderRadius: 18, padding: 22, marginBottom: 18, borderWidth: 1, borderColor: "#27272a" }}>
          <Text style={{ fontSize: 15, fontWeight: "600", color: "#f4f4f5", marginBottom: 18 }}>Your Strengths</Text>
          {osResult.os_details.strengths.map((s: string, i: number) => (
            <View key={i} style={{ flexDirection: "row", marginBottom: 12 }}>
              <Text style={{ color: "#6366f1", marginRight: 12, marginTop: 2 }}>•</Text>
              <Text style={{ fontSize: 14, color: "#a1a1aa", flex: 1, lineHeight: 20 }}>{s}</Text>
            </View>
          ))}
        </View>

        {/* Patterns Card */}
        <View style={{ backgroundColor: "#18191d", borderRadius: 18, padding: 22, marginBottom: 28, borderWidth: 1, borderColor: "#27272a" }}>
          <Text style={{ fontSize: 15, fontWeight: "600", color: "#f4f4f5", marginBottom: 18 }}>Patterns to Watch</Text>
          {osResult.os_details.patterns_to_watch.map((p: string, i: number) => (
            <View key={i} style={{ flexDirection: "row", marginBottom: 12 }}>
              <Text style={{ color: "#6366f1", marginRight: 12, marginTop: 2 }}>•</Text>
              <Text style={{ fontSize: 14, color: "#a1a1aa", flex: 1, lineHeight: 20 }}>{p}</Text>
            </View>
          ))}
        </View>

        {/* Message */}
        <Text style={finalStyles.message}>
          This is a good picture to start with.
        </Text>
        <Text style={finalStyles.submessage}>
          Sakhi will continue learning as you talk.
        </Text>

        {/* CTA */}
        <View style={finalStyles.ctaSection}>
          <Pressable style={finalStyles.primaryButton} onPress={onStartConversation}>
            <Text style={finalStyles.primaryButtonText}>Start a conversation</Text>
          </Pressable>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

// =============================================================================
// FINAL OS STYLES
// =============================================================================

const finalStyles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#0a0a0a",
  },
  scrollView: {
    flex: 1,
  },
  content: {
    flexGrow: 1,
    padding: 28,
    paddingTop: 56,
    justifyContent: "center",
  },
  header: {
    fontSize: 11,
    fontWeight: "500",
    color: "#52525b",
    letterSpacing: 2,
    textAlign: "center",
    marginBottom: 10,
  },
  subheader: {
    fontSize: 14,
    color: "#22c55e",
    textAlign: "center",
    marginBottom: 28,
  },
  primaryTitle: {
    fontSize: 28,
    fontWeight: "600",
    color: "#f4f4f5",
    textAlign: "center",
    letterSpacing: -0.5,
    marginBottom: 36,
  },
  barsContainer: {
    gap: 16,
    marginBottom: 36,
  },
  barRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 14,
  },
  barLabel: {
    fontSize: 13,
    color: "#71717a",
    width: 95,
  },
  barTrack: {
    flex: 1,
    height: 10,
    backgroundColor: "#18191d",
    borderRadius: 5,
    overflow: "hidden",
  },
  barFill: {
    height: "100%",
    borderRadius: 5,
  },
  barAdaptive: {
    backgroundColor: "#8b5cf6",
  },
  barPerformance: {
    backgroundColor: "#f59e0b",
  },
  barConservation: {
    backgroundColor: "#10b981",
  },
  barValue: {
    fontSize: 13,
    color: "#71717a",
    width: 44,
    textAlign: "right",
  },
  message: {
    fontSize: 16,
    color: "#f4f4f5",
    textAlign: "center",
    marginBottom: 10,
  },
  submessage: {
    fontSize: 14,
    color: "#52525b",
    textAlign: "center",
    marginBottom: 44,
  },
  ctaSection: {
    alignItems: "center",
  },
  primaryButton: {
    backgroundColor: "#6366f1",
    paddingVertical: 18,
    paddingHorizontal: 36,
    borderRadius: 14,
    width: "100%",
    alignItems: "center",
    minHeight: 56,
    justifyContent: "center",
  },
  primaryButtonText: {
    fontSize: 16,
    fontWeight: "500",
    color: "#fff",
  },
  loadingContainer: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    padding: 28,
  },
  loadingText: {
    fontSize: 16,
    color: "#a1a1aa",
    marginTop: 16,
    textAlign: "center",
  },
  errorText: {
    fontSize: 16,
    color: "#ef4444",
    textAlign: "center",
    marginBottom: 24,
    lineHeight: 24,
  },
  retryButton: {
    backgroundColor: "#27272a",
    paddingVertical: 14,
    paddingHorizontal: 28,
    borderRadius: 12,
    minHeight: 48,
    justifyContent: "center",
  },
  retryButtonText: {
    fontSize: 14,
    fontWeight: "500",
    color: "#a1a1aa",
  },
});

// =============================================================================
// MAIN COMPONENT
// =============================================================================

function SlimNameOnboardingScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ user?: string; name?: string }>();
  const { user, session, hydrateLinkedProfile } = useAuth();
  const [name, setName] = useState(
    typeof params.name === "string" && params.name.trim()
      ? params.name
      : user?.fullName || "",
  );
  const [isSaving, setIsSaving] = useState(false);

  const authToken = session?.access_token || "";
  const canContinue = name.trim().length > 0 && !!authToken;

  const handleContinue = useCallback(async () => {
    const trimmedName = name.trim();
    if (!trimmedName || !authToken) {
      return;
    }

    setIsSaving(true);
    try {
      const profile = await bootstrapMobileAuthProfile(authToken, {
        email: user?.email || "",
        full_name: trimmedName,
        avatar_url: user?.avatarUrl,
      }, { supabaseUserId: user?.id });
      await hydrateLinkedProfile({
        personId: profile.person_id,
        email: profile.email,
        fullName: trimmedName,
        avatarUrl: profile.avatar_url,
      }, { supabaseUserId: user?.id });

      void supabase.auth.updateUser({
        data: {
          full_name: trimmedName,
          name: trimmedName,
        },
      }).catch(() => {});

      router.replace("/" as never);
    } catch (error) {
      console.error("Name setup failed:", error);
      Alert.alert("Could not continue", "Please try again.");
    } finally {
      setIsSaving(false);
    }
  }, [authToken, hydrateLinkedProfile, name, router, user?.avatarUrl, user?.email, user?.id]);

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" />
      <KeyboardAvoidingView
        style={styles.keyboardView}
        behavior={Platform.OS === "ios" ? "padding" : "height"}
      >
        <View style={styles.content}>
          <View style={[styles.header, styles.framingHeader]}>
            <Text style={styles.title}>What should I call you?</Text>
            <Text style={styles.subtitle}>Whatever feels natural to you.</Text>
          </View>

          <View style={styles.questionContainer}>
            <TextInput
              style={styles.textInput}
              placeholder="Your name (or a nickname)"
              placeholderTextColor="#52525b"
              value={name}
              onChangeText={setName}
              autoFocus
              returnKeyType="done"
              onSubmitEditing={() => void handleContinue()}
            />
          </View>
        </View>

        <View style={styles.footer}>
          <Pressable
            style={[
              styles.transitionContinueButton,
              (!canContinue || isSaving) && styles.calibrationButtonDisabled,
            ]}
            onPress={() => void handleContinue()}
            disabled={!canContinue || isSaving}
          >
            {isSaving ? (
              <ActivityIndicator color="#fff" size="small" />
            ) : (
              <Text
                style={[
                  styles.transitionContinueText,
                  !canContinue && styles.calibrationButtonTextDisabled,
                ]}
              >
                Continue
              </Text>
            )}
          </Pressable>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

export function LegacyOnboardingScreen() {
  const router = useRouter();
  const [currentScreen, setCurrentScreen] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string | string[]>>({});
  const [refineMode, setRefineMode] = useState(false);
  const [refineScreen, setRefineScreen] = useState(0);

  // API integration
  const { loading, error, osResult, submitOnboarding } = useOnboarding();
  const [phase1Submitted, setPhase1Submitted] = useState(false);
  const [phase2aSubmitted, setPhase2aSubmitted] = useState(false);
  const [phase2bSubmitted, setPhase2bSubmitted] = useState(false);

  // Submit Phase 1 when entering mirror screen
  useEffect(() => {
    const screens = refineMode ? REFINE_SCREENS : SCREENS;
    const screenIndex = refineMode ? refineScreen : currentScreen;
    const screen = screens[screenIndex];

    if (screen.isMirror && !phase1Submitted && !loading) {
      setPhase1Submitted(true);
      submitOnboarding("phase1", answers);
    }
  }, [currentScreen, refineMode, refineScreen, phase1Submitted, loading, answers, submitOnboarding]);

  // Submit Phase 2a when entering intermediate OS screen
  useEffect(() => {
    const screens = refineMode ? REFINE_SCREENS : SCREENS;
    const screenIndex = refineMode ? refineScreen : currentScreen;
    const screen = screens[screenIndex];

    if (screen.isIntermediateOS && !phase2aSubmitted && !loading) {
      setPhase2aSubmitted(true);
      submitOnboarding("phase2a", answers);
    }
  }, [currentScreen, refineMode, refineScreen, phase2aSubmitted, loading, answers, submitOnboarding]);

  // Submit Phase 2b when entering final OS screen
  useEffect(() => {
    const screens = refineMode ? REFINE_SCREENS : SCREENS;
    const screenIndex = refineMode ? refineScreen : currentScreen;
    const screen = screens[screenIndex];

    if (screen.isFinalOS && !phase2bSubmitted && !loading) {
      setPhase2bSubmitted(true);
      submitOnboarding("phase2b", answers);
    }
  }, [currentScreen, refineMode, refineScreen, phase2bSubmitted, loading, answers, submitOnboarding]);

  // Determine which screen set and current screen
  const screens = refineMode ? REFINE_SCREENS : SCREENS;
  const screenIndex = refineMode ? refineScreen : currentScreen;
  const screen = screens[screenIndex];
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
        // Refine complete - go to conversation
        router.replace("/" as never);
      } else {
        setRefineScreen((prev) => prev + 1);
      }
    } else {
      setCurrentScreen((prev) => prev + 1);
    }
  }, [refineMode, refineScreen, router]);

  const handleBack = useCallback(() => {
    if (refineMode) {
      if (refineScreen > 0) {
        setRefineScreen((prev) => prev - 1);
      } else {
        // Exit refine mode, go back to follow-up
        setRefineMode(false);
      }
    } else {
      if (currentScreen > 0) {
        setCurrentScreen((prev) => prev - 1);
      }
    }
  }, [refineMode, refineScreen, currentScreen]);

  const handleSkip = useCallback(() => {
    // Skip current question and move to next
    if (refineMode) {
      if (refineScreen >= REFINE_SCREENS.length - 1) {
        router.replace("/" as never);
      } else {
        setRefineScreen((prev) => prev + 1);
      }
    } else {
      setCurrentScreen((prev) => prev + 1);
    }
  }, [refineMode, refineScreen, router]);

  const handleMirrorContinue = useCallback(() => {
    setCurrentScreen((prev) => prev + 1);
  }, []);

  const handleStartConversation = useCallback(() => {
    // Save preferred name if entered (fire and forget)
    const name = answers.preferred_name;
    if (typeof name === "string" && name.trim()) {
      supabase.auth.getUser().then(({ data: { user } }) => {
        if (user?.id) {
          supabase
            .from("auth_users")
            .update({ full_name: name.trim() })
            .eq("supabase_user_id", user.id)
            .then(() => {}); // best effort
        }
      }).catch(() => {}); // don't block navigation
    }
    router.replace("/" as never);
  }, [router, answers]);

  const handleRefine = useCallback(() => {
    setRefineMode(true);
    setRefineScreen(0);
  }, []);

  const handleRefineMore = useCallback(() => {
    // Continue to next question after intermediate OS
    setRefineScreen((prev) => prev + 1);
  }, []);

  // Render Mirror screen
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

  // Render Follow-up screen
  if (screen.isFollowUp) {
    return (
      <FollowUpScreen
        onStartConversation={handleStartConversation}
        onRefine={handleRefine}
      />
    );
  }

  // Render Intermediate OS screen (in refine flow)
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

  // Render Final OS screen (end of refine flow)
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

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" />

      {/* Progress bar - hidden for first screen, transition and calibration screens */}
      {refineMode ? (
        <View style={styles.progressContainer}>
          <View style={[styles.progressBar, { width: `${((refineScreen + 1) / REFINE_SCREENS.length) * 100}%` }]} />
        </View>
      ) : null}

      {/* Sakhi header for transition and calibration screens */}
      {(screen.isTransition || screen.isCalibration) && !refineMode && (
        <View style={styles.transitionHeader}>
          <Text style={styles.transitionHeaderText}>Sakhi</Text>
        </View>
      )}

      {/* Back button for refine mode */}
      {refineMode && refineScreen > 0 && (
        <View style={styles.refineBackHeader}>
          <Pressable style={styles.refineBackButton} onPress={handleBack}>
            <Text style={styles.refineBackText}>← Back</Text>
          </Pressable>
        </View>
      )}

      <KeyboardAvoidingView
        style={styles.keyboardView}
        behavior={Platform.OS === "ios" ? "padding" : "height"}
      >
        <ScrollView
          style={styles.scrollView}
          contentContainerStyle={[
            styles.content,
            screen.id === "framing" && styles.centeredContent,
          ]}
          keyboardShouldPersistTaps="handled"
        >
          {/* Header */}
          <View style={[
            styles.header,
            screen.isTransition && styles.transitionContent,
            screen.isCalibration && styles.calibrationContent,
            screen.id === "framing" && styles.framingHeader,
          ]}>
            <Text style={[
              styles.title,
              screen.isTransition && styles.transitionTitle,
              screen.isCalibration && styles.calibrationTitle,
            ]}>
              {screen.title}
            </Text>
            {screen.subtitle && <Text style={styles.subtitle}>{screen.subtitle}</Text>}
            {screen.body && (
              <Text style={styles.transitionBody}>{screen.body}</Text>
            )}
          </View>

          {/* Questions */}
          {screen.questions.map((question) => (
            <View key={question.id} style={styles.questionContainer}>
              {question.text ? (
                <Text style={styles.questionText}>{question.text}</Text>
              ) : null}

              {question.type === "text" ? (
                <TextInput
                  style={styles.textInput}
                  placeholder={question.placeholder}
                  placeholderTextColor="#52525b"
                  value={(answers[question.id] as string) || ""}
                  onChangeText={(value) => handleTextAnswer(question.id, value)}
                />
              ) : (
                <View style={styles.optionsContainer}>
                  {question.options?.map((option) => {
                    const isMulti = question.type === "multi";
                    const currentAnswer = answers[question.id];
                    const isSelected = isMulti
                      ? ((currentAnswer as string[]) || []).includes(option.value)
                      : currentAnswer === option.value;

                    return (
                      <Pressable
                        key={option.value}
                        style={[styles.option, isSelected && styles.optionSelected]}
                        onPress={() => handleAnswer(question.id, option.value, isMulti)}
                      >
                        <View style={[
                          isMulti ? styles.checkbox : styles.radio,
                          isSelected && styles.checkboxSelected,
                        ]}>
                          {isSelected && (
                            <View style={isMulti ? styles.checkmark : styles.radioDot} />
                          )}
                        </View>
                        <Text style={[styles.optionText, isSelected && styles.optionTextSelected]}>
                          {option.label}
                        </Text>
                      </Pressable>
                    );
                  })}
                </View>
              )}
            </View>
          ))}
        </ScrollView>

        {/* Footer */}
        <View style={[
          styles.footer,
          (screen.isTransition || screen.isCalibration) && styles.transitionFooter,
        ]}>
          {screen.isTransition ? (
            <>
              <Pressable
                style={styles.transitionContinueButton}
                onPress={isLastRefineScreen ? handleStartConversation : handleNext}
              >
                <Text style={styles.transitionContinueText}>
                  {isLastRefineScreen
                    ? "Start a conversation"
                    : refineMode && refineScreen === 0
                      ? "Let's continue"
                      : "Continue"}
                </Text>
              </Pressable>
              {screen.skipAllowed && !refineMode && (
                <Pressable
                  style={styles.skipButton}
                  onPress={() => router.replace("/" as never)}
                >
                  <Text style={styles.skipButtonText}>Skip for now</Text>
                </Pressable>
              )}
            </>
          ) : screen.isCalibration ? (
            <>
              {/* Skip button for skippable calibration questions */}
              {screen.skipAllowed && (
                <Pressable
                  style={styles.skipCalibrationButton}
                  onPress={handleSkip}
                >
                  <Text style={styles.skipCalibrationText}>Skip</Text>
                </Pressable>
              )}
              <Pressable
                style={[
                  styles.transitionContinueButton,
                  !canProceed && !screen.skipAllowed && styles.calibrationButtonDisabled,
                ]}
                onPress={handleNext}
                disabled={!canProceed && !screen.skipAllowed}
              >
                <Text style={[
                  styles.transitionContinueText,
                  !canProceed && !screen.skipAllowed && styles.calibrationButtonTextDisabled,
                ]}>
                  Continue
                </Text>
              </Pressable>
            </>
          ) : (
            <>
              <View style={styles.footerLeft}>
                {!isFirstScreen && (
                  <Pressable style={styles.backButton} onPress={handleBack}>
                    <Text style={styles.backButtonText}>Back</Text>
                  </Pressable>
                )}
              </View>

              <Pressable
                style={[styles.nextButton, !canProceed && styles.nextButtonDisabled]}
                onPress={handleNext}
                disabled={!canProceed && screen.questions.length > 0}
              >
                <Text style={styles.nextButtonText}>Continue</Text>
              </Pressable>
            </>
          )}
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

// =============================================================================
// STYLES
// =============================================================================

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#0a0a0a",
  },
  progressContainer: {
    height: 4,
    backgroundColor: "#27272a",
  },
  progressBar: {
    height: "100%",
    backgroundColor: "#6366f1",
  },
  keyboardView: {
    flex: 1,
  },
  scrollView: {
    flex: 1,
  },
  content: {
    padding: 28,
    paddingBottom: 120,
  },
  centeredContent: {
    flexGrow: 1,
    justifyContent: "center",
    paddingBottom: 140,
  },
  header: {
    marginBottom: 44,
    alignItems: "center",
  },
  framingHeader: {
    marginBottom: 32,
  },
  title: {
    fontSize: 28,
    fontWeight: "600",
    color: "#f4f4f5",
    textAlign: "center",
    marginBottom: 14,
    letterSpacing: -0.5,
  },
  subtitle: {
    fontSize: 16,
    color: "#a1a1aa",
    textAlign: "center",
    lineHeight: 24,
  },
  questionContainer: {
    marginBottom: 36,
  },
  questionText: {
    fontSize: 16,
    fontWeight: "500",
    color: "#f4f4f5",
    marginBottom: 18,
  },
  textInput: {
    backgroundColor: "#18191d",
    borderWidth: 1,
    borderColor: "#27272a",
    borderRadius: 14,
    paddingVertical: 18,
    paddingHorizontal: 18,
    fontSize: 15,
    color: "#f4f4f5",
    minHeight: 56,
  },
  optionsContainer: {
    gap: 12,
  },
  option: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "transparent",
    borderWidth: 1,
    borderColor: "#27272a",
    borderRadius: 14,
    paddingVertical: 18,
    paddingHorizontal: 18,
    gap: 16,
    minHeight: 56,
  },
  optionSelected: {
    borderColor: "#6366f1",
    backgroundColor: "rgba(99, 102, 241, 0.1)",
  },
  checkbox: {
    width: 22,
    height: 22,
    borderRadius: 5,
    borderWidth: 2,
    borderColor: "#52525b",
    alignItems: "center",
    justifyContent: "center",
  },
  radio: {
    width: 22,
    height: 22,
    borderRadius: 11,
    borderWidth: 2,
    borderColor: "#52525b",
    alignItems: "center",
    justifyContent: "center",
  },
  checkboxSelected: {
    borderColor: "#6366f1",
    backgroundColor: "#6366f1",
  },
  checkmark: {
    width: 11,
    height: 11,
    backgroundColor: "#fff",
    borderRadius: 2,
  },
  radioDot: {
    width: 10,
    height: 10,
    backgroundColor: "#fff",
    borderRadius: 5,
  },
  optionText: {
    fontSize: 15,
    color: "#a1a1aa",
    flex: 1,
  },
  optionTextSelected: {
    color: "#f4f4f5",
  },
  footer: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingVertical: 20,
    paddingHorizontal: 24,
    paddingBottom: 36,
    backgroundColor: "#0a0a0a",
  },
  footerLeft: {
    width: 80,
  },
  backButton: {
    paddingVertical: 14,
    paddingHorizontal: 16,
    minHeight: 48,
    justifyContent: "center",
  },
  backButtonText: {
    fontSize: 14,
    color: "#71717a",
  },
  nextButton: {
    backgroundColor: "#6366f1",
    paddingVertical: 14,
    paddingHorizontal: 28,
    borderRadius: 12,
    minWidth: 110,
    minHeight: 48,
    alignItems: "center",
    justifyContent: "center",
  },
  nextButtonDisabled: {
    backgroundColor: "#3f3f46",
  },
  nextButtonText: {
    fontSize: 14,
    fontWeight: "500",
    color: "#fff",
  },

  // Transition screen styles
  transitionHeader: {
    paddingTop: 24,
    paddingHorizontal: 28,
    alignItems: "center",
  },
  transitionHeaderText: {
    fontSize: 16,
    fontWeight: "500",
    color: "#71717a",
    letterSpacing: 1,
  },
  transitionContent: {
    flex: 1,
    justifyContent: "center",
    marginBottom: 0,
    paddingTop: 48,
  },
  transitionTitle: {
    fontSize: 26,
    fontWeight: "400",
    lineHeight: 36,
    marginBottom: 36,
  },
  transitionBody: {
    fontSize: 16,
    color: "#a1a1aa",
    textAlign: "center",
    lineHeight: 28,
    marginTop: 8,
  },
  transitionFooter: {
    flexDirection: "column",
    alignItems: "center",
    gap: 18,
    paddingBottom: 52,
  },
  transitionContinueButton: {
    backgroundColor: "#6366f1",
    paddingVertical: 18,
    paddingHorizontal: 52,
    borderRadius: 14,
    minWidth: 220,
    minHeight: 56,
    alignItems: "center",
    justifyContent: "center",
  },
  transitionContinueText: {
    fontSize: 16,
    fontWeight: "500",
    color: "#fff",
  },
  skipButton: {
    paddingVertical: 14,
    paddingHorizontal: 28,
    minHeight: 48,
    justifyContent: "center",
  },
  skipButtonText: {
    fontSize: 14,
    color: "#52525b",
  },

  // Calibration screen styles
  calibrationContent: {
    marginBottom: 28,
    paddingTop: 44,
  },
  calibrationTitle: {
    fontSize: 24,
    fontWeight: "400",
    lineHeight: 34,
    marginBottom: 0,
  },
  calibrationButtonDisabled: {
    backgroundColor: "#27272a",
  },
  calibrationButtonTextDisabled: {
    color: "#52525b",
  },
  skipCalibrationButton: {
    paddingVertical: 14,
    paddingHorizontal: 28,
    marginBottom: 10,
    minHeight: 48,
    justifyContent: "center",
  },
  skipCalibrationText: {
    fontSize: 14,
    color: "#52525b",
  },
  refineBackHeader: {
    paddingTop: 16,
    paddingHorizontal: 16,
  },
  refineBackButton: {
    paddingVertical: 12,
    paddingHorizontal: 12,
    minHeight: 48,
    justifyContent: "center",
  },
  refineBackText: {
    fontSize: 14,
    color: "#71717a",
  },
});

export default function OnboardingScreen() {
  return <SlimNameOnboardingScreen />;
}
