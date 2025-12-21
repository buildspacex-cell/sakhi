"use client";

import React, { useEffect, useState } from "react";
import { ScrollView, View, Text, StyleSheet } from "react-native";
import { VictoryBar, VictoryChart, VictoryTheme, VictoryAxis } from "victory-native";
import { timelineSeries } from "@ui/soulViewModel";
import { useMemo } from "react";

export default function SoulFrictionScreen() {
  const [friction, setFriction] = useState<string | null>(null);
  const [heat, setHeat] = useState<{ name: string; value: number }[]>([]);

  useEffect(() => {
    Promise.all([
      fetch("http://localhost:8000/soul/summary/demo").then((r) => r.json()).catch(() => ({})),
      fetch("http://localhost:8000/soul/timeline/demo").then((r) => r.json()).catch(() => []),
    ]).then(([summary, tl]) => {
      setFriction(summary?.dominant_friction || null);
      const series = timelineSeries(tl || []);
      const buckets = series.reduce<Record<string, number>>((acc, pt) => {
        if (pt.conflict) acc.conflict = (acc.conflict || 0) + pt.conflict;
        if (pt.friction) acc.friction = (acc.friction || 0) + pt.friction;
        return acc;
      }, {});
      setHeat(Object.entries(buckets).map(([name, value]) => ({ name, value })));
    });
  }, []);

  const heatRows = useMemo(() => {
    if (!heat.length) return null;
    const max = Math.max(...heat.map((h) => h.value), 1);
    return heat.map((h) => {
      const alpha = 0.25 + (h.value / max) * 0.6;
      return (
        <View key={h.name} style={[styles.heatRow, { backgroundColor: `rgba(249, 115, 22, ${alpha})` }]}>
          <Text style={styles.heatLabel}>{h.name}</Text>
          <Text style={styles.heatValue}>{h.value}</Text>
        </View>
      );
    });
  }, [heat]);

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.heading}>Value–Friction</Text>
      {heat.length ? (
        <View style={styles.chartCard}>
          <VictoryChart theme={VictoryTheme.material} domainPadding={15}>
            <VictoryAxis />
            <VictoryBar data={heat} x="name" y="value" style={{ data: { fill: "#f97316" } }} />
          </VictoryChart>
        </View>
      ) : null}
      {heatRows}
      <View style={styles.card}>
        <Text style={styles.title}>Dominant Friction</Text>
        <Text style={styles.subtitle}>{friction || "None detected."}</Text>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#fdfbf6" },
  content: { padding: 16, gap: 12 },
  heading: { fontSize: 20, fontWeight: "700", color: "#1f2937" },
  chartCard: { backgroundColor: "#fff", borderRadius: 14, padding: 12, shadowColor: "#000", shadowOpacity: 0.05, shadowRadius: 4 },
  card: { backgroundColor: "#fff", borderRadius: 14, padding: 12, shadowColor: "#000", shadowOpacity: 0.05, shadowRadius: 4 },
  title: { fontSize: 14, fontWeight: "600", color: "#4b5563", marginBottom: 6 },
  subtitle: { fontSize: 12, color: "#6b7280" },
  heatRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", padding: 10, borderRadius: 12, marginVertical: 4 },
  heatLabel: { fontSize: 13, fontWeight: "600", color: "#7c2d12" },
  heatValue: { fontSize: 16, fontWeight: "700", color: "#7c2d12" },
});
