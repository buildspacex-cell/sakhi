"use client";

import React, { useEffect, useState } from "react";
import { ScrollView, View, Text, StyleSheet } from "react-native";
import { VictoryPie, VictoryTheme, VictoryLegend } from "victory-native";
import { summarizeSoul, normalizeSoulState } from "@ui/soulViewModel";

export default function SoulShadowScreen() {
  const [summary, setSummary] = useState<any>({});
  useEffect(() => {
    Promise.all([
      fetch("http://localhost:8000/soul/state/demo").then((r) => r.json()).catch(() => ({})),
      fetch("http://localhost:8000/soul/summary/demo").then((r) => r.json()).catch(() => ({})),
    ]).then(([state, sum]) => setSummary(summarizeSoul(normalizeSoulState(state || {}), sum || {})));
  }, []);

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.heading}>Shadow & Light</Text>
      {(summary.shadow?.length || summary.light?.length) ? (
        <View style={styles.chartCard}>
          <VictoryLegend
            x={40}
            orientation="horizontal"
            gutter={20}
            data={[
              { name: "Shadow", symbol: { fill: "#b91c1c" } },
              { name: "Light", symbol: { fill: "#047857" } },
            ]}
          />
          <VictoryPie
            theme={VictoryTheme.material}
            colorScale={["#b91c1c", "#047857"]}
            data={[
              { x: "Shadow", y: summary.shadow?.length || 0.1 },
              { x: "Light", y: summary.light?.length || 0.1 },
            ]}
            innerRadius={60}
            labels={({ datum }) => `${datum.x}: ${datum.y}`}
          />
        </View>
      ) : null}
      <Card title="Shadow" items={summary.shadow} tone="shadow" />
      <Card title="Light" items={summary.light} tone="light" />
      <View style={styles.card}>
        <Text style={styles.title}>Dominant Friction</Text>
        <Text style={styles.subtitle}>{summary.friction || "None detected"}</Text>
      </View>
    </ScrollView>
  );
}

function Card({ title, items, tone }: { title: string; items?: string[]; tone?: "shadow" | "light" }) {
  const style = tone === "shadow" ? styles.shadow : tone === "light" ? styles.light : null;
  return (
    <View style={styles.card}>
      <Text style={styles.title}>{title}</Text>
      {items?.length ? items.map((item) => <Text key={item} style={[styles.tag, style]}>{item}</Text>) : <Text style={styles.subtitle}>None yet.</Text>}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#fdfbf6" },
  content: { padding: 16, gap: 12 },
  heading: { fontSize: 20, fontWeight: "700", color: "#1f2937" },
  chartCard: { backgroundColor: "#fff", borderRadius: 14, padding: 12, shadowColor: "#000", shadowOpacity: 0.05, shadowRadius: 4 },
  card: { backgroundColor: "#fff", borderRadius: 14, padding: 12, shadowColor: "#000", shadowOpacity: 0.05, shadowRadius: 4 },
  title: { fontSize: 14, fontWeight: "600", color: "#4b5563", marginBottom: 6 },
  tag: { paddingVertical: 4, paddingHorizontal: 8, borderRadius: 12, marginVertical: 2, color: "#111827", backgroundColor: "#f3f4f6" },
  subtitle: { fontSize: 12, color: "#6b7280" },
  shadow: { backgroundColor: "#fee2e2", color: "#b91c1c" },
  light: { backgroundColor: "#d1fae5", color: "#065f46" },
});
