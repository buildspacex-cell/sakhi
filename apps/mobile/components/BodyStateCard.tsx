// =============================================================================
// BodyStateCard — Shows current body state from HealthKit data
// =============================================================================
// Displays on the Soul dashboard: sleep, heart rate, HRV, energy, dosha assessment.

import React, { useEffect, useState } from "react";
import { View, Text, StyleSheet, ActivityIndicator } from "react-native";
import { config } from "../lib/config";

interface BodyState {
  sleep?: {
    quality?: string;
    duration_hours?: number;
  };
  vitals?: {
    resting_hr?: number;
    hrv_sdnn?: number;
  };
  energy?: {
    level?: string;
  };
  dosha?: {
    dominant?: string;
    assessment?: string;
  };
  ojas?: {
    level?: number;
  };
}

interface Props {
  personId: string;
}

export default function BodyStateCard({ personId }: Props) {
  const [bodyState, setBodyState] = useState<BodyState | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!personId) return;

    fetch(`${config.backendUrl}/health/body-state/${personId}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        setBodyState(data);
        setLoading(false);
      })
      .catch(() => {
        setError(true);
        setLoading(false);
      });
  }, [personId]);

  if (loading) {
    return (
      <View style={styles.card}>
        <ActivityIndicator size="small" color="#6366f1" />
      </View>
    );
  }

  if (error || !bodyState) {
    return null; // Graceful degradation — no card if no data
  }

  const sleep = bodyState.sleep;
  const vitals = bodyState.vitals;
  const energy = bodyState.energy;
  const dosha = bodyState.dosha;

  return (
    <View style={styles.card}>
      <Text style={styles.cardTitle}>Body State</Text>

      <View style={styles.grid}>
        {/* Sleep */}
        {sleep?.duration_hours != null && (
          <View style={styles.metric}>
            <Text style={styles.metricValue}>
              {sleep.duration_hours.toFixed(1)}h
            </Text>
            <Text style={styles.metricLabel}>Sleep</Text>
            {sleep.quality && (
              <Text style={styles.metricSub}>{sleep.quality}</Text>
            )}
          </View>
        )}

        {/* Resting HR */}
        {vitals?.resting_hr != null && (
          <View style={styles.metric}>
            <Text style={styles.metricValue}>
              {Math.round(vitals.resting_hr)}
            </Text>
            <Text style={styles.metricLabel}>RHR (bpm)</Text>
          </View>
        )}

        {/* HRV */}
        {vitals?.hrv_sdnn != null && (
          <View style={styles.metric}>
            <Text style={styles.metricValue}>
              {Math.round(vitals.hrv_sdnn)}
            </Text>
            <Text style={styles.metricLabel}>HRV (ms)</Text>
          </View>
        )}

        {/* Energy */}
        {energy?.level && (
          <View style={styles.metric}>
            <Text style={styles.metricValue}>
              {energy.level.charAt(0).toUpperCase() + energy.level.slice(1)}
            </Text>
            <Text style={styles.metricLabel}>Energy</Text>
          </View>
        )}
      </View>

      {/* Dosha Assessment */}
      {dosha?.dominant && (
        <View style={styles.doshaRow}>
          <Text style={styles.doshaLabel}>Body dosha:</Text>
          <Text style={styles.doshaValue}>
            {dosha.dominant.charAt(0).toUpperCase() + dosha.dominant.slice(1)}
          </Text>
          {dosha.assessment && (
            <Text style={styles.doshaSub}> — {dosha.assessment}</Text>
          )}
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
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
  grid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 16,
  },
  metric: {
    minWidth: 70,
    alignItems: "center",
  },
  metricValue: {
    fontSize: 22,
    fontWeight: "700",
    color: "#f4f4f5",
  },
  metricLabel: {
    fontSize: 11,
    color: "#71717a",
    marginTop: 2,
  },
  metricSub: {
    fontSize: 10,
    color: "#6366f1",
    marginTop: 1,
  },
  doshaRow: {
    flexDirection: "row",
    alignItems: "center",
    marginTop: 16,
    paddingTop: 12,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: "#27272a",
  },
  doshaLabel: {
    fontSize: 12,
    color: "#71717a",
  },
  doshaValue: {
    fontSize: 12,
    fontWeight: "600",
    color: "#f4f4f5",
    marginLeft: 4,
  },
  doshaSub: {
    fontSize: 12,
    color: "#a1a1aa",
  },
});
