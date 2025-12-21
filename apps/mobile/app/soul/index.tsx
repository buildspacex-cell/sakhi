"use client";

import React from "react";
import { View, Text, ScrollView, StyleSheet } from "react-native";
import { useEffect, useState } from "react";
import { normalizeSoulState, summarizeSoul } from "@ui/soulViewModel";
import { VictoryPie, VictoryTheme } from "victory-native";

export default function SoulHomeScreen() {
  const [state, setState] = useState<any>({});
  const [summary, setSummary] = useState<any>({});

  useEffect(() => {
    const fetchData = async () => {
      const [s, sm] = await Promise.all([
        fetch("http://localhost:8000/soul/state/demo").then((r) => r.json()).catch(() => ({})),
        fetch("http://localhost:8000/soul/summary/demo").then((r) => r.json()).catch(() => ({})),
      ]);
      setState(normalizeSoulState(s || {}));
      setSummary(summarizeSoul(normalizeSoulState(s || {}), sm || {}));
    };
    fetchData();
  }, []);

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.heading}>Soul Snapshot</Text>
      <View style={styles.chartCard}>
        <Text style={styles.title}>Coherence</Text>
        <VictoryPie
          theme={VictoryTheme.material}
          colorScale={["#22c55e", "#e5e7eb"]}
          innerRadius={60}
          padAngle={2}
          data={[
            { x: "Aligned", y: (summary.coherence || 0) * 100 },
            { x: "Gap", y: 100 - (summary.coherence || 0) * 100 },
          ]}
          labels={() => null}
        />
        <Text style={styles.value}>{Math.round((summary.coherence || 0) * 100)}%</Text>
      </View>
      <Card title="Values" items={state.core_values} />
      <Card title="Identity Themes" items={state.identity_themes} />
      <Card title="Shadow" items={summary.shadow} tone="shadow" />
      <Card title="Light" items={summary.light} tone="light" />
      <View style={styles.card}>
        <Text style={styles.title}>Coherence</Text>
        <Text style={styles.value}>{Math.round((summary.coherence || 0) * 100)}%</Text>
        <Text style={styles.subtitle}>Dominant friction: {summary.friction || "None"}</Text>
      </View>
    </ScrollView>
  );
}

function Card({ title, items, tone }: { title: string; items?: string[]; tone?: "shadow" | "light" }) {
  return (
    <View style={styles.card}>
      <Text style={styles.title}>{title}</Text>
      {items?.length ? (
        items.map((item) => (
          <Text key={item} style={[styles.tag, tone === "shadow" ? styles.shadow : tone === "light" ? styles.light : null]}>
            {item}
          </Text>
        ))
      ) : (
        <Text style={styles.subtitle}>None yet.</Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#fdfbf6" },
  content: { padding: 16, gap: 12 },
  heading: { fontSize: 22, fontWeight: "700", color: "#1f2937" },
  chartCard: { backgroundColor: "#fff", borderRadius: 16, padding: 12, shadowColor: "#000", shadowOpacity: 0.05, shadowRadius: 4, alignItems: "center" },
  card: { backgroundColor: "#fff", borderRadius: 16, padding: 12, shadowColor: "#000", shadowOpacity: 0.05, shadowRadius: 4 },
  title: { fontSize: 14, fontWeight: "600", color: "#4b5563", marginBottom: 6 },
  value: { fontSize: 24, fontWeight: "700", color: "#111827" },
  subtitle: { fontSize: 12, color: "#6b7280" },
  tag: { paddingVertical: 4, paddingHorizontal: 8, borderRadius: 12, marginVertical: 2, color: "#111827", backgroundColor: "#f3f4f6" },
  shadow: { backgroundColor: "#fee2e2", color: "#b91c1c" },
  light: { backgroundColor: "#d1fae5", color: "#065f46" },
});
