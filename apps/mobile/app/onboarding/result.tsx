import React, { useState, useEffect } from "react";
import {
  View,
  Text,
  ScrollView,
  Pressable,
  StyleSheet,
  SafeAreaView,
  StatusBar,
} from "react-native";
import { useRouter, useLocalSearchParams } from "expo-router";

// =============================================================================
// TYPES & DATA
// =============================================================================

interface OperatingSystemResult {
  operating_system: string;
  primary: string;
  secondary: string | null;
  dosha_baseline: {
    vata: number;
    pitta: number;
    kapha: number;
  };
}

const OS_CONTENT: Record<string, {
  tagline: string;
  description: string;
  strengths: string[];
  watchFor: string[];
  color: string;
}> = {
  Adaptive: {
    tagline: "Quick-thinking & Creative",
    description: "You thrive on variety and change. Your mind moves quickly, making connections others miss.",
    strengths: ["Quick thinking", "Creative problem-solving", "Adaptable to change", "Enthusiastic starter"],
    watchFor: ["Scattered energy", "Difficulty with routine", "Overcommitting", "Sleep disruption"],
    color: "#e8c547",
  },
  Performance: {
    tagline: "Driven & Focused",
    description: "You're naturally goal-oriented with strong focus and drive. You transform ideas into reality.",
    strengths: ["Strong focus", "Natural leadership", "Decisive action", "Results-oriented"],
    watchFor: ["Pushing past limits", "Impatience", "Burnout from intensity", "Difficulty relaxing"],
    color: "#ef6461",
  },
  Conservation: {
    tagline: "Steady & Grounded",
    description: "You bring stability and endurance to everything. Your calm presence anchors others.",
    strengths: ["Steady energy", "Patient & reliable", "Strong memory", "Calm under pressure"],
    watchFor: ["Resistance to change", "Holding on too long", "Low energy dips", "Comfort zone attachment"],
    color: "#4ecdc4",
  },
  "Adaptive-Performance": {
    tagline: "Creative Drive",
    description: "You blend creativity with execution. Ideas flow easily, and you have the drive to make them real.",
    strengths: ["Innovation + execution", "Quick adaptation", "Passionate pursuit", "Problem solver"],
    watchFor: ["Burnout from intensity", "Scattered focus", "Impatience", "Difficulty with routine"],
    color: "#e8c547",
  },
  "Performance-Conservation": {
    tagline: "Driven Endurance",
    description: "You combine ambition with staying power. You can push hard and sustain effort over time.",
    strengths: ["Sustained focus", "Patient ambition", "Reliable execution", "Strategic thinking"],
    watchFor: ["Stubbornness", "Over-controlling", "Difficulty delegating", "Slow to pivot"],
    color: "#ef6461",
  },
  "Adaptive-Conservation": {
    tagline: "Creative Stability",
    description: "You blend imagination with groundedness. Visionary yet dependable.",
    strengths: ["Grounded creativity", "Flexible stability", "Patient innovation", "Calm adaptability"],
    watchFor: ["Analysis paralysis", "Slow starts", "Comfort zone creativity", "Difficulty with urgency"],
    color: "#4ecdc4",
  },
  Balanced: {
    tagline: "Natural Equilibrium",
    description: "You have a naturally balanced constitution. This gives you flexibility across situations.",
    strengths: ["Situational flexibility", "Even temperament", "Broad adaptability", "Natural balance"],
    watchFor: ["Lack of specialization", "May need more structure", "Can drift without focus"],
    color: "#6366f1",
  },
};

// =============================================================================
// COMPONENT
// =============================================================================

export default function OnboardingResultScreen() {
  const router = useRouter();
  const params = useLocalSearchParams();
  const [result, setResult] = useState<OperatingSystemResult | null>(null);
  const [showDetails, setShowDetails] = useState(false);

  useEffect(() => {
    if (params.result) {
      try {
        const parsed = JSON.parse(params.result as string);
        setResult(parsed);
      } catch {
        // Use default balanced result
        setResult({
          operating_system: "Balanced",
          primary: "balanced",
          secondary: null,
          dosha_baseline: { vata: 0.33, pitta: 0.33, kapha: 0.34 },
        });
      }
    } else {
      // Use default if no result passed
      setResult({
        operating_system: "Balanced",
        primary: "balanced",
        secondary: null,
        dosha_baseline: { vata: 0.33, pitta: 0.33, kapha: 0.34 },
      });
    }
  }, [params.result]);

  const handleContinue = () => {
    router.replace("/voice" as never);
  };

  if (!result) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.loadingContainer}>
          <Text style={styles.loadingText}>Analyzing your responses...</Text>
        </View>
      </SafeAreaView>
    );
  }

  const osType = result.operating_system || "Balanced";
  const content = OS_CONTENT[osType] || OS_CONTENT.Balanced;
  const doshaBaseline = result.dosha_baseline || { vata: 0.33, pitta: 0.33, kapha: 0.34 };

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" />

      <ScrollView style={styles.scrollView} contentContainerStyle={styles.content}>
        {/* Label */}
        <Text style={styles.label}>YOUR OPERATING SYSTEM</Text>

        {/* OS Type */}
        <Text style={[styles.osType, { color: content.color }]}>{osType}</Text>
        <Text style={styles.tagline}>{content.tagline}</Text>

        {/* Description */}
        <Text style={styles.description}>{content.description}</Text>

        {/* Dosha Bars */}
        <View style={styles.doshaContainer}>
          <DoshaBar label="Adaptive" value={doshaBaseline.vata} color="#e8c547" />
          <DoshaBar label="Performance" value={doshaBaseline.pitta} color="#ef6461" />
          <DoshaBar label="Conservation" value={doshaBaseline.kapha} color="#4ecdc4" />
        </View>

        {/* Toggle Details */}
        <Pressable style={styles.toggleButton} onPress={() => setShowDetails(!showDetails)}>
          <Text style={styles.toggleText}>
            {showDetails ? "Hide details" : "See your strengths & patterns"}
          </Text>
          <Text style={[styles.toggleArrow, showDetails && styles.toggleArrowUp]}>▼</Text>
        </Pressable>

        {/* Strengths & Watch For */}
        {showDetails && (
          <>
            <View style={styles.card}>
              <Text style={styles.cardTitle}>✦ Your Strengths</Text>
              {content.strengths.map((strength, i) => (
                <View key={i} style={styles.listItem}>
                  <Text style={styles.listBullet}>+</Text>
                  <Text style={styles.listText}>{strength}</Text>
                </View>
              ))}
            </View>

            <View style={styles.card}>
              <Text style={styles.cardTitle}>⚡ Patterns to Watch</Text>
              {content.watchFor.map((pattern, i) => (
                <View key={i} style={styles.listItem}>
                  <Text style={[styles.listBullet, { color: "#e8c547" }]}>~</Text>
                  <Text style={styles.listText}>{pattern}</Text>
                </View>
              ))}
            </View>
          </>
        )}

        {/* Note */}
        <Text style={styles.note}>
          This is your baseline tendency, not a fixed identity.{"\n"}
          Sakhi will learn and adapt as you share more.
        </Text>
      </ScrollView>

      {/* Footer */}
      <View style={styles.footer}>
        <Pressable style={styles.continueButton} onPress={handleContinue}>
          <Text style={styles.continueButtonText}>Start a Conversation</Text>
        </Pressable>
      </View>
    </SafeAreaView>
  );
}

// =============================================================================
// DOSHA BAR COMPONENT
// =============================================================================

function DoshaBar({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <View style={styles.doshaRow}>
      <Text style={styles.doshaLabel}>{label}</Text>
      <View style={styles.doshaBarBg}>
        <View style={[styles.doshaBarFill, { width: `${value * 100}%`, backgroundColor: color }]} />
      </View>
      <Text style={styles.doshaPercent}>{Math.round(value * 100)}%</Text>
    </View>
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
  loadingContainer: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  loadingText: {
    color: "#71717a",
    fontSize: 16,
  },
  scrollView: {
    flex: 1,
  },
  content: {
    padding: 24,
    paddingBottom: 140,
    alignItems: "center",
  },
  label: {
    fontSize: 12,
    fontWeight: "600",
    color: "#71717a",
    letterSpacing: 2,
    marginBottom: 16,
  },
  osType: {
    fontSize: 36,
    fontWeight: "600",
    textAlign: "center",
    marginBottom: 8,
    letterSpacing: -1,
  },
  tagline: {
    fontSize: 18,
    color: "#a1a1aa",
    marginBottom: 32,
  },
  description: {
    fontSize: 16,
    color: "#e4e4e7",
    textAlign: "center",
    lineHeight: 26,
    marginBottom: 40,
    paddingHorizontal: 16,
  },
  doshaContainer: {
    width: "100%",
    marginBottom: 32,
  },
  doshaRow: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 16,
    gap: 12,
  },
  doshaLabel: {
    width: 100,
    fontSize: 14,
    color: "#71717a",
  },
  doshaBarBg: {
    flex: 1,
    height: 8,
    backgroundColor: "#27272a",
    borderRadius: 4,
    overflow: "hidden",
  },
  doshaBarFill: {
    height: "100%",
    borderRadius: 4,
  },
  doshaPercent: {
    width: 40,
    fontSize: 14,
    color: "#71717a",
    textAlign: "right",
  },
  toggleButton: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginBottom: 24,
  },
  toggleText: {
    fontSize: 14,
    color: "#6366f1",
  },
  toggleArrow: {
    fontSize: 10,
    color: "#6366f1",
  },
  toggleArrowUp: {
    transform: [{ rotate: "180deg" }],
  },
  card: {
    width: "100%",
    backgroundColor: "#18191d",
    borderRadius: 16,
    padding: 20,
    marginBottom: 16,
  },
  cardTitle: {
    fontSize: 14,
    fontWeight: "600",
    color: "#f4f4f5",
    marginBottom: 16,
  },
  listItem: {
    flexDirection: "row",
    gap: 10,
    paddingVertical: 6,
  },
  listBullet: {
    color: "#22c55e",
    fontSize: 14,
    fontWeight: "600",
  },
  listText: {
    color: "#a1a1aa",
    fontSize: 14,
    flex: 1,
  },
  note: {
    fontSize: 13,
    color: "#52525b",
    textAlign: "center",
    lineHeight: 20,
    marginTop: 16,
  },
  footer: {
    position: "absolute",
    bottom: 0,
    left: 0,
    right: 0,
    padding: 20,
    paddingBottom: 40,
    backgroundColor: "#0a0a0a",
  },
  continueButton: {
    backgroundColor: "#6366f1",
    paddingVertical: 18,
    borderRadius: 14,
    alignItems: "center",
  },
  continueButtonText: {
    fontSize: 16,
    fontWeight: "600",
    color: "#fff",
  },
});
