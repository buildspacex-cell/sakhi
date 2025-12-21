"use client";

import React, { useEffect, useState } from "react";
import { ScrollView, View, Text, StyleSheet } from "react-native";
import { VictoryPie, VictoryTheme } from "victory-native";

export default function SoulAlignmentScreen() {
  const [data, setData] = useState<any>({});

  useEffect(() => {
    fetch("http://localhost:8000/soul/alignment/demo")
      .then((r) => r.json())
      .then((d) => setData(d || {}))
      .catch(() => setData({}));
  }, []);

  const score = Math.max(0, Math.min(1, data.alignment_score || 0));

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.heading}>Alignment</Text>
      <View style={styles.card}>
        <Text style={styles.title}>Alignment Score</Text>
        <VictoryPie
          theme={VictoryTheme.material}
          colorScale={["#22c55e", "#e5e7eb"]}
          innerRadius={60}
          padAngle={2}
          data={[
            { x: "Aligned", y: score * 100 },
            { x: "Gap", y: 100 - score * 100 },
          ]}
          labels={() => null}
        />
        <Text style={styles.value}>{Math.round(score * 100)}%</Text>
      </View>
      <View style={styles.card}>
        <Text style={styles.title}>Conflict Zones</Text>
        {data.conflict_zones?.length ? (
          data.conflict_zones.map((c: string) => <Text key={c} style={styles.subtitle}>{c}</Text>)
        ) : (
          <Text style={styles.subtitle}>None</Text>
        )}
      </View>
      <View style={styles.card}>
        <Text style={styles.title}>Suggestions</Text>
        {data.action_suggestions?.length ? (
          data.action_suggestions.map((c: string) => <Text key={c} style={styles.subtitle}>{c}</Text>)
        ) : (
          <Text style={styles.subtitle}>None</Text>
        )}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#fdfbf6" },
  content: { padding: 16, gap: 12 },
  heading: { fontSize: 20, fontWeight: "700", color: "#1f2937" },
  card: { backgroundColor: "#fff", borderRadius: 14, padding: 12, shadowColor: "#000", shadowOpacity: 0.05, shadowRadius: 4, alignItems: "center" },
  title: { fontSize: 14, fontWeight: "600", color: "#4b5563", marginBottom: 6 },
  value: { fontSize: 24, fontWeight: "700", color: "#111827" },
  subtitle: { fontSize: 12, color: "#6b7280", alignSelf: "flex-start" },
});
