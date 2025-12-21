"use client";

import React, { useEffect, useState } from "react";
import { ScrollView, View, Text, StyleSheet } from "react-native";
import { timelineSeries } from "@ui/soulViewModel";
import { VictoryChart, VictoryLine, VictoryTheme, VictoryLegend } from "victory-native";

export default function SoulTimelineScreen() {
  const [series, setSeries] = useState<any[]>([]);
  useEffect(() => {
    fetch("http://localhost:8000/soul/timeline/demo")
      .then((r) => r.json())
      .then((data) => setSeries(timelineSeries(data || [])))
      .catch(() => setSeries([]));
  }, []);

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.heading}>Soul Timeline</Text>
      {series.length ? (
        <View style={styles.chartCard}>
          <VictoryChart theme={VictoryTheme.material} domainPadding={10}>
            <VictoryLegend
              x={50}
              orientation="horizontal"
              gutter={20}
              data={[
                { name: "Shadow", symbol: { fill: "#b91c1c" } },
                { name: "Light", symbol: { fill: "#047857" } },
              ]}
            />
            <VictoryLine data={series.map((s, i) => ({ x: i + 1, y: s.shadow }))} style={{ data: { stroke: "#b91c1c" } }} />
            <VictoryLine data={series.map((s, i) => ({ x: i + 1, y: s.light }))} style={{ data: { stroke: "#047857" } }} />
          </VictoryChart>
        </View>
      ) : (
        <Text style={styles.subtitle}>No timeline data.</Text>
      )}
      {series.map((pt, idx) => (
        <View key={idx} style={styles.card}>
          <Text style={styles.title}>{pt.ts || `T-${idx + 1}`}</Text>
          <Text style={styles.subtitle}>Shadow {pt.shadow} · Light {pt.light} · Conflict {pt.conflict} · Friction {pt.friction}</Text>
        </View>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#fdfbf6" },
  content: { padding: 16, gap: 10 },
  heading: { fontSize: 20, fontWeight: "700", color: "#1f2937" },
  card: { backgroundColor: "#fff", borderRadius: 14, padding: 12, shadowColor: "#000", shadowOpacity: 0.05, shadowRadius: 4 },
  chartCard: { backgroundColor: "#fff", borderRadius: 14, padding: 12, shadowColor: "#000", shadowOpacity: 0.05, shadowRadius: 4, height: 260 },
  title: { fontSize: 14, fontWeight: "600", color: "#111827" },
  subtitle: { fontSize: 12, color: "#6b7280", marginTop: 4 },
});
