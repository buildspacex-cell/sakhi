import React, { useMemo, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  SafeAreaView,
  ScrollView,
  StatusBar,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import { useAuth } from "../lib/auth/AuthContext";

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL || "http://localhost:8080";
const API_KEY = process.env.EXPO_PUBLIC_API_KEY || "";
const DEMO_PERSON_ID = process.env.EXPO_PUBLIC_DEMO_PERSON_ID || "";

type ProtocolOption = {
  id: string;
  title: string;
  category: string;
  duration_minutes: number;
  related_dosha?: string | null;
  expected_effect: string;
  safety_note: string;
  steps: string[];
};

type CheckinResult = {
  checkin_id: string;
  symptom: string;
  dosha_hint?: string | null;
  confidence: number;
  uncertainty: number;
  dosha_context?: string | null;
  explanation: string;
  urgency: string;
  evidence: Array<{
    factor_type: string;
    description: string;
    confidence: number;
    evidence?: string | null;
  }>;
  protocols: ProtocolOption[];
};

const symptoms = ["anxious", "scattered", "irritable", "sluggish", "overwhelmed"];
const energyLevels = [0.2, 0.4, 0.6, 0.8, 1.0];

export default function MobileCheckinScreen() {
  const router = useRouter();
  const { user } = useAuth();
  const personId = user?.personId || DEMO_PERSON_ID;

  const [symptom, setSymptom] = useState("anxious");
  const [energyIndex, setEnergyIndex] = useState(2);
  const [bodyCuesText, setBodyCuesText] = useState("");
  const [note, setNote] = useState("");

  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [result, setResult] = useState<CheckinResult | null>(null);
  const [busyProtocolId, setBusyProtocolId] = useState<string | null>(null);

  const energy = energyLevels[energyIndex];
  const bodyCues = useMemo(
    () =>
      bodyCuesText
        .split(",")
        .map((v) => v.trim())
        .filter(Boolean),
    [bodyCuesText]
  );

  const requestHeaders = {
    "Content-Type": "application/json",
    ...(API_KEY ? { "X-API-Key": API_KEY } : {}),
  };

  const runCheckin = async () => {
    if (!personId || !symptom.trim()) return;

    setRunning(true);
    setError(null);
    setStatus(null);
    setResult(null);

    try {
      const response = await fetch(`${BACKEND_URL}/learning/companion/checkin`, {
        method: "POST",
        headers: requestHeaders,
        body: JSON.stringify({
          person_id: personId,
          symptom: symptom.trim(),
          energy_level: energy,
          body_cues: bodyCues,
          note: note.trim() || undefined,
        }),
      });

      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(payload?.detail || payload?.error || "Check-in failed");
      }

      setResult(payload as CheckinResult);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Check-in failed");
    } finally {
      setRunning(false);
    }
  };

  const trackProtocol = async (protocol: ProtocolOption) => {
    if (!personId || !result) return;

    setError(null);
    setStatus(null);
    setBusyProtocolId(protocol.id);

    try {
      const response = await fetch(`${BACKEND_URL}/learning/companion/followup/plan`, {
        method: "POST",
        headers: requestHeaders,
        body: JSON.stringify({
          person_id: personId,
          symptom: result.symptom,
          protocol_id: protocol.id,
          target_days: 7,
          target_per_day: 1,
          checkin_id: result.checkin_id,
        }),
      });

      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(payload?.detail || payload?.error || "Failed to start tracking");
      }

      setStatus(`Tracking started for ${protocol.title}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start tracking");
    } finally {
      setBusyProtocolId(null);
    }
  };

  const markDone = async (protocol: ProtocolOption) => {
    if (!personId || !result) return;

    setError(null);
    setStatus(null);
    setBusyProtocolId(protocol.id);

    try {
      const response = await fetch(`${BACKEND_URL}/learning/companion/protocol/complete`, {
        method: "POST",
        headers: requestHeaders,
        body: JSON.stringify({
          person_id: personId,
          symptom: result.symptom,
          protocol_id: protocol.id,
          was_effective: true,
          effectiveness_score: 0.8,
        }),
      });

      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(payload?.detail || payload?.error || "Failed to mark protocol complete");
      }

      setStatus(`Completed ${protocol.title}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to mark protocol complete");
    } finally {
      setBusyProtocolId(null);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" />
      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.headerRow}>
          <View>
            <Text style={styles.kicker}>Ayurvedic Companion</Text>
            <Text style={styles.title}>Quick Check-In</Text>
            <Text style={styles.subtitle}>Understand this moment and choose a 2, 5, or 10 minute action.</Text>
          </View>
          <Pressable style={styles.backButton} onPress={() => router.back()}>
            <Ionicons name="close" size={20} color="#a1a1aa" />
          </Pressable>
        </View>

        {!personId && (
          <View style={styles.noticeWarning}>
            <Text style={styles.noticeText}>Sign in to run a live check-in.</Text>
          </View>
        )}

        <View style={styles.card}>
          <Text style={styles.label}>What are you feeling right now?</Text>
          <View style={styles.rowWrap}>
            {symptoms.map((item) => (
              <Pressable
                key={item}
                style={[styles.pill, symptom === item && styles.pillActive]}
                onPress={() => setSymptom(item)}
              >
                <Text style={[styles.pillText, symptom === item && styles.pillTextActive]}>{item}</Text>
              </Pressable>
            ))}
          </View>

          <Text style={styles.label}>Energy ({Math.round(energy * 100)}%)</Text>
          <View style={styles.rowWrap}>
            {energyLevels.map((level, idx) => (
              <Pressable
                key={level}
                style={[styles.energyPill, energyIndex === idx && styles.energyPillActive]}
                onPress={() => setEnergyIndex(idx)}
              >
                <Text style={[styles.energyText, energyIndex === idx && styles.energyTextActive]}>
                  {Math.round(level * 100)}%
                </Text>
              </Pressable>
            ))}
          </View>

          <Text style={styles.label}>Body cues (optional, comma-separated)</Text>
          <TextInput
            style={styles.input}
            value={bodyCuesText}
            onChangeText={setBodyCuesText}
            placeholder="dry mouth, shallow breath"
            placeholderTextColor="#52525b"
          />

          <Text style={styles.label}>Note (optional)</Text>
          <TextInput
            style={[styles.input, styles.textarea]}
            multiline
            value={note}
            onChangeText={setNote}
            placeholder="What happened right before this?"
            placeholderTextColor="#52525b"
          />

          <Pressable
            style={[styles.primaryButton, (running || !personId) && styles.buttonDisabled]}
            onPress={runCheckin}
            disabled={running || !personId}
          >
            {running ? (
              <ActivityIndicator size="small" color="#f4f4f5" />
            ) : (
              <Text style={styles.primaryButtonText}>Understand This Moment</Text>
            )}
          </Pressable>
        </View>

        {error && (
          <View style={styles.noticeError}>
            <Text style={styles.noticeText}>{error}</Text>
          </View>
        )}

        {status && (
          <View style={styles.noticeSuccess}>
            <Text style={styles.noticeText}>{status}</Text>
          </View>
        )}

        {result && (
          <>
            <View style={styles.card}>
              <Text style={styles.cardTitle}>Why this might be happening</Text>
              <Text style={styles.explanation}>{result.explanation}</Text>
              <Text style={styles.metaText}>
                Dosha: {result.dosha_hint || "unknown"} | Confidence: {Math.round(result.confidence * 100)}% | Uncertainty: {Math.round(result.uncertainty * 100)}%
              </Text>
              {result.dosha_context && <Text style={styles.metaText}>Context: {result.dosha_context}</Text>}

              {result.evidence?.map((item, index) => (
                <View key={`${item.description}-${index}`} style={styles.evidenceRow}>
                  <Text style={styles.evidenceText}>
                    {Math.round(item.confidence * 100)}% {item.description}
                  </Text>
                </View>
              ))}
            </View>

            <View style={styles.card}>
              <Text style={styles.cardTitle}>Choose your protocol</Text>
              {result.protocols.map((protocol) => (
                <View key={protocol.id} style={styles.protocolCard}>
                  <View style={styles.protocolHeader}>
                    <Text style={styles.protocolTitle}>{protocol.title}</Text>
                    <Text style={styles.durationTag}>{protocol.duration_minutes}m</Text>
                  </View>
                  <Text style={styles.protocolEffect}>{protocol.expected_effect}</Text>
                  {protocol.steps.map((step, index) => (
                    <Text key={`${protocol.id}-${index}`} style={styles.stepText}>• {step}</Text>
                  ))}
                  <Text style={styles.safetyText}>Safety: {protocol.safety_note}</Text>

                  <View style={styles.actionsRow}>
                    <Pressable
                      style={[styles.secondaryButton, busyProtocolId === protocol.id && styles.buttonDisabled]}
                      onPress={() => trackProtocol(protocol)}
                      disabled={busyProtocolId === protocol.id}
                    >
                      <Text style={styles.secondaryButtonText}>Track 7 Days</Text>
                    </Pressable>
                    <Pressable
                      style={[styles.secondaryButton, busyProtocolId === protocol.id && styles.buttonDisabled]}
                      onPress={() => markDone(protocol)}
                      disabled={busyProtocolId === protocol.id}
                    >
                      <Text style={styles.secondaryButtonText}>Mark Done</Text>
                    </Pressable>
                  </View>
                </View>
              ))}
            </View>
          </>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#0a0a0a",
  },
  content: {
    padding: 16,
    gap: 12,
    paddingBottom: 40,
  },
  headerRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
  },
  kicker: {
    fontSize: 12,
    color: "#71717a",
    textTransform: "uppercase",
    letterSpacing: 1,
  },
  title: {
    marginTop: 4,
    fontSize: 28,
    fontWeight: "700",
    color: "#f4f4f5",
  },
  subtitle: {
    marginTop: 4,
    color: "#a1a1aa",
    maxWidth: 290,
    lineHeight: 20,
  },
  backButton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: "#2a2b30",
    alignItems: "center",
    justifyContent: "center",
  },
  card: {
    backgroundColor: "#141416",
    borderRadius: 14,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: "#24242a",
    padding: 14,
    gap: 10,
  },
  label: {
    fontSize: 13,
    color: "#a1a1aa",
  },
  rowWrap: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
  },
  pill: {
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: "#2f3036",
    backgroundColor: "#111215",
  },
  pillActive: {
    borderColor: "#22c55e",
    backgroundColor: "rgba(34, 197, 94, 0.15)",
  },
  pillText: {
    color: "#d4d4d8",
    fontSize: 13,
  },
  pillTextActive: {
    color: "#dcfce7",
  },
  energyPill: {
    paddingHorizontal: 10,
    paddingVertical: 7,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: "#2f3036",
  },
  energyPillActive: {
    borderColor: "#22c55e",
    backgroundColor: "rgba(34, 197, 94, 0.15)",
  },
  energyText: {
    color: "#a1a1aa",
    fontSize: 12,
  },
  energyTextActive: {
    color: "#dcfce7",
  },
  input: {
    borderRadius: 10,
    borderWidth: 1,
    borderColor: "#2f3036",
    backgroundColor: "#101116",
    color: "#f4f4f5",
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
  textarea: {
    minHeight: 90,
    textAlignVertical: "top",
  },
  primaryButton: {
    marginTop: 4,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: "#22c55e",
    backgroundColor: "rgba(34, 197, 94, 0.2)",
    paddingVertical: 12,
    alignItems: "center",
  },
  primaryButtonText: {
    color: "#f4f4f5",
    fontWeight: "600",
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  noticeWarning: {
    borderRadius: 10,
    borderWidth: 1,
    borderColor: "#f59e0b",
    backgroundColor: "rgba(245, 158, 11, 0.12)",
    padding: 10,
  },
  noticeError: {
    borderRadius: 10,
    borderWidth: 1,
    borderColor: "#ef4444",
    backgroundColor: "rgba(239, 68, 68, 0.12)",
    padding: 10,
  },
  noticeSuccess: {
    borderRadius: 10,
    borderWidth: 1,
    borderColor: "#22c55e",
    backgroundColor: "rgba(34, 197, 94, 0.12)",
    padding: 10,
  },
  noticeText: {
    color: "#e4e4e7",
  },
  cardTitle: {
    color: "#f4f4f5",
    fontSize: 17,
    fontWeight: "600",
  },
  explanation: {
    color: "#f4f4f5",
    lineHeight: 22,
  },
  metaText: {
    color: "#a1a1aa",
    fontSize: 13,
    lineHeight: 18,
  },
  evidenceRow: {
    borderLeftWidth: 2,
    borderLeftColor: "#3f3f46",
    paddingLeft: 10,
  },
  evidenceText: {
    color: "#d4d4d8",
    fontSize: 13,
  },
  protocolCard: {
    backgroundColor: "#101116",
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#2a2b30",
    padding: 12,
    gap: 8,
  },
  protocolHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  protocolTitle: {
    color: "#f4f4f5",
    fontSize: 15,
    fontWeight: "600",
    flex: 1,
    paddingRight: 8,
  },
  durationTag: {
    color: "#22c55e",
    borderWidth: 1,
    borderColor: "#22c55e",
    borderRadius: 999,
    paddingHorizontal: 8,
    paddingVertical: 2,
    fontSize: 12,
  },
  protocolEffect: {
    color: "#a1a1aa",
    fontSize: 13,
    lineHeight: 18,
  },
  stepText: {
    color: "#e4e4e7",
    fontSize: 13,
    lineHeight: 18,
  },
  safetyText: {
    color: "#f59e0b",
    fontSize: 12,
  },
  actionsRow: {
    flexDirection: "row",
    gap: 8,
    marginTop: 2,
  },
  secondaryButton: {
    flex: 1,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#34353b",
    alignItems: "center",
    paddingVertical: 9,
  },
  secondaryButtonText: {
    color: "#f4f4f5",
    fontSize: 13,
  },
});
