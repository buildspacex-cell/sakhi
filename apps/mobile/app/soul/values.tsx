"use client";

import React, { useEffect, useState } from "react";
import { ScrollView, View, Text, StyleSheet } from "react-native";
import { VictoryPie, VictoryTheme, VictoryBar, VictoryChart, VictoryAxis } from "victory-native";
import { normalizeSoulState } from "@ui/soulViewModel";

export default function SoulValuesScreen() {
  const [state, setState] = useState<any>({});
  useEffect(() => {
    fetch("http://localhost:8000/soul/state/demo")
      .then((r) => r.json())
      .then((data) => setState(normalizeSoulState(data || {})))
      .catch(() => setState({}));
  }, []);

  const aversionVsLonging = [
    { name: "Longing", value: (state.longing || []).length },
    { name: "Aversions", value: (state.aversions || []).length },
    { name: "Commitments", value: (state.commitments || []).length },
  ];

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.heading}>Values & Commitments</Text>
      {state.core_values?.length ? (
        <View style={styles.chartCard}>
          <VictoryPie
            theme={VictoryTheme.material}
            innerRadius={70}
            padAngle={3}
            colorScale="qualitative"
            data={(state.core_values || []).map((v: string) => ({ x: v, y: 1 }))}
            labels={({ datum }) => datum.x}
          />
        </View>
      ) : null}
      {aversionVsLonging.some((item) => item.value > 0) ? (
        <View style={styles.chartCard}>
          <VictoryChart domainPadding={10}>
            <VictoryAxis />
            <VictoryBar data={aversionVsLonging} x="name" y="value" style={{ data: { fill: "#0ea5e9" } }} />
          </VictoryChart>
        </View>
      ) : null}
      <Card title="Values" items={state.core_values} />
      <Card title="Longings" items={state.longing} />
      <Card title="Aversions" items={state.aversions} />
      <Card title="Identity Themes" items={state.identity_themes} />
      <Card title="Commitments" items={state.commitments} />
    </ScrollView>
  );
}

function Card({ title, items }: { title: string; items?: string[] }) {
  return (
    <View style={styles.card}>
      <Text style={styles.title}>{title}</Text>
      {items?.length ? items.map((item) => <Text key={item} style={styles.tag}>{item}</Text>) : <Text style={styles.subtitle}>None yet.</Text>}
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
});
