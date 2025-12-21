"use client";

import React, { useEffect, useState } from "react";
import { ScrollView, View, Text, StyleSheet } from "react-native";

export default function SoulNarrativeScreen() {
  const [data, setData] = useState<any>({});
  useEffect(() => {
    fetch("http://localhost:8000/soul/narrative/demo")
      .then((r) => r.json())
      .then((d) => setData(d || {}))
      .catch(() => setData({}));
  }, []);

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.heading}>Soul Narrative</Text>
      <Card title="Identity Arc" text={data.identity_arc} />
      <Card title="Archetype" text={data.soul_archetype} />
      <Card title="Life Phase" text={data.life_phase} />
      <Card title="Value Conflicts" list={data.value_conflicts} />
      <Card title="Healing Direction" list={data.healing_direction} />
      <Card title="Narrative Tension" text={data.narrative_tension} />
    </ScrollView>
  );
}

function Card({ title, text, list }: { title: string; text?: string; list?: string[] }) {
  return (
    <View style={styles.card}>
      <Text style={styles.title}>{title}</Text>
      {list?.length ? list.map((item) => <Text key={item} style={styles.subtitle}>{item}</Text>) : <Text style={styles.subtitle}>{text || "None"}</Text>}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#fdfbf6" },
  content: { padding: 16, gap: 12 },
  heading: { fontSize: 20, fontWeight: "700", color: "#1f2937" },
  card: { backgroundColor: "#fff", borderRadius: 14, padding: 12, shadowColor: "#000", shadowOpacity: 0.05, shadowRadius: 4 },
  title: { fontSize: 14, fontWeight: "600", color: "#4b5563", marginBottom: 6 },
  subtitle: { fontSize: 12, color: "#6b7280" },
});
